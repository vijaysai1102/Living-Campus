import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ResetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "campus.db"
        os.environ["LC_DB_PATH"] = str(self.db_path)

        import config.settings as settings
        import core.database as database
        self.settings_patch = patch.object(settings, "DB_PATH", self.db_path)
        self.database_patch = patch.object(database, "DB_PATH", self.db_path)
        self.settings_patch.start()
        self.database_patch.start()

        database.init_db()

        from core.emotion_engine import update_emotions
        from core.memory_manager import save_chat_message, save_memory
        from core.relationship_engine import increment_interactions, update_relationship

        update_emotions("professor", {"angry": 20, "happy": -10})
        update_relationship("professor", {"trust": -15, "hostility": 12})
        increment_interactions("professor")
        save_memory("professor", "Student admitted using ChatGPT on Lab 7")
        save_chat_message("professor", "user", "I used ChatGPT")
        save_chat_message("professor", "npc", "That is academic dishonesty.")

        save_memory("ta", "Student emails at 2am")
        save_chat_message("ta", "user", "can you grade this tonight")

    def tearDown(self):
        self.settings_patch.stop()
        self.database_patch.stop()
        self.tmp.cleanup()

    def test_reset_npc_clears_all_persisted_state(self):
        from core.emotion_engine import get_emotions
        from core.memory_manager import get_recent_memories, load_chat_history
        from core.npc_loader import load_npc
        from core.relationship_engine import DEFAULT_RELATIONSHIP, get_relationship
        from core.reset import reset_npc

        reset_npc("professor")

        npc = load_npc("professor")
        self.assertEqual(get_emotions("professor"), npc["initial_mood"])
        self.assertEqual(get_relationship("professor"), DEFAULT_RELATIONSHIP)
        self.assertEqual(get_recent_memories("professor", n=20), [])
        self.assertEqual(load_chat_history("professor"), [])

        # Other NPCs are left alone
        self.assertTrue(get_recent_memories("ta", n=20))
        self.assertTrue(load_chat_history("ta"))

    def test_reset_campus_clears_every_npc(self):
        from core.memory_manager import get_recent_memories, load_chat_history
        from core.reset import reset_campus

        reset_campus()
        self.assertEqual(get_recent_memories("professor", n=20), [])
        self.assertEqual(get_recent_memories("ta", n=20), [])
        self.assertEqual(load_chat_history("ta"), [])

    def test_session_helpers_drop_cached_chat(self):
        from core.reset import clear_session_campus, clear_session_npc

        session = {
            "chat_histories": {"professor": [{"role": "npc", "content": "hello"}]},
            "opening_sent": {"professor", "ta"},
            "active_npc": "professor",
        }
        clear_session_npc(session, "professor")
        self.assertNotIn("professor", session["chat_histories"])
        self.assertNotIn("professor", session["opening_sent"])
        self.assertIn("ta", session["opening_sent"])

        clear_session_campus(session)
        self.assertEqual(session["chat_histories"], {})
        self.assertEqual(session["opening_sent"], set())
        self.assertIsNone(session["active_npc"])


if __name__ == "__main__":
    unittest.main()

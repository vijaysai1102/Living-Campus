import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai.gemini_client import _parse_response


class PromiseTests(unittest.TestCase):
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

    def tearDown(self):
        self.settings_patch.stop()
        self.database_patch.stop()
        self.tmp.cleanup()

    def test_parser_reads_promise_status(self):
        parsed = _parse_response("""{
          "reply": "You actually showed up.",
          "memory_kind": "promise",
          "promise_status": "Kept"
        }""")
        self.assertEqual(parsed["promise_status"], "kept")

    def test_promise_memory_creates_pending_due_in_three_ticks(self):
        from core.gossip_engine import get_tick
        from core.promises import get_pending_promises, maybe_track_from_turn

        maybe_track_from_turn("ta", {
            "memory_note": "Student promised to stop emailing at 2am",
            "memory_kind": "promise",
            "memory_tags": "",
            "promise_status": "",
        }, memory_id=1)
        pending = get_pending_promises("ta")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["status"], "pending")
        self.assertEqual(pending[0]["due_tick"], get_tick() + 3)

    def test_kept_before_due_raises_trust(self):
        from core.promises import get_promises, maybe_track_from_turn
        from core.relationship_engine import get_relationship

        maybe_track_from_turn("ta", {
            "memory_note": "Student promised to come to office hours",
            "memory_kind": "promise",
            "promise_status": "",
        })
        before = get_relationship("ta")["trust"]
        maybe_track_from_turn("ta", {"promise_status": "kept", "memory_kind": "fact"})
        after = get_relationship("ta")
        self.assertEqual(get_promises("ta")[0]["status"], "kept")
        self.assertEqual(after["trust"], before + 4)

    def test_ghosting_breaks_promise_and_hurts_trust(self):
        from core.gossip_engine import advance_and_resolve
        from core.memory_manager import get_recent_memories
        from core.promises import create_promise, get_promises
        from core.relationship_engine import get_relationship

        create_promise("professor", "Student promised to attend the BBQ")
        before = get_relationship("professor")["trust"]
        for _ in range(3):
            advance_and_resolve()
        promises = get_promises("professor")
        self.assertEqual(promises[0]["status"], "broken")
        self.assertEqual(get_relationship("professor")["trust"], max(0, before - 8))
        memories = get_recent_memories("professor", n=10)
        self.assertTrue(any(m.get("kind") == "grievance" for m in memories))

    def test_prompt_lists_open_promises(self):
        from ai.prompt_builder import build_prompt
        from core.npc_loader import load_npc
        from core.promises import create_promise, format_pending_promises

        create_promise("ta", "Student promised to stop emailing at 2am")
        prompt = build_prompt(
            npc=load_npc("ta"),
            emotions={"happy": 20, "angry": 10, "suspicious": 40, "stressed": 75, "excited": 10, "annoyed": 55},
            relationship={"trust": 50, "friendship": 30, "hostility": 0, "respect": 30, "interactions_count": 0},
            memories=[],
            rag_context=[],
            chat_history=[],
            user_message="hey",
            promises_text=format_pending_promises("ta"),
        )
        self.assertIn("OPEN PROMISES", prompt)
        self.assertIn("stop emailing at 2am", prompt)

    def test_reset_clears_promises(self):
        from core.promises import create_promise, get_pending_promises
        from core.reset import reset_npc

        create_promise("ta", "Student promised to rewrite Lab 7")
        reset_npc("ta")
        self.assertEqual(get_pending_promises("ta"), [])


if __name__ == "__main__":
    unittest.main()

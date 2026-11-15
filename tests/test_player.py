import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class PlayerIdentityTests(unittest.TestCase):
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

    def test_default_player_is_unnamed(self):
        from core.player import format_player_for_prompt, get_player

        player = get_player()
        self.assertFalse(player["introduced"])
        self.assertIn("has not given you a name", format_player_for_prompt())

    def test_saved_name_is_injected_into_prompts(self):
        from ai.prompt_builder import build_prompt
        from core.npc_loader import load_npc
        from core.player import format_player_for_prompt, player_label, save_player

        save_player("Amina", "sophomore")
        self.assertEqual(player_label()[:5], "Amina")
        text = format_player_for_prompt()
        self.assertIn("Amina", text)
        self.assertIn("sophomore", text)
        prompt = build_prompt(
            npc=load_npc("friend"),
            emotions={"happy": 70, "angry": 0, "suspicious": 0, "stressed": 30, "excited": 65, "annoyed": 5},
            relationship={"trust": 50, "friendship": 30, "hostility": 0, "respect": 30, "interactions_count": 0},
            memories=[],
            rag_context=[],
            chat_history=[],
            user_message="hey",
            player_text=text,
        )
        self.assertIn("THE STUDENT", prompt)
        self.assertIn("Amina", prompt)


if __name__ == "__main__":
    unittest.main()

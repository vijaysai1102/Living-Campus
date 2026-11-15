import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class StoryHookTests(unittest.TestCase):
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

    def test_batman_almost_slips_when_trust_is_high(self):
        from ai.prompt_builder import build_prompt
        from core.npc_loader import load_npc
        from core.relationship_engine import update_relationship
        from core.story_engine import format_story_hooks

        update_relationship("friend", {"trust": 10})
        update_relationship("friend", {"trust": 10})
        hooks = format_story_hooks("friend")
        self.assertIn("@CSHallwayDrama", hooks)
        self.assertIn("do not invent a new quest", hooks.lower())
        prompt = build_prompt(
            npc=load_npc("friend"),
            emotions={"happy": 70, "angry": 0, "suspicious": 0, "stressed": 30, "excited": 65, "annoyed": 5},
            relationship={"trust": 70, "friendship": 30, "hostility": 0, "respect": 30, "interactions_count": 0},
            memories=[],
            rag_context=[],
            chat_history=[],
            user_message="what's the tea",
            hooks_text=hooks,
        )
        self.assertIn("STORY HOOKS", prompt)
        self.assertIn("@CSHallwayDrama", prompt)


if __name__ == "__main__":
    unittest.main()

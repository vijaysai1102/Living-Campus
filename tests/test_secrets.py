import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class SecretFlagTests(unittest.TestCase):
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

    def test_instagram_is_learnable_from_batman_without_reading_json_in_play(self):
        from core.relationship_engine import update_relationship
        from core.story_engine import consider_discovery, known_secrets, secret_state

        self.assertEqual(secret_state("batman_instagram"), "unknown")
        update_relationship("friend", {"trust": 25})
        consider_discovery("friend", {
            "reply": "bro ngl I run @CSHallwayDrama, Priya is the decoy",
            "memory_note": "Admitted he runs the Instagram",
            "memory_kind": "secret",
            "keep_secret": True,
            "shareable_facts": [],
        })
        self.assertEqual(secret_state("batman_instagram"), "known")
        titles = {item["title"] for item in known_secrets()}
        self.assertIn("Who runs @CSHallwayDrama", titles)

    def test_leak_creates_a_campus_fact(self):
        from core.social_graph import list_recent_facts
        from core.story_engine import set_secret_state, secret_state

        set_secret_state("batman_instagram", "leaked")
        self.assertEqual(secret_state("batman_instagram"), "leaked")
        texts = " ".join(fact.get("fact_text", "") for fact in list_recent_facts())
        self.assertIn("@CSHallwayDrama", texts)

    def test_reset_campus_clears_flags(self):
        from core.reset import reset_campus
        from core.story_engine import get_flag, set_flag

        set_flag("secret.batman_instagram", "known")
        reset_campus()
        self.assertEqual(get_flag("secret.batman_instagram"), "")


if __name__ == "__main__":
    unittest.main()

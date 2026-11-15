import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class CampusPulseTests(unittest.TestCase):
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

    def test_quiet_campus_has_empty_pulse(self):
        from core.gossip_engine import player_pulse
        self.assertEqual(player_pulse(), [])

    def test_pulse_shows_what_you_said_not_who_reported_it(self):
        from core.fact_extractor import ingest_shareable_facts
        from core.gossip_engine import player_pulse, propagate_facts

        ingest_shareable_facts("friend", {
            "shareable_facts": ["Student admitted using ChatGPT on Lab 7"],
            "keep_secret": False,
            "fact_sensitivity": 75,
        })
        before = player_pulse()
        self.assertTrue(any("You told Batman" in line for line in before))
        self.assertFalse(any("Kevin" in line and "Webb" in line for line in before))

        propagate_facts()
        after = " ".join(player_pulse())
        self.assertIn("You told Batman", after)
        self.assertNotIn("professor", after.lower())
        self.assertFalse("told Dr." in after and "Kevin" in after)


if __name__ == "__main__":
    unittest.main()

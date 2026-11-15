import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class EndingTests(unittest.TestCase):
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

    def test_finals_week_and_instagram_tag(self):
        from core.clock import clock_from_tick, is_finals_week
        from core.player import save_player
        from core.reset import start_new_semester
        from core.story_engine import ending_tags, format_ending_recap, set_secret_state

        self.assertTrue(is_finals_week({"week": 12, "weekday": "monday", "period": "morning"}))
        self.assertTrue(is_finals_week({"week": 11, "weekday": "friday", "period": "night"}))
        self.assertFalse(is_finals_week(clock_from_tick(0)))
        set_secret_state("batman_instagram", "leaked")
        tags = ending_tags()
        self.assertIn("instagram_exposed", tags)
        recap = format_ending_recap()
        self.assertIn("@CSHallwayDrama", recap)
        save_player("Amina", "sophomore")
        start_new_semester()
        from core.clock import get_clock
        from core.player import get_player
        from core.story_engine import secret_state
        self.assertEqual(get_clock()["week"], 6)
        self.assertEqual(get_player()["display_name"], "Amina")
        self.assertEqual(secret_state("batman_instagram"), "unknown")


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class CampusMapTests(unittest.TestCase):
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

    def test_thursday_afternoon_places_match_schedules(self):
        from core.schedules import locations, npcs_at

        clock = {"weekday": "thursday", "period": "afternoon"}
        self.assertEqual(npcs_at("Webb's office", clock), ["professor"])
        self.assertEqual(npcs_at("Kevin's cubicle (Room 203)", clock), ["ta"])
        self.assertEqual(npcs_at("Quad", clock), ["friend"])
        self.assertEqual(npcs_at("The Dungeon", clock), [])
        self.assertIn("lecture hall", locations())


if __name__ == "__main__":
    unittest.main()

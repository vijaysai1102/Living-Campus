import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class JournalTests(unittest.TestCase):
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

    def test_journal_lists_favors_secrets_and_deadlines(self):
        from core.story_engine import format_favor_hooks, journal_data, set_secret_state

        format_favor_hooks("ta")
        set_secret_state("batman_instagram", "known")
        data = journal_data()
        self.assertTrue(any(favor["id"] == "kevin_no_2am" for favor in data["favors"]))
        self.assertTrue(any(secret["title"].startswith("Who runs") for secret in data["secrets"]))
        self.assertTrue(any("Midterm" in item["title"] for item in data["deadlines"]))


if __name__ == "__main__":
    unittest.main()

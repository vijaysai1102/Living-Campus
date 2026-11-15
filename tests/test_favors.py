import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class FavorTests(unittest.TestCase):
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

    def test_kevin_asks_once_then_succeeds(self):
        from core.story_engine import (
            format_favor_hooks,
            get_favor_status,
            resolve_favors,
        )

        hook = format_favor_hooks("ta")
        self.assertIn("Stop the 2am emails", hook)
        self.assertEqual(get_favor_status("kevin_no_2am"), "asked")
        second = format_favor_hooks("ta")
        self.assertIn("2am", second)
        resolve_favors("ta", {"favor_update": "succeeded", "memory_note": "Student promised to stop emailing at 2am"})
        self.assertEqual(get_favor_status("kevin_no_2am"), "succeeded")

    def test_batman_favor_waits_for_instagram_secret(self):
        from core.story_engine import format_favor_hooks, get_favor_status, set_secret_state
        from core.relationship_engine import update_relationship

        update_relationship("friend", {"trust": 10})
        update_relationship("friend", {"trust": 10})
        self.assertEqual(format_favor_hooks("friend"), "")
        self.assertEqual(get_favor_status("batman_dont_tell"), "locked")
        set_secret_state("batman_instagram", "known")
        hook = format_favor_hooks("friend")
        self.assertIn("Don't tell about the Instagram", hook)
        self.assertEqual(get_favor_status("batman_dont_tell"), "asked")


if __name__ == "__main__":
    unittest.main()

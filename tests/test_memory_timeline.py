import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class MemoryTimelineTests(unittest.TestCase):
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

    def test_recent_memories_include_kind(self):
        from core.memory_manager import get_recent_memories, save_memory

        save_memory("friend", "Student knows about the Instagram", importance=9, kind="secret")
        save_memory("friend", "Student promised not to tell", importance=7, kind="promise")
        rows = get_recent_memories("friend", n=10)
        kinds = {row["kind"] for row in rows}
        self.assertIn("secret", kinds)
        self.assertIn("promise", kinds)

    def test_filter_and_secret_styling(self):
        from ui.meters import filter_timeline_memories, format_timeline_entry

        memories = [
            {"content": "Said hello", "kind": "fact", "importance": 3, "created_at": "2026-05-10 12:00:00"},
            {"content": "Knows Batman runs the Instagram", "kind": "secret", "importance": 9, "created_at": "2026-05-10 12:01:00"},
            {"content": "Broke a BBQ promise", "kind": "grievance", "importance": 8, "created_at": "2026-05-10 12:02:00"},
        ]
        secrets = filter_timeline_memories(memories, "secret")
        self.assertEqual(len(secrets), 1)
        entry = format_timeline_entry(secrets[0])
        self.assertTrue(entry["lock"])
        self.assertTrue(entry["star"])
        self.assertEqual(entry["emoji"], "🔒")
        self.assertEqual(entry["color"], "#c084fc")
        grievance = format_timeline_entry(memories[2])
        self.assertTrue(grievance["star"])
        self.assertFalse(grievance["lock"])


if __name__ == "__main__":
    unittest.main()

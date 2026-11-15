import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai.gemini_client import _parse_response


class TypedMemoryTests(unittest.TestCase):
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

    def test_parser_reads_kind_and_importance(self):
        parsed = _parse_response("""{
          "reply": "Do not be late.",
          "memory_note": "Student promised to come to Thursday office hours",
          "memory_kind": "Promise",
          "memory_importance": 8,
          "memory_tags": "office-hours,kevin"
        }""")
        self.assertEqual(parsed["memory_kind"], "promise")
        self.assertEqual(parsed["memory_importance"], 8)
        self.assertIn("office-hours", parsed["memory_tags"])

    def test_saved_memory_keeps_kind(self):
        from core.memory_manager import format_memories, get_recent_memories, save_memory

        save_memory("ta", "Student promised to stop emailing at 2am", importance=9, tags="promise", kind="promise")
        save_memory("ta", "Said hello in the hallway", importance=2, kind="fact")
        memories = get_recent_memories("ta", n=5)
        kinds = {m["kind"] for m in memories}
        self.assertIn("promise", kinds)
        self.assertIn("[promise | importance 9]", format_memories(memories))


if __name__ == "__main__":
    unittest.main()

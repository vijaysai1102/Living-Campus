import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class MemoryRetrievalTests(unittest.TestCase):
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

    def test_lab7_query_pulls_older_important_memory(self):
        from core.memory_manager import get_relevant_memories, save_memory

        save_memory("ta", "Student used ChatGPT on Lab 7", importance=9, tags="lab7,chatgpt", kind="secret")
        for i in range(6):
            save_memory("ta", f"Small talk number {i} about the weather", importance=2, kind="fact")

        relevant = get_relevant_memories("ta", query="can you help me with Lab 7", n=5)
        contents = [m["content"] for m in relevant]
        self.assertTrue(any("Lab 7" in c for c in contents))
        self.assertLess(contents.index(next(c for c in contents if "Lab 7" in c)), 5)


if __name__ == "__main__":
    unittest.main()

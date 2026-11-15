import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TimeAwareRagTests(unittest.TestCase):
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

    def test_week_six_boosts_midterm_and_hides_last_week(self):
        from core.rag_retriever import retrieve_context

        items = retrieve_context("professor", query="", clock={"week": 6})
        titles = [item.get("title", "") for item in items]
        self.assertTrue(any("Midterm" in title for title in titles))
        self.assertFalse(any("Project 2" in title for title in titles))

    def test_later_weeks_drop_expired_deadlines(self):
        from core.rag_retriever import retrieve_context

        items = retrieve_context("professor", query="midterm", clock={"week": 8})
        blob = " ".join(
            (item.get("title") or "") + " " + (item.get("description") or "")
            for item in items
        )
        self.assertNotIn("Midterm is this week", blob)
        self.assertFalse(any(item.get("due_week") == 6 for item in items))

    def test_opening_context_can_mention_this_week(self):
        from core.rag_retriever import format_context, retrieve_context

        text = format_context(retrieve_context("friend", query="", clock={"week": 6}))
        self.assertIn("week 6", text.lower())


if __name__ == "__main__":
    unittest.main()

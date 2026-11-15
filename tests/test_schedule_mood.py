import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ScheduleMoodTests(unittest.TestCase):
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

    def test_modifiers_are_prompt_only(self):
        from core.emotion_engine import get_emotions, mood_for_prompt

        base = get_emotions("professor")
        prompt_mood = mood_for_prompt("professor", base, {"week": 6, "weekday": "thursday", "period": "afternoon"})
        self.assertGreater(prompt_mood["annoyed"], base["annoyed"])
        self.assertEqual(get_emotions("professor"), base)

    def test_kevin_stresses_on_grading_and_batman_buzzes_friday(self):
        from core.emotion_engine import mood_caption, mood_for_prompt

        kevin = {"happy": 20, "angry": 10, "suspicious": 40, "stressed": 75, "excited": 10, "annoyed": 55}
        batman = {"happy": 70, "angry": 0, "suspicious": 0, "stressed": 30, "excited": 65, "annoyed": 5}
        grading = mood_for_prompt("ta", kevin, {"week": 6, "weekday": "thursday", "period": "night"})
        self.assertGreater(grading["stressed"], kevin["stressed"])
        friday = mood_for_prompt("friend", batman, {"week": 6, "weekday": "friday", "period": "evening"})
        self.assertGreater(friday["excited"], batman["excited"])
        self.assertIn("Dungeon", mood_caption("friend", {"week": 6, "weekday": "friday", "period": "evening"}))


if __name__ == "__main__":
    unittest.main()

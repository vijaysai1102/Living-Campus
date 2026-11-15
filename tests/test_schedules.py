import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ScheduleTests(unittest.TestCase):
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

    def test_thursday_afternoon_office_hours_are_open(self):
        from core.schedules import current_slot, is_interruptible

        clock = {"weekday": "thursday", "period": "afternoon"}
        webb = current_slot("professor", clock)
        self.assertEqual(webb["location"], "Webb's office")
        self.assertTrue(is_interruptible("professor", clock))
        self.assertTrue(is_interruptible("ta", clock))
        self.assertEqual(current_slot("friend", clock)["location"], "Quad")

    def test_webb_lecture_is_a_hallway_wave(self):
        from core.schedules import is_interruptible, unavailable_line

        clock = {"weekday": "thursday", "period": "morning"}
        self.assertFalse(is_interruptible("professor", clock))
        line = unavailable_line("professor", clock)
        self.assertIn("not taking visitors", line)

    def test_long_chat_can_miss_kevin(self):
        from core.clock import clock_from_tick
        from core.schedules import is_interruptible

        # tick 0 Thu afternoon: Kevin is free. A few periods later he is busy or gone.
        self.assertTrue(is_interruptible("ta", clock_from_tick(0)))
        friday_evening = clock_from_tick(6)  # Thu eve, night, Fri morning, afternoon, evening?
        # tick 3 = Friday morning (Kevin in lecture, busy)
        self.assertFalse(is_interruptible("ta", clock_from_tick(3)))
        self.assertEqual(friday_evening["weekday"], "friday")

    def test_prompt_includes_location(self):
        from ai.prompt_builder import build_prompt
        from core.npc_loader import load_npc
        from core.schedules import format_location_for_prompt

        clock = {"weekday": "thursday", "period": "afternoon"}
        prompt = build_prompt(
            npc=load_npc("professor"),
            emotions={"happy": 40, "angry": 0, "suspicious": 30, "stressed": 20, "excited": 20, "annoyed": 10},
            relationship={"trust": 50, "friendship": 30, "hostility": 0, "respect": 30, "interactions_count": 0},
            memories=[],
            rag_context=[],
            chat_history=[],
            user_message="got a minute?",
            location_text=format_location_for_prompt("professor", clock),
        )
        self.assertIn("WHERE YOU ARE", prompt)
        self.assertIn("Webb's office", prompt)


if __name__ == "__main__":
    unittest.main()

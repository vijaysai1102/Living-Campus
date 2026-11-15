import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class CampusClockTests(unittest.TestCase):
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

    def test_tick_zero_is_week_six_thursday_afternoon(self):
        from core.clock import format_clock, get_clock

        clock = get_clock()
        self.assertEqual(clock["week"], 6)
        self.assertEqual(clock["weekday"], "thursday")
        self.assertEqual(clock["period"], "afternoon")
        self.assertIn("Week 6", format_clock(clock))
        self.assertIn("Thursday afternoon", format_clock(clock))

    def test_each_tick_is_one_period_and_persists(self):
        from core.clock import clock_from_tick, get_clock
        from core.database import get_connection
        from core.gossip_engine import advance_and_resolve

        self.assertEqual(clock_from_tick(1)["period"], "evening")
        self.assertEqual(clock_from_tick(2)["period"], "night")
        friday_morning = clock_from_tick(3)
        self.assertEqual(friday_morning["weekday"], "friday")
        self.assertEqual(friday_morning["period"], "morning")

        advance_and_resolve()
        clock = get_clock()
        self.assertEqual(clock["period"], "evening")
        conn = get_connection()
        row = conn.execute("SELECT week, weekday, period FROM campus_state WHERE id = 1").fetchone()
        conn.close()
        self.assertEqual(row["weekday"], "thursday")
        self.assertEqual(row["period"], "evening")

    def test_skip_day_lands_on_next_morning(self):
        from core.clock import get_clock, skip_day

        skip_day()
        clock = get_clock()
        self.assertEqual(clock["weekday"], "friday")
        self.assertEqual(clock["period"], "morning")

    def test_reset_campus_restores_midterm_week(self):
        from core.clock import get_clock
        from core.gossip_engine import advance_and_resolve
        from core.reset import reset_campus

        for _ in range(10):
            advance_and_resolve()
        reset_campus()
        clock = get_clock()
        self.assertEqual(clock["tick"], 0)
        self.assertEqual(clock["week"], 6)
        self.assertEqual(clock["weekday"], "thursday")
        self.assertEqual(clock["period"], "afternoon")


if __name__ == "__main__":
    unittest.main()

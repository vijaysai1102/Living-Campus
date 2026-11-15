import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TimeCostTests(unittest.TestCase):
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

    def test_chat_or_leave_costs_exactly_one_period(self):
        from core.clock import advance_period, get_clock
        from core.gossip_engine import advance_and_resolve

        start = get_clock()
        advance_and_resolve()  # a chat beat
        after_chat = get_clock()
        self.assertEqual(after_chat["tick"], start["tick"] + 1)
        self.assertEqual(after_chat["period"], "evening")

        advance_period()  # leave / next period
        after_leave = get_clock()
        self.assertEqual(after_leave["tick"], start["tick"] + 2)
        self.assertEqual(after_leave["period"], "night")

    def test_prompt_knows_the_current_time(self):
        from ai.prompt_builder import build_prompt
        from core.clock import format_clock_for_prompt
        from core.npc_loader import load_npc

        prompt = build_prompt(
            npc=load_npc("ta"),
            emotions={"happy": 20, "angry": 10, "suspicious": 40, "stressed": 75, "excited": 10, "annoyed": 55},
            relationship={"trust": 50, "friendship": 30, "hostility": 0, "respect": 30, "interactions_count": 0},
            memories=[],
            rag_context=[],
            chat_history=[],
            user_message="got a minute?",
            clock_text=format_clock_for_prompt(),
        )
        self.assertIn("CURRENT TIME", prompt)
        self.assertIn("Thursday afternoon", prompt)
        self.assertIn("week 6", prompt)


if __name__ == "__main__":
    unittest.main()

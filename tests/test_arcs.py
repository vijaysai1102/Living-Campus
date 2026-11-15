import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config.settings import ARCS_PATH


class ArcAuthoringTests(unittest.TestCase):
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

    def test_four_arcs_have_hook_pressure_resolution(self):
        data = json.loads(ARCS_PATH.read_text(encoding="utf-8"))
        arcs = {arc["id"]: arc for arc in data["arcs"]}
        self.assertEqual(set(arcs), {"webb", "kevin", "batman", "campus"})
        for arc in arcs.values():
            phases = [beat["phase"] for beat in arc["beats"]]
            self.assertGreaterEqual(len(arc["beats"]), 3)
            self.assertIn("hook", phases)
            self.assertIn("pressure", phases)
            self.assertIn("resolution", phases)
            self.assertTrue(set(arc.get("npc_ids", [])).issubset({"professor", "ta", "friend"}))

    def test_webb_hook_is_prompted_in_week_six(self):
        from core.story_engine import consider_arcs, format_arc_hooks, get_flag

        hook = format_arc_hooks("professor")
        self.assertIn("MOSS", hook)
        consider_arcs("professor", {"reply": "A recommendation requires a clean MOSS record."})
        self.assertEqual(get_flag("arc.webb"), "hook")
        pressure = format_arc_hooks("professor")
        self.assertIn("Dean", pressure)


if __name__ == "__main__":
    unittest.main()

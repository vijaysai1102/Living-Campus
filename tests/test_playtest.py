import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config.settings import THRESHOLDS_PATH


class PlaytestThresholdTests(unittest.TestCase):
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

    def test_people_pleaser_and_chaos_endings_differ(self):
        from core.npc_loader import load_all_npcs
        from core.relationship_engine import update_relationship
        from core.story_engine import ending_tags, set_secret_state

        for npc in load_all_npcs():
            update_relationship(npc["id"], {"trust": 10})
        pleased = set(ending_tags())
        self.assertIn("people_pleaser", pleased)
        self.assertNotIn("chaos_run", pleased)

        set_secret_state("batman_instagram", "leaked")
        chaos = set(ending_tags())
        self.assertIn("chaos_run", chaos)
        self.assertNotEqual(pleased, chaos)

    def test_instagram_is_learnable_and_documented(self):
        from core.relationship_engine import update_relationship
        from core.story_engine import consider_discovery, load_thresholds, secret_state

        documented = load_thresholds()["instagram"]
        secrets = json.loads((Path(__file__).resolve().parents[1] / "data" / "story" / "secrets.json").read_text(encoding="utf-8"))
        insta = next(item for item in secrets["secrets"] if item["id"] == "batman_instagram")
        self.assertEqual(insta["discovery_conditions"]["min_trust_known"], documented["min_trust_known"])
        update_relationship("friend", {"trust": 10})
        update_relationship("friend", {"trust": 10})
        consider_discovery("friend", {"reply": "yeah I run @CSHallwayDrama, Priya is cover", "keep_secret": True})
        self.assertEqual(secret_state("batman_instagram"), "known")

    def test_promise_breaks_overnight_and_gossip_still_has_a_head_start(self):
        from core.clock import skip_day
        from core.fact_extractor import ingest_shareable_facts
        from core.gossip_engine import queue_new_gossip
        from core.promises import create_promise, get_promises
        from core.social_graph import get_knowledge_for_npc
        from core.story_engine import load_thresholds

        thresholds = load_thresholds()
        self.assertEqual(thresholds["promise_grace_ticks"], 3)
        create_promise("ta", "Student promised to stop emailing at 2am")
        skip_day()
        self.assertEqual(get_promises("ta")[0]["status"], "broken")

        ingest_shareable_facts("friend", {
            "shareable_facts": ["Student admitted using ChatGPT on Lab 7"],
            "keep_secret": False,
            "fact_sensitivity": 75,
        })
        queue_new_gossip()
        self.assertEqual(get_knowledge_for_npc("professor"), [])
        self.assertEqual(thresholds["gossip"]["kevin_to_webb_delay"], 2)


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class GossipDelayTests(unittest.TestCase):
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

    def test_rumors_do_not_land_on_the_same_tick(self):
        from core.fact_extractor import ingest_shareable_facts
        from core.gossip_engine import get_tick, queue_new_gossip
        from core.social_graph import get_knowledge_for_npc

        ingest_shareable_facts("friend", {
            "shareable_facts": ["Student admitted using ChatGPT on Lab 7"],
            "keep_secret": False,
            "fact_sensitivity": 75,
        })
        queued = queue_new_gossip()
        self.assertTrue(queued)
        self.assertEqual(get_tick(), 0)
        self.assertEqual(get_knowledge_for_npc("ta"), [])
        self.assertEqual(get_knowledge_for_npc("professor"), [])

    def test_you_can_reach_kevin_before_webb_hears(self):
        from core.fact_extractor import ingest_shareable_facts
        from core.gossip_engine import advance_and_resolve, queue_new_gossip
        from core.social_graph import get_knowledge_for_npc

        ingest_shareable_facts("friend", {
            "shareable_facts": ["Student admitted using ChatGPT on Lab 7"],
            "keep_secret": False,
            "fact_sensitivity": 75,
        })
        queue_new_gossip()

        # Walking across campus: Kevin hears, Webb does not.
        kevin_tick = webb_tick = None
        for i in range(1, 6):
            events = advance_and_resolve()
            if get_knowledge_for_npc("ta") and kevin_tick is None:
                kevin_tick = i
                self.assertTrue(any(event["to"] == "ta" for event in events))
                self.assertEqual(get_knowledge_for_npc("professor"), [])
            if get_knowledge_for_npc("professor"):
                webb_tick = i
                break

        self.assertEqual(kevin_tick, 1)
        self.assertIsNotNone(webb_tick)
        self.assertGreater(webb_tick, kevin_tick)


if __name__ == "__main__":
    unittest.main()

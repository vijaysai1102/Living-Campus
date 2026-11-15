import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class GossipEngineTests(unittest.TestCase):
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

    def _fact(self, text, source="friend", sensitivity=60, keep_secret=False):
        from core.social_graph import create_fact, grant_knowledge
        fact_id = create_fact(
            text,
            source_npc_id=source,
            sensitivity=sensitivity,
            keep_secret=keep_secret,
        )
        grant_knowledge(source, fact_id, status="known", hop=0)
        return fact_id

    def test_batman_leaks_to_kevin_not_webb(self):
        from core.gossip_engine import propagate_facts
        from core.social_graph import get_knowledge_for_npc

        fact_id = self._fact("Student skipped the faculty BBQ", sensitivity=40)
        spread = propagate_facts()
        listeners = {(e["from"], e["to"]) for e in spread}
        self.assertIn(("friend", "ta"), listeners)
        self.assertNotIn(("friend", "professor"), listeners)
        self.assertEqual(get_knowledge_for_npc("ta")[0]["fact_id"], fact_id)
        self.assertEqual(get_knowledge_for_npc("ta")[0]["status"], "rumor")
        self.assertEqual(get_knowledge_for_npc("professor"), [])

    def test_webb_does_not_gossip_to_batman(self):
        from core.gossip_engine import will_share

        fact = {
            "fact_text": "Student asked a weak question in lecture",
            "sensitivity": 20,
            "keep_secret": 0,
        }
        self.assertFalse(will_share("professor", "friend", fact))

    def test_high_trust_secret_is_kept(self):
        from core.gossip_engine import will_share
        from core.relationship_engine import reset_relationship

        reset_relationship("friend", {"trust": 80})
        fact = {
            "fact_text": "Student told Batman they run on almost no sleep",
            "sensitivity": 50,
            "keep_secret": 1,
        }
        self.assertFalse(will_share("friend", "ta", fact))

    def test_batman_still_leaks_secrets_when_trust_is_low(self):
        from core.gossip_engine import will_share
        from core.relationship_engine import reset_relationship

        reset_relationship("friend", {"trust": 25})
        fact = {
            "fact_text": "Student asked Batman to hide a ChatGPT confession",
            "sensitivity": 80,
            "keep_secret": 1,
        }
        self.assertTrue(will_share("friend", "ta", fact))

    def test_kevin_reports_cheating_to_webb_and_distorts_on_second_hop(self):
        from core.gossip_engine import propagate_facts
        from core.social_graph import get_fact, get_knowledge_for_npc

        fact_id = self._fact("Student admitted using ChatGPT on Lab 7", sensitivity=75)
        propagate_facts()

        webb = get_knowledge_for_npc("professor")
        self.assertEqual(len(webb), 1)
        self.assertEqual(webb[0]["fact_id"], fact_id)
        self.assertGreaterEqual(webb[0]["hop"], 2)
        self.assertIn("Someone in CS mentioned", get_fact(fact_id)["distorted_text"])

    def test_kevin_does_not_report_if_he_promised_secrecy(self):
        from core.gossip_engine import will_share

        fact = {
            "fact_text": "Student admitted using ChatGPT on Lab 7",
            "sensitivity": 80,
            "keep_secret": 1,
        }
        self.assertFalse(will_share("ta", "professor", fact))
        self.assertFalse(will_share("ta", "friend", fact))


if __name__ == "__main__":
    unittest.main()

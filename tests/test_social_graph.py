import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class SocialGraphTests(unittest.TestCase):
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

    def test_opinions_are_seeded_for_every_npc_pair(self):
        from core.social_graph import get_opinion, list_opinions

        webb_on_kevin = get_opinion("professor", "ta")
        self.assertIsNotNone(webb_on_kevin)
        self.assertGreater(webb_on_kevin["respect"], 50)

        batman_on_webb = get_opinion("friend", "professor")
        self.assertLess(batman_on_webb["trust"], 40)
        self.assertGreater(batman_on_webb["respect"], 50)

        self.assertEqual(len(list_opinions("professor")), 2)
        self.assertIsNone(get_opinion("professor", "professor"))

    def test_facts_and_knowledge_round_trip(self):
        from core.social_graph import create_fact, get_knowledge_for_npc, grant_knowledge

        fact_id = create_fact(
            "Student admitted using ChatGPT on Lab 7",
            source_npc_id="friend",
            sensitivity=70,
            keep_secret=False,
        )
        grant_knowledge("friend", fact_id, status="known", hop=0)
        grant_knowledge("ta", fact_id, status="rumor", hop=1)

        kevin_knows = get_knowledge_for_npc("ta")
        self.assertEqual(len(kevin_knows), 1)
        self.assertEqual(kevin_knows[0]["status"], "rumor")
        self.assertEqual(kevin_knows[0]["hop"], 1)
        self.assertIn("ChatGPT", kevin_knows[0]["fact_text"])
        self.assertEqual(get_knowledge_for_npc("professor"), [])

    def test_reset_restores_opinions_and_clears_knowledge(self):
        from core.reset import reset_campus, reset_npc
        from core.social_graph import (
            create_fact,
            get_knowledge_for_npc,
            get_opinion,
            grant_knowledge,
            upsert_opinion,
        )

        upsert_opinion("professor", "friend", trust=5, respect=5, irritation=90, note="furious")
        fact_id = create_fact("secret", source_npc_id="professor")
        grant_knowledge("professor", fact_id)
        grant_knowledge("ta", fact_id, status="rumor", hop=1)

        reset_npc("professor")
        restored = get_opinion("professor", "friend")
        self.assertEqual(restored["irritation"], 42)
        self.assertEqual(get_knowledge_for_npc("professor"), [])
        self.assertEqual(len(get_knowledge_for_npc("ta")), 1)

        reset_campus()
        self.assertEqual(get_knowledge_for_npc("ta"), [])
        self.assertEqual(get_opinion("ta", "professor")["respect"], 82)


if __name__ == "__main__":
    unittest.main()

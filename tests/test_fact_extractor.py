import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai.gemini_client import _parse_response


class FactExtractorTests(unittest.TestCase):
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

    def test_parser_reads_shareable_facts(self):
        parsed = _parse_response("""{
          "reply": "Bro what.",
          "shareable_facts": ["Student admitted using ChatGPT on Lab 7", {"text": ""}],
          "keep_secret": "true",
          "fact_sensitivity": 80
        }""")
        self.assertEqual(parsed["shareable_facts"], ["Student admitted using ChatGPT on Lab 7"])
        self.assertTrue(parsed["keep_secret"])
        self.assertEqual(parsed["fact_sensitivity"], 80)

    def test_small_talk_creates_no_facts(self):
        from core.fact_extractor import ingest_shareable_facts
        from core.social_graph import get_knowledge_for_npc, list_recent_facts

        ids = ingest_shareable_facts("friend", {"shareable_facts": [], "keep_secret": False})
        self.assertEqual(ids, [])
        self.assertEqual(list_recent_facts(), [])
        self.assertEqual(get_knowledge_for_npc("friend"), [])

    def test_confession_is_stored_and_known_by_speaker(self):
        from core.fact_extractor import ingest_shareable_facts
        from core.social_graph import get_fact, get_knowledge_for_npc

        ids = ingest_shareable_facts("friend", {
            "shareable_facts": ["Student admitted using ChatGPT on Lab 7"],
            "keep_secret": False,
            "fact_sensitivity": 75,
        })
        self.assertEqual(len(ids), 1)
        fact = get_fact(ids[0])
        self.assertIn("ChatGPT", fact["fact_text"])
        self.assertEqual(fact["source_npc_id"], "friend")
        self.assertEqual(fact["keep_secret"], 0)
        self.assertEqual(get_knowledge_for_npc("ta"), [])
        known = get_knowledge_for_npc("friend")
        self.assertEqual(len(known), 1)
        self.assertEqual(known[0]["status"], "known")

    def test_keep_secret_raises_sensitivity(self):
        from core.fact_extractor import ingest_shareable_facts
        from core.social_graph import get_fact

        fact_id = ingest_shareable_facts("ta", {
            "shareable_facts": ["Student asked Kevin not to tell Webb about a leaked guide"],
            "keep_secret": True,
            "fact_sensitivity": 40,
        })[0]
        fact = get_fact(fact_id)
        self.assertEqual(fact["keep_secret"], 1)
        self.assertGreaterEqual(fact["sensitivity"], 70)


if __name__ == "__main__":
    unittest.main()

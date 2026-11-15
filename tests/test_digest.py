import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class DigestTests(unittest.TestCase):
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

    def test_digest_includes_clock_and_deadlines(self):
        from core.digest import while_you_were_away

        lines = while_you_were_away()
        blob = " ".join(lines)
        self.assertTrue(any("Week 6" in line for line in lines))
        self.assertIn("Coming up", blob)
        self.assertLessEqual(len(lines), 4)

    def test_digest_mentions_hallway_noise_without_a_god_log(self):
        from core.digest import while_you_were_away
        from core.fact_extractor import ingest_shareable_facts
        from core.gossip_engine import advance_and_resolve, queue_new_gossip

        ingest_shareable_facts("friend", {
            "shareable_facts": ["Student admitted using ChatGPT on Lab 7"],
            "keep_secret": False,
            "fact_sensitivity": 75,
        })
        queue_new_gossip()
        advance_and_resolve()
        blob = " ".join(while_you_were_away())
        self.assertIn("ChatGPT", blob)
        self.assertNotIn("reported", blob.lower())


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class CrossNpcTests(unittest.TestCase):
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

    def test_insulting_kevin_to_batman_raises_irritation(self):
        from core.fact_extractor import ingest_shareable_facts
        from core.social_graph import get_opinion

        before = get_opinion("friend", "ta")["irritation"]
        ingest_shareable_facts("friend", {
            "shareable_facts": ["Student called Kevin useless and said his autograder is a joke"],
            "keep_secret": False,
            "fact_sensitivity": 55,
        })
        after = get_opinion("friend", "ta")
        self.assertGreater(after["irritation"], before)

    def test_kevin_gets_colder_when_the_insult_leaks(self):
        from core.fact_extractor import ingest_shareable_facts
        from core.gossip_engine import propagate_facts
        from core.relationship_engine import DEFAULT_RELATIONSHIP, get_relationship
        from core.social_graph import get_opinion

        ingest_shareable_facts("friend", {
            "shareable_facts": ["Student told Batman that Kevin is a useless TA"],
            "keep_secret": False,
            "fact_sensitivity": 50,
        })
        propagate_facts()
        rel = get_relationship("ta")
        self.assertGreater(rel["hostility"], DEFAULT_RELATIONSHIP["hostility"])
        self.assertLess(rel["trust"], DEFAULT_RELATIONSHIP["trust"])
        self.assertGreater(get_opinion("ta", "friend")["irritation"], 32)

    def test_prompt_includes_npc_opinions(self):
        from ai.prompt_builder import build_prompt
        from core.npc_loader import load_npc
        from core.social_graph import format_opinions_for_prompt

        text = format_opinions_for_prompt("professor")
        self.assertIn("Kevin Park", text)
        prompt = build_prompt(
            npc=load_npc("professor"),
            emotions={"happy": 40, "angry": 0, "suspicious": 30, "stressed": 20, "excited": 20, "annoyed": 10},
            relationship={"trust": 50, "friendship": 30, "hostility": 0, "respect": 30, "interactions_count": 0},
            memories=[],
            rag_context=[],
            chat_history=[],
            user_message="hi",
            opinions_text=text,
        )
        self.assertIn("HOW YOU FEEL ABOUT OTHER PEOPLE ON CAMPUS", prompt)
        self.assertIn("Kevin Park", prompt)


if __name__ == "__main__":
    unittest.main()

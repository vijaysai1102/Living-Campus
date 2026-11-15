import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class GossipPromptTests(unittest.TestCase):
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

    def test_format_uses_direct_and_rumor_wording(self):
        from core.gossip_engine import format_heard_around_campus
        from core.social_graph import create_fact, grant_knowledge

        self.assertIn("have not heard", format_heard_around_campus("ta"))

        fact_id = create_fact("Student admitted using ChatGPT on Lab 7", source_npc_id="friend")
        grant_knowledge("friend", fact_id, status="known", hop=0)
        grant_knowledge("ta", fact_id, status="rumor", hop=1)

        batman = format_heard_around_campus("friend")
        kevin = format_heard_around_campus("ta")
        webb = format_heard_around_campus("professor")
        self.assertIn("the student told you this", batman)
        self.assertIn("ChatGPT", batman)
        self.assertIn("you heard this as a rumor", kevin)
        self.assertIn("have not heard", webb)

    def test_prompt_includes_gossip_and_forbids_invention(self):
        from ai.prompt_builder import build_prompt
        from core.npc_loader import load_npc

        prompt = build_prompt(
            npc=load_npc("ta"),
            emotions={"happy": 20, "angry": 0, "suspicious": 40, "stressed": 75, "excited": 10, "annoyed": 55},
            relationship={"trust": 50, "friendship": 30, "hostility": 0, "respect": 30, "interactions_count": 2},
            memories=[],
            rag_context=[],
            chat_history=[],
            user_message="hey",
            gossip_text="- (you heard this as a rumor) Student admitted using ChatGPT on Lab 7",
        )
        self.assertIn("WHAT YOU'VE HEARD AROUND CAMPUS", prompt)
        self.assertIn("Student admitted using ChatGPT on Lab 7", prompt)
        self.assertIn("NEVER invent campus knowledge", prompt)


if __name__ == "__main__":
    unittest.main()

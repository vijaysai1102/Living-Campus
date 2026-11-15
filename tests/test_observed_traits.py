import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai.gemini_client import _parse_response


class ObservedTraitTests(unittest.TestCase):
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

    def test_parser_reads_observed_trait(self):
        parsed = _parse_response("""{
          "reply": "Do the work.",
          "observed_trait": "Diligent"
        }""")
        self.assertEqual(parsed["observed_trait"], "Diligent")

    def test_two_npcs_can_disagree(self):
        from core.traits import format_observed_traits, get_observed_traits, observe_trait

        observe_trait("professor", "diligent")
        observe_trait("friend", "untrustworthy")
        observe_trait("professor", "diligent")  # unique, no duplicate

        self.assertEqual(get_observed_traits("professor"), ["diligent"])
        self.assertEqual(get_observed_traits("friend"), ["untrustworthy"])
        self.assertIn("diligent", format_observed_traits("professor"))
        self.assertNotIn("untrustworthy", format_observed_traits("professor"))

    def test_prompt_includes_observed_traits(self):
        from ai.prompt_builder import build_prompt
        from core.npc_loader import load_npc
        from core.traits import format_observed_traits, observe_trait

        observe_trait("professor", "diligent")
        observe_trait("friend", "flaky")
        prompt = build_prompt(
            npc=load_npc("professor"),
            emotions={"happy": 40, "angry": 0, "suspicious": 30, "stressed": 20, "excited": 20, "annoyed": 10},
            relationship={"trust": 50, "friendship": 30, "hostility": 0, "respect": 30, "interactions_count": 0},
            memories=[],
            rag_context=[],
            chat_history=[],
            user_message="I finished the lab.",
            traits_text=format_observed_traits("professor"),
        )
        self.assertIn("HOW YOU CURRENTLY SEE THIS STUDENT", prompt)
        self.assertIn("How you currently see this student: diligent", prompt)
        self.assertNotIn("flaky", prompt)

    def test_reset_npc_clears_only_that_npcs_traits(self):
        from core.reset import reset_npc
        from core.traits import get_observed_traits, observe_trait

        observe_trait("professor", "diligent")
        observe_trait("friend", "untrustworthy")
        reset_npc("professor")
        self.assertEqual(get_observed_traits("professor"), [])
        self.assertEqual(get_observed_traits("friend"), ["untrustworthy"])


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class RelationshipDeltaTests(unittest.TestCase):
    def test_parser_extracts_relationship_delta(self):
        from ai.gemini_client import _parse_response

        raw = """{
          "reply": "That was a foolish lie.",
          "emotion_delta": {"Angry": 8, "happy": -4},
          "relationship_delta": {"Trust": -6, "hostility": 5, "respect": -3},
          "memory_note": "Student lied about the assignment."
        }"""
        parsed = _parse_response(raw)
        self.assertEqual(parsed["reply"], "That was a foolish lie.")
        self.assertEqual(parsed["emotion_delta"]["angry"], 8)
        self.assertEqual(parsed["relationship_delta"], {
            "trust": -6,
            "hostility": 5,
            "respect": -3,
        })

    def test_parser_survives_missing_relationship_delta(self):
        from ai.gemini_client import _parse_response

        parsed = _parse_response('{"reply": "ok", "memory_note": ""}')
        self.assertEqual(parsed["relationship_delta"], {})

    def test_deltas_are_clamped_and_applied(self):
        tmp = tempfile.TemporaryDirectory()
        db_path = Path(tmp.name) / "campus.db"
        os.environ["LC_DB_PATH"] = str(db_path)

        import config.settings as settings
        import core.database as database
        with patch.object(settings, "DB_PATH", db_path), patch.object(database, "DB_PATH", db_path):
            database.init_db()
            from core.relationship_engine import (
                DEFAULT_RELATIONSHIP,
                clamp_relationship_delta,
                get_relationship,
                update_relationship,
            )

            self.assertEqual(
                clamp_relationship_delta({"trust": -40, "friendship": 3, "nope": 1}),
                {"trust": -10, "friendship": 3},
            )

            update_relationship("professor", {"trust": -8, "hostility": 7, "respect": -4})
            rel = get_relationship("professor")
            self.assertEqual(rel["trust"], DEFAULT_RELATIONSHIP["trust"] - 8)
            self.assertEqual(rel["hostility"], DEFAULT_RELATIONSHIP["hostility"] + 7)
            self.assertEqual(rel["respect"], DEFAULT_RELATIONSHIP["respect"] - 4)
            self.assertEqual(rel["friendship"], DEFAULT_RELATIONSHIP["friendship"])

        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()

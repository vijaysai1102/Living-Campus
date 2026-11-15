import unittest

from core.consequences import format_consequences


class ConsequenceTests(unittest.TestCase):
    def test_formats_big_trust_swing_and_gossip(self):
        lines = format_consequences(
            {"trust": 50, "friendship": 30, "hostility": 0, "respect": 30, "npc_id": "ta"},
            {"trust": 42, "friendship": 30, "hostility": 4, "respect": 30, "npc_id": "ta"},
            [{"from": "friend", "to": "ta", "queued": True}],
        )
        self.assertIn("Kevin's trust -8", lines)
        self.assertIn("Batman might talk", lines)
        self.assertFalse(any("hostility" in line for line in lines))

    def test_ignores_small_relationship_noise(self):
        lines = format_consequences(
            {"trust": 50, "friendship": 30, "hostility": 0, "respect": 30, "npc_id": "professor"},
            {"trust": 52, "friendship": 31, "hostility": 0, "respect": 31, "npc_id": "professor"},
            [],
        )
        self.assertEqual(lines, [])

    def test_nested_snapshots_cover_every_npc(self):
        before = {
            "professor": {"trust": 50, "friendship": 30, "hostility": 0, "respect": 30},
            "friend": {"trust": 50, "friendship": 30, "hostility": 0, "respect": 30},
        }
        after = {
            "professor": {"trust": 42, "friendship": 30, "hostility": 0, "respect": 30},
            "friend": {"trust": 50, "friendship": 30, "hostility": 0, "respect": 30},
        }
        lines = format_consequences(before, after, [{"from": "ta", "to": "professor"}])
        self.assertIn("Webb's trust -8", lines)
        self.assertIn("Kevin might talk", lines)


if __name__ == "__main__":
    unittest.main()

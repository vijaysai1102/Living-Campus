import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CanonTests(unittest.TestCase):
    def _load(self, relative: str):
        with open(ROOT / relative, encoding="utf-8") as f:
            return json.load(f)

    def test_batman_runs_cshallwaydrama(self):
        npcs = self._load("data/npcs.json")
        batman = next(npc for npc in npcs["npcs"] if npc["id"] == "friend")
        self.assertIn("@CSHallwayDrama", batman["context"])
        self.assertIn("Priya Sharma", batman["context"])

        lore = self._load("data/campus_context/lore.json")
        instagram = next(item for item in lore["lore"] if "CSHallwayDrama" in item["content"])
        self.assertIn("Batman", instagram["content"])
        self.assertNotIn("Priya Sharma secretly runs", instagram["content"])

        rumors = self._load("data/campus_context/rumors.json")
        decoy = next(item for item in rumors["rumors"] if "CSHallwayDrama" in item["content"])
        self.assertIn("Priya Sharma", decoy["content"])


if __name__ == "__main__":
    unittest.main()

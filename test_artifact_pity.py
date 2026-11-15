"""Soul Artifact pity timer (pure logic). Run: python -m unittest test_artifact_pity -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_artifacts import art_due  # noqa: E402

H = 3600


class ArtifactPityTests(unittest.TestCase):
    def test_plain_chance_still_works(self):
        self.assertTrue(art_due(0.12, now=1000, last_art_at=999, pity_seconds=6 * H, roll=0.05))
        self.assertFalse(art_due(0.12, now=1000, last_art_at=999, pity_seconds=6 * H, roll=0.5))

    def test_pity_forces_an_artifact_after_the_window(self):
        now = 100 * H
        self.assertTrue(art_due(0.0, now=now, last_art_at=now - 6 * H, pity_seconds=6 * H, roll=0.99))
        self.assertFalse(art_due(0.0, now=now, last_art_at=now - 5 * H, pity_seconds=6 * H, roll=0.99))

    def test_never_had_one_counts_as_due(self):
        self.assertTrue(art_due(0.0, now=50 * H, last_art_at=0, pity_seconds=6 * H, roll=0.99))

    def test_pity_disabled_when_zero(self):
        self.assertFalse(art_due(0.0, now=50 * H, last_art_at=0, pity_seconds=0, roll=0.99))

    def test_chance_is_bounded(self):
        self.assertFalse(art_due(0.0, now=1, last_art_at=1, pity_seconds=6 * H, roll=0.0))
        self.assertTrue(art_due(1.0, now=1, last_art_at=1, pity_seconds=6 * H, roll=0.999))


if __name__ == "__main__":
    unittest.main()

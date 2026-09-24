import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from process_session import (  # noqa: E402
    campaign_slug,
    resolve_slug,
)


def _registry():
    return [
        {"slug": "michaelh", "display_name": "Michael", "discord_aliases": ["Michael"]},
        {"slug": "bigmikemc", "display_name": "Mike", "discord_aliases": ["Big Mike Mc"]},
    ]


class ResolveSlugTests(unittest.TestCase):
    def test_slug_override_beats_display_name(self):
        # 2026-07-15: player_name "Mike" + slug michaelh filed Michael under bigmikemc.
        reg = _registry()
        slug = resolve_slug(reg, "Mike", "Michael", slug_override="michaelh")
        self.assertEqual(slug, "michaelh")
        self.assertEqual(reg[1]["discord_aliases"], ["Big Mike Mc"])

    def test_slug_override_adds_alias_to_that_entry(self):
        reg = _registry()
        resolve_slug(reg, "Mike", "Big Mike (new handle)", slug_override="bigmikemc")
        self.assertIn("Big Mike (new handle)", reg[1]["discord_aliases"])
        self.assertEqual(len(reg), 2)

    def test_unknown_slug_override_appends_entry(self):
        reg = _registry()
        slug = resolve_slug(reg, "Patman", "Patman (Veratyr)", slug_override="patman")
        self.assertEqual(slug, "patman")
        self.assertEqual(reg[-1]["discord_aliases"], ["Patman (Veratyr)"])

    def test_known_alias_wins_without_override(self):
        reg = _registry()
        self.assertEqual(resolve_slug(reg, "Mike", "Michael", derive_if_missing=True), "michaelh")

    def test_display_name_fallback_without_override(self):
        reg = _registry()
        slug = resolve_slug(reg, "Mike", "BigMike2", derive_if_missing=True)
        self.assertEqual(slug, "bigmikemc")
        self.assertIn("BigMike2", reg[1]["discord_aliases"])


class CampaignSlugTests(unittest.TestCase):
    def test_slug_from_config_else_dir_name(self):
        self.assertEqual(campaign_slug(pathlib.Path("x/pandodnd"), {"slug": "pando", "name": "PandoDnD"}), "pando")
        self.assertEqual(campaign_slug(pathlib.Path("x/pandodnd"), {}), "pandodnd")


if __name__ == "__main__":
    unittest.main()

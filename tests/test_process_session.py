import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from process_session import (  # noqa: E402
    campaign_slug,
    leading_code,
    lookup_catalog,
    reconcile_adventure_code,
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


class LeadingCodeTests(unittest.TestCase):
    def test_codes(self):
        self.assertEqual(leading_code("FR-DC-LOOSE-001 Spells on the Loose"), "FR-DC-LOOSE-001")
        self.assertEqual(leading_code("PS-DC-PUB-15"), "PS-DC-PUB-15")
        self.assertEqual(leading_code("DDAL07-01 A City on the Edge"), "DDAL07-01")

    def test_no_code(self):
        self.assertIsNone(leading_code("Spells on the Loose"))
        self.assertIsNone(leading_code("This Spells Trouble FR-DC-LOOSE-003"))
        self.assertIsNone(leading_code("Half-Orc Tavern Night"))


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)
        entries = {
            # Real catalog typo: code -01, full_title -02.
            "546997": {"code": "FR-DC-LOOSE-01", "title": "Spells on the Loose",
                       "full_title": "FR-DC-LOOSE-02 Spells on the Loose", "level_range": "1-4"},
            "548631": {"code": "FR-DC-LOOSE-02", "title": "Spells Gone Wild",
                       "full_title": "FR-DC-LOOSE-02 Spells Gone Wild"},
            "100001": {"code": "PS-DC-PUB-1", "title": "First Round",
                       "full_title": "PS-DC-PUB-1 First Round"},
            "100015": {"code": "PS-DC-PUB-15", "title": "Spider Hunt",
                       "full_title": "PS-DC-PUB-15 Spider Hunt"},
            "200001": {"code": "SJ-DC", "title": "Happy New Year!",
                       "full_title": "SJ-DC Happy New Year!"},
            "200002": {"code": "SJ-DC-KEEP", "title": "The Keep",
                       "full_title": "SJ-DC-KEEP The Keep"},
        }
        for name, data in entries.items():
            (self.dir / f"{name}.json").write_text(json.dumps({"is_adventure": True, **data}))

    def tearDown(self):
        self._tmp.cleanup()

    def test_exact_code_beats_prefix_code(self):
        self.assertEqual(lookup_catalog(self.dir, "PS-DC-PUB-15 Spider Hunt")["code"], "PS-DC-PUB-15")

    def test_exact_code_without_digits(self):
        self.assertEqual(lookup_catalog(self.dir, "SJ-DC-KEEP The Keep")["code"], "SJ-DC-KEEP")

    def test_title_fallback(self):
        self.assertEqual(lookup_catalog(self.dir, "Spells Gone Wild")["code"], "FR-DC-LOOSE-02")

    def test_scenario_code_overrides_inconsistent_catalog(self):
        name = "FR-DC-LOOSE-001 Spells on the Loose"
        adv = reconcile_adventure_code(lookup_catalog(self.dir, name), name)
        self.assertEqual(adv["code"], "FR-DC-LOOSE-001")
        self.assertEqual(adv["full_title"], "FR-DC-LOOSE-001 Spells on the Loose")
        self.assertEqual(adv["level_range"], "1-4")

    def test_matching_code_left_alone(self):
        adv = lookup_catalog(self.dir, "PS-DC-PUB-15 Spider Hunt")
        self.assertIs(reconcile_adventure_code(adv, "PS-DC-PUB-15 Spider Hunt"), adv)


class CampaignSlugTests(unittest.TestCase):
    def test_slug_from_config_else_dir_name(self):
        self.assertEqual(campaign_slug(pathlib.Path("x/pandodnd"), {"slug": "pando", "name": "PandoDnD"}), "pando")
        self.assertEqual(campaign_slug(pathlib.Path("x/pandodnd"), {}), "pandodnd")


if __name__ == "__main__":
    unittest.main()

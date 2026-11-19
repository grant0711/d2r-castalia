"""
test_char_manager.py
Unit tests for multi-class character creation, respec/stat/level calculation,
waypoint & quest unlocking, level-bracket starter gold, and 100% bit-for-bit
preservation of the template's JM item section.
"""
import os
import struct
import tempfile
import unittest

from tests.fixture import read_mod_tsv  # ensures tools/ is on sys.path
from mod_builder.char_manager import (
    TEMPLATE_DIR,
    calc_d2s_checksum,
    compute_completed_quest_bonuses,
    configure_character_d2s,
    create_character_from_template,
    default_gold_for_level,
    inspect_character_d2s,
    locate_sections,
    tier_template_for_level,
)


class TestCharManager(unittest.TestCase):
    """Verify multi-class character generation, charstats.txt pool math, WPs, quest rewards, and item preservation."""

    def test_level_1_to_9_omits_starter_gold_and_preserves_template_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            info = create_character_from_template(
                "FRESH_ASS",
                "ass",
                level=1,
                wp_target="start",
                save_dir=tmpdir,
            )
            self.assertEqual(info["level"], 1)
            self.assertEqual(info["stash_gold"], 0)
            self.assertEqual(info["inv_gold"], 0)

            with open(info["path"], "rb") as f:
                rebuilt = bytearray(f.read())
            with open(os.path.join(TEMPLATE_DIR, "default.d2s"), "rb") as f:
                tmpl_raw = bytearray(f.read())
            _, _, r_jm = locate_sections(rebuilt)
            _, _, t_jm = locate_sections(tmpl_raw)
            self.assertEqual(rebuilt[r_jm:], tmpl_raw[t_jm:])

    def test_create_level_53_paladin_with_a3nm_waypoints_quests_and_preserve_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_out = os.path.join(tmpdir, "PAL53_starter.zip")
            info = create_character_from_template(
                "PAL_TEST",
                "pal",
                level=53,
                wp_target="a3nm",
                save_dir=tmpdir,
                export_path=zip_out,
            )

            self.assertEqual(info["name"], "PAL_TEST")
            self.assertEqual(info["class_id"], 3)
            self.assertEqual(info["class_name"], "Paladin")
            self.assertEqual(info["level"], 53)
            # Starting at the beginning of Act 3 NM: Normal Acts 1-5 completed + NM Acts 1-2 completed
            self.assertEqual(info["stat_pts"], 52 * 5 + 5)    # 260 + 5 (Normal Lam Esen) = 265
            self.assertEqual(info["skill_pts"], 52 * 2 + 6)   # 104 + 6 (N A1/A2/A4 + NM A1/A2) = 110
            self.assertEqual(info["life"], 55 + 52 * 7 + 20)  # 419 base + 20 (Normal Golden Bird) = 439
            self.assertEqual(info["stash_gold"], 825_000)
            # 18 WPs for NM Acts 1..2 + 1 arrival town WP (Kurast Docks bit 18) = 19/39
            self.assertEqual(info["waypoints"], "N:39/39 NM:19/39")
            self.assertTrue(os.path.exists(zip_out))

            d2s_path = info["path"]
            with open(d2s_path, "rb") as f:
                rebuilt = bytearray(f.read())
            with open(os.path.join(TEMPLATE_DIR, "tier4_flawless.d2s"), "rb") as f:
                tmpl_raw = bytearray(f.read())

            self.assertEqual(info["template_used"], "tier4_flawless.d2s")
            # Verify D2R v105 progression byte at offset 21 (7 = NM Act 2 completed) and active town byte at offset 153 (0x82 = NM Act 3 Kurast Docks)
            self.assertEqual(rebuilt[21], 7)
            self.assertEqual(rebuilt[152:155], b"\x00\x82\x00")

            _, _, r_jm = locate_sections(rebuilt)
            _, _, t_jm = locate_sections(tmpl_raw)
            self.assertEqual(
                rebuilt[r_jm:],
                tmpl_raw[t_jm:],
                "JM item section must be preserved 100% bit-for-bit from the starter template",
            )
            self.assertEqual(compute_completed_quest_bonuses(rebuilt), (6, 5, 20))
            stored_csum = struct.unpack_from("<I", rebuilt, 12)[0]
            self.assertEqual(stored_csum, calc_d2s_checksum(rebuilt))

    def test_five_gem_skull_tier_templates_resolve_and_preserve_items(self):
        expected_tiers = [
            (1, "default.d2s"),
            (12, "tier1_chipped.d2s"),
            (20, "tier2_flawed.d2s"),
            (35, "tier3_normal.d2s"),
            (50, "tier4_flawless.d2s"),
            (65, "tier5_perfect.d2s"),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            for lvl, exp_tmpl in expected_tiers:
                self.assertEqual(f"{tier_template_for_level(lvl)}.d2s", exp_tmpl)
                info = create_character_from_template(
                    f"TIER_{lvl}",
                    "sor",
                    level=lvl,
                    wp_target="a1n",
                    save_dir=tmpdir,
                )
                self.assertEqual(info["template_used"], exp_tmpl)
                with open(info["path"], "rb") as f:
                    rebuilt = bytearray(f.read())
                with open(os.path.join(TEMPLATE_DIR, exp_tmpl), "rb") as f:
                    tmpl_raw = bytearray(f.read())
                _, _, r_jm = locate_sections(rebuilt)
                _, _, t_jm = locate_sections(tmpl_raw)
                self.assertEqual(rebuilt[r_jm:], tmpl_raw[t_jm:])

    def test_level_bracket_gold_curve(self):
        expected_gold = {
            5: 0,
            15: 60_000,
            25: 240_000,
            35: 315_000,
            45: 535_000,
            55: 825_000,
            65: 1_240_000,
            75: 1_450_000,
        }
        for lvl, exp_g in expected_gold.items():
            self.assertEqual(default_gold_for_level(lvl), exp_g)

    def test_all_seven_classes_compute_authentic_charstats_pools(self):
        _, cstat_rows = read_mod_tsv("charstats.txt")
        cs_by_name = {r["class"]: r for r in cstat_rows if r.get("class")}

        with tempfile.TemporaryDirectory() as tmpdir:
            for short_cls, full_name in (
                ("ama", "Amazon"),
                ("sor", "Sorceress"),
                ("nec", "Necromancer"),
                ("pal", "Paladin"),
                ("bar", "Barbarian"),
                ("dru", "Druid"),
                ("ass", "Assassin"),
            ):
                lvl = 32
                info = create_character_from_template(
                    f"T_{short_cls.upper()}",
                    short_cls,
                    level=lvl,
                    wp_target="a5n",
                    save_dir=tmpdir,
                )
                cs = cs_by_name[full_name]
                exp_life = int(cs["hpadd"]) + int(cs["vit"]) + (lvl - 1) * (int(cs["LifePerLevel"]) / 4.0) + 20
                exp_mana = int(cs["int"]) + (lvl - 1) * (int(cs["ManaPerLevel"]) / 4.0)
                exp_stam = int(cs["stamina"]) + (lvl - 1) * (int(cs["StaminaPerLevel"]) / 4.0)

                self.assertEqual(info["class_name"], full_name)
                self.assertAlmostEqual(info["life"], exp_life, places=2)
                self.assertAlmostEqual(info["mana"], exp_mana, places=2)
                self.assertAlmostEqual(info["stamina"], exp_stam, places=2)
                self.assertEqual(info["skill_pts"], (lvl - 1) * 2 + 4)
                self.assertEqual(info["stat_pts"], (lvl - 1) * 5 + 5)
                self.assertEqual(info["stash_gold"], 315_000)
                # Starting at beginning of Act 5 Normal: Acts 1-4 completed (30 WPs) + Harrogath town WP (1) = 31/39
                self.assertEqual(info["waypoints"], "N:31/39")

                updated = configure_character_d2s(info["path"], level=60, wp_target="all")
                self.assertEqual(updated["level"], 60)
                self.assertEqual(updated["skill_pts"], 59 * 2 + 12)
                self.assertEqual(updated["stat_pts"], 59 * 5 + 15)
                self.assertEqual(updated["waypoints"], "N:39/39 NM:39/39 H:39/39")
                inspected = inspect_character_d2s(info["path"])
                self.assertEqual(inspected["allocated_skills"], 0)


if __name__ == "__main__":
    unittest.main()

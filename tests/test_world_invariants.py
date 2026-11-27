"""
test_world_invariants.py
Property-based world, drop table, chest, shrine, potion, and gem/rune tier invariants.
"""
import json
import os
import unittest

from tests.fixture import read_mod_tsv, read_vanilla_tsv
from mod_builder.common import MOD_ROOT


class TestWorldInvariants(unittest.TestCase):
    """TreasureClassEx, objects.txt, shrines.txt, objpreset.txt, and misc.txt world contracts."""

    def test_treasure_class_and_world_object_invariants(self):
        _, tc_rows = read_mod_tsv("treasureclassex.txt")
        globally_forbidden_tc_items = {
            "key", "ky0", "ky1", "ky2", "ky3", "tbk", "rvs", "rvl", "cm1", "cm2", "cm3", "cs2",
        }
        monster_forbidden_potions = {
            "hp1", "hp2", "hp3", "hp4", "hp5",
            "mp1", "mp2", "mp3", "mp4", "mp5",
            "vps", "yps", "wms",
            "vp2", "vp3", "yp2", "yp3", "wm2", "wm3",
        }
        for r in tc_rows:
            tc_name = r.get("Treasure Class", "")
            is_chest_tc = "Chest" in tc_name
            is_act_potion_tc = tc_name.endswith(" Potion")
            has_lockbox = False
            for i in range(1, 11):
                it = r.get(f"Item{i}", "").strip()
                self.assertFalse(
                    it in globally_forbidden_tc_items or it == "tsc",
                    f"TreasureClassEx.txt ({tc_name}): globally forbidden item {it!r} in Item{i}",
                )
                if not is_chest_tc and not is_act_potion_tc:
                    self.assertNotIn(
                        it,
                        monster_forbidden_potions,
                        f"TreasureClassEx.txt ({tc_name}): forbidden potion {it!r} in monster TC Item{i}",
                    )
                elif is_chest_tc:
                    self.assertFalse(
                        any(bad in it for bad in ("Equip", "Weap", "Armo", "Melee", "Bow", "Junk")),
                        f"TreasureClassEx.txt ({tc_name}): forbidden equipment/junk {it!r} in Chest Item{i}",
                    )
                    if "Lockbox" in it or "Chest Roll" in it or "Chest Pair" in it:
                        has_lockbox = True
            if is_chest_tc:
                self.assertTrue(has_lockbox, f"TreasureClassEx.txt ({tc_name}): Chest TC missing Lockbox entry")

            tc_items = {r.get(f"Item{i}", "").strip() for i in range(1, 11) if r.get(f"Item{i}", "").strip()}
            if tc_name in ("Act 1 Good", "Act 1 GemRune"):
                self.assertFalse(tc_items & {"Flawed Gem", "Normal Gem", "Flawless Gem", "Perfect Gem"})
            if tc_name in ("Act 2 Good", "Act 2 GemRune", "Act 3 Good", "Act 3 GemRune"):
                self.assertFalse(tc_items & {"Normal Gem", "Flawless Gem", "Perfect Gem"})
            if tc_name in ("Act 4 Good", "Act 4 GemRune", "Act 5 Good", "Act 5 GemRune"):
                self.assertFalse(tc_items & {"Flawless Gem", "Perfect Gem"})
            if tc_name in ("Act 1 (N) Good", "Act 1 (N) GemRune", "Act 2 (N) Good", "Act 2 (N) GemRune"):
                self.assertNotIn("Perfect Gem", tc_items)
            if tc_name in ("Act 3 (N) Good", "Act 3 (N) GemRune"):
                self.assertIn("Perfect Gem", tc_items)
            if tc_name == "Act 3 (N) H2H A":
                self.assertGreaterEqual(int(r.get("level") or "0"), 50)
            if tc_name == "Act 3 (N) Unique A":
                self.assertGreaterEqual(int(r.get("level") or "0"), 53)
            if tc_name in ("Chipped Gem Skel", "Flawed Gem Skel", "Normal Gem Skel", "Flawless Gem Skel", "Perfect Gem Skel"):
                self.assertEqual(r.get("Prob7"), "6")

        _, obj_rows = read_mod_tsv("objects.txt")
        for r in obj_rows:
            self.assertNotEqual(r.get("Lockable"), "1", f"objects.txt ({r.get('Class')}): Lockable=1 found")
            if r.get("OperateFn") == "21":
                self.assertEqual(r.get("Selectable0"), "1")
            if r.get("Class") in ("LargeChestR", "TombChest1", "SewerChestLargeLeft", "ArcaneChest1", "WoodChestL"):
                self.assertEqual((r.get("OperateFn"), r.get("InitFn"), r.get("Damage")), ("4", "3", "100"))
            if r.get("OperateFn") == "22":
                self.assertEqual((r.get("Parm0"), r.get("Parm1")), ("250", "256"))
            if r.get("OperateFn") == "2" and r.get("InitFn") == "1":
                self.assertIn(r.get("Parm0"), ("1", "2"))

        _, shrine_rows = read_mod_tsv("shrines.txt")
        for sr in shrine_rows:
            scode = sr.get("Code", "").strip()
            if not scode or scode == "0":
                continue
            if scode in ("1", "2", "3", "13"):
                self.assertEqual((sr.get("LevelMin"), sr.get("reset time in minutes")), ("1", "1"))
            else:
                self.assertEqual(sr.get("LevelMin"), "120")

        _, preset_rows = read_mod_tsv("objpreset.txt")
        forbidden_preset_chests = {
            "PlaceUniqueChest",
            "ConsolationChest",
            "SpecialChest100",
            "PlaceRandomTreasureChest",
        }
        for pr in preset_rows:
            self.assertNotIn(pr.get("ObjectClass"), forbidden_preset_chests)

    def test_misc_stat_sound_and_consumable_invariants(self):
        _, isc_rows = read_vanilla_tsv("itemstatcost.txt")
        valid_stats = {r["Stat"] for r in isc_rows if r.get("Stat")}
        _, snd_rows = read_vanilla_tsv("sounds.txt")
        valid_sounds = {r["Sound"] for r in snd_rows if r.get("Sound")}
        _, misc_rows = read_mod_tsv("misc.txt")
        misc_by_code = {r.get("code", ""): r for r in misc_rows}

        hd_items_path = os.path.join(MOD_ROOT, "data/hd/items/items.json")
        with open(hd_items_path, "r", encoding="utf-8") as f:
            hd_list = json.load(f)
        hd_map = {k: v for entry in hd_list if isinstance(entry, dict) for k, v in entry.items()}

        for kcode in ("key", "ky0", "ky1", "ky2", "ky3"):
            self.assertIn(kcode, misc_by_code)
            self.assertEqual(misc_by_code[kcode].get("PermStoreItem"), "1")
        for bad_lb in ("zee", "zef", "zeg"):
            self.assertNotIn(bad_lb, misc_by_code)
        for pcode in (
            "hp1", "hp2", "hp3", "hp4", "hp5", "h1a", "h1b", "h1c", "h1d", "h2b", "h2c", "h2d",
            "mp1", "mp2", "mp3", "mp4", "mp5", "m1a", "m1b", "m1c", "m1d", "m2b", "m2c", "m2d",
        ):
            self.assertIn(pcode, misc_by_code)
            self.assertEqual(misc_by_code[pcode].get("PermStoreItem"), "1")
            self.assertIn(pcode, hd_map)
        for ecode in ("wms", "wm2", "wm3", "yps", "yp2", "yp3", "vps", "vp2", "vp3"):
            self.assertEqual(misc_by_code.get(ecode, {}).get("autobelt"), "1")

        vendor_names = (
            "Charsi", "Gheed", "Akara", "Fara", "Lysander", "Drognan",
            "Hratli", "Alkor", "Ormus", "Elzix", "Asheara", "Cain",
            "Halbu", "Malah", "Larzuk", "Anya", "Jamella",
        )
        for tp_code in ("tsc", "tbk"):
            tp_row = misc_by_code.get(tp_code, {})
            for vn in vendor_names:
                self.assertFalse(tp_row.get(f"{vn}Min") or tp_row.get(f"{vn}Max"))

        gem_families = (
            ("gcv", "gfv", "gsv", "gzv", "gpv"),
            ("gcy", "gfy", "gsy", "gly", "gpy"),
            ("gcb", "gfb", "gsb", "glb", "gpb"),
            ("gcg", "gfg", "gsg", "glg", "gpg"),
            ("gcr", "gfr", "gsr", "glr", "gpr"),
            ("gcw", "gfw", "gsw", "glw", "gpw"),
            ("skc", "skf", "sku", "skl", "skz"),
        )
        expected_gem_reqs = ("1", "15", "30", "45", "60")
        for gfam in gem_families:
            for gcode, exp_req in zip(gfam, expected_gem_reqs):
                self.assertEqual(misc_by_code.get(gcode, {}).get("levelreq"), exp_req)

        _, cstat_rows = read_mod_tsv("charstats.txt")
        for cr in cstat_rows:
            for i in range(1, 11):
                self.assertNotEqual(cr.get(f"item{i}", "").strip(), "tsc")

        for r in misc_rows:
            code = r.get("code", "")
            for scol in ("stat1", "stat2", "stat3"):
                sval = r.get(scol, "").strip()
                if sval:
                    self.assertIn(sval, valid_stats, f"misc.txt ({code}): {scol}={sval!r} invalid stat")
            for snd_col in ("dropsound", "usesound"):
                snd_val = r.get(snd_col, "").strip()
                if snd_val:
                    self.assertIn(snd_val, valid_sounds, f"misc.txt ({code}): {snd_col}={snd_val!r} invalid sound")


if __name__ == "__main__":
    unittest.main()

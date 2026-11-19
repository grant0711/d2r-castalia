"""
test_item_invariants.py
Property-based invariants for weapons.txt, armor.txt, automagic.txt staffmods,
magicprefix/magicsuffix levelreq curves, locked unique/set parity, and oskill compatibility.
"""
import os
import unittest
from typing import Dict, Tuple

from tests.fixture import get_indexed_tables, read_mod_tsv, read_vanilla_tsv
from mod_builder.common import MOD_EXCEL


class TestItemInvariants(unittest.TestCase):
    """Equipment, staffmod, affix, and unique/set compatibility contracts."""

    VENDOR_NAMES = (
        "Charsi", "Gheed", "Akara", "Fara", "Lysander", "Drognan",
        "Hratli", "Alkor", "Ormus", "Elzix", "Asheara", "Cain",
        "Halbu", "Malah", "Larzuk", "Anya", "Jamella",
    )

    def test_weapons_armor_and_vendor_progression_invariants(self):
        _, van_weap_rows = read_vanilla_tsv("weapons.txt")
        van_weap_by_code = {r["code"]: r for r in van_weap_rows if r.get("code")}
        _, weap_rows = read_mod_tsv("weapons.txt")
        _, arm_rows = read_mod_tsv("armor.txt")
        _, npc_rows = read_mod_tsv("npc.txt")
        for nr in npc_rows:
            self.assertEqual(nr.get("rep mult"), "768")

        _, mod_isc_rows = read_mod_tsv("itemstatcost.txt")
        isc_by_stat = {r.get("Stat", ""): r for r in mod_isc_rows if r.get("Stat")}
        self.assertEqual(
            (isc_by_stat["item_charged_skill"].get("Multiply"), isc_by_stat["item_charged_skill"].get("Add")),
            ("1", "10"),
        )
        self.assertEqual(
            (isc_by_stat["item_damagetargetac"].get("Save Bits"), isc_by_stat["item_damagetargetac"].get("Save Add")),
            ("10", "512"),
        )
        for zero_st in (
            "armorclass", "mindamage", "maxdamage", "secondary_mindamage",
            "secondary_maxdamage", "item_throw_mindamage", "item_throw_maxdamage", "maxdurability",
        ):
            zr = isc_by_stat[zero_st]
            self.assertEqual((zr.get("Multiply"), zr.get("Add")), ("0", "0"))

        ranged_only_types = {"bow", "abow", "xbow", "tpot"}
        expected_weap_ap = {
            "staf": "310", "wand": "311", "scep": "312", "orb": "303",
            "h2h": "315", "h2h2": "315", "aspe": "302", "ajav": "308",
        }
        for r in weap_rows:
            code = r.get("code", "")
            wtype = r.get("type", "")
            if not code or not wtype or code == "um1":
                continue
            if wtype != "tpot":
                for vn in self.VENDOR_NAMES:
                    self.assertFalse(r.get(f"{vn}Min") or r.get(f"{vn}Max"))
            if r.get("spawnable") != "1" or wtype == "tpot" or code in ("bml", "um1"):
                continue
            vw = van_weap_by_code.get(code)
            if vw and r.get("nodurability") != "1" and int(vw.get("durability") or "0") > 0:
                exp_dur = min(255, int(vw["durability"]) * 2)
                self.assertEqual(int(r.get("durability") or "0"), exp_dur)
            self.assertTrue(2 <= int(r.get("cost") or "0") <= 50000)

            if code == r.get("normcode"):
                exp_nm = r.get("ubercode") if r.get("ubercode") != code else "xxx"
                exp_hell = r.get("ultracode") if r.get("ultracode") != code else "xxx"
                self.assertEqual((r.get("NightmareUpgrade"), r.get("HellUpgrade")), (exp_nm, exp_hell))
                stocked_vendors = [vn for vn in self.VENDOR_NAMES if int(r.get(f"{vn}MagicMax") or "0") >= 1]
                self.assertEqual(len(stocked_vendors), 1)
                self.assertEqual(r.get(f"{stocked_vendors[0]}MagicLvl"), "1")
            else:
                for vn in self.VENDOR_NAMES:
                    self.assertFalse(r.get(f"{vn}MagicMin") or r.get(f"{vn}MagicMax"))

            if wtype not in ranged_only_types:
                self.assertGreaterEqual(int(r.get("rangeadder") or "0"), 1)
            if wtype in ("jave", "ajav"):
                expected_min = 3 if code in ("glv", "9gl", "7gl", "tsp", "9ts", "7ts") else 2
                self.assertGreaterEqual(int(r.get("rangeadder") or "0"), expected_min)
            if wtype in ("jave", "ajav", "tkni", "taxe"):
                self.assertEqual((r.get("nodurability"), r.get("hasinv")), ("1", "1"))
            for dcol in ("mindam", "maxdam", "2handmindam", "2handmaxdam", "minmisdam", "maxmisdam"):
                dval = r.get(dcol, "")
                if dval:
                    self.assertLessEqual(int(dval), 255, f"weapons.txt ({code}): {dcol}={dval} overflows uint8_t (255)")
            if wtype in expected_weap_ap:
                self.assertEqual(r.get("auto prefix"), expected_weap_ap[wtype])

        expected_arm_ap = {"phlm": "313", "pelt": "314", "head": "305"}
        for r in arm_rows:
            code = r.get("code", "")
            if not code:
                continue
            for vn in self.VENDOR_NAMES:
                self.assertFalse(r.get(f"{vn}Min") or r.get(f"{vn}Max"))
            if r.get("spawnable") != "1":
                continue
            atype = r.get("type", "")
            if atype in expected_arm_ap:
                self.assertEqual(r.get("auto prefix"), expected_arm_ap[atype])
            self.assertTrue(50 <= int(r.get("cost") or "0") <= 50000)

    def test_automagic_staffmod_brackets_match_skill_reqlevel_gates(self):
        _, auto_rows = read_mod_tsv("automagic.txt")
        _, sk_rows = read_mod_tsv("skills.txt")
        sk_req_by_id = {
            int(r["*Id"]): (r.get("charclass", ""), int(r.get("reqlevel") or "0"), r["skill"])
            for r in sk_rows
            if r.get("*Id")
        }
        grp_to_cls = {
            "303": "sor", "305": "nec", "310": "sor", "311": "nec",
            "312": "pal", "313": "bar", "314": "dru", "315": "ass",
        }
        bracket_to_reqcap = {
            ("1", "7"): 1, ("8", "13"): 8, ("14", "20"): 16,
            ("21", "28"): 24, ("29", "36"): 32, ("37", ""): 40,
        }
        seen_by_grp_bracket = {(g, b): set() for g in grp_to_cls for b in bracket_to_reqcap}

        for r in auto_rows:
            grp = r.get("group", "")
            if grp not in grp_to_cls:
                continue
            cls_code = grp_to_cls[grp]
            bkey = (r.get("level", ""), r.get("maxlevel", ""))
            self.assertIn(bkey, bracket_to_reqcap)
            req_cap = bracket_to_reqcap[bkey]
            row_ranges = []
            for idx in (1, 2, 3):
                if r.get(f"mod{idx}code") == "skill-rand":
                    lo = int(r[f"mod{idx}min"])
                    hi = int(r[f"mod{idx}max"])
                    self.assertLessEqual(lo, hi)
                    for prev_lo, prev_hi in row_ranges:
                        self.assertTrue(hi < prev_lo or lo > prev_hi)
                    row_ranges.append((lo, hi))
                    for sid in range(lo, hi + 1):
                        s_cls, s_req, s_name = sk_req_by_id.get(sid, ("", 999, "?"))
                        self.assertEqual(s_cls, cls_code)
                        self.assertLessEqual(s_req, req_cap, f"Leaked skill {sid} ({s_name})")
                        seen_by_grp_bracket[(grp, bkey)].add(sid)

        for (grp, bkey), seen_ids in seen_by_grp_bracket.items():
            cls_code = grp_to_cls[grp]
            req_cap = bracket_to_reqcap[bkey]
            expected_ids = {sid for sid, (c, rq, _) in sk_req_by_id.items() if c == cls_code and rq <= req_cap}
            self.assertEqual(seen_ids, expected_ids)

    def test_affixes_and_locked_unique_set_oskill_compatibility(self):
        forbidden_skill_refs = {
            "37", "40", "43", "46", "50", "52", "54", "58", "60", "61", "63", "65", "91",
            "Warmth", "Frozen Armor", "Telekinesis", "Blaze", "Shiver Armor",
            "Enchant", "Teleport", "Energy Shield", "Chilling Armor",
            "Fire Mastery", "Lightning Mastery", "Cold Mastery", "Lower Resist",
        }
        forbidden_pierce_props = {"pierce-fire", "pierce-cold", "pierce-ltng", "pierce-pois", "pierce-mag"}

        for afx_fn in ("magicprefix.txt", "magicsuffix.txt"):
            _, afx_rows = read_mod_tsv(afx_fn)
            for r in afx_rows:
                if r.get("spawnable") != "1":
                    continue
                if "jewl" in {r.get(f"itype{i}", "").strip() for i in range(1, 8)}:
                    self.assertGreaterEqual(int(r.get("level") or "1"), 2)
                m1c = r.get("mod1code", "").strip()
                m1p = r.get("mod1param", "").strip()
                self.assertNotIn(m1c, forbidden_pierce_props | {"pierce-dmg"})
                if m1c in ("charged", "oskill", "skill", "att-skill", "hit-skill", "gethit-skill"):
                    self.assertNotIn(m1p, forbidden_skill_refs)
                if r.get("version") != "0":
                    alvl = int(r.get("level") or "1")
                    lreq = int(r.get("levelreq") or "0")
                    if r.get("rare") == "1":
                        if alvl <= 22:
                            self.assertEqual(lreq, 0)
                        elif alvl <= 29:
                            self.assertLessEqual(lreq, 3)
                        elif alvl <= 44:
                            self.assertLessEqual(lreq, 14)
                        elif alvl <= 59:
                            self.assertLessEqual(lreq, 26)
                        else:
                            self.assertLessEqual(lreq, 46)
                    else:
                        self.assertLessEqual(lreq, max(1, min(62, alvl - 15)))

        # Verify locked unique/set table parity & oskill compatibility
        locked_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "tools", "mod_builder", "locked_tables")
        )
        for lfn in ("uniqueitems.txt", "setitems.txt", "sets.txt"):
            lpath = os.path.join(locked_dir, lfn)
            mpath = os.path.join(MOD_EXCEL, lfn)
            self.assertTrue(os.path.exists(lpath), f"locked_tables/{lfn} is missing")
            with open(lpath, "rb") as f1, open(mpath, "rb") as f2:
                self.assertEqual(f1.read(), f2.read(), f"MOD_EXCEL/{lfn} diverges from locked_tables/{lfn}")

        idx = get_indexed_tables()
        skill_by_name = idx["skills_by_lower"]
        skill_by_id = idx["skills_by_id"]
        _, weap_rows = read_mod_tsv("weapons.txt")
        _, arm_rows = read_mod_tsv("armor.txt")
        _, it_rows = read_mod_tsv("itemtypes.txt")
        weap_type_by_code = {r["code"]: r.get("type", "") for r in weap_rows if r.get("code")}
        arm_type_by_code = {r["code"]: r.get("type", "") for r in arm_rows if r.get("code")}
        it_by_code = {r["Code"]: r for r in it_rows if r.get("Code")}

        def _type_ancestors(tcode: str) -> set:
            visited = set()
            stack = [tcode]
            while stack:
                cur = stack.pop()
                if not cur or cur in visited:
                    continue
                visited.add(cur)
                row = it_by_code.get(cur)
                if row:
                    for col in ("Equiv1", "Equiv2"):
                        eq = row.get(col, "").strip()
                        if eq:
                            stack.append(eq)
            return visited

        def _validate_oskill(table_label: str, item_code: str, sk_ref: str, item_oskills: set):
            srow = skill_by_name.get(sk_ref.lower()) or skill_by_id.get(sk_ref)
            self.assertIsNotNone(srow, f"{table_label}: invalid oskill {sk_ref!r}")
            self.assertNotEqual(srow.get("aura"), "1", f"{table_label}: oskill {sk_ref!r} is a Paladin aura")
            st1 = srow.get("State1", "").strip()
            if st1 and srow.get("restrict", "").strip() == "2":
                has_wolf = bool({"Wearwolf", "Werewolf", "223"} & item_oskills)
                has_bear = bool({"Wearbear", "Werebear", "228"} & item_oskills)
                self.assertTrue((st1 == "wolf" and has_wolf) or (st1 == "bear" and has_bear))
            self.assertNotIn(sk_ref, ("54", "Teleport", "380", "Blood Boil"))
            if item_code in weap_type_by_code:
                wtype = weap_type_by_code[item_code]
                anc = _type_ancestors(wtype)
                req_itypes = [srow.get(f"itypea{k}", "").strip() for k in (1, 2, 3) if srow.get(f"itypea{k}", "").strip()]
                if req_itypes:
                    self.assertTrue(any(rt in anc for rt in req_itypes), f"{table_label}: weapon {item_code} incompatible with {sk_ref}")

        _, van_u_rows = read_vanilla_tsv("uniqueitems.txt")
        van_u_by_idx = {r["index"]: r for r in van_u_rows if r.get("index")}
        _, mod_u_rows = read_mod_tsv("uniqueitems.txt")
        seen_added_oskills: Dict[str, str] = {}
        seen_added_auras_by_slot: Dict[Tuple[str, str], str] = {}

        for r in mod_u_rows:
            if r.get("spawnable") != "1" or r.get("disabled") == "1":
                continue
            u_idx = r.get("index", "")
            code = r.get("code", "")
            sb = "weapon" if code in weap_type_by_code else arm_type_by_code.get(code, code)
            van_r = van_u_by_idx.get(u_idx)
            van_props = {van_r.get(f"prop{i}", "").strip() for i in range(1, 13)} if van_r else set()
            item_oskills = {r.get(f"par{i}", "").strip() for i in range(1, 13) if r.get(f"prop{i}", "").strip() == "oskill"}
            for i in range(1, 13):
                p = r.get(f"prop{i}", "").strip()
                par = r.get(f"par{i}", "").strip()
                self.assertNotEqual(p, "nofreeze")
                self.assertNotIn(p, forbidden_pierce_props)
                if p in ("charged", "oskill", "skill", "gethit-skill", "hit-skill", "att-skill", "levelup-skill", "kill-skill", "death-skill"):
                    self.assertNotIn(par, ("54", "Teleport"))
                    if p in ("charged", "oskill", "gethit-skill", "hit-skill", "att-skill", "levelup-skill"):
                        self.assertNotIn(par, forbidden_skill_refs)
                if p == "oskill":
                    _validate_oskill(f"uniqueitems.txt ({u_idx})", code, par, item_oskills)
                    if "oskill" not in van_props:
                        self.assertNotIn(par, seen_added_oskills)
                        seen_added_oskills[par] = u_idx
                elif p == "aura" and "aura" not in van_props:
                    arow = skill_by_id.get(par) or skill_by_name.get(par.lower())
                    self.assertIsNotNone(arow)
                    self.assertEqual(arow.get("aura"), "1")
                    self.assertNotIn((sb, par), seen_added_auras_by_slot)
                    seen_added_auras_by_slot[(sb, par)] = u_idx


if __name__ == "__main__":
    unittest.main()

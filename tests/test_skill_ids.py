"""
test_skill_ids.py
Save-format & skill-id invariants guarding the "items vanish on Save & Exit" class of bugs.

1. automagic.txt must stay below the 11-bit (2048) automagic id that .d2s saves store per item; every row of every
   group referenced by an item's `auto prefix` must have a row index < 2048.
2. Every class's 30 skills must occupy tier-contiguous id blocks in skills.txt (tier 1 lowest ids ... tier 6 highest),
   so each "tiers 1..k" staffmod pool is a single skill-rand interval.
3. Every automagic skill-rand range must cover only skills of its class within the bracket's unlocked tiers.
4. The skill-id permutation is applied consistently: row names travel with their content, numeric skill params in
   item tables and HD state machine skillIndex bindings follow the moved rows.
"""
import glob
import json
import os
import unittest

from tests.fixture import read_mod_tsv, read_vanilla_tsv
from mod_builder import skill_order
from mod_builder.common import MOD_ROOT, VANILLA_ROOT

CLASS_RANGES = {
    "sor": (36, 65), "nec": (66, 95), "pal": (96, 125), "bar": (126, 155),
    "dru": (221, 250), "ass": (251, 280),
}
TIERS = [1, 8, 16, 24, 32, 40]


class TestSkillIds(unittest.TestCase):
    def test_automagic_rows_fit_d2s_save_format(self):
        _, auto_rows = read_mod_tsv("automagic.txt")
        self.assertLess(len(auto_rows), 2048, "automagic.txt rows >= 2048 cannot be saved (items get deleted)")
        self.assertLessEqual(len(auto_rows), 2000, "automagic.txt is within 48 rows of the 2048 save limit")
        last_idx = {}
        for idx, r in enumerate(auto_rows):
            last_idx[r.get("group", "")] = idx
        for table in ("armor.txt", "weapons.txt", "misc.txt"):
            _, rows = read_mod_tsv(table)
            for r in rows:
                grp = r.get("auto prefix", "")
                if grp:
                    self.assertIn(grp, last_idx, f"{table} {r.get('name')}: auto prefix group {grp} has no rows")
                    self.assertLess(last_idx[grp], 2048,
                                    f"{table} {r.get('name')}: auto prefix group {grp} reaches row {last_idx[grp]}")

    def test_class_skill_tiers_are_contiguous_id_blocks(self):
        _, sk_rows = read_mod_tsv("skills.txt")
        for idx, r in enumerate(sk_rows):
            self.assertEqual(r.get("*Id"), str(idx), f"skills.txt row {idx} ({r.get('skill')}) has *Id {r.get('*Id')}")
        for cls, (lo, hi) in CLASS_RANGES.items():
            rows = sk_rows[lo:hi + 1]
            self.assertTrue(all(r.get("charclass") == cls for r in rows), f"{cls}: ids {lo}..{hi} not all {cls}")
            if cls == "sor":
                # Sorceress is ordered by (Tree, Tier): 36..45 Fire, 46..55 Lightning, 56..65 Cold
                for tree_idx in range(3):
                    sub = rows[tree_idx * 10:(tree_idx + 1) * 10]
                    levels = [int(r["reqlevel"]) for r in sub]
                    self.assertEqual(levels, sorted(levels), f"sor tree {tree_idx}: reqlevels not tier-ordered: {levels}")
                    self.assertEqual(sorted(set(levels)), TIERS, f"sor tree {tree_idx}: unexpected tiers {sorted(set(levels))}")
            else:
                levels = [int(r["reqlevel"]) for r in rows]
                self.assertEqual(levels, sorted(levels), f"{cls}: reqlevels not tier-ordered by id: {levels}")
                self.assertEqual(sorted(set(levels)), TIERS, f"{cls}: unexpected tier levels {sorted(set(levels))}")

    def test_staffmod_ranges_stay_inside_class_and_unlocked_tiers(self):
        _, auto_rows = read_mod_tsv("automagic.txt")
        _, sk_rows = read_mod_tsv("skills.txt")
        by_id = {int(r["*Id"]): r for r in sk_rows}
        bracket_cap = {
            ("1", "7"): 1, ("8", "13"): 8, ("14", "20"): 16,
            ("21", "28"): 24, ("29", "36"): 32, ("32", "36"): 32, ("37", ""): 40,
        }
        for r in auto_rows:
            ranges = [(int(r[f"mod{i}min"]), int(r[f"mod{i}max"])) for i in (1, 2, 3) if r.get(f"mod{i}code") == "skill-rand"]
            if not ranges:
                continue
            cap = bracket_cap[(r.get("level", ""), r.get("maxlevel", ""))]
            classes = set()
            seen = set()
            for lo, hi in ranges:
                ids = set(range(lo, hi + 1))
                self.assertFalse(ids & seen, f"automagic group {r['group']}: overlapping skill-rand ranges {ranges}")
                seen |= ids
                for sid in ids:
                    classes.add(by_id[sid]["charclass"])
                    self.assertLessEqual(int(by_id[sid]["reqlevel"]), cap,
                                         f"group {r['group']} bracket {cap}: {by_id[sid]['skill']} leaks a locked tier")
            self.assertEqual(len(classes), 1, f"automagic group {r['group']}: ranges span classes {classes}")

    def test_permutation_keeps_names_and_references_attached(self):
        perm = skill_order.permutation()
        _, sk_rows = read_mod_tsv("skills.txt")
        _, van_rows = read_vanilla_tsv("skills.txt")
        for old, new in perm.items():
            self.assertEqual(sk_rows[new]["skill"], van_rows[old]["skill"],
                             f"skill row {van_rows[old]['skill']!r} (source id {old}) should now be id {new}")
        # Numeric skill params in item tables point at the same NAMED row as in vanilla.
        skill_props = skill_order._skill_param_props()
        for table, code_fmt, par_fmt, n in (("uniqueitems.txt", "prop{}", "par{}", 12), ("setitems.txt", "prop{}", "par{}", 9)):
            _, mod_rows = read_mod_tsv(table)
            _, vrows = read_vanilla_tsv(table)
            van = {r.get("index"): r for r in vrows}
            for r in mod_rows:
                v = van.get(r.get("index"))
                if not v:
                    continue
                for i in range(1, n + 1):
                    c, p = code_fmt.format(i), par_fmt.format(i)
                    if (r.get(c) in skill_props and r.get(c) == v.get(c) and v.get(p, "").isdigit()
                            and int(v[p]) in perm and r.get(p, "").isdigit()):
                        # Builders may deliberately substitute a skill; the bug to catch is a value left in the
                        # source id space (identical to vanilla although that skill moved).
                        if perm[int(v[p])] != int(v[p]):
                            self.assertNotEqual(r.get(p), v[p],
                                                f"{table} {r['index']} {p}: {v[p]} was not remapped to {perm[int(v[p])]}")

    def test_state_machines_follow_moved_skills(self):
        moved = {k: v for k, v in skill_order.permutation().items() if k != v}
        for van_path in glob.glob(os.path.join(VANILLA_ROOT, "data/hd/character/player/*/*state_machine*.json")):
            rel = os.path.relpath(van_path, VANILLA_ROOT)
            with open(van_path, encoding="utf-8-sig") as f:
                van = json.load(f)
            if not any(s.get("skillIndex") in moved for s in van.get("states", [])):
                continue
            mod_path = os.path.join(MOD_ROOT, rel)
            self.assertTrue(os.path.exists(mod_path), f"{rel} references moved skills but has no remapped mod copy")
            with open(mod_path, encoding="utf-8") as f:
                mod = json.load(f)
            mod_keys = {(s.get("modeId"), s.get("skillIndex"), s.get("stepIndex")) for s in mod.get("states", [])}
            for s in van.get("states", []):
                si = s.get("skillIndex")
                if si in moved:
                    self.assertIn((s.get("modeId"), moved[si], s.get("stepIndex")), mod_keys,
                                  f"{rel}: state for skill {si} must move to {moved[si]}")


    def test_sorc_staff_and_orb_automagic_coherence_and_affix_exclusions(self):
        _, auto_rows = read_mod_tsv("automagic.txt")
        tree_blocks = {"extra-fire": (36, 45), "extra-ltng": (46, 55), "extra-cold": (56, 65)}
        for r in auto_rows:
            grp = r.get("group", "")
            if grp not in ("303", "310"):
                continue
            ranges = [(int(r[f"mod{i}min"]), int(r[f"mod{i}max"])) for i in (1, 2, 3) if r.get(f"mod{i}code") == "skill-rand"]
            self.assertTrue(ranges, f"group {grp} row missing skill-rand")
            # All skill-rand ranges on a Staff (310) or Orb (303) row must lie inside ONE Sorc tree block
            trees_hit = set()
            for lo, hi in ranges:
                for sid in range(lo, hi + 1):
                    trees_hit.add((sid - 36) // 10)
            self.assertEqual(len(trees_hit), 1, f"group {grp} spans multiple Sorc trees: {ranges}")
            # If elemental skill damage is present, must unlock >= 32, cap <= 20%, and match the tree!
            m1 = r.get("mod1code", "")
            if m1 in tree_blocks:
                self.assertGreaterEqual(int(r.get("level", "0")), 32, f"elem dmg automagic unlocked below lvl 32: {r}")
                self.assertLessEqual(int(r.get("mod1max", "0")), 20, f"elem dmg automagic exceeds 20% cap: {r}")
                tlo, thi = tree_blocks[m1]
                for lo, hi in ranges:
                    self.assertTrue(tlo <= lo <= hi <= thi, f"{m1} row has mismatched skill-rand {(lo, hi)}")

        # Verify blocked melee affixes (dmg-demon/undead, IAS, OW, DS, CB) cannot spawn on staf or orb
        _, it_rows = read_mod_tsv("itemtypes.txt")
        parents = {r["Code"]: [p for p in (r.get("Equiv1", ""), r.get("Equiv2", "")) if p] for r in it_rows if r.get("Code")}
        def anc(code):
            s, st = {code}, [code]
            while st:
                c = st.pop()
                for p in parents.get(c, []):
                    if p not in s:
                        s.add(p); st.append(p)
            return s
        staf_a, orb_a = anc("staf"), anc("orb")
        for fname, blocked_grps in (("magicprefix.txt", {"123", "142"}), ("magicsuffix.txt", {"7", "61", "62", "63"})):
            _, arows = read_mod_tsv(fname)
            for r in arows:
                if r.get("spawnable") != "1" or r.get("version") == "0" or r.get("group") not in blocked_grps:
                    continue
                its = {r.get(f"itype{i}", "").strip() for i in range(1, 8) if r.get(f"itype{i}", "").strip()}
                ets = {r.get(f"etype{i}", "").strip() for i in range(1, 6) if r.get(f"etype{i}", "").strip()}
                self.assertFalse(bool(its & staf_a) and not bool(ets & staf_a), f"{fname} {r['Name']} (grp {r['group']}) still spawns on staf")
                self.assertFalse(bool(its & orb_a) and not bool(ets & orb_a), f"{fname} {r['Name']} (grp {r['group']}) still spawns on orb")


if __name__ == "__main__":
    unittest.main()

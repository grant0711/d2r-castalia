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
        for fname in ("automagic.txt", "magicprefix.txt", "magicsuffix.txt"):
            _, trows = read_mod_tsv(fname)
            self.assertLess(len(trows), 2048, f"{fname} rows >= 2048 cannot be saved in .d2s (11-bit limit)")
            self.assertLessEqual(len(trows), 2000, f"{fname} ({len(trows)} rows) is within 48 rows of the 2048 save limit")
        _, auto_rows = read_mod_tsv("automagic.txt")
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
        for r in auto_rows:
            grp = r.get("group", "")
            if grp not in ("303", "310"):
                continue
            mods = [r.get(f"mod{i}code", "") for i in (1, 2, 3) if r.get(f"mod{i}code", "")]
            self.assertTrue(mods, f"group {grp} row has no mods")
            # Staves (310) and Orbs (303) automagic must be pure 'skill-rand' ONLY (no hp/mana/cast1/extra-* noise)
            self.assertTrue(
                all(m == "skill-rand" for m in mods),
                f"group {grp} must only contain skill-rand automagic, got {mods}",
            )
            ranges = [(int(r[f"mod{i}min"]), int(r[f"mod{i}max"])) for i in (1, 2, 3) if r.get(f"mod{i}code") == "skill-rand"]
            # All skill-rand ranges on a Staff (310) or Orb (303) row must lie inside ONE Sorc tree block
            trees_hit = set()
            for lo, hi in ranges:
                for sid in range(lo, hi + 1):
                    trees_hit.add((sid - 36) // 10)
            self.assertEqual(len(trees_hit), 1, f"group {grp} spans multiple Sorc trees: {ranges}")

        # Verify blocked melee affixes cannot spawn on staf, orb, or wand
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
        staf_a, orb_a, wand_a = anc("staf"), anc("orb"), anc("wand")
        for fname, blocked_grps in (
            ("magicprefix.txt", {"123", "137", "138", "139", "140", "142", "145"}),
            ("magicsuffix.txt", {"4", "7", "10", "12", "13", "16", "24", "25", "27", "28", "60", "61", "62", "63", "64"}),
        ):
            _, arows = read_mod_tsv(fname)
            for r in arows:
                if r.get("spawnable") != "1" or r.get("version") == "0" or r.get("group") not in blocked_grps:
                    continue
                its = {r.get(f"itype{i}", "").strip() for i in range(1, 8) if r.get(f"itype{i}", "").strip()}
                ets = {r.get(f"etype{i}", "").strip() for i in range(1, 6) if r.get(f"etype{i}", "").strip()}
                self.assertFalse(bool(its & staf_a) and not bool(ets & staf_a), f"{fname} {r['Name']} (grp {r['group']}) still spawns on staf")
                self.assertFalse(bool(its & orb_a) and not bool(ets & orb_a), f"{fname} {r['Name']} (grp {r['group']}) still spawns on orb")
                self.assertFalse(bool(its & wand_a) and not bool(ets & wand_a), f"{fname} {r['Name']} (grp {r['group']}) still spawns on wand")

        # Verify Staff-only +% Elemental Skill Damage prefixes (grp 147) spawn on staf and NOT on orb
        _, mp_rows = read_mod_tsv("magicprefix.txt")
        elem_staf = [r for r in mp_rows if r.get("group") == "147" and r.get("spawnable") == "1"]
        self.assertEqual(len(elem_staf), 6, "Expected 6 Staff-only +% Elemental Skill Damage prefix rows (grp 147)")
        for r in elem_staf:
            self.assertEqual(r.get("itype1"), "staf")
            self.assertGreaterEqual(int(r.get("level") or "0"), 32)
            self.assertLessEqual(int(r.get("mod1max") or "0"), 25)

        # Verify no att-skill / hit-skill melee procs spawn on staf, orb, or wand
        _, ms_rows = read_mod_tsv("magicsuffix.txt")
        for r in ms_rows:
            if r.get("spawnable") != "1" or r.get("version") == "0":
                continue
            if r.get("mod1code") not in ("att-skill", "hit-skill"):
                continue
            its = {r.get(f"itype{i}", "").strip() for i in range(1, 8) if r.get(f"itype{i}", "").strip()}
            ets = {r.get(f"etype{i}", "").strip() for i in range(1, 6) if r.get(f"etype{i}", "").strip()}
            self.assertFalse(bool(its & staf_a) and not bool(ets & staf_a), f"{r['Name']} ({r['mod1code']}) still spawns on staf")
            self.assertFalse(bool(its & orb_a) and not bool(ets & orb_a), f"{r['Name']} ({r['mod1code']}) still spawns on orb")
            self.assertFalse(bool(its & wand_a) and not bool(ets & wand_a), f"{r['Name']} ({r['mod1code']}) still spawns on wand")

        # Verify Staff-only +Life (grp 26) and FHR (grp 18) suffixes spawn on staf and NOT on orb/wand
        for s_grp, label in (("26", "+Life"), ("18", "FHR")):
            staf_hits = [
                r for r in ms_rows
                if r.get("spawnable") == "1" and r.get("version") != "0" and r.get("group") == s_grp
                and ({r.get(f"itype{i}", "").strip() for i in range(1, 8)} & staf_a)
                and not ({r.get(f"etype{i}", "").strip() for i in range(1, 6)} & staf_a)
            ]
            orb_hits = [
                r for r in ms_rows
                if r.get("spawnable") == "1" and r.get("version") != "0" and r.get("group") == s_grp
                and ({r.get(f"itype{i}", "").strip() for i in range(1, 8)} & orb_a)
                and not ({r.get(f"etype{i}", "").strip() for i in range(1, 6)} & orb_a)
            ]
            self.assertGreaterEqual(len(staf_hits), 3, f"Expected {label} (grp {s_grp}) suffix rows on staf")
            self.assertEqual(len(orb_hits), 0, f"{label} (grp {s_grp}) should not spawn on orb")

    def test_weapon_and_armor_archetype_affix_invariants(self):
        _, it_rows = read_mod_tsv("itemtypes.txt")
        _, mp_rows = read_mod_tsv("magicprefix.txt")
        _, ms_rows = read_mod_tsv("magicsuffix.txt")
        parents = {r["Code"]: [p for p in (r.get("Equiv1", ""), r.get("Equiv2", "")) if p] for r in it_rows if r.get("Code")}
        def anc(code):
            s, st = {code}, [code]
            while st:
                c = st.pop()
                for p in parents.get(c, []):
                    if p not in s:
                        s.add(p); st.append(p)
            return s

        # 1. Tactical suffix groups 60..64 must be absent from magicsuffix.txt
        tactical_rows = [r for r in ms_rows if r.get("spawnable") == "1" and r.get("group") in {"60", "61", "62", "63", "64"}]
        self.assertEqual(tactical_rows, [], "Tactical suffix groups 60..64 must not exist in magicsuffix.txt")

        def grp_weight(rows, types, grp, alvl=75):
            a = set()
            for t in types:
                a |= anc(t)
            w = 0
            for r in rows:
                if r.get("spawnable") != "1" or r.get("version") == "0" or r.get("rare") != "1" or r.get("group") != grp:
                    continue
                if not (int(r.get("level") or 0) <= alvl <= int(r.get("maxlevel") or 999)):
                    continue
                its = {r.get(f"itype{i}", "").strip() for i in range(1, 8) if r.get(f"itype{i}", "").strip()}
                ets = {r.get(f"etype{i}", "").strip() for i in range(1, 6) if r.get(f"etype{i}", "").strip()}
                if (its & a) and not (ets & a):
                    w += int(r.get("frequency") or 0)
            return w

        # 2. Hell alvl=75 Rare single-resists restored on Belt/Armor/Boots & IAS restored on Bow
        for slot in (["belt"], ["tors", "ltor"], ["boot", "lbot"]):
            self.assertGreater(grp_weight(mp_rows, slot, "117"), 0, f"Single-res missing at alvl=75 on {slot}")
        self.assertGreater(grp_weight(ms_rows, ["bow"], "7"), 0, "Bow IAS missing at alvl=75")

        # 3. Archetype probability ordering checks
        self.assertGreater(grp_weight(mp_rows, ["hamm"], "105"), grp_weight(mp_rows, ["knif"], "105"))
        self.assertGreater(grp_weight(mp_rows, ["hamm"], "142"), grp_weight(mp_rows, ["swor"], "142"))
        self.assertLess(grp_weight(ms_rows, ["hamm"], "7"), grp_weight(ms_rows, ["swor"], "7"))
        self.assertEqual(grp_weight(ms_rows, ["wand"], "27"), 0)
        self.assertEqual(grp_weight(ms_rows, ["wand"], "28"), 0)
        self.assertEqual(grp_weight(ms_rows, ["bowq"], "24"), 0)
        self.assertEqual(grp_weight(ms_rows, ["xboq"], "24"), 0)
        self.assertGreater(grp_weight(ms_rows, ["glov", "lglv"], "9"), 0)
        self.assertEqual(grp_weight(ms_rows, ["glov", "hglv"], "9"), 0)
        self.assertGreater(grp_weight(mp_rows, ["tors", "htor"], "101"), grp_weight(mp_rows, ["tors", "ltor"], "101"))
        self.assertGreater(grp_weight(mp_rows, ["shie", "hshi"], "101"), grp_weight(mp_rows, ["shie", "lshi"], "101"))
        self.assertGreater(grp_weight(mp_rows, ["ashd", "hash"], "101"), grp_weight(mp_rows, ["ashd", "lash"], "101"))
        self.assertGreater(grp_weight(ms_rows, ["boot", "lbot"], "35"), grp_weight(ms_rows, ["boot", "hbot"], "35"))
        # Caster Body Armor ('ctor': Light/Mage/Archon Plate) rolls FCR, MAEK, All Res, and excludes Thorns/Str
        self.assertGreater(grp_weight(ms_rows, ["tors", "ctor"], "9"), 0)
        self.assertEqual(grp_weight(ms_rows, ["tors", "ltor"], "9"), 0)
        self.assertGreater(grp_weight(mp_rows, ["tors", "ctor"], "116"), 0)
        self.assertGreater(grp_weight(mp_rows, ["tors", "ctor"], "121"), 0)
        self.assertEqual(grp_weight(ms_rows, ["tors", "ctor"], "6"), 0)

    def test_affix_pool_diversity_no_single_group_monopoly(self):
        """Across all 38 weapon/armor families and alvls (12, 30, 50, 75), no single affix group may monopolize a Rare pool."""
        from collections import defaultdict
        _, it_rows = read_mod_tsv("itemtypes.txt")
        _, mp_rows = read_mod_tsv("magicprefix.txt")
        _, ms_rows = read_mod_tsv("magicsuffix.txt")
        parents = {r["Code"]: [p for p in (r.get("Equiv1", ""), r.get("Equiv2", "")) if p] for r in it_rows if r.get("Code")}
        def anc(code):
            s, st = {code}, [code]
            while st:
                c = st.pop()
                for p in parents.get(c, []):
                    if p not in s:
                        s.add(p); st.append(p)
            return s

        slots = [
            ("Sword", ["swor"]), ("Axe", ["axe"]), ("Hammer", ["hamm"]), ("Mace", ["mace"]),
            ("Dagger", ["knif"]), ("Polearm", ["pole"]), ("Spear", ["spea"]), ("Bow", ["bow"]),
            ("Xbow", ["xbow"]), ("Claw", ["h2h"]), ("Scepter", ["scep"]), ("Wand", ["wand"]),
            ("Staff", ["staf"]), ("Orb", ["orb"]), ("Javelin", ["jave"]),
            ("LightArm", ["tors", "ltor"]), ("MedArm", ["tors", "mtor"]), ("HeavyArm", ["tors", "htor"]),
            ("LightShd", ["shie", "lshi"]), ("MedShd", ["shie", "mshi"]), ("HeavyShd", ["shie", "hshi"]),
            ("LightPal", ["ashd", "lash"]), ("MedPal", ["ashd", "mash"]), ("HeavyPal", ["ashd", "hash"]),
            ("NecHead", ["head"]), ("Helm", ["helm"]), ("Circlet", ["circ"]),
            ("BarbHlm", ["phlm"]), ("Pelt", ["pelt"]),
            ("LightGlv", ["glov", "lglv"]), ("MedGlv", ["glov", "mglv"]), ("HeavyGlv", ["glov", "hglv"]),
            ("LightBot", ["boot", "lbot"]), ("MedBot", ["boot", "mbot"]), ("HeavyBot", ["boot", "hbot"]),
            ("Belt", ["belt"]), ("Arrows", ["bowq"]), ("Bolts", ["xboq"]),
        ]
        # No single Rare affix group may exceed 58% of the pool (catches accidental monopolies)
        MAX_SHARE = 0.58
        for kind, arows in (("prefix", mp_rows), ("suffix", ms_rows)):
            for label, types in slots:
                a = set()
                for t in types:
                    a |= anc(t)
                for alvl in (12, 30, 50, 70, 75):
                    bg = defaultdict(int)
                    by_grp_lvls = defaultdict(list)
                    tot = 0
                    for r in arows:
                        if r.get("spawnable") != "1" or r.get("version") == "0" or r.get("rare") != "1":
                            continue
                        lvl = int(r.get("level") or 0)
                        if not (lvl <= alvl <= int(r.get("maxlevel") or 999)):
                            continue
                        freq = int(r.get("frequency") or 0)
                        if freq <= 0:
                            continue
                        its = {r.get(f"itype{i}", "").strip() for i in range(1, 8) if r.get(f"itype{i}", "").strip()}
                        ets = {r.get(f"etype{i}", "").strip() for i in range(1, 6) if r.get(f"etype{i}", "").strip()}
                        if (its & a) and not (ets & a):
                            bg[r["group"]] += freq
                            by_grp_lvls[r["group"]].append((lvl, r.get("Name", ""), r.get("maxlevel", "")))
                            tot += freq
                    self.assertGreaterEqual(len(bg), 3, f"{label} {kind} at alvl={alvl} has only {len(bg)} groups")
                    top_g, top_w = max(bg.items(), key=lambda x: x[1])
                    share = top_w / tot
                    self.assertLessEqual(
                        share, MAX_SHARE,
                        f"{label} {kind} at alvl={alvl} dominated by grp {top_g} ({share*100:.1f}% > {MAX_SHARE*100:.0f}%, TotW={tot})",
                    )
                    # Guard against stale low-tier Normal rows (lvl <= 14) stacking at alvl=75 alongside a Hell tier (lvl >= 35)
                    # in core cutoff groups (e.g., Tireless lvl 6/14 stacking with Untiring lvl 36 on Heavy Boots)
                    if alvl == 75 and kind == "prefix":
                        for grp, entries in by_grp_lvls.items():
                            if grp in ("101", "105", "108", "116", "117", "118", "119", "120"):
                                hi_lvls = [lv for lv, _, _ in entries if lv >= 35]
                                lo_rows = [(lv, nm) for lv, nm, _ in entries if lv <= 14]
                                if hi_lvls and lo_rows:
                                    self.fail(
                                        f"{label} prefix grp {grp} at alvl=75 has stale low-tier rows {lo_rows} "
                                        f"stacking alongside high-tier lvl {max(hi_lvls)}"
                                    )

    def test_core_affix_groups_have_magic_only_apex_tier(self):
        """Every core scalable prefix & suffix group (plus Shield Single/All Res) must possess a Magic-only apex tier."""
        _, mp_rows = read_mod_tsv("magicprefix.txt")
        _, ms_rows = read_mod_tsv("magicsuffix.txt")

        core_prefix_groups = {
            "101", "105", "108", "109", "110", "111", "114", "115", "116",
            "117", "118", "119", "120", "122", "123", "125", "140", "142", "145",
        }
        core_suffix_groups = {
            "1", "2", "6", "9", "14", "15", "17", "19", "22", "23", "26", "35",
        }

        for fname, rows, req_groups in (
            ("magicprefix.txt", mp_rows, core_prefix_groups),
            ("magicsuffix.txt", ms_rows, core_suffix_groups),
        ):
            by_g = {}
            for r in rows:
                if r.get("spawnable") != "1" or r.get("version") == "0":
                    continue
                if r.get("itype1", "") in ("lcha", "mcha", "scha", "jewl", "malu"):
                    continue
                by_g.setdefault(r.get("group", ""), []).append(r)
            for grp in sorted(req_groups):
                gr = by_g.get(grp, [])
                magic_only = [r for r in gr if r.get("rare") != "1"]
                self.assertTrue(magic_only, f"{fname} group {grp} is missing a Magic-only apex tier")

        # Shield Single-Res (117..120) and All-Res (116) must each have a Magic-only apex strictly exceeding top Rare
        for grp in ("116", "117", "118", "119", "120"):
            shld_rows = [
                r for r in mp_rows
                if r.get("spawnable") == "1" and r.get("version") != "0"
                and r.get("group") == grp and r.get("itype1") == "shld" and not r.get("etype1")
            ]
            rare_max = max(int(r.get("mod1max") or 0) for r in shld_rows if r.get("rare") == "1")
            magic_max = max((int(r.get("mod1max") or 0) for r in shld_rows if r.get("rare") != "1"), default=0)
            self.assertGreater(magic_max, rare_max, f"Shield group {grp} Magic-only apex ({magic_max}) must exceed Rare max ({rare_max})")

    def test_zero_rare_affix_group_dropoffs_across_progression(self):
        """Every Rare affix group available at alvl 10/30/50 must still be rollable at alvl 75 (zero drop-offs)."""
        _, it_rows = read_mod_tsv("itemtypes.txt")
        _, mp_rows = read_mod_tsv("magicprefix.txt")
        _, ms_rows = read_mod_tsv("magicsuffix.txt")
        parents = {r["Code"]: [p for p in (r.get("Equiv1", ""), r.get("Equiv2", "")) if p] for r in it_rows if r.get("Code")}
        def anc(code):
            s, st = {code}, [code]
            while st:
                c = st.pop()
                for p in parents.get(c, []):
                    if p not in s:
                        s.add(p); st.append(p)
            return s

        slots = [
            ("Sword", ["swor"]), ("Axe", ["axe"]), ("Hammer", ["hamm"]), ("Mace", ["mace"]),
            ("Dagger", ["knif"]), ("Polearm", ["pole"]), ("Spear", ["spea"]), ("Bow", ["bow"]),
            ("Xbow", ["xbow"]), ("Claw", ["h2h"]), ("Scepter", ["scep"]), ("Wand", ["wand"]),
            ("Staff", ["staf"]), ("Orb", ["orb"]), ("Javelin", ["jave"]),
            ("LightArm", ["tors", "ltor"]), ("MedArm", ["tors", "mtor"]), ("HeavyArm", ["tors", "htor"]),
            ("LightShd", ["shie", "lshi"]), ("MedShd", ["shie", "mshi"]), ("HeavyShd", ["shie", "hshi"]),
            ("LightPal", ["ashd", "lash"]), ("MedPal", ["ashd", "mash"]), ("HeavyPal", ["ashd", "hash"]),
            ("NecHead", ["head"]), ("Helm", ["helm"]), ("Circlet", ["circ"]),
            ("BarbHlm", ["phlm"]), ("Pelt", ["pelt"]),
            ("LightGlv", ["glov", "lglv"]), ("MedGlv", ["glov", "mglv"]), ("HeavyGlv", ["glov", "hglv"]),
            ("LightBot", ["boot", "lbot"]), ("MedBot", ["boot", "mbot"]), ("HeavyBot", ["boot", "hbot"]),
            ("Belt", ["belt"]), ("Ring", ["ring"]), ("Amulet", ["amul"]), ("Arrows", ["bowq"]), ("Bolts", ["xboq"]),
        ]

        def active_grps(rows, types, alvl):
            a = set()
            for t in types:
                a |= anc(t)
            gs = set()
            for r in rows:
                if r.get("spawnable") != "1" or r.get("version") == "0" or r.get("rare") != "1":
                    continue
                if not (int(r.get("level") or 0) <= alvl <= int(r.get("maxlevel") or 999)):
                    continue
                if int(r.get("frequency") or 0) <= 0:
                    continue
                its = {r.get(f"itype{i}", "").strip() for i in range(1, 8) if r.get(f"itype{i}", "").strip()}
                ets = {r.get(f"etype{i}", "").strip() for i in range(1, 6) if r.get(f"etype{i}", "").strip()}
                if (its & a) and not (ets & a):
                    gs.add(r["group"])
            return gs

        for kind, arows in (("prefix", mp_rows), ("suffix", ms_rows)):
            for label, types in slots:
                early = active_grps(arows, types, 10) | active_grps(arows, types, 30) | active_grps(arows, types, 50)
                late = active_grps(arows, types, 75)
                dropped = sorted(early - late)
                self.assertEqual(dropped, [], f"{label} {kind} groups dropped off by alvl=75: {dropped}")


if __name__ == "__main__":
    unittest.main()

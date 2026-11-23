"""
test_monster_invariants.py
Property-based invariants for monstats.txt, levels.txt, Optional Exploration Dungeons,
monprop.txt, monumod.txt, cubemain.txt distillation, and hireling.txt 9-aura matrix.
"""
import json
import os
import unittest

from tests.fixture import get_indexed_tables, read_mod_tsv, read_vanilla_tsv
from mod_builder.common import MOD_ROOT, MOD_STRINGS, load_config


class TestMonsterAndSystemInvariants(unittest.TestCase):
    """Monsters, zone density, optional dungeons, cube distillation, and hireling contracts."""

    def test_monster_affinities_resistance_caps_and_optional_dungeons(self):
        cfg = load_config()
        from mod_builder.monsters import (
            FIXED_SKIP_ZONE_IDS,
            HEAVY_BRUTE_BASES,
            OPTIONAL_DUNGEON_IDS,
            OPTIONAL_DUNGEON_MONSTER_IDS,
            OPT_DST_TO_SRC,
            TACTICAL_DESCSTR_MAP,
            _get_monster_affinity,
            _parse_monster_tier,
            scale_int,
        )

        _, mon_rows = read_mod_tsv("monstats.txt")
        _, mprop_rows = read_mod_tsv("monprop.txt")
        _, prop_rows = read_vanilla_tsv("properties.txt")
        _, tc_rows = read_mod_tsv("treasureclassex.txt")
        _, van_mon_rows = read_vanilla_tsv("monstats.txt")

        valid_props = {r["code"] for r in prop_rows if r.get("code")}
        mprop_ids = {r["Id"] for r in mprop_rows if r.get("Id")}
        van_mon_by_id = {r["Id"]: r for r in van_mon_rows if r.get("Id")}
        mod_mon_by_id = {r["Id"]: r for r in mon_rows if r.get("Id")}
        tc_by_name = {r["Treasure Class"]: r for r in tc_rows if r.get("Treasure Class")}

        with open(os.path.join(MOD_STRINGS, "monsters.json"), "r", encoding="utf-8-sig") as f:
            mod_mon_strings = {e["Key"]: e for e in json.load(f) if isinstance(e, dict) and "Key" in e}

        for r in mprop_rows:
            for sfx in ("", " (N)", " (H)"):
                for idx in range(1, 7):
                    pcode = r.get(f"prop{idx}{sfx}", "").strip()
                    if pcode:
                        self.assertIn(pcode, valid_props)

        for r in mon_rows:
            mid = r.get("Id", "").strip()
            for exp_col in ("Exp", "Exp(N)", "Exp(H)", "minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
                ev = (r.get(exp_col) or "").strip()
                if ev.lstrip("-").isdigit():
                    self.assertTrue(0 <= int(ev) <= 32767, f"monstats.txt ({mid}): {exp_col}={ev} overflows int16_t")
            if mid == "zombie1" and not cfg.get("qa_blood_moor_boost", False):
                self.assertLess(int(r.get("Level", "1")), 50)
            mp_ref = r.get("MonProp", "").strip()
            if mp_ref:
                self.assertIn(mp_ref, mprop_ids)
            if mid in ("andariel", "duriel", "mephisto", "diablo", "baalcrab", "griswold", "smith", "radament", "izual", "hephasto"):
                ad_n, ad_nm, ad_h = int(r.get("aidist") or "0"), int(r.get("aidist(N)") or "0"), int(r.get("aidist(H)") or "0")
                self.assertTrue(42 <= ad_n < ad_nm < ad_h)

            if (
                r.get("isSpawn") != "1"
                or r.get("killable") != "1"
                or r.get("Align") != ""
                or (r.get("boss") == "1" and r.get("BaseId", "").strip() != "putriddefiler1")
                or r.get("primeevil") == "1"
                or int(r.get("Velocity") or "0") <= 0
            ):
                continue

            eff_mid = OPT_DST_TO_SRC.get(mid, mid)
            vr = van_mon_by_id.get(eff_mid)
            if not vr:
                continue
            bid = r.get("BaseId", "").strip()
            if eff_mid not in ("cowking", "darkelder"):
                t_idx = _parse_monster_tier(eff_mid, bid)
                v_el, _, r_el, _ = _get_monster_affinity(eff_mid, bid, t_idx)
                has_tactical = vr.get("DescStr", "").strip() in TACTICAL_DESCSTR_MAP
                dstr_key = r.get("DescStr", "").strip()
                if v_el or r_el or has_tactical:
                    self.assertTrue(
                        bool(dstr_key and dstr_key in mod_mon_strings and int(mod_mon_strings[dstr_key].get("id", 99999)) < 23000)
                    )
                else:
                    self.assertEqual(dstr_key, "")
                for rtype in ("Dm", "Ma", "Fi", "Li", "Co", "Po"):
                    for sfx in ("", "(N)", "(H)"):
                        self.assertLess(int(r.get(f"Res{rtype}{sfx}") or "0"), 100)

            ad_n, ad_nm, ad_h = int(r.get("aidist") or "0"), int(r.get("aidist(N)") or "0"), int(r.get("aidist(H)") or "0")
            self.assertTrue(38 <= ad_n < ad_nm < ad_h)
            if bid in HEAVY_BRUTE_BASES and eff_mid not in ("cowking", "darkelder"):
                self.assertLessEqual(int(r.get("Velocity") or "0"), int(vr.get("Velocity") or "0"))
            for gcol in ("MinGrp", "MaxGrp", "PartyMin", "PartyMax"):
                self.assertLessEqual(int(r.get(gcol) or "0"), int(vr.get(gcol) or "0"))
            for hcol in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
                vh = int(vr.get(hcol) or "0")
                if vh > 0:
                    self.assertGreater(int(r.get(hcol) or "0"), vh)
            self.assertGreaterEqual(int(r.get("Crit") or "0"), 10)

        for dst_id, src_id in OPT_DST_TO_SRC.items():
            dst_r, src_r = mod_mon_by_id[dst_id], mod_mon_by_id[src_id]
            for hcol in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)", "AC", "Exp"):
                if src_r.get(hcol, ""):
                    self.assertEqual(dst_r.get(hcol), scale_int(src_r[hcol], 1.20))

        for opt_id in OPTIONAL_DUNGEON_MONSTER_IDS:
            orow = mod_mon_by_id[opt_id]
            if opt_id not in ("maggotegg3", "maggotbaby3"):
                for tcol in ("TreasureClass", "TreasureClassChamp", "TreasureClassUnique", "TreasureClass(N)", "TreasureClass(H)"):
                    tval = orow.get(tcol, "").strip()
                    self.assertTrue(tval.endswith(" Opt") and tval in tc_by_name)

        _, van_lvl_rows = read_vanilla_tsv("levels.txt")
        van_lvl_by_name = {r["Name"]: r for r in van_lvl_rows if r.get("Name")}
        _, mod_lvl_rows = read_mod_tsv("levels.txt")
        for r in mod_lvl_rows:
            lname, zid = r.get("Name", ""), r.get("Id", "")
            if not lname or lname == "Expansion" or zid in FIXED_SKIP_ZONE_IDS:
                continue
            vr = van_lvl_by_name.get(lname)
            if not vr:
                continue
            for dcol in ("MonDen", "MonDen(N)", "MonDen(H)"):
                md, vd = int(r.get(dcol) or "0"), int(vr.get(dcol) or "0")
                if lname == "Act 5 - Siege 1" and dcol == "MonDen":
                    vd = int(vr.get("MonDen(N)") or "650")
                self.assertLessEqual(md, vd)
            if int(r.get("MonDen(N)") or "0") > 0:
                z_mons = {
                    r.get(f"{p}{i}", "").strip()
                    for i in range(1, 26)
                    for p in ("mon", "nmon", "umon")
                    if r.get(f"{p}{i}", "").strip()
                }
                if zid in OPTIONAL_DUNGEON_IDS:
                    self.assertEqual(z_mons - OPTIONAL_DUNGEON_MONSTER_IDS, set())
                else:
                    self.assertEqual(z_mons & OPTIONAL_DUNGEON_MONSTER_IDS, set())

        _, umod_rows = read_mod_tsv("monumod.txt")
        umod_consts = {r.get("id", "").strip(): int(r.get("constants") or "0") for r in umod_rows if r.get("id")}
        self.assertTrue(umod_consts.get("1", 0) < umod_consts.get("2", 0) < umod_consts.get("3", 0))
        self.assertTrue(umod_consts.get("4", 0) < umod_consts.get("5", 0) < umod_consts.get("6", 0))
        self.assertTrue(umod_consts.get("7", 0) < umod_consts.get("8", 0) < umod_consts.get("9", 0))

    def test_cubemain_distillation_and_hireling_9_aura_matrix(self):
        cfg = load_config()
        if not cfg.get("qa_cube_starter_kit", False):
            from mod_builder.cubemain import BINARY_OR_SKILL_PROPS, DISTILL_AFFIX_CAPS, PER_LEVEL_PROPS
            _, cube_rows = read_mod_tsv("cubemain.txt", max_rows=3000)
            expected_socket_punches = {
                (f'"{it},{qt},nos"', mn, mx)
                for it in ("weap", "armo")
                for qt, mn, mx in (("mag", "2", "3"), ("rar", "1", "2"), ("crf", "1", "2"), ("uni", "1", "1"), ("set", "1", "1"))
            }
            seen_socket_punches = {
                (r.get("input 1", ""), r.get("mod 1 min", ""), r.get("mod 1 max", ""))
                for r in cube_rows
                if r.get("input 2") == "bml" and r.get("input 3") == "skz" and r.get("mod 1") == "sock"
            }
            self.assertEqual(seen_socket_punches, expected_socket_punches)

            # Verify Caster Weapons (staf, orb, wand) precede generic 'weap', Sapphire boot/belt precede btbl,
            # and all 7 non-offsettable Gem Busts stamp cleanly into mod 5 with exact header column count.
            from mod_builder.common import MOD_ROOT
            import os
            cube_path = os.path.join(MOD_ROOT, "data/global/excel/cubemain.txt")
            first_idx = {}
            samples = {}
            wanted_samples = {
                "Craft staf gpr", "Craft orb gpr", "Craft wand gpr",
                "Craft weap gpb", "Craft staf gpb", "Craft shld gpb", "Craft boot gpb", "Craft belt gpb",
                "Craft glov gpb", "Craft ring gpb", "Craft amul gpb",
                "Craft weap gpy", "Craft ring gpy", "Craft tors gpy", "Craft staf gpy", "Craft amul gpy",
                "Craft tors gpg", "Craft tors gpw", "Craft tors gpv", "Craft tors skz", "Craft ring skz",
            }
            with open(cube_path, "r", encoding="utf-8", errors="replace") as cf:
                chdr = cf.readline().rstrip("\r\n").split("\t")
                ci = {h: i for i, h in enumerate(chdr)}
                ncols = len(chdr)
                for lnum, line in enumerate(cf, start=1):
                    parts = line.rstrip("\r\n").split("\t")
                    if len(parts) <= ci["mod 5 max"]:
                        continue
                    d = parts[ci["description"]]
                    for tag in ("Craft staf ", "Craft orb ", "Craft wand ", "Craft weap ", "Craft boot ", "Craft belt ", "Craft btbl "):
                        if d.startswith(tag) and tag not in first_idx:
                            first_idx[tag] = lnum
                    if d in wanted_samples and parts[ci["input 3"]] == '"r26,qty=2"':
                        self.assertEqual(len(parts), ncols, f"Column count mismatch on {d}")
                        samples[d] = (
                            parts[ci["mod 1"]], parts[ci["mod 1 min"]], parts[ci["mod 1 max"]],
                            parts[ci["mod 2"]],
                            parts[ci["mod 5"]], parts[ci["mod 5 min"]], parts[ci["mod 5 max"]],
                        )
            self.assertTrue(
                first_idx["Craft staf "] < first_idx["Craft orb "] < first_idx["Craft wand "] < first_idx["Craft weap "],
                f"Caster weapon crafts must precede generic weap: {first_idx}",
            )
            self.assertTrue(
                first_idx["Craft boot "] < first_idx["Craft belt "] < first_idx["Craft btbl "],
                f"Sapphire boot/belt crafts must precede shared btbl: {first_idx}",
            )
            self.assertEqual(samples["Craft staf gpr"], ("res-fire", "22", "32", "extra-fire", "damageresist", "-8", "-8"))
            self.assertEqual(samples["Craft orb gpr"][0], "res-fire")
            self.assertEqual(samples["Craft orb gpr"][3], "extra-fire")
            self.assertEqual(samples["Craft orb gpr"][4:], ("damageresist", "-6", "-6"))
            self.assertEqual(samples["Craft wand gpr"], samples["Craft orb gpr"])
            # Sapphire slot-contextual speed busts
            self.assertEqual(samples["Craft weap gpb"][4:], ("swing1", "-12", "-12"))
            self.assertEqual(samples["Craft staf gpb"][4:], ("cast1", "-12", "-12"))
            self.assertEqual(samples["Craft shld gpb"][4:], ("block2", "-12", "-12"))
            self.assertEqual(samples["Craft boot gpb"][4:], ("move1", "-7", "-7"))
            self.assertEqual(samples["Craft belt gpb"][4:], ("balance1", "-7", "-7"))
            self.assertEqual(samples["Craft glov gpb"][4:], ("swing1", "-7", "-7"))
            self.assertEqual(samples["Craft ring gpb"][4:], ("swing1", "-6", "-6"))
            self.assertEqual(samples["Craft amul gpb"][4:], ("balance1", "-6", "-6"))
            # Topaz (-Total Defense % via total-ac% -> skill_armor_percent across ALL slots)
            self.assertEqual(samples["Craft weap gpy"][4:], ("total-ac%", "-25", "-25"))
            self.assertEqual(samples["Craft ring gpy"][4:], ("total-ac%", "-12", "-12"))
            self.assertEqual(samples["Craft tors gpy"][4:], ("total-ac%", "-25", "-25"))
            self.assertEqual(samples["Craft staf gpy"][4:], ("total-ac%", "-25", "-25"))
            self.assertEqual(samples["Craft amul gpy"][4:], ("total-ac%", "-12", "-12"))
            # Emerald (-hp%), Diamond (-mana%), Amethyst (-red-mag), Skull (skull-curse)
            self.assertEqual(samples["Craft tors gpg"][4:], ("hp%", "-9", "-9"))
            self.assertEqual(samples["Craft tors gpw"][4:], ("mana%", "-9", "-9"))
            self.assertEqual(samples["Craft tors gpv"][4:], ("red-mag", "-15", "-15"))
            self.assertEqual(samples["Craft tors skz"][4:], ("skull-curse", "-10", "-3"))
            self.assertEqual(samples["Craft ring skz"][4:], ("skull-curse", "-5", "-2"))
            distill_count = 0
            for r in cube_rows:
                self.assertFalse(r.get("numinputs") == "1" and r.get("input 1") in ("isc", "tsc"))
                desc = r.get("description", "")
                if desc.startswith("Distill "):
                    distill_count += 1
                    self.assertEqual(
                        (r.get("numinputs"), r.get("input 2"), r.get("input 3"), r.get("output"), r.get("lvl")),
                        ("3", "bml", '"jew,mag"', '"jew,crf"', "1"),
                    )
                    for m_i in range(1, 6):
                        mcode = r.get(f"mod {m_i}", "").strip()
                        if not mcode:
                            continue
                        self.assertNotIn(mcode, ("levelreq", "nofreeze", "cannotbefrozen"))
                        if mcode not in BINARY_OR_SKILL_PROPS:
                            self.assertEqual(r.get(f"mod {m_i} chance", "").strip(), "100")
                            self.assertIn(mcode, DISTILL_AFFIX_CAPS)
                            c_min, c_max = DISTILL_AFFIX_CAPS[mcode]
                            if mcode in PER_LEVEL_PROPS:
                                self.assertTrue(c_min <= int(r.get(f"mod {m_i} param", "0")) <= c_max)
                            else:
                                v_lo, v_hi = int(r.get(f"mod {m_i} min", "0")), int(r.get(f"mod {m_i} max", "0"))
                                self.assertTrue(c_min <= v_lo < v_hi <= c_max)
            self.assertGreaterEqual(distill_count, 800)

        idx = get_indexed_tables()
        skill_by_name = idx["skills_by_lower"]
        sdesc_by_name = idx["desc_by_lower"]
        _, hire_rows = read_mod_tsv("hireling.txt")
        act2_auras_by_diff = {"1": set(), "2": set(), "3": set()}

        for r in hire_rows:
            ver, act, diff = r.get("Version", "").strip(), r.get("Act", "").strip(), r.get("Difficulty", "").strip()
            if act == "2":
                act2_auras_by_diff[diff].add(r.get("Skill2", "").strip())
            active_count = 0
            for s_idx in range(1, 7):
                sk = r.get(f"Skill{s_idx}", "").strip()
                if not sk:
                    continue
                md = r.get(f"Mode{s_idx}", "").strip()
                slvl = int(r.get(f"Level{s_idx}", "0") or "0")
                ch = int(r.get(f"Chance{s_idx}", "0") or "0")
                sk_row = skill_by_name.get(sk.lower())
                self.assertIsNotNone(sk_row)
                sd_key = sk_row.get("skilldesc", "").strip().lower()
                hic = sdesc_by_name.get(sd_key, {}).get("HireableIconCel", "").strip()
                self.assertTrue(hic.isdigit() and 0 <= int(hic) <= 54)
                if ver == "100":
                    self.assertGreaterEqual(slvl, 4)
                    if md != "5":
                        active_count += 1
                        self.assertLessEqual(s_idx, 3)
                        self.assertGreaterEqual(ch, 15)
            if ver == "100":
                self.assertLessEqual(active_count, 3)

        expected_act2 = {
            "1": {"Thorns", "Defiance", "Blessed Aim"},
            "2": {"Cleansing", "Holy Freeze", "Vigor"},
            "3": {"Meditation", "Salvation", "Sanctuary"},
        }
        self.assertEqual(act2_auras_by_diff, expected_act2)

        for spr_rel, exp_len in (
            ("data/hd/global/ui/spells/hireables/hrskillicon.sprite", 40 + 55 * 132 * 130 * 4),
            ("data/hd/global/ui/spells/hireables/hrskillicon.lowend.sprite", 40 + 55 * 67 * 65 * 4),
        ):
            spr_path = os.path.join(MOD_ROOT, spr_rel)
            self.assertTrue(os.path.exists(spr_path) and os.path.getsize(spr_path) == exp_len)


if __name__ == "__main__":
    unittest.main()

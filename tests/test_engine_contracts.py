"""
test_engine_contracts.py
Engine Crash, Referential Integrity, and Function-to-Column Coupling Contracts.
Encodes universal D2R C++ engine rules across all rows without hardcoding single-skill balance numbers.
"""
import json
import os
import unittest
from typing import Dict

from tests.fixture import get_indexed_tables, load_all_string_keys, read_mod_tsv, read_vanilla_tsv
from mod_builder.common import MOD_ROOT, MOD_STRINGS, read_strings_json


class TestEngineContracts(unittest.TestCase):
    """Universal D2R engine referential, binary-bound, and function-coupling contracts."""

    def test_states_and_overlay_referential_integrity(self):
        _, state_rows = read_mod_tsv("states.txt")
        _, ov_rows = read_vanilla_tsv("overlay.txt")
        valid_overlays = {r["overlay"] for r in ov_rows if r.get("overlay")}
        states_by_name = {r["state"]: r for r in state_rows if r.get("state")}

        self.assertEqual(
            states_by_name.get("staminapot", {}).get("stambarblue", ""),
            "",
            "states.txt: staminapot.stambarblue must be cleared",
        )
        for r in state_rows:
            st_name = r.get("state", "")
            for ocol in (
                "overlay1",
                "overlay2",
                "overlay3",
                "overlay4",
                "pgsvoverlay",
                "castoverlay",
                "removerlay",
            ):
                oval = r.get(ocol, "").strip()
                if oval:
                    self.assertIn(
                        oval,
                        valid_overlays,
                        f"states.txt ({st_name}): {ocol}={oval!r} not found in overlay.txt",
                    )

    def test_skills_and_missiles_referential_integrity(self):
        idx = get_indexed_tables()
        states_by_name = idx["states_by_name"]
        missiles_by_name = idx["missiles_by_name"]
        _, skill_rows = read_mod_tsv("skills.txt")
        _, missile_rows = read_mod_tsv("missiles.txt")

        for r in skill_rows:
            sname = r.get("skill", "")
            if not sname:
                continue
            for scol in ("aurastate", "auratargetstate", "passivestate"):
                st = r.get(scol, "").strip()
                if st:
                    self.assertIn(
                        st,
                        states_by_name,
                        f"skills.txt ({sname}): {scol}={st!r} missing from states.txt",
                    )
            for mcol in (
                "srvmissile",
                "srvmissilea",
                "srvmissileb",
                "srvmissilec",
                "cltmissile",
                "cltmissilea",
                "cltmissileb",
                "cltmissilec",
            ):
                ms = r.get(mcol, "").strip()
                if ms:
                    self.assertIn(
                        ms,
                        missiles_by_name,
                        f"skills.txt ({sname}): {mcol}={ms!r} missing from missiles.txt",
                    )

        for mr in missile_rows:
            mname = mr.get("Missile", "")
            if not mname:
                continue
            for sm_col in (
                "ExplosionMissile",
                "SubMissile1",
                "SubMissile2",
                "SubMissile3",
                "HitSubMissile1",
                "HitSubMissile2",
                "HitSubMissile3",
                "HitSubMissile4",
                "CltSubMissile1",
                "CltSubMissile2",
                "CltSubMissile3",
                "CltHitSubMissile1",
                "CltHitSubMissile2",
                "CltHitSubMissile3",
                "CltHitSubMissile4",
            ):
                sm_val = mr.get(sm_col, "").strip()
                if sm_val:
                    self.assertIn(
                        sm_val,
                        missiles_by_name,
                        f"missiles.txt ({mname}): {sm_col}={sm_val!r} missing from missiles.txt",
                    )

    def test_skill_and_missile_function_column_coupling_rules(self):
        """
        Verify engine function-to-column contracts across ALL skills and missiles:
        - Rollback skills (cltdofunc=37 or srvdofunc=13) must have 0 < Param2 <= 100
        - Blade Shield periodic aura pulse (srvdofunc=28) requires aurastate, perdelay, and srvmissile
        - Ground AoE spawner (srvdofunc=99) requires srvmissilea & cltmissilea
        - Charge consumer (srvstfunc=39 with progressive_ aurastate) requires calc2='' and auralencalc='12'
        - Charge-Up attacks (srvstfunc=23, srvdofunc=34) require anim='A1', seqtrans='A1', seqnum='', weapsel='', itypea1='mele'
        - Ground AoE visual spawner missiles (pCltDoFunc=48) require CltSubMissile1
        """
        idx = get_indexed_tables()
        missiles_by_name = idx["missiles_by_name"]
        _, skill_rows = read_mod_tsv("skills.txt")

        for r in skill_rows:
            sname = r.get("skill", "")
            if not sname:
                continue

            # Rule 1: Animation rollback bounds (Zeal / Fury / Fend)
            if r.get("cltdofunc") == "37" or r.get("srvdofunc") == "13":
                p2 = r.get("Param2", "").strip()
                if p2:
                    val = int(p2)
                    self.assertTrue(
                        0 < val <= 100,
                        f"skills.txt ({sname}): rollback Param2={val} out of safe (0..100] bounds",
                    )

            # Rule 2a: srvdofunc=28 + aura=1 (Blade Shield periodic pulse) must use srvmissile + aurastate + perdelay
            if r.get("srvdofunc") == "28" and r.get("aura") == "1":
                self.assertTrue(
                    bool(r.get("aurastate", "").strip()),
                    f"skills.txt ({sname}): srvdofunc=28 (aura=1) requires aurastate",
                )
                self.assertTrue(
                    bool(r.get("perdelay", "").strip()),
                    f"skills.txt ({sname}): srvdofunc=28 (aura=1) requires perdelay",
                )
                self.assertTrue(
                    bool(r.get("srvmissile", "").strip()),
                    f"skills.txt ({sname}): srvdofunc=28 (aura=1) reads srvmissile (not srvmissilea)",
                )

            # Rule 2b: srvstfunc=14 + srvdofunc=28 (Fire Wall line spawner) requires srvmissilea
            if r.get("srvstfunc") == "14" and r.get("srvdofunc") == "28":
                self.assertTrue(
                    bool(r.get("srvmissilea", "").strip()),
                    f"skills.txt ({sname}): Fire Wall spawner (srvstfunc=14, srvdofunc=28) requires srvmissilea",
                )

            # Rule 3: srvdofunc=99 (Shock Web ground AoE throw) requires srvmissilea & cltmissilea
            if r.get("srvdofunc") == "99" and r.get("charclass") in ("sor", "ass"):
                sma = r.get("srvmissilea", "").strip()
                cma = r.get("cltmissilea", "").strip()
                self.assertTrue(
                    bool(sma and cma),
                    f"skills.txt ({sname}): srvdofunc=99 requires both srvmissilea and cltmissilea",
                )
                ms_row = missiles_by_name.get(cma, {})
                if ms_row.get("pCltDoFunc") == "48":
                    self.assertTrue(
                        bool(ms_row.get("CltSubMissile1", "").strip()),
                        f"missiles.txt ({cma}): pCltDoFunc=48 requires CltSubMissile1",
                    )

            # Rule 4: srvstfunc=39 charge consumer contract
            if r.get("srvstfunc") == "39" and r.get("aurastate", "").startswith("progressive_"):
                self.assertEqual(
                    r.get("calc2", "").strip(),
                    "",
                    f"skills.txt ({sname}): srvstfunc=39 charge consumer must have calc2=''",
                )
                self.assertEqual(
                    r.get("auralencalc", "").strip(),
                    "12",
                    f"skills.txt ({sname}): srvstfunc=39 charge consumer must have auralencalc='12'",
                )

            # Rule 5: Assassin Charge-Up attacks (srvstfunc=23, srvdofunc=34)
            if r.get("charclass") == "ass" and r.get("srvstfunc") == "23" and r.get("srvdofunc") == "34":
                self.assertEqual(r.get("weapsel"), "", f"{sname}: Charge-Up must have weapsel=''")
                self.assertEqual(r.get("itypea1"), "mele", f"{sname}: Charge-Up must have itypea1='mele'")
                self.assertEqual(r.get("anim"), "A1", f"{sname}: Charge-Up must use anim='A1'")
                self.assertEqual(r.get("seqtrans"), "A1", f"{sname}: Charge-Up must use seqtrans='A1'")
                self.assertEqual(r.get("seqnum"), "", f"{sname}: Charge-Up must have seqnum=''")

    def test_skilldesc_string_keys_and_format_guards(self):
        all_str_keys = load_all_string_keys()
        _, desc_rows = read_mod_tsv("skilldesc.txt")
        forbidden_warlock_keys = {"ModStr2u"}
        forbidden_line19_fmt_keys = {"StrSkillRadiusSingular", "StrSkill29", "StrSkill18", "StrSkill62"}

        for r in desc_rows:
            dname = r.get("skilldesc", "")
            if not dname:
                continue
            for col, val in r.items():
                if col.startswith(("desctext", "dsc2text", "dsc3text")) and val:
                    self.assertNotIn(
                        val,
                        forbidden_warlock_keys,
                        f"skilldesc.txt ({dname}): {col}={val!r} uses forbidden Warlock string key",
                    )
                    self.assertFalse(
                        dname == "sanctuary" and val == "Skillname224",
                        "skilldesc.txt (sanctuary): forbidden Skillname224 reference",
                    )
                    self.assertIn(
                        val,
                        all_str_keys,
                        f"skilldesc.txt ({dname}): {col}={val!r} not found in any string JSON table",
                    )

            for pfx in ("descline", "dsc2line", "dsc3line"):
                t_pfx = pfx.replace("line", "text")
                for idx_n in range(1, 8):
                    if r.get(f"{pfx}{idx_n}", "").strip() == "19":
                        for ab in ("a", "b"):
                            tk = r.get(f"{t_pfx}{ab}{idx_n}", "").strip()
                            self.assertNotIn(
                                tk,
                                forbidden_line19_fmt_keys,
                                f"skilldesc.txt ({dname}): {pfx}{idx_n}=19 uses %d format string {tk!r} (use descline=36)",
                            )

    def test_custom_string_ids_and_shared_json_completeness(self):
        # 1. Shared items.json and item-names.json cross-module keys
        hd_items_path = os.path.join(MOD_ROOT, "data/hd/items/items.json")
        with open(hd_items_path, "r", encoding="utf-8") as f:
            hd_list = json.load(f)
        hd_map = {}
        for entry in hd_list:
            if isinstance(entry, dict):
                for k, v in entry.items():
                    hd_map[k] = v.get("asset") if isinstance(v, dict) else None
        for req_code in ("wm2", "yp2", "vp2", "bml", "um1", "vk1", "sw1", "va1", "ky2", "ky3", "z00"):
            self.assertIn(req_code, hd_map, f"data/hd/items/items.json: missing {req_code!r}")
        self.assertEqual(hd_map.get("um1"), "hammer/horadric_malus")
        self.assertEqual(hd_map.get("bml"), "hammer/horadric_malus")

        mod_item_names_path = os.path.join(MOD_STRINGS, "item-names.json")
        with open(mod_item_names_path, "r", encoding="utf-8-sig") as f:
            mod_item_names = {e.get("Key") for e in json.load(f) if isinstance(e, dict)}
        for req_key in ("wm2", "bml", "um1", "opl", "vk1", "ky2", "ky3", "z00"):
            self.assertIn(req_key, mod_item_names, f"item-names.json: missing {req_key!r}")

        # 2. Vanilla monsters.json keys must never be overwritten
        van_mon_strings = {
            e["Key"]: e["enUS"]
            for e in read_strings_json("monsters.json")
            if isinstance(e, dict) and "Key" in e
        }
        with open(os.path.join(MOD_STRINGS, "monsters.json"), "r", encoding="utf-8-sig") as f:
            for e in json.load(f):
                if isinstance(e, dict) and "Key" in e:
                    mk = e["Key"]
                    if mk in van_mon_strings:
                        self.assertEqual(
                            e.get("enUS"),
                            van_mon_strings[mk],
                            f"monsters.json: existing vanilla key {mk!r} was overwritten",
                        )

        # 3. Zero custom string ID (>= 60000) collisions across all JSON tables
        seen_custom_ids: Dict[int, str] = {}
        for sfn in (
            "item-names.json",
            "item-modifiers.json",
            "item-nameaffixes.json",
            "skills.json",
            "ui.json",
            "quests.json",
        ):
            sp = os.path.join(MOD_STRINGS, sfn)
            with open(sp, "r", encoding="utf-8-sig") as f:
                for e in json.load(f):
                    if isinstance(e, dict):
                        sid = int(e.get("id") or 0)
                        skey = str(e.get("Key") or "")
                        if sid >= 60000:
                            self.assertNotIn(
                                sid,
                                seen_custom_ids,
                                f"Duplicate custom string id={sid}: {sfn}:{skey} collides with {seen_custom_ids.get(sid)}",
                            )
                            seen_custom_ids[sid] = f"{sfn}:{skey}"

        # 4. Compiled HD sprites & Barbarian 3D state machine completeness
        for rel_sp in (
            "herb/herb.sprite",
            "torch/torch.sprite",
            "body_part/tail.sprite",
            "key/skeleton_key.sprite",
            "body_part/jawbone.sprite",
            "body_part/horn.sprite",
            "potion/elixir.sprite",
            "potion/healing_potion.sprite",
            "potion/full_healing_potion.sprite",
            "potion/mana_potion.sprite",
            "potion/full_mana_potion.sprite",
            "potion/rejuv_potion.sprite",
        ):
            sp_path = os.path.join(MOD_ROOT, "data/hd/global/ui/items/misc", rel_sp)
            self.assertTrue(os.path.exists(sp_path), f"Missing compiled HD sprite: {sp_path}")

        barb_sm_path = os.path.join(
            MOD_ROOT, "data/hd/character/player/barbarian/barbarian_state_machine.json"
        )
        self.assertTrue(os.path.exists(barb_sm_path), f"Missing Barbarian 3D state machine: {barb_sm_path}")
        with open(barb_sm_path, "r", encoding="utf-8") as f:
            barb_sm = json.load(f)
        barb_seq_states = {
            (s.get("modeId"), s.get("skillIndex"), s.get("stepIndex")): s
            for s in barb_sm.get("states", [])
        }
        for req_key in ((18, 139, 0), (18, 139, 1), (18, 107, 0), (18, 107, 1)):
            self.assertIn(
                req_key,
                barb_seq_states,
                f"barbarian_state_machine.json missing sequence state {req_key}",
            )


if __name__ == "__main__":
    unittest.main()

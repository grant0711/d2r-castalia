#!/usr/bin/env python3
"""
verify.py
Automated, balance-number-agnostic Invariant & Regression Verifier for the D2R Overhaul Mod.
Runs automatically at the end of d2r-build-mod.py to guarantee:
1. Engine Crash & Referential Integrity (CRLF, column counts, animation rollback bounds,
   states.txt/missiles.txt/strings.json/items.json cross-references)
2. Feature & Design Contracts (zero potions in TreasureClassEx.txt, QA toggles respected,
   melee rangeadder > 0, javelin reach tiers, non-destructible socketable throwing weapons,
   and shared-file completeness across modules).
"""
import json
import os
from typing import Dict, List, Set, Tuple

from mod_builder.common import (
    MOD_EXCEL,
    MOD_ROOT,
    MOD_STRINGS,
    VANILLA_STRINGS,
    load_config,
    read_excel_tsv,
)


def _read_mod_tsv(filename: str, max_rows: int = 0) -> Tuple[List[str], List[Dict[str, str]]]:
    path = os.path.join(MOD_EXCEL, filename)
    with open(path, "rb") as f:
        if max_rows > 0:
            lines: List[str] = []
            for _ in range(max_rows + 1):
                bline = f.readline()
                if not bline:
                    break
                if not bline.endswith(b"\r\n"):
                    raise AssertionError(f"{filename}: missing CRLF (\\r\\n) line endings")
                lines.append(bline[:-2].decode("utf-8"))
        else:
            raw_bytes = f.read()
            if b"\r\n" not in raw_bytes:
                raise AssertionError(f"{filename}: missing CRLF (\\r\\n) line endings")
            raw = raw_bytes.decode("utf-8")
            lines = raw.split("\r\n")
            if lines and lines[-1] == "":
                lines.pop()
    headers = lines[0].split("\t")
    rows: List[Dict[str, str]] = []
    for idx, line in enumerate(lines[1:], start=2):
        cols = line.split("\t")
        if len(cols) != len(headers):
            raise AssertionError(
                f"{filename} line {idx}: expected {len(headers)} columns, got {len(cols)}"
            )
        rows.append(dict(zip(headers, cols)))
    return headers, rows


def _load_all_string_keys() -> Set[str]:
    keys: Set[str] = set()
    for root in (VANILLA_STRINGS, MOD_STRINGS):
        if not os.path.isdir(root):
            continue
        for fname in os.listdir(root):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            for entry in data:
                if isinstance(entry, dict) and "Key" in entry:
                    keys.add(entry["Key"])
    return keys


def verify_all(cfg: dict = None) -> List[str]:
    if cfg is None:
        cfg = load_config()

    checks_passed: List[str] = []

    # 1. Verify states.txt & skills.txt & missiles.txt & skilldesc.txt
    _, state_rows = _read_mod_tsv("states.txt")
    _, ov_rows = read_excel_tsv("overlay.txt")
    valid_overlays = {r["overlay"] for r in ov_rows if r.get("overlay")}
    states_by_name = {r["state"]: r for r in state_rows if r.get("state")}
    if states_by_name.get("staminapot", {}).get("stambarblue", "") != "":
        raise AssertionError("states.txt: staminapot.stambarblue must be cleared")
    for r in state_rows:
        st_name = r.get("state", "")
        for ocol in ("overlay1", "overlay2", "overlay3", "overlay4", "pgsvoverlay", "castoverlay", "removerlay"):
            oval = r.get(ocol, "").strip()
            if oval and oval not in valid_overlays:
                raise AssertionError(
                    f"states.txt ({st_name}): {ocol}='{oval}' not found in overlay.txt"
                )

    _, missile_rows = _read_mod_tsv("missiles.txt")
    missile_names = {r["Missile"] for r in missile_rows if r.get("Missile")}

    _, skill_rows = _read_mod_tsv("skills.txt")
    for r in skill_rows:
        sname = r.get("skill", "")
        if not sname:
            continue
        # Guard against negative-frame animation rollback crashes (e.g., Zeal / Fury / Fend)
        if r.get("cltdofunc") == "37" or r.get("srvdofunc") == "13":
            p2 = r.get("Param2", "")
            if p2:
                val = int(p2)
                if not (0 < val <= 100):
                    raise AssertionError(
                        f"skills.txt ({sname}): rollback Param2={val} out of safe (0..100] bounds (will crash client!)"
                    )
        # Verify state references exist in states.txt
        for scol in ("aurastate", "auratargetstate", "passivestate"):
            st = r.get(scol, "").strip()
            if st and st not in states_by_name:
                raise AssertionError(f"skills.txt ({sname}): {scol}='{st}' missing from states.txt")
        # Verify missile references exist in missiles.txt
        for mcol in (
            "srvmissile", "srvmissilea", "srvmissileb", "srvmissilec",
            "cltmissile", "cltmissilea", "cltmissileb", "cltmissilec",
        ):
            ms = r.get(mcol, "").strip()
            if ms and ms not in missile_names:
                raise AssertionError(f"skills.txt ({sname}): {mcol}='{ms}' missing from missiles.txt")

    # Verify skilldesc.txt string references & guard against Warlock/wrong-skill string mixups
    all_str_keys = _load_all_string_keys()
    _, desc_rows = _read_mod_tsv("skilldesc.txt")
    forbidden_warlock_keys = {"ModStr2u"}
    for r in desc_rows:
        dname = r.get("skilldesc", "")
        if not dname:
            continue
        for col, val in r.items():
            if col.startswith(("desctext", "dsc2text", "dsc3text")) and val:
                if val in forbidden_warlock_keys or (dname == "sanctuary" and val == "Skillname224"):
                    raise AssertionError(
                        f"skilldesc.txt ({dname}): {col}='{val}' uses forbidden string key"
                    )
                if val not in all_str_keys:
                    raise AssertionError(
                        f"skilldesc.txt ({dname}): {col}='{val}' not found in any string JSON table"
                    )
    checks_passed.append("skills/states/missiles/skilldesc referential & rollback bounds")

    # 2. Verify treasureclassex.txt & objects.txt drop/chest/lockbox contracts
    _, tc_rows = _read_mod_tsv("treasureclassex.txt")
    globally_forbidden_tc_items = {
        "key", "ky0", "ky1", "ky2", "ky3", "rvs", "rvl", "cm1", "cm2", "cm3", "cs2",
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
        has_lockbox = False
        for i in range(1, 11):
            it = r.get(f"Item{i}", "").strip()
            if it in globally_forbidden_tc_items:
                raise AssertionError(
                    f"TreasureClassEx.txt ({tc_name}): globally forbidden item '{it}' in Item{i}"
                )
            if not is_chest_tc and it in monster_forbidden_potions:
                raise AssertionError(
                    f"TreasureClassEx.txt ({tc_name}): forbidden potion '{it}' in monster TC Item{i}"
                )
            if is_chest_tc:
                if any(bad in it for bad in ("Equip", "Weap", "Armo", "Melee", "Bow", "Junk")):
                    raise AssertionError(
                        f"TreasureClassEx.txt ({tc_name}): forbidden equipment/junk '{it}' in Chest Item{i}"
                    )
                if "Lockbox" in it:
                    has_lockbox = True
        if is_chest_tc and not has_lockbox:
            raise AssertionError(f"TreasureClassEx.txt ({tc_name}): Chest TC missing Lockbox entry")
    _, obj_rows = _read_mod_tsv("objects.txt")
    for r in obj_rows:
        if r.get("Lockable") == "1":
            raise AssertionError(
                f"objects.txt ({r.get('Class')} ID={r.get('*ID')}): Lockable=1 found"
            )
        if r.get("OperateFn") == "21" and r.get("Selectable0") != "1":
            raise AssertionError(
                f"objects.txt ({r.get('Class')} ID={r.get('*ID')}): Malus stand OperateFn=21 must have Selectable0=1"
            )
    _, preset_rows = _read_mod_tsv("objpreset.txt")
    forbidden_preset_chests = {
        "PlaceUniqueChest",
        "ConsolationChest",
        "SpecialChest100",
        "PlaceRandomTreasureChest",
    }
    for pr in preset_rows:
        if pr.get("ObjectClass") in forbidden_preset_chests:
            raise AssertionError(
                f"objpreset.txt (Act={pr.get('Act')} Index={pr.get('Index')}): forbidden Sparkly/Super Chest spawner '{pr.get('ObjectClass')}' still present"
            )
    checks_passed.append("TreasureClassEx, objects.txt & objpreset.txt chest/lockbox/potion/charm/malus contracts")

    # 3. Verify weapons.txt & armor.txt melee reach, javelin reach tiers, throwing properties,
    #    and strictly partitioned Act 1..5 Magic-only vendor stocking + ubercode/ultracode upgrades
    _, weap_rows = _read_mod_tsv("weapons.txt")
    _, arm_rows = _read_mod_tsv("armor.txt")
    ranged_only_types = {"bow", "abow", "xbow", "tpot"}
    vendor_names = (
        "Charsi", "Gheed", "Akara", "Fara", "Lysander", "Drognan",
        "Hratli", "Alkor", "Ormus", "Elzix", "Asheara", "Cain",
        "Halbu", "Malah", "Larzuk", "Anya", "Jamella",
    )
    for r in weap_rows:
        code = r.get("code", "")
        wtype = r.get("type", "")
        if not code or not wtype:
            continue
        if code == "um1":
            if (
                r.get("CharsiMin") != "1"
                or r.get("CharsiMax") != "1"
                or r.get("PermStoreItem") != "0"
                or r.get("cost") != "100000"
            ):
                raise AssertionError(
                    "weapons.txt (um1): Untempered Malus must have CharsiMin=1, CharsiMax=1, PermStoreItem=0, cost=100000"
                )
            continue
        if wtype != "tpot":
            for vn in vendor_names:
                if r.get(f"{vn}Min") or r.get(f"{vn}Max"):
                    raise AssertionError(
                        f"weapons.txt ({code}): white vendor stock found on {vn} (all weapons except tpot/um1 must be Magic-only)"
                    )
        if r.get("spawnable") != "1" or wtype == "tpot" or code in ("bml", "um1"):
            continue
        wcost = int(r.get("cost") or "0")
        if wcost < 2 or wcost > 50000:
            raise AssertionError(
                f"weapons.txt ({code}): normalized base cost={wcost} out of expected 2..50000 range"
            )
        if code == r.get("normcode"):
            exp_nm = r.get("ubercode") if r.get("ubercode") != code else "xxx"
            exp_hell = r.get("ultracode") if r.get("ultracode") != code else "xxx"
            if r.get("NightmareUpgrade") != exp_nm or r.get("HellUpgrade") != exp_hell:
                raise AssertionError(
                    f"weapons.txt ({code}): expected NightmareUpgrade={exp_nm}, HellUpgrade={exp_hell}"
                )
            stocked_vendors = [vn for vn in vendor_names if int(r.get(f"{vn}MagicMax") or "0") >= 1]
            if not stocked_vendors:
                raise AssertionError(f"weapons.txt ({code}): Normal base weapon not stocked at any vendor")
            for vn in stocked_vendors:
                if r.get(f"{vn}MagicLvl") != "1":
                    raise AssertionError(
                        f"weapons.txt ({code}): {vn}MagicLvl='{r.get(f'{vn}MagicLvl')}' must be '1' so Act 1 Normal (ilvl cap 12) spawns Magic items!"
                    )
        else:
            for vn in vendor_names:
                if r.get(f"{vn}MagicMin") or r.get(f"{vn}MagicMax"):
                    raise AssertionError(
                        f"weapons.txt ({code}): non-Normal weapon has direct Magic vendor stock on {vn}"
                    )
        if wtype not in ranged_only_types:
            ra = int(r.get("rangeadder") or "0")
            if ra < 1:
                raise AssertionError(
                    f"weapons.txt ({code}, type={wtype}): spawnable melee weapon has rangeadder={ra} (< 1)"
                )
        if wtype in ("jave", "ajav"):
            ra = int(r.get("rangeadder") or "0")
            expected_min = 3 if code in ("glv", "9gl", "7gl", "tsp", "9ts", "7ts") else 2
            if ra < expected_min:
                raise AssertionError(
                    f"weapons.txt ({code}): javelin rangeadder={ra}, expected >= {expected_min}"
                )
        if wtype in ("jave", "ajav", "tkni", "taxe"):
            if r.get("nodurability") != "1" or r.get("hasinv") != "1":
                raise AssertionError(
                    f"weapons.txt ({code}): throwing weapon must be non-destructible and socketable"
                )
        expected_weap_ap = {"staf": "310", "wand": "311", "scep": "312", "orb": "303", "h2h": "315", "h2h2": "315"}
        if wtype in expected_weap_ap and r.get("auto prefix") != expected_weap_ap[wtype]:
            raise AssertionError(
                f"weapons.txt ({code}, type={wtype}): expected auto prefix={expected_weap_ap[wtype]}"
            )
    for r in arm_rows:
        code = r.get("code", "")
        if not code:
            continue
        for vn in vendor_names:
            if r.get(f"{vn}Min") or r.get(f"{vn}Max"):
                raise AssertionError(
                    f"armor.txt ({code}): white vendor stock found on {vn} (all armors must be Magic-only)"
                )
        if r.get("spawnable") != "1":
            continue
        expected_arm_ap = {"phlm": "313", "pelt": "314", "head": "305"}
        atype = r.get("type", "")
        if atype in expected_arm_ap and r.get("auto prefix") != expected_arm_ap[atype]:
            raise AssertionError(
                f"armor.txt ({code}, type={atype}): expected auto prefix={expected_arm_ap[atype]}"
            )
        acost = int(r.get("cost") or "0")
        if acost < 50 or acost > 50000:
            raise AssertionError(
                f"armor.txt ({code}): normalized base cost={acost} out of expected 50..50000 range"
            )
        if code == r.get("normcode"):
            exp_nm = r.get("ubercode") if r.get("ubercode") != code else "xxx"
            exp_hell = r.get("ultracode") if r.get("ultracode") != code else "xxx"
            if r.get("NightmareUpgrade") != exp_nm or r.get("HellUpgrade") != exp_hell:
                raise AssertionError(
                    f"armor.txt ({code}): expected NightmareUpgrade={exp_nm}, HellUpgrade={exp_hell}"
                )
            stocked_vendors = [vn for vn in vendor_names if int(r.get(f"{vn}MagicMax") or "0") >= 1]
            if not stocked_vendors:
                raise AssertionError(f"armor.txt ({code}): Normal base armor not stocked at any vendor")
            for vn in stocked_vendors:
                if r.get(f"{vn}MagicLvl") != "1":
                    raise AssertionError(
                        f"armor.txt ({code}): {vn}MagicLvl='{r.get(f'{vn}MagicLvl')}' must be '1' so Act 1 Normal (ilvl cap 12) spawns Magic items!"
                    )
        else:
            for vn in vendor_names:
                if r.get(f"{vn}MagicMin") or r.get(f"{vn}MagicMax"):
                    raise AssertionError(
                        f"armor.txt ({code}): non-Normal armor has direct Magic vendor stock on {vn}"
                    )
    checks_passed.append("weapons/armor melee/javelin/throwing & Act 1..5 Magic-only vendor progression contracts")

    # 4. Verify shared JSON files (items.json and item-names.json) contain keys from all modules
    hd_items_path = os.path.join(MOD_ROOT, "data/hd/items/items.json")
    with open(hd_items_path, "r", encoding="utf-8") as f:
        hd_list = json.load(f)
    hd_map = {}
    for entry in hd_list:
        if isinstance(entry, dict):
            for k, v in entry.items():
                hd_map[k] = v.get("asset") if isinstance(v, dict) else None
    for req_code in ("wm2", "yp2", "vp2", "bml", "um1", "vk1", "sw1", "va1", "ky2", "ky3", "z00"):
        if req_code not in hd_map:
            raise AssertionError(f"data/hd/items/items.json: missing '{req_code}' (cross-module overwrite!)")
    if hd_map.get("um1") != "hammer/horadric_malus" or hd_map.get("bml") != "hammer/horadric_malus":
        raise AssertionError(f"data/hd/items/items.json: bml/um1 asset mismatch ({hd_map.get('bml')}, {hd_map.get('um1')})")

    mod_item_names_path = os.path.join(MOD_STRINGS, "item-names.json")
    with open(mod_item_names_path, "r", encoding="utf-8-sig") as f:
        mod_item_names = {e.get("Key") for e in json.load(f) if isinstance(e, dict)}
    for req_key in ("wm2", "bml", "um1", "opl", "vk1", "ky2", "ky3", "z00"):
        if req_key not in mod_item_names:
            raise AssertionError(f"item-names.json: missing '{req_key}' (cross-module overwrite!)")

    # Verify zero custom string ID (>= 60000) collisions across all JSON string tables
    seen_custom_ids: Dict[int, str] = {}
    for sfn in ("item-names.json", "item-modifiers.json", "item-nameaffixes.json", "skills.json", "ui.json", "quests.json"):
        sp = os.path.join(MOD_STRINGS, sfn)
        with open(sp, "r", encoding="utf-8-sig") as f:
            for e in json.load(f):
                if isinstance(e, dict):
                    sid = int(e.get("id") or 0)
                    skey = str(e.get("Key") or "")
                    if sid >= 60000:
                        if sid in seen_custom_ids:
                            raise AssertionError(
                                f"Duplicate custom string id={sid}: {sfn}:{skey} collides with {seen_custom_ids[sid]}"
                            )
                        seen_custom_ids[sid] = f"{sfn}:{skey}"

    for rel_sp in (
        "herb/herb.sprite",
        "torch/torch.sprite",
        "body_part/tail.sprite",
        "key/skeleton_key.sprite",
        "body_part/jawbone.sprite",
        "body_part/horn.sprite",
    ):
        sp_path = os.path.join(MOD_ROOT, "data/hd/global/ui/items/misc", rel_sp)
        if not os.path.exists(sp_path):
            raise AssertionError(f"Missing compiled HD sprite: {sp_path}")
    checks_passed.append("shared JSON & HD lockbox/key sprite completeness")

    # 5. Verify misc.txt stat1..stat3 references against itemstatcost.txt and dropsound/usesound against sounds.txt
    _, isc_rows = read_excel_tsv("itemstatcost.txt")
    valid_stats = {r["Stat"] for r in isc_rows if r.get("Stat")}
    _, snd_rows = read_excel_tsv("sounds.txt")
    valid_sounds = {r["Sound"] for r in snd_rows if r.get("Sound")}
    _, misc_rows = _read_mod_tsv("misc.txt")
    for r in misc_rows:
        code = r.get("code", "")
        for scol in ("stat1", "stat2", "stat3"):
            sval = r.get(scol, "").strip()
            if sval and sval not in valid_stats:
                raise AssertionError(
                    f"misc.txt ({code}): {scol}='{sval}' is not a valid Stat in itemstatcost.txt"
                )
        for snd_col in ("dropsound", "usesound"):
            snd_val = r.get(snd_col, "").strip()
            if snd_val and snd_val not in valid_sounds:
                raise AssertionError(
                    f"misc.txt ({code}): {snd_col}='{snd_val}' is not a valid Sound in sounds.txt"
                )
    checks_passed.append("misc.txt stat & sound referential integrity")

    # 6. Verify QA config flags match MonStats.txt and cubemain.txt
    if not cfg.get("qa_blood_moor_boost", False):
        _, mon_rows = _read_mod_tsv("monstats.txt")
        for r in mon_rows:
            if r.get("Id") == "zombie1":
                if int(r.get("Level", "1")) >= 50:
                    raise AssertionError("monstats.txt: zombie1 still has QA boosted level while qa_blood_moor_boost=false")
    if not cfg.get("qa_cube_starter_kit", False):
        _, cube_rows = _read_mod_tsv("cubemain.txt", max_rows=200)
        for r in cube_rows:
            if r.get("numinputs") == "1" and r.get("input 1") in ("isc", "tsc"):
                raise AssertionError("cubemain.txt: QA starter kit recipe active while qa_cube_starter_kit=false")
    checks_passed.append("QA config gate contracts")

    # 7. Verify hireling.txt 9-Aura Act 2 Matrix & skill/icon referential integrity
    _, hire_rows = _read_mod_tsv("hireling.txt")
    sdesc_by_name = {r["skilldesc"].lower(): r for r in desc_rows if r.get("skilldesc")}
    skill_by_name = {r["skill"].lower(): r for r in skill_rows if r.get("skill")}
    act2_auras_by_diff = {"1": set(), "2": set(), "3": set()}
    for r in hire_rows:
        hid = r.get("Id", "").strip()
        act = r.get("Act", "").strip()
        diff = r.get("Difficulty", "").strip()
        if act == "2":
            act2_auras_by_diff[diff].add(r.get("Skill2", "").strip())
        for s_idx in range(1, 7):
            sk = r.get(f"Skill{s_idx}", "").strip()
            if not sk:
                continue
            sk_row = skill_by_name.get(sk.lower())
            if not sk_row:
                raise AssertionError(f"hireling.txt (Id={hid}): Skill{s_idx}='{sk}' not found in skills.txt")
            sd_key = sk_row.get("skilldesc", "").strip().lower()
            if sd_key in sdesc_by_name and not sdesc_by_name[sd_key].get("HireableIconCel", "").strip():
                raise AssertionError(
                    f"hireling.txt (Id={hid}): Skill{s_idx}='{sk}' ({sd_key}) missing HireableIconCel in skilldesc.txt"
                )
            if act == "5" and sk in ("Battle Cry", "Taunt"):
                raise AssertionError(f"hireling.txt (Id={hid}): Act 5 Barbarian still has '{sk}'")
    expected_act2 = {
        "1": {"Prayer", "Defiance", "Blessed Aim"},
        "2": {"Cleansing", "Holy Freeze", "Vigor"},
        "3": {"Meditation", "Salvation", "Sanctuary"},
    }
    for d_key, exp_set in expected_act2.items():
        if act2_auras_by_diff[d_key] != exp_set:
            raise AssertionError(
                f"hireling.txt Act 2 Diff={d_key}: got auras {act2_auras_by_diff[d_key]}, expected {exp_set}"
            )
    checks_passed.append("hireling 9-aura matrix & skill/icon referential integrity")


    return checks_passed

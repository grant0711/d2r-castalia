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

    # 2. Verify treasureclassex.txt zero-potion & zero-base-charm drop contract
    _, tc_rows = _read_mod_tsv("treasureclassex.txt")
    forbidden_potions = {
        "hp1", "hp2", "hp3", "hp4", "hp5",
        "mp1", "mp2", "mp3", "mp4", "mp5",
        "rvs", "rvl", "vps", "yps", "wms",
        "vp2", "vp3", "yp2", "yp3", "wm2", "wm3",
        "cm1", "cm2", "cm3", "cs2",
    }
    for r in tc_rows:
        tc_name = r.get("Treasure Class", "")
        for i in range(1, 11):
            it = r.get(f"Item{i}", "").strip()
            if it in forbidden_potions:
                raise AssertionError(
                    f"TreasureClassEx.txt ({tc_name}): forbidden potion/charm base '{it}' in Item{i}"
                )
    checks_passed.append("TreasureClassEx zero-potion & zero-base-charm contract")

    # 3. Verify weapons.txt melee reach, javelin reach tiers, and throwing weapon properties
    _, weap_rows = _read_mod_tsv("weapons.txt")
    ranged_only_types = {"bow", "abow", "xbow", "tpot"}
    for r in weap_rows:
        code = r.get("code", "")
        wtype = r.get("type", "")
        if not code or not wtype or r.get("spawnable") != "1":
            continue
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
    checks_passed.append("weapons melee/javelin rangeadder & throwing contracts")

    # 4. Verify shared JSON files (items.json and item-names.json) contain keys from all modules
    hd_items_path = os.path.join(MOD_ROOT, "data/hd/items/items.json")
    with open(hd_items_path, "r", encoding="utf-8") as f:
        hd_list = json.load(f)
    hd_codes = set()
    for entry in hd_list:
        if isinstance(entry, dict):
            hd_codes.update(entry.keys())
    for req_code in ("wm2", "yp2", "vp2", "bml", "vk1", "sw1", "va1"):
        if req_code not in hd_codes:
            raise AssertionError(f"data/hd/items/items.json: missing '{req_code}' (cross-module overwrite!)")

    mod_item_names_path = os.path.join(MOD_STRINGS, "item-names.json")
    with open(mod_item_names_path, "r", encoding="utf-8-sig") as f:
        mod_item_names = {e.get("Key") for e in json.load(f) if isinstance(e, dict)}
    for req_key in ("wm2", "bml", "opl", "vk1"):
        if req_key not in mod_item_names:
            raise AssertionError(f"item-names.json: missing '{req_key}' (cross-module overwrite!)")
    checks_passed.append("shared JSON cross-module completeness")

    # 5. Verify misc.txt stat1..stat3 references against itemstatcost.txt
    _, isc_rows = read_excel_tsv("itemstatcost.txt")
    valid_stats = {r["Stat"] for r in isc_rows if r.get("Stat")}
    _, misc_rows = _read_mod_tsv("misc.txt")
    for r in misc_rows:
        code = r.get("code", "")
        for scol in ("stat1", "stat2", "stat3"):
            sval = r.get(scol, "").strip()
            if sval and sval not in valid_stats:
                raise AssertionError(
                    f"misc.txt ({code}): {scol}='{sval}' is not a valid Stat in itemstatcost.txt"
                )
    checks_passed.append("misc.txt stat1..stat3 itemstatcost referential integrity")

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

    return checks_passed

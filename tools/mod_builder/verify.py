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
    read_strings_json,
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

    # Verify missiles.txt sub-missile cross-references & conditional stun/overlay contracts
    missiles_by_name = {r["Missile"]: r for r in missile_rows if r.get("Missile")}
    for mr in missile_rows:
        mname = mr.get("Missile", "")
        if not mname:
            continue
        for sm_col in (
            "ExplosionMissile",
            "SubMissile1", "SubMissile2", "SubMissile3",
            "HitSubMissile1", "HitSubMissile2", "HitSubMissile3", "HitSubMissile4",
            "CltSubMissile1", "CltSubMissile2", "CltSubMissile3",
            "CltHitSubMissile1", "CltHitSubMissile2", "CltHitSubMissile3", "CltHitSubMissile4",
        ):
            sm_val = mr.get(sm_col, "").strip()
            if sm_val and sm_val not in missile_names:
                raise AssertionError(
                    f"missiles.txt ({mname}): {sm_col}='{sm_val}' missing from missiles.txt"
                )

    for no_stun_ms in ("vampirefireball", "sucfireball", "bladefury3", "bladefragment3"):
        ms_row = missiles_by_name.get(no_stun_ms, {})
        if ms_row.get("pSrvDmgFunc") == "7" or ms_row.get("ProgOverlay"):
            raise AssertionError(
                f"missiles.txt ({no_stun_ms}): must not have unconditional pSrvDmgFunc='7' or ProgOverlay"
            )
        if ms_row.get("pSrvHitFunc") in ("21", "22"):
            raise AssertionError(
                f"missiles.txt ({no_stun_ms}): forbidden pSrvHitFunc='{ms_row.get('pSrvHitFunc')}' (breaks damage or causes infinite 0-charge stun)"
            )
    for stun_ms_name in ("sucfireballexplode",):
        sfe_row = missiles_by_name.get(stun_ms_name, {})
        if (
            sfe_row.get("pSrvDmgFunc") != "7"
            or sfe_row.get("InitSteps") != "0"
            or ">= 3" not in sfe_row.get("Range", "")
            or sfe_row.get("ProgOverlay") != ""
        ):
            raise AssertionError(
                f"missiles.txt ({stun_ms_name}): Charge-3 micro-stun missile must have pSrvDmgFunc='7', InitSteps='0', Range gated by '>= 3', and ProgOverlay=''"
            )
    bf3_row = missiles_by_name.get("bladefragment3", {})
    if (
        bf3_row.get("pSrvDoFunc") != "1"
        or bf3_row.get("pSrvHitFunc") != ""
        or bf3_row.get("CollideKill") != "1"
        or bf3_row.get("SrcDamage") != "128"
        or bf3_row.get("CelFile") != "Expansion\\bladefury_C"
    ):
        raise AssertionError(
            "missiles.txt (bladefragment3): Shrapnel Sentry missile must be straight-line Blade Fury star (CollideKill='1', SrcDamage='128', CelFile='Expansion\\bladefury_C')"
        )

    # Verify pettype.txt dedicated trap types & srvstfunc='39' charge-consumption invariants
    _, pet_rows = _read_mod_tsv("pettype.txt")
    pet_by_type = {r.get("pet type", ""): r for r in pet_rows if r.get("pet type")}
    for req_pt in ("phystrap", "firetrap", "ltngtrap", "miasmatrap", "deathtrap", "bladesentinel"):
        if req_pt not in pet_by_type or pet_by_type[req_pt].get("partysend") != "1":
            raise AssertionError(
                f"pettype.txt: missing dedicated trap pettype '{req_pt}' with partysend='1'"
            )

    skills_by_name = {r["skill"]: r for r in skill_rows if r.get("skill")}
    for r in skill_rows:
        sname = r.get("skill", "")
        if r.get("srvstfunc") == "39" and r.get("aurastate", "").startswith("progressive_"):
            if r.get("calc2", "").strip() != "" or r.get("auralencalc", "").strip() != "12":
                raise AssertionError(
                    f"skills.txt ({sname}): srvstfunc='39' charge consumer must have calc2='' and auralencalc='12' so charges expire on cast"
                )
    wof_sk = skills_by_name.get("Wake of Fire Sentry", {})
    if (
        wof_sk.get("pettype") != "firetrap"
        or ">= 10" not in wof_sk.get("petmax", "")
        or ">= 25" not in wof_sk.get("petmax", "")
        or wof_sk.get("aurastate") != "progressive_fire"
        or wof_sk.get("sumskill1") != "Wake Of Destruction Sentry"
        or wof_sk.get("sumskill2") != "Wake of Fire Sentry"
        or wof_sk.get("sumskill3") != "Fists of Fire"
        or wof_sk.get("sumskill4") != "Fire Trauma"
        or wof_sk.get("sumskill5") != "Ass Trap Charge Consume"
    ):
        raise AssertionError(
            "skills.txt (Wake of Fire Sentry): trap synergy petmax (1->2->3), progressive_fire charge consumption, or sumskill1..5 contract violated"
        )
    ft_sk = skills_by_name.get("Fire Trauma", {})
    if (
        ft_sk.get("pettype") != "phystrap"
        or ft_sk.get("summon") != "infernosentry"
        or ">= 10" not in ft_sk.get("petmax", "")
        or ">= 25" not in ft_sk.get("petmax", "")
        or ft_sk.get("aurastate") != "progressive_damage"
        or ft_sk.get("sumskill1") != "mon inferno sentry"
        or ft_sk.get("sumskill2") != "Fire Trauma"
        or ft_sk.get("sumskill3") != "Tiger Strike"
        or ft_sk.get("sumskill4") != "Shock Field"
        or ft_sk.get("sumskill5") != "Ass Trap Charge Consume"
    ):
        raise AssertionError(
            "skills.txt (Fire Trauma / Shrapnel Sentry): trap synergy petmax (1->2->3), progressive_damage charge consumption, or sumskill1..5 contract violated"
        )
    ts_sk = skills_by_name.get("Tiger Strike", {})
    if (
        ts_sk.get("passivestate") != ""
        or ts_sk.get("aurastat2") != "damagepercent"
        or ts_sk.get("aurastatcalc2") != "clc1"
    ):
        raise AssertionError(
            "skills.txt (Tiger Strike): must grant per-orb melee Enhanced Damage % directly inside progressive_damage via aurastat2='damagepercent' and passivestate=''"
        )
    for cu_name in ("Tiger Strike", "Fists of Fire", "Cobra Strike", "Claws of Thunder", "Blades of Ice"):
        cu_sk = skills_by_name.get(cu_name, {})
        if (
            cu_sk.get("srvstfunc") != "23"
            or cu_sk.get("srvdofunc") != "34"
            or cu_sk.get("weapsel") != ""
            or cu_sk.get("itypea1") != "mele"
            or cu_sk.get("anim") != "A1"
            or cu_sk.get("seqtrans") != "A1"
            or cu_sk.get("seqnum") != ""
        ):
            raise AssertionError(
                f"skills.txt ({cu_name}): Charge-Up must use anim='A1', seqtrans='A1', seqnum='', weapsel='', srvdofunc='34', itypea1='mele'"
            )
    fof_sk = skills_by_name.get("Fists of Fire", {})
    if (
        fof_sk.get("passivestate") != "ass_fof_passive"
        or fof_sk.get("passivestat1") != "item_absorb_slash"
        or fof_sk.get("passivecalc1") != "1"
        or fof_sk.get("aurastat2") != "item_slash_damage"
        or fof_sk.get("aurastatcalc2") != "clc3"
    ):
        raise AssertionError(
            "skills.txt (Fists of Fire): must grant per-orb firemindam/firemaxdam (clc3) inside progressive_fire via aurastat2='item_slash_damage' (op=2 on item_absorb_slash=1)"
        )
    wods_sk = skills_by_name.get("Wake Of Destruction Sentry", {})
    if (
        wods_sk.get("srvdofunc") != ""
        or wods_sk.get("cltdofunc") != ""
        or wods_sk.get("srvmissile") != "vampirefireball"
        or wods_sk.get("cltmissile") != "vampirefireball"
    ):
        raise AssertionError(
            "skills.txt (Wake Of Destruction Sentry): must fire straight-line vampirefireball with srvdofunc='' and cltdofunc=''"
        )
    ft_sk = skills_by_name.get("Fire Trauma", {})
    mis_sk = skills_by_name.get("mon inferno sentry", {})
    if (
        ft_sk.get("passivestat2") != "item_openwounds"
        or mis_sk.get("srvmissile") != "bladefragment3"
        or mis_sk.get("cltmissile") != "bladefragment3"
    ):
        raise AssertionError(
            "skills.txt (Fire Trauma / mon inferno sentry): must fire straight-line bladefragment3 with 100% Open Wounds at 3 Tiger Strike charges"
        )
    checks_passed.append("skills/states/missiles/skilldesc referential & rollback bounds")

    # 2. Verify treasureclassex.txt & objects.txt drop/chest/lockbox contracts
    _, tc_rows = _read_mod_tsv("treasureclassex.txt")
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
        is_duriel_tc = tc_name.startswith("Duriel")
        has_lockbox = False
        tsc_count = 0
        for i in range(1, 11):
            it = r.get(f"Item{i}", "").strip()
            if it in globally_forbidden_tc_items:
                raise AssertionError(
                    f"TreasureClassEx.txt ({tc_name}): globally forbidden item '{it}' in Item{i}"
                )
            if it == "tsc":
                if not is_duriel_tc:
                    raise AssertionError(
                        f"TreasureClassEx.txt ({tc_name}): Scroll of Town Portal ('tsc') is only allowed on Duriel TCs"
                    )
                if r.get(f"Prob{i}", "").strip() != "1":
                    raise AssertionError(
                        f"TreasureClassEx.txt ({tc_name}): Duriel 'tsc' must have Prob='1'"
                    )
                tsc_count += 1
            if not is_chest_tc and it in monster_forbidden_potions:
                raise AssertionError(
                    f"TreasureClassEx.txt ({tc_name}): forbidden potion '{it}' in monster TC Item{i}"
                )
            if is_chest_tc:
                if any(bad in it for bad in ("Equip", "Weap", "Armo", "Melee", "Bow", "Junk")):
                    raise AssertionError(
                        f"TreasureClassEx.txt ({tc_name}): forbidden equipment/junk '{it}' in Chest Item{i}"
                    )
                if "Lockbox" in it or "Chest Roll" in it or "Chest Pair" in it:
                    has_lockbox = True
        if is_chest_tc and not has_lockbox:
            raise AssertionError(f"TreasureClassEx.txt ({tc_name}): Chest TC missing Lockbox entry")
        if is_duriel_tc and r.get("Picks") == "-6" and tsc_count != 1:
            raise AssertionError(f"TreasureClassEx.txt ({tc_name}): Duriel TC must drop 1 and only 1 'tsc'")
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
        if r.get("Class") in ("LargeChestR", "TombChest1", "SewerChestLargeLeft", "ArcaneChest1", "WoodChestL"):
            if r.get("OperateFn") != "4" or r.get("InitFn") != "3" or r.get("Damage") != "100":
                raise AssertionError(
                    f"objects.txt ({r.get('Class')}): expected OperateFn=4, InitFn=3, Damage=100 for trapped chests"
                )
        if r.get("OperateFn") == "22":
            if r.get("Parm0") != "250" or r.get("Parm1") != "256":
                raise AssertionError(
                    f"objects.txt (Well ID={r.get('*ID')}): expected Parm0='250' (10s) and Parm1='256' (100% refill)"
                )
        if r.get("OperateFn") == "2" and r.get("InitFn") == "1":
            if r.get("Parm0") not in ("1", "2"):
                raise AssertionError(
                    f"objects.txt (Shrine ID={r.get('*ID')}): Parm0='{r.get('Parm0')}' must be '1' (Health) or '2' (Mana)"
                )
    _, shrine_rows = _read_mod_tsv("shrines.txt")
    for sr in shrine_rows:
        scode = sr.get("Code", "").strip()
        if not scode or scode == "0":
            continue
        if scode in ("1", "2", "3", "13"):
            if sr.get("LevelMin") != "1" or sr.get("reset time in minutes") != "1":
                raise AssertionError(
                    f"shrines.txt (Code={scode}): recovery shrine must have LevelMin='1' and reset time in minutes='1'"
                )
        else:
            if sr.get("LevelMin") != "120":
                raise AssertionError(
                    f"shrines.txt (Code={scode}): non-recovery shrine must be disabled via LevelMin='120'"
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
    _, van_weap_rows = read_excel_tsv("weapons.txt")
    van_weap_by_code = {r["code"]: r for r in van_weap_rows if r.get("code")}
    _, weap_rows = _read_mod_tsv("weapons.txt")
    _, arm_rows = _read_mod_tsv("armor.txt")
    _, npc_rows = _read_mod_tsv("npc.txt")
    for nr in npc_rows:
        if nr.get("rep mult") != "768":
            raise AssertionError(f"npc.txt ({nr.get('npc')}): expected rep mult='768', got '{nr.get('rep mult')}'")
    _, mod_isc_rows = _read_mod_tsv("itemstatcost.txt")
    isc_by_stat = {r.get("Stat", ""): r for r in mod_isc_rows if r.get("Stat")}
    isc_charged = isc_by_stat.get("item_charged_skill")
    if not isc_charged or isc_charged.get("Multiply") != "1" or isc_charged.get("Add") != "10":
        raise AssertionError("itemstatcost.txt (item_charged_skill): expected Multiply='1', Add='10' for cheap charge refills")
    for zero_st in (
        "armorclass", "mindamage", "maxdamage", "secondary_mindamage",
        "secondary_maxdamage", "item_throw_mindamage", "item_throw_maxdamage", "maxdurability",
    ):
        zr = isc_by_stat.get(zero_st)
        if not zr or zr.get("Multiply") != "0" or zr.get("Add") != "0":
            raise AssertionError(
                f"itemstatcost.txt ({zero_st}): expected Multiply='0', Add='0' so base stats and op=13 %ED never double-count"
            )
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
                or r.get("PermStoreItem") != "1"
                or r.get("cost") != "100000"
            ):
                raise AssertionError(
                    "weapons.txt (um1): Untempered Malus must have CharsiMin=1, CharsiMax=1, PermStoreItem=1, cost=100000"
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
        vw = van_weap_by_code.get(code)
        if vw and r.get("nodurability") != "1" and int(vw.get("durability") or "0") > 0:
            exp_dur = min(255, int(vw["durability"]) * 2)
            if int(r.get("durability") or "0") != exp_dur:
                raise AssertionError(
                    f"weapons.txt ({code}): expected 2x durability={exp_dur}, got {r.get('durability')}"
                )
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
            if len(stocked_vendors) != 1:
                raise AssertionError(
                    f"weapons.txt ({code}): Normal base weapon must be stocked at exactly 1 exclusive vendor, found {stocked_vendors}"
                )
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
        for dcol in ("mindam", "maxdam", "2handmindam", "2handmaxdam", "minmisdam", "maxmisdam"):
            dval = r.get(dcol, "")
            if dval and int(dval) > 255:
                raise AssertionError(
                    f"weapons.txt ({code}, {r.get('name')}): {dcol}={dval} exceeds engine uint8_t limit (255) and will integer-rollover!"
                )
        expected_weap_ap = {
            "staf": "310",
            "wand": "311",
            "scep": "312",
            "orb": "303",
            "h2h": "315",
            "h2h2": "315",
            "aspe": "302",
            "ajav": "308",
        }
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
        expected_belts = {
            "lbl": ("2", "0"), "zlb": ("2", "20"), "ulc": ("2", "50"),
            "vbl": ("2", "0"), "zvb": ("2", "20"), "uvc": ("2", "50"),
            "mbl": ("1", "35"), "zmb": ("1", "65"), "umc": ("1", "106"),
            "tbl": ("1", "50"), "ztb": ("1", "88"), "utc": ("1", "145"),
            "hbl": ("0", "100"), "zhb": ("0", "140"), "uhc": ("0", "185"),
        }
        if code in expected_belts:
            exp_b, exp_s = expected_belts[code]
            if r.get("belt") != exp_b or r.get("reqstr") != exp_s:
                raise AssertionError(
                    f"armor.txt ({code}): expected belt='{exp_b}', reqstr='{exp_s}', got belt='{r.get('belt')}', reqstr='{r.get('reqstr')}'"
                )
        acost = int(r.get("cost") or "0")
        if acost < 50 or acost > 50000:
            raise AssertionError(
                f"armor.txt ({code}): normalized base cost={acost} out of expected 50..50000 range"
            )
        if code == "ci0":
            if r.get("NightmareUpgrade") != "ci1" or r.get("HellUpgrade") != "ci2":
                raise AssertionError("armor.txt (ci0): expected NightmareUpgrade=ci1, HellUpgrade=ci2")
        elif code == "ci1":
            if r.get("NightmareUpgrade") != "ci2" or r.get("HellUpgrade") != "ci3":
                raise AssertionError("armor.txt (ci1): expected NightmareUpgrade=ci2, HellUpgrade=ci3")

    # Verify automagic.txt staffmod groups (303, 305, 310..315) against skills.txt reqlevel tiers (1, 8, 16, 24, 32, 40)
    _, auto_rows = _read_mod_tsv("automagic.txt")
    _, sk_rows_for_auto = _read_mod_tsv("skills.txt")
    sk_req_by_id = {int(r["*Id"]): (r.get("charclass", ""), int(r.get("reqlevel") or "0"), r["skill"]) for r in sk_rows_for_auto if r.get("*Id")}
    grp_to_cls = {"303": "sor", "305": "nec", "310": "sor", "311": "nec", "312": "pal", "313": "bar", "314": "dru", "315": "ass"}
    bracket_to_reqcap = {("1", "7"): 1, ("8", "13"): 8, ("14", "20"): 16, ("21", "28"): 24, ("29", "36"): 32, ("37", ""): 40}
    seen_by_grp_bracket = {(g, b): set() for g in grp_to_cls for b in bracket_to_reqcap}

    for r in auto_rows:
        grp = r.get("group", "")
        if grp not in grp_to_cls:
            continue
        cls_code = grp_to_cls[grp]
        bkey = (r.get("level", ""), r.get("maxlevel", ""))
        if bkey not in bracket_to_reqcap:
            raise AssertionError(f"automagic.txt (group={grp}): unexpected ilvl bracket {bkey}")
        req_cap = bracket_to_reqcap[bkey]
        row_ranges = []
        for idx in (1, 2, 3):
            if r.get(f"mod{idx}code") == "skill-rand":
                lo = int(r[f"mod{idx}min"])
                hi = int(r[f"mod{idx}max"])
                if lo > hi:
                    raise AssertionError(f"automagic.txt (group={grp}): lo={lo} > hi={hi}")
                for prev_lo, prev_hi in row_ranges:
                    if not (hi < prev_lo or lo > prev_hi):
                        raise AssertionError(
                            f"automagic.txt (group={grp}, bracket={bkey}): overlapping skill-rand ranges [{lo},{hi}] and [{prev_lo},{prev_hi}]"
                        )
                row_ranges.append((lo, hi))
                for sid in range(lo, hi + 1):
                    s_cls, s_req, s_name = sk_req_by_id.get(sid, ("", 999, "?"))
                    if s_cls != cls_code or s_req > req_cap:
                        raise AssertionError(
                            f"automagic.txt (group={grp}, bracket={bkey}, req_cap={req_cap}): leaked skill {sid} ({s_name}, class={s_cls}, reqlevel={s_req})"
                        )
                    seen_by_grp_bracket[(grp, bkey)].add(sid)

    for (grp, bkey), seen_ids in seen_by_grp_bracket.items():
        cls_code = grp_to_cls[grp]
        req_cap = bracket_to_reqcap[bkey]
        expected_ids = {sid for sid, (c, rq, _) in sk_req_by_id.items() if c == cls_code and rq <= req_cap}
        if seen_ids != expected_ids:
            missing = sorted(expected_ids - seen_ids)
            raise AssertionError(
                f"automagic.txt (group={grp}, bracket={bkey}, req_cap={req_cap}): missing unlocked skills {missing}"
            )
        elif code == "ci2":
            if r.get("NightmareUpgrade") != "xxx" or r.get("HellUpgrade") != "ci3":
                raise AssertionError("armor.txt (ci2): expected NightmareUpgrade=xxx, HellUpgrade=ci3")
        elif code == r.get("normcode"):
            exp_nm = r.get("ubercode") if r.get("ubercode") != code else "xxx"
            exp_hell = r.get("ultracode") if r.get("ultracode") != code else "xxx"
            if r.get("NightmareUpgrade") != exp_nm or r.get("HellUpgrade") != exp_hell:
                raise AssertionError(
                    f"armor.txt ({code}): expected NightmareUpgrade={exp_nm}, HellUpgrade={exp_hell}"
                )
            stocked_vendors = [vn for vn in vendor_names if int(r.get(f"{vn}MagicMax") or "0") >= 1]
            expected_v_count = 2 if code in ("bsh", "msk", "ltp") else 1
            if len(stocked_vendors) != expected_v_count:
                raise AssertionError(
                    f"armor.txt ({code}): expected {expected_v_count} vendor(s), found {stocked_vendors}"
                )
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

    # Verify zero existing vanilla keys in monsters.json are overwritten (prevents clobbering
    # rare item prefixes like GhoulRI or interactive objects like TrappDoor)
    van_mon_strings = {
        e["Key"]: e["enUS"]
        for e in read_strings_json("monsters.json")
        if isinstance(e, dict) and "Key" in e
    }
    with open(os.path.join(MOD_STRINGS, "monsters.json"), "r", encoding="utf-8-sig") as f:
        for e in json.load(f):
            if isinstance(e, dict) and "Key" in e:
                mk = e["Key"]
                if mk in van_mon_strings and e.get("enUS") != van_mon_strings[mk]:
                    raise AssertionError(
                        f"monsters.json: existing vanilla key {mk!r} was overwritten ({van_mon_strings[mk]!r} -> {e.get('enUS')!r})"
                    )

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
        "potion/elixir.sprite",
        "potion/healing_potion.sprite",
        "potion/full_healing_potion.sprite",
        "potion/mana_potion.sprite",
        "potion/full_mana_potion.sprite",
        "potion/rejuv_potion.sprite",
    ):
        sp_path = os.path.join(MOD_ROOT, "data/hd/global/ui/items/misc", rel_sp)
        if not os.path.exists(sp_path):
            raise AssertionError(f"Missing compiled HD sprite: {sp_path}")
    barb_sm_path = os.path.join(
        MOD_ROOT, "data/hd/character/player/barbarian/barbarian_state_machine.json"
    )
    if not os.path.exists(barb_sm_path):
        raise AssertionError(f"Missing Barbarian 3D state machine: {barb_sm_path}")
    with open(barb_sm_path, "r", encoding="utf-8") as f:
        barb_sm = json.load(f)
    barb_seq_states = {
        (s.get("modeId"), s.get("skillIndex"), s.get("stepIndex")): s
        for s in barb_sm.get("states", [])
    }
    for req_key in ((18, 139, 0), (18, 139, 1), (18, 107, 0), (18, 107, 1)):
        if req_key not in barb_seq_states:
            raise AssertionError(
                f"barbarian_state_machine.json missing Shield Charge sequence state {req_key}"
            )
    checks_passed.append("shared JSON & HD lockbox/key/elixir sprite completeness")

    # 5. Verify misc.txt stat1..stat3 references against itemstatcost.txt and dropsound/usesound against sounds.txt
    _, isc_rows = read_excel_tsv("itemstatcost.txt")
    valid_stats = {r["Stat"] for r in isc_rows if r.get("Stat")}
    _, snd_rows = read_excel_tsv("sounds.txt")
    valid_sounds = {r["Sound"] for r in snd_rows if r.get("Sound")}
    _, misc_rows = _read_mod_tsv("misc.txt")
    misc_by_code = {r.get("code", ""): r for r in misc_rows}
    for kcode in ("key", "ky0", "ky1", "ky2", "ky3"):
        if kcode not in misc_by_code:
            raise AssertionError(f"misc.txt missing lockbox/skeleton key row '{kcode}'")
        if misc_by_code[kcode].get("PermStoreItem") != "1":
            raise AssertionError(f"misc.txt ({kcode}): PermStoreItem must be '1' so Nightmare/Hell vendors stock keys at ilvl >= 25")
    for pcode in (
        "hp1", "hp2", "hp3", "hp4", "hp5", "h1a", "h1b", "h1c", "h1d", "h2b", "h2c", "h2d",
        "mp1", "mp2", "mp3", "mp4", "mp5", "m1a", "m1b", "m1c", "m1d", "m2b", "m2c", "m2d",
    ):
        if pcode not in misc_by_code:
            raise AssertionError(f"misc.txt missing potion/helper row '{pcode}'")
        if misc_by_code[pcode].get("PermStoreItem") != "1":
            raise AssertionError(f"misc.txt ({pcode}): PermStoreItem must be '1'")
        if pcode not in hd_map:
            raise AssertionError(f"data/hd/items/items.json missing potion/helper code '{pcode}'")
    for ecode in ("wms", "wm2", "wm3", "yps", "yp2", "yp3", "vps", "vp2", "vp3"):
        if misc_by_code.get(ecode, {}).get("autobelt") != "1":
            raise AssertionError(f"misc.txt ({ecode}): elixir must have autobelt='1'")
    for tp_code in ("tsc", "tbk"):
        tp_row = misc_by_code.get(tp_code, {})
        for vn in vendor_names:
            if tp_row.get(f"{vn}Min") or tp_row.get(f"{vn}Max"):
                raise AssertionError(f"misc.txt ({tp_code}): must not be sold at vendor {vn}")
    if misc_by_code.get("isc", {}).get("cost") != "250":
        raise AssertionError("misc.txt (isc): Scroll of Identify cost must be '250'")
    if misc_by_code.get("ibk", {}).get("maxstack") != "10" or misc_by_code.get("ibk", {}).get("cost") != "10000":
        raise AssertionError("misc.txt (ibk): Tome of Identify must have maxstack='10' and cost='10000'")
    _, book_rows = _read_mod_tsv("books.txt")
    for br in book_rows:
        if br.get("Name") == "Tome of Identify" and (br.get("CostPerCharge") != "250" or br.get("BaseCost") != "9750"):
            raise AssertionError("books.txt (Tome of Identify): must have BaseCost='9750' and CostPerCharge='250'")
    _, cstat_rows = _read_mod_tsv("charstats.txt")
    for cr in cstat_rows:
        for i in range(1, 11):
            if cr.get(f"item{i}", "").strip() == "tsc":
                raise AssertionError(f"charstats.txt ({cr.get('class')}): starting item{i} still has 'tsc'")
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

    # 6. Verify QA config flags, progressive aidist, monprop.txt, and monumod.txt contracts
    _, mon_rows = _read_mod_tsv("monstats.txt")
    _, mprop_rows = _read_mod_tsv("monprop.txt")
    _, prop_rows = read_excel_tsv("properties.txt")
    valid_props = {r["code"] for r in prop_rows if r.get("code")}
    mprop_ids = {r["Id"] for r in mprop_rows if r.get("Id")}
    for r in mprop_rows:
        mp_id = r.get("Id", "")
        for sfx in ("", " (N)", " (H)"):
            for idx in range(1, 7):
                pcode = r.get(f"prop{idx}{sfx}", "").strip()
                if pcode and pcode not in valid_props:
                    raise AssertionError(
                        f"monprop.txt ({mp_id}): prop{idx}{sfx}='{pcode}' not found in properties.txt"
                    )
    for r in mon_rows:
        mid = r.get("Id", "").strip()
        if mid == "zombie1" and not cfg.get("qa_blood_moor_boost", False):
            if int(r.get("Level", "1")) >= 50:
                raise AssertionError("monstats.txt: zombie1 still has QA boosted level while qa_blood_moor_boost=false")
        mp_ref = r.get("MonProp", "").strip()
        if mp_ref and mp_ref not in mprop_ids:
            raise AssertionError(f"monstats.txt ({mid}): MonProp='{mp_ref}' missing from monprop.txt")
        if mid in ("andariel", "duriel", "mephisto", "diablo", "baalcrab", "griswold", "smith", "radament", "izual", "hephasto"):
            ad_n = int(r.get("aidist") or "0")
            ad_nm = int(r.get("aidist(N)") or "0")
            ad_h = int(r.get("aidist(H)") or "0")
            if not (42 <= ad_n < ad_nm < ad_h):
                raise AssertionError(
                    f"monstats.txt ({mid}): expected progressive off-screen aidist (42 <= {ad_n} < {ad_nm} < {ad_h})"
                )
    from mod_builder.monsters import FAMILY_RESIST_PROFILES, FIXED_SKIP_ZONE_IDS, HEAVY_BRUTE_BASES
    _, van_mon_rows = read_excel_tsv("monstats.txt")
    van_mon_by_id = {r["Id"]: r for r in van_mon_rows if r.get("Id")}
    with open(os.path.join(MOD_STRINGS, "monsters.json"), "r", encoding="utf-8-sig") as f:
        mod_mon_strings = {e["Key"]: e for e in json.load(f) if isinstance(e, dict) and "Key" in e}
    for r in mon_rows:
        mid = r.get("Id", "").strip()
        if (
            r.get("isSpawn") != "1"
            or r.get("killable") != "1"
            or r.get("Align") != ""
            or r.get("boss") == "1"
            or r.get("primeevil") == "1"
            or int(r.get("Velocity") or "0") <= 0
        ):
            continue
        vr = van_mon_by_id.get(mid)
        if not vr:
            continue
        if r.get("BaseId", "").strip() in FAMILY_RESIST_PROFILES and mid not in ("cowking", "darkelder"):
            dstr_key = r.get("DescStr", "").strip()
            if not dstr_key or dstr_key not in mod_mon_strings or int(mod_mon_strings[dstr_key].get("id", 99999)) >= 23000:
                raise AssertionError(
                    f"monstats.txt ({mid}): DescStr='{dstr_key}' must be a valid .tbl-backed key (id < 23000) in monsters.json"
                )
        ad_n = int(r.get("aidist") or "0")
        ad_nm = int(r.get("aidist(N)") or "0")
        ad_h = int(r.get("aidist(H)") or "0")
        if not (38 <= ad_n < ad_nm < ad_h):
            raise AssertionError(
                f"monstats.txt ({mid}): aidist ({ad_n}/{ad_nm}/{ad_h}) must be >= 38 (above vanilla's 35-subtile default)"
            )
        if r.get("BaseId", "").strip() in HEAVY_BRUTE_BASES and mid not in ("cowking", "darkelder"):
            m_vel = int(r.get("Velocity") or "0")
            v_vel = int(vr.get("Velocity") or "0")
            if m_vel > v_vel:
                raise AssertionError(
                    f"monstats.txt ({mid}): Heavy Brute Velocity={m_vel} exceeds vanilla {v_vel}"
                )
            if r.get("BaseId", "").strip() == "zombie1" and (m_vel != 1 or int(r.get("Run") or "0") > 2):
                raise AssertionError(
                    f"monstats.txt ({mid}): Zombie must remain slow and clunky (Velocity=1, Run<=2)"
                )
        for gcol in ("MinGrp", "MaxGrp", "PartyMin", "PartyMax"):
            mv = int(r.get(gcol) or "0")
            vv = int(vr.get(gcol) or "0")
            if mv > vv:
                raise AssertionError(
                    f"monstats.txt ({mid}): {gcol}={mv} exceeds vanilla {vv} (group sizes must never exceed vanilla)"
                )
        for hcol in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            mh = int(r.get(hcol) or "0")
            vh = int(vr.get(hcol) or "0")
            if vh > 0 and mh <= vh:
                raise AssertionError(
                    f"monstats.txt ({mid}): {hcol}={mh} is not strictly greater than vanilla {vh}"
                )
        if int(r.get("Crit") or "0") < 10:
            raise AssertionError(f"monstats.txt ({mid}): Crit={r.get('Crit')} must be >= 10")
        for s_i in range(1, 9):
            v_sk = int(vr.get(f"Sk{s_i}lvl") or "0")
            m_sk = int(r.get(f"Sk{s_i}lvl") or "0")
            if v_sk > 0 and m_sk < v_sk + 2:
                raise AssertionError(
                    f"monstats.txt ({mid}): Sk{s_i}lvl={m_sk} was not boosted by >= +2 over vanilla {v_sk}"
                )

    from mod_builder.monsters import FIXED_SKIP_ZONE_IDS
    _, van_lvl_rows = read_excel_tsv("levels.txt")
    van_lvl_by_name = {r["Name"]: r for r in van_lvl_rows if r.get("Name")}
    _, mod_lvl_rows = _read_mod_tsv("levels.txt")
    mod_lvl_by_name = {r["Name"]: r for r in mod_lvl_rows if r.get("Name")}
    for r in mod_lvl_rows:
        lname = r.get("Name", "")
        zid = r.get("Id", "")
        if not lname or lname == "Expansion" or zid in FIXED_SKIP_ZONE_IDS:
            continue
        vr = van_lvl_by_name.get(lname)
        if not vr:
            continue
        for dcol in ("MonDen", "MonDen(N)", "MonDen(H)"):
            md = int(r.get(dcol) or "0")
            vd = int(vr.get(dcol) or "0")
            if lname == "Act 5 - Siege 1" and dcol == "MonDen":
                vd = int(vr.get("MonDen(N)") or "650")
            if md > vd:
                raise AssertionError(
                    f"levels.txt ({lname}): {dcol}={md} exceeds vanilla {vd} (zone density must never exceed vanilla)"
                )
        for ucol in ("MonUMin", "MonUMax", "MonUMin(N)", "MonUMax(N)", "MonUMin(H)", "MonUMax(H)"):
            mu = int(r.get(ucol) or "0")
            if mu > 1:
                raise AssertionError(f"levels.txt ({lname}): {ucol}={mu} must be <= 1")
        if lname.startswith("Act 5 -") and int(r.get("MonDen(N)") or "0") > 0:
            mons = [r.get(f"mon{i}", "") for i in range(1, 26) if r.get(f"mon{i}", "")]
            nmons = [r.get(f"nmon{i}", "") for i in range(1, 26) if r.get(f"nmon{i}", "")]
            if mons != nmons:
                raise AssertionError(f"levels.txt ({lname}): Act 5 mon={mons} != nmon={nmons} (Guest monsters still present)")
    if "willowisp1" not in {mod_lvl_by_name["Act 3 - Jungle 2"].get(f"mon{i}", "") for i in range(1, 26)}:
        raise AssertionError("levels.txt (Act 3 - Jungle 2 / Great Marsh): willowisp1 (Gloam) missing from monster roster")
    if int(mod_lvl_by_name["Act 1 - Crypt 2 A"].get("MonDen") or "0") < 260:
        raise AssertionError("levels.txt (Act 1 - Crypt 2 A / Mausoleum): MonDen decreased below 260")
    if mod_lvl_by_name["Act 1 - Wilderness 1"].get("MonDen") != str(int(round(int(van_lvl_by_name["Act 1 - Wilderness 1"]["MonDen"]) * 0.75))):
        raise AssertionError("levels.txt (Act 1 - Wilderness 1 / Blood Moor): expected Tier 2 (0.75x vanilla) MonDen")
    if mod_lvl_by_name["Act 3 - Jungle 3"].get("MonDen") != van_lvl_by_name["Act 3 - Jungle 3"]["MonDen"]:
        raise AssertionError("levels.txt (Act 3 - Jungle 3 / Flayer Jungle): expected Tier 1 (1.00x vanilla) MonDen")
    _, umod_rows = _read_mod_tsv("monumod.txt")
    umod_consts = {r.get("id", "").strip(): int(r.get("constants") or "0") for r in umod_rows if r.get("id")}
    if not (umod_consts.get("1", 0) < umod_consts.get("2", 0) < umod_consts.get("3", 0)):
        raise AssertionError("monumod.txt: Minion HP % bonus (id 1..3) must increase progressively across N < NM < H")
    if not (umod_consts.get("4", 0) < umod_consts.get("5", 0) < umod_consts.get("6", 0)):
        raise AssertionError("monumod.txt: Champion HP % bonus (id 4..6) must increase progressively across N < NM < H")
    if not (umod_consts.get("7", 0) < umod_consts.get("8", 0) < umod_consts.get("9", 0)):
        raise AssertionError("monumod.txt: Unique HP % bonus (id 7..9) must increase progressively across N < NM < H")
    if not cfg.get("qa_cube_starter_kit", False):
        from mod_builder.cubemain import BINARY_OR_SKILL_PROPS, DISTILL_AFFIX_CAPS, PER_LEVEL_PROPS
        _, cube_rows = _read_mod_tsv("cubemain.txt", max_rows=3000)
        distill_count = 0
        forbidden_distill_names = {
            "Amulet of the Viper", "Staff of Kings", "Horadric Staff",
            "Hell Forge Hammer", "KhalimFlail", "SuperKhalimFlail",
            "Rainbow Facet", "Gheed's Fortune", "Annihilus", "Hellfire Torch",
            "Signet of the Maiden", "Carapace of Pain", "Soulstone Shard", "Eye of Destruction",
            '"jew,uni"', '"cjw,uni"', '"cm1,uni"', '"cm2,uni"', '"cm3,uni"', '"cs2,uni"',
        }
        for r in cube_rows:
            if r.get("numinputs") == "1" and r.get("input 1") in ("isc", "tsc"):
                raise AssertionError("cubemain.txt: QA starter kit recipe active while qa_cube_starter_kit=false")
            desc = r.get("description", "")
            if desc.startswith("Distill "):
                distill_count += 1
                in1 = r.get("input 1", "").strip()
                if in1 in forbidden_distill_names:
                    raise AssertionError(f"cubemain.txt ({desc}): Quest item, Unique Jewel, or Unique Charm '{in1}' must not have a distillation recipe")
                if (
                    r.get("numinputs") != "3"
                    or r.get("input 2") != "bml"
                    or r.get("input 3") != '"jew,mag"'
                    or r.get("output") != '"jew,crf"'
                    or r.get("lvl") != "1"
                ):
                    raise AssertionError(
                        f"cubemain.txt ({desc}): expected numinputs=3, input 2=bml, input 3='\"jew,mag\"', output='\"jew,crf\"', lvl='1'"
                    )
                if "levelreq" not in (r.get(f"mod {i}", "") for i in range(1, 6)):
                    raise AssertionError(
                        f"cubemain.txt ({desc}): missing levelreq modifier"
                    )
                for m_i in range(1, 6):
                    mcode = r.get(f"mod {m_i}", "").strip()
                    if not mcode or mcode == "levelreq":
                        continue
                    if mcode in ("nofreeze", "cannotbefrozen"):
                        raise AssertionError(f"cubemain.txt ({desc}): forbidden {mcode} present on distilled jewel")
                    mch = r.get(f"mod {m_i} chance", "").strip()
                    mpar = r.get(f"mod {m_i} param", "").strip()
                    mmn = r.get(f"mod {m_i} min", "").strip()
                    mmx = r.get(f"mod {m_i} max", "").strip()
                    if mcode not in BINARY_OR_SKILL_PROPS:
                        if mch != "100":
                            raise AssertionError(f"cubemain.txt ({desc}): numeric mod {mcode} has chance={mch} != 100")
                        if mcode not in DISTILL_AFFIX_CAPS:
                            raise AssertionError(f"cubemain.txt ({desc}): mod {mcode} missing from DISTILL_AFFIX_CAPS")
                        c_min, c_max = DISTILL_AFFIX_CAPS[mcode]
                        if mcode in PER_LEVEL_PROPS:
                            v = int(mpar)
                            if not (c_min <= v <= c_max):
                                raise AssertionError(f"cubemain.txt ({desc}): {mcode} param={v} outside [{c_min}, {c_max}]")
                        else:
                            v_lo = int(mmn)
                            v_hi = int(mmx)
                            if not (c_min <= v_lo < v_hi <= c_max):
                                raise AssertionError(f"cubemain.txt ({desc}): {mcode} [{v_lo}, {v_hi}] must have variability (v_lo < v_hi) within [{c_min}, {c_max}]")
        if distill_count < 800:
            raise AssertionError(f"cubemain.txt: expected >= 800 distillation rows, found {distill_count}")
    for afx_fn in ("magicprefix.txt", "magicsuffix.txt"):
        _, afx_rows = _read_mod_tsv(afx_fn)
        for r in afx_rows:
            if r.get("spawnable") == "1" and "jewl" in {r.get(f"itype{i}", "").strip() for i in range(1, 8)}:
                if int(r.get("level") or "1") < 2:
                    raise AssertionError(
                        f"{afx_fn} ({r.get('Name')}): jewl affix has level < 2 (would pollute lvl=1 distilled Crafted Jewels)"
                    )
    checks_passed.append("QA config gates, progressive off-screen aidist, monprop, monumod & lvl=1 crafted jewel distillation contracts")

    # 7. Verify hireling.txt 9-Aura Act 2 Matrix, 3-Active-Skill UI cap, level/chance floors & HrSkillIcon sprite integrity
    _, hire_rows = _read_mod_tsv("hireling.txt")
    sdesc_by_name = {r["skilldesc"].lower(): r for r in desc_rows if r.get("skilldesc")}
    skill_by_name = {r["skill"].lower(): r for r in skill_rows if r.get("skill")}
    act2_auras_by_diff = {"1": set(), "2": set(), "3": set()}
    for r in hire_rows:
        hid = r.get("Id", "").strip()
        ver = r.get("Version", "").strip()
        act = r.get("Act", "").strip()
        diff = r.get("Difficulty", "").strip()
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
            if not sk_row:
                raise AssertionError(f"hireling.txt (Id={hid}): Skill{s_idx}='{sk}' not found in skills.txt")
            sd_key = sk_row.get("skilldesc", "").strip().lower()
            hic = sdesc_by_name.get(sd_key, {}).get("HireableIconCel", "").strip()
            if not hic or not hic.isdigit() or not (0 <= int(hic) <= 54):
                raise AssertionError(
                    f"hireling.txt (Id={hid}): Skill{s_idx}='{sk}' ({sd_key}) invalid HireableIconCel={hic!r} in skilldesc.txt"
                )
            if act == "5" and sk in ("Battle Cry", "Taunt"):
                raise AssertionError(f"hireling.txt (Id={hid}): Act 5 Barbarian still has '{sk}'")
            if act == "3" and md == "1":
                raise AssertionError(f"hireling.txt (Id={hid}): Act 3 Iron Wolf has unsupported Mode=1 Aura '{sk}'")
            if ver == "100":
                if slvl < 4:
                    raise AssertionError(f"hireling.txt (Id={hid}): Skill{s_idx}='{sk}' has Level{s_idx}={slvl} < 4")
                if md != "5":
                    active_count += 1
                    if s_idx > 3:
                        raise AssertionError(
                            f"hireling.txt (Id={hid}): Active/Aura Skill{s_idx}='{sk}' (Mode={md}) is outside UI slots Skill1..3"
                        )
                    if ch < 15:
                        raise AssertionError(
                            f"hireling.txt (Id={hid}): Active/Aura Skill{s_idx}='{sk}' has Chance{s_idx}={ch} < 15"
                        )
        if ver == "100" and active_count > 3:
            raise AssertionError(f"hireling.txt (Id={hid}): has {active_count} > 3 active/aura skills")
    expected_act2 = {
        "1": {"Thorns", "Defiance", "Blessed Aim"},
        "2": {"Cleansing", "Holy Freeze", "Vigor"},
        "3": {"Meditation", "Salvation", "Sanctuary"},
    }
    for d_key, exp_set in expected_act2.items():
        if act2_auras_by_diff[d_key] != exp_set:
            raise AssertionError(
                f"hireling.txt Act 2 Diff={d_key}: got auras {act2_auras_by_diff[d_key]}, expected {exp_set}"
            )
    for spr_rel, exp_len in (
        ("data/hd/global/ui/spells/hireables/hrskillicon.sprite", 40 + 55 * 132 * 130 * 4),
        ("data/hd/global/ui/spells/hireables/hrskillicon.lowend.sprite", 40 + 55 * 67 * 65 * 4),
    ):
        spr_path = os.path.join(MOD_ROOT, spr_rel)
        if not os.path.exists(spr_path) or os.path.getsize(spr_path) != exp_len:
            raise AssertionError(f"Missing or invalid size for expanded {spr_rel}")
    checks_passed.append("hireling 9-aura matrix, 3-active-skill UI cap & expanded HrSkillIcon sprite integrity")

    # 8. Verify uniqueitems.txt, setitems.txt, sets.txt locked table parity & zero duplicate added oskills/auras
    locked_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locked_tables")
    for lfn in ("uniqueitems.txt", "setitems.txt", "sets.txt"):
        lpath = os.path.join(locked_dir, lfn)
        mpath = os.path.join(MOD_EXCEL, lfn)
        if not os.path.exists(lpath):
            raise AssertionError(f"locked_tables/{lfn} is missing; unique/set tables must be locked in source control")
        with open(lpath, "rb") as f1, open(mpath, "rb") as f2:
            if f1.read() != f2.read():
                raise AssertionError(f"MOD_EXCEL/{lfn} diverges from locked_tables/{lfn}")

    _, van_u_rows = read_excel_tsv("uniqueitems.txt")
    van_u_by_idx = {r["index"]: r for r in van_u_rows if r.get("index")}
    _, mod_u_rows = _read_mod_tsv("uniqueitems.txt")
    skill_by_id = {r["*Id"]: r for r in skill_rows if r.get("*Id")}
    weap_type_by_code = {r["code"]: r.get("type", "") for r in weap_rows if r.get("code")}
    arm_type_by_code = {r["code"]: r.get("type", "") for r in arm_rows if r.get("code")}

    def _slot_bucket(code: str) -> str:
        if code in weap_type_by_code:
            return "weapon"
        if code in arm_type_by_code:
            return arm_type_by_code[code]
        return code

    seen_added_oskills: Dict[str, str] = {}
    seen_added_auras_by_slot: Dict[Tuple[str, str], str] = {}

    for r in mod_u_rows:
        if r.get("spawnable") != "1" or r.get("disabled") == "1":
            continue
        idx = r.get("index", "")
        code = r.get("code", "")
        sb = _slot_bucket(code)
        van_r = van_u_by_idx.get(idx)
        van_props = {van_r.get(f"prop{i}", "").strip() for i in range(1, 13)} if van_r else set()
        for i in range(1, 13):
            p = r.get(f"prop{i}", "").strip()
            par = r.get(f"par{i}", "").strip()
            if p == "nofreeze":
                raise AssertionError(f"uniqueitems.txt ({idx}): forbidden nofreeze still present")
            if p == "oskill" and "oskill" not in van_props:
                if par.lower() not in skill_by_name:
                    raise AssertionError(f"uniqueitems.txt ({idx}): invalid oskill '{par}'")
                if skill_by_name[par.lower()].get("aura") == "1":
                    raise AssertionError(f"uniqueitems.txt ({idx}): oskill '{par}' is a Paladin aura (use aura prop instead)")
                if par in seen_added_oskills:
                    raise AssertionError(
                        f"uniqueitems.txt ({idx}): duplicate added oskill '{par}' (already on {seen_added_oskills[par]})"
                    )
                seen_added_oskills[par] = idx
            elif p == "aura" and "aura" not in van_props:
                arow = skill_by_id.get(par) or skill_by_name.get(par.lower())
                if not arow or arow.get("aura") != "1":
                    raise AssertionError(f"uniqueitems.txt ({idx}): invalid aura reference '{par}'")
                if (sb, par) in seen_added_auras_by_slot:
                    raise AssertionError(
                        f"uniqueitems.txt ({idx}): duplicate added aura '{par}' in slot '{sb}' (already on {seen_added_auras_by_slot[(sb, par)]})"
                    )
                seen_added_auras_by_slot[(sb, par)] = idx
    checks_passed.append("locked unique/set table parity & zero duplicate oskill/aura curation contracts")

    return checks_passed

#!/usr/bin/env python3
"""
itemtypes_automagic.py
Step 5: Build itemtypes.txt and automagic.txt:
- Enable sockets on Javelins (jave, ajav) and Throwing Weapons (tkni, taxe):
  MaxSockets1 = 2, MaxSockets2 = 3, MaxSockets3 = 3
- Enable Magic & Rare Quivers on bowq (Arrows) and xboq (Bolts):
  Magic = "", Rare = "1", Normal = "0", AutoStack = "0"
- Add group 307 (Self-Replenishing, rep-quant = 10) to automagic.txt and also add
  mod2code = rep-quant (10) to group 302 rows so Amazon Javelins (am5, ama, amf)
  and all generic Throwing Weapons (group 307) automatically replenish stack quantity!
"""
import os
from typing import Dict, List

from mod_builder.common import MOD_ROOT, VANILLA_ROOT, read_excel_tsv, write_excel_tsv


def build_itemtypes(cfg: dict) -> str:
    headers, rows = read_excel_tsv("itemtypes.txt")
    by_code = {r["Code"]: r for r in rows if r.get("Code")}

    # 1. Enable sockets on Javelins (jave, ajav) and Throwing Knives/Axes (tkni, taxe)
    for tcode in ("tkni", "taxe", "jave", "ajav"):
        if tcode in by_code:
            row = by_code[tcode]
            row["MaxSockets1"] = "2"
            row["MaxSocketsLevelThreshold1"] = "25"
            row["MaxSockets2"] = "3"
            row["MaxSocketsLevelThreshold2"] = "40"
            row["MaxSockets3"] = "3"

    # 2. Enable Magic-only Quivers on bowq and xboq (Normal=0, Magic="", Rare="":
    # vendors still sell Normal white quivers via CharsiMin/Max, while monster drops roll Magic-only)
    for qcode in ("bowq", "xboq"):
        if qcode in by_code:
            row = by_code[qcode]
            row["Magic"] = ""
            row["Rare"] = ""
            row["Normal"] = "0"
            row["AutoStack"] = "0"

    # 3. Add dedicated 'malu' item type for Blacksmith's Malus (bml) so it can be gambled in gamble.txt
    # without inheriting from 'weap' (preventing monsters from ever dropping it in Weap TCs),
    # and 'umal' for Untempered Malus (um1), which inherits from 'blun' (-> 'mele' -> 'weap') so Charsi's
    # "Temper Malus" (Imbue) window accepts it and transforms it into a Rare Tempered Malus (um1,rar)!
    if "malu" not in by_code and "hamm" in by_code:
        malu = dict(by_code["hamm"])
        malu["ItemType"] = "Malus"
        malu["Code"] = "malu"
        malu["Equiv1"] = ""
        malu["Equiv2"] = ""
        malu["Body"] = "0"
        malu["BodyLoc1"] = ""
        malu["BodyLoc2"] = ""
        malu["Magic"] = "1"
        malu["Rare"] = ""
        malu["Normal"] = "0"
        malu["MaxSockets1"] = "0"
        malu["MaxSockets2"] = "0"
        malu["MaxSockets3"] = "0"
        rows.append(malu)

    if "umal" not in by_code and "hamm" in by_code:
        umal = dict(by_code["hamm"])
        umal["ItemType"] = "Untempered Malus"
        umal["Code"] = "umal"
        umal["Equiv1"] = "blun"
        umal["Equiv2"] = ""
        umal["Body"] = "1"
        umal["BodyLoc1"] = "rarm"
        umal["BodyLoc2"] = "larm"
        umal["Magic"] = ""
        umal["Rare"] = "1"
        umal["Normal"] = "0"
        umal["TreasureClass"] = "0"
        umal["Rarity"] = "0"
        umal["MaxSockets1"] = "0"
        umal["MaxSockets2"] = "0"
        umal["MaxSockets3"] = "0"
        rows.append(umal)

    # 4. Add Crafting Slot Umbrella ItemTypes ('jwly' for Ring/Amulet and 'btbl' for Boots/Belt)
    # so cubemain.txt can evaluate each disjoint slot group cleanly, AND wire up the Row 37 ('hlm1')
    # Mercenary Equipment inheritance trick so Hirelings can equip Gloves, Boots, Belts, Rings, and Amulets
    # without leaking Helm affixes or Helm cube recipes onto those item types!
    if rows[37].get("Code") == "helm" and rows[14].get("ItemType") == "Not Used":
        orig_helm = dict(rows[37])
        orig_unused = dict(rows[14])
        orig_helm["Equiv1"] = "armo"
        orig_helm["Equiv2"] = "hlm1"
        rows[14] = orig_helm
        by_code["helm"] = rows[14]

        hlm1 = dict(orig_unused)
        hlm1["ItemType"] = "Merc Equip"
        hlm1["Code"] = "hlm1"
        hlm1["Equiv1"] = ""
        hlm1["Equiv2"] = ""
        hlm1["Body"] = "0"
        hlm1["BodyLoc1"] = ""
        hlm1["BodyLoc2"] = ""
        rows[37] = hlm1
        by_code["hlm1"] = rows[37]

    if "jwly" not in by_code and "misc" in by_code:
        jwly = dict(by_code["misc"])
        jwly["ItemType"] = "Jewelry"
        jwly["Code"] = "jwly"
        jwly["Equiv1"] = "hlm1"
        jwly["Equiv2"] = ""
        rows.append(jwly)
    for c in ("ring", "amul"):
        if c in by_code:
            by_code[c]["Equiv2"] = "jwly"
    if "glov" in by_code:
        by_code["glov"]["Equiv2"] = "hlm1"

    if "btbl" not in by_code and "armo" in by_code:
        btbl = dict(by_code["armo"])
        btbl["ItemType"] = "Boots or Belt"
        btbl["Code"] = "btbl"
        btbl["Equiv1"] = "armo"
        btbl["Equiv2"] = "hlm1"
        rows.append(btbl)
    for c in ("boot", "belt"):
        if c in by_code:
            by_code[c]["Equiv2"] = "btbl"

    # 5. Configure 'herb' and 'ques' (used for 2x2 Lockboxes) with Normal = 1 so Lockboxes always drop
    # as normal items, and set AutoStack = 0 on 'key' so Lockbox Keys are individual 1x1 items.
    for ltype in ("herb", "ques"):
        if ltype in by_code:
            by_code[ltype]["Normal"] = "1"
            by_code[ltype]["Magic"] = ""
            by_code[ltype]["Rare"] = ""
    if "key" in by_code:
        by_code["key"]["AutoStack"] = "0"

    # 5b. Add '1hml' (One-Handed Melee) and '2hml' (Two-Handed Melee) item type tags so skills and masteries
    # (e.g., One-Handed Mastery, Two-Handed Mastery, Desperate Berserk) cleanly partition 1H vs. 2H melee weapons!
    if "1hml" not in by_code and "mele" in by_code:
        ohml = dict(by_code["mele"])
        ohml["ItemType"] = "One-Handed Melee"
        ohml["Code"] = "1hml"
        ohml["Equiv1"] = ""
        ohml["Equiv2"] = ""
        ohml["Body"] = "0"
        ohml["BodyLoc1"] = ""
        ohml["BodyLoc2"] = ""
        rows.append(ohml)
    if "2hml" not in by_code and "mele" in by_code:
        thml = dict(by_code["mele"])
        thml["ItemType"] = "Two-Handed Melee"
        thml["Code"] = "2hml"
        thml["Equiv1"] = ""
        thml["Equiv2"] = ""
        thml["Body"] = "0"
        thml["BodyLoc1"] = ""
        thml["BodyLoc2"] = ""
        rows.append(thml)

    # 5c. Add 'bcas' (Bone Caster Armor umbrella), 'bhlm' (Bone Helm & Mask secondary type tag inheriting from 'bcas'),
    # and 'bshd' (Bone Shield secondary type tag inheriting from 'bcas') assigned via armor.txt 'type2' (keeping primary
    # 'type' as 'helm' / 'shie' so hardcoded 3D shield/helm attachment orientations remain 100% intact)!
    if "bcas" not in by_code and "armo" in by_code:
        bcas = dict(by_code["armo"])
        bcas["ItemType"] = "Bone Caster Armor"
        bcas["Code"] = "bcas"
        bcas["Equiv1"] = ""
        bcas["Equiv2"] = ""
        bcas["Body"] = "0"
        bcas["BodyLoc1"] = ""
        bcas["BodyLoc2"] = ""
        bcas["TreasureClass"] = "0"
        bcas["Rarity"] = "0"
        rows.append(bcas)
        by_code["bcas"] = bcas
    if "bhlm" not in by_code and "helm" in by_code:
        bhlm = dict(by_code["helm"])
        bhlm["ItemType"] = "Bone Helm"
        bhlm["Code"] = "bhlm"
        bhlm["Equiv1"] = "bcas"
        bhlm["Equiv2"] = ""
        bhlm["Body"] = "0"
        bhlm["BodyLoc1"] = ""
        bhlm["BodyLoc2"] = ""
        bhlm["TreasureClass"] = "0"
        bhlm["Rarity"] = "0"
        rows.append(bhlm)
        by_code["bhlm"] = bhlm
    if "bshd" not in by_code and "shie" in by_code:
        bshd = dict(by_code["shie"])
        bshd["ItemType"] = "Bone Shield"
        bshd["Code"] = "bshd"
        bshd["Equiv1"] = "bcas"
        bshd["Equiv2"] = ""
        bshd["Body"] = "0"
        bshd["BodyLoc1"] = ""
        bshd["BodyLoc2"] = ""
        bshd["TreasureClass"] = "0"
        bshd["Rarity"] = "0"
        rows.append(bshd)
        by_code["bshd"] = bshd

    # 6. Clear hardcoded StaffMods in itemtypes.txt so our automagic.txt 'skill-rand' groups (303, 305, 310..315)
    # control 100% of class skill rolls across all 6 progression tiers (reqlevel 1/8/16/24/32/40)!
    for row in rows:
        if row.get("StaffMods"):
            row["StaffMods"] = ""

    return write_excel_tsv("itemtypes.txt", headers, rows)


# Exact Skill IDs per class and tier (Tiers 1..6 corresponding to reqlevel 1 / 8 / 16 / 24 / 32 / 40 in skills.txt).
# Vanilla classes are tier-ordered by id. The reworked Sorceress, Barbarian and Assassin moved skills between tiers,
# so mod_builder/skill_order.py permutes their skills.txt rows at write time to make every tier a contiguous id
# block again; automagic 'skill-rand' ranges are emitted directly in that FINAL id space (one interval per pool).
from mod_builder import skill_order as _skill_order  # noqa: E402

CLASS_SKILL_TIERS: Dict[str, List[tuple]] = {
    "nec": [(66, 70), (71, 75), (76, 80), (81, 85), (86, 90), (91, 95)],
    "pal": [(96, 100), (101, 105), (106, 110), (111, 115), (116, 120), (121, 125)],
    "dru": [(221, 225), (226, 230), (231, 235), (236, 240), (241, 245), (246, 250)],
}
for _cls in _skill_order.PERMUTED_CLASSES:
    CLASS_SKILL_TIERS[_cls] = _skill_order.final_tier_ranges(_cls)

CLASS_SKILL_ID_SETS: Dict[str, List[List[int]]] = {
    cls: [list(range(a, b + 1)) for a, b in tiers] for cls, tiers in CLASS_SKILL_TIERS.items()
}

# .d2s saves store an item's automagic (auto prefix) row index in 11 bits: rows >= 2048 cannot be saved and the
# item is DELETED on Save & Exit. Keep a safety margin below the hard limit.
AUTOMAGIC_SAVE_LIMIT = 2048
AUTOMAGIC_MAX_ROWS = 2000


def _to_intervals(skill_ids: List[int]) -> List[tuple]:
    s = sorted(set(skill_ids))
    if not s:
        return []
    out: List[tuple] = []
    lo = hi = s[0]
    for x in s[1:]:
        if x == hi + 1:
            hi = x
        else:
            out.append((lo, hi))
            lo = hi = x
    out.append((lo, hi))
    return out

# Progression brackets (K = 1..6): (bracket_idx_1based, min_alvl, max_alvl, levelreq)
STAFFMOD_BRACKETS = [
    (1, "1", "7", "1"),     # Act 1 Early Normal -> Tier 1
    (2, "8", "13", "6"),    # Act 1 Late Normal  -> Tiers 1..2
    (3, "14", "20", "12"),  # Act 2 Normal       -> Tiers 1..3
    (4, "21", "28", "18"),  # Act 3 Normal       -> Tiers 1..4
    (5, "29", "36", "24"),  # Act 4 Normal       -> Tiers 1..5
    (6, "37", "", "30"),    # Act 5 Normal + NM + Hell -> Tiers 1..6 (all 30 class skills eligible!)
]


def _make_auto_row(
    headers: List[str],
    group: str,
    lvl: str,
    maxlvl: str,
    lvlreq: str,
    freq: str,
    mods: List[tuple],
    itype1: str = "weap",
    itype2: str = "armo",
) -> Dict[str, str]:
    r = {k: "" for k in headers}
    r["Name"] = "Fletcher's"
    r["version"] = "100"
    r["spawnable"] = "1"
    r["rare"] = "1"
    r["level"] = lvl
    r["maxlevel"] = maxlvl
    r["levelreq"] = lvlreq
    r["frequency"] = freq
    r["group"] = group
    for idx, (mcode, mparam, mmin, mmax) in enumerate(mods[:3], start=1):
        r[f"mod{idx}code"] = mcode
        r[f"mod{idx}param"] = str(mparam) if mparam != "" else ""
        r[f"mod{idx}min"] = str(mmin) if mmin != "" else ""
        r[f"mod{idx}max"] = str(mmax) if mmax != "" else ""
    r["itype1"] = itype1
    r["itype2"] = itype2
    r["multiply"] = "0"
    r["add"] = "0"
    return r


def _build_class_staffmod_rows(headers: List[str], group: str, cls: str) -> List[Dict[str, str]]:
    """
    Build progressive 1-skill, 2-skill, and 3-skill 'skill-rand' rows for a class across the 6 brackets.
    Disjoint [min_id, max_id] tier partitions on multi-skill rows guarantee an item never rolls duplicate skills,
    while spanning Tiers 1..K so every unlocked tier (1..6 in Bracket 6) can spawn without leaking locked higher-tier skills!
    """
    tier_sets = CLASS_SKILL_ID_SETS[cls]
    out: List[Dict[str, str]] = []

    def union_ids(t_lo: int, t_hi: int) -> List[int]:
        res: List[int] = []
        for t_idx in range(t_lo - 1, t_hi):
            res.extend(tier_sets[t_idx])
        return sorted(set(res))

    def emit_1skill(min_lvl: str, max_lvl: str, lreq: str, base_freq: int, id_list: List[int]) -> None:
        ivs = _to_intervals(id_list)
        for lo, hi in ivs:
            f = str(max(1, (base_freq * (hi - lo + 1) + 2) // 5)) if len(ivs) > 1 else str(base_freq)
            out.append(
                _make_auto_row(
                    headers, group, min_lvl, max_lvl, lreq, f,
                    [("skill-rand", slvl, lo, hi)],
                )
            )

    def emit_2skill(min_lvl: str, max_lvl: str, lreq: str, freq: str, s1: str, s2: str, ids1: List[int], ids2: List[int]) -> None:
        ivs1 = _to_intervals(ids1)
        ivs2 = _to_intervals(ids2)
        n = max(len(ivs1), len(ivs2))
        for i in range(n):
            a_lo, a_hi = ivs1[i % len(ivs1)]
            b_lo, b_hi = ivs2[i % len(ivs2)]
            out.append(
                _make_auto_row(
                    headers, group, min_lvl, max_lvl, lreq, freq,
                    [("skill-rand", s1, a_lo, a_hi), ("skill-rand", s2, b_lo, b_hi)],
                )
            )

    def emit_3skill(min_lvl: str, max_lvl: str, lreq: str, freq: str, s1: str, s2: str, s3: str, ids1: List[int], ids2: List[int], ids3: List[int]) -> None:
        ivs1 = _to_intervals(ids1)
        ivs2 = _to_intervals(ids2)
        ivs3 = _to_intervals(ids3)
        n = max(len(ivs1), len(ivs2), len(ivs3))
        for i in range(n):
            a_lo, a_hi = ivs1[i % len(ivs1)]
            b_lo, b_hi = ivs2[i % len(ivs2)]
            c_lo, c_hi = ivs3[i % len(ivs3)]
            out.append(
                _make_auto_row(
                    headers, group, min_lvl, max_lvl, lreq, freq,
                    [
                        ("skill-rand", s1, a_lo, a_hi),
                        ("skill-rand", s2, b_lo, b_hi),
                        ("skill-rand", s3, c_lo, c_hi),
                    ],
                )
            )

    for k, min_lvl, max_lvl, lreq in STAFFMOD_BRACKETS:
        full_ids = union_ids(1, k)
        top_ids = union_ids(max(1, k - 1), k)

        # 1. Single-skill rolls: half from full Tiers 1..k pool, half weighted to top Tiers (k-1..k)
        for slvl, freq in (("1", 4), ("2", 3), ("3", 1)):
            emit_1skill(min_lvl, max_lvl, lreq, freq, full_ids)
            if k >= 2:
                emit_1skill(min_lvl, max_lvl, lreq, freq, top_ids)

        # 2. Two-skill & Three-skill rolls (strictly disjoint skill ID sets!)
        if k == 1:
            t1_ids = union_ids(1, 1)
            mid_idx = max(1, len(t1_ids) // 2)
            t1a, t1b = t1_ids[:mid_idx], t1_ids[mid_idx:]
            for s1, s2, freq in (("1", "1", "4"), ("2", "1", "2"), ("2", "2", "1"), ("3", "2", "1")):
                emit_2skill(min_lvl, max_lvl, lreq, freq, s1, s2, t1a, t1b)
        elif k == 2:
            t2_ids = union_ids(2, 2)
            t1_ids = union_ids(1, 1)
            mid_idx = max(1, len(t1_ids) // 2)
            t1a, t1b = t1_ids[:mid_idx], t1_ids[mid_idx:]
            for s1, s2, freq in (("1", "1", "3"), ("2", "1", "2"), ("2", "2", "2"), ("3", "2", "1"), ("3", "3", "1")):
                emit_2skill(min_lvl, max_lvl, lreq, freq, s1, s2, t2_ids, t1_ids)
            for s1, s2, s3, freq in (("2", "1", "1", "2"), ("2", "2", "1", "1"), ("3", "2", "1", "1"), ("3", "2", "2", "1")):
                emit_3skill(min_lvl, max_lvl, lreq, freq, s1, s2, s3, t2_ids, t1a, t1b)
        else:
            tk_ids = union_ids(k, k)
            low_a_ids = union_ids(1, k - 1)
            hi_b_ids = union_ids(k - 1, k)
            low_b_ids = union_ids(1, k - 2)
            for s1, s2, freq in (("1", "1", "2"), ("2", "1", "2"), ("2", "2", "2"), ("3", "2", "1"), ("3", "3", "1")):
                emit_2skill(min_lvl, max_lvl, lreq, freq, s1, s2, tk_ids, low_a_ids)
                emit_2skill(min_lvl, max_lvl, lreq, freq, s1, s2, hi_b_ids, low_b_ids)
            mid_tier = max(2, (k + 1) // 2)
            p1_ids = union_ids(k, k)
            p2_ids = union_ids(mid_tier, k - 1)
            p3_ids = union_ids(1, mid_tier - 1)
            for s1, s2, s3, freq in (
                ("1", "1", "1", "2"),
                ("2", "2", "1", "2"),
                ("3", "2", "1", "2"),
                ("3", "2", "2", "1"),
                ("3", "3", "2", "1"),
                ("3", "3", "3", "1"),
            ):
                emit_3skill(min_lvl, max_lvl, lreq, freq, s1, s2, s3, p1_ids, p2_ids, p3_ids)
    return out



def _merge_duplicate_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Collapse rows identical in every column except `frequency` into one row with the summed frequency.
    Lossless: the engine picks a row within a group with probability frequency / sum(frequency)."""
    out: List[Dict[str, str]] = []
    seen: Dict[tuple, Dict[str, str]] = {}
    for r in rows:
        key = tuple(sorted((k, v) for k, v in r.items() if k != "frequency"))
        if key in seen and r.get("frequency", "").isdigit() and seen[key].get("frequency", "").isdigit():
            seen[key]["frequency"] = str(int(seen[key]["frequency"]) + int(r["frequency"]))
            continue
        r = dict(r)
        seen[key] = r
        out.append(r)
    return out


def _check_automagic_save_limit(rows: List[Dict[str, str]]) -> None:
    if len(rows) > AUTOMAGIC_MAX_ROWS:
        groups: Dict[str, int] = {}
        for r in rows:
            groups[r.get("group", "")] = groups.get(r.get("group", ""), 0) + 1
        raise RuntimeError(
            f"automagic.txt has {len(rows)} rows (budget {AUTOMAGIC_MAX_ROWS}, hard save limit "
            f"{AUTOMAGIC_SAVE_LIMIT}). Items whose auto-affix row index is >= {AUTOMAGIC_SAVE_LIMIT} are DELETED "
            f"on Save & Exit. Rows per group: {groups}")


def build_automagic(cfg: dict) -> str:
    headers, rows = read_excel_tsv("automagic.txt")

    # Filter out vanilla groups 303 (Orb hp/mana) and 305 (Head poison) so we can rebuild them
    # with both their innate mod1 stat AND 1-2 'skill-rand' staffmods in mod2/mod3!
    # Also clone group 302 into group 308 (with mod2code = rep-quant) exclusivamente for Amazon Javelins (ajav),
    # while leaving group 302 untouched for Amazon Spears (aspe) so Maiden/Ceremonial/Matriarchal Spears
    # NEVER roll 'Replenishes Quantity'!
    kept_rows: List[Dict[str, str]] = []
    ajav_rows: List[Dict[str, str]] = []
    for r in rows:
        grp = r.get("group", "")
        if grp in ("303", "305"):
            continue
        kept_rows.append(r)
        if grp == "302":
            ajav_r = dict(r)
            ajav_r["group"] = "308"
            ajav_r["mod2code"] = "rep-quant"
            ajav_r["mod2param"] = "10"
            ajav_r["mod2min"] = ""
            ajav_r["mod2max"] = ""
            ajav_rows.append(ajav_r)

    rows = kept_rows + ajav_rows

    # 2. Add group 307 row for generic Throwing Weapons (jave, tkni, taxe)
    rows.append(
        _make_auto_row(
            headers, "307", "1", "", "1", "1",
            [("rep-quant", "10", "", "")],
            itype1="thro", itype2="misl",
        )
    )
    # Everything appended so far is a small fixed group; the class staffmod groups below are large.
    head_count = len(rows)

    # 3. Rebuild group 303 (Sorceress Orbs: innate +Life or +Mana in mod1 + 1-2 Sorceress skill-rand in mod2/mod3)
    # Sorceress tiers come from the 1:1 skill map and are NOT contiguous id blocks, so every skill pool is
    # decomposed into maximal contiguous [lo, hi] intervals (one automagic row per interval).
    sor_sets = CLASS_SKILL_ID_SETS["sor"]

    def sor_union(t_lo: int, t_hi: int) -> List[int]:
        return sorted({i for t in range(t_lo - 1, t_hi) for i in sor_sets[t]})

    orb_stat_tiers = [
        # (k, min_lvl, max_lvl, lreq, hp_min, hp_max, mana_min, mana_max)
        (1, "1", "7", "1", "5", "12", "5", "12"),
        (2, "8", "13", "6", "10", "20", "10", "20"),
        (3, "14", "20", "12", "18", "30", "18", "30"),
        (4, "21", "28", "18", "28", "45", "28", "45"),
        (5, "29", "36", "24", "40", "60", "40", "60"),
        (6, "37", "", "30", "55", "80", "55", "80"),
    ]
    for k, min_lvl, max_lvl, lreq, hp_lo, hp_hi, mp_lo, mp_hi in orb_stat_tiers:
        full_ids = sor_union(1, k)
        for base_stat, st_lo, st_hi in (("hp", hp_lo, hp_hi), ("mana", mp_lo, mp_hi)):
            for slvl, freq in (("1", 3), ("2", 2), ("3", 1)):
                ivs = _to_intervals(full_ids)
                for lo, hi in ivs:
                    f = str(max(1, (freq * (hi - lo + 1) + 2) // 5)) if len(ivs) > 1 else str(freq)
                    rows.append(
                        _make_auto_row(
                            headers, "303", min_lvl, max_lvl, lreq, f,
                            [(base_stat, "", st_lo, st_hi), ("skill-rand", slvl, lo, hi)],
                        )
                    )
            if k >= 2:
                top_ivs = _to_intervals(sor_sets[k - 1])
                low_ivs = _to_intervals(sor_union(1, k - 1))
                pairs = ((("2", "1", "2"), ("2", "2", "1"), ("3", "2", "1"), ("3", "3", "1")))
                for s1, s2, freq in pairs:
                    for i in range(max(len(top_ivs), len(low_ivs))):
                        t_lo, t_hi = top_ivs[i % len(top_ivs)]
                        l_lo, l_hi = low_ivs[i % len(low_ivs)]
                        rows.append(
                            _make_auto_row(
                                headers, "303", min_lvl, max_lvl, lreq, freq,
                                [(base_stat, "", st_lo, st_hi), ("skill-rand", s1, t_lo, t_hi), ("skill-rand", s2, l_lo, l_hi)],
                            )
                        )
            else:
                half = max(1, len(full_ids) // 2)
                a_ivs = _to_intervals(full_ids[:half])
                b_ivs = _to_intervals(full_ids[half:])
                for i in range(max(len(a_ivs), len(b_ivs))):
                    a_lo, a_hi = a_ivs[i % len(a_ivs)]
                    b_lo, b_hi = b_ivs[i % len(b_ivs)]
                    rows.append(
                        _make_auto_row(
                            headers, "303", min_lvl, max_lvl, lreq, "2",
                            [(base_stat, "", st_lo, st_hi), ("skill-rand", "2", a_lo, a_hi), ("skill-rand", "1", b_lo, b_hi)],
                        )
                    )

    # 4. Rebuild group 305 (Necromancer Shrunken Heads: innate dmg-pois in mod1 + 1-2 Necromancer skill-rand in mod2/mod3)
    nec_tiers = CLASS_SKILL_TIERS["nec"]
    head_stat_tiers = [
        (1, "1", "7", "1", "75", "8", "24"),
        (2, "8", "13", "6", "75", "16", "48"),
        (3, "14", "20", "12", "100", "24", "60"),
        (4, "21", "28", "18", "100", "32", "72"),
        (5, "29", "36", "24", "100", "48", "96"),
        (6, "37", "", "30", "100", "64", "128"),
    ]
    for k, min_lvl, max_lvl, lreq, plen, p_lo, p_hi in head_stat_tiers:
        full_lo, full_hi = nec_tiers[0][0], nec_tiers[k - 1][1]
        for slvl, freq in (("1", "3"), ("2", "2"), ("3", "1")):
            rows.append(
                _make_auto_row(
                    headers, "305", min_lvl, max_lvl, lreq, freq,
                    [("dmg-pois", plen, p_lo, p_hi), ("skill-rand", slvl, full_lo, full_hi)],
                )
            )
        if k >= 2:
            tk_lo, tk_hi = nec_tiers[k - 1][0], nec_tiers[k - 1][1]
            low_lo, low_hi = nec_tiers[0][0], nec_tiers[k - 2][1]
            for s1, s2, freq in (("2", "1", "2"), ("2", "2", "1"), ("3", "2", "1"), ("3", "3", "1")):
                rows.append(
                    _make_auto_row(
                        headers, "305", min_lvl, max_lvl, lreq, freq,
                        [
                            ("dmg-pois", plen, p_lo, p_hi),
                            ("skill-rand", s1, tk_lo, tk_hi),
                            ("skill-rand", s2, low_lo, low_hi),
                        ],
                    )
                )
        else:
            mid = full_lo + 2
            rows.append(
                _make_auto_row(
                    headers, "305", min_lvl, max_lvl, lreq, "2",
                    [
                        ("dmg-pois", plen, p_lo, p_hi),
                        ("skill-rand", "2", full_lo, mid),
                        ("skill-rand", "1", mid + 1, full_hi),
                    ],
                )
            )

    # 5. Build dedicated 1..3 skill-rand groups for Staves (310), Wands (311), Scepters (312),
    # Primal Helms (313), Druid Pelts (314), and Assassin Claws (315)
    staffmod_groups = [
        ("310", "sor"),
        ("311", "nec"),
        ("312", "pal"),
        ("313", "bar"),
        ("314", "dru"),
        ("315", "ass"),
    ]
    for grp_id, cls_code in staffmod_groups:
        rows.extend(_build_class_staffmod_rows(headers, grp_id, cls_code))

    # 6. Add Shield Block Rate & Helm Light Radius implicit automagic groups (316..321):
    # - 316: Light Shields (+15% Faster Block Rate)
    # - 317: Heavy Shields (-15% Faster Block Rate)
    # - 318: Light Paladin Shields (clones 304 + mod3code=block2 +15%)
    # - 319: Heavy Paladin Shields (clones 304 + mod3code=block2 -15%)
    # - 320: Enclosed Visor Helms (Mask & Full Helm lines: -2 Light Radius)
    # - 321: Fully Enclosed Greathelms (Great/Winged/Spired Helm line: -3 Light Radius)
    # These are inserted BEFORE the large class staffmod groups so common shields/helms always get low row ids.
    fixed_rows: List[Dict[str, str]] = []
    fixed_rows.append(
        _make_auto_row(
            headers, "316", "1", "", "1", "1",
            [("block2", "", "15", "15")],
            itype1="shie", itype2="",
        )
    )
    fixed_rows.append(
        _make_auto_row(
            headers, "317", "1", "", "1", "1",
            [("block2", "", "-15", "-15")],
            itype1="shie", itype2="",
        )
    )
    for r in list(kept_rows):
        if r.get("group") == "304":
            for new_grp, fbr_val in (("318", "15"), ("319", "-15")):
                pr = dict(r)
                pr["group"] = new_grp
                pr["mod3code"] = "block2"
                pr["mod3param"] = ""
                pr["mod3min"] = fbr_val
                pr["mod3max"] = fbr_val
                fixed_rows.append(pr)
    fixed_rows.append(
        _make_auto_row(
            headers, "320", "1", "", "1", "1",
            [("light", "", "-2", "-2")],
            itype1="helm", itype2="",
        )
    )
    fixed_rows.append(
        _make_auto_row(
            headers, "321", "1", "", "1", "1",
            [("light", "", "-3", "-3")],
            itype1="helm", itype2="",
        )
    )

    rows = rows[:head_count] + fixed_rows + rows[head_count:]
    rows = _merge_duplicate_rows(rows)
    _check_automagic_save_limit(rows)

    return write_excel_tsv("automagic.txt", headers, rows)


def build_inventory(cfg: dict) -> str:
    """Populate neck, rHand, lHand, belt, feet, and gloves slot coordinates on Hireling & Hireling2 in inventory.txt."""
    headers, rows = read_excel_tsv("inventory.txt")
    by_cls = {r.get("class", ""): r for r in rows}
    slot_prefixes = ("neck", "rHand", "lHand", "belt", "feet", "gloves")
    for src_cls, dst_cls in (("Amazon", "Hireling"), ("Amazon2", "Hireling2")):
        if src_cls in by_cls and dst_cls in by_cls:
            src = by_cls[src_cls]
            dst = by_cls[dst_cls]
            for pfx in slot_prefixes:
                dst[f"{pfx}Left"] = str(int(src[f"{pfx}Left"]) - 320)
                dst[f"{pfx}Right"] = str(int(src[f"{pfx}Right"]) - 320)
                dst[f"{pfx}Top"] = src[f"{pfx}Top"]
                dst[f"{pfx}Bottom"] = src[f"{pfx}Bottom"]
                dst[f"{pfx}Width"] = src[f"{pfx}Width"]
                dst[f"{pfx}Height"] = src[f"{pfx}Height"]
    return write_excel_tsv("inventory.txt", headers, rows)


def _patch_hireling_sprite(hp_src: str, cb_src: str, dst_path: str, scale: int) -> None:
    """
    Composite all 10 equipment slot frames from classic_background.sprite onto hirelingpanel.sprite
    (scale=1 for full 1162x1507 HD, scale=2 for 581x753 lowend).
    """
    with open(hp_src, "rb") as f:
        hp_bytes = bytearray(f.read())
    with open(cb_src, "rb") as f:
        cb_bytes = bytearray(f.read())

    W = 1162 // scale
    H = 1507 // scale
    hp_px = hp_bytes[40:]
    cb_px = cb_bytes[40:]
    out_px = bytearray(hp_px)

    # Erase the entire interior paperdoll stone region (x=86..1076, y=148..758) using mirror-tiled
    # unmarked stone from x=326..458 so 100% of the old 4 slot frames are removed with zero seams!
    strip_x0 = 326 // scale
    strip_w = 132 // scale
    y_start = 148 // scale
    y_end = 758 // scale
    x_start = 86 // scale
    x_end = 1076 // scale
    for y in range(y_start, min(H, y_end)):
        sy = min((745 // scale), max((150 // scale), y))
        for x in range(x_start, min(W, x_end)):
            if y < (195 // scale) and (x < (120 // scale) or x > (1042 // scale)):
                continue
            rel = x - x_start
            cycle = rel // strip_w
            offset = rel % strip_w
            if cycle % 2 == 1:
                offset = strip_w - 1 - offset
            sx = strip_x0 + offset
            sidx = (sy * W + sx) * 4
            didx = (y * W + x) * 4
            out_px[didx:didx + 4] = hp_px[sidx:sidx + 4]

    slots = (
        (482 // scale, 185 // scale, 196 // scale, 196 // scale, 481 // scale, 148 // scale),
        (482 // scale, 428 // scale, 196 // scale, 294 // scale, 481 // scale, 355 // scale),
        (483 // scale, 769 // scale, 196 // scale,  98 // scale, 481 // scale, 660 // scale),
        (718 // scale, 353 // scale,  98 // scale,  98 // scale, 718 // scale, 290 // scale),
        (344 // scale, 770 // scale,  98 // scale,  98 // scale, 344 // scale, 660 // scale),
        (718 // scale, 770 // scale,  98 // scale,  98 // scale, 718 // scale, 660 // scale),
        (108 // scale, 232 // scale, 196 // scale, 392 // scale, 108 // scale, 150 // scale),
        (860 // scale, 232 // scale, 196 // scale, 392 // scale, 861 // scale, 150 // scale),
        (107 // scale, 672 // scale, 196 // scale, 196 // scale, 108 // scale, 562 // scale),
        (859 // scale, 672 // scale, 196 // scale, 196 // scale, 861 // scale, 562 // scale),
    )
    pad = max(6, 12 // scale)
    for sx, sy, w, h, dx, dy in slots:
        for ry in range(-pad, h + pad):
            for rx in range(-pad, w + pad):
                sidx = ((sy + ry) * W + (sx + rx)) * 4
                didx = ((dy + ry) * W + (dx + rx)) * 4
                out_px[didx:didx + 4] = cb_px[sidx:sidx + 4]

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "wb") as f:
        f.write(hp_bytes[:40] + out_px)


def build_hireling_ui(cfg: dict) -> str:
    """
    Build expanded 10-slot HirelingInventoryPanel HD layout JSON and HD/lowend background sprites
    so mercenaries can equip Helm, Amulet, Torso, Right Arm, Left Arm (including Arrows on Act 1 Rogue),
    Gloves, Boots, Belt, and 2 Rings!
    """
    src_json = os.path.join(VANILLA_ROOT, "data/global/ui/layouts/hirelinginventorypanelhd.json")
    with open(src_json, "r", encoding="utf-8") as f:
        content = f.read()

    old_slots_block = """        {
            "type": "InventorySlotWidget", "name": "slot_head",
            "fields": {
                "rect": { "x": 481, "y": 193, "width": 196, "height": 196 },
                "cellSize": "$ItemCellSize",
                "location": "head",
                "gemSocketFilename": "PANEL\\\\gemsocket",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_HeadArmor",
                "isHireable": true,
            }
        },
        {
            "type": "InventorySlotWidget", "name": "slot_torso",
            "fields": {
                "rect": { "x": 481, "y": 433, "width": 196, "height": 294 },
                "cellSize": "$ItemCellSize",
                "location": "torso",
                "gemSocketFilename": "PANEL\\\\gemsocket",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_ChestArmor",
                "isHireable": true,
            }
        },
        {
            "type": "InventorySlotWidget", "name": "slot_right_arm",
            "fields": {
                "rect": { "x": 108, "y": 336, "width": 196, "height": 392 },
                "cellSize": "$ItemCellSize",
                "location": "right_arm",
                "gemSocketFilename": "PANEL\\\\gemsocket",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_Weapon",
                "isHireable": true,
            }
        },
        {
            "type": "InventorySlotWidget", "name": "slot_left_arm",
            "fields": {
                "rect": { "x": 861, "y": 336, "width": 196, "height": 392 },
                "cellSize": "$ItemCellSize",
                "location": "left_arm",
                "gemSocketFilename": "PANEL\\\\gemsocket",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_Weapon",
                "isHireable": true,
            }
        },"""

    new_slots_block = """        {
            "type": "InventorySlotWidget", "name": "slot_head",
            "fields": {
                "rect": { "x": 481, "y": 148, "width": 196, "height": 196 },
                "cellSize": "$ItemCellSize",
                "location": "head",
                "gemSocketFilename": "PANEL\\\\gemsocket",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_HeadArmor",
                "isHireable": true,
            }
        },
        {
            "type": "InventorySlotWidget", "name": "slot_neck",
            "fields": {
                "rect": { "x": 718, "y": 290, "width": 98, "height": 98 },
                "cellSize": "$ItemCellSize",
                "location": "neck",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_Amulet",
                "isHireable": true,
            }
        },
        {
            "type": "InventorySlotWidget", "name": "slot_torso",
            "fields": {
                "rect": { "x": 481, "y": 355, "width": 196, "height": 294 },
                "cellSize": "$ItemCellSize",
                "location": "torso",
                "gemSocketFilename": "PANEL\\\\gemsocket",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_ChestArmor",
                "isHireable": true,
            }
        },
        {
            "type": "InventorySlotWidget", "name": "slot_right_arm",
            "fields": {
                "rect": { "x": 108, "y": 150, "width": 196, "height": 392 },
                "cellSize": "$ItemCellSize",
                "location": "right_arm",
                "gemSocketFilename": "PANEL\\\\gemsocket",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_Weapon",
                "isHireable": true,
            }
        },
        {
            "type": "InventorySlotWidget", "name": "slot_left_arm",
            "fields": {
                "rect": { "x": 861, "y": 150, "width": 196, "height": 392 },
                "cellSize": "$ItemCellSize",
                "location": "left_arm",
                "gemSocketFilename": "PANEL\\\\gemsocket",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_Weapon",
                "isHireable": true,
            }
        },
        {
            "type": "InventorySlotWidget", "name": "slot_right_hand",
            "fields": {
                "rect": { "x": 344, "y": 660, "width": 98, "height": 98 },
                "cellSize": "$ItemCellSize",
                "location": "right_hand",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_Ring",
                "isHireable": true,
            }
        },
        {
            "type": "InventorySlotWidget", "name": "slot_left_hand",
            "fields": {
                "rect": { "x": 718, "y": 660, "width": 98, "height": 98 },
                "cellSize": "$ItemCellSize",
                "location": "left_hand",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_Ring",
                "isHireable": true,
            }
        },
        {
            "type": "InventorySlotWidget", "name": "slot_belt",
            "fields": {
                "rect": { "x": 481, "y": 660, "width": 196, "height": 98 },
                "cellSize": "$ItemCellSize",
                "location": "belt",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_Belt",
                "isHireable": true,
            }
        },
        {
            "type": "InventorySlotWidget", "name": "slot_feet",
            "fields": {
                "rect": { "x": 861, "y": 562, "width": 196, "height": 196 },
                "cellSize": "$ItemCellSize",
                "location": "feet",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_Boots",
                "isHireable": true,
            }
        },
        {
            "type": "InventorySlotWidget", "name": "slot_gloves",
            "fields": {
                "rect": { "x": 108, "y": 562, "width": 196, "height": 196 },
                "cellSize": "$ItemCellSize",
                "location": "gloves",
                "backgroundFilename": "PANEL\\\\Inventory\\\\Inventory_Paperdoll_Glove",
                "isHireable": true,
            }
        },"""

    norm_content = content.replace("\r\n", "\n")
    norm_content = norm_content.replace('"\\\\PANEL\\\\Hireling\\\\HirelingPanel"', '"panel\\\\hireling\\\\hirelingpanel"')
    norm_content = norm_content.replace('"Spells/Hireables/HrSkillIcon"', '"spells/hireables/hrskillicon"')
    assert old_slots_block in norm_content, "Failed to locate slot block in hirelinginventorypanelhd.json"
    norm_content = norm_content.replace(old_slots_block, new_slots_block, 1)

    dst_json = os.path.join(MOD_ROOT, "data/global/ui/layouts/hirelinginventorypanelhd.json")
    os.makedirs(os.path.dirname(dst_json), exist_ok=True)
    with open(dst_json, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(norm_content)

    # Also normalize skillIconFilename in hiremenupanelhd.json so the Hire Menu loads our expanded hrskillicon.sprite
    src_menu_json = os.path.join(VANILLA_ROOT, "data/global/ui/layouts/hiremenupanelhd.json")
    dst_menu_json = os.path.join(MOD_ROOT, "data/global/ui/layouts/hiremenupanelhd.json")
    with open(src_menu_json, "r", encoding="utf-8", newline="") as f:
        menu_content = f.read().replace("\r\n", "\n")
    menu_content = menu_content.replace('"Spells/Hireables/HrSkillIcon"', '"spells/hireables/hrskillicon"')
    with open(dst_menu_json, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(menu_content)

    # Generate HD and lowend hirelingpanel sprites
    _patch_hireling_sprite(
        os.path.join(VANILLA_ROOT, "data/hd/global/ui/panel/hireling/hirelingpanel.sprite"),
        os.path.join(VANILLA_ROOT, "data/hd/global/ui/panel/inventory/classic_background.sprite"),
        os.path.join(MOD_ROOT, "data/hd/global/ui/panel/hireling/hirelingpanel.sprite"),
        scale=1,
    )
    _patch_hireling_sprite(
        os.path.join(VANILLA_ROOT, "data/hd/global/ui/panel/hireling/hirelingpanel.lowend.sprite"),
        os.path.join(VANILLA_ROOT, "data/hd/global/ui/panel/inventory/classic_background.lowend.sprite"),
        os.path.join(MOD_ROOT, "data/hd/global/ui/panel/hireling/hirelingpanel.lowend.sprite"),
        scale=2,
    )

    # Generate expanded HD and lowend HrSkillIcon sprites (frames 0..28 vanilla + 29..54 custom class skill icons)
    _build_hireling_skill_icons(suffix=".sprite", frame_w=132, frame_h=130)
    _build_hireling_skill_icons(suffix=".lowend.sprite", frame_w=67, frame_h=65)
    return dst_json


def _build_hireling_skill_icons(suffix: str, frame_w: int, frame_h: int) -> None:
    """
    Append authentic class skill icon frames (29..54) from each class's native skillicon.sprite
    onto Spells/Hireables/HrSkillIcon (.sprite and .lowend.sprite).
    """
    import struct
    from mod_builder.skills import CUSTOM_MERC_SKILL_ICONS

    hr_src = os.path.join(VANILLA_ROOT, f"data/hd/global/ui/spells/hireables/hrskillicon{suffix}")
    with open(hr_src, "rb") as f:
        hr_data = f.read()
    hr_hdr = bytearray(hr_data[:40])
    hr_px = hr_data[40:]
    base_frames = 29
    base_row_bytes = base_frames * frame_w * 4

    # Cache class sprite pixel payloads
    cls_px_cache: Dict[Tuple[str, str], bytes] = {}
    for _fidx, _sdesc, cls_dir, spr_prefix, _icel in CUSTOM_MERC_SKILL_ICONS:
        key = (cls_dir, spr_prefix)
        if key not in cls_px_cache:
            cpath = os.path.join(VANILLA_ROOT, f"data/hd/global/ui/spells/{cls_dir}/{spr_prefix}{suffix}")
            with open(cpath, "rb") as f:
                cls_px_cache[key] = f.read()[40:]

    cls_row_bytes = 60 * frame_w * 4
    total_frames = base_frames + len(CUSTOM_MERC_SKILL_ICONS)
    total_w = total_frames * frame_w
    out_px = bytearray(total_w * frame_h * 4)
    out_row_bytes = total_w * 4

    for y in range(frame_h):
        dst_row_off = y * out_row_bytes
        src_hr_off = y * base_row_bytes
        out_px[dst_row_off : dst_row_off + base_row_bytes] = hr_px[src_hr_off : src_hr_off + base_row_bytes]
        for frame_idx, _sdesc, cls_dir, spr_prefix, icon_cel in CUSTOM_MERC_SKILL_ICONS:
            c_px = cls_px_cache[(cls_dir, spr_prefix)]
            c_off = y * cls_row_bytes + icon_cel * frame_w * 4
            f_off = dst_row_off + frame_idx * frame_w * 4
            out_px[f_off : f_off + frame_w * 4] = c_px[c_off : c_off + frame_w * 4]
            # Clamp rightmost separator column (frame_w - 1) to match column (frame_w - 2)
            out_px[f_off + (frame_w - 1) * 4 : f_off + frame_w * 4] = out_px[
                f_off + (frame_w - 2) * 4 : f_off + (frame_w - 1) * 4
            ]

    # Update SpA1 header: w (offset 8), h (offset 12), frames (offset 20), byte_len (offset 32)
    struct.pack_into("<I", hr_hdr, 8, total_w)
    struct.pack_into("<I", hr_hdr, 12, frame_h)
    struct.pack_into("<I", hr_hdr, 20, total_frames)
    struct.pack_into("<I", hr_hdr, 32, len(out_px))

    dst_path = os.path.join(MOD_ROOT, f"data/hd/global/ui/spells/hireables/hrskillicon{suffix}")
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "wb") as f:
        f.write(hr_hdr + out_px)


def build_itemtypes_automagic(cfg: dict) -> str:
    p1 = build_itemtypes(cfg)
    p2 = build_automagic(cfg)
    p3 = build_inventory(cfg)
    p4 = build_hireling_ui(cfg)
    return f"{p1}, {p2}, {p3}, {p4}"

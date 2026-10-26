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
from typing import Dict, List

from mod_builder.common import read_excel_tsv, write_excel_tsv


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
        malu["Rare"] = "1"
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

    # 4. Add Crafting Slot Umbrella ItemTypes ('gljw' for Gloves/Ring/Amulet and 'btbl' for Boots/Belt)
    # so cubemain.txt can evaluate 'gljw' and 'btbl' before the 'armo' catch-all!
    if "gljw" not in by_code and "misc" in by_code:
        gljw = dict(by_code["misc"])
        gljw["ItemType"] = "Glove or Jewelry"
        gljw["Code"] = "gljw"
        gljw["Equiv1"] = ""
        gljw["Equiv2"] = ""
        rows.append(gljw)
    for c in ("glov", "ring", "amul"):
        if c in by_code:
            by_code[c]["Equiv2"] = "gljw"

    if "btbl" not in by_code and "armo" in by_code:
        btbl = dict(by_code["armo"])
        btbl["ItemType"] = "Boots or Belt"
        btbl["Code"] = "btbl"
        btbl["Equiv1"] = "armo"
        btbl["Equiv2"] = ""
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

    # 6. Clear hardcoded StaffMods in itemtypes.txt so our automagic.txt 'skill-rand' groups (303, 305, 310..315)
    # control 100% of class skill rolls across all 6 progression tiers (reqlevel 1/8/16/24/32/40)!
    for row in rows:
        if row.get("StaffMods"):
            row["StaffMods"] = ""

    return write_excel_tsv("itemtypes.txt", headers, rows)


# Contiguous Skill ID ranges per class and tier (Tiers 1..6 corresponding to reqlevel 1 / 8 / 16 / 24 / 32 / 40)
CLASS_SKILL_TIERS: Dict[str, List[ tuple ]] = {
    "sor": [(36, 40), (41, 45), (46, 50), (51, 55), (56, 60), (61, 65)],
    "nec": [(66, 70), (71, 75), (76, 80), (81, 85), (86, 90), (91, 95)],
    "pal": [(96, 100), (101, 105), (106, 110), (111, 115), (116, 120), (121, 125)],
    "bar": [(126, 131), (132, 138), (139, 142), (143, 146), (147, 150), (151, 155)],
    "dru": [(221, 225), (226, 230), (231, 235), (236, 240), (241, 245), (246, 250)],
    "ass": [(251, 255), (256, 260), (261, 265), (266, 270), (271, 275), (276, 280)],
}

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
    while spanning Tiers 1..K so every unlocked tier (1..6 in Bracket 6) can spawn!
    """
    tiers = CLASS_SKILL_TIERS[cls]
    out: List[Dict[str, str]] = []

    def span(t_lo: int, t_hi: int) -> tuple:
        return (tiers[t_lo - 1][0], tiers[t_hi - 1][1])

    for k, min_lvl, max_lvl, lreq in STAFFMOD_BRACKETS:
        full_lo, full_hi = span(1, k)
        top_lo, top_hi = span(max(1, k - 1), k)

        # 1. Single-skill rolls: half from full Tiers 1..k pool, half weighted to top Tiers (k-1..k)
        for slvl, freq in (("1", "4"), ("2", "3"), ("3", "1")):
            out.append(
                _make_auto_row(
                    headers, group, min_lvl, max_lvl, lreq, freq,
                    [("skill-rand", slvl, full_lo, full_hi)],
                )
            )
            if k >= 2:
                out.append(
                    _make_auto_row(
                        headers, group, min_lvl, max_lvl, lreq, freq,
                        [("skill-rand", slvl, top_lo, top_hi)],
                    )
                )

        # 2. Two-skill & Three-skill rolls (strictly disjoint skill ID ranges!)
        if k == 1:
            # Split Tier 1 into two disjoint halves: first 3 skills vs remaining skills
            mid = full_lo + 2
            for s1, s2, freq in (("1", "1", "4"), ("2", "1", "2"), ("2", "2", "1"), ("3", "2", "1")):
                out.append(
                    _make_auto_row(
                        headers, group, min_lvl, max_lvl, lreq, freq,
                        [("skill-rand", s1, full_lo, mid), ("skill-rand", s2, mid + 1, full_hi)],
                    )
                )
        elif k == 2:
            # Tier 2 vs Tier 1 (disjoint), plus 3-skill (Tier 2 + Tier 1a + Tier 1b)
            t2_lo, t2_hi = span(2, 2)
            t1_lo, t1_hi = span(1, 1)
            t1_mid = t1_lo + 2
            for s1, s2, freq in (("1", "1", "3"), ("2", "1", "2"), ("2", "2", "2"), ("3", "2", "1"), ("3", "3", "1")):
                out.append(
                    _make_auto_row(
                        headers, group, min_lvl, max_lvl, lreq, freq,
                        [("skill-rand", s1, t2_lo, t2_hi), ("skill-rand", s2, t1_lo, t1_hi)],
                    )
                )
            for s1, s2, s3, freq in (("2", "1", "1", "2"), ("2", "2", "1", "1"), ("3", "2", "1", "1"), ("3", "2", "2", "1")):
                out.append(
                    _make_auto_row(
                        headers, group, min_lvl, max_lvl, lreq, freq,
                        [
                            ("skill-rand", s1, t2_lo, t2_hi),
                            ("skill-rand", s2, t1_lo, t1_mid),
                            ("skill-rand", s3, t1_mid + 1, t1_hi),
                        ],
                    )
                )
        else:
            # k >= 3 (Tiers 1..k unlocked):
            # Disjoint 2-skill partition A: Tier k + Tiers 1..(k-1)
            tk_lo, tk_hi = span(k, k)
            low_a_lo, low_a_hi = span(1, k - 1)
            # Disjoint 2-skill partition B: Tiers (k-1)..k + Tiers 1..(k-2)
            hi_b_lo, hi_b_hi = span(k - 1, k)
            low_b_lo, low_b_hi = span(1, k - 2)
            for s1, s2, freq in (("1", "1", "2"), ("2", "1", "2"), ("2", "2", "2"), ("3", "2", "1"), ("3", "3", "1")):
                out.append(
                    _make_auto_row(
                        headers, group, min_lvl, max_lvl, lreq, freq,
                        [("skill-rand", s1, tk_lo, tk_hi), ("skill-rand", s2, low_a_lo, low_a_hi)],
                    )
                )
                out.append(
                    _make_auto_row(
                        headers, group, min_lvl, max_lvl, lreq, freq,
                        [("skill-rand", s1, hi_b_lo, hi_b_hi), ("skill-rand", s2, low_b_lo, low_b_hi)],
                    )
                )
            # Disjoint 3-skill partition across all unlocked Tiers 1..k:
            # Slot 1: Tier k | Slot 2: Tiers mid..k-1 | Slot 3: Tiers 1..(mid-1)
            mid_tier = max(2, (k + 1) // 2)
            p1_lo, p1_hi = span(k, k)
            p2_lo, p2_hi = span(mid_tier, k - 1)
            p3_lo, p3_hi = span(1, mid_tier - 1)
            for s1, s2, s3, freq in (
                ("1", "1", "1", "2"),
                ("2", "2", "1", "2"),
                ("3", "2", "1", "2"),
                ("3", "2", "2", "1"),
                ("3", "3", "2", "1"),
                ("3", "3", "3", "1"),
            ):
                out.append(
                    _make_auto_row(
                        headers, group, min_lvl, max_lvl, lreq, freq,
                        [
                            ("skill-rand", s1, p1_lo, p1_hi),
                            ("skill-rand", s2, p2_lo, p2_hi),
                            ("skill-rand", s3, p3_lo, p3_hi),
                        ],
                    )
                )
    return out


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

    # 3. Rebuild group 303 (Sorceress Orbs: innate +Life or +Mana in mod1 + 1-2 Sorceress skill-rand in mod2/mod3)
    sor_tiers = CLASS_SKILL_TIERS["sor"]
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
        full_lo, full_hi = sor_tiers[0][0], sor_tiers[k - 1][1]
        top_lo, top_hi = sor_tiers[max(0, k - 2)][0], sor_tiers[k - 1][1]
        for base_stat, st_lo, st_hi in (("hp", hp_lo, hp_hi), ("mana", mp_lo, mp_hi)):
            for slvl, freq in (("1", "3"), ("2", "2"), ("3", "1")):
                rows.append(
                    _make_auto_row(
                        headers, "303", min_lvl, max_lvl, lreq, freq,
                        [(base_stat, "", st_lo, st_hi), ("skill-rand", slvl, full_lo, full_hi)],
                    )
                )
            if k >= 2:
                tk_lo, tk_hi = sor_tiers[k - 1][0], sor_tiers[k - 1][1]
                low_lo, low_hi = sor_tiers[0][0], sor_tiers[k - 2][1]
                for s1, s2, freq in (("2", "1", "2"), ("2", "2", "1"), ("3", "2", "1"), ("3", "3", "1")):
                    rows.append(
                        _make_auto_row(
                            headers, "303", min_lvl, max_lvl, lreq, freq,
                            [
                                (base_stat, "", st_lo, st_hi),
                                ("skill-rand", s1, tk_lo, tk_hi),
                                ("skill-rand", s2, low_lo, low_hi),
                            ],
                        )
                    )
            else:
                mid = full_lo + 2
                rows.append(
                    _make_auto_row(
                        headers, "303", min_lvl, max_lvl, lreq, "2",
                        [
                            (base_stat, "", st_lo, st_hi),
                            ("skill-rand", "2", full_lo, mid),
                            ("skill-rand", "1", mid + 1, full_hi),
                        ],
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

    return write_excel_tsv("automagic.txt", headers, rows)


def build_itemtypes_automagic(cfg: dict) -> str:
    p1 = build_itemtypes(cfg)
    p2 = build_automagic(cfg)
    return f"{p1}, {p2}"

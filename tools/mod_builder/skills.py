#!/usr/bin/env python3
"""
skills.py
Step 11: 7-Class Skill, Synergy & Passive Overhaul
Generates:
  - excel/states.txt (including staminapot fix + custom skill passive states)
  - excel/skills.txt
  - excel/skilldesc.txt
  - data/local/lng/strings/skills.json
And provides apply_skill_missile_updates() called by weapons_armor.py (and build_skills_all).
"""
from typing import Dict, List, Tuple

from mod_builder.common import (
    read_excel_tsv,
    read_strings_json,
    upsert_string_entries,
    write_excel_tsv,
    write_strings_json,
)


def parse_int(val: str, default: int = 0) -> int:
    if not val or not val.strip():
        return default
    try:
        return int(float(val.strip()))
    except ValueError:
        return default


def scale_int(val: str, mult: float, min_val: int = 1) -> str:
    v = parse_int(val, 0)
    if v <= 0:
        return val
    return str(max(min_val, int(round(v * mult))))


# 4-stage non-linear progression formulas replacing linear ln12 / ln34 / ln56:
#   - Levels 1..5:  0.50x step per level (10/20)
#   - Levels 6..10: 0.75x step per level (15/20)
#   - Levels 11..15: 1.15x step per level (23/20)
#   - Levels 16+:   1.50x step per level (30/20)
# At Level 20: (10*19 + 5*15 + 8*10 + 7*5)/20 = 380/20 = 19 -> parA + 19*parB (100% identical to lnAB at Level 20!)
RAMP12 = "(par1+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*par2/20)"
RAMP34 = "(par3+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*par4/20)"
RAMP56 = "(par5+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*par6/20)"


def _curve_lev_brackets(
    row: Dict[str, str],
    base_col: str,
    lev_cols: Tuple[str, str, str, str, str],
    mult: float = 1.0,
) -> None:
    """
    Redistribute Base + Lev1..5 across a non-linear curve (gentle Levels 1-8, medium 9-16, steep 17-22+)
    while preserving the EXACT same total value at Level 20 (Base + 7*L1 + 8*L2 + 4*L3) as linear scaling!
    """
    b0 = parse_int(row.get(base_col, "0"))
    l1 = parse_int(row.get(lev_cols[0], "0"))
    l2 = parse_int(row.get(lev_cols[1], "0"))
    l3 = parse_int(row.get(lev_cols[2], "0"))
    l4 = parse_int(row.get(lev_cols[3], "0"))
    l5 = parse_int(row.get(lev_cols[4], "0"))

    if b0 <= 0 and l1 <= 0:
        return

    # Target total at Level 20 under the linear multiplier
    target_20 = int(round((b0 + 7 * l1 + 8 * l2 + 4 * l3) * mult))

    # Gentle start at Level 1 (~0.70x) and Levels 2-8 (~0.50x), near-normal at Levels 9-16 (~0.90x),
    # and catch up in Levels 17-20 so Level 20 hits target_20!
    new_b0 = max(1, int(round(b0 * mult * 0.70))) if b0 > 0 else 0
    new_l1 = max(1, int(round(l1 * mult * 0.50))) if l1 > 0 else 0
    new_l2 = max(new_l1, int(round(l2 * mult * 0.90))) if l2 > 0 else 0
    rem_for_l3 = target_20 - new_b0 - 7 * new_l1 - 8 * new_l2
    new_l3 = max(new_l2, int(round(rem_for_l3 / 4.0))) if l3 > 0 else 0
    new_l4 = max(new_l3, int(round(l4 * mult * 1.15))) if l4 > 0 else 0
    new_l5 = max(new_l4, int(round(l5 * mult * 1.20))) if l5 > 0 else 0

    if b0 > 0:
        row[base_col] = str(new_b0)
    if l1 > 0:
        row[lev_cols[0]] = str(new_l1)
    if l2 > 0:
        row[lev_cols[1]] = str(new_l2)
    if l3 > 0:
        row[lev_cols[2]] = str(new_l3)
    if l4 > 0:
        row[lev_cols[3]] = str(new_l4)
    if l5 > 0:
        row[lev_cols[4]] = str(new_l5)


# Custom passive/potion states to append to states.txt (each gets a unique ID >= 232)
PALADIN_PASSIVE_STATES = [
    "pal_sacrifice",
    "pal_might",
    "pal_thorns",
    "pal_concentration",
    "pal_conviction",
    "pal_prayer",
    "pal_defiance",
    "pal_cleansing",
    "pal_vigor",
    "pal_meditation",
    "pal_redemption",
    "pal_salvation",
    "hp_cooldown",
]


def build_states(cfg: dict) -> str:
    headers, rows = read_excel_tsv("states.txt")
    existing_states = set()
    max_id = 0
    for r in rows:
        st = r.get("state", "")
        if st:
            existing_states.add(st)
        if st == "staminapot":
            # Keep stambarblue disabled so the HUD stamina bar visibly drains/refills,
            # and use monster-only Inner Sight (white/silver sparkles) while active.
            r["stambarblue"] = ""
            r["overlay1"] = "innersight"
        elif st == "thawing":
            # Monster-only Korlic cold pierce aura overlay while active.
            r["overlay1"] = "korliccoldpierce"
        elif st == "antidote":
            # Monster-only Terror overlay (green swirl in D2R HD) while active.
            r["overlay1"] = "curseterror"
        sid = parse_int(r.get("*ID", ""), -1)
        if sid > max_id:
            max_id = sid

    all_new_states = list(PALADIN_PASSIVE_STATES)
    next_id = max_id + 1
    for st_name in all_new_states:
        if st_name in existing_states:
            continue
        new_row = {h: "" for h in headers}
        new_row["state"] = st_name
        new_row["*ID"] = str(next_id)
        new_row["*eol"] = "0"
        rows.append(new_row)
        existing_states.add(st_name)
        next_id += 1

    return write_excel_tsv("states.txt", headers, rows)


def _apply_paladin_skills(by_name: Dict[str, Dict[str, str]]) -> None:
    """Apply the Paladin Combat, Offensive Aura, and Defensive Aura overhaul to skills.txt."""
    # -------------------------------------------------------------------------
    # 1. COMBAT SKILLS
    # -------------------------------------------------------------------------
    # Sacrifice (Id 96): 250% + 25%/lvl ED; self-damage 12% scaling down to 4% via blvl + Prayer/Redemption;
    # synergies: Prayer (10%), Redemption (10%), Fanaticism (8%); Passive: +1% Open Wounds per blvl
    sac = by_name["Sacrifice"]
    sac["passivestate"] = "pal_sacrifice"
    sac["passivestat1"] = "item_openwounds"
    sac["passivecalc1"] = "skill('Sacrifice'.blvl)"
    sac["Param1"] = "250"  # Damage % baseline
    sac["Param2"] = "25"   # Damage % per level
    sac["Param3"] = "3"    # Self Damage Reduction per level (1/#)
    sac["Param5"] = "12"   # Self Damage % baseline
    sac["Param6"] = "4"    # Self Damage % min
    sac["Param7"] = "8"    # Fanaticism synergy %
    sac["Param8"] = "10"   # Prayer & Redemption synergy %
    sac["calc1"] = f"{RAMP12}+(skill('Prayer'.blvl)+skill('Redemption'.blvl))*par8+skill('Fanaticism'.blvl)*par7"
    sac["calc2"] = "max(par6, par5 - blvl/par3 - (skill('Prayer'.blvl)+skill('Redemption'.blvl))/4)"

    # Smite (Id 97): 30% + 20%/lvl (ramped) ED, 1.0s + 0.24s/lvl stun, +8%/lvl ED synergy from Charge
    smite = by_name["Smite"]
    smite["Param1"] = "25"  # Stun Length baseline (1.0s)
    smite["Param2"] = "6"   # Stun Length per level (+0.24s)
    smite["Param3"] = "30"  # Damage % baseline
    smite["Param4"] = "20"  # Damage % per level
    smite["Param8"] = "8"   # Charge synergy %
    smite["calc1"] = f"{RAMP34}+skill('Charge'.blvl)*par8"

    # Charge (Id 107): 120% + 25%/lvl (ramped) ED, 10% synergy from Vigor & Might, mana 9 -> 6,
    # AND Stuns target on impact! (EType = stun, 1.4s + 0.2s/lvl, +8% stun length/lvl from Smite)
    chg = by_name["Charge"]
    chg["mana"] = "6"
    chg["Param3"] = "120"  # Damage % baseline
    chg["Param4"] = "25"   # Damage % per level
    chg["Param6"] = "8"    # Stun duration synergy % from Smite
    chg["*Param6 Description"] = "Stun Duration synergy"
    chg["Param8"] = "10"   # Damage synergy % from Vigor & Might
    chg["calc1"] = f"{RAMP34}+(skill('Vigor'.blvl)+skill('Might'.blvl))*par8"
    chg["calc4"] = "0"     # 0% physical converted to elemental so 100% stays Physical + Stun
    chg["EType"] = "stun"
    chg["ELen"] = "35"     # 1.4s base stun
    chg["ELevLen1"] = "5"  # +0.2s per level
    chg["ELevLen2"] = "5"
    chg["ELevLen3"] = "5"
    chg["ELenSymPerCalc"] = "skill('Smite'.blvl)*par6"

    # Zeal (Id 106): Capped at 4 hits (2 hits Lvl 1-5, 3 hits Lvl 6-11, 4 hits Lvl 12+),
    # vanilla 100% rollback (so 4-frame hits strictly require EIAS = 75), 15% + 10%/lvl (ramped) ED, +8% Sacrifice synergy
    zeal = by_name["Zeal"]
    zeal["Param2"] = "100"  # % Anim frame rollback (100% = full 7 base frames per swing; 4-hit cap + melee rangeadder prevents whiffing)
    zeal["Param3"] = "15"   # Damage % baseline
    zeal["Param4"] = "10"   # Damage % per level
    zeal["Param5"] = "2"    # # of hits Min
    zeal["Param6"] = "4"    # # of hits Max
    zeal["Param8"] = "8"    # Sacrifice synergy %
    zeal["calc1"] = "min(par5+lvl/6,par6)"
    zeal["calc2"] = f"{RAMP34}+skill('Sacrifice'.blvl)*par8"
    zeal["ToHit"] = "20"
    zeal["LevToHit"] = "12"

    # Vengeance (Id 111): 140% + 16%/lvl (ramped) Fire/Cold/Ltng damage, synergized by Salvation (10%) & Conviction (8%) + Resist auras (8%)
    veng = by_name["Vengeance"]
    veng["manashift"] = "6"
    veng["mana"] = "12"
    veng["lvlmana"] = "1"
    veng["Param1"] = "140"  # Damage % baseline
    veng["Param2"] = "16"   # Damage % per level
    veng["Param7"] = "10"   # Salvation synergy %
    veng["Param8"] = "8"    # Conviction & Resist Fire/Cold/Ltng synergy %
    veng["calc1"] = f"{RAMP12}+(skill('Resist Fire'.blvl)+skill('Conviction'.blvl))*par8+skill('Salvation'.blvl)*par7"
    veng["calc2"] = f"{RAMP12}+(skill('Resist Cold'.blvl)+skill('Conviction'.blvl))*par8+skill('Salvation'.blvl)*par7"
    veng["calc3"] = f"{RAMP12}+(skill('Resist Lightning'.blvl)+skill('Conviction'.blvl))*par8+skill('Salvation'.blvl)*par7"
    veng["ToHit"] = "40"
    veng["LevToHit"] = "15"

    # Blessed Hammer (Id 112): 37.5% Concentration multiplier (Param1 = 3 in 8ths), 8% synergies, non-linear bracket curve
    bham = by_name["Blessed Hammer"]
    bham["Param1"] = "3"    # 3/8 = 37.5% from Concentration
    bham["Param8"] = "8"    # 8% synergy from Blessed Aim & Vigor
    bham["EMinLev4"] = scale_int(bham["EMinLev4"], 1.25)
    bham["EMaxLev4"] = scale_int(bham["EMaxLev4"], 1.25)
    bham["EMinLev5"] = scale_int(bham["EMinLev5"], 1.35)
    bham["EMaxLev5"] = scale_int(bham["EMaxLev5"], 1.35)
    _curve_lev_brackets(bham, "EMin", ("EMinLev1", "EMinLev2", "EMinLev3", "EMinLev4", "EMinLev5"), 1.0)
    _curve_lev_brackets(bham, "EMax", ("EMaxLev1", "EMaxLev2", "EMaxLev3", "EMaxLev4", "EMaxLev5"), 1.0)

    # Conversion (Id 116): 75% weapon damage (SrcDam = 96), 50% + 15%/lvl AR, 10s + 1s/lvl duration
    conv = by_name["Conversion"]
    conv["Param1"] = "250"  # 10s baseline
    conv["Param2"] = "25"   # +1s per level
    conv["ToHit"] = "50"
    conv["LevToHit"] = "15"
    conv["SrcDam"] = "96"

    # Holy Shield (Id 117): Keep vanilla prerequisites so UI arrows match; 1.5x Smite damage (non-linear), ramped Defense, 10% Defiance synergy
    hshd = by_name["Holy Shield"]
    hshd["Param8"] = "10"
    hshd["aurastatcalc2"] = f"{RAMP34}+skill('Defiance'.blvl)*par8"
    hshd["calc1"] = f"{RAMP34}+skill('Defiance'.blvl)*par8"
    _curve_lev_brackets(hshd, "MinDam", ("MinLevDam1", "MinLevDam2", "MinLevDam3", "MinLevDam4", "MinLevDam5"), 1.50)
    _curve_lev_brackets(hshd, "MaxDam", ("MaxLevDam1", "MaxLevDam2", "MaxLevDam3", "MaxLevDam4", "MaxLevDam5"), 1.50)

    # Cleric Trinity 1: Holy Bolt (Id 101) — Non-linear progression preserving exact Level 20 power (267-298)
    # while cutting Level 1-8 spike in half!
    hbolt = by_name["Holy Bolt"]
    hbolt["lvlmana"] = "4"  # +0.25 mana/lvl (in 16ths) instead of +0.0625/lvl
    hbolt["Param7"] = "15"  # Healing synergy from Prayer
    hbolt["Param8"] = "12"  # Damage synergy from Sanctuary & Fist of the Heavens
    hbolt["calc1"] = f"{RAMP12} * (100 + skill('Prayer'.blvl) * par7) / 100"
    hbolt["calc2"] = f"{RAMP34} * (100 + skill('Prayer'.blvl) * par7) / 100"
    hbolt["EMin"] = "8"
    hbolt["EMinLev1"] = "5"
    hbolt["EMinLev2"] = "14"
    hbolt["EMinLev3"] = "28"
    hbolt["EMinLev4"] = "28"
    hbolt["EMinLev5"] = "32"
    hbolt["EMax"] = "16"
    hbolt["EMaxLev1"] = "6"
    hbolt["EMaxLev2"] = "15"
    hbolt["EMaxLev3"] = "30"
    hbolt["EMaxLev4"] = "30"
    hbolt["EMaxLev5"] = "35"
    hbolt["EDmgSymPerCalc"] = "(skill('Fist of the Heavens'.blvl)+skill('Sanctuary'.blvl))*par8"

    # Cleric Trinity 2: Fist of the Heavens (Id 121) — Non-linear progression preserving Level 20 power (1002-1082)
    foh = by_name["Fist of the Heavens"]
    foh["localdelay"] = "25"  # 1.0s tactical nuke cooldown
    foh["mana"] = "35"
    foh["lvlmana"] = "2"
    foh["Param8"] = "12"  # 12% Lightning synergy from Holy Shock only
    foh["EMin"] = "160"
    foh["EMinLev1"] = "12"
    foh["EMinLev2"] = "42"
    foh["EMinLev3"] = "105"
    foh["EMinLev4"] = "105"
    foh["EMinLev5"] = "120"
    foh["EMax"] = "220"
    foh["EMaxLev1"] = "14"
    foh["EMaxLev2"] = "44"
    foh["EMaxLev3"] = "103"
    foh["EMaxLev4"] = "105"
    foh["EMaxLev5"] = "120"
    foh["EDmgSymPerCalc"] = "skill('Holy Shock'.blvl)*par8"

    # -------------------------------------------------------------------------
    # 2. OFFENSIVE AURAS
    # -------------------------------------------------------------------------
    # Might (Id 98): 40% + 12%/lvl (ramped) active ED; holds pal_might passive state for Might (+2% ED/blvl)
    # and for its child offensive auras that use passivestat1..6 for active-only self buffs
    might = by_name["Might"]
    might["Param4"] = "12"
    might["aurastatcalc1"] = RAMP34
    might["passivestate"] = "pal_might"
    might["passivestat1"] = "damagepercent"
    might["passivecalc1"] = "skill('Might'.blvl)*2"
    might["passivestat2"] = "passive_fire_mastery"
    might["passivecalc2"] = "skill('Holy Fire'.blvl)/2"
    might["passivestat3"] = "passive_cold_mastery"
    might["passivecalc3"] = "skill('Holy Freeze'.blvl)/2"
    might["passivestat4"] = "passive_ltng_mastery"
    might["passivecalc4"] = "skill('Holy Shock'.blvl)/2"
    might["passivestat5"] = "passive_mag_mastery"
    might["passivecalc5"] = "skill('Sanctuary'.blvl)/2"
    might["passivestat6"] = "item_fasterattackrate"
    might["passivecalc6"] = "skill('Fanaticism'.blvl)/2"

    # Holy Fire (Id 102): ~1.5x Level-20 pulse & on-hit fire damage with non-linear curve (gentle Levels 1-8!),
    # 12% Resist Fire / 8% Salvation synergies
    hfire = by_name["Holy Fire"]
    hfire["Param7"] = "8"
    hfire["Param8"] = "12"
    _curve_lev_brackets(hfire, "EMin", ("EMinLev1", "EMinLev2", "EMinLev3", "EMinLev4", "EMinLev5"), 1.50)
    _curve_lev_brackets(hfire, "EMax", ("EMaxLev1", "EMaxLev2", "EMaxLev3", "EMaxLev4", "EMaxLev5"), 1.50)

    # Thorns (Id 103): 3.0x Level-20 flat thorns (non-linear), ramped % thorns, active Flat PDR (lvl + blvl), passive +2 flat thorns/blvl
    thorns = by_name["Thorns"]
    thorns["aurastatcalc2"] = RAMP34
    thorns["aurastat3"] = "normal_damage_reduction"
    thorns["aurastatcalc3"] = "lvl+blvl"
    thorns["passivestate"] = "pal_thorns"
    thorns["passivestat1"] = "item_attackertakesdamage"
    thorns["passivecalc1"] = "skill('Thorns'.blvl)*2"
    _curve_lev_brackets(thorns, "MinDam", ("MinLevDam1", "MinLevDam2", "MinLevDam3", "MinLevDam4", "MinLevDam5"), 3.00)

    # Blessed Aim (Id 108): Ramped active Attack Rating %
    baim = by_name["Blessed Aim"]
    baim["aurastatcalc1"] = RAMP34

    # Concentration (Id 113): 60% + 22%/lvl (ramped -> +478% ED at Lvl 20 vs Fanaticism's +373% Self / +248% Party),
    # 25% uninterruptible, passive +1% FHR per hard point
    conc = by_name["Concentration"]
    conc["Param3"] = "60"
    conc["Param4"] = "22"
    conc["Param5"] = "25"
    conc["aurastatcalc1"] = RAMP34
    conc["passivestate"] = "pal_concentration"
    conc["passivestat1"] = "item_fastergethitrate"
    conc["passivecalc1"] = "skill('Concentration'.blvl)"

    # Holy Freeze (Id 114): ~1.4x Level-20 pulse & on-hit cold damage (non-linear curve), 50% max slow, 10% / 8% synergies
    hfrz = by_name["Holy Freeze"]
    hfrz["Param4"] = "50"
    hfrz["Param7"] = "8"
    hfrz["Param8"] = "10"
    _curve_lev_brackets(hfrz, "EMin", ("EMinLev1", "EMinLev2", "EMinLev3", "EMinLev4", "EMinLev5"), 1.40)
    _curve_lev_brackets(hfrz, "EMax", ("EMaxLev1", "EMaxLev2", "EMaxLev3", "EMaxLev4", "EMaxLev5"), 1.40)

    # Holy Shock (Id 118): ~1.25x Level-20 pulse & on-hit lightning damage (non-linear curve), 10% / 8% synergies
    hshk = by_name["Holy Shock"]
    hshk["Param7"] = "8"
    hshk["Param8"] = "10"
    _curve_lev_brackets(hshk, "EMax", ("EMaxLev1", "EMaxLev2", "EMaxLev3", "EMaxLev4", "EMaxLev5"), 1.25)

    # Cleric Trinity 3: Sanctuary (Id 119): 2.0x Level-20 radial Magic pulse (non-linear), synergized by Holy Bolt (10%) + FoH (10%),
    # Active bonus: ramped Magic Skill Damage (15% -> 72% at Lvl 20) + ramped Undead/Demon Damage & AR.
    sanc = by_name["Sanctuary"]
    sanc["passivestat1"] = "item_undeaddamage_percent"
    sanc["passivecalc1"] = RAMP34
    sanc["passivestat2"] = "item_undead_tohit"
    sanc["passivecalc2"] = RAMP56
    sanc["passivestat4"] = "item_demondamage_percent"
    sanc["passivecalc4"] = RAMP34
    sanc["passivestat5"] = "item_demon_tohit"
    sanc["passivecalc5"] = RAMP56
    sanc["passivestat6"] = "passive_mag_mastery"
    sanc["passivecalc6"] = "18+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*3/20"
    sanc["Param8"] = "10"
    _curve_lev_brackets(sanc, "EMin", ("EMinLev1", "EMinLev2", "EMinLev3", "EMinLev4", "EMinLev5"), 2.00)
    _curve_lev_brackets(sanc, "EMax", ("EMaxLev1", "EMaxLev2", "EMaxLev3", "EMaxLev4", "EMaxLev5"), 2.00)
    sanc["EDmgSymPerCalc"] = "(skill('Holy Bolt'.blvl)+skill('Fist of the Heavens'.blvl))*par8"

    # Fanaticism (Id 122): Ramped self ED (RAMP56) & Party ED share (RAMP56*2/3);
    # Attack Speed % Max (Param4) tuned from 40 -> 30 (+27 SIAS at Lvl 20) so hitting 4-frame max cap on slow weapons requires multi-slot IAS investment
    fana = by_name["Fanaticism"]
    fana["Param4"] = "30"
    fana["passivecalc1"] = RAMP56
    fana["aurastatcalc3"] = f"{RAMP56}*2/3"

    # Conviction (Id 123, "Aura of Guilt"): Ramped -Enemy Res (cap -100%),
    # adds Enemy Physical Damage Reduction (-10 - lvl) & Enemy Slow (-10 - lvl/2);
    # Passive: -1% Enemy Fire/Cold/Ltng Res per 4 hard points
    convic = by_name["Conviction"]
    convic["Param3"] = "20"
    convic["Param4"] = "4"
    convic["aurastatcalc2"] = f"-min({RAMP34},100)"
    convic["aurastatcalc3"] = f"-min({RAMP34},100)"
    convic["aurastatcalc4"] = f"-min({RAMP34},100)"
    convic["aurastat5"] = "damagepercent"
    convic["aurastatcalc5"] = "-10-lvl"
    convic["aurastat6"] = "velocitypercent"
    convic["aurastatcalc6"] = "-10-lvl/2"
    convic["passivestate"] = "pal_conviction"
    convic["passivestat1"] = "passive_fire_pierce"
    convic["passivecalc1"] = "skill('Conviction'.blvl)/4"
    convic["passivestat2"] = "passive_cold_pierce"
    convic["passivecalc2"] = "skill('Conviction'.blvl)/4"
    convic["passivestat3"] = "passive_ltng_pierce"
    convic["passivecalc3"] = "skill('Conviction'.blvl)/4"

    # -------------------------------------------------------------------------
    # 3. DEFENSIVE AURAS
    # -------------------------------------------------------------------------
    # Prayer (Id 99): 0 mana cost, 1.5x Level-20 base healing (non-linear), passive +1 Replenish Life per hard point
    pray = by_name["Prayer"]
    pray["mana"] = "0"
    pray["lvlmana"] = "0"
    pray["passivestate"] = "pal_prayer"
    pray["passivestat1"] = "hpregen"
    pray["passivecalc1"] = "skill('Prayer'.blvl)"
    _curve_lev_brackets(pray, "MinDam", ("MinLevDam1", "MinLevDam2", "MinLevDam3", "MinLevDam4", "MinLevDam5"), 1.50)

    # Resist Fire / Cold / Lightning (Id 100, 105, 110):
    # Replace front-loaded dm34 (52% at Lvl 1!) with RAMP34 starting at 25% (Param3=25, Param4=6 -> 25% at Lvl 1, 139% at Lvl 20),
    # keep +1% Max Res per 2 blvl AND +2% Base Res per blvl
    for res_name, res_stat in (
        ("Resist Fire", "fireresist"),
        ("Resist Cold", "coldresist"),
        ("Resist Lightning", "lightresist"),
    ):
        raura = by_name[res_name]
        raura["Param3"] = "25"
        raura["Param4"] = "6"
        raura["aurastatcalc1"] = RAMP34
        raura["passivestat2"] = res_stat
        raura["passivecalc2"] = f"skill('{res_name}'.blvl)*2"

    # Defiance (Id 104): 80% + 12%/lvl (ramped) active Defense, passive +3% Defense per hard point
    defi = by_name["Defiance"]
    defi["Param3"] = "80"
    defi["Param4"] = "12"
    defi["aurastatcalc1"] = RAMP34
    defi["passivestate"] = "pal_defiance"
    defi["passivestat1"] = "item_armor_percent"
    defi["passivecalc1"] = "skill('Defiance'.blvl)*3"

    # Cleansing (Id 109): Also reduces Curse Duration (curse_resistance = dm34), passive +2% PLR per hard point
    clns = by_name["Cleansing"]
    clns["aurastat3"] = "curse_resistance"
    clns["aurastatcalc3"] = "dm34"
    clns["passivestate"] = "pal_cleansing"
    clns["passivestat1"] = "item_poisonlengthresist"
    clns["passivecalc1"] = "skill('Cleansing'.blvl)*2"

    # Vigor (Id 115): Passive +1% FRW per 2 hard points + +5% Stamina Regen per hard point
    vig = by_name["Vigor"]
    vig["passivestate"] = "pal_vigor"
    vig["passivestat1"] = "item_fastermovevelocity"
    vig["passivecalc1"] = "skill('Vigor'.blvl)/2"
    vig["passivestat2"] = "staminarecoverybonus"
    vig["passivecalc2"] = "skill('Vigor'.blvl)*5"

    # Meditation (Id 120): Ramped active Mana Recovery %, passive +5% Mana Recovery per hard point
    medi = by_name["Meditation"]
    medi["aurastatcalc1"] = RAMP34
    medi["passivestate"] = "pal_meditation"
    medi["passivestat1"] = "manarecoverybonus"
    medi["passivecalc1"] = "skill('Meditation'.blvl)*5"

    # Redemption (Id 124): 40 + 8/lvl (ramped) HP & Mana redeemed, passive +1 Life After Each Kill per 2 hard points
    redm = by_name["Redemption"]
    redm["Param5"] = "40"
    redm["Param6"] = "8"
    redm["calc2"] = RAMP56
    redm["calc3"] = RAMP56
    redm["passivestate"] = "pal_redemption"
    redm["passivestat1"] = "item_healafterkill"
    redm["passivecalc1"] = "skill('Redemption'.blvl)/2"

    # Salvation (Id 125): Ramped 25% + 5%/lvl (25% at Lvl 1 -> 120% All-Res at Lvl 20 instead of 71% at Lvl 1),
    # passive +1% All Resistances per hard point
    salv = by_name["Salvation"]
    salv["Param3"] = "25"
    salv["Param4"] = "5"
    salv["aurastatcalc1"] = RAMP34
    salv["aurastatcalc2"] = RAMP34
    salv["aurastatcalc3"] = RAMP34
    salv["passivestate"] = "pal_salvation"
    salv["passivestat1"] = "fireresist"
    salv["passivecalc1"] = "skill('Salvation'.blvl)"
    salv["passivestat2"] = "coldresist"
    salv["passivecalc2"] = "skill('Salvation'.blvl)"
    salv["passivestat3"] = "lightresist"
    salv["passivecalc3"] = "skill('Salvation'.blvl)"
    salv["passivestat4"] = "poisonresist"
    salv["passivecalc4"] = "skill('Salvation'.blvl)"


def _set_dsc_line(row: Dict[str, str], prefix: str, idx: int, ltype: str, ta: str = "", tb: str = "", ca: str = "", cb: str = "") -> None:
    row[f"{prefix}line{idx}"] = ltype
    row[f"{prefix}texta{idx}"] = ta
    row[f"{prefix}textb{idx}"] = tb
    row[f"{prefix}calca{idx}"] = ca
    row[f"{prefix}calcb{idx}"] = cb


def _clear_dsc3_synergies(row: Dict[str, str], skill_title_key: str) -> None:
    _set_dsc_line(row, "dsc3", 1, "40", "Sksyn", skill_title_key, "2", "")
    for i in range(2, 8):
        _set_dsc_line(row, "dsc3", i, "", "", "", "", "")


def _apply_paladin_skilldesc(by_desc: Dict[str, Dict[str, str]]) -> None:
    """Synchronize skilldesc.txt tooltips with all Paladin skill, passive, and synergy changes."""
    # 1. Sacrifice
    sac = by_desc["sacrifice"]
    sac["ddam calc1"] = "clc1"
    sac["desccalca1"] = "clc1"
    sac["desccalca4"] = "clc2"
    _set_dsc_line(sac, "dsc2", 1, "74", "ModPassiveOpenWounds", "", "(skill('Sacrifice'.blvl)<1)?1:skill('Sacrifice'.blvl)", "")
    _clear_dsc3_synergies(sac, "skillname96")
    _set_dsc_line(sac, "dsc3", 2, "76", "Damplev", "skillname99", "par8", "")
    _set_dsc_line(sac, "dsc3", 3, "76", "Damplev", "skillname124", "par8", "")
    _set_dsc_line(sac, "dsc3", 4, "76", "Damplev", "skillname122", "par7", "")

    # 2. Smite
    smite = by_desc["smite"]
    smite["desccalca2"] = "clc1"
    _clear_dsc3_synergies(smite, "skillname97")
    _set_dsc_line(smite, "dsc3", 2, "76", "Damplev", "skillname107", "par8", "")

    # 3. Charge (Display Ramped ED + Stun Length + Smite Stun Synergy!)
    chg = by_desc["charge"]
    chg["ddam calc1"] = "clc1"
    chg["desccalca1"] = "clc1"
    _set_dsc_line(chg, "desc", 3, "36", "StrSkillStunLengthSingular", "StrSkill48", "min(250,edln)", "25")
    _clear_dsc3_synergies(chg, "skillname107")
    _set_dsc_line(chg, "dsc3", 2, "76", "Damplev", "skillname98", "par8", "")
    _set_dsc_line(chg, "dsc3", 3, "76", "Damplev", "skillname115", "par8", "")
    _set_dsc_line(chg, "dsc3", 4, "76", "Durateplev", "skillname97", "par6", "")

    # 4. Zeal
    zeal = by_desc["zeal"]
    zeal["ddam calc1"] = "clc2"
    zeal["desccalca1"] = "clc2"
    zeal["desccalca3"] = "clc1"

    # 4b. Holy Shield (Display Ramped Defense %)
    hshd = by_desc["holy shield"]
    hshd["desccalca3"] = "clc1"

    # 5. Vengeance
    veng = by_desc["vengeance"]
    veng["desccalca2"] = "clc3"
    veng["desccalca4"] = "clc2"
    veng["desccalca5"] = "clc1"
    _clear_dsc3_synergies(veng, "skillname111")
    _set_dsc_line(veng, "dsc3", 2, "76", "ElemDampLev", "skillname125", "par7", "")
    _set_dsc_line(veng, "dsc3", 3, "76", "ElemDampLev", "skillname123", "par8", "")
    _set_dsc_line(veng, "dsc3", 4, "76", "Firedplev", "skillname100", "par8", "")
    _set_dsc_line(veng, "dsc3", 5, "76", "Colddplev", "skillname105", "par8", "")
    _set_dsc_line(veng, "dsc3", 6, "76", "Ltngdplev", "skillname110", "par8", "")

    # 5b. Conversion (Display Attack Rating +X% and 3/4 Weapon Damage!)
    conv = by_desc["conversion"]
    _set_dsc_line(conv, "desc", 2, "74", "StrSkill22", "", "toht", "")
    _set_dsc_line(conv, "dsc2", 1, "74", "WeapDamsk", "", "96*100/128", "")

    # 6. Cleric Trinity: Holy Bolt, Sanctuary, Fist of the Heavens
    hb = by_desc["holy bolt"]
    hb["desccalca2"] = "clc1"
    hb["desccalcb2"] = "clc2"
    _clear_dsc3_synergies(hb, "skillname101")
    _set_dsc_line(hb, "dsc3", 2, "76", "Magdplev", "skillname119", "par8", "")
    _set_dsc_line(hb, "dsc3", 3, "76", "Magdplev", "skillname121", "par8", "")
    _set_dsc_line(hb, "dsc3", 4, "76", "Healplev", "skillname99", "par7", "")

    sanc = by_desc["sanctuary"]
    sanc["desccalca3"] = RAMP34
    _set_dsc_line(sanc, "desc", 4, "74", "ModActiveMagSkillDmg", "", "18+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*3/20", "")
    _set_dsc_line(sanc, "desc", 5, "74", "ModActiveDmgToDemons", "", RAMP34, "")
    _set_dsc_line(sanc, "dsc2", 2, "74", "ModPassiveMagSkillDmg", "", "(skill('Sanctuary'.blvl)<2)?1:(skill('Sanctuary'.blvl)/2)", "")
    _clear_dsc3_synergies(sanc, "skillname119")
    _set_dsc_line(sanc, "dsc3", 2, "76", "Magdplev", "skillname101", "par8", "")
    _set_dsc_line(sanc, "dsc3", 3, "76", "Magdplev", "skillname121", "par8", "")

    foh = by_desc["fist of the heavens"]
    foh["desccalca5"] = "25"  # 1.0s casting delay display
    _clear_dsc3_synergies(foh, "skillname121")
    _set_dsc_line(foh, "dsc3", 2, "76", "Hbdplev", "skillname101", "12", "")
    _set_dsc_line(foh, "dsc3", 3, "76", "Hbdplev", "skillname119", "12", "")
    _set_dsc_line(foh, "dsc3", 4, "76", "Ltngdplev", "skillname118", "par8", "")

    # 7. Offensive & Defensive Aura Tooltips
    might = by_desc["might"]
    might["desccalca2"] = RAMP34
    _set_dsc_line(might, "dsc2", 1, "74", "ModPassiveED", "", "(skill('Might'.blvl)<1)?2:(skill('Might'.blvl)*2)", "")

    baim = by_desc["blessed aim"]
    baim["desccalca3"] = RAMP34

    hfire = by_desc["holy fire"]
    _set_dsc_line(hfire, "dsc2", 2, "74", "ModPassiveFireSkillDmg", "", "(skill('Holy Fire'.blvl)<2)?1:(skill('Holy Fire'.blvl)/2)", "")

    thorns = by_desc["thorns"]
    thorns["desccalca3"] = RAMP34
    _set_dsc_line(thorns, "desc", 4, "74", "ModActiveFlatPDR", "", "lvl+blvl", "")
    _set_dsc_line(thorns, "dsc2", 1, "74", "ModPassiveThorns", "", "(skill('Thorns'.blvl)<1)?2:(skill('Thorns'.blvl)*2)", "")

    conc = by_desc["concentration"]
    conc["desccalca2"] = RAMP34
    _set_dsc_line(conc, "dsc2", 2, "74", "ModPassiveFHR", "", "(skill('Concentration'.blvl)<1)?1:skill('Concentration'.blvl)", "")

    hfrz = by_desc["holy freeze"]
    _set_dsc_line(hfrz, "dsc2", 2, "74", "ModPassiveColdSkillDmg", "", "(skill('Holy Freeze'.blvl)<2)?1:(skill('Holy Freeze'.blvl)/2)", "")

    hshk = by_desc["holy shock"]
    _set_dsc_line(hshk, "dsc2", 2, "74", "ModPassiveLtngSkillDmg", "", "(skill('Holy Shock'.blvl)<2)?1:(skill('Holy Shock'.blvl)/2)", "")

    fana = by_desc["fanaticism"]
    fana["desccalca3"] = f"{RAMP56}*2/3"
    fana["desccalca4"] = RAMP56
    _set_dsc_line(fana, "dsc2", 1, "74", "ModPassiveIAS", "", "(skill('Fanaticism'.blvl)<2)?1:(skill('Fanaticism'.blvl)/2)", "")

    convic = by_desc["conviction"]
    convic["desccalca2"] = f"-min({RAMP34},100)"
    _set_dsc_line(convic, "desc", 4, "74", "StrSkill38", "", "-10-lvl", "")
    _set_dsc_line(convic, "desc", 5, "74", "Cgslow", "", "10+lvl/2", "")
    _set_dsc_line(convic, "dsc2", 1, "74", "ModPassiveElemPierce", "", "(skill('Conviction'.blvl)<4)?1:(skill('Conviction'.blvl)/4)", "")

    pray = by_desc["prayer"]
    _set_dsc_line(pray, "desc", 1, "", "", "", "", "")  # Clear mana cost line since Prayer now costs 0 mana
    _set_dsc_line(pray, "dsc2", 1, "74", "ModPassiveLifeRegen", "", "(skill('Prayer'.blvl)<1)?1:skill('Prayer'.blvl)", "")

    rfire = by_desc["resist fire"]
    rfire["desccalca4"] = RAMP34
    _set_dsc_line(rfire, "dsc2", 1, "74", "ModPassiveFireRes", "", "(skill('Resist Fire'.blvl)<1)?2:(skill('Resist Fire'.blvl)*2)", "")

    rcold = by_desc["resist cold"]
    rcold["desccalca4"] = RAMP34
    _set_dsc_line(rcold, "dsc2", 1, "74", "ModPassiveColdRes", "", "(skill('Resist Cold'.blvl)<1)?2:(skill('Resist Cold'.blvl)*2)", "")

    rltng = by_desc["resist lightning"]
    rltng["desccalca4"] = RAMP34
    _set_dsc_line(rltng, "dsc2", 1, "74", "ModPassiveLtngRes", "", "(skill('Resist Lightning'.blvl)<1)?2:(skill('Resist Lightning'.blvl)*2)", "")

    defi = by_desc["defiance"]
    defi["desccalca2"] = RAMP34
    _set_dsc_line(defi, "dsc2", 1, "74", "ModPassiveDefPct", "", "(skill('Defiance'.blvl)<1)?3:(skill('Defiance'.blvl)*3)", "")

    clns = by_desc["cleansing"]
    _set_dsc_line(clns, "desc", 3, "74", "StrSkill85", "", "dm34", "")
    _set_dsc_line(clns, "dsc2", 2, "74", "ModPassivePLR", "", "(skill('Cleansing'.blvl)<1)?2:(skill('Cleansing'.blvl)*2)", "")

    vig = by_desc["vigor"]
    _set_dsc_line(vig, "dsc2", 1, "74", "ModPassiveFRW", "", "(skill('Vigor'.blvl)<2)?1:(skill('Vigor'.blvl)/2)", "")
    _set_dsc_line(vig, "dsc2", 2, "74", "ModPassiveStamRegen", "", "(skill('Vigor'.blvl)<1)?5:(skill('Vigor'.blvl)*5)", "")

    medi = by_desc["meditation"]
    medi["desccalca2"] = RAMP34
    _set_dsc_line(medi, "dsc2", 2, "74", "ModPassiveManaRegen", "", "(skill('Meditation'.blvl)<1)?5:(skill('Meditation'.blvl)*5)", "")

    redm = by_desc["redemption"]
    redm["desccalca1"] = RAMP56
    _set_dsc_line(redm, "dsc2", 1, "74", "ModPassiveLAEK", "", "(skill('Redemption'.blvl)<2)?1:(skill('Redemption'.blvl)/2)", "")

    salv = by_desc["salvation"]
    salv["desccalca2"] = RAMP34
    _set_dsc_line(salv, "dsc2", 1, "74", "ModPassiveAllRes", "", "(skill('Salvation'.blvl)<1)?1:skill('Salvation'.blvl)", "")


def apply_skill_missile_updates(rows_by_name: Dict[str, Dict[str, str]]) -> None:
    """Apply skill-related missile updates (called by weapons_armor.build_missiles and build_skills_all)."""
    # 1. Holy Bolt: Velocity 20 -> 30 for crisp line piercing & ally healing
    if "holybolt" in rows_by_name:
        hb = rows_by_name["holybolt"]
        hb["Vel"] = "30"
        hb["MaxVel"] = "30"

    # 2. Fist of the Heavens radial Holy Bolts: Velocity 12 -> 18, ~1.35x base damage,
    # synergized by Holy Bolt (12%) + Sanctuary (12%) + active Sanctuary bonus (+25%)
    if "fistoftheheavensbolt" in rows_by_name:
        fohb = rows_by_name["fistoftheheavensbolt"]
        fohb["Vel"] = "18"
        fohb["MaxVel"] = "18"
        fohb["EMin"] = "40"
        fohb["MinELev1"] = "4"
        fohb["MinELev2"] = "13"
        fohb["MinELev3"] = "35"
        fohb["MinELev4"] = "44"
        fohb["MinELev5"] = "65"
        fohb["EMax"] = "50"
        fohb["MaxELev1"] = "5"
        fohb["MaxELev2"] = "14"
        fohb["MaxELev3"] = "32"
        fohb["MaxELev4"] = "44"
        fohb["MaxELev5"] = "65"
        fohb["EDmgSymPerCalc"] = "(skill('Holy Bolt'.blvl)+skill('Sanctuary'.blvl))*12"

    # 3. Chest & Environmental Trap Missiles:
    #    Scale raw pre-resistance trap damage to ~100% of expected character Life across Normal,
    #    Nightmare, and Hell (so a character with ~50% resistance loses ~50% of their Life total,
    #    while wide min-max roll variance makes opening chests with low resistances genuinely dangerous).
    #    Note: D2Game.dll evaluates chest trap missiles at sLvl = max(1, AreaLevel // 4) (sLvl 1..21).
    if "trapnova" in rows_by_name:
        tn = rows_by_name["trapnova"]
        tn["HitShift"] = "8"
        tn["EType"] = "ltng"
        tn["EMin"] = "40"
        tn["MinELev1"] = "35"
        tn["MinELev2"] = "45"
        tn["MinELev3"] = "60"
        tn["MinELev4"] = "70"
        tn["MinELev5"] = "80"
        tn["EMax"] = "180"
        tn["MaxELev1"] = "105"
        tn["MaxELev2"] = "135"
        tn["MaxELev3"] = "180"
        tn["MaxELev4"] = "210"
        tn["MaxELev5"] = "240"

    if "trapfirebolt" in rows_by_name:
        tfb = rows_by_name["trapfirebolt"]
        tfb["HitShift"] = "8"
        tfb["EType"] = "fire"
        # Fires a burst of 3-4 bolts; each bolt hits for ~30-35% of single-hit trap damage
        tfb["EMin"] = "20"
        tfb["MinELev1"] = "14"
        tfb["MinELev2"] = "18"
        tfb["MinELev3"] = "24"
        tfb["MinELev4"] = "28"
        tfb["MinELev5"] = "32"
        tfb["EMax"] = "65"
        tfb["MaxELev1"] = "36"
        tfb["MaxELev2"] = "48"
        tfb["MaxELev3"] = "64"
        tfb["MaxELev4"] = "75"
        tfb["MaxELev5"] = "85"

    if "fireexplosion" in rows_by_name:
        fe = rows_by_name["fireexplosion"]
        fe["HitShift"] = "8"
        fe["EType"] = "fire"
        fe["EMin"] = "55"
        fe["MinELev1"] = "35"
        fe["MinELev2"] = "45"
        fe["MinELev3"] = "60"
        fe["MinELev4"] = "70"
        fe["MinELev5"] = "80"
        fe["EMax"] = "165"
        fe["MaxELev1"] = "95"
        fe["MaxELev2"] = "125"
        fe["MaxELev3"] = "165"
        fe["MaxELev4"] = "195"
        fe["MaxELev5"] = "225"

    if "trappoisonjavcloud" in rows_by_name:
        tpj = rows_by_name["trappoisonjavcloud"]
        tpj["EType"] = "pois"
        tpj["ELen"] = "200"  # 8 seconds (down from 20s so the poison bite is felt urgently)
        tpj["EMin"] = "45"
        tpj["MinELev1"] = "28"
        tpj["MinELev2"] = "36"
        tpj["MinELev3"] = "48"
        tpj["MinELev4"] = "56"
        tpj["MinELev5"] = "64"
        tpj["EMax"] = "95"
        tpj["MaxELev1"] = "52"
        tpj["MaxELev2"] = "68"
        tpj["MaxELev3"] = "88"
        tpj["MaxELev4"] = "104"
        tpj["MaxELev5"] = "120"

    if "primepoisoncloud" in rows_by_name:
        ppc = rows_by_name["primepoisoncloud"]
        ppc["EType"] = "pois"
        ppc["ELen"] = "200"
        ppc["EMin"] = "45"
        ppc["MinELev1"] = "28"
        ppc["MinELev2"] = "36"
        ppc["MinELev3"] = "48"
        ppc["MinELev4"] = "56"
        ppc["MinELev5"] = "64"
        ppc["EMax"] = "95"
        ppc["MaxELev1"] = "52"
        ppc["MaxELev2"] = "68"
        ppc["MaxELev3"] = "88"
        ppc["MaxELev4"] = "104"
        ppc["MaxELev5"] = "120"

    for gas_name, gmin, gmax in (
        ("rancidgascloud", "140", "240"),
        ("chokinggascloud", "320", "540"),
        ("stranglinggascloud", "600", "980"),
    ):
        if gas_name in rows_by_name:
            gc = rows_by_name[gas_name]
            gc["EType"] = "pois"
            gc["ELen"] = "100"  # 4 seconds
            gc["EMin"] = gmin
            gc["EMax"] = gmax
            gc["MinELev1"] = "24"
            gc["MinELev2"] = "32"
            gc["MinELev3"] = "42"
            gc["MinELev4"] = "50"
            gc["MinELev5"] = "58"
            gc["MaxELev1"] = "42"
            gc["MaxELev2"] = "56"
            gc["MaxELev3"] = "74"
            gc["MaxELev4"] = "88"
            gc["MaxELev5"] = "102"


def build_skills_and_desc(cfg: dict) -> Tuple[str, str]:
    s_headers, s_rows = read_excel_tsv("skills.txt")
    by_name = {r["skill"]: r for r in s_rows if r.get("skill")}

    # Stretch the 6 skill tier unlock requirements across the full 1-48 Normal difficulty curve:
    # Vanilla: 1 / 6 / 12 / 18 / 24 / 30  ->  Mod: 1 / 8 / 16 / 24 / 32 / 40
    tier_reqlevel_map = {
        "1": "1",
        "6": "8",
        "12": "16",
        "18": "24",
        "24": "32",
        "30": "40",
    }
    for r in s_rows:
        if r.get("charclass"):
            rl = r.get("reqlevel", "")
            if rl in tier_reqlevel_map:
                r["reqlevel"] = tier_reqlevel_map[rl]
        # Scale down staffmod / skill cost multipliers (0.28x) and flat cost additions (0.22x)
        # so multi-staffmod Wands, Staves, Scepters, Orbs, Pelts & Helms cap near ~300,000g
        # instead of vanilla's 800,000g - 1,800,000g.
        if r.get("cost mult"):
            r["cost mult"] = scale_int(r["cost mult"], 0.28, min_val=1)
        if r.get("cost add"):
            r["cost add"] = scale_int(r["cost add"], 0.22, min_val=1)

    d_headers, d_rows = read_excel_tsv("skilldesc.txt")
    by_desc = {r["skilldesc"]: r for r in d_rows if r.get("skilldesc")}

    _apply_paladin_skills(by_name)
    _apply_paladin_skilldesc(by_desc)

    # Scale Monster/Object Trap Skills (PoisonBallTrap, CursedBallTrapRight/Left, Trap Nova, PrimePoisonNova)
    for t_skill in ("PoisonBallTrap", "CursedBallTrapRight", "CursedBallTrapLeft"):
        if t_skill in by_name:
            ts = by_name[t_skill]
            ts["HitShift"] = "8"
            ts["MinDam"] = "55"
            ts["MinLevDam1"] = "35"
            ts["MinLevDam2"] = "45"
            ts["MinLevDam3"] = "60"
            ts["MinLevDam4"] = "70"
            ts["MinLevDam5"] = "80"
            ts["MaxDam"] = "165"
            ts["MaxLevDam1"] = "95"
            ts["MaxLevDam2"] = "125"
            ts["MaxLevDam3"] = "165"
            ts["MaxLevDam4"] = "195"
            ts["MaxLevDam5"] = "225"

    # Populate HireableIconCel (0..28 in Spells/Hireables/HrSkillIcon) for custom Mercenary skills
    # so HireMenuPanelHD & HirelingInventoryPanelHD always render a visible skill icon next to tooltips.
    merc_hireable_icons = {
        "cleansing": "6",          # Prayer / Healing aura icon
        "meditation": "6",         # Prayer / Meditation aura icon
        "salvation": "7",          # Defiance / Defensive aura icon
        "vigor": "8",              # Blessed Aim / Utility aura icon
        "sanctuary": "9",          # Thorns / Radiant aura icon
        "redemption": "9",         # Thorns / Radiant aura icon
        "concentration": "11",     # Might / Offensive aura icon
        "fanaticism": "11",        # Might / Offensive aura icon
        "holy fire": "15",         # Enchant / Fire aura icon
        "holy shock": "21",        # Static Field / Lightning aura icon
        "fire mastery": "14",      # Fire Ball icon
        "cold mastery": "18",      # Frozen Armor icon
        "lightning mastery": "20", # Lightning icon
        "multiple shot": "1",      # Bow arrow icon
        "strafe": "2",             # Volley arrow icon
        "critical strike": "0",    # Inner Sight icon
        "weaken": "24",            # Debuff warcry/curse icon
        "life tap": "24",          # Debuff warcry/curse icon
        "lower resist": "24",      # Debuff warcry/curse icon
        "dim vision": "0",         # Vision debuff icon
        "slow missiles": "0",      # Missile debuff icon
        "decrepify": "24",         # Debuff warcry/curse icon
        "cloak of shadows": "0",   # Shadow debuff icon
        "amplify damage": "24",    # Debuff warcry/curse icon
        "battle orders": "24",     # Warcry icon
        "double swing": "26",      # Frenzy dual-swing icon
    }
    for sdesc_key, cel_idx in merc_hireable_icons.items():
        if sdesc_key in by_desc and not by_desc[sdesc_key].get("HireableIconCel"):
            by_desc[sdesc_key]["HireableIconCel"] = cel_idx

    p_skills = write_excel_tsv("skills.txt", s_headers, s_rows)
    p_desc = write_excel_tsv("skilldesc.txt", d_headers, d_rows)
    return p_skills, p_desc


def build_skill_strings(cfg: dict) -> str:
    entries = read_strings_json("skills.json")
    updates = [
        (61001, "ModPassiveOpenWounds", "Passive Bonus: +%d%% Chance of Open Wounds"),
        (61002, "ModPassiveED", "Passive Bonus: +%d%% Enhanced Damage"),
        (61003, "ModPassiveFireSkillDmg", "Passive Bonus: +%d%% Fire Skill Damage (1%% per 2 Base Levels)"),
        (61004, "ModPassiveColdSkillDmg", "Passive Bonus: +%d%% Cold Skill Damage (1%% per 2 Base Levels)"),
        (61005, "ModPassiveLtngSkillDmg", "Passive Bonus: +%d%% Lightning Skill Damage (1%% per 2 Base Levels)"),
        (61006, "ModPassiveMagSkillDmg", "Passive Bonus: +%d%% Magic Skill Damage (1%% per 2 Base Levels)"),
        (61007, "ModPassiveThorns", "Passive Bonus: Attacker Takes Damage of %d"),
        (61008, "ModPassiveFHR", "Passive Bonus: +%d%% Faster Hit Recovery"),
        (61009, "ModPassiveIAS", "Passive Bonus: +%d%% Increased Attack Speed (1%% per 2 Base Levels)"),
        (61010, "ModPassiveElemPierce", "Passive Bonus: -%d%% Enemy Elemental Resist (1%% per 4 Base Levels)"),
        (61011, "ModPassiveLifeRegen", "Passive Bonus: Replenish Life +%d"),
        (61012, "ModPassiveFireRes", "Passive Bonus: Fire Resist +%d%%"),
        (61013, "ModPassiveColdRes", "Passive Bonus: Cold Resist +%d%%"),
        (61014, "ModPassiveLtngRes", "Passive Bonus: Lightning Resist +%d%%"),
        (61015, "ModPassiveAllRes", "Passive Bonus: All Resistances +%d%%"),
        (61016, "ModPassiveDefPct", "Passive Bonus: +%d%% Enhanced Defense"),
        (61017, "ModPassivePLR", "Passive Bonus: Poison Length Reduced by %d%%"),
        (61018, "ModPassiveFRW", "Passive Bonus: +%d%% Faster Run/Walk (1%% per 2 Base Levels)"),
        (61019, "ModPassiveStamRegen", "Passive Bonus: Heal Stamina Plus %d%%"),
        (61020, "ModPassiveManaRegen", "Passive Bonus: Regenerate Mana +%d%%"),
        (61021, "ModPassiveLAEK", "Passive Bonus: +%d Life After Each Kill (1 per 2 Base Levels)"),
        (61022, "ModActiveMagSkillDmg", "Magic Skill Damage: +%d%%"),
        (61023, "ModActiveFlatPDR", "Physical Damage Reduced by %d"),
        (61024, "ModActiveDmgToDemons", "Damage to Demons: +%d%%"),
    ]
    entries = upsert_string_entries(entries, updates)
    return write_strings_json("skills.json", entries)


def build_skills_all(cfg: dict) -> str:
    from mod_builder.weapons_armor import build_missiles

    p1 = build_states(cfg)
    p2, p3 = build_skills_and_desc(cfg)
    p4 = build_skill_strings(cfg)
    p5 = build_missiles(cfg)
    return f"{p1}, {p2}, {p3}, {p4}, {p5}"

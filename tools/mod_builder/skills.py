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
    "pal_dismiss_aura",
]

BARBARIAN_STATES = [
    ("bar_second_wind", {"castoverlay": "shoutstart", "overlay1": "innersight"}),
    ("bar_battle_trance", {"group": "11", "aura": "1", "overlay1": "battlecommand", "castoverlay": "battlecommandcast"}),
    ("bar_trance_pulse", {"overlay1": "innersight"}),
    ("bar_totem_debuff", {"group": "10", "aura": "1", "overlay1": "bloodlust_state", "castoverlay": "battleorderscast"}),
    ("bar_totem_stamina", {"stambarblue": "1", "overlay1": "innersight"}),
    ("bar_stamina_reflex", {"curable": "1", "curse": "1"}),
    ("bar_warcry_debuff", {"overlay1": "battlecry", "onsound": "barbarian_battlecry_state"}),
]

ASSASSIN_STATES = [
    ("ass_trap_consume", {"group": "12", "aura": "1", "active": "1", "srvactivefunc": "18", "stat": "item_kickdamage", "overlay1": "innersight"}),
    ("ass_whirl_shred", {"curable": "1"}),
    ("ass_fof_passive", {}),
    ("ass_flow_passive", {}),
    (
        "ass_shadow_bind",
        {
            "curse": "1",
            "curable": "1",
            "overlay1": "cloaked",
            "castoverlay": "psychic_hammer_hit",
            "colorpri": "85",
            "colorshift": "73",
            "light-r": "140",
            "light-g": "110",
            "light-b": "180",
        },
    ),
    ("ass_ts_passive", {}),
    ("ass_cobra_debuff", {"curable": "1", "curse": "1"}),
    ("ass_boi_passive", {}),
    ("ass_cot_passive", {}),
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
        elif st == "shout":
            # Group 11: Mutually exclusive with Enduring Cry (bar_battle_trance) so the player must choose either Bulwark Shout OR Enduring Cry!
            r["group"] = "11"
            r["armblue"] = ""
            r["stat"] = ""
        elif st == "battleorders":
            # Group 10: Mutually exclusive with Bloodlust (bar_totem_debuff) so the player must choose either Battle Orders OR Bloodlust!
            r["group"] = "10"
        elif st in (
            "progressive_damage",
            "progressive_steal",
            "progressive_other",
            "progressive_fire",
            "progressive_cold",
            "progressive_lightning",
        ):
            # Group 12: Single Active Charge-Up Rule (1 -> 2 -> 3 charges per state)
            r["group"] = "12"
        sid = parse_int(r.get("*ID", ""), -1)
        if sid > max_id:
            max_id = sid

    all_new_states = (
        [
            (
                st_name,
                {"aura": "1", "onsound": "paladin_aura_prayer"} if st_name == "pal_dismiss_aura" else {},
            )
            for st_name in PALADIN_PASSIVE_STATES
        ]
        + list(BARBARIAN_STATES)
        + list(ASSASSIN_STATES)
    )
    next_id = max_id + 1
    for st_name, extra_cols in all_new_states:
        if st_name in existing_states:
            continue
        new_row = {h: "" for h in headers}
        new_row["state"] = st_name
        new_row["*ID"] = str(next_id)
        for col_k, col_v in extra_cols.items():
            if col_k in new_row:
                new_row[col_k] = col_v
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
    # Sacrifice (Id 96): 300% + 32%/lvl (ramped) ED; self-damage 12% scaling down to 4% via blvl + Prayer/Redemption;
    # synergies: Prayer (12%), Redemption (12%), Fanaticism (10%); zero passive bonus
    sac = by_name["Sacrifice"]
    sac["passivestate"] = ""
    sac["passivestat1"] = ""
    sac["passivecalc1"] = ""
    sac["Param1"] = "300"  # Damage % baseline
    sac["Param2"] = "32"   # Damage % per level
    sac["Param3"] = "3"    # Self Damage Reduction per level (1/#)
    sac["Param5"] = "12"   # Self Damage % baseline
    sac["Param6"] = "4"    # Self Damage % min
    sac["Param7"] = "10"   # Fanaticism synergy %
    sac["Param8"] = "12"   # Prayer & Redemption synergy %
    sac["calc1"] = f"{RAMP12}+(skill('Prayer'.blvl)+skill('Redemption'.blvl))*par8+skill('Fanaticism'.blvl)*par7"
    sac["calc2"] = "max(par6, par5 - blvl/par3 - (skill('Prayer'.blvl)+skill('Redemption'.blvl))/4)"

    # Smite (Id 97): Boosted innate ED (100% + 45%/lvl ramped -> +955% ED at Lvl 20 to compensate for removing flat Smite damage from Holy Shield),
    # 1.0s + 0.24s/lvl stun, +15%/lvl ED synergy from Charge
    smite = by_name["Smite"]
    smite["Param1"] = "25"   # Stun Length baseline (1.0s)
    smite["Param2"] = "6"    # Stun Length per level (+0.24s)
    smite["Param3"] = "100"  # Damage % baseline (up from 60%)
    smite["Param4"] = "45"   # Damage % per level (ramped -> +955% ED at Lvl 20)
    smite["Param8"] = "15"   # Charge synergy % (+15%/lvl -> +300% ED at 20 Charge)
    smite["calc1"] = f"{RAMP34}+skill('Charge'.blvl)*par8"

    # Charge (Id 107): 150% + 32%/lvl (ramped) ED, 12% synergy from Vigor & Might, mana 9 -> 6,
    # AND Stuns target on impact! (EType = stun, fixed 1.4s base stun that ONLY increases via Smite at +8%/lvl)
    chg = by_name["Charge"]
    chg["mana"] = "6"
    chg["Param3"] = "150"  # Damage % baseline
    chg["Param4"] = "32"   # Damage % per level
    chg["Param6"] = "8"    # Stun duration synergy % from Smite
    chg["*Param6 Description"] = "Stun Duration synergy"
    chg["Param8"] = "12"   # Damage synergy % from Vigor & Might
    chg["calc1"] = f"{RAMP34}+(skill('Vigor'.blvl)+skill('Might'.blvl))*par8"
    chg["calc4"] = "0"     # 0% physical converted to elemental so 100% stays Physical + Stun
    chg["EType"] = "stun"
    chg["ELen"] = "35"     # 1.4s fixed base stun (only increases with points in Smite)
    chg["ELevLen1"] = "0"
    chg["ELevLen2"] = "0"
    chg["ELevLen3"] = "0"
    chg["ELenSymPerCalc"] = "skill('Smite'.blvl)*par6"

    # Zeal (Id 106): Capped at 4 hits (2 hits Lvl 1-5, 3 hits Lvl 6-11, 4 hits Lvl 12+),
    # vanilla 100% rollback (so 4-frame hits strictly require EIAS = 75), 20% + 11%/lvl (ramped -> +229% ED at Lvl 20),
    # +8% Sacrifice synergy (+160% ED at Lvl 20 -> +389% total skill ED).
    zeal = by_name["Zeal"]
    zeal["Param2"] = "100"  # % Anim frame rollback (100% = full 7 base frames per swing; 4-hit cap + melee rangeadder prevents whiffing)
    zeal["Param3"] = "20"   # Damage % baseline
    zeal["Param4"] = "11"   # Damage % per level (20 + 19*11 = 229% at Lvl 20)
    zeal["Param5"] = "2"    # # of hits Min
    zeal["Param6"] = "4"    # # of hits Max
    zeal["Param8"] = "8"    # Sacrifice synergy %
    zeal["calc1"] = "min(par5+lvl/6,par6)"
    zeal["calc2"] = f"{RAMP34}+skill('Sacrifice'.blvl)*par8"
    zeal["ToHit"] = "20"
    zeal["LevToHit"] = "12"

    # Vengeance (Id 111): Frontal Arc Cleave (srvstfunc=35 + srvdofunc=164, 156-degree arc via calc5=13, calc6=30, +0 range bonus),
    # non-linear base scaling: 90% -> 338% Fire/Cold/Ltng damage at Lvl 20 (Param1=90, Param2=16),
    # synergized ONLY by individual Resist Fire / Resist Cold / Resist Lightning auras (+14%/lvl -> +280% at 20 pts, reaching +618% in chosen elements).
    veng = by_name["Vengeance"]
    veng["srvdofunc"] = "164"
    veng["cltdofunc"] = "103"
    veng["aurafilter"] = "41347"
    veng["tgtoverlay"] = "fire_hit"
    veng["srvoverlay"] = "fire_hit"
    veng["manashift"] = "6"
    veng["mana"] = "12"
    veng["lvlmana"] = "1"
    veng["Param1"] = "90"   # Damage % baseline (90% at Lvl 1)
    veng["Param2"] = "16"   # Damage % per level (ramped -> 90 + 310*16/20 = 338% at Lvl 20)
    veng["Param7"] = ""
    veng["Param8"] = "14"   # +14%/lvl to specific element from Resist Fire / Resist Cold / Resist Lightning
    veng["calc1"] = f"{RAMP12}+skill('Resist Fire'.blvl)*par8"
    veng["calc2"] = f"{RAMP12}+skill('Resist Cold'.blvl)*par8"
    veng["calc3"] = f"{RAMP12}+skill('Resist Lightning'.blvl)*par8"
    veng["calc5"] = "13"    # 13 / 30 slices = 156-degree frontal cleave arc
    veng["calc6"] = "30"
    veng["calc7"] = "0"     # +0 sub-tiles Cleave Range Bonus (strictly weapon melee range)
    veng["ToHit"] = "40"
    veng["LevToHit"] = "15"

    # Blessed Hammer (Id 112): Reworked into a bouncing "Chain Hammer" crowd-control & Magic Damage skill!
    #   - Bounces between monsters using Chain Lightning mechanics (srvdofunc = 26, cltdofunc = 27,
    #     aurarangecalc = par1 = 16 sub-tiles / ~10.6 yards, calc1 = ln34/par5 -> 4 hits at sLvl 1, 8 hits at sLvl 20)
    #   - 1.0s casting delay (localdelay = 25) and high Mana cost (15 + 1.0/lvl -> 15 at sLvl 1, 34 at sLvl 20)
    #   - Knocks back and stuns each hit target (base 0.6s / 15 frames, synergized by Smite: +0.06s / +10% per Smite blvl -> 1.8s at 20 Smite)
    #   - Magic Damage scaled to ~25% of an average regular monster's HP across Normal/NM/Hell, synergized by Sanctuary (+12%/lvl)
    bham = by_name["Blessed Hammer"]
    bham["srvdofunc"] = "26"
    bham["srvmissilea"] = "blessedhammer"
    bham["srvmissileb"] = "blessedhammer"
    bham["srvmissilec"] = "blessedhammer"
    bham["cltdofunc"] = "27"
    bham["cltmissilea"] = "blessedhammer"
    bham["cltmissileb"] = "blessedhammer"
    bham["cltmissilec"] = "blessedhammer"
    bham["aurarangecalc"] = "par1"
    bham["localdelay"] = "25"      # 1.0s casting delay
    bham["manashift"] = "8"
    bham["mana"] = "15"            # 15 Mana at sLvl 1 -> 34 Mana at sLvl 20
    bham["lvlmana"] = "1"
    bham["Param1"] = "16"          # Bounce search radius (16 sub-tiles = ~10.6 yards)
    bham["*Param1 Description"] = "Radius of jump to next target"
    bham["Param2"] = "15"          # Base stun length in frames (15 frames = 0.6s)
    bham["*Param2 Description"] = "Stun Length baseline"
    bham["Param3"] = "16"          # # of target jump hits baseline (16/4 = 4 hits at sLvl 1)
    bham["*Param3 Description"] = "# of target jump hits baseline"
    bham["Param4"] = "1"           # # of target jump hits per level
    bham["*Param4 Description"] = "# of target jump hits per level"
    bham["Param5"] = "4"           # Every 4 levels, increase target jump (8 hits at sLvl 17+, 9 at sLvl 21+)
    bham["*Param5 Description"] = "Every # levels, increase target jump"
    bham["Param6"] = "10"          # +10% Stun Duration per Smite blvl (+1.5 frames / +0.06s per Smite level)
    bham["*Param6 Description"] = "Stun Duration synergy"
    bham["Param8"] = "12"          # +12% Magic Damage per Sanctuary blvl
    bham["*Param8 Description"] = "Damage synergy"
    bham["calc1"] = "ln34/par5"
    bham["*calc1 desc"] = "# of target jump hits"
    bham["calc4"] = "min(250,par2*(100+skill('Smite'.blvl)*par6)/100)"
    bham["*calc4 desc"] = "Stun Length"
    bham["EMin"] = "48"
    bham["EMinLev1"] = "8"
    bham["EMinLev2"] = "16"
    bham["EMinLev3"] = "40"
    bham["EMinLev4"] = "55"
    bham["EMinLev5"] = "70"
    bham["EMax"] = "64"
    bham["EMaxLev1"] = "10"
    bham["EMaxLev2"] = "18"
    bham["EMaxLev3"] = "44"
    bham["EMaxLev4"] = "60"
    bham["EMaxLev5"] = "75"
    bham["EDmgSymPerCalc"] = "skill('Sanctuary'.blvl)*par8"

    # Conversion (Id 116): 50% weapon damage (-50% penalty, SrcDam = 64), 50% + 15%/lvl AR,
    # vanilla % chance to convert (dm34: 19% -> 49%), 12s + 0.5s/lvl duration (300 + (lvl-1)*25/2 frames),
    # mana cost 4.0 + 0.25/lvl (manashift=6, mana=16, lvlmana=1 -> 4.0 at Lvl 1, 8.75 at Lvl 20).
    conv = by_name["Conversion"]
    conv["manashift"] = "6"
    conv["mana"] = "16"
    conv["lvlmana"] = "1"
    conv["Param1"] = "300"  # 12s baseline (300 frames)
    conv["Param2"] = "12"   # +0.5s per level (exact via auralencalc)
    conv["auralencalc"] = "300+(lvl-1)*25/2"
    conv["ToHit"] = "50"
    conv["LevToHit"] = "15"
    conv["SrcDam"] = "64"

    # Holy Shield (Id 117): Tactical defensive bastion cast before engaging dangerous packs/bosses:
    #   - Removed bonus Smite damage entirely (refocused as a pure defensive skill)
    #   - 0% innate Defense bonus; 100% of its Defense bonus comes from Defiance synergy (+15%/lvl -> up to +300% Defense)
    #   - Scaled back Block % chance (Param5 = 5, Param6 = 25 -> +7% at sLvl 1, +14% at sLvl 5, +18% at sLvl 10, +22% at sLvl 20)
    #   - Grants flat Physical Damage Reduced & Magic Damage Reduced (calc2 = 5 at sLvl 1 -> 22 at sLvl 10 -> 62 at sLvl 20)
    #   - Shorter tactical duration: 15s + 2s/lvl (Param1 = 375, Param2 = 50 -> 15s at sLvl 1, 34s at sLvl 10, 53s at sLvl 20)
    #   - Higher Mana cost: 40 + 2/lvl (40 Mana at sLvl 1 -> 78 Mana at sLvl 20)
    hshd = by_name["Holy Shield"]
    hshd["mana"] = "40"
    hshd["lvlmana"] = "2"
    hshd["Param1"] = "375"  # 15s baseline duration (down from 30s)
    hshd["Param2"] = "50"   # +2s per level (down from +25s/lvl -> 53s at Lvl 20 instead of 505s)
    hshd["Param3"] = "0"    # 0% base Defense
    hshd["Param4"] = "0"    # 0% Defense per level
    hshd["Param5"] = "5"    # Block % Min (down from 10)
    hshd["Param6"] = "25"   # Block % Max (down from 40 -> +7% at Lvl 1, +22% at Lvl 20)
    hshd["Param8"] = "15"   # +15% Defense per hard point in Defiance (+300% at 20 Defiance)
    hshd["calc1"] = "skill('Defiance'.blvl)*par8"
    hshd["calc2"] = "5+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*3/20"
    hshd["*calc2 desc"] = "Physical and Magic Damage Reduced"
    hshd["aurastatcalc2"] = "skill('Defiance'.blvl)*par8"
    hshd["aurastat3"] = "normal_damage_reduction"
    hshd["aurastatcalc3"] = "clc2"
    hshd["aurastat4"] = "magic_damage_reduction"
    hshd["aurastatcalc4"] = "clc2"
    for col in ("MinDam", "MinLevDam1", "MinLevDam2", "MinLevDam3", "MinLevDam4", "MinLevDam5",
                "MaxDam", "MaxLevDam1", "MaxLevDam2", "MaxLevDam3", "MaxLevDam4", "MaxLevDam5"):
        hshd[col] = ""

    # Cleric Trinity 1: Holy Bolt (Id 101) — Non-linear progression reaching ~4,000 Magic Damage late game with synergies!
    #   - Mana cost: manashift=5, mana=32, lvlmana=4 -> 4.0 Mana at sLvl 1 (+0.5/lvl -> 13.5 Mana at sLvl 20)
    #   - Base Magic Damage: 8-16 at sLvl 1 -> 395-458 at sLvl 20
    #   - Synergies: +25%/lvl from Fist of the Heavens (Param9 = 25, +500% at 20) and +15%/lvl from Sanctuary (Param8 = 15, +300% at 20)
    #     -> +800% max synergy (9x) = 3,555-4,122 Magic Damage at sLvl 20 (~3,840 avg)!
    hbolt = by_name["Holy Bolt"]
    hbolt["manashift"] = "5"
    hbolt["mana"] = "32"
    hbolt["lvlmana"] = "4"  # 4.0 Mana at Lvl 1 -> 13.5 Mana at Lvl 20 (+0.5/lvl)
    hbolt["Param7"] = "15"  # Healing synergy from Prayer (+15%/lvl)
    hbolt["Param8"] = "15"  # Damage synergy from Sanctuary (+15%/lvl)
    hbolt["Param9"] = "25"  # Damage synergy from Fist of the Heavens (+25%/lvl)
    hbolt["*Param9 Description"] = "Damage synergy from Fist of the Heavens"
    hbolt["calc1"] = f"{RAMP12} * (100 + skill('Prayer'.blvl) * par7) / 100"
    hbolt["calc2"] = f"{RAMP34} * (100 + skill('Prayer'.blvl) * par7) / 100"
    hbolt["EMin"] = "8"
    hbolt["EMinLev1"] = "5"
    hbolt["EMinLev2"] = "16"
    hbolt["EMinLev3"] = "56"
    hbolt["EMinLev4"] = "60"
    hbolt["EMinLev5"] = "68"
    hbolt["EMax"] = "16"
    hbolt["EMaxLev1"] = "6"
    hbolt["EMaxLev2"] = "18"
    hbolt["EMaxLev3"] = "64"
    hbolt["EMaxLev4"] = "68"
    hbolt["EMaxLev5"] = "76"
    hbolt["EDmgSymPerCalc"] = "skill('Sanctuary'.blvl)*par8+skill('Fist of the Heavens'.blvl)*par9"

    # Cleric Trinity 2: Fist of the Heavens (Id 121) — Heavy single-target Lightning nuke with toned-down radial Holy Bolts:
    #   - Casting delay: localdelay = 35 (1.4s cooldown, up from 1.0s)
    #   - Mana cost: mana = 40, lvlmana = 3 -> 40 Mana at sLvl 1, 97 Mana at sLvl 20 (up from 35 -> 73)
    #   - Radial Holy Bolt count & search radius: aurarangecalc = 10 (6.6 yds, down from 20 / 13.3 yds),
    #     calc4 = 3+(lvl-1)/4 (3 bolts at sLvl 1 -> 7 bolts at sLvl 17-20, down from 6 -> 25 bolts!)
    #   - Single-target Lightning Damage: 220-300 at sLvl 1 -> 2,092-2,320 at sLvl 20 base,
    #     synergized by Holy Shock at +18%/lvl (Param8 = 18, +360% max -> 9,623-10,672 Lightning Damage at sLvl 20!)
    foh = by_name["Fist of the Heavens"]
    foh["localdelay"] = "35"       # 1.4s tactical nuke cooldown
    foh["mana"] = "40"             # 40 Mana at sLvl 1 -> 97 Mana at sLvl 20
    foh["lvlmana"] = "3"
    foh["aurarangecalc"] = "10"    # 6.6-yard bolt target search radius (down from 20 = 13.3 yards)
    foh["Param1"] = "3"            # # of Holy Bolt Missiles created baseline (down from 6)
    foh["Param2"] = "1"            # +1 bolt per 4 levels via calc4
    foh["calc4"] = "par1+(lvl-1)/4"
    foh["Param8"] = "18"           # 18% Lightning synergy from Holy Shock (up from 12%)
    foh["EMin"] = "220"
    foh["EMinLev1"] = "36"
    foh["EMinLev2"] = "105"
    foh["EMinLev3"] = "195"
    foh["EMinLev4"] = "220"
    foh["EMinLev5"] = "250"
    foh["EMax"] = "300"
    foh["EMaxLev1"] = "40"
    foh["EMaxLev2"] = "115"
    foh["EMaxLev3"] = "205"
    foh["EMaxLev4"] = "230"
    foh["EMaxLev5"] = "260"
    foh["EDmgSymPerCalc"] = "skill('Holy Shock'.blvl)*par8"

    # -------------------------------------------------------------------------
    # 2. OFFENSIVE AURAS
    # -------------------------------------------------------------------------
    # Might (Id 98): Progressive 30% + 15%/lvl (ramped -> +315% ED at Lvl 20);
    # perdelay = 10 (0.4s tick) with active mana upkeep (manashift=4, mana=2, lvlmana=1 -> 0.6/sec at Lvl 1, 6.5/sec at Lvl 20);
    # passive +3% Enhanced Damage per hard point (hosted on Blessed Aim's penetrate state once Blessed Aim >= 1
    # so Might's own passivestat1 never collides with aurastat1 = damagepercent!).
    might = by_name["Might"]
    might["immediate"] = "1"
    might["perdelay"] = "10"
    might["minmana"] = "0"
    might["manashift"] = "4"
    might["mana"] = "2"
    might["lvlmana"] = "1"
    might["Param3"] = "30"
    might["Param4"] = "15"
    might["aurastatcalc1"] = RAMP34
    might["passivestate"] = "pal_might"
    might["passivestat1"] = "damagepercent"
    might["passivecalc1"] = "(skill('Blessed Aim'.blvl)<1)?(skill('Might'.blvl)*3):0"
    might["passivestat2"] = ""
    might["passivecalc2"] = ""
    might["passivestat3"] = ""
    might["passivecalc3"] = ""
    might["passivestat4"] = ""
    might["passivecalc4"] = ""
    might["passivestat5"] = ""
    might["passivecalc5"] = ""
    might["passivestat6"] = ""
    might["passivecalc6"] = ""

    # Holy Fire (Id 102, unlocks at Lvl 8):
    # Starts at 2-4 Pulse / 12-24 On-Hit (Avg 18.0) at sLvl 1 to reflect its Lvl 8 unlock,
    # smoothed across sLvl 1-20 (cLvl 8-27 in Normal: 22-32.5 Pulse / 132-195 On-Hit base at sLvl 20)
    # with steep late-game scaling in Lev4/Lev5 (sLvl 23+) and Level-40 Salvation synergy;
    # on-screen radius 4.0 yds -> 13.3 yds cap (min(20, par1 + (lvl-1)*3/4) sub-tiles);
    # active mana upkeep (manashift=7, mana=2, lvlmana=1, perdelay=50 -> 1.0/tick = 0.5/sec at Lvl 1, 10.5/tick = 5.2/sec at Lvl 20);
    # 6% Resist Fire (early) / 12% Salvation (Lvl 40) synergies (+360% max).
    elem_aura_range = "min(20,par1+(lvl-1)*3/4)"
    hfire = by_name["Holy Fire"]
    hfire["immediate"] = "1"
    hfire["minmana"] = "1"
    hfire["manashift"] = "7"
    hfire["mana"] = "2"
    hfire["lvlmana"] = "1"
    hfire["Param1"] = "6"
    hfire["aurarangecalc"] = elem_aura_range
    hfire["Param7"] = "12"
    hfire["Param8"] = "6"
    hfire["EMin"] = "4"
    hfire["EMinLev1"] = "1"
    hfire["EMinLev2"] = "3"
    hfire["EMinLev3"] = "7"
    hfire["EMinLev4"] = "14"
    hfire["EMinLev5"] = "18"
    hfire["EMax"] = "8"
    hfire["EMaxLev1"] = "2"
    hfire["EMaxLev2"] = "4"
    hfire["EMaxLev3"] = "9"
    hfire["EMaxLev4"] = "16"
    hfire["EMaxLev5"] = "20"

    # Thorns (Id 103, unlocks at Lvl 8):
    # perdelay = 10 (0.4s tick, 5x faster than 50 frames so Thorns expires in ~0.2s when Conversion ends!)
    # with active mana upkeep (manashift=4, mana=2, lvlmana=1 -> 0.6/sec at Lvl 1, 6.5/sec at Lvl 20);
    # percentage Damage Returned (thorns_percent = clc1) synergized by Sacrifice (+3%/lvl) and Redemption (+6%/lvl);
    # grants active % Physical Damage Reduction (damageresist = min(20, lvl), capped at 20% at Lvl 20+)
    # and active % Chance of Open Wounds (item_openwounds = min(75, RAMP56), 10% -> 48% at Lvl 20);
    # zero flat attacker takes damage, zero passive bonus.
    thorns = by_name["Thorns"]
    thorns["immediate"] = "1"
    thorns["perdelay"] = "10"
    thorns["minmana"] = "0"
    thorns["manashift"] = "4"
    thorns["mana"] = "2"
    thorns["lvlmana"] = "1"
    thorns["Param3"] = "250"
    thorns["Param4"] = "40"
    thorns["Param5"] = "10"
    thorns["Param6"] = "2"
    thorns["Param7"] = "6"   # Redemption synergy %
    thorns["Param8"] = "3"   # Sacrifice synergy %
    for col in ("EMin", "EMinLev1", "EMinLev2", "EMinLev3", "EMinLev4", "EMinLev5", "EDmgSymPerCalc"):
        thorns[col] = ""
    thorns["calc1"] = f"({RAMP34})*(100+skill('Sacrifice'.blvl)*par8+skill('Redemption'.blvl)*par7)/100"
    thorns["calc2"] = f"min(75,{RAMP56})"
    thorns["aurastat1"] = "thorns_percent"
    thorns["aurastatcalc1"] = "clc1"
    thorns["aurastat2"] = "damageresist"
    thorns["aurastatcalc2"] = "min(20,lvl)"
    thorns["aurastat3"] = "item_openwounds"
    thorns["aurastatcalc3"] = "clc2"
    thorns["aurastat4"] = ""
    thorns["aurastatcalc4"] = ""
    thorns["passivestate"] = ""
    thorns["passivestat1"] = ""
    thorns["passivecalc1"] = ""

    # Blessed Aim (Id 108): Ramped active Attack Rating %,
    # perdelay = 10 (0.4s tick) with active mana upkeep (manashift=4, mana=2, lvlmana=1 -> 0.6/sec at Lvl 1, 6.5/sec at Lvl 20),
    # keeps vanilla +5% passive Attack Rating per hard point, AND hosts Might + Concentration's +3%/blvl passive ED!
    baim = by_name["Blessed Aim"]
    baim["immediate"] = "1"
    baim["perdelay"] = "10"
    baim["minmana"] = "0"
    baim["manashift"] = "4"
    baim["mana"] = "2"
    baim["lvlmana"] = "1"
    baim["aurastatcalc1"] = RAMP34
    baim["passivestat2"] = "damagepercent"
    baim["passivecalc2"] = "(skill('Might'.blvl)+skill('Concentration'.blvl))*3"

    # Concentration (Id 113): Progressive 45% + 18%/lvl (ramped -> +387% ED at Lvl 20, highest among physical auras),
    # 25% uninterruptible, perdelay = 10 (0.4s tick) with active mana upkeep (manashift=4, mana=3, lvlmana=1 -> 0.9/sec at Lvl 1, 6.8/sec at Lvl 20),
    # passive +3% Enhanced Damage per hard point (hosted on Blessed Aim's penetrate state so Concentration's own passivestat1 stays empty!).
    conc = by_name["Concentration"]
    conc["immediate"] = "1"
    conc["perdelay"] = "10"
    conc["minmana"] = "0"
    conc["manashift"] = "4"
    conc["mana"] = "3"
    conc["lvlmana"] = "1"
    conc["Param3"] = "45"
    conc["Param4"] = "18"
    conc["Param5"] = "25"
    conc["aurastatcalc1"] = RAMP34
    conc["passivestate"] = ""
    conc["passivestat1"] = ""
    conc["passivecalc1"] = ""

    # Holy Freeze (Id 114, unlocks at Lvl 24):
    # Starts at 9-12 Pulse / 45-60 On-Hit (Avg 52.5) at sLvl 1 to reflect its Lvl 24 unlock,
    # scaling non-linearly to 52-55 Pulse / 260-275 On-Hit (Avg 267.5) at sLvl 20;
    # on-screen radius 4.0 yds -> 13.3 yds cap (min(20, par1 + (lvl-1)*3/4) sub-tiles);
    # active mana upkeep (manashift=7, mana=2, lvlmana=1, perdelay=50 -> 1.0/tick = 0.5/sec at Lvl 1, 10.5/tick = 5.2/sec at Lvl 20);
    # 50% max slow, 6% Resist Cold (early) / 12% Salvation (Lvl 40) synergies (+360% max).
    hfrz = by_name["Holy Freeze"]
    hfrz["immediate"] = "1"
    hfrz["minmana"] = "1"
    hfrz["manashift"] = "7"
    hfrz["mana"] = "2"
    hfrz["lvlmana"] = "1"
    hfrz["Param1"] = "6"
    hfrz["aurarangecalc"] = elem_aura_range
    hfrz["Param4"] = "50"
    hfrz["Param7"] = "12"
    hfrz["Param8"] = "6"
    hfrz["EMin"] = "9"
    hfrz["EMinLev1"] = "1"
    hfrz["EMinLev2"] = "2"
    hfrz["EMinLev3"] = "5"
    hfrz["EMinLev4"] = "6"
    hfrz["EMinLev5"] = "8"
    hfrz["EMax"] = "12"
    hfrz["EMaxLev1"] = "1"
    hfrz["EMaxLev2"] = "2"
    hfrz["EMaxLev3"] = "5"
    hfrz["EMaxLev4"] = "6"
    hfrz["EMaxLev5"] = "8"

    # Holy Shock (Id 118, unlocks at Lvl 32):
    # Starts at 1-25 Pulse / 1-150 On-Hit (Avg 75.5) at sLvl 1 to reflect its Lvl 32 unlock,
    # scaling non-linearly to 1-197 Pulse / 1-1182 On-Hit (Avg 591.5) at sLvl 20;
    # on-screen radius 4.0 yds -> 13.3 yds cap (min(20, par1 + (lvl-1)*3/4) sub-tiles);
    # active mana upkeep (manashift=7, mana=2, lvlmana=1, perdelay=50 -> 1.0/tick = 0.5/sec at Lvl 1, 10.5/tick = 5.2/sec at Lvl 20);
    # 6% Resist Lightning (early) / 12% Salvation (Lvl 40) synergies (+360% max).
    hshk = by_name["Holy Shock"]
    hshk["immediate"] = "1"
    hshk["minmana"] = "1"
    hshk["manashift"] = "7"
    hshk["mana"] = "2"
    hshk["lvlmana"] = "1"
    hshk["Param1"] = "6"
    hshk["aurarangecalc"] = elem_aura_range
    hshk["Param7"] = "12"
    hshk["Param8"] = "6"
    hshk["EMin"] = "1"
    hshk["EMax"] = "25"
    hshk["EMaxLev1"] = "4"
    hshk["EMaxLev2"] = "8"
    hshk["EMaxLev3"] = "20"
    hshk["EMaxLev4"] = "22"
    hshk["EMaxLev5"] = "24"

    # Sanctuary (Id 119, unlocks at Lvl 32):
    # Simplified into the 4th "Magic Weapon & Pulse Aura" sibling to Holy Fire / Freeze / Shock:
    # - Radial Magic Pulse + Knockback vs. Undead (11-16 at sLvl 1 -> 78-102 at sLvl 20, capped at 13.3 yds)
    # - Adds Magic Damage to Attack (passivestat1/2 = magicmindam/magicmaxdam, Param5 = 4 -> 44-64 at sLvl 1 to 312-408 at sLvl 20 base)
    # - Active mana upkeep (manashift=7, mana=2, lvlmana=1, immediate=1, perdelay=50 -> 1.0/tick = 0.5/sec at Lvl 1, 10.5/tick = 5.2/sec at Lvl 20)
    # - Synergized by Cleansing (+6%/lvl) and Blessed Hammer (+12%/lvl) (+360% max -> 1,435-1,877 On-Hit Magic Damage).
    sanc = by_name["Sanctuary"]
    sanc["immediate"] = "1"
    sanc["minmana"] = "1"
    sanc["manashift"] = "7"
    sanc["mana"] = "2"
    sanc["lvlmana"] = "1"
    sanc["Param1"] = "5"
    sanc["aurarangecalc"] = elem_aura_range
    sanc["Param5"] = "4"
    sanc["Param6"] = "100"
    sanc["Param7"] = "12"  # Blessed Hammer synergy %
    sanc["Param8"] = "6"   # Cleansing synergy %
    sanc["EMin"] = "11"
    sanc["EMinLev1"] = "1"
    sanc["EMinLev2"] = "3"
    sanc["EMinLev3"] = "9"
    sanc["EMinLev4"] = "11"
    sanc["EMinLev5"] = "13"
    sanc["EMax"] = "16"
    sanc["EMaxLev1"] = "2"
    sanc["EMaxLev2"] = "4"
    sanc["EMaxLev3"] = "10"
    sanc["EMaxLev4"] = "12"
    sanc["EMaxLev5"] = "14"
    sanc["EDmgSymPerCalc"] = "skill('Cleansing'.blvl)*par8+skill('Blessed Hammer'.blvl)*par7"
    sanc["passivestat1"] = "magicmindam"
    sanc["passivecalc1"] = "enms*par5/256"
    sanc["passivestat2"] = "magicmaxdam"
    sanc["passivecalc2"] = "exms*par5/256"
    sanc["passivestat3"] = "skill_bypass_undead"
    sanc["passivecalc3"] = "1"
    sanc["passivestat4"] = ""
    sanc["passivecalc4"] = ""
    sanc["passivestat5"] = ""
    sanc["passivecalc5"] = ""
    sanc["passivestat6"] = ""
    sanc["passivecalc6"] = ""

    # Fanaticism (Id 122): Linear Self ED (65% + 10%/lvl -> +255% at Lvl 20) & Party ED share (2/3 -> +43% to +170%),
    # Attack Speed % Max (Param4 = 30 -> +14% to +27% IAS), toned-down Attack Rating (+25% + 3%/lvl -> +82% at Lvl 20),
    # perdelay = 10 (0.4s tick) with active mana upkeep (manashift=4, mana=4, lvlmana=1 -> 1.2/sec at Lvl 1, 7.1/sec at Lvl 20), zero passive bonus.
    fana = by_name["Fanaticism"]
    fana["immediate"] = "1"
    fana["perdelay"] = "10"
    fana["minmana"] = "0"
    fana["manashift"] = "4"
    fana["mana"] = "4"
    fana["lvlmana"] = "1"
    fana["Param3"] = "10"
    fana["Param4"] = "30"
    fana["Param5"] = "65"
    fana["Param6"] = "10"
    fana["ToHit"] = "25"
    fana["LevToHit"] = "3"
    fana["passivecalc1"] = "ln56"
    fana["aurastatcalc3"] = "ln56*2/3"

    # Conviction (Id 123, "Aura of Guilt"): Ramped -Enemy Res (cap -100%),
    # adds Enemy Physical Damage Reduction (-10 - lvl) & Enemy Slow (-10 - lvl/2);
    # perdelay = 10 (0.4s tick) with active mana upkeep (manashift=4, mana=4, lvlmana=1 -> 1.2/sec at Lvl 1, 7.1/sec at Lvl 20);
    # zero passive bonus.
    convic = by_name["Conviction"]
    convic["immediate"] = "1"
    convic["perdelay"] = "10"
    convic["minmana"] = "0"
    convic["manashift"] = "4"
    convic["mana"] = "4"
    convic["lvlmana"] = "1"
    convic["Param3"] = "20"
    convic["Param4"] = "4"
    convic["aurastatcalc2"] = f"-min({RAMP34},100)"
    convic["aurastatcalc3"] = f"-min({RAMP34},100)"
    convic["aurastatcalc4"] = f"-min({RAMP34},100)"
    convic["aurastat5"] = "damagepercent"
    convic["aurastatcalc5"] = "-10-lvl"
    convic["aurastat6"] = "velocitypercent"
    convic["aurastatcalc6"] = "-10-lvl/2"
    convic["passivestate"] = ""
    convic["passivestat1"] = ""
    convic["passivecalc1"] = ""
    convic["passivestat2"] = ""
    convic["passivecalc2"] = ""
    convic["passivestat3"] = ""
    convic["passivecalc3"] = ""

    # -------------------------------------------------------------------------
    # 3. DEFENSIVE AURAS
    # -------------------------------------------------------------------------
    # Prayer (Id 99): Active healing stance with immediate=1 (fires tick #1 on switch),
    # reduced mana tick cost (manashift=7, mana=2 [1.0 at Lvl 1], lvlmana=1 [+0.5/lvl -> 10.5/tick = 5.2/sec at Lvl 20]),
    # healing curve (3 Life at Lvl 1 -> 30 Life at Lvl 20 base, up to 84 Life/tick with 20 Cleansing),
    # +9% healing synergy per hard point in Cleansing ONLY, and zero passive bonus.
    pray = by_name["Prayer"]
    pray["InTown"] = "1"
    pray["aurafilter"] = "73731"
    pray["aurastate"] = "prayer"
    pray["auratargetstate"] = "prayer"
    pray["immediate"] = "1"
    pray["minmana"] = "1"
    pray["manashift"] = "7"
    pray["mana"] = "2"
    pray["lvlmana"] = "1"
    pray["EMin"] = "3"
    pray["EMinLev1"] = "1"
    pray["EMinLev2"] = "1"
    pray["EMinLev3"] = "3"
    pray["EMinLev4"] = "3"
    pray["EMinLev5"] = "4"
    pray["Param8"] = "9"
    pray["*Param8 Description"] = "Healing synergy % from Cleansing"
    pray["aurastat1"] = "hitpoints"
    pray["aurastatcalc1"] = "edns"
    pray["aurastat2"] = ""
    pray["aurastatcalc2"] = ""
    pray["EDmgSymPerCalc"] = "skill('Cleansing'.blvl)*par8"
    pray["passivestate"] = ""
    pray["passivestat1"] = ""
    pray["passivecalc1"] = ""

    # Resist Fire / Cold / Lightning (Id 100, 105, 110):
    # Replace front-loaded dm34 (52% at Lvl 1!) with RAMP34 starting at 33% (Param3=33, Param4=5 -> 33% at Lvl 1, 128% at Lvl 20,
    # or exact 33% -> 120% via calc1="par3+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*87/310"),
    # perdelay = 10 (0.4s tick) with active mana upkeep (manashift=4, mana=2, lvlmana=1 -> 0.6/sec at Lvl 1, 6.5/sec at Lvl 20),
    # keep vanilla +0.5% Max Res per blvl and remove custom passive base resist.
    res_single_curve = "par3+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*87/310"
    for res_name in ("Resist Fire", "Resist Cold", "Resist Lightning"):
        raura = by_name[res_name]
        raura["immediate"] = "1"
        raura["perdelay"] = "10"
        raura["minmana"] = "0"
        raura["manashift"] = "4"
        raura["mana"] = "2"
        raura["lvlmana"] = "1"
        raura["Param3"] = "33"
        raura["Param4"] = "5"
        raura["calc1"] = res_single_curve
        raura["aurastatcalc1"] = "clc1"
        raura["passivestat2"] = ""
        raura["passivecalc2"] = ""

    # Defiance (Id 104): 80% + 12%/lvl (ramped) active Defense,
    # non-linear active Physical Damage Reduced (normal_damage_reduction = clc1: 2 at Lvl 1 -> 5 at Lvl 5 -> 12 at Lvl 10 -> 21 at Lvl 15 -> 35 at Lvl 20, ~56% of Holy Shield's 62),
    # perdelay = 10 (0.4s tick) with active mana upkeep (manashift=4, mana=2, lvlmana=1 -> 0.6/sec at Lvl 1, 6.5/sec at Lvl 20), zero passive bonus.
    defi = by_name["Defiance"]
    defi["immediate"] = "1"
    defi["perdelay"] = "10"
    defi["minmana"] = "0"
    defi["manashift"] = "4"
    defi["mana"] = "2"
    defi["lvlmana"] = "1"
    defi["Param3"] = "80"
    defi["Param4"] = "12"
    defi["calc1"] = "2+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*33/310"
    defi["aurastatcalc1"] = RAMP34
    defi["aurastat2"] = "normal_damage_reduction"
    defi["aurastatcalc2"] = "clc1"
    defi["passivestate"] = ""
    defi["passivestat1"] = ""
    defi["passivecalc1"] = ""

    # Cleansing (Id 109): Active curse/poison-purging stance with immediate=1,
    # reduced mana consumption curve matching Prayer (manashift=7, mana=2 [1.0 at Lvl 1], lvlmana=1 [+0.5/lvl -> 10.5/tick = 5.2/sec at Lvl 20]),
    # ramped per-tick Poison & Curse Duration reduction (Param3=25, Param4=2 -> 25% at Lvl 1, 31% at Lvl 5, 63% at Lvl 20,
    # compounding every 2s tick to clear a 56s Hell Cursed Unique Amplify Damage in ~5 seconds!),
    # zero redundant curse_resistance, zero Prayer heal inheritance & zero passive bonus.
    clns = by_name["Cleansing"]
    clns["immediate"] = "1"
    clns["minmana"] = "1"
    clns["manashift"] = "7"
    clns["mana"] = "2"
    clns["lvlmana"] = "1"
    clns["Param3"] = "25"
    clns["Param4"] = "2"
    clns["aurastat1"] = "item_poisonlengthresist"
    clns["aurastatcalc1"] = f"100-min(90,{RAMP34})"
    clns["aurastat2"] = ""
    clns["aurastatcalc2"] = ""
    clns["aurastat3"] = ""
    clns["aurastatcalc3"] = ""
    clns["passivestate"] = ""
    clns["passivestat1"] = ""
    clns["passivecalc1"] = ""

    # Vigor (Id 115): Focused movement & hit-recovery aura (removed stamina recovery & max stamina buffs),
    # grants Run/Walk Speed (dm56: +13% at Lvl 1 -> +43% at Lvl 20) and Faster Hit Recovery (clc1: +10% at Lvl 1 -> +56% at Lvl 20),
    # perdelay = 10 (0.4s tick) with active mana upkeep (manashift=4, mana=2, lvlmana=1 -> 0.6/sec at Lvl 1, 6.5/sec at Lvl 20), zero passive bonus.
    vig = by_name["Vigor"]
    vig["immediate"] = "1"
    vig["perdelay"] = "10"
    vig["minmana"] = "0"
    vig["manashift"] = "4"
    vig["mana"] = "2"
    vig["lvlmana"] = "1"
    vig["Param3"] = "10"
    vig["Param4"] = "3"
    vig["calc1"] = RAMP34
    vig["aurastat1"] = "velocitypercent"
    vig["aurastatcalc1"] = "dm56"
    vig["aurastat2"] = "item_fastergethitrate"
    vig["aurastatcalc2"] = "clc1"
    vig["aurastat3"] = ""
    vig["aurastatcalc3"] = ""
    vig["passivestate"] = ""
    vig["passivestat1"] = ""
    vig["passivecalc1"] = ""
    vig["passivestat2"] = ""
    vig["passivecalc2"] = ""

    # Meditation (Id 120): perdelay = 10 (0.4s tick), ramped active Mana Recovery %, zero Prayer heal inheritance,
    # active self-only -50% Base Weapon Damage (item_slash_damage_percent & item_crush_damage_percent = -50 via op=11 on min/maxdamage),
    # and zero passive Mana Recovery (Mana Recovery is purely an active property of Meditation!).
    medi = by_name["Meditation"]
    medi["immediate"] = "1"
    medi["perdelay"] = "10"
    medi["aurastatcalc1"] = RAMP34
    medi["aurastat2"] = ""
    medi["aurastatcalc2"] = ""
    medi["passivestate"] = ""
    medi["passivestat1"] = "item_slash_damage_percent"
    medi["passivecalc1"] = "-50"
    medi["passivestat2"] = "item_crush_damage_percent"
    medi["passivecalc2"] = "-50"

    # Redemption (Id 124): Native corpse-clearing aura (srvdofunc=82, aurafilter=4354, 0 Mana cost, immediate=1)
    # that consumes nearby monster corpses (calc1 = dm34 chance, calc2=0, calc3=0) so they cannot be resurrected,
    # while granting active self Life After Each Kill (passivestat1 = item_healafterkill: +21 at Lvl 1 -> +96 at Lvl 20)
    # and active self Mana After Each Kill (passivestat2 = item_manaafterkill: +14 at Lvl 1 -> +64 at Lvl 20, exact 2/3 of Life)!
    redm_lak_curve = "21+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*75/310"
    redm_mak_curve = f"({redm_lak_curve})*2/3"
    redm = by_name["Redemption"]
    redm["immediate"] = "1"
    redm["Param2"] = "1"
    redm["Param3"] = "25"
    redm["Param4"] = "100"
    redm["calc1"] = "dm34"
    redm["calc2"] = "0"
    redm["calc3"] = "0"
    redm["auraevent1"] = ""
    redm["auraeventfunc1"] = ""
    redm["auraevent2"] = "kill"
    redm["auraeventfunc2"] = "28"
    redm["passivestate"] = ""
    redm["passivestat1"] = "item_healafterkill"
    redm["passivecalc1"] = redm_lak_curve
    redm["passivestat2"] = "item_manaafterkill"
    redm["passivecalc2"] = redm_mak_curve

    # Salvation (Id 125): Ramped 25% -> 100% All-Res at Lvl 20 (instead of 71% at Lvl 1),
    # perdelay = 10 (0.4s tick) with active mana upkeep (manashift=4, mana=2, lvlmana=1 -> 0.6/sec at Lvl 1, 6.5/sec at Lvl 20), zero passive bonus.
    salv = by_name["Salvation"]
    salv["immediate"] = "1"
    salv["perdelay"] = "10"
    salv["minmana"] = "0"
    salv["manashift"] = "4"
    salv["mana"] = "2"
    salv["lvlmana"] = "1"
    salv["Param3"] = "25"
    salv["Param4"] = "4"
    salv["calc1"] = "par3+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*15/62"
    salv["aurastatcalc1"] = "clc1"
    salv["aurastatcalc2"] = "clc1"
    salv["aurastatcalc3"] = "clc1"
    salv["passivestate"] = ""
    salv["passivestat1"] = ""
    salv["passivecalc1"] = ""
    salv["passivestat2"] = ""
    salv["passivecalc2"] = ""
    salv["passivestat3"] = ""
    salv["passivecalc3"] = ""
    salv["passivestat4"] = ""
    salv["passivecalc4"] = ""


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
    _set_dsc_line(sac, "dsc2", 1, "74", "StrSkill47", "", "clc2", "")
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

    # 4b. Holy Shield (Display Duration, Block %, Damage Reduced, Magic Damage Reduced, and Defiance Defense % synergy)
    hshd = by_desc["holy shield"]
    _set_dsc_line(hshd, "desc", 1, "36", "StrSkillDurationSingular", "StrSkill20", "ln12", "25")
    _set_dsc_line(hshd, "desc", 2, "74", "StrSkill110", "", "dm56", "")
    _set_dsc_line(hshd, "desc", 3, "74", "ModActiveFlatPDR", "", "clc2", "")
    _set_dsc_line(hshd, "desc", 4, "74", "ModActiveFlatMDR", "", "clc2", "")
    _set_dsc_line(hshd, "desc", 5, "74", "StrSkill21", "", "clc1", "")

    # 5. Vengeance (Display Fire/Cold/Ltng %, Attack Rating %, Cold Length, and 156-degree Cleave Arc!)
    veng = by_desc["vengeance"]
    veng["desccalca2"] = "clc3"
    veng["desccalca4"] = "clc2"
    veng["desccalca5"] = "clc1"
    _set_dsc_line(veng, "dsc2", 1, "74", "StrSkillCleaveArcRadius", "", "clc5*12", "")
    _clear_dsc3_synergies(veng, "skillname111")
    _set_dsc_line(veng, "dsc3", 2, "76", "Firedplev", "skillname100", "par8", "")
    _set_dsc_line(veng, "dsc3", 3, "76", "Colddplev", "skillname105", "par8", "")
    _set_dsc_line(veng, "dsc3", 4, "76", "Ltngdplev", "skillname110", "par8", "")

    # 5b. Blessed Hammer (Bouncing Chain Hammer: Magic Damage, Hits, Stun Length, Casting Delay, Smite & Sanctuary synergies)
    bham_d = by_desc["blessed hammer"]
    bham_d["descdam"] = "5"
    _set_dsc_line(bham_d, "desc", 1, "36", "StrSkill3", "", "usmc", "256")
    _set_dsc_line(bham_d, "desc", 2, "75", "StrSkill39", "", "enma", "exma")
    _set_dsc_line(bham_d, "desc", 3, "74", "StrSkill11", "", "ln34/par5", "")
    _set_dsc_line(bham_d, "desc", 4, "36", "StrSkillStunLengthSingular", "StrSkill48", "min(250,par2*(100+skill('Smite'.blvl)*par6)/100)", "25")
    _set_dsc_line(bham_d, "dsc2", 1, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "25", "25")
    _clear_dsc3_synergies(bham_d, "skillname112")
    _set_dsc_line(bham_d, "dsc3", 2, "76", "Magdplev", "skillname119", "par8", "")
    _set_dsc_line(bham_d, "dsc3", 3, "76", "Durateplev", "skillname97", "par6", "")

    # 5c. Conversion (Display Attack Rating +X%, 1/2 Weapon Damage, and 12s + 0.5s/lvl Duration!)
    conv = by_desc["conversion"]
    _set_dsc_line(conv, "desc", 2, "74", "StrSkill22", "", "toht", "")
    _set_dsc_line(conv, "dsc2", 1, "74", "WeapDamsk", "", "64*100/128", "")
    _set_dsc_line(conv, "dsc2", 2, "36", "StrSkill3", "", "usmc", "256")
    _set_dsc_line(conv, "dsc2", 3, "36", "StrSkillDurationSingular", "StrSkill20", "300+(lvl-1)*25/2", "25")

    # 6. Cleric Trinity: Holy Bolt, Sanctuary, Fist of the Heavens
    hb = by_desc["holy bolt"]
    hb["desccalca2"] = "clc1"
    hb["desccalcb2"] = "clc2"
    _clear_dsc3_synergies(hb, "skillname101")
    _set_dsc_line(hb, "dsc3", 2, "76", "Magdplev", "skillname119", "par8", "")
    _set_dsc_line(hb, "dsc3", 3, "76", "Magdplev", "skillname121", "par9", "")
    _set_dsc_line(hb, "dsc3", 4, "76", "Healplev", "skillname99", "par7", "")

    sanc = by_desc["sanctuary"]
    elem_aura_range_yds = "min(20,par1+(lvl-1)*3/4)*2"
    _set_dsc_line(sanc, "desc", 1, "36", "StrSkill34", "", "usmc", "512")
    _set_dsc_line(sanc, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", elem_aura_range_yds, "3")
    _set_dsc_line(sanc, "desc", 3, "75", "StrSkill39", "", "enma", "exma*((100+par6)/100)")
    _set_dsc_line(sanc, "desc", 4, "75", "StrSkillMagicDamageToYourAttack", "", "edns*par5/256", "edxs*par5/256")
    _set_dsc_line(sanc, "desc", 5, "", "", "", "", "")
    _set_dsc_line(sanc, "dsc2", 2, "", "", "", "", "")
    _clear_dsc3_synergies(sanc, "skillname119")
    _set_dsc_line(sanc, "dsc3", 2, "76", "Magdplev", "skillname109", "par8", "")
    _set_dsc_line(sanc, "dsc3", 3, "76", "Magdplev", "skillname112", "par7", "")

    foh = by_desc["fist of the heavens"]
    foh["desccalca5"] = ""
    _set_dsc_line(foh, "desc", 3, "74", "StrSkill27", "", "clc4", "")
    _set_dsc_line(foh, "dsc2", 2, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "35", "25")
    _clear_dsc3_synergies(foh, "skillname121")
    _set_dsc_line(foh, "dsc3", 2, "76", "Hbdplev", "skillname101", "12", "")
    _set_dsc_line(foh, "dsc3", 3, "76", "Hbdplev", "skillname119", "12", "")
    _set_dsc_line(foh, "dsc3", 4, "76", "Ltngdplev", "skillname118", "par8", "")

    # 7. Offensive & Defensive Aura Tooltips
    might = by_desc["might"]
    _set_dsc_line(might, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(might, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(might, "desc", 3, "74", "StrSkillDamagePercent", "", RAMP34, "")
    _set_dsc_line(might, "dsc2", 1, "74", "ModPassiveED", "", "(skill('Might'.blvl)<1)?3:(skill('Might'.blvl)*3)", "")

    baim = by_desc["blessed aim"]
    _set_dsc_line(baim, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(baim, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(baim, "desc", 3, "74", "StrSkillAttackRatingPassive", "", "(skill('Blessed Aim'.blvl) < 1) ? par8 : skill('Blessed Aim'.blvl) * par8", "")
    _set_dsc_line(baim, "desc", 4, "74", "StrSkillAttackRatingActive", "", RAMP34, "")

    elem_aura_range_yds = "min(20,par1+(lvl-1)*3/4)*2"
    hfire = by_desc["holy fire"]
    _set_dsc_line(hfire, "desc", 1, "36", "StrSkill34", "", "usmc", "512")
    _set_dsc_line(hfire, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", elem_aura_range_yds, "3")
    _set_dsc_line(hfire, "desc", 3, "75", "StrSkill5", "", "enma", "exma*((100+par6)/100)")
    _set_dsc_line(hfire, "desc", 4, "75", "StrSkillFireDamageToYourAttack", "", "edns*par5/256", "edxs*par5/256")
    _set_dsc_line(hfire, "dsc2", 2, "", "", "", "", "")

    thorns = by_desc["thorns"]
    _set_dsc_line(thorns, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(thorns, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(thorns, "desc", 3, "74", "StrSkill55", "", "clc1", "")
    _set_dsc_line(thorns, "desc", 4, "74", "ModActivePctPDR", "", "min(20,lvl)", "")
    _set_dsc_line(thorns, "desc", 5, "74", "ModStr3m", "", "clc2", "")
    _set_dsc_line(thorns, "desc", 6, "", "", "", "", "")
    _set_dsc_line(thorns, "dsc2", 1, "", "", "", "", "")
    _clear_dsc3_synergies(thorns, "skillname103")
    _set_dsc_line(thorns, "dsc3", 2, "76", "Damplev", "skillname96", "par8", "")
    _set_dsc_line(thorns, "dsc3", 3, "76", "Damplev", "skillname124", "par7", "")

    conc = by_desc["concentration"]
    _set_dsc_line(conc, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(conc, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(conc, "desc", 3, "74", "StrSkillDamagePercent", "", RAMP34, "")
    _set_dsc_line(conc, "dsc2", 1, "74", "StrSkill76", "", "par5", "")
    _set_dsc_line(conc, "dsc2", 2, "74", "ModPassiveED", "", "(skill('Concentration'.blvl)<1)?3:(skill('Concentration'.blvl)*3)", "")

    hfrz = by_desc["holy freeze"]
    _set_dsc_line(hfrz, "desc", 1, "36", "StrSkill34", "", "usmc", "512")
    _set_dsc_line(hfrz, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", elem_aura_range_yds, "3")
    _set_dsc_line(hfrz, "desc", 3, "74", "StrSkill77", "", "dm34", "")
    _set_dsc_line(hfrz, "desc", 4, "75", "StrSkill6", "", "enma", "exma*((100+par6)/100)")
    _set_dsc_line(hfrz, "desc", 5, "75", "StrSkillColdDamageToYourAttack", "", "edns*par5/256", "edxs*par5/256")
    _set_dsc_line(hfrz, "dsc2", 2, "", "", "", "", "")

    hshk = by_desc["holy shock"]
    _set_dsc_line(hshk, "desc", 1, "36", "StrSkill34", "", "usmc", "512")
    _set_dsc_line(hshk, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", elem_aura_range_yds, "3")
    _set_dsc_line(hshk, "desc", 3, "75", "StrSkill7", "", "enma", "exma*((100+par6)/100)")
    _set_dsc_line(hshk, "desc", 4, "75", "strEskilllighttoattack", "", "edns/256", "edxs*par5/256")
    _set_dsc_line(hshk, "dsc2", 2, "", "", "", "", "")

    fana = by_desc["fanaticism"]
    _set_dsc_line(fana, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(fana, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(fana, "desc", 3, "74", "StrSkill106", "", "dm34", "")
    _set_dsc_line(fana, "desc", 4, "74", "PartDam", "", "ln56*2/3", "")
    _set_dsc_line(fana, "desc", 5, "74", "FanYDam", "", "ln56", "")
    _set_dsc_line(fana, "desc", 6, "74", "StrSkill22", "", "toht", "")
    _set_dsc_line(fana, "dsc2", 1, "", "", "", "", "")

    convic = by_desc["conviction"]
    _set_dsc_line(convic, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(convic, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(convic, "desc", 3, "74", "StrSkill54", "", f"-min({RAMP34},100)", "")
    _set_dsc_line(convic, "desc", 4, "74", "StrSkill21", "", "-dm56", "")
    _set_dsc_line(convic, "desc", 5, "74", "StrSkill38", "", "-10-lvl", "")
    _set_dsc_line(convic, "desc", 6, "74", "Cgslow", "", "10+lvl/2", "")
    _set_dsc_line(convic, "dsc2", 1, "", "", "", "", "")

    pray = by_desc["prayer"]
    _set_dsc_line(pray, "desc", 1, "36", "StrSkill34", "", "usmc", "512")
    _set_dsc_line(pray, "desc", 3, "74", "StrSkillHealFlat", "", "enma", "")
    _set_dsc_line(pray, "desc", 4, "", "", "", "", "")
    _set_dsc_line(pray, "dsc2", 1, "", "", "", "", "")
    _clear_dsc3_synergies(pray, "skillname99")
    _set_dsc_line(pray, "dsc3", 2, "76", "Healplev", "skillname109", "par8", "")

    rfire = by_desc["resist fire"]
    _set_dsc_line(rfire, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(rfire, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(rfire, "desc", 3, "36", "StrSkillMaxResistFirePassive", "StrSkillMaxResistFirePassive", "(skill('Resist Fire'.blvl) < 1) ? 1 : skill('Resist Fire'.blvl)", "2")
    _set_dsc_line(rfire, "desc", 4, "74", "StrSkillMaxResistFireActive", "", "(skill('Resist Fire'.blvl) < 1) ? 1 : skill('Resist Fire'.blvl)", "")
    _set_dsc_line(rfire, "desc", 5, "74", "StrSkill51", "", "clc1", "")
    _set_dsc_line(rfire, "dsc2", 1, "", "", "", "", "")

    rcold = by_desc["resist cold"]
    _set_dsc_line(rcold, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(rcold, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(rcold, "desc", 3, "36", "StrSkillMaxResistColdPassive", "StrSkillMaxResistColdPassive", "(skill('Resist Cold'.blvl) < 1) ? 1 : skill('Resist Cold'.blvl)", "2")
    _set_dsc_line(rcold, "desc", 4, "74", "StrSkillMaxResistColdActive", "", "(skill('Resist Cold'.blvl) < 1) ? 1 : skill('Resist Cold'.blvl)", "")
    _set_dsc_line(rcold, "desc", 5, "74", "StrSkill52", "", "clc1", "")
    _set_dsc_line(rcold, "dsc2", 1, "", "", "", "", "")

    rltng = by_desc["resist lightning"]
    _set_dsc_line(rltng, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(rltng, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(rltng, "desc", 3, "36", "StrSkillMaxResistLightningPassive", "StrSkillMaxResistLightningPassive", "(skill('Resist Lightning'.blvl) < 1) ? 1 : skill('Resist Lightning'.blvl)", "2")
    _set_dsc_line(rltng, "desc", 4, "74", "StrSkillMaxResistLightningActive", "", "(skill('Resist Lightning'.blvl) < 1) ? 1 : skill('Resist Lightning'.blvl)", "")
    _set_dsc_line(rltng, "desc", 5, "74", "StrSkill53", "", "clc1", "")
    _set_dsc_line(rltng, "dsc2", 1, "", "", "", "", "")

    defi = by_desc["defiance"]
    _set_dsc_line(defi, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(defi, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(defi, "desc", 3, "74", "StrSkill21", "", RAMP34, "")
    _set_dsc_line(defi, "desc", 4, "74", "ModActiveFlatPDR", "", "clc1", "")
    _set_dsc_line(defi, "dsc2", 1, "", "", "", "", "")

    clns = by_desc["cleansing"]
    _set_dsc_line(clns, "desc", 1, "36", "StrSkill34", "", "usmc", "512")
    _set_dsc_line(clns, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(clns, "desc", 3, "74", "StrSkill74", "", f"min(90,{RAMP34})", "")
    _set_dsc_line(clns, "desc", 4, "", "", "", "", "")
    _set_dsc_line(clns, "dsc2", 1, "", "", "", "", "")
    _set_dsc_line(clns, "dsc2", 2, "", "", "", "", "")
    for i in range(1, 8):
        _set_dsc_line(clns, "dsc3", i, "", "", "", "", "")

    vig = by_desc["vigor"]
    _set_dsc_line(vig, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(vig, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(vig, "desc", 3, "74", "StrSkill89", "", "dm56", "")
    _set_dsc_line(vig, "desc", 4, "74", "ModStr4p", "", "clc1", "")
    _set_dsc_line(vig, "desc", 5, "", "", "", "", "")
    _set_dsc_line(vig, "dsc2", 1, "", "", "", "", "")
    _set_dsc_line(vig, "dsc2", 2, "", "", "", "", "")

    medi = by_desc["meditation"]
    medi["desccalca2"] = RAMP34
    _set_dsc_line(medi, "desc", 3, "74", "FanYDam", "", "-50", "")
    _set_dsc_line(medi, "dsc2", 1, "", "", "", "", "")
    _set_dsc_line(medi, "dsc2", 2, "", "", "", "", "")
    for i in range(1, 8):
        _set_dsc_line(medi, "dsc3", i, "", "", "", "", "")

    redm = by_desc["redemption"]
    redm_lak_curve = "21+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*75/310"
    redm_mak_curve = f"({redm_lak_curve})*2/3"
    _set_dsc_line(redm, "desc", 1, "74", "StrSkill109", "", "dm34", "")
    _set_dsc_line(redm, "desc", 2, "74", "ModitemHPaK", "", redm_lak_curve, "")
    _set_dsc_line(redm, "desc", 3, "74", "ModStr5f", "", redm_mak_curve, "")
    _set_dsc_line(redm, "dsc2", 1, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")

    salv = by_desc["salvation"]
    _set_dsc_line(salv, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(salv, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(salv, "desc", 3, "74", "StrSkill54", "", "clc1", "")
    _set_dsc_line(salv, "dsc2", 1, "", "", "", "", "")


def _apply_barbarian_skills(by_name: Dict[str, Dict[str, str]]) -> None:
    """
    Apply Barbarian Stamina Pendulum Overhaul ("Well-Rested vs. Exhaustion / Last Stand"):
      1. Stamina Spenders (0 Mana, drain Stamina in melee contact, penalized when Exhausted <= 10 Stamina):
         - Leap (Id 132), Leap Attack (Id 143), Whirlwind (Id 151)
      2. "Well-Rested" Skills (Scale UP continuously with current Stamina % from 0% to 100%):
         - Rested Bash (Id 126), Rested Stun (Id 139), Rested Concentrate (Id 144)
      3. "Exhaustion / Last Stand" Skills (Scale UP continuously with missing Stamina % from 0% to 100%):
         - Desperate Swing (Id 133), Desperate Throw (Id 140), Desperate Frenzy (Id 147)
      4. Stamina Control Warcries & Passives:
         - Second Wind (Id 131, replaces Find Potion): Instant Stamina Restoration Warcry
         - Enduring Cry (Id 142, replaces Find Item): Warcry that temporarily boosts Maximum Stamina
         - Bloodlust (Id 150, replaces Grim Ward): Passive that amplifies damage & AR of all skills as Stamina drops
         - Unflinching (Id 141, replaces Increased Stamina): Passive Faster Hit Recovery %
    """
    RESTED_PCT = "((stat('stamina'.accr)*100)/max(256,stat('maxstamina'.accr)))"
    EXHAUST_PCT = "(100-(stat('stamina'.accr)*100)/max(256,stat('maxstamina'.accr)))"
    BLOODLUST_MAX_DMG = "((stat('skill_chillingarmor'.accr)>0)?skill('Grim Ward'.clc1):0)"
    BLOODLUST_CUR_AR = "((stat('skill_chillingarmor'.accr)>0)?skill('Grim Ward'.clc4):0)"

    # -------------------------------------------------------------------------
    # 1. STAMINA SPENDERS (Leap 132, Leap Attack 143, Whirlwind 151)
    #    0 Mana, drain Stamina in melee contact, and degrade smoothly via gradient as Stamina drops!
    # -------------------------------------------------------------------------
    # Leap (Id 132, Col 2 Row 2, Req Lvl 8, no prerequisites):
    # 0 Mana, uses srvdofunc=170 + calc5=433 (Bar Stamina Reflex at sLvl 3, 6-subtile drain radius)
    # Jump Range (aurarangecalc = clc3), Leap Speed (calc2), and Knockback Radius (calc1) all degrade smoothly with Stamina %!
    leap = by_name["Leap"]
    leap["reqlevel"] = "8"
    leap["reqskill1"] = ""
    leap["reqskill2"] = ""
    leap["reqskill3"] = ""
    leap["srvdofunc"] = "170"
    leap["srvmissilea"] = "leapknockback"
    leap["minmana"] = "0"
    leap["mana"] = "0"
    leap["lvlmana"] = "0"
    leap["calc1"] = f"2+((ln34-2)*({RESTED_PCT}))/100"
    leap["calc2"] = f"90+((par7-90)*({RESTED_PCT}))/100"
    leap["calc3"] = f"6+((dm12-6)*({RESTED_PCT}))/100"
    leap["*calc3 desc"] = "Stamina-scaled Leap Range"
    leap["aurarangecalc"] = "clc3"
    leap["calc4"] = ""
    leap["calc5"] = "433"   # Cast Bar Stamina Reflex (Id 433) during leap
    leap["*calc5 desc"] = "Skill ID to cast when leap ends"
    leap["calc6"] = "1"     # sLvl 1 Bar Stamina Reflex (6-subtile drain radius, gentle per-monster drain)
    leap["*calc6 desc"] = "Level of cast skill ID"

    # Leap Attack (Id 143, Col 2 Row 4, Req Lvl 24, requires Leap):
    # 0 Mana, uses srvdofunc=170 + calc5=433 (Bar Stamina Reflex at sLvl 10)
    # Both Weapon Damage % (calc1) and AoE Shockwave Damage (DmgSymPerCalc) degrade smoothly via gradient with Stamina %.
    # AoE Landing Stun (calc4) is enabled ONLY when Stamina is >= 50% full (RESTED_PCT >= 50).
    lpat = by_name["Leap Attack"]
    lpat["reqlevel"] = "24"
    lpat["reqskill1"] = "Leap"
    lpat["reqskill2"] = ""
    lpat["reqskill3"] = ""
    lpat["srvdofunc"] = "170"
    lpat["srvoverlay"] = ""
    lpat["minmana"] = "0"
    lpat["mana"] = "0"
    lpat["lvlmana"] = "0"
    lpat["Param3"] = "150"  # Damage % baseline (+150% at Lvl 1)
    lpat["Param4"] = "20"   # Damage % per level (ramped -> +530% at Lvl 20)
    lpat["Param6"] = "35"   # AoE landing Stun length (35 frames = 1.4s when Stamina >= 50%)
    lpat["*Param6 Description"] = "Landing Stun Length"
    lpat["Param7"] = "175"  # Leap Speed %
    lpat["Param8"] = "10"   # +10%/lvl Damage synergy from Leap
    lpat["calc3"] = f"{RAMP34}+skill('Leap'.blvl)*par8"
    lpat["*calc3 desc"] = "Max Damage % at Full Stamina"
    lpat["calc1"] = f"((clc3+50)*({RESTED_PCT}))/100-50"
    lpat["calc2"] = f"90+((par7-90)*({RESTED_PCT}))/100"
    lpat["calc4"] = f"(({RESTED_PCT})>=50)?par6:0"
    lpat["*calc4 desc"] = "Landing Stun Length (Requires >= 50% Stamina)"
    lpat["calc5"] = "433"   # Cast Bar Stamina Reflex (Id 433) during leap
    lpat["*calc5 desc"] = "Skill ID to cast when leap ends"
    lpat["calc6"] = "10"    # sLvl 10 Bar Stamina Reflex (strong single-target/pack Stamina drain on landing)
    lpat["*calc6 desc"] = "Level of cast skill ID"
    lpat["DmgSymPerCalc"] = f"((75+skill('Leap'.blvl)*par8)*({RESTED_PCT}))/100-75"

    # Whirlwind (Id 151, Col 2 Row 6, Req Lvl 40, requires Leap Attack and Berserk):
    # 0 Mana, uses srvdofunc=168 (Talic's Whirlwind) to cast Bar Stamina Reflex (Id 433 at sLvl 2).
    # Damage % (calc1) degrades smoothly via gradient from Full Stamina (RAMP12 + Leap/Leap Attack synergies) down to -50% at Zero Stamina.
    ww = by_name["Whirlwind"]
    ww["reqlevel"] = "40"
    ww["reqskill1"] = "Leap Attack"
    ww["reqskill2"] = "Berserk"
    ww["reqskill3"] = ""
    ww["srvdofunc"] = "168"
    ww["minmana"] = "0"
    ww["mana"] = "0"
    ww["lvlmana"] = "0"
    ww["Param1"] = "80"   # Damage % baseline (+80% at Lvl 1)
    ww["Param2"] = "14"   # Damage % per level (ramped -> +346% at Lvl 20)
    ww["Param8"] = "8"    # +8%/lvl Damage synergy from Leap and Leap Attack
    ww["*Param8 Description"] = "Damage % synergy from Leap and Leap Attack"
    ww["calc1"] = f"(({RAMP12}+(skill('Leap'.blvl)+skill('Leap Attack'.blvl))*par8+50)*({RESTED_PCT}))/100-50"
    ww["calc2"] = "2"     # sLvl 2 Bar Stamina Reflex (2.67x stronger Stamina drain than sLvl 1 @ EMin=6)
    ww["*calc2 desc"] = "Escalation 1 Skill Level"
    ww["calc3"] = "100"
    ww["*calc3 desc"] = "Chance to Cast Escalation 1 Skill"
    ww["calc4"] = "0"
    ww["*calc4 desc"] = "Escalation 2 Skill Level"
    ww["calc5"] = "0"
    ww["*calc5 desc"] = "Chance To Cast Escalation 2 Skill"
    ww["calc6"] = "433"   # Cast Bar Stamina Reflex (Id 433, EType=stam monster reflection) while spinning
    ww["*calc6 desc"] = "Escalation 1 Skill Id"
    ww["calc7"] = "0"
    ww["*calc7desc"] = "Escalation 2 Skill Id"
    ww["aurastat1"] = ""
    ww["aurastatcalc1"] = ""
    ww["TargetableOnly"] = ""
    ww["AttackNoMana"] = ""

    # -------------------------------------------------------------------------
    # 2. "WELL-RESTED" SKILLS (Bash 126, Shield Slam 139, Concentrate 144)
    #    Scale UP continuously with current Stamina % (RESTED_PCT: 0% -> 100%)
    # -------------------------------------------------------------------------
    # Rested Bash (Id 126, Col 1 Row 1, Req Lvl 1, no prerequisites):
    # Disciplined heavy blow that scales strongly with current Stamina %.
    bash = by_name["Bash"]
    bash["reqlevel"] = "1"
    bash["reqskill1"] = ""
    bash["reqskill2"] = ""
    bash["reqskill3"] = ""
    bash["minmana"] = "0"
    bash["mana"] = "0"
    bash["lvlmana"] = "0"
    bash["Param1"] = "30"   # Base Damage % baseline (+30% at Lvl 1)
    bash["Param2"] = "6"    # Base Damage % per level (ramped -> +144% at Lvl 20)
    bash["Param3"] = "2"    # Flat Damage baseline (+2 at Lvl 1)
    bash["Param4"] = "1"    # Flat Damage per level (ramped -> +21 at Lvl 20)
    bash["Param7"] = "8"    # Attack Rating synergy from Concentrate
    bash["Param8"] = "6"    # Damage % synergy from Concentrate
    bash["calc2"] = RAMP34
    bash["calc5"] = f"{RAMP12}+skill('Concentrate'.blvl)*par8"
    bash["*calc5 desc"] = "Base Damage % at Zero Stamina"
    bash["calc6"] = "40+(lvl-1)*5"
    bash["*calc6 desc"] = "Max Well-Rested Damage % Bonus at Full Stamina"
    bash["calc1"] = f"clc5+(({RESTED_PCT})*clc6)/100"

    # Shield Slam (Id 139, replaces Stun, Col 1 Row 5, Req Lvl 32, requires Concentrate):
    # Tactical Shield-Requiring Charge (srvstfunc=31, srvdofunc=67, cltstfunc=25, cltdofunc=37)
    # Strictly requires an equipped Shield (itypea1="shld"), 0 Mana cost, 25-frame (1.0s) localdelay,
    # AttackNoMana="" so it NEVER falls back to regular attack when in melee range or on cooldown,
    # full 100% weapon damage (SrcDam=128) + 4x Shield Block % bonus at full stamina + Well-Rested Stamina scaling,
    # and knocks back and actively stuns the impacted target!
    stun = by_name["Stun"]
    stun["reqlevel"] = "32"
    stun["reqskill1"] = "Concentrate"
    stun["reqskill2"] = ""
    stun["reqskill3"] = ""
    stun["srvstfunc"] = "31"
    stun["srvdofunc"] = "67"
    stun["stsuccessonly"] = "1"
    stun["cltstfunc"] = "25"
    stun["cltdofunc"] = "37"
    stun["attackrank"] = "3"
    stun["range"] = "none"
    stun["weapsel"] = ""
    stun["itypea1"] = "shld"  # Strictly requires an equipped Shield!
    stun["anim"] = "SQ"
    stun["seqtrans"] = "A1"
    stun["monanim"] = "xx"
    stun["seqnum"] = "4"
    stun["seqinput"] = "8"
    stun["durability"] = "1"
    stun["UseAttackRate"] = ""
    stun["LineOfSight"] = ""
    stun["interrupt"] = ""
    stun["TargetableOnly"] = "1"
    stun["SearchEnemyXY"] = "1"
    stun["AttackNoMana"] = ""  # Never auto-switch to regular attack when in melee range or on cooldown!
    stun["KeepCursorStateOnKill"] = "1"
    stun["localdelay"] = "25"  # 1.0-second local casting delay (25 frames)
    stun["minmana"] = "0"      # 0 Mana cost
    stun["mana"] = "0"
    stun["lvlmana"] = "0"
    stun["Param1"] = "200"  # Charge Velocity % (+200% sprint speed)
    stun["*Param1 Description"] = "Velocity %"
    stun["Param2"] = ""     # Must be empty for Charge (cltdofunc=37)
    stun["*Param2 Description"] = ""
    stun["Param3"] = "100"  # Base Damage % baseline (+100% at Lvl 1)
    stun["*Param3 Description"] = "Damage % baseline"
    stun["Param4"] = "15"   # Base Damage % per level (ramped -> +385% at Lvl 20)
    stun["*Param4 Description"] = "Damage % per level"
    stun["Param6"] = ""
    stun["*Param6 Description"] = ""
    stun["Param7"] = "12"   # Attack Rating synergy % from Concentrate (+12%/lvl)
    stun["Param8"] = "8"    # Damage % synergy from Strike and Concentrate (+8%/lvl)
    stun["calc5"] = f"{RAMP34}+stat('toblock'.accr)*2+(skill('Bash'.blvl)+skill('Concentrate'.blvl))*par8"
    stun["*calc5 desc"] = "Base Damage % at Zero Stamina"
    stun["calc6"] = "100+(lvl-1)*15+stat('toblock'.accr)*2"
    stun["*calc6 desc"] = "Max Well-Rested Damage % Bonus at Full Stamina"
    stun["calc1"] = f"clc5+(({RESTED_PCT})*clc6)/100"
    stun["calc2"] = "par1"
    stun["*calc2 desc"] = "Velocity %"
    stun["calc3"] = "stat('toblock'.accr)*4"
    stun["*calc3 desc"] = "Shield Block Damage % Bonus at Full Stamina"
    stun["calc4"] = "0"
    stun["*calc4 desc"] = "% Damage Dealt as Elemental"
    stun["ToHit"] = "75"
    stun["LevToHit"] = "15"
    stun["ToHitCalc"] = "75+(lvl-1)*15+skill('Concentrate'.blvl)*par7"
    stun["HitShift"] = "8"
    stun["SrcDam"] = "128"  # Full 100% Weapon Damage (rate-limited by 25-frame localdelay)
    stun["EType"] = "stun"
    stun["ELen"] = "30"     # 1.2s base stun (+0.2s/lvl -> 5.0s at Lvl 20, capped at 250 frames = 10s)
    stun["ELevLen1"] = "5"
    stun["ELevLen2"] = "5"
    stun["ELevLen3"] = "5"
    stun["ELenSymPerCalc"] = f"(({RESTED_PCT})*50)/100"

    # Rested Concentrate (Id 144, Col 1 Row 3, Req Lvl 16, requires Bash):
    # Uninterruptible precision strike; both Damage % and Defense % scale UP with current Stamina %.
    conc = by_name["Concentrate"]
    conc["reqlevel"] = "16"
    conc["reqskill1"] = "Bash"
    conc["reqskill2"] = ""
    conc["reqskill3"] = ""
    conc["minmana"] = "0"
    conc["mana"] = "0"
    conc["lvlmana"] = "0"
    conc["EType"] = ""
    conc["calc4"] = "0"
    conc["Param1"] = "50"   # Base Damage % baseline (+50% at Lvl 1)
    conc["Param2"] = "8"    # Base Damage % per level (ramped -> +202% at Lvl 20)
    conc["Param3"] = "100"  # Base Defense % baseline (+100% at Lvl 1)
    conc["Param4"] = "10"   # Base Defense % per level (ramped -> +290% at Lvl 20, +580% at Full Stamina)
    conc["Param7"] = "6"    # Damage % synergy from Shield Slam (Stun)
    conc["Param8"] = "6"    # Damage % synergy from Bash
    conc["calc5"] = f"{RAMP12}+skill('Bash'.blvl)*par8+skill('Stun'.blvl)*par7"
    conc["*calc5 desc"] = "Base Damage % at Zero Stamina"
    conc["calc6"] = "60+(lvl-1)*10"
    conc["*calc6 desc"] = "Max Well-Rested Damage % Bonus at Full Stamina"
    conc["calc1"] = f"clc5+(({RESTED_PCT})*clc6)/100"
    conc["aurastatcalc1"] = f"{RAMP34}+(({RESTED_PCT})*{RAMP34})/100"

    # -------------------------------------------------------------------------
    # 3. "EXHAUSTION / LAST STAND" SKILLS (Double Swing 133, Double Throw 140, Frenzy 147, Berserk 152)
    #    Scale UP continuously with missing Stamina % (EXHAUST_PCT: 0% -> 100%)
    #    and are the ONLY skills amplified by Bloodlust (Id 150)!
    # -------------------------------------------------------------------------
    # Desperate Berserk (Id 152, Berserk, Col 3 Row 5, Req Lvl 32, requires Double Throw):
    # Strictly requires a Two-Handed Melee Weapon (itypea1="2hml")!
    # Drops Defense to 0 and converts all damage to Magic; surges in Magic Damage % and AR % as Stamina drops toward 0,
    # and is amplified by Bloodlust (Id 150)!
    berz = by_name["Berserk"]
    berz["reqlevel"] = "32"
    berz["reqskill1"] = "Double Throw"
    berz["reqskill2"] = ""
    berz["reqskill3"] = ""
    berz["minmana"] = "0"
    berz["mana"] = "0"
    berz["lvlmana"] = "0"
    berz["itypea1"] = "2hml"  # Strictly requires a Two-Handed Melee Weapon!
    berz["Param1"] = "80"     # Base Magic Damage % baseline (+80% at Lvl 1)
    berz["Param2"] = "12"     # Base Magic Damage % per level (ramped -> +308% at Lvl 20)
    berz["Param8"] = "8"      # Magic Damage % synergy from Double Swing and Desperate Frenzy
    berz["calc5"] = f"{RAMP12}+(skill('Double Swing'.blvl)+skill('Frenzy'.blvl))*par8"
    berz["*calc5 desc"] = "Base Magic Damage % at Full Stamina"
    berz["calc6"] = f"100+(lvl-1)*20+{BLOODLUST_MAX_DMG}"
    berz["*calc6 desc"] = "Max Exhaustion Magic Damage % Bonus at Zero Stamina"
    berz["calc1"] = f"clc5+(({EXHAUST_PCT})*clc6)/100"
    berz["ToHitCalc"] = f"100+(lvl-1)*15+{BLOODLUST_CUR_AR}"

    # Desperate Swing (Id 133, Double Swing, Col 3 Row 1, Req Lvl 1, no prerequisites):
    # 0 Mana; surges in Damage % and Attack Rating % as Stamina drops toward 0.
    dswg = by_name["Double Swing"]
    dswg["reqlevel"] = "1"
    dswg["reqskill1"] = ""
    dswg["reqskill2"] = ""
    dswg["reqskill3"] = ""
    dswg["minmana"] = "0"
    dswg["mana"] = "0"
    dswg["lvlmana"] = "0"
    dswg["Param3"] = "25"   # Base Damage % baseline (+25% at Lvl 1)
    dswg["*Param3 Description"] = "Damage % baseline"
    dswg["Param4"] = "6"    # Base Damage % per level (ramped -> +139% at Lvl 20)
    dswg["*Param4 Description"] = "Damage % per level"
    dswg["Param8"] = "6"    # Damage % synergy from Double Throw
    dswg["calc5"] = f"{RAMP34}+skill('Double Throw'.blvl)*par8"
    dswg["*calc5 desc"] = "Base Damage % at Full Stamina"
    dswg["calc6"] = f"50+(lvl-1)*10+{BLOODLUST_MAX_DMG}"
    dswg["*calc6 desc"] = "Max Exhaustion Damage % Bonus at Zero Stamina"
    dswg["calc1"] = f"clc5+(({EXHAUST_PCT})*clc6)/100"
    dswg["ToHitCalc"] = f"15+(lvl-1)*5+{BLOODLUST_CUR_AR}"

    # Desperate Throw (Id 140, Double Throw, Col 3 Row 3, Req Lvl 16, requires Double Swing):
    # 0 Mana; surges in Damage % and Attack Rating % as Stamina drops toward 0.
    dthr = by_name["Double Throw"]
    dthr["reqlevel"] = "16"
    dthr["reqskill1"] = "Double Swing"
    dthr["reqskill2"] = ""
    dthr["reqskill3"] = ""
    dthr["minmana"] = "0"
    dthr["mana"] = "0"
    dthr["lvlmana"] = "0"
    dthr["Param1"] = "40"   # Base Damage % baseline (+40% at Lvl 1)
    dthr["Param2"] = "8"    # Base Damage % per level (ramped -> +192% at Lvl 20)
    dthr["Param8"] = "8"    # Damage % synergy from Double Swing
    dthr["calc5"] = f"{RAMP12}+skill('Double Swing'.blvl)*par8"
    dthr["*calc5 desc"] = "Base Damage % at Full Stamina"
    dthr["calc6"] = f"70+(lvl-1)*15+{BLOODLUST_MAX_DMG}"
    dthr["*calc6 desc"] = "Max Exhaustion Damage % Bonus at Zero Stamina"
    dthr["calc1"] = f"clc5+(({EXHAUST_PCT})*clc6)/100"
    dthr["ToHitCalc"] = f"20+(lvl-1)*10+{BLOODLUST_CUR_AR}"

    # Desperate Frenzy (Id 147, Frenzy, Col 3 Row 6, Req Lvl 40, requires Berserk):
    # 0 Mana; Last Stand dual-wield flurry that surges in Damage % and Attack Rating % as Stamina drops toward 0.
    fren = by_name["Frenzy"]
    fren["reqlevel"] = "40"
    fren["reqskill1"] = "Berserk"
    fren["reqskill2"] = ""
    fren["reqskill3"] = ""
    fren["minmana"] = "0"
    fren["mana"] = "0"
    fren["lvlmana"] = "0"
    fren["srvmissilea"] = ""
    fren["aurafilter"] = ""
    fren["auratargetstate"] = ""
    fren["aurarangecalc"] = ""
    fren["auralencalc"] = "par7"
    fren["passivestate"] = ""
    fren["Param1"] = "70"   # Base Damage % baseline (+70% at Lvl 1)
    fren["Param2"] = "10"   # Base Damage % per level (ramped -> +260% at Lvl 20)
    fren["Param3"] = "20"   # Velocity % Min
    fren["Param4"] = "180"  # Velocity % Max
    fren["Param5"] = "10"   # Attack Speed % Min
    fren["Param6"] = "50"   # Attack Speed % Max
    fren["Param7"] = "150"  # Duration (6.0 seconds)
    fren["Param8"] = "8"    # Damage synergy % from Double Swing and Berserk
    fren["calc5"] = f"{RAMP12}+(skill('Double Swing'.blvl)+skill('Berserk'.blvl))*par8"
    fren["*calc5 desc"] = "Base Damage % at Full Stamina"
    fren["calc6"] = f"90+(lvl-1)*20+{BLOODLUST_MAX_DMG}"
    fren["*calc6 desc"] = "Max Exhaustion Damage % Bonus at Zero Stamina"
    fren["calc1"] = f"clc5+(({EXHAUST_PCT})*clc6)/100"
    fren["calc4"] = "skill('Berserk'.blvl)"
    fren["ToHitCalc"] = f"100+(lvl-1)*7+{BLOODLUST_CUR_AR}"
    fren["aurastat1"] = "velocitypercent"
    fren["aurastatcalc1"] = "dm34"
    fren["aurastat2"] = "attackrate"
    fren["aurastatcalc2"] = "dm56"
    fren["aurastat3"] = ""
    fren["aurastatcalc3"] = ""
    fren["aurastat4"] = ""
    fren["aurastatcalc4"] = ""
    fren["auraevent1"] = ""
    fren["auraeventfunc1"] = ""
    fren["auraevent2"] = ""
    fren["auraeventfunc2"] = ""
    fren["auraevent3"] = ""
    fren["auraeventfunc3"] = ""
    fren["auraevent4"] = ""
    fren["auraeventfunc4"] = ""
    fren["HitShift"] = "8"
    fren["EType"] = "mag"
    fren["EMin"] = ""
    fren["EMax"] = ""

    # -------------------------------------------------------------------------
    # 4. COMBAT MASTERIES & STAMINA CONTROL WARCRIES (127..129, 134..136, 141, 131, 138, 142, 149, 150)
    # -------------------------------------------------------------------------
    # One-Handed Mastery (Id 127, replaces Blade Mastery, Row 1 Col 1, Req Lvl 1):
    # +Attack Rating % and +Damage % with all strictly 1-handed melee weapons (passiveitype="1hml").
    ohm = by_name["Blade Mastery"]
    ohm["reqlevel"] = "1"
    ohm["passiveitype"] = "1hml"
    ohm["passivestat1"] = "passive_mastery_melee_th"
    ohm["passivecalc1"] = "ln12"
    ohm["passivestat2"] = "passive_mastery_melee_dmg"
    ohm["passivecalc2"] = "ln34"
    ohm["passivestat3"] = ""
    ohm["passivecalc3"] = ""
    ohm["Param1"] = "40"
    ohm["Param2"] = "8"
    ohm["Param3"] = "28"
    ohm["Param4"] = "5"
    ohm["Param5"] = ""
    ohm["*Param5 Description"] = ""
    ohm["Param6"] = ""
    ohm["*Param6 Description"] = ""

    # Two-Handed Mastery (Id 128, replaces Axe Mastery, Row 1 Col 2, Req Lvl 1):
    # +Attack Rating % and +Damage % with all 2-handed melee weapons (passiveitype="2hml", including all 2H swords).
    thm = by_name["Axe Mastery"]
    thm["reqlevel"] = "1"
    thm["passiveitype"] = "2hml"
    thm["passivestat1"] = "passive_mastery_melee_th"
    thm["passivecalc1"] = "ln12"
    thm["passivestat2"] = "passive_mastery_melee_dmg"
    thm["passivecalc2"] = "ln34"
    thm["passivestat3"] = ""
    thm["passivecalc3"] = ""
    thm["Param1"] = "40"
    thm["Param2"] = "8"
    thm["Param3"] = "28"
    thm["Param4"] = "5"
    thm["Param5"] = ""
    thm["*Param5 Description"] = ""
    thm["Param6"] = ""
    thm["*Param6 Description"] = ""

    # Throwing Mastery (Id 135, moved to Row 1 Col 3, Req Lvl 1):
    # +Attack Rating %, +Damage %, Pierce %, Chance Not to Consume Quantity %, and Replenish on Crit (Crit pulled to Id 134).
    thrw = by_name["Throwing Mastery"]
    thrw["reqlevel"] = "1"
    thrw["passiveitype"] = "thro"
    thrw["passivestat1"] = "passive_mastery_throw_th"
    thrw["passivecalc1"] = "ln12"
    thrw["passivestat2"] = "passive_mastery_throw_dmg"
    thrw["passivecalc2"] = "ln34"
    thrw["passivestat3"] = "skill_pierce"
    thrw["passivecalc3"] = "dm78"
    thrw["passivestat4"] = "passive_mastery_noconsume"
    thrw["passivecalc4"] = "dm91"
    thrw["passivestat5"] = "passive_mastery_replenish_oncrit"
    thrw["passivecalc5"] = "pa11"
    thrw["passivestat6"] = ""
    thrw["passivecalc6"] = ""
    thrw["Param5"] = ""
    thrw["*Param5 Description"] = ""
    thrw["Param6"] = ""
    thrw["*Param6 Description"] = ""

    # Critical Strike (Id 134, replaces Pole Arm Mastery, Row 2 Col 2, Req Lvl 8):
    # Universal Critical Strike % that works with ANY equipped melee or thrown weapon (passiveitype="weap").
    crit = by_name["Pole Arm Mastery"]
    crit["reqlevel"] = "8"
    crit["reqskill1"] = ""
    crit["passiveitype"] = "weap"
    crit["passivestat1"] = "passive_mastery_melee_crit"
    crit["passivecalc1"] = "dm12"
    crit["passivestat2"] = "passive_mastery_throw_crit"
    crit["passivecalc2"] = "dm12"
    crit["passivestat3"] = ""
    crit["passivecalc3"] = ""
    crit["Param1"] = "8"
    crit["*Param1 Description"] = "% chance for Critical Hit Min"
    crit["Param2"] = "50"
    crit["*Param2 Description"] = "% chance for Critical Hit Max"
    crit["Param3"] = ""
    crit["*Param3 Description"] = ""
    crit["Param4"] = ""
    crit["*Param4 Description"] = ""
    crit["Param5"] = ""
    crit["*Param5 Description"] = ""
    crit["Param6"] = ""
    crit["*Param6 Description"] = ""

    # Left-Side Chain (Column 1: Unflinching [Row 2, Lvl 8] -> Increased Speed [Row 3, Lvl 16] -> Battle Fervor [Row 5, Lvl 32])
    # Unflinching (Id 141, replaces Increased Stamina, Row 2 Col 1, Req Lvl 8): Passive Faster Hit Recovery %.
    istam = by_name["Increased Stamina"]
    istam["reqlevel"] = "8"
    istam["reqskill1"] = ""
    istam["passivestat1"] = "item_fastergethitrate"
    istam["passivecalc1"] = "dm12"
    istam["Param1"] = "15"  # Faster Hit Recovery % Min (+15% at Lvl 1)
    istam["*Param1 Description"] = "Faster Hit Recovery % Min"
    istam["Param2"] = "75"  # Faster Hit Recovery % Max (+75% ceiling)
    istam["*Param2 Description"] = "Faster Hit Recovery % Max"

    # Increased Speed (Id 148, moved to Row 3 Col 1, Req Lvl 16, requires Unflinching): Passive Faster Run/Walk %.
    ispd = by_name["Increased Speed"]
    ispd["reqlevel"] = "16"
    ispd["reqskill1"] = "Increased Stamina"

    # Battle Fervor (Id 129, replaces Mace Mastery, moved to Row 5 Col 1, Req Lvl 32, requires Increased Speed):
    # Universal passive Increased Attack Speed % (item_fasterattackrate).
    ferv = by_name["Mace Mastery"]
    ferv["reqlevel"] = "32"
    ferv["reqskill1"] = "Increased Speed"
    ferv["passiveitype"] = ""
    ferv["passivestat1"] = "item_fasterattackrate"
    ferv["passivecalc1"] = "dm12"
    ferv["passivestat2"] = ""
    ferv["passivecalc2"] = ""
    ferv["passivestat3"] = ""
    ferv["passivecalc3"] = ""
    ferv["Param1"] = "7"
    ferv["*Param1 Description"] = "Attack Speed % Min"
    ferv["Param2"] = "40"
    ferv["*Param2 Description"] = "Attack Speed % Max"
    ferv["Param3"] = ""
    ferv["*Param3 Description"] = ""
    ferv["Param4"] = ""
    ferv["*Param4 Description"] = ""
    ferv["Param5"] = ""
    ferv["*Param5 Description"] = ""
    ferv["Param6"] = ""
    ferv["*Param6 Description"] = ""

    # Right-Side Chain (Column 3: Iron Skin [Row 3, Lvl 16] -> Venom Ward [Row 4, Lvl 24] -> Natural Resistance [Row 6, Lvl 40])
    # Iron Skin (Id 145, Row 3 Col 3, Req Lvl 16): Passive Defense %.
    iskin = by_name["Iron Skin"]
    iskin["reqlevel"] = "16"
    iskin["reqskill1"] = ""

    # Venom Ward (Id 136, replaces Spear Mastery, moved to Row 4 Col 3, Req Lvl 24, requires Iron Skin):
    # Universal passive Poison Length Reduced % (item_poisonlengthresist) and +Maximum Poison Resist % (maxpoisonresist).
    vward = by_name["Spear Mastery"]
    vward["reqlevel"] = "24"
    vward["reqskill1"] = "Iron Skin"
    vward["passiveitype"] = ""
    vward["passivestat1"] = "item_poisonlengthresist"
    vward["passivecalc1"] = "dm12"
    vward["passivestat2"] = "maxpoisonresist"
    vward["passivecalc2"] = "clc1"
    vward["passivestat3"] = ""
    vward["passivecalc3"] = ""
    vward["Param1"] = "15"
    vward["*Param1 Description"] = "Poison Length Reduced % Min"
    vward["Param2"] = "75"
    vward["*Param2 Description"] = "Poison Length Reduced % Max"
    vward["Param3"] = ""
    vward["*Param3 Description"] = ""
    vward["Param4"] = ""
    vward["*Param4 Description"] = ""
    vward["Param5"] = ""
    vward["*Param5 Description"] = ""
    vward["Param6"] = ""
    vward["*Param6 Description"] = ""
    vward["calc1"] = "min(15,2+lvl/2)"
    vward["*calc1 desc"] = "+Maximum Poison Resist %"

    # Natural Resistance (Id 153, Row 6 Col 3, Req Lvl 40, requires Venom Ward): Passive All Resistances %.
    nres = by_name["Natural Resistance"]
    nres["reqlevel"] = "40"
    nres["reqskill1"] = "Spear Mastery"

    # Shout (Id 138, Col 1 Row 1, Req Lvl 1, no prerequisites):
    # Mutually exclusive with Enduring Cry (Id 142) via state group 11!
    # Grants ONLY flat Physical Damage Reduced (normal_damage_reduction: 3 at Lvl 1 -> 41 at Lvl 20 via RAMP12).
    shout = by_name["Shout"]
    shout["reqlevel"] = "1"
    shout["reqskill1"] = ""
    shout["reqskill2"] = ""
    shout["reqskill3"] = ""
    shout["InTown"] = ""
    shout["localdelay"] = "75"
    shout["globaldelay"] = "75"
    shout["minmana"] = "1"
    shout["manashift"] = "7"
    shout["mana"] = "10"
    shout["lvlmana"] = "1"
    shout["auralencalc"] = "ln34"
    shout["Param1"] = "3"    # Flat Physical Damage Reduced baseline (3 at Lvl 1)
    shout["*Param1 Description"] = "Physical Damage Reduced baseline"
    shout["Param2"] = "2"    # Flat Physical Damage Reduced per level (ramped -> 41 at Lvl 20)
    shout["*Param2 Description"] = "Physical Damage Reduced per level"
    shout["Param3"] = "500"  # Duration baseline (20 seconds)
    shout["Param4"] = "13"   # Duration per level (+0.52 seconds/lvl -> 29.88s at Lvl 20)
    shout["Param5"] = ""
    shout["*Param5 Description"] = ""
    shout["Param6"] = ""
    shout["*Param6 Description"] = ""
    shout["Param7"] = ""
    shout["*Param7 Description"] = ""
    shout["Param8"] = ""
    shout["*Param8 Description"] = ""
    shout["calc1"] = RAMP12
    shout["*calc1 desc"] = "Physical Damage Reduced"
    shout["calc2"] = ""
    shout["*calc2 desc"] = ""
    shout["aurastat1"] = "normal_damage_reduction"
    shout["aurastatcalc1"] = "clc1"
    shout["aurastat2"] = ""
    shout["aurastatcalc2"] = ""
    shout["aurastat3"] = ""
    shout["aurastatcalc3"] = ""
    shout["aurastat4"] = ""
    shout["aurastatcalc4"] = ""

    # Battle Command (Id 155, Col 1 Row 4, Req Lvl 24, requires Shout):
    # Short-acting restorative warcry mirroring Second Wind (Id 131): exchanges Mana on a 3.0s shared cooldown
    # for an immediate flat Life heal (60 Life at Lvl 1 -> 402 Life at Lvl 20 via RAMP12, +10/lvl from Shout).
    bcmd = by_name["Battle Command"]
    bcmd["reqlevel"] = "24"
    bcmd["reqskill1"] = "Shout"
    bcmd["reqskill2"] = ""
    bcmd["reqskill3"] = ""
    bcmd["auralencalc"] = "5"
    bcmd["aurastat1"] = "hpregen"
    bcmd["aurastatcalc1"] = "(clc1*256)/5"
    bcmd["aurastat2"] = ""
    bcmd["aurastatcalc2"] = ""
    bcmd["aurastat3"] = ""
    bcmd["aurastatcalc3"] = ""
    bcmd["InTown"] = ""
    bcmd["localdelay"] = "75"
    bcmd["globaldelay"] = "75"
    bcmd["minmana"] = "1"
    bcmd["manashift"] = "7"
    bcmd["mana"] = "22"
    bcmd["lvlmana"] = "1"
    bcmd["Param1"] = "60"   # Instant Life Restored baseline (60 at Lvl 1)
    bcmd["*Param1 Description"] = "Life Restored baseline"
    bcmd["Param2"] = "18"   # Instant Life Restored per level (ramped -> 402 at Lvl 20)
    bcmd["*Param2 Description"] = "Life Restored per level"
    bcmd["Param3"] = ""
    bcmd["*Param3 Description"] = ""
    bcmd["Param7"] = "10"   # +10 flat Life Restored per level of Shout
    bcmd["*Param7 Description"] = "Life Restored synergy from Shout"
    bcmd["Param8"] = ""
    bcmd["*Param8 Description"] = ""
    bcmd["calc1"] = f"{RAMP12}+skill('Shout'.blvl)*par7"
    bcmd["*calc1 desc"] = "Life Restored"

    # Battle Orders (Id 149, Col 1 Row 5, Req Lvl 32, requires Battle Command):
    # Pure Maximum Life % Warcry (removed Max Mana % and Max Stamina % so Barbarians cannot expand their Mana pool).
    # Mutually exclusive with Bloodlust (Id 150) via state group 10!
    bo = by_name["Battle Orders"]
    bo["reqlevel"] = "32"
    bo["reqskill1"] = "Battle Command"
    bo["reqskill2"] = ""
    bo["reqskill3"] = ""
    bo["InTown"] = ""
    bo["localdelay"] = "75"
    bo["globaldelay"] = "75"
    bo["minmana"] = "1"
    bo["manashift"] = "7"
    bo["mana"] = "28"
    bo["lvlmana"] = "1"
    bo["auralencalc"] = "ln12"
    bo["Param1"] = "500"  # Duration baseline (20 seconds)
    bo["Param2"] = "13"   # Duration per level (+0.52 seconds/lvl -> 29.88s at Lvl 20)
    bo["Param8"] = ""
    bo["*Param8 Description"] = ""
    bo["aurastat1"] = "item_maxhp_percent"
    bo["aurastatcalc1"] = "ln34"
    bo["aurastat2"] = ""
    bo["aurastatcalc2"] = ""
    bo["aurastat3"] = ""
    bo["aurastatcalc3"] = ""

    # Center Column Warcries (Col 2): Taunt (Row 2) -> Howl (Row 3) -> Battle Cry (Row 4) -> War Cry (Row 6)
    taunt = by_name["Taunt"]
    taunt["reqlevel"] = "8"
    taunt["reqskill1"] = ""
    taunt["reqskill2"] = ""
    taunt["reqskill3"] = ""
    taunt["InTown"] = ""
    taunt["localdelay"] = "75"
    taunt["globaldelay"] = "75"
    taunt["minmana"] = "1"
    taunt["manashift"] = "8"
    taunt["mana"] = "3"
    taunt["lvlmana"] = "0"

    howl = by_name["Howl"]
    howl["reqlevel"] = "16"
    howl["reqskill1"] = "Taunt"
    howl["reqskill2"] = ""
    howl["reqskill3"] = ""
    howl["InTown"] = ""
    howl["localdelay"] = "75"
    howl["globaldelay"] = "75"
    howl["minmana"] = "1"
    howl["manashift"] = "7"
    howl["mana"] = "14"
    howl["lvlmana"] = "1"

    bcry = by_name["Battle Cry"]
    bcry["reqlevel"] = "24"
    bcry["reqskill1"] = "Howl"
    bcry["reqskill2"] = ""
    bcry["reqskill3"] = ""
    bcry["InTown"] = ""
    bcry["localdelay"] = "75"
    bcry["globaldelay"] = "75"
    bcry["minmana"] = "1"
    bcry["manashift"] = "7"
    bcry["mana"] = "20"
    bcry["lvlmana"] = "1"
    bcry["Param1"] = "300"  # Duration baseline (12 seconds)
    bcry["Param2"] = "23"   # Duration per level (+0.92 seconds/lvl -> 29.48s at Lvl 20)

    # War Cry (Id 154, Col 2 Row 6, Req Lvl 40, requires Battle Orders + Battle Cry + Bloodlust):
    # Capstone "Shattering Roar" for Tactical, Hybrid, and Berserker Barbarians alike!
    # Unleashes a 360-degree radial shockwave that stuns surrounding enemies (1.4s -> 6.0s) AND applies
    # bar_warcry_debuff (reducing Enemy Physical Resistance [damageresist] and Enemy Magic Resistance [magicresist]
    # by -18% at Lvl 1 -> -75% at Lvl 20 with 1pt Battle Cry, plus -1% per additional point in Battle Cry).
    wcry = by_name["War Cry"]
    wcry["reqlevel"] = "40"
    wcry["reqskill1"] = "Battle Orders"
    wcry["reqskill2"] = "Battle Cry"
    wcry["reqskill3"] = "Grim Ward"
    wcry["InTown"] = ""
    wcry["localdelay"] = "75"
    wcry["globaldelay"] = "75"
    wcry["aurafilter"] = "98304"
    wcry["auratargetstate"] = "bar_warcry_debuff"
    wcry["auralencalc"] = "par3+(lvl-1)*par4"
    wcry["aurastat1"] = "damageresist"
    wcry["aurastatcalc1"] = "-clc1"
    wcry["aurastat2"] = "magicresist"
    wcry["aurastatcalc2"] = "-clc1"
    wcry["minmana"] = "1"
    wcry["manashift"] = "7"
    wcry["mana"] = "32"
    wcry["lvlmana"] = "1"
    wcry["Param1"] = "35"   # Stun Length baseline (1.4 seconds at Lvl 1)
    wcry["*Param1 Description"] = "Stun Length baseline"
    wcry["Param2"] = "6"    # Stun Length per level (+0.24 seconds/lvl -> 6.0s at Lvl 20)
    wcry["*Param2 Description"] = "Stun Length per level"
    wcry["Param3"] = "200"  # Debuff Duration baseline (8.0 seconds)
    wcry["*Param3 Description"] = "Debuff Duration baseline"
    wcry["Param4"] = "25"   # Debuff Duration per level (+1.0 second/lvl -> 27.0s at Lvl 20)
    wcry["*Param4 Description"] = "Debuff Duration per level"
    wcry["Param5"] = "17"   # Enemy Physical & Magic Resistance Reduced % baseline (17% at Lvl 1 -> 18% with 1pt Battle Cry)
    wcry["*Param5 Description"] = "Enemy Physical & Magic Resistance Reduced % baseline"
    wcry["Param6"] = "3"    # Enemy Physical & Magic Resistance Reduced % per level (+3%/lvl -> 74% base, 75% at Lvl 20 with 1pt Battle Cry)
    wcry["*Param6 Description"] = "Enemy Physical & Magic Resistance Reduced % per level"
    wcry["Param7"] = "1"    # +1% Enemy Physical & Magic Resistance Reduced per level of Battle Cry
    wcry["*Param7 Description"] = "Resistance break synergy from Battle Cry"
    wcry["Param8"] = ""
    wcry["*Param8 Description"] = ""
    wcry["calc1"] = "ln56+skill('Battle Cry'.blvl)*par7"
    wcry["*calc1 desc"] = "Enemy Physical & Magic Resistance Reduced %"
    wcry["calc4"] = "min(250,ln12)"
    wcry["*calc4 desc"] = "Stun Length"
    wcry["MinDam"] = "1"
    wcry["MinLevDam1"] = ""
    wcry["MinLevDam2"] = ""
    wcry["MinLevDam3"] = ""
    wcry["MinLevDam4"] = ""
    wcry["MinLevDam5"] = ""
    wcry["MaxDam"] = "2"
    wcry["MaxLevDam1"] = ""
    wcry["MaxLevDam2"] = ""
    wcry["MaxLevDam3"] = ""
    wcry["MaxLevDam4"] = ""
    wcry["MaxLevDam5"] = ""
    wcry["DmgSymPerCalc"] = ""

    # Right Column Warcries (Col 3): Enduring Cry (Row 1) -> Second Wind (Row 3) -> Bloodlust (Row 5)
    # Second Wind (Id 131, replaces Find Potion, Col 3 Row 3, Req Lvl 16, requires Find Item):
    # Active Warcry that exchanges Mana for an immediate Stamina refill.
    swind = by_name["Find Potion"]
    swind["reqlevel"] = "16"
    swind["reqskill1"] = "Find Item"
    swind["reqskill2"] = ""
    swind["reqskill3"] = ""
    swind["srvstfunc"] = ""
    swind["srvdofunc"] = "68"
    swind["srvmissilea"] = "battlecommand"
    swind["aurastate"] = "bar_second_wind"
    swind["auratargetstate"] = "bar_second_wind"
    swind["auralencalc"] = "2"
    swind["aurastat1"] = "staminarecoverybonus"
    swind["aurastatcalc1"] = "(clc1*15000*256)/max(256,stat('maxstamina'.accr))-100"
    swind["aurastat2"] = "item_staminadrainpct"
    swind["aurastatcalc2"] = "100"
    swind["stsuccessonly"] = ""
    swind["stsoundclass"] = "barbarian_shout_1"
    swind["tgtsound"] = ""
    swind["cltstfunc"] = ""
    swind["cltdofunc"] = "25"
    swind["cltmissilea"] = "battlecommand"
    swind["range"] = "none"
    swind["anim"] = "SC"
    swind["seqtrans"] = "SC"
    swind["UseAttackRate"] = "1"
    swind["SearchEnemyNear"] = ""
    swind["SelectProc"] = ""
    swind["TargetCorpse"] = ""
    swind["InTown"] = ""
    swind["localdelay"] = "75"
    swind["globaldelay"] = "75"
    swind["minmana"] = "1"
    swind["manashift"] = "7"
    swind["mana"] = "16"
    swind["lvlmana"] = "1"
    swind["Param1"] = "60"  # Instant Stamina Restored baseline (60 at Lvl 1)
    swind["*Param1 Description"] = "Stamina Restored baseline"
    swind["Param2"] = "18"  # Instant Stamina Restored per level (ramped -> 402 at Lvl 20)
    swind["*Param2 Description"] = "Stamina Restored per level"
    swind["Param3"] = ""
    swind["Param4"] = ""
    swind["calc1"] = RAMP12
    swind["*calc1 desc"] = "Stamina Restored"

    # Enduring Cry (Id 142, replaces Find Item, Col 3 Row 1, Req Lvl 1, no prerequisites):
    # Mutually exclusive with Shout (Id 138) via state group 11!
    # Grants ONLY flat Maximum Stamina (maxstamina: +25 at Lvl 1 -> +253 at Lvl 20 via RAMP12,
    # plus +5 per hard point in Second Wind -> up to +353 flat Max Stamina!).
    ecry = by_name["Find Item"]
    ecry["reqlevel"] = "1"
    ecry["reqskill1"] = ""
    ecry["reqskill2"] = ""
    ecry["reqskill3"] = ""
    ecry["srvstfunc"] = ""
    ecry["srvdofunc"] = "68"
    ecry["srvmissilea"] = "battleorders"
    ecry["aurafilter"] = ""
    ecry["aurastate"] = "bar_battle_trance"
    ecry["auratargetstate"] = "bar_battle_trance"
    ecry["auralencalc"] = "ln34"
    ecry["aurarangecalc"] = ""
    ecry["aurastat1"] = "maxstamina"
    ecry["aurastatcalc1"] = "clc1*256"
    ecry["aurastat2"] = ""
    ecry["aurastatcalc2"] = ""
    ecry["aurastat3"] = ""
    ecry["aurastatcalc3"] = ""
    ecry["aurastat4"] = ""
    ecry["aurastatcalc4"] = ""
    ecry["auraevent1"] = ""
    ecry["auraeventfunc1"] = ""
    ecry["auraevent2"] = ""
    ecry["auraeventfunc2"] = ""
    ecry["auraevent3"] = ""
    ecry["auraeventfunc3"] = ""
    ecry["auraevent4"] = ""
    ecry["auraeventfunc4"] = ""
    ecry["stsuccessonly"] = ""
    ecry["stsoundclass"] = "barbarian_battleorders_1"
    ecry["dosound"] = ""
    ecry["castoverlay"] = ""
    ecry["cltstfunc"] = ""
    ecry["cltdofunc"] = "25"
    ecry["cltmissilea"] = "battleorders"
    ecry["range"] = "none"
    ecry["anim"] = "SC"
    ecry["seqtrans"] = "SC"
    ecry["UseAttackRate"] = "1"
    ecry["SearchEnemyNear"] = ""
    ecry["SelectProc"] = ""
    ecry["TargetCorpse"] = ""
    ecry["InTown"] = ""
    ecry["localdelay"] = "75"
    ecry["globaldelay"] = "75"
    ecry["periodic"] = ""
    ecry["perdelay"] = ""
    ecry["minmana"] = "1"
    ecry["manashift"] = "7"
    ecry["mana"] = "10"
    ecry["lvlmana"] = "1"
    ecry["Param1"] = "25"    # Flat Max Stamina baseline (+25 at Lvl 1)
    ecry["*Param1 Description"] = "Flat Max Stamina baseline"
    ecry["Param2"] = "12"    # Flat Max Stamina per level (ramped -> +253 at Lvl 20)
    ecry["*Param2 Description"] = "Flat Max Stamina per level"
    ecry["Param3"] = "500"   # Duration baseline (20 seconds, matching Shout)
    ecry["*Param3 Description"] = "Duration baseline"
    ecry["Param4"] = "13"    # Duration per level (+0.52 seconds/lvl -> 29.88s at Lvl 20)
    ecry["*Param4 Description"] = "Duration per level"
    ecry["Param5"] = ""
    ecry["*Param5 Description"] = ""
    ecry["Param6"] = ""
    ecry["*Param6 Description"] = ""
    ecry["Param7"] = "5"     # +5 flat Max Stamina per level of Second Wind
    ecry["*Param7 Description"] = "Flat Max Stamina synergy from Second Wind"
    ecry["Param8"] = ""
    ecry["*Param8 Description"] = ""
    ecry["calc1"] = f"{RAMP12}+skill('Find Potion'.blvl)*par7"
    ecry["*calc1 desc"] = "Flat Max Stamina"
    ecry["calc2"] = ""
    ecry["*calc2 desc"] = ""

    # Bloodlust (Id 150, replaces Grim Ward, Col 3 Row 5, Req Lvl 32, requires Find Potion):
    # Active self-buff Warcry (mutually exclusive with Battle Orders via state group 10!)
    # that amplifies Desperate Swing, Desperate Throw, and Desperate Frenzy Damage % and Attack Rating % as Stamina drops toward zero,
    # at the cost of a progressive Life Drain (hpregen < 0) while active!
    blust = by_name["Grim Ward"]
    blust["reqlevel"] = "32"
    blust["reqskill1"] = "Find Potion"
    blust["reqskill2"] = ""
    blust["reqskill3"] = ""
    blust["srvstfunc"] = ""
    blust["srvdofunc"] = "18"
    blust["prgcalc1"] = ""
    blust["srvmissilea"] = "shout"
    blust["srvmissileb"] = ""
    blust["srvmissilec"] = ""
    blust["aurafilter"] = ""
    blust["aurastate"] = "bar_totem_debuff"
    blust["auratargetstate"] = ""
    blust["auralencalc"] = "par7+(lvl-1)*par8"
    blust["aurarangecalc"] = ""
    blust["aurastat1"] = "hpregen"
    blust["aurastatcalc1"] = "-(clc5*256)/25"
    blust["aurastat2"] = "skill_chillingarmor"
    blust["aurastatcalc2"] = "1"
    blust["aurastat3"] = ""
    blust["aurastatcalc3"] = ""
    blust["aurastat4"] = ""
    blust["aurastatcalc4"] = ""
    blust["auraevent1"] = ""
    blust["auraeventfunc1"] = ""
    blust["auraevent2"] = ""
    blust["auraeventfunc2"] = ""
    blust["ItemEffect"] = ""
    blust["passive"] = ""
    blust["passivestate"] = ""
    blust["passivestat1"] = ""
    blust["passivecalc1"] = ""
    blust["stsoundclass"] = "barbarian_warcry_1"
    blust["tgtsound"] = ""
    blust["cltstfunc"] = ""
    blust["cltdofunc"] = "25"
    blust["cltmissilea"] = "shout"
    blust["cltmissileb"] = ""
    blust["cltmissilec"] = ""
    blust["range"] = "none"
    blust["anim"] = "SC"
    blust["seqtrans"] = "SC"
    blust["UseAttackRate"] = "1"
    blust["LineOfSight"] = ""
    blust["SearchOpenXY"] = ""
    blust["SearchEnemyNear"] = ""
    blust["SelectProc"] = ""
    blust["TargetCorpse"] = ""
    blust["InTown"] = ""
    blust["localdelay"] = "75"
    blust["globaldelay"] = "75"
    blust["leftskill"] = "0"
    blust["rightskill"] = "1"
    blust["minmana"] = "1"
    blust["manashift"] = "7"
    blust["mana"] = "28"
    blust["lvlmana"] = "1"
    blust["periodic"] = ""
    blust["perdelay"] = ""
    blust["progressive"] = ""
    blust["Param1"] = "30"   # Max Exhaustion Damage % Bonus baseline (+30% at Lvl 1)
    blust["*Param1 Description"] = "Max Exhaustion Damage % baseline"
    blust["Param2"] = "14"   # Max Exhaustion Damage % Bonus per level (ramped -> +296% at Lvl 20)
    blust["*Param2 Description"] = "Max Exhaustion Damage % per level"
    blust["Param3"] = "20"   # Max Exhaustion Attack Rating % Bonus baseline (+20% at Lvl 1)
    blust["*Param3 Description"] = "Max Exhaustion Attack Rating % baseline"
    blust["Param4"] = "8"    # Max Exhaustion Attack Rating % Bonus per level (ramped -> +172% at Lvl 20)
    blust["*Param4 Description"] = "Max Exhaustion Attack Rating % per level"
    blust["Param5"] = "4"    # Life Drained per Second baseline (4 Life/sec at Lvl 1)
    blust["*Param5 Description"] = "Life Drained per Second baseline"
    blust["Param6"] = "1"    # Life Drained per Second per level (ramped -> 23 Life/sec at Lvl 20)
    blust["*Param6 Description"] = "Life Drained per Second per level"
    blust["Param7"] = "500"  # Duration baseline (20 seconds)
    blust["*Param7 Description"] = "Duration baseline"
    blust["Param8"] = "13"   # Duration per level (+0.52 seconds/lvl -> 29.88s at Lvl 20)
    blust["*Param8 Description"] = "Duration per level"
    blust["calc1"] = RAMP12
    blust["*calc1 desc"] = "Max Exhaustion Damage % Bonus at Zero Stamina"
    blust["calc2"] = RAMP34
    blust["*calc2 desc"] = "Max Exhaustion Attack Rating % Bonus at Zero Stamina"
    blust["calc3"] = f"(({EXHAUST_PCT})*clc1)/100"
    blust["*calc3 desc"] = "Current Exhaustion Damage % Bonus"
    blust["calc4"] = f"(({EXHAUST_PCT})*clc2)/100"
    blust["*calc4 desc"] = "Current Exhaustion Attack Rating % Bonus"
    blust["calc5"] = RAMP56
    blust["*calc5 desc"] = "Life Drained per Second"


def _apply_barbarian_skilldesc(by_desc: Dict[str, Dict[str, str]]) -> None:
    """Update skilldesc.txt tooltips for the Barbarian Stamina Pendulum Overhaul."""
    # 1. Well-Rested Skills: Rested Bash (126, Col 1 Row 1), Shield Slam (139, Col 1 Row 5), Rested Concentrate (144, Col 1 Row 3)
    bash_d = by_desc["bash"]
    bash_d["SkillColumn"] = "1"
    bash_d["SkillRow"] = "1"
    _set_dsc_line(bash_d, "desc", 1, "74", "ModBarWellRestedBonus", "", "clc6", "")
    _set_dsc_line(bash_d, "desc", 2, "74", "StrSkillDamagePercent", "", "clc1", "")
    _set_dsc_line(bash_d, "desc", 3, "74", "StrSkillDamageFlat", "", "clc2", "")
    _set_dsc_line(bash_d, "desc", 4, "74", "StrSkill22", "", "toht", "")
    _set_dsc_line(bash_d, "dsc2", 1, "", "", "", "", "")
    _clear_dsc3_synergies(bash_d, "skillname126")
    _set_dsc_line(bash_d, "dsc3", 2, "76", "Damplev", "skillname144", "par8", "")
    _set_dsc_line(bash_d, "dsc3", 3, "76", "AttRateplev", "skillname144", "par7", "")

    stun_d = by_desc["stun"]
    stun_d["SkillColumn"] = "1"
    stun_d["SkillRow"] = "5"
    stun_d["descatt"] = "2"
    _set_dsc_line(stun_d, "desc", 1, "74", "ModBarWellRestedBonus", "", "clc6", "")
    _set_dsc_line(stun_d, "desc", 2, "74", "ModBarShieldBlockDmg", "", "clc3", "")
    _set_dsc_line(stun_d, "desc", 3, "74", "StrSkillDamagePercent", "", "clc1", "")
    _set_dsc_line(stun_d, "desc", 4, "36", "StrSkillStunLengthSingular", "StrSkill48", "min(250,edln)", "25")
    _set_dsc_line(stun_d, "desc", 5, "74", "StrSkill22", "", "toht", "")
    _set_dsc_line(stun_d, "dsc2", 1, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "25", "25")
    _set_dsc_line(stun_d, "dsc2", 2, "", "", "", "", "")
    _clear_dsc3_synergies(stun_d, "skillname139")
    _set_dsc_line(stun_d, "dsc3", 2, "76", "Damplev", "skillname126", "par8", "")
    _set_dsc_line(stun_d, "dsc3", 3, "76", "Damplev", "skillname144", "par8", "")
    _set_dsc_line(stun_d, "dsc3", 4, "76", "AttRateplev", "skillname144", "par7", "")

    conc_d = by_desc["concentrate"]
    conc_d["SkillColumn"] = "1"
    conc_d["SkillRow"] = "3"
    _set_dsc_line(conc_d, "desc", 1, "74", "ModBarWellRestedBonus", "", "clc6", "")
    _set_dsc_line(conc_d, "desc", 2, "74", "StrSkillDamagePercent", "", "clc1", "")
    _set_dsc_line(conc_d, "desc", 3, "74", "StrSkill21", "", f"{RAMP34}+((stat('stamina'.accr)*100)/max(256,stat('maxstamina'.accr))*{RAMP34})/100", "")
    _set_dsc_line(conc_d, "desc", 4, "74", "StrSkill22", "", "toht", "")
    _set_dsc_line(conc_d, "dsc2", 1, "", "", "", "", "")
    _clear_dsc3_synergies(conc_d, "skillname144")
    _set_dsc_line(conc_d, "dsc3", 2, "76", "Damplev", "skillname126", "par8", "")
    _set_dsc_line(conc_d, "dsc3", 3, "76", "Damplev", "skillname139", "par7", "")

    # 2. Exhaustion / Last Stand Skills: Desperate Swing (133, Col 3 Row 1), Desperate Throw (140, Col 3 Row 3),
    #    Desperate Berserk (152, Col 3 Row 5), Desperate Frenzy (147, Col 3 Row 6)
    dswg_d = by_desc["double swing"]
    dswg_d["SkillColumn"] = "3"
    dswg_d["SkillRow"] = "1"
    _set_dsc_line(dswg_d, "desc", 1, "74", "ModBarExhaustedBonus", "", "clc6", "")
    _set_dsc_line(dswg_d, "desc", 2, "74", "StrSkillDamagePercent", "", "clc1", "")
    _set_dsc_line(dswg_d, "desc", 3, "74", "StrSkill22", "", "toht", "")
    _set_dsc_line(dswg_d, "dsc2", 1, "", "", "", "", "")
    _clear_dsc3_synergies(dswg_d, "skillname133")
    _set_dsc_line(dswg_d, "dsc3", 2, "76", "Damplev", "skillname140", "par8", "")

    dthr_d = by_desc["double throw"]
    dthr_d["SkillColumn"] = "3"
    dthr_d["SkillRow"] = "3"
    dthr_d["ddam calc1"] = "clc1"
    _set_dsc_line(dthr_d, "desc", 1, "74", "ModBarExhaustedBonus", "", "clc6", "")
    _set_dsc_line(dthr_d, "desc", 2, "74", "StrSkillDamagePercent", "", "clc1", "")
    _set_dsc_line(dthr_d, "desc", 3, "74", "StrSkill22", "", "toht", "")
    _set_dsc_line(dthr_d, "dsc2", 1, "", "", "", "", "")
    _clear_dsc3_synergies(dthr_d, "skillname140")
    _set_dsc_line(dthr_d, "dsc3", 2, "76", "Damplev", "skillname133", "par8", "")

    fren_d = by_desc["frenzy"]
    fren_d["SkillColumn"] = "3"
    fren_d["SkillRow"] = "6"
    _set_dsc_line(fren_d, "desc", 1, "74", "ModBarExhaustedBonus", "", "clc6", "")
    _set_dsc_line(fren_d, "desc", 2, "74", "StrSkillDamagePercent", "", "clc1", "")
    _set_dsc_line(fren_d, "desc", 3, "75", "StrSkillRunWalkRange", "", "15*(par4-par3)/100+par3", "dm34")
    _set_dsc_line(fren_d, "desc", 4, "75", "StrSkillAttackSpeedRange", "", "15*(par6-par5)/100+par5", "dm56")
    _set_dsc_line(fren_d, "desc", 5, "74", "StrSkill22", "", "toht", "")
    _set_dsc_line(fren_d, "dsc2", 1, "36", "StrSkillDurationSingular", "StrSkill20", "par7", "25")
    _set_dsc_line(fren_d, "dsc2", 2, "74", "StrSkillMagicDamagePercent", "", "clc4", "")
    _set_dsc_line(fren_d, "dsc2", 3, "", "", "", "", "")
    _clear_dsc3_synergies(fren_d, "skillname147")
    _set_dsc_line(fren_d, "dsc3", 2, "76", "Damplev", "skillname133", "par8", "")
    _set_dsc_line(fren_d, "dsc3", 3, "76", "Damplev", "skillname152", "par8", "")
    _set_dsc_line(fren_d, "dsc3", 4, "76", "Magdplev", "skillname152", "1", "")

    berz_d = by_desc["berserk"]
    berz_d["SkillColumn"] = "3"
    berz_d["SkillRow"] = "5"
    _set_dsc_line(berz_d, "desc", 1, "74", "ModBarExhaustedBonus", "", "clc6", "")
    _set_dsc_line(berz_d, "desc", 2, "74", "StrSkillMagicDamagePercent", "", "clc1", "")
    _set_dsc_line(berz_d, "desc", 3, "74", "StrSkill22", "", "toht", "")
    _set_dsc_line(berz_d, "desc", 4, "36", "StrSkillDurationSingular", "StrSkill20", '"par4-min(((110*lvl)/(lvl+6)*(par4-par3)/100),(par4-par3))"', "25")
    _set_dsc_line(berz_d, "dsc2", 1, "", "", "", "", "")
    _clear_dsc3_synergies(berz_d, "skillname152")
    _set_dsc_line(berz_d, "dsc3", 2, "76", "Magdplev", "skillname133", "par8", "")
    _set_dsc_line(berz_d, "dsc3", 3, "76", "Magdplev", "skillname147", "par8", "")

    # 3. Stamina Spender Skills: Leap (132, Col 2 Row 2), Leap Attack (143, Col 2 Row 4), Whirlwind (151, Col 2 Row 6)
    leap_d = by_desc["leap"]
    leap_d["SkillColumn"] = "2"
    leap_d["SkillRow"] = "2"
    _set_dsc_line(leap_d, "desc", 1, "36", "StrSkillKnockbackRadius", "StrSkillKnockbackRadius", "clc1*2", "3")
    _set_dsc_line(leap_d, "desc", 2, "36", "StrSkillRangeRadius", "StrSkillRangeRadius", "clc3*2", "3")
    _set_dsc_line(leap_d, "dsc2", 1, "74", "ModBarStamCostJump", "", "12", "")

    lpat_d = by_desc["leap attack"]
    lpat_d["SkillColumn"] = "2"
    lpat_d["SkillRow"] = "4"
    _set_dsc_line(lpat_d, "desc", 1, "74", "ModBarStamDegradePenalty", "", "-50", "")
    _set_dsc_line(lpat_d, "desc", 2, "74", "StrSkillDamagePercent", "", "clc1", "")
    _set_dsc_line(lpat_d, "desc", 3, "74", "StrSkill22", "", "toht", "")
    _set_dsc_line(lpat_d, "desc", 4, "75", "StrSkill4", "", "pnma", "pxma")
    _set_dsc_line(lpat_d, "desc", 5, "36", "StrSkillRadiusSingular", "StrSkill18", "7*2", "3")
    _set_dsc_line(lpat_d, "dsc2", 1, "74", "ModBarStamCostJump", "", "16", "")
    _set_dsc_line(lpat_d, "dsc2", 2, "36", "StrSkill9", "StrSkill20", "clc4", "25")

    ww_d = by_desc["whirlwind"]
    ww_d["SkillColumn"] = "2"
    ww_d["SkillRow"] = "6"
    _set_dsc_line(ww_d, "desc", 1, "74", "ModBarStamCostSpin", "", "6", "")
    _set_dsc_line(ww_d, "desc", 2, "74", "ModBarStamDegradePenalty", "", "-50", "")
    _set_dsc_line(ww_d, "desc", 3, "74", "StrSkillDamagePercent", "", "clc1", "")
    _set_dsc_line(ww_d, "desc", 4, "74", "StrSkill22", "", "toht", "")
    _clear_dsc3_synergies(ww_d, "skillname151")
    _set_dsc_line(ww_d, "dsc3", 2, "76", "Damplev", "skillname132", "par8", "")
    _set_dsc_line(ww_d, "dsc3", 3, "76", "Damplev", "skillname143", "par8", "")

    # 4. Stamina Control Warcries & Passives:
    # Combat Masteries (127 One-Handed Mastery, 128 Two-Handed Mastery, 135 Throwing Mastery,
    #                   134 Critical Strike, 129 Battle Fervor, 136 Venom Ward, 141 Unflinching)
    ohm_d = by_desc["blade mastery"]
    _set_dsc_line(ohm_d, "desc", 1, "74", "StrSkillDamagePercent", "", "madm", "")
    _set_dsc_line(ohm_d, "desc", 2, "74", "StrSkill22", "", "math", "")
    _set_dsc_line(ohm_d, "desc", 3, "", "", "", "", "")

    thm_d = by_desc["axe mastery"]
    _set_dsc_line(thm_d, "desc", 1, "74", "StrSkillDamagePercent", "", "madm", "")
    _set_dsc_line(thm_d, "desc", 2, "74", "StrSkill22", "", "math", "")
    _set_dsc_line(thm_d, "desc", 3, "", "", "", "", "")

    thrw_d = by_desc["throwing mastery"]
    thrw_d["SkillRow"] = "1"
    thrw_d["SkillColumn"] = "3"
    _set_dsc_line(thrw_d, "desc", 1, "18", "StrSkillReplenishOnCrit", "", "", "")
    _set_dsc_line(thrw_d, "desc", 2, "74", "StrSkillNoConsumeChance", "", "manc", "")
    _set_dsc_line(thrw_d, "desc", 3, "74", "StrSkillPiercingChance", "", "mapi", "")
    _set_dsc_line(thrw_d, "desc", 4, "74", "StrSkillDamagePercent", "", "madm", "")
    _set_dsc_line(thrw_d, "desc", 5, "74", "StrSkill22", "", "math", "")
    _set_dsc_line(thrw_d, "desc", 6, "", "", "", "", "")

    crit_d = by_desc["pole arm mastery"]
    crit_d["SkillRow"] = "2"
    crit_d["SkillColumn"] = "2"
    _set_dsc_line(crit_d, "desc", 1, "74", "eskillincasemasteryX", "", "dm12", "")
    _set_dsc_line(crit_d, "desc", 2, "", "", "", "", "")
    _set_dsc_line(crit_d, "desc", 3, "", "", "", "", "")

    # Left Chain (Col 1): Unflinching (Row 2) -> Increased Speed (Row 3) -> Battle Fervor (Row 5)
    istam_d = by_desc["increased stamina"]
    istam_d["SkillRow"] = "2"
    istam_d["SkillColumn"] = "1"
    _set_dsc_line(istam_d, "desc", 1, "74", "ModBarFHRPassive", "", "dm12", "")

    ispd_d = by_desc["increased speed"]
    ispd_d["SkillRow"] = "3"
    ispd_d["SkillColumn"] = "1"

    ferv_d = by_desc["mace mastery"]
    ferv_d["SkillRow"] = "5"
    ferv_d["SkillColumn"] = "1"
    _set_dsc_line(ferv_d, "desc", 1, "74", "ModBarAttackSpeedPassive", "", "dm12", "")
    _set_dsc_line(ferv_d, "desc", 2, "", "", "", "", "")
    _set_dsc_line(ferv_d, "desc", 3, "", "", "", "", "")

    # Right Chain (Col 3): Iron Skin (Row 3) -> Venom Ward (Row 4) -> Natural Resistance (Row 6)
    iskin_d = by_desc["iron skin"]
    iskin_d["SkillRow"] = "3"
    iskin_d["SkillColumn"] = "3"

    vward_d = by_desc["spear mastery"]
    vward_d["SkillRow"] = "4"
    vward_d["SkillColumn"] = "3"
    _set_dsc_line(vward_d, "desc", 1, "74", "ModBarPoisonLenRedPassive", "", "dm12", "")
    _set_dsc_line(vward_d, "desc", 2, "74", "ModBarMaxPoisResPassive", "", "clc1", "")
    _set_dsc_line(vward_d, "desc", 3, "", "", "", "", "")

    nres_d = by_desc["natural resistance"]
    nres_d["SkillRow"] = "6"
    nres_d["SkillColumn"] = "3"

    # Shout (shout, Id 138, Col 1 Row 1): Mutually exclusive with Enduring Cry (group 11), grants ONLY flat Physical Damage Reduced
    shout_d = by_desc["shout"]
    shout_d["SkillColumn"] = "1"
    shout_d["SkillRow"] = "1"
    _set_dsc_line(shout_d, "desc", 1, "74", "ModActiveFlatPDR", "", "clc1", "")
    _set_dsc_line(shout_d, "desc", 2, "36", "StrSkillDurationSingular", "StrSkill20", "len", "25")
    _set_dsc_line(shout_d, "desc", 3, "36", "StrSkillRadiusSingular", "StrSkill18", "19*2", "3")
    for i in range(4, 7):
        _set_dsc_line(shout_d, "desc", i, "", "", "", "", "")
    _set_dsc_line(shout_d, "dsc2", 1, "36", "StrSkill3", "", "usmc", "256")
    _set_dsc_line(shout_d, "dsc2", 2, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "75", "25")
    for i in range(1, 7):
        _set_dsc_line(shout_d, "dsc3", i, "", "", "", "", "")

    # Battle Command (battle command, Id 155, Col 1 Row 4): Short-cooldown restorative warcry that heals flat Life
    bcmd_d = by_desc["battle command"]
    bcmd_d["SkillColumn"] = "1"
    bcmd_d["SkillRow"] = "4"
    _set_dsc_line(bcmd_d, "desc", 1, "74", "ModBarLifeRestore", "", "clc1", "")
    _set_dsc_line(bcmd_d, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "19*2", "3")
    for i in range(3, 7):
        _set_dsc_line(bcmd_d, "desc", i, "", "", "", "", "")
    _set_dsc_line(bcmd_d, "dsc2", 1, "36", "StrSkill3", "", "usmc", "256")
    _set_dsc_line(bcmd_d, "dsc2", 2, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "75", "25")
    _set_dsc_line(bcmd_d, "dsc3", 1, "40", "Sksyn", "skillname155", "2", "")
    _set_dsc_line(bcmd_d, "dsc3", 2, "76", "ModSynLifeRestorePerLev", "skillname138", "par7", "")
    for i in range(3, 7):
        _set_dsc_line(bcmd_d, "dsc3", i, "", "", "", "", "")

    # Battle Orders (battle orders, Id 149, Col 1 Row 5): Pure Max Life % Warcry (removed Max Mana % and Max Stamina %)
    bo_d = by_desc["battle orders"]
    bo_d["SkillColumn"] = "1"
    bo_d["SkillRow"] = "5"
    _set_dsc_line(bo_d, "desc", 2, "74", "StrSkill100", "", "ln34", "")
    _set_dsc_line(bo_d, "desc", 3, "36", "StrSkillRadiusSingular", "StrSkill18", "19*2", "3")
    _set_dsc_line(bo_d, "desc", 4, "", "", "", "", "")
    _set_dsc_line(bo_d, "desc", 5, "", "", "", "", "")
    _set_dsc_line(bo_d, "dsc2", 1, "36", "StrSkill3", "", "usmc", "256")
    _set_dsc_line(bo_d, "dsc2", 2, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "75", "25")
    for i in range(1, 7):
        _set_dsc_line(bo_d, "dsc3", i, "", "", "", "", "")

    # Center Column Warcries (Col 2): Taunt (Row 2) -> Howl (Row 3) -> Battle Cry (Row 4) -> War Cry (Row 6)
    taunt_d = by_desc["taunt"]
    taunt_d["SkillColumn"] = "2"
    taunt_d["SkillRow"] = "2"
    _set_dsc_line(taunt_d, "dsc2", 1, "36", "StrSkill3", "", "usmc", "256")
    _set_dsc_line(taunt_d, "dsc2", 2, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "75", "25")

    howl_d = by_desc["howl"]
    howl_d["SkillColumn"] = "2"
    howl_d["SkillRow"] = "3"
    _set_dsc_line(howl_d, "dsc2", 1, "36", "StrSkill3", "", "usmc", "256")
    _set_dsc_line(howl_d, "dsc2", 2, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "75", "25")

    bcry_d = by_desc["battle cry"]
    bcry_d["SkillColumn"] = "2"
    bcry_d["SkillRow"] = "4"
    _set_dsc_line(bcry_d, "dsc2", 1, "36", "StrSkill3", "", "usmc", "256")
    _set_dsc_line(bcry_d, "dsc2", 2, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "75", "25")

    wcry_d = by_desc["war cry"]
    wcry_d["SkillColumn"] = "2"
    wcry_d["SkillRow"] = "6"
    wcry_d["descdam"] = ""
    _set_dsc_line(wcry_d, "desc", 1, "36", "StrSkillStunLengthSingular", "StrSkill48", "min(250,ln12)", "25")
    _set_dsc_line(wcry_d, "desc", 2, "74", "ModBarWarCryPhysMagBreak", "", "-clc1", "")
    _set_dsc_line(wcry_d, "desc", 3, "36", "StrSkillDurationSingular", "StrSkill20", "len", "25")
    _set_dsc_line(wcry_d, "desc", 4, "36", "StrSkillRadiusSingular", "StrSkill18", "7*2", "3")
    _set_dsc_line(wcry_d, "desc", 5, "", "", "", "", "")
    _set_dsc_line(wcry_d, "desc", 6, "", "", "", "", "")
    _set_dsc_line(wcry_d, "dsc2", 1, "36", "StrSkill3", "", "usmc", "256")
    _set_dsc_line(wcry_d, "dsc2", 2, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "75", "25")
    _set_dsc_line(wcry_d, "dsc3", 1, "40", "Sksyn", "skillname154", "2", "")
    _set_dsc_line(wcry_d, "dsc3", 2, "76", "ModSynPhysMagBreakPerLev", "skillname146", "par7", "")
    for i in range(3, 7):
        _set_dsc_line(wcry_d, "dsc3", i, "", "", "", "", "")

    # Second Wind (find potion, Id 131, Col 3 Row 3)
    swind = by_desc["find potion"]
    swind["SkillColumn"] = "3"
    swind["SkillRow"] = "3"
    _set_dsc_line(swind, "desc", 1, "74", "ModBarStamRestore", "", "clc1", "")
    _set_dsc_line(swind, "dsc2", 1, "36", "StrSkill3", "", "usmc", "256")
    _set_dsc_line(swind, "dsc2", 2, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "75", "25")
    for i in range(1, 7):
        _set_dsc_line(swind, "dsc3", i, "", "", "", "", "")

    # Enduring Cry (find item, Id 142, Col 3 Row 1): Mutually exclusive with Shout (group 11), grants ONLY flat Max Stamina
    ecry = by_desc["find item"]
    ecry["SkillColumn"] = "3"
    ecry["SkillRow"] = "1"
    _set_dsc_line(ecry, "desc", 1, "74", "ModBarMaxStamFlat", "", "clc1", "")
    _set_dsc_line(ecry, "desc", 2, "36", "StrSkillDurationSingular", "StrSkill20", "len", "25")
    _set_dsc_line(ecry, "desc", 3, "36", "StrSkillRadiusSingular", "StrSkill18", "19*2", "3")
    for i in range(4, 7):
        _set_dsc_line(ecry, "desc", i, "", "", "", "", "")
    _set_dsc_line(ecry, "dsc2", 1, "36", "StrSkill3", "", "usmc", "256")
    _set_dsc_line(ecry, "dsc2", 2, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "75", "25")
    _set_dsc_line(ecry, "dsc3", 1, "40", "Sksyn", "skillname142", "2", "")
    _set_dsc_line(ecry, "dsc3", 2, "76", "ModSynMaxStamPerLev", "skillname131", "par7", "")
    for i in range(3, 7):
        _set_dsc_line(ecry, "dsc3", i, "", "", "", "", "")

    # Bloodlust (grim ward, Id 150, Col 3 Row 5): Active Warcry Exhaustion Damage & AR Amplifier for Desperate Skills + Progressive Life Drain
    blust = by_desc["grim ward"]
    blust["SkillColumn"] = "3"
    blust["SkillRow"] = "5"
    _set_dsc_line(blust, "desc", 1, "74", "ModBarBloodlustMaxDmg", "", "clc1", "")
    _set_dsc_line(blust, "desc", 2, "74", "ModBarBloodlustCurDmg", "", "clc3", "")
    _set_dsc_line(blust, "desc", 3, "74", "ModBarBloodlustMaxAR", "", "clc2", "")
    _set_dsc_line(blust, "desc", 4, "74", "ModBarBloodlustDrain", "", "clc5", "")
    _set_dsc_line(blust, "desc", 5, "36", "StrSkillDurationSingular", "StrSkill20", "len", "25")
    _set_dsc_line(blust, "dsc2", 1, "36", "StrSkill3", "", "usmc", "256")
    _set_dsc_line(blust, "dsc2", 2, "36", "StrSkillCastingDelaySingular", "StrSkillCastingDelayPlural", "75", "25")
    for i in range(3, 7):
        _set_dsc_line(blust, "dsc2", i, "", "", "", "", "")
    for i in range(1, 7):
        _set_dsc_line(blust, "dsc3", i, "", "", "", "", "")


def apply_skill_missile_updates(rows_by_name: Dict[str, Dict[str, str]]) -> None:
    """Apply skill-related missile updates (called by weapons_armor.build_missiles and build_skills_all)."""
    # 1. Holy Bolt: Velocity 20 -> 30 for crisp line piercing & ally healing
    if "holybolt" in rows_by_name:
        hb = rows_by_name["holybolt"]
        hb["Vel"] = "30"
        hb["MaxVel"] = "30"

    # 1b. Blessed Hammer: Straight-line bouncing "Chain Hammer" that knocks back and stuns on each bounce!
    # Velocity scales with skill level via VelLev (Vel=16 at sLvl 1 -> ~31 at sLvl 20, capped at MaxVel=40).
    if "blessedhammer" in rows_by_name:
        bh = rows_by_name["blessedhammer"]
        bh["pCltDoFunc"] = "1"
        bh["pSrvDoFunc"] = "1"
        bh["pCltHitFunc"] = "16"
        bh["pSrvHitFunc"] = "12"
        bh["sHitPar1"] = "0"
        bh["cHitPar1"] = "0"
        bh["pSrvDmgFunc"] = "7"       # Apply skill calc4 Stun Length on hit
        bh["dParam1"] = "0"           # Use skill calc4 for stun duration
        bh["dParam2"] = "0"
        bh["Vel"] = "16"              # Starts at 16 velocity at sLvl 1
        bh["VelLev"] = "6"            # +0.75 velocity per skill level (6/8 per lvl -> ~30.25 at sLvl 20, ~38 at sLvl 30)
        bh["MaxVel"] = "40"           # Cap velocity at 40
        bh["Accel"] = ""
        bh["Range"] = "35"
        bh["Size"] = "2"
        bh["Pierce"] = ""
        bh["CollideKill"] = "1"
        bh["ClientCol"] = "1"
        bh["NextHit"] = "1"
        bh["NextDelay"] = "4"
        bh["ResultFlags"] = "5"       # 4 (GetHit) + 1 (Knockback)
        bh["ProgOverlay"] = "doubledamage1"  # Swirling stun overlay on hit

    # 2. Fist of the Heavens radial Holy Bolts: Velocity 12 -> 18, scaled to ~40%-45% of Holy Bolt's damage
    # (30-40 at sLvl 1 -> 231-276 base at sLvl 20, 1,340-1,601 with max synergies vs Holy Bolt's 3,555-4,122),
    # synergized by Holy Bolt (12%) + Sanctuary (12%).
    if "fistoftheheavensbolt" in rows_by_name:
        fohb = rows_by_name["fistoftheheavensbolt"]
        fohb["Vel"] = "18"
        fohb["MaxVel"] = "18"
        fohb["EMin"] = "30"
        fohb["MinELev1"] = "3"
        fohb["MinELev2"] = "10"
        fohb["MinELev3"] = "25"
        fohb["MinELev4"] = "30"
        fohb["MinELev5"] = "35"
        fohb["EMax"] = "40"
        fohb["MaxELev1"] = "4"
        fohb["MaxELev2"] = "12"
        fohb["MaxELev3"] = "28"
        fohb["MaxELev4"] = "34"
        fohb["MaxELev5"] = "40"
        fohb["EDmgSymPerCalc"] = "(skill('Holy Bolt'.blvl)+skill('Sanctuary'.blvl))*12"

    # 3. Chest & Environmental Trap Missiles:
    #    Scale raw pre-resistance trap damage to ~100% of expected character Life across Normal,
    #    Nightmare, and Hell (so a character with ~50% resistance loses ~50% of their Life total,
    #    while wide min-max roll variance makes opening chests with low resistances genuinely dangerous).
    #    Note: For trap entities (trap-firebolt, trap-nova, trap-poisoncloud), D2Game.dll spawns the
    #    missile via MONAI_TrapMissile / Skill1 at sLvl = max(1, mLvl / 6) (sLvl=3 in Normal at mLvl=18,
    #    sLvl=8 in Nightmare at mLvl=48, sLvl=13 in Hell at mLvl=78).
    if "trapnova" in rows_by_name:
        tn = rows_by_name["trapnova"]
        tn["HitShift"] = "8"
        tn["EType"] = "ltng"
        tn["EMin"] = "60"
        tn["MinELev1"] = "60"
        tn["MinELev2"] = "110"
        tn["MinELev3"] = "160"
        tn["MinELev4"] = "180"
        tn["MinELev5"] = "200"
        tn["EMax"] = "200"
        tn["MaxELev1"] = "180"
        tn["MaxELev2"] = "330"
        tn["MaxELev3"] = "480"
        tn["MaxELev4"] = "540"
        tn["MaxELev5"] = "600"

    if "trapfirebolt" in rows_by_name:
        tfb = rows_by_name["trapfirebolt"]
        tfb["HitShift"] = "8"
        tfb["EType"] = "fire"
        # Ensure a SINGLE Fire Bolt hit deals full chest trap damage (~150-500 raw in Normal,
        # ~500-1,600 raw in Nightmare, ~950-3,000 raw in Hell) since the player only gets hit by 1 bolt
        tfb["EMin"] = "70"
        tfb["MinELev1"] = "55"
        tfb["MinELev2"] = "105"
        tfb["MinELev3"] = "155"
        tfb["MinELev4"] = "175"
        tfb["MinELev5"] = "195"
        tfb["EMax"] = "200"
        tfb["MaxELev1"] = "170"
        tfb["MaxELev2"] = "320"
        tfb["MaxELev3"] = "470"
        tfb["MaxELev4"] = "530"
        tfb["MaxELev5"] = "590"

    if "fireexplosion" in rows_by_name:
        fe = rows_by_name["fireexplosion"]
        fe["HitShift"] = "8"
        fe["EType"] = "fire"
        fe["EMin"] = "70"
        fe["MinELev1"] = "55"
        fe["MinELev2"] = "105"
        fe["MinELev3"] = "155"
        fe["MinELev4"] = "175"
        fe["MinELev5"] = "195"
        fe["EMax"] = "200"
        fe["MaxELev1"] = "170"
        fe["MaxELev2"] = "320"
        fe["MaxELev3"] = "470"
        fe["MaxELev4"] = "530"
        fe["MaxELev5"] = "590"

    if "trappoisonjavcloud" in rows_by_name:
        tpj = rows_by_name["trappoisonjavcloud"]
        tpj["EType"] = "pois"
        tpj["ELen"] = "150"  # 6 seconds (fast, urgent poison drain)
        tpj["EMin"] = "75"
        tpj["MinELev1"] = "55"
        tpj["MinELev2"] = "105"
        tpj["MinELev3"] = "155"
        tpj["MinELev4"] = "175"
        tpj["MinELev5"] = "195"
        tpj["EMax"] = "160"
        tpj["MaxELev1"] = "115"
        tpj["MaxELev2"] = "215"
        tpj["MaxELev3"] = "315"
        tpj["MaxELev4"] = "355"
        tpj["MaxELev5"] = "395"

    if "primepoisoncloud" in rows_by_name:
        ppc = rows_by_name["primepoisoncloud"]
        ppc["EType"] = "pois"
        ppc["ELen"] = "150"  # 6 seconds
        ppc["EMin"] = "75"
        ppc["MinELev1"] = "55"
        ppc["MinELev2"] = "105"
        ppc["MinELev3"] = "155"
        ppc["MinELev4"] = "175"
        ppc["MinELev5"] = "195"
        ppc["EMax"] = "160"
        ppc["MaxELev1"] = "115"
        ppc["MaxELev2"] = "215"
        ppc["MaxELev3"] = "315"
        ppc["MaxELev4"] = "355"
        ppc["MaxELev5"] = "395"

    for gas_name, gmin, gmax in (
        ("rancidgascloud", "240", "480"),
        ("chokinggascloud", "540", "1080"),
        ("stranglinggascloud", "960", "1920"),
    ):
        if gas_name in rows_by_name:
            gc = rows_by_name[gas_name]
            gc["EType"] = "pois"
            gc["ELen"] = "100"  # 4 seconds
            gc["EMin"] = gmin
            gc["EMax"] = gmax
            gc["MinELev1"] = "50"
            gc["MinELev2"] = "95"
            gc["MinELev3"] = "140"
            gc["MinELev4"] = "160"
            gc["MinELev5"] = "180"
            gc["MaxELev1"] = "100"
            gc["MaxELev2"] = "190"
            gc["MaxELev3"] = "280"
            gc["MaxELev4"] = "320"
            gc["MaxELev5"] = "360"

    # 4. Act Boss Missiles (Andariel Poison Spray & Poison Bolt — 1.45x base + progressive per-level scaling)
    for boss_ms in ("andarielspray", "andypoisonbolt"):
        if boss_ms in rows_by_name:
            bm = rows_by_name[boss_ms]
            for dcol in (
                "MinDamage", "MaxDamage", "MinLevDam1", "MinLevDam2", "MinLevDam3", "MinLevDam4", "MinLevDam5",
                "MaxLevDam1", "MaxLevDam2", "MaxLevDam3", "MaxLevDam4", "MaxLevDam5",
                "EMin", "EMax", "MinELev1", "MinELev2", "MinELev3", "MinELev4", "MinELev5",
                "MaxELev1", "MaxELev2", "MaxELev3", "MaxELev4", "MaxELev5",
            ):
                if bm.get(dcol):
                    bm[dcol] = scale_int(bm[dcol], 1.45)
            if bm.get("Vel"):
                bm["Vel"] = str(min(28, int(bm["Vel"]) + 3))
            if bm.get("MaxVel"):
                bm["MaxVel"] = str(min(28, int(bm["MaxVel"]) + 3))

    # 5. Barbarian Phase 1 Stamina Consumption & Sustain Missiles:
    #    - leapknockback (Id 346): Spawns grimwardsmallstop on landing to drain Stamina on Leap
    #    - leapattack (Id 685): Landing shockwave stun + spawns grimwardsmallstop to drain Stamina
    #    - grimwardsmallstop (Id 251): Invisible self-hit Stamina Drain pulse (Skill = Bar Stamina Drain)
    #    - grimwardlargestart (Id 255): Invisible self-hit Battle Trance Stamina Restore pulse (Skill = Battle Trance Pulse)
    #    - grimwardmediumstart (Id 252): Totem of the Ancients startup that spawns both grimwardmedium (Enemy Debuff Totem)
    #      and grimwardsmall (Friendly Proximity Stamina Emitter)
    #    - grimwardmedium (Id 253): Totem of the Ancients body (Range=300 [12s], pulses srvdofunc=30 every 6 frames)
    #    - grimwardsmall (Id 250): Stationary Totem Proximity Stamina Emitter (Range=300 [12s], pulses srvdofunc=22 every 10 frames)
    #    - grimwardlarge (Id 256): Radial Totem Proximity Stamina Wave (pSrvHitFunc=18, CollideFriend=1, Skill = Bar Totem Stamina Pulse)
    if "leapknockback" in rows_by_name:
        lpk = rows_by_name["leapknockback"]
        lpk["pCltDoFunc"] = "1"
        lpk["pSrvDoFunc"] = "1"
        lpk["Vel"] = "10"
        lpk["MaxVel"] = "10"
        lpk["Range"] = "4"
        lpk["InitSteps"] = "1"
        lpk["AnimLen"] = "4"
        lpk["AnimSpeed"] = "16"
        lpk["CollideType"] = "3"
        lpk["ClientCol"] = "1"
        lpk["LastCollide"] = ""
        lpk["NextHit"] = "1"
        lpk["NextDelay"] = "4"
        lpk["Size"] = "2"
        lpk["GetHit"] = "1"
        lpk["KnockBack"] = "100"
        lpk["ResultFlags"] = "9"
        lpk["NumDirections"] = "32"

    if "leapattack" in rows_by_name:
        lpa = rows_by_name["leapattack"]
        lpa["pCltHitFunc"] = ""
        lpa["pSrvDoFunc"] = "1"
        lpa["pSrvDmgFunc"] = "7"
        lpa["dParam1"] = "0"
        lpa["GetHit"] = "1"
        lpa["ResultFlags"] = "4"
        lpa["ProgOverlay"] = ""
        lpa["Skill"] = "Leap Attack"

    if "grimwardsmallstart" in rows_by_name:
        gwss = rows_by_name["grimwardsmallstart"]
        gwss["pCltDoFunc"] = "1"
        gwss["pCltHitFunc"] = ""
        gwss["pSrvDoFunc"] = "1"
        gwss["pSrvHitFunc"] = "38"
        gwss["sHitPar1"] = "0"
        gwss["sHitPar2"] = "0"
        gwss["cHitPar1"] = "0"
        gwss["cHitPar2"] = "0"
        gwss["Vel"] = "0"
        gwss["MaxVel"] = "0"
        gwss["Range"] = "1"
        gwss["CelFile"] = "null"
        gwss["AnimLen"] = "1"
        gwss["CollideType"] = ""
        gwss["CanDestroy"] = ""
        gwss["LocalBlood"] = ""
        gwss["NumDirections"] = "32"
        gwss["Skill"] = "Leap"
        gwss["AlwaysExplode"] = "1"
        gwss["Explosion"] = "1"
        gwss["HitSubMissile1"] = "leapknockback"
        gwss["CltHitSubMissile1"] = ""

    if "warcry" in rows_by_name:
        wc_ms = rows_by_name["warcry"]
        wc_ms["pSrvDoFunc"] = "2"
        wc_ms["SrvCalc1"] = "1"
        wc_ms["SubMissile1"] = "grimwardsmall"

    if "grimwardsmall" in rows_by_name:
        gws = rows_by_name["grimwardsmall"]
        gws["pCltDoFunc"] = "1"
        gws["pCltHitFunc"] = ""
        gws["pSrvDoFunc"] = "1"
        gws["pSrvHitFunc"] = "21"
        gws["Param1"] = ""
        gws["Param2"] = ""
        gws["Vel"] = "0"
        gws["MaxVel"] = "0"
        gws["Range"] = "2"
        gws["CelFile"] = "null"
        gws["AnimLen"] = "1"
        gws["CollideType"] = "3"
        gws["LastCollide"] = "1"
        gws["NextHit"] = "1"
        gws["NextDelay"] = "4"
        gws["Size"] = "2"
        gws["NumDirections"] = "1"
        gws["Skill"] = "War Cry"
        gws["AlwaysExplode"] = ""
        gws["CltHitSubMissile1"] = ""

    if "grimwardsmallstop" in rows_by_name:
        ms_drain = rows_by_name["grimwardsmallstop"]
        ms_drain["pCltDoFunc"] = "1"
        ms_drain["pSrvDoFunc"] = "14"
        ms_drain["pSrvHitFunc"] = "27"
        ms_drain["Param1"] = "1"
        ms_drain["Param2"] = "68"
        ms_drain["Vel"] = "0"
        ms_drain["MaxVel"] = "0"
        ms_drain["Range"] = "2"
        ms_drain["InitSteps"] = "0"
        ms_drain["CelFile"] = "null"
        ms_drain["AnimLen"] = "1"
        ms_drain["CollideType"] = ""
        ms_drain["CollideKill"] = ""
        ms_drain["CollideFriend"] = ""
        ms_drain["LastCollide"] = ""
        ms_drain["NextHit"] = ""
        ms_drain["Size"] = "1"
        ms_drain["HitShift"] = "8"
        ms_drain["NumDirections"] = "1"
        ms_drain["Skill"] = "Battle Trance Pulse"
        ms_drain["CanDestroy"] = ""
        ms_drain["AlwaysExplode"] = "1"
        ms_drain["Explosion"] = ""

    if "grimwardlargestart" in rows_by_name:
        ms_trance = rows_by_name["grimwardlargestart"]
        ms_trance["pCltDoFunc"] = "1"
        ms_trance["pCltHitFunc"] = ""
        ms_trance["pSrvDoFunc"] = "1"
        ms_trance["pSrvHitFunc"] = "26"
        ms_trance["sHitPar1"] = "2"
        ms_trance["cHitPar1"] = "2"
        ms_trance["Param1"] = ""
        ms_trance["Param2"] = ""
        ms_trance["Vel"] = "18"
        ms_trance["MaxVel"] = "18"
        ms_trance["Accel"] = ""
        ms_trance["Range"] = "1"
        ms_trance["InitSteps"] = "0"
        ms_trance["CelFile"] = "null"
        ms_trance["AnimLen"] = "1"
        ms_trance["CollideType"] = ""
        ms_trance["CollideKill"] = ""
        ms_trance["CollideFriend"] = ""
        ms_trance["LastCollide"] = ""
        ms_trance["NextHit"] = ""
        ms_trance["Size"] = "1"
        ms_trance["NumDirections"] = "16"
        ms_trance["Skill"] = "Battle Trance Pulse"
        ms_trance["HitSubMissile1"] = "grimwardlarge"
        ms_trance["HitSubMissile2"] = "grimwardsmallstop"
        ms_trance["CltHitSubMissile1"] = ""
        ms_trance["CanDestroy"] = "1"
        ms_trance["AlwaysExplode"] = "1"

    if "grimwardmediumstart" in rows_by_name:
        gwms = rows_by_name["grimwardmediumstart"]
        gwms["pSrvDoFunc"] = "1"
        gwms["pSrvHitFunc"] = "26"
        gwms["Range"] = "8"
        gwms["HitSubMissile1"] = "grimwardmedium"
        gwms["CltHitSubMissile1"] = "grimwardmedium"

    if "grimwardmedium" in rows_by_name:
        gwm = rows_by_name["grimwardmedium"]
        gwm["pSrvDoFunc"] = "14"
        gwm["Param1"] = "6"
        gwm["Param2"] = "30"
        gwm["Range"] = "250"
        gwm["Skill"] = "Grim Ward"

    if "grimwardlarge" in rows_by_name:
        gwl = rows_by_name["grimwardlarge"]
        gwl["pCltDoFunc"] = "1"
        gwl["pCltHitFunc"] = ""
        gwl["pSrvDoFunc"] = "14"
        gwl["pSrvHitFunc"] = "27"
        gwl["Param1"] = "1"
        gwl["Param2"] = "18"
        gwl["Vel"] = "0"
        gwl["MaxVel"] = "0"
        gwl["Accel"] = ""
        gwl["Range"] = "2"
        gwl["InitSteps"] = "0"
        gwl["LoopAnim"] = "1"
        gwl["CelFile"] = "null"
        gwl["animrate"] = "1024"
        gwl["AnimLen"] = "1"
        gwl["AnimSpeed"] = "16"
        gwl["CollideType"] = ""
        gwl["CollideFriend"] = ""
        gwl["LastCollide"] = ""
        gwl["NextHit"] = ""
        gwl["NextDelay"] = ""
        gwl["Size"] = "1"
        gwl["Trans"] = ""
        gwl["NumDirections"] = "4"
        gwl["Skill"] = "Battle Trance Pulse"
        gwl["CanDestroy"] = "1"
        gwl["AlwaysExplode"] = "1"
        gwl["Explosion"] = "1"
        gwl["CltHitSubMissile1"] = ""

    # Assassin Trap Charge Consumption Timer (bladefury1 -> bladefury2 after 8 frames)
    if "bladefury1" in rows_by_name:
        bf1 = rows_by_name["bladefury1"]
        bf1["pCltDoFunc"] = "1"
        bf1["pCltHitFunc"] = ""
        bf1["pSrvDoFunc"] = "1"
        bf1["pSrvHitFunc"] = "26"
        bf1["sHitPar1"] = "1"
        bf1["cHitPar1"] = "1"
        bf1["Vel"] = "0"
        bf1["MaxVel"] = "0"
        bf1["Range"] = "1"
        bf1["InitSteps"] = "0"
        bf1["CelFile"] = "null"
        bf1["AnimLen"] = "1"
        bf1["CollideType"] = ""
        bf1["CollideKill"] = ""
        bf1["ClientCol"] = ""
        bf1["Size"] = "1"
        bf1["ToHit"] = ""
        bf1["AlwaysExplode"] = "1"
        bf1["Explosion"] = "1"
        bf1["CanDestroy"] = "1"
        bf1["NumDirections"] = "32"
        bf1["Skill"] = "Ass Trap Charge Consume"
        bf1["HitSubMissile1"] = "bladefury2"
        bf1["CltHitSubMissile1"] = ""

    if "bladefury2" in rows_by_name:
        bf2 = rows_by_name["bladefury2"]
        bf2["pCltDoFunc"] = "1"
        bf2["pCltHitFunc"] = ""
        bf2["pSrvDoFunc"] = "1"
        bf2["pSrvHitFunc"] = "18"
        bf2["Param1"] = ""
        bf2["Param2"] = ""
        bf2["Vel"] = "30"
        bf2["MaxVel"] = "30"
        bf2["Range"] = "25"
        bf2["InitSteps"] = "1"
        bf2["LoopAnim"] = "0"
        bf2["CelFile"] = "BAYellShockWave01"
        bf2["AnimLen"] = "15"
        bf2["CollideType"] = "3"
        bf2["CollideFriend"] = "1"
        bf2["LastCollide"] = "1"
        bf2["NextHit"] = "1"
        bf2["NextDelay"] = "4"
        bf2["CollideKill"] = ""
        bf2["ClientCol"] = ""
        bf2["Size"] = "2"
        bf2["ToHit"] = ""
        bf2["AlwaysExplode"] = ""
        bf2["Explosion"] = ""
        bf2["CanDestroy"] = ""
        bf2["NumDirections"] = "32"
        bf2["Skill"] = "Ass Trap Charge Consume"
        bf2["HitSubMissile1"] = ""
        bf2["CltHitSubMissile1"] = ""

    # Step 1: Wake of Fire Sentry (Fists of Fire 1/2/3 Charge Tier Upgrades via clean straight-line Fireballs)
    wof_c = "skill('Ass Trap Charge Consume'.blvl)"
    fof_m = "skill('Fists of Fire'.blvl)"
    if "vampirefireball" in rows_by_name:
        vfb_ms = rows_by_name["vampirefireball"]
        vfb_ms["pCltDoFunc"] = "1"
        vfb_ms["pCltHitFunc"] = "1"
        vfb_ms["pSrvDoFunc"] = "1"
        vfb_ms["pSrvHitFunc"] = "38"
        vfb_ms["pSrvDmgFunc"] = ""
        vfb_ms["dParam1"] = ""
        vfb_ms["SrvCalc1"] = ""
        vfb_ms["CltCalc1"] = ""
        vfb_ms["SubMissile1"] = ""
        vfb_ms["CltSubMissile1"] = ""
        vfb_ms["sHitPar1"] = "6"
        vfb_ms["sHitPar2"] = "0"
        vfb_ms["cHitPar1"] = "3"
        vfb_ms["cHitPar2"] = "1"
        vfb_ms["Vel"] = "10"
        vfb_ms["VelLev"] = "8"
        vfb_ms["MaxVel"] = "30"
        vfb_ms["Range"] = f"16 + (({wof_c} >= 2) ? (12 + {fof_m}) : 0)"
        vfb_ms["AlwaysExplode"] = "1"
        vfb_ms["MissileSkill"] = ""
        vfb_ms["Skill"] = ""
        vfb_ms["ResultFlags"] = "4"
        vfb_ms["HitFlags"] = "2"
        vfb_ms["HitShift"] = "8"
        vfb_ms["MinDamage"] = ""
        vfb_ms["MaxDamage"] = ""
        vfb_ms["EType"] = ""
        vfb_ms["EMin"] = ""
        vfb_ms["MinELev1"] = ""
        vfb_ms["MinELev2"] = ""
        vfb_ms["MinELev3"] = ""
        vfb_ms["MinELev4"] = ""
        vfb_ms["MinELev5"] = ""
        vfb_ms["EMax"] = ""
        vfb_ms["MaxELev1"] = ""
        vfb_ms["MaxELev2"] = ""
        vfb_ms["MaxELev3"] = ""
        vfb_ms["MaxELev4"] = ""
        vfb_ms["MaxELev5"] = ""
        vfb_ms["EDmgSymPerCalc"] = ""
        vfb_ms["ProgOverlay"] = ""
        vfb_ms["TravelSound"] = "sorceress_fireball_1"
        vfb_ms["HitSound"] = "sorceress_fireball_impact_1"
        vfb_ms["ExplosionMissile"] = "explodingarrowexp"
        vfb_ms["HitSubMissile1"] = "sucfireball"
        vfb_ms["CltHitSubMissile1"] = "fireexplosion2"

    if "sucfireball" in rows_by_name:
        sfb_ms = rows_by_name["sucfireball"]
        sfb_ms["pCltDoFunc"] = "1"
        sfb_ms["pCltHitFunc"] = ""
        sfb_ms["pSrvDoFunc"] = "2"
        sfb_ms["SrvCalc1"] = f"({wof_c} >= 3) ? 1 : 0"
        sfb_ms["pSrvHitFunc"] = ""
        sfb_ms["pSrvDmgFunc"] = ""
        sfb_ms["dParam1"] = ""
        sfb_ms["Param1"] = ""
        sfb_ms["CltParam1"] = ""
        sfb_ms["sHitPar1"] = ""
        sfb_ms["sHitPar2"] = ""
        sfb_ms["Vel"] = "12"
        sfb_ms["MaxVel"] = "12"
        sfb_ms["Range"] = f"4 + (({wof_c} >= 2) ? (1 + {fof_m} / 10) : 0)"
        sfb_ms["InitSteps"] = "1"
        sfb_ms["CelFile"] = "null"
        sfb_ms["AnimLen"] = "4"
        sfb_ms["AnimSpeed"] = "16"
        sfb_ms["CollideType"] = "3"
        sfb_ms["CollideKill"] = ""
        sfb_ms["LastCollide"] = "1"
        sfb_ms["ClientCol"] = "1"
        sfb_ms["NextHit"] = "1"
        sfb_ms["NextDelay"] = "4"
        sfb_ms["Size"] = "2"
        sfb_ms["AlwaysExplode"] = ""
        sfb_ms["GetHit"] = "1"
        sfb_ms["Trans"] = "1"
        sfb_ms["Skill"] = ""
        sfb_ms["ResultFlags"] = "4"
        sfb_ms["HitFlags"] = "2"
        sfb_ms["HitShift"] = "8"
        sfb_ms["EType"] = "fire"
        sfb_ms["EMin"] = "14"
        sfb_ms["MinELev1"] = "0"
        sfb_ms["MinELev2"] = "0"
        sfb_ms["MinELev3"] = "0"
        sfb_ms["MinELev4"] = "0"
        sfb_ms["MinELev5"] = "0"
        sfb_ms["EMax"] = "24"
        sfb_ms["MaxELev1"] = "0"
        sfb_ms["MaxELev2"] = "0"
        sfb_ms["MaxELev3"] = "0"
        sfb_ms["MaxELev4"] = "0"
        sfb_ms["MaxELev5"] = "0"
        sfb_ms["EDmgSymPerCalc"] = "(skill('Wake Of Destruction Sentry'.clc2) * skill('Wake Of Destruction Sentry'.clc3)) / 100 - 100"
        sfb_ms["NumDirections"] = "32"
        sfb_ms["SubMissile1"] = "sucfireballexplode"
        sfb_ms["HitSubMissile1"] = ""
        sfb_ms["CltHitSubMissile1"] = ""
        sfb_ms["ProgOverlay"] = ""

    if "sucfireballexplode" in rows_by_name:
        sfe_ms = rows_by_name["sucfireballexplode"]
        sfe_ms["pCltDoFunc"] = "1"
        sfe_ms["pSrvDoFunc"] = "1"
        sfe_ms["pSrvHitFunc"] = ""
        sfe_ms["pSrvDmgFunc"] = "7"
        sfe_ms["dParam1"] = "10"
        sfe_ms["sHitPar1"] = ""
        sfe_ms["Vel"] = "12"
        sfe_ms["MaxVel"] = "12"
        sfe_ms["Range"] = f"({wof_c} >= 3) ? 3 : 0"
        sfe_ms["InitSteps"] = "0"
        sfe_ms["CelFile"] = "null"
        sfe_ms["AnimLen"] = "4"
        sfe_ms["AnimSpeed"] = "16"
        sfe_ms["RandStart"] = ""
        sfe_ms["CollideType"] = "3"
        sfe_ms["CollideKill"] = "1"
        sfe_ms["LastCollide"] = "1"
        sfe_ms["ClientCol"] = "1"
        sfe_ms["NextHit"] = ""
        sfe_ms["NextDelay"] = ""
        sfe_ms["Size"] = "2"
        sfe_ms["AlwaysExplode"] = ""
        sfe_ms["Explosion"] = ""
        sfe_ms["NoMultiShot"] = ""
        sfe_ms["GetHit"] = "1"
        sfe_ms["Trans"] = "1"
        sfe_ms["MissileSkill"] = ""
        sfe_ms["Skill"] = ""
        sfe_ms["ResultFlags"] = "4"
        sfe_ms["HitFlags"] = "2"
        sfe_ms["HitShift"] = "8"
        sfe_ms["MinDamage"] = "1"
        sfe_ms["MaxDamage"] = "2"
        sfe_ms["EType"] = ""
        sfe_ms["EMin"] = ""
        sfe_ms["EMax"] = ""
        sfe_ms["EDmgSymPerCalc"] = ""
        sfe_ms["NumDirections"] = "32"
        sfe_ms["ProgOverlay"] = ""

    # Fists of Fire (Flamestrike) Finishing Move Release Missiles (1 distinct effect per orb tier,
    # with smooth Normal/Nightmare scaling across ELev1..3 and endgame acceleration in ELev4..5):
    # - Charge 1 Finisher Release: fistsoffireexplode (Instant AoE Fire Explosion)
    # - Charge 2 Finisher Release: fistsoffirefirewall (Wide AoE Burning Ground carpet)
    # - Charge 3 Finisher Release: royalstrikemeteorcenter -> royalstrikemeteor + royalstrikemeteorfire (Crashing Meteor)
    fof_syn_expr = "12*skill('Wake of Fire Sentry'.blvl) + 6*skill('Blades of Ice'.blvl) + 6*skill('Claws of Thunder'.blvl)"
    if "fistsoffireexplode" in rows_by_name:
        ffe = rows_by_name["fistsoffireexplode"]
        ffe["CollideType"] = "3"
        ffe["Collision"] = "1"
        ffe["CollideKill"] = ""
        ffe["LastCollide"] = "1"
        ffe["NextHit"] = "1"
        ffe["NextDelay"] = "25"
        ffe["Size"] = "3"
        ffe["HitShift"] = "8"
        ffe["ApplyMastery"] = "1"
        ffe["EType"] = "fire"
        ffe["EMin"] = "8"
        ffe["MinELev1"] = "2"
        ffe["MinELev2"] = "3"
        ffe["MinELev3"] = "5"
        ffe["MinELev4"] = "14"
        ffe["MinELev5"] = "24"
        ffe["EMax"] = "16"
        ffe["MaxELev1"] = "4"
        ffe["MaxELev2"] = "6"
        ffe["MaxELev3"] = "10"
        ffe["MaxELev4"] = "28"
        ffe["MaxELev5"] = "48"
        ffe["EDmgSymPerCalc"] = fof_syn_expr
    if "fistsoffirefirewall" in rows_by_name:
        ffw = rows_by_name["fistsoffirefirewall"]
        ffw["Range"] = "85"
        ffw["Size"] = "3"
        ffw["EMin"] = "5"
        ffw["MinELev1"] = "1"
        ffw["MinELev2"] = "2"
        ffw["MinELev3"] = "3"
        ffw["MinELev4"] = "9"
        ffw["MinELev5"] = "15"
        ffw["EMax"] = "10"
        ffw["MaxELev1"] = "2"
        ffw["MaxELev2"] = "4"
        ffw["MaxELev3"] = "6"
        ffw["MaxELev4"] = "18"
        ffw["MaxELev5"] = "30"
        ffw["EDmgSymPerCalc"] = fof_syn_expr
    if "royalstrikemeteorcenter" in rows_by_name:
        rsmc = rows_by_name["royalstrikemeteorcenter"]
        rsmc["Range"] = "30"
        rsmc["CltParam1"] = "29"
        rsmc["CltParam2"] = "50"
        rsmc["CltParam3"] = "30"
    if "royalstrikemeteor" in rows_by_name:
        rsm = rows_by_name["royalstrikemeteor"]
        rsm["sHitPar1"] = "9"
        rsm["EMin"] = "24"
        rsm["MinELev1"] = "6"
        rsm["MinELev2"] = "9"
        rsm["MinELev3"] = "15"
        rsm["MinELev4"] = "42"
        rsm["MinELev5"] = "72"
        rsm["EMax"] = "48"
        rsm["MaxELev1"] = "12"
        rsm["MaxELev2"] = "18"
        rsm["MaxELev3"] = "30"
        rsm["MaxELev4"] = "84"
        rsm["MaxELev5"] = "144"
        rsm["EDmgSymPerCalc"] = fof_syn_expr
    if "royalstrikemeteorfire" in rows_by_name:
        rsmf = rows_by_name["royalstrikemeteorfire"]
        rsmf["Range"] = "75"
        rsmf["Size"] = "3"
        rsmf["EMin"] = "3"
        rsmf["MinELev1"] = "1"
        rsmf["MinELev2"] = "1"
        rsmf["MinELev3"] = "2"
        rsmf["MinELev4"] = "5"
        rsmf["MinELev5"] = "8"
        rsmf["EMax"] = "6"
        rsmf["MaxELev1"] = "2"
        rsmf["MaxELev2"] = "2"
        rsmf["MaxELev3"] = "4"
        rsmf["MaxELev4"] = "10"
        rsmf["MaxELev5"] = "16"
        rsmf["EDmgSymPerCalc"] = fof_syn_expr

    # Step 2: Shrapnel Sentry (Tiger Strike 1/2/3 Charge Tier Upgrades via straight-line Blade Fury shuriken turret)
    # Note: Use 'bladefragment3' (not 'bladefury3', which had CelFile='null' in vanilla and therefore has no 3D HD model in D2R's missiles.json).
    ss_c = "skill('Ass Trap Charge Consume'.blvl)"
    ts_m = "skill('Tiger Strike'.blvl)"
    if "bladefragment3" in rows_by_name:
        bf3_ms = rows_by_name["bladefragment3"]
        bf3_ms["pCltDoFunc"] = "1"
        bf3_ms["pCltHitFunc"] = ""
        bf3_ms["pSrvDoFunc"] = "1"
        bf3_ms["pSrvHitFunc"] = ""
        bf3_ms["pSrvDmgFunc"] = ""
        bf3_ms["SrvCalc1"] = ""
        bf3_ms["dParam1"] = ""
        bf3_ms["sHitPar1"] = ""
        bf3_ms["sHitPar2"] = ""
        bf3_ms["cHitPar1"] = ""
        bf3_ms["cHitPar2"] = ""
        bf3_ms["cHitPar3"] = ""
        bf3_ms["Vel"] = "16"
        bf3_ms["VelLev"] = "8"
        bf3_ms["MaxVel"] = "32"
        bf3_ms["Range"] = f"18 + (({ss_c} >= 2) ? (14 + {ts_m}) : 0)"
        bf3_ms["InitSteps"] = "1"
        bf3_ms["Activate"] = "1"
        bf3_ms["LoopAnim"] = "1"
        bf3_ms["CelFile"] = "Expansion\\bladefury_C"
        bf3_ms["animrate"] = "1024"
        bf3_ms["AnimLen"] = "7"
        bf3_ms["AnimSpeed"] = "32"
        bf3_ms["CollideType"] = "3"
        bf3_ms["CollideKill"] = "1"
        bf3_ms["LastCollide"] = "1"
        bf3_ms["ClientCol"] = "1"
        bf3_ms["NextHit"] = "1"
        bf3_ms["NextDelay"] = "4"
        bf3_ms["Size"] = "1"
        bf3_ms["ToHit"] = ""
        bf3_ms["AlwaysExplode"] = ""
        bf3_ms["Explosion"] = ""
        bf3_ms["CanSlow"] = "1"
        bf3_ms["ReturnFire"] = "1"
        bf3_ms["GetHit"] = "1"
        bf3_ms["Pierce"] = ""
        bf3_ms["Skill"] = ""
        bf3_ms["ResultFlags"] = "4"
        bf3_ms["HitFlags"] = "2"
        bf3_ms["HitShift"] = "8"
        bf3_ms["SrcDamage"] = "128"
        bf3_ms["Half2HSrc"] = ""
        bf3_ms["MinDamage"] = "10"
        bf3_ms["MinLevDam1"] = "0"
        bf3_ms["MinLevDam2"] = "0"
        bf3_ms["MinLevDam3"] = "0"
        bf3_ms["MinLevDam4"] = "0"
        bf3_ms["MinLevDam5"] = "0"
        bf3_ms["MaxDamage"] = "18"
        bf3_ms["MaxLevDam1"] = "0"
        bf3_ms["MaxLevDam2"] = "0"
        bf3_ms["MaxLevDam3"] = "0"
        bf3_ms["MaxLevDam4"] = "0"
        bf3_ms["MaxLevDam5"] = "0"
        bf3_ms["DmgSymPerCalc"] = "(skill('mon inferno sentry'.clc2) * skill('mon inferno sentry'.clc3)) / 100 - 100"
        bf3_ms["EType"] = ""
        bf3_ms["EMin"] = ""
        bf3_ms["EMax"] = ""
        bf3_ms["NumDirections"] = "1"
        bf3_ms["TravelSound"] = "assassin_bladefury_throw_1"
        bf3_ms["HitSound"] = "assassin_bladefury_hit"
        bf3_ms["ExplosionMissile"] = ""
        bf3_ms["SubMissile1"] = ""
        bf3_ms["HitSubMissile1"] = ""
        bf3_ms["CltHitSubMissile1"] = ""
        bf3_ms["ProgOverlay"] = ""

    # Tiger Strike Finishing Move Release Missiles (360-degree Expanding Physical Shockwave Ring):
    # All 3 charge tiers use srvprgfunc=41 / cltprgfunc=15 (prgcalc=36) rather than srvprgfunc=36 (Nova),
    # because srvprgfunc=36 hardcodes a full-screen ~20-subtile Nova radius in C++ while srvprgfunc=41
    # strictly obeys missiles.txt Vel and Range!
    # At Vel=8 (1.0 sub-tile/frame) and plain integer Range=7, the shockwave travels 7.0 sub-tiles
    # (~4.6 yards, right in the middle between 3.75 and 11.25 sub-tiles) while completing its
    # 7-frame expansion_shockwave animation (AnimSpeed=16 -> 7 frames) right as it expires.
    ts_c123_syn = "skill('Tiger Strike'.clc6)"
    ts_ring_specs = [
        # (m_name, vel, rng, size, res_flags, kb, syn_calc, min_d, min1, min2, min3, min4, min5, max_d, max1, max2, max3, max4, max5)
        ("inferno sentry 1",          "8", "7", "2", "4",  "",    ts_c123_syn, "4", "1", "2", "3", "7", "12", "8", "2", "3", "5", "12", "20"),
        ("inferno sentry 2",          "8", "7", "2", "4",  "",    ts_c123_syn, "4", "1", "2", "3", "7", "12", "8", "2", "3", "5", "12", "20"),
        ("progressive radius damage", "8", "7", "2", "13", "100", ts_c123_syn, "4", "1", "2", "3", "7", "12", "8", "2", "3", "5", "12", "20"),
    ]
    for (
        m_name, vel, rng, sz, rflags, kb, syn_calc,
        mn0, mn1, mn2, mn3, mn4, mn5,
        mx0, mx1, mx2, mx3, mx4, mx5,
    ) in ts_ring_specs:
        if m_name in rows_by_name:
            trm = rows_by_name[m_name]
            trm["pCltDoFunc"] = "1"
            trm["pCltHitFunc"] = ""
            trm["pSrvDoFunc"] = "1"
            trm["pSrvHitFunc"] = ""
            trm["pSrvDmgFunc"] = ""
            trm["Vel"] = vel
            trm["MaxVel"] = vel
            trm["VelLev"] = ""
            trm["Accel"] = ""
            trm["Range"] = rng
            trm["Light"] = ""
            trm["Red"] = "255"
            trm["Green"] = "255"
            trm["Blue"] = "255"
            trm["InitSteps"] = "0"
            trm["Activate"] = "0"
            trm["LoopAnim"] = "0"
            trm["CelFile"] = "expansion\\shockwave"
            trm["animrate"] = "1024"
            trm["AnimLen"] = "7"
            trm["AnimSpeed"] = "16"
            trm["CollideType"] = "3"
            trm["CollideKill"] = ""
            trm["LastCollide"] = "1"
            trm["Collision"] = "1"
            trm["ClientCol"] = "1"
            trm["NextHit"] = "1"
            trm["NextDelay"] = "30"
            trm["Size"] = sz
            trm["CanSlow"] = ""
            trm["ReturnFire"] = "1"
            trm["GetHit"] = "1"
            trm["KnockBack"] = kb
            trm["Trans"] = "1"
            trm["Pierce"] = "1"
            trm["Skill"] = ""
            trm["ResultFlags"] = rflags
            trm["HitFlags"] = "2"
            trm["HitShift"] = "8"
            trm["SrcDamage"] = ""
            trm["MinDamage"] = mn0
            trm["MinLevDam1"] = mn1
            trm["MinLevDam2"] = mn2
            trm["MinLevDam3"] = mn3
            trm["MinLevDam4"] = mn4
            trm["MinLevDam5"] = mn5
            trm["MaxDamage"] = mx0
            trm["MaxLevDam1"] = mx1
            trm["MaxLevDam2"] = mx2
            trm["MaxLevDam3"] = mx3
            trm["MaxLevDam4"] = mx4
            trm["MaxLevDam5"] = mx5
            trm["DmgSymPerCalc"] = syn_calc
            trm["EType"] = ""
            trm["EMin"] = ""
            trm["EMax"] = ""
            trm["EDmgSymPerCalc"] = ""
            trm["DamageRate"] = ""
            trm["NumDirections"] = "32"
            trm["TravelSound"] = "druid_shockwave"
            trm["HitSound"] = "assassin_bladefury_hit"
            trm["ProgOverlay"] = "doubledamage1"
            trm["SubMissile1"] = ""

    # Step 3: Cobra Strike (progressive_steal) Finishing Move Soul-Hex Wave + Soul Siphon Sentry (Charged Bolt Sentry, Id 261)
    # 1. Cobra Strike 1/2/3 Orb Release Missiles (unholybolt2..4 -> undeadmissile2..4):
    #    - 7.0-sub-tile (4.6-yard) translucent Soul-Hex Wave (b_a_yell_shock_wave_01)
    #    - Plays the growing green Soul-Drain swirl (cobrastrike1 / cobrastrike2 / cobrastrike3) on every monster hit
    #    - Applies Ass Cobra Hex 1 / 2 / 3 (Monster Defense Shred: -1x / -2x / -3x Defense) via pSrvHitFunc=21 submissile
    cs_wave_specs = [
        ("unholybolt2", "undeadmissile2", "cobrastrike1", "Ass Cobra Hex 1"),
        ("unholybolt3", "undeadmissile3", "cobrastrike2", "Ass Cobra Hex 2"),
        ("unholybolt4", "undeadmissile4", "cobrastrike3", "Ass Cobra Hex 3"),
    ]
    for wave_m, sub_m, prog_ov, hex_sk in cs_wave_specs:
        if wave_m in rows_by_name:
            wm = rows_by_name[wave_m]
            wm["pCltDoFunc"] = "1"
            wm["pCltHitFunc"] = "10"
            wm["pSrvDoFunc"] = "2"
            wm["SrvCalc1"] = "1"
            wm["pSrvHitFunc"] = ""
            wm["pSrvDmgFunc"] = ""
            wm["Vel"] = "8"
            wm["MaxVel"] = "8"
            wm["VelLev"] = ""
            wm["Accel"] = ""
            wm["Range"] = "7"
            wm["Light"] = ""
            wm["Red"] = ""
            wm["Green"] = ""
            wm["Blue"] = ""
            wm["InitSteps"] = "1"
            wm["Activate"] = "0"
            wm["LoopAnim"] = "0"
            wm["CelFile"] = "null"
            wm["animrate"] = "1024"
            wm["AnimLen"] = "7"
            wm["AnimSpeed"] = "16"
            wm["CollideType"] = "3"
            wm["CollideKill"] = ""
            wm["LastCollide"] = "1"
            wm["Collision"] = "1"
            wm["ClientCol"] = "1"
            wm["NextHit"] = "1"
            wm["NextDelay"] = "25"
            wm["Size"] = "2"
            wm["CanSlow"] = ""
            wm["ReturnFire"] = ""
            wm["GetHit"] = ""
            wm["KnockBack"] = ""
            wm["Trans"] = "1"
            wm["Pierce"] = "1"
            wm["Skill"] = ""
            wm["ResultFlags"] = "4"
            wm["HitFlags"] = "2"
            wm["HitShift"] = "8"
            wm["SrcDamage"] = ""
            wm["MinDamage"] = "1"
            wm["MaxDamage"] = "2"
            wm["EType"] = ""
            wm["EMin"] = ""
            wm["MinELev1"] = ""
            wm["MinELev2"] = ""
            wm["MinELev3"] = ""
            wm["MinELev4"] = ""
            wm["MinELev5"] = ""
            wm["EMax"] = ""
            wm["MaxELev1"] = ""
            wm["MaxELev2"] = ""
            wm["MaxELev3"] = ""
            wm["MaxELev4"] = ""
            wm["MaxELev5"] = ""
            wm["NumDirections"] = "32"
            wm["TravelSound"] = "assassin_chargeup_cobra_1"
            wm["HitSound"] = ""
            wm["ProgOverlay"] = prog_ov
            wm["SubMissile1"] = sub_m
        if sub_m in rows_by_name:
            sm = rows_by_name[sub_m]
            sm["pCltDoFunc"] = "1"
            sm["pCltHitFunc"] = ""
            sm["pSrvDoFunc"] = "1"
            sm["pSrvHitFunc"] = "21"
            sm["pSrvDmgFunc"] = ""
            sm["Param1"] = ""
            sm["Param2"] = ""
            sm["Vel"] = "0"
            sm["MaxVel"] = "0"
            sm["Range"] = "2"
            sm["CelFile"] = "null"
            sm["AnimLen"] = "1"
            sm["AnimSpeed"] = "16"
            sm["CollideType"] = "3"
            sm["CollideKill"] = ""
            sm["LastCollide"] = "1"
            sm["NextHit"] = "1"
            sm["NextDelay"] = "4"
            sm["Size"] = "2"
            sm["NumDirections"] = "1"
            sm["Skill"] = hex_sk
            sm["EType"] = ""
            sm["EMin"] = ""
            sm["MinELev1"] = ""
            sm["MinELev2"] = ""
            sm["MinELev3"] = ""
            sm["MinELev4"] = ""
            sm["MinELev5"] = ""
            sm["EMax"] = ""
            sm["MaxELev1"] = ""
            sm["MaxELev2"] = ""
            sm["MaxELev3"] = ""
            sm["MaxELev4"] = ""
            sm["MaxELev5"] = ""
            sm["AlwaysExplode"] = ""
            sm["ExplosionMissile"] = ""
            sm["SubMissile1"] = ""
            sm["HitSubMissile1"] = ""
            sm["CltHitSubMissile1"] = ""

    # 2. Soul Siphon Sentry (sentrychargedbolt -> sentryspikeinair -> sentryspikeonground):
    #    - Fires straight-line piercing Black Unholy Bolts (unholy_bolt in missiles.json) with pSrvDoFunc=2, pCltDoFunc=1
    #    - sentrychargedbolt directly deals the Magic damage (EType=mag, 42-66 base) and pierces through all enemies (CollideKill="", LastCollide="1", Pierce="1")
    #    - Charge 1: +Shots (handled in BoltSentry calc4)
    #    - Charge 2: BoltSentry sumsk1calc sets lvl=2 (Vel=16 -> MaxVel=24 via VelLev=8) & +Range (30 -> 46+blvl frames)
    #    - Charge 3: BoltSentry sumsk1calc sets lvl=10; sentryspikeinair (pSrvDoFunc=1, pSrvHitFunc=38, sHitPar1=-4, sHitPar2=1)
    #      spawns (-4 + lvl*1) = 6 sentryspikeonground (Life Tap) missiles ONLY when lvl >= 5 (3 charges), and 0 when lvl <= 2 (0-2 charges)!
    cs_c = "skill('Ass Trap Charge Consume'.blvl)"
    cs_m = "skill('Cobra Strike'.blvl)"
    if "sentrychargedbolt" in rows_by_name:
        scb = rows_by_name["sentrychargedbolt"]
        scb["pCltDoFunc"] = "1"
        scb["pCltHitFunc"] = ""
        scb["pSrvDoFunc"] = "2"
        scb["SrvCalc1"] = "(lvl >= 3) ? 1 : 999"
        scb["pSrvHitFunc"] = ""
        scb["pSrvDmgFunc"] = ""
        scb["Param1"] = ""
        scb["Param2"] = ""
        scb["CltParam1"] = ""
        scb["sHitPar1"] = ""
        scb["sHitPar2"] = ""
        scb["Vel"] = "16"
        scb["VelLev"] = "8"
        scb["MaxVel"] = "24"
        scb["Range"] = f"30 + ((lvl >= 2) ? (16 + {cs_m}) : 0)"
        scb["Light"] = "5"
        scb["Flicker"] = ""
        scb["Red"] = "0"
        scb["Green"] = "0"
        scb["Blue"] = "0"
        scb["InitSteps"] = "1"
        scb["Activate"] = "0"
        scb["LoopAnim"] = "0"
        scb["CelFile"] = "UnholyBolt"
        scb["animrate"] = "1024"
        scb["AnimLen"] = "64"
        scb["AnimSpeed"] = "16"
        scb["SubLoop"] = ""
        scb["SubStart"] = ""
        scb["SubStop"] = ""
        scb["CollideType"] = "3"
        scb["CollideKill"] = ""
        scb["LastCollide"] = "1"
        scb["ClientCol"] = "1"
        scb["NextHit"] = "1"
        scb["NextDelay"] = "8"
        scb["Size"] = "2"
        scb["AlwaysExplode"] = ""
        scb["CanSlow"] = "1"
        scb["ReturnFire"] = "1"
        scb["GetHit"] = "1"
        scb["Trans"] = "2"
        scb["Pierce"] = "1"
        scb["Skill"] = ""
        scb["ResultFlags"] = "4"
        scb["HitFlags"] = "2"
        scb["HitShift"] = "8"
        scb["HitClass"] = ""
        scb["EType"] = "mag"
        scb["EMin"] = "32"
        scb["MinELev1"] = "0"
        scb["MinELev2"] = "0"
        scb["MinELev3"] = "0"
        scb["MinELev4"] = "0"
        scb["MinELev5"] = "0"
        scb["EMax"] = "50"
        scb["MaxELev1"] = "0"
        scb["MaxELev2"] = "0"
        scb["MaxELev3"] = "0"
        scb["MaxELev4"] = "0"
        scb["MaxELev5"] = "0"
        scb["EDmgSymPerCalc"] = "(skill('BoltSentry'.clc2) * skill('BoltSentry'.clc3)) / 100 - 100"
        scb["NumDirections"] = "1"
        scb["TravelSound"] = "greatermummy_unholybolt_1"
        scb["HitSound"] = "paladin_holybolt_impact_1"
        scb["ExplosionMissile"] = "bonespiritexplode"
        scb["SubMissile1"] = "sentryspikeinair"
        scb["HitSubMissile1"] = ""
        scb["CltHitSubMissile1"] = ""

    if "sentryspikeinair" in rows_by_name:
        ssa = rows_by_name["sentryspikeinair"]
        ssa["pCltDoFunc"] = "1"
        ssa["pCltHitFunc"] = ""
        ssa["pSrvDoFunc"] = "1"
        ssa["SrvCalc1"] = ""
        ssa["pSrvHitFunc"] = "38"
        ssa["sHitPar1"] = "-4"
        ssa["sHitPar2"] = "1"
        ssa["pSrvDmgFunc"] = ""
        ssa["Vel"] = "16"
        ssa["MaxVel"] = "24"
        ssa["Range"] = "(lvl >= 3) ? 2 : 0"
        ssa["InitSteps"] = "0"
        ssa["Activate"] = "0"
        ssa["LoopAnim"] = "0"
        ssa["CelFile"] = "null"
        ssa["AnimLen"] = "4"
        ssa["AnimSpeed"] = "16"
        ssa["SubLoop"] = ""
        ssa["SubStop"] = ""
        ssa["CollideType"] = "3"
        ssa["CollideKill"] = "1"
        ssa["LastCollide"] = "1"
        ssa["ClientCol"] = "1"
        ssa["NextHit"] = "1"
        ssa["NextDelay"] = "4"
        ssa["Size"] = "2"
        ssa["AlwaysExplode"] = ""
        ssa["Explosion"] = ""
        ssa["NoMultiShot"] = ""
        ssa["GetHit"] = "1"
        ssa["Trans"] = "1"
        ssa["Skill"] = ""
        ssa["ResultFlags"] = "4"
        ssa["HitFlags"] = "2"
        ssa["HitShift"] = "8"
        ssa["EType"] = ""
        ssa["EMin"] = ""
        ssa["MinELev1"] = ""
        ssa["MinELev2"] = ""
        ssa["MinELev3"] = ""
        ssa["MinELev4"] = ""
        ssa["MinELev5"] = ""
        ssa["EMax"] = ""
        ssa["MaxELev1"] = ""
        ssa["MaxELev2"] = ""
        ssa["MaxELev3"] = ""
        ssa["MaxELev4"] = ""
        ssa["MaxELev5"] = ""
        ssa["EDmgSymPerCalc"] = ""
        ssa["NumDirections"] = "32"
        ssa["SubMissile1"] = ""
        ssa["HitSubMissile1"] = "sentryspikeonground"
        ssa["CltHitSubMissile1"] = ""

    if "sentryspikeonground" in rows_by_name:
        ssg = rows_by_name["sentryspikeonground"]
        ssg["pCltDoFunc"] = "1"
        ssg["pCltHitFunc"] = ""
        ssg["pSrvDoFunc"] = "14"
        ssg["pSrvHitFunc"] = ""
        ssg["Param1"] = "1"
        ssg["*param1 desc"] = "Periodic Delay until Repeat (Min=1)"
        ssg["Param2"] = "30"
        ssg["*param2 desc"] = "Use skills srvdofunc #"
        ssg["Vel"] = "0"
        ssg["MaxVel"] = "0"
        ssg["Range"] = "(lvl >= 3) ? 2 : 0"
        ssg["Radius"] = "5"
        ssg["InitSteps"] = "0"
        ssg["LoopAnim"] = "0"
        ssg["CelFile"] = "null"
        ssg["AnimLen"] = "2"
        ssg["AnimSpeed"] = "16"
        ssg["CollideType"] = ""
        ssg["CollideKill"] = ""
        ssg["CollideFriend"] = ""
        ssg["LastCollide"] = ""
        ssg["Collision"] = ""
        ssg["ClientCol"] = ""
        ssg["ClientSend"] = ""
        ssg["NextHit"] = ""
        ssg["NextDelay"] = ""
        ssg["Size"] = "1"
        ssg["AlwaysExplode"] = ""
        ssg["Explosion"] = ""
        ssg["NoMultiShot"] = "1"
        ssg["CanSlow"] = ""
        ssg["Skill"] = "BoltSentry"
        ssg["HitShift"] = "8"
        ssg["NumDirections"] = "1"
        ssg["ExplosionMissile"] = ""

    # Step 4: Blades of Ice (progressive_cold, Id 274) <-> Ice Sentry (Death Sentry, Id 276)
    # 1. Blades of Ice Finishing Move Release Missiles (smooth Normal/Nightmare scaling across ELev1..3, endgame ramp in ELev4..5):
    #    - Charge 1 Finisher Release: bladesoficeexplode (Compact AoE Ice Blast + Solid Freeze)
    #    - Charge 2 Finisher Release: royalstrikechaosice -> bladesoficeexplode (Ice Blast + 12 Radiating Ice Bolts)
    #    - Charge 3 Finisher Release: catapult cold ball on (Full Frozen Orb -> catapult cold ball)
    boi_syn_expr = "12*skill('Death Sentry'.blvl) + 6*skill('Fists of Fire'.blvl) + 6*skill('Claws of Thunder'.blvl)"
    if "bladesoficeexplode" in rows_by_name:
        bie = rows_by_name["bladesoficeexplode"]
        bie["pCltDoFunc"] = "1"
        bie["pSrvDoFunc"] = "1"
        bie["pSrvHitFunc"] = ""
        bie["pSrvDmgFunc"] = "2"
        bie["dParam1"] = "100"
        bie["Range"] = "16"
        bie["CollideType"] = "3"
        bie["Collision"] = "1"
        bie["CollideKill"] = ""
        bie["LastCollide"] = "1"
        bie["NextHit"] = "1"
        bie["NextDelay"] = "25"
        bie["Size"] = "3"
        bie["ResultFlags"] = "4"
        bie["HitFlags"] = "2"
        bie["HitShift"] = "8"
        bie["ApplyMastery"] = "1"
        bie["EType"] = "cold"
        bie["EMin"] = "10"
        bie["MinELev1"] = "3"
        bie["MinELev2"] = "4"
        bie["MinELev3"] = "6"
        bie["MinELev4"] = "16"
        bie["MinELev5"] = "26"
        bie["EMax"] = "20"
        bie["MaxELev1"] = "6"
        bie["MaxELev2"] = "8"
        bie["MaxELev3"] = "12"
        bie["MaxELev4"] = "32"
        bie["MaxELev5"] = "52"
        bie["EDmgSymPerCalc"] = boi_syn_expr
        bie["ELen"] = "50"
        bie["ELevLen1"] = "3"
        bie["ELevLen2"] = "3"
        bie["ELevLen3"] = "3"

    if "royalstrikechaosice" in rows_by_name:
        rsci = rows_by_name["royalstrikechaosice"]
        rsci["pCltDoFunc"] = "1"
        rsci["pCltHitFunc"] = "1"
        rsci["pSrvDoFunc"] = "1"
        rsci["pSrvHitFunc"] = "38"
        rsci["pSrvDmgFunc"] = "2"
        rsci["Param1"] = ""
        rsci["dParam1"] = "100"
        rsci["sHitPar1"] = "4"
        rsci["sHitPar2"] = "0"
        rsci["cHitPar1"] = "3"
        rsci["cHitPar2"] = "1"
        rsci["Vel"] = "14"
        rsci["MaxVel"] = "14"
        rsci["Range"] = "18"
        rsci["InitSteps"] = "1"
        rsci["CollideType"] = "3"
        rsci["CollideKill"] = "1"
        rsci["LastCollide"] = "1"
        rsci["ClientCol"] = "1"
        rsci["NextHit"] = "1"
        rsci["NextDelay"] = "4"
        rsci["Size"] = "1"
        rsci["AlwaysExplode"] = "1"
        rsci["ResultFlags"] = "5"
        rsci["HitFlags"] = "2"
        rsci["HitShift"] = "8"
        rsci["ApplyMastery"] = "1"
        rsci["EType"] = "frze"
        rsci["EMin"] = "20"
        rsci["MinELev1"] = "6"
        rsci["MinELev2"] = "8"
        rsci["MinELev3"] = "12"
        rsci["MinELev4"] = "32"
        rsci["MinELev5"] = "52"
        rsci["EMax"] = "40"
        rsci["MaxELev1"] = "12"
        rsci["MaxELev2"] = "16"
        rsci["MaxELev3"] = "24"
        rsci["MaxELev4"] = "64"
        rsci["MaxELev5"] = "104"
        rsci["EDmgSymPerCalc"] = boi_syn_expr
        rsci["ELen"] = "65"
        rsci["ELevLen1"] = "4"
        rsci["ELevLen2"] = "4"
        rsci["ELevLen3"] = "4"
        rsci["ProgOverlay"] = "ice_explode"
        rsci["ExplosionMissile"] = "bladesoficeexplode"
        rsci["HitSubMissile1"] = "bladesoficeexplode"
        rsci["CltHitSubMissile1"] = "bladesoficeexplode"

    if "catapult cold ball on" in rows_by_name:
        ccbo = rows_by_name["catapult cold ball on"]
        ccbo["pCltDoFunc"] = "19"
        ccbo["pCltHitFunc"] = "30"
        ccbo["pSrvDoFunc"] = "15"
        ccbo["pSrvHitFunc"] = "29"
        ccbo["Param1"] = "1"
        ccbo["*param1 desc"] = "Missile Spawn Rate (Min=1)"
        ccbo["Param2"] = "19"
        ccbo["*param2 desc"] = "Direction Index Increment"
        ccbo["CltParam1"] = "1"
        ccbo["*client param1 desc"] = "CltSubMissile1 Spawn Rate (Min=1)"
        ccbo["CltParam2"] = "19"
        ccbo["*client param2 desc"] = "CltSubMissile1 Direction Index Increment (Max = 64)"
        ccbo["sHitPar1"] = "4"
        ccbo["*server hit param1 desc"] = "Increment for # of HitSubMissile1 created (Higher value means less Missiles created) (Min=1)"
        ccbo["cHitPar1"] = "4"
        ccbo["*client hit param1 desc"] = "Density of CltHitSubMissile1 (Higher value means less Missiles created)"
        ccbo["Vel"] = "10"
        ccbo["MaxVel"] = "10"
        ccbo["Range"] = "30"
        ccbo["Light"] = "6"
        ccbo["Red"] = "81"
        ccbo["Green"] = "81"
        ccbo["Blue"] = "255"
        ccbo["InitSteps"] = "1"
        ccbo["Activate"] = "0"
        ccbo["LoopAnim"] = "1"
        ccbo["CelFile"] = "IceOrb"
        ccbo["animrate"] = "1024"
        ccbo["AnimLen"] = "16"
        ccbo["AnimSpeed"] = "16"
        ccbo["CollideType"] = "3"
        ccbo["LastCollide"] = "1"
        ccbo["ClientCol"] = "1"
        ccbo["Size"] = "1"
        ccbo["AlwaysExplode"] = "1"
        ccbo["ReturnFire"] = "1"
        ccbo["GetHit"] = "1"
        ccbo["Trans"] = "1"
        ccbo["ResultFlags"] = "4"
        ccbo["HitShift"] = "8"
        ccbo["NumDirections"] = "1"
        ccbo["TravelSound"] = "sorceress_cast_cold"
        ccbo["HitSound"] = "sorceress_iceblast_impact_1"
        ccbo["SubMissile1"] = "catapult cold ball"
        ccbo["HitSubMissile1"] = "catapult cold explosion"
        ccbo["CltSubMissile1"] = "catapult cold ball"
        ccbo["CltHitSubMissile1"] = "catapult cold explosion"
        ccbo["ExplosionMissile"] = "frozenorbexplode"

    for fo_child in ("catapult cold ball", "catapult cold explosion"):
        if fo_child in rows_by_name:
            fcb = rows_by_name[fo_child]
            is_nova = fo_child == "catapult cold explosion"
            fcb["pCltDoFunc"] = "20" if is_nova else "1"
            fcb["pCltHitFunc"] = ""
            fcb["pSrvDoFunc"] = "16" if is_nova else "1"
            fcb["pSrvHitFunc"] = ""
            fcb["pSrvDmgFunc"] = "2"
            fcb["dParam1"] = "100"
            fcb["Param1"] = "6" if is_nova else ""
            fcb["Param2"] = "2" if is_nova else ""
            fcb["CltParam1"] = "6" if is_nova else ""
            fcb["CltParam2"] = "2" if is_nova else ""
            fcb["sHitPar1"] = ""
            fcb["Vel"] = "24" if is_nova else "18"
            fcb["MaxVel"] = "24" if is_nova else "18"
            fcb["Range"] = "25"
            fcb["Light"] = "4"
            fcb["Red"] = "81"
            fcb["Green"] = "81"
            fcb["Blue"] = "255"
            fcb["InitSteps"] = "0"
            fcb["Activate"] = "0"
            fcb["LoopAnim"] = "1"
            fcb["CelFile"] = "IceBolt"
            fcb["animrate"] = "1024"
            fcb["AnimLen"] = "6"
            fcb["AnimSpeed"] = "16"
            fcb["CollideType"] = "3"
            fcb["CollideKill"] = "1"
            fcb["LastCollide"] = "1"
            fcb["ClientCol"] = "1"
            fcb["ClientSend"] = ""
            fcb["NextHit"] = "1"
            fcb["NextDelay"] = "4"
            fcb["Size"] = "1"
            fcb["AlwaysExplode"] = ""
            fcb["Explosion"] = ""
            fcb["NoMultiShot"] = ""
            fcb["ReturnFire"] = "1"
            fcb["GetHit"] = "1"
            fcb["Trans"] = "1"
            fcb["Skill"] = ""
            fcb["ResultFlags"] = "4"
            fcb["HitFlags"] = "2"
            fcb["HitShift"] = "8"
            fcb["ApplyMastery"] = "1"
            fcb["EType"] = "cold"
            fcb["EMin"] = "15"
            fcb["MinELev1"] = "4"
            fcb["MinELev2"] = "6"
            fcb["MinELev3"] = "9"
            fcb["MinELev4"] = "24"
            fcb["MinELev5"] = "39"
            fcb["EMax"] = "30"
            fcb["MaxELev1"] = "8"
            fcb["MaxELev2"] = "12"
            fcb["MaxELev3"] = "18"
            fcb["MaxELev4"] = "48"
            fcb["MaxELev5"] = "78"
            fcb["EDmgSymPerCalc"] = boi_syn_expr
            fcb["ELen"] = "75"
            fcb["ELevLen1"] = "5"
            fcb["ELevLen2"] = "5"
            fcb["ELevLen3"] = "5"
            fcb["NumDirections"] = "16"
            fcb["TravelSound"] = "" if is_nova else "sorceress_glacialspike_1"
            fcb["HitSound"] = "sorceress_iceblast_impact_1"
            fcb["ExplosionMissile"] = "iceexplode"

    # 2. Ice Sentry (Death Sentry, Id 276 -> mon death sentry, Id 312 -> frozenhorror arcticblast1 -> frozenhorror arcticblast2):
    #    - Fires Arctic Blast jet (frozenhorror arcticblast1)
    #    - Charge 1: +Range (Range = 16 -> 26 + Blades of Ice.blvl / 2 frames)
    #    - Charge 2: +Duration (5 base bursts -> 8 + Blades of Ice.blvl / 10 bursts via mon death sentry calc4)
    #    - Charge 3: Solid Freeze in place (spawns frozenhorror arcticblast2 with EType=frze, pSrvDmgFunc=2, dParam1=100)
    ds_c = "skill('Ass Trap Charge Consume'.blvl)"
    boi_m = "skill('Blades of Ice'.blvl)"
    if "frozenhorror arcticblast1" in rows_by_name:
        fhab1 = rows_by_name["frozenhorror arcticblast1"]
        fhab1["pCltDoFunc"] = "1"
        fhab1["pSrvDoFunc"] = "2"
        fhab1["SrvCalc1"] = "1"
        fhab1["pSrvHitFunc"] = ""
        fhab1["pSrvDmgFunc"] = ""
        fhab1["sHitPar1"] = ""
        fhab1["sHitPar2"] = ""
        fhab1["Param2"] = "16"
        fhab1["Vel"] = "12"
        fhab1["MaxVel"] = "12"
        fhab1["Range"] = f"16 + (({ds_c} >= 1) ? (10 + {boi_m} / 2) : 0)"
        fhab1["InitSteps"] = "1"
        fhab1["Activate"] = "0"
        fhab1["LoopAnim"] = "0"
        fhab1["CelFile"] = "expansion\\ArcticBlastIce"
        fhab1["animrate"] = "1024"
        fhab1["AnimLen"] = "16"
        fhab1["AnimSpeed"] = "16"
        fhab1["CollideType"] = "3"
        fhab1["CollideKill"] = ""
        fhab1["LastCollide"] = "1"
        fhab1["ClientCol"] = "1"
        fhab1["NextHit"] = "1"
        fhab1["NextDelay"] = "4"
        fhab1["Size"] = "2"
        fhab1["NoUniqueMod"] = ""
        fhab1["CanSlow"] = "1"
        fhab1["ReturnFire"] = "1"
        fhab1["GetHit"] = "1"
        fhab1["Trans"] = "1"
        fhab1["Pierce"] = "1"
        fhab1["Skill"] = ""
        fhab1["ResultFlags"] = "4"
        fhab1["HitFlags"] = "2"
        fhab1["HitShift"] = "8"
        fhab1["EType"] = "cold"
        fhab1["EMin"] = "10"
        fhab1["MinELev1"] = "0"
        fhab1["MinELev2"] = "0"
        fhab1["MinELev3"] = "0"
        fhab1["MinELev4"] = "0"
        fhab1["MinELev5"] = "0"
        fhab1["EMax"] = "16"
        fhab1["MaxELev1"] = "0"
        fhab1["MaxELev2"] = "0"
        fhab1["MaxELev3"] = "0"
        fhab1["MaxELev4"] = "0"
        fhab1["MaxELev5"] = "0"
        fhab1["EDmgSymPerCalc"] = "(skill('mon death sentry'.clc2) * skill('mon death sentry'.clc3)) / 100 - 100"
        fhab1["ELen"] = "100"
        fhab1["ELevLen1"] = "5"
        fhab1["ELevLen2"] = "5"
        fhab1["ELevLen3"] = "5"
        fhab1["HitClass"] = "32"
        fhab1["NumDirections"] = "16"
        fhab1["DamageRate"] = ""
        fhab1["TravelSound"] = "druid_arcticblast"
        fhab1["SubMissile1"] = "frozenhorror arcticblast2"
        fhab1["HitSubMissile1"] = ""
        fhab1["CltHitSubMissile1"] = ""

    if "frozenhorror arcticblast2" in rows_by_name:
        fhab2 = rows_by_name["frozenhorror arcticblast2"]
        fhab2["pCltDoFunc"] = "1"
        fhab2["pSrvDoFunc"] = "1"
        fhab2["pSrvHitFunc"] = ""
        fhab2["pSrvDmgFunc"] = "2"
        fhab2["dParam1"] = "100"
        fhab2["Param2"] = ""
        fhab2["Vel"] = "12"
        fhab2["MaxVel"] = "12"
        fhab2["Range"] = f"({ds_c} >= 3) ? 2 : 0"
        fhab2["InitSteps"] = "0"
        fhab2["Activate"] = "0"
        fhab2["LoopAnim"] = "0"
        fhab2["CelFile"] = "null"
        fhab2["AnimLen"] = "4"
        fhab2["AnimSpeed"] = "16"
        fhab2["CollideType"] = "3"
        fhab2["CollideKill"] = "1"
        fhab2["LastCollide"] = "1"
        fhab2["ClientCol"] = "1"
        fhab2["NextHit"] = "1"
        fhab2["NextDelay"] = "4"
        fhab2["Size"] = "2"
        fhab2["AlwaysExplode"] = ""
        fhab2["Explosion"] = ""
        fhab2["NoUniqueMod"] = ""
        fhab2["CanSlow"] = ""
        fhab2["ReturnFire"] = ""
        fhab2["GetHit"] = "1"
        fhab2["Trans"] = "1"
        fhab2["Skill"] = ""
        fhab2["ResultFlags"] = "5"
        fhab2["HitFlags"] = "2"
        fhab2["HitShift"] = "8"
        fhab2["EType"] = "frze"
        fhab2["EMin"] = "1"
        fhab2["MinELev1"] = "0"
        fhab2["MinELev2"] = "0"
        fhab2["MinELev3"] = "0"
        fhab2["MinELev4"] = "0"
        fhab2["MinELev5"] = "0"
        fhab2["EMax"] = "2"
        fhab2["MaxELev1"] = "0"
        fhab2["MaxELev2"] = "0"
        fhab2["MaxELev3"] = "0"
        fhab2["MaxELev4"] = "0"
        fhab2["MaxELev5"] = "0"
        fhab2["ELen"] = "75"
        fhab2["ELevLen1"] = "5"
        fhab2["ELevLen2"] = "5"
        fhab2["ELevLen3"] = "5"
        fhab2["NumDirections"] = "16"
        fhab2["TravelSound"] = ""

    # 5. Claws of Thunder / Electrocute (Id 269) & Lightning Sentry (Id 271) Missiles:
    #    - Charge 1 Finisher: clawsofthunderbolt (spread of 8..16 Charged Bolts)
    #    - Charge 2 Finisher: clawsofthundernova (360-degree Lightning Nova)
    #    - Charge 3 Finisher: royalstrikechainlightning (Chain Lightning)
    #    - Lightning Sentry: sentrylightningbolt (piercing bolt, Charge 1+ extends range) + sentrylightningbolt2 (Charge 3 blinds hit monsters)
    cot_syn_expr = "12*skill('Lightning Sentry'.blvl) + 6*skill('Fists of Fire'.blvl) + 6*skill('Blades of Ice'.blvl)"
    if "clawsofthunderbolt" in rows_by_name:
        cotb = rows_by_name["clawsofthunderbolt"]
        cotb["Skill"] = ""
        cotb["HitShift"] = "8"
        cotb["EType"] = "ltng"
        cotb["EMin"] = "1"
        cotb["MinELev1"] = "0"
        cotb["MinELev2"] = "0"
        cotb["MinELev3"] = "0"
        cotb["MinELev4"] = "0"
        cotb["MinELev5"] = "0"
        cotb["EMax"] = "30"
        cotb["MaxELev1"] = "8"
        cotb["MaxELev2"] = "12"
        cotb["MaxELev3"] = "18"
        cotb["MaxELev4"] = "42"
        cotb["MaxELev5"] = "64"
        cotb["EDmgSymPerCalc"] = cot_syn_expr

    if "clawsofthundernova" in rows_by_name:
        cotn = rows_by_name["clawsofthundernova"]
        cotn["Skill"] = ""
        cotn["HitShift"] = "8"
        cotn["EType"] = "ltng"
        cotn["EMin"] = "1"
        cotn["MinELev1"] = "0"
        cotn["MinELev2"] = "0"
        cotn["MinELev3"] = "0"
        cotn["MinELev4"] = "0"
        cotn["MinELev5"] = "0"
        cotn["EMax"] = "80"
        cotn["MaxELev1"] = "20"
        cotn["MaxELev2"] = "30"
        cotn["MaxELev3"] = "46"
        cotn["MaxELev4"] = "110"
        cotn["MaxELev5"] = "168"
        cotn["EDmgSymPerCalc"] = cot_syn_expr

    if "royalstrikechainlightning" in rows_by_name:
        rscl = rows_by_name["royalstrikechainlightning"]
        rscl["pCltDoFunc"] = "8"
        rscl["pCltHitFunc"] = "16"
        rscl["pSrvDoFunc"] = "1"
        rscl["pSrvHitFunc"] = "12"
        rscl["sHitPar1"] = "12"
        rscl["cHitPar1"] = "12"
        rscl["CollideKill"] = "1"
        rscl["LastCollide"] = "1"
        rscl["Skill"] = ""
        rscl["HitShift"] = "8"
        rscl["EType"] = "ltng"
        rscl["EMin"] = "1"
        rscl["MinELev1"] = "0"
        rscl["MinELev2"] = "0"
        rscl["MinELev3"] = "0"
        rscl["MinELev4"] = "0"
        rscl["MinELev5"] = "0"
        rscl["EMax"] = "120"
        rscl["MaxELev1"] = "30"
        rscl["MaxELev2"] = "45"
        rscl["MaxELev3"] = "70"
        rscl["MaxELev4"] = "165"
        rscl["MaxELev5"] = "252"
        rscl["EDmgSymPerCalc"] = cot_syn_expr

    if "sentrylightningbolt" in rows_by_name:
        slb = rows_by_name["sentrylightningbolt"]
        slb["pCltDoFunc"] = "8"
        slb["pSrvDoFunc"] = "2"
        slb["SrvCalc1"] = "1"
        slb["*SrvCalc1 desc"] = "Submissile spawn frequency"
        slb["Vel"] = "30"
        slb["MaxVel"] = "30"
        slb["Range"] = "8 + ((skill('Ass Trap Charge Consume'.blvl) >= 1) ? (6 + skill('Claws of Thunder'.blvl) / 3) : 0)"
        slb["LoopAnim"] = "0"
        slb["AnimLen"] = "32"
        slb["AnimSpeed"] = "16"
        slb["Pierce"] = "1"
        slb["NextHit"] = "1"
        slb["NextDelay"] = "4"
        slb["CollideKill"] = ""
        slb["Skill"] = ""
        slb["HitShift"] = "8"
        slb["EType"] = "ltng"
        slb["EMin"] = "1"
        slb["MinELev1"] = "0"
        slb["MinELev2"] = "0"
        slb["MinELev3"] = "0"
        slb["MinELev4"] = "0"
        slb["MinELev5"] = "0"
        slb["EMax"] = "64"
        slb["MaxELev1"] = "0"
        slb["MaxELev2"] = "0"
        slb["MaxELev3"] = "0"
        slb["MaxELev4"] = "0"
        slb["MaxELev5"] = "0"
        slb["EDmgSymPerCalc"] = "(skill('sentry lightning'.clc2) * skill('sentry lightning'.clc3)) / 100 - 100"
        slb["SubMissile1"] = "sentrylightningbolt2"

    if "sentrylightningbolt2" in rows_by_name:
        slb2 = rows_by_name["sentrylightningbolt2"]
        slb2["pCltDoFunc"] = "1"
        slb2["pCltHitFunc"] = ""
        slb2["pSrvDoFunc"] = "1"
        slb2["pSrvHitFunc"] = "21"
        slb2["pSrvDmgFunc"] = ""
        slb2["Param1"] = ""
        slb2["Param2"] = ""
        slb2["CltParam1"] = ""
        slb2["sHitPar1"] = ""
        slb2["cHitPar1"] = ""
        slb2["Vel"] = "30"
        slb2["MaxVel"] = "30"
        slb2["Range"] = "(skill('Ass Trap Charge Consume'.blvl) >= 3) ? 2 : 0"
        slb2["Light"] = ""
        slb2["Flicker"] = ""
        slb2["Red"] = ""
        slb2["Green"] = ""
        slb2["Blue"] = ""
        slb2["InitSteps"] = "0"
        slb2["Activate"] = "0"
        slb2["LoopAnim"] = "0"
        slb2["CelFile"] = "null"
        slb2["animrate"] = "1024"
        slb2["AnimLen"] = "4"
        slb2["AnimSpeed"] = "16"
        slb2["SubLoop"] = ""
        slb2["SubStart"] = ""
        slb2["SubStop"] = ""
        slb2["CollideType"] = "3"
        slb2["CollideKill"] = ""
        slb2["CollideFriend"] = ""
        slb2["LastCollide"] = "1"
        slb2["Collision"] = ""
        slb2["ClientCol"] = "1"
        slb2["ClientSend"] = ""
        slb2["NextHit"] = "1"
        slb2["NextDelay"] = "4"
        slb2["Size"] = "2"
        slb2["ReturnFire"] = ""
        slb2["GetHit"] = ""
        slb2["Trans"] = "1"
        slb2["Pierce"] = "1"
        slb2["MissileSkill"] = ""
        slb2["Skill"] = "sentry lightning"
        slb2["ResultFlags"] = ""
        slb2["HitFlags"] = ""
        slb2["HitShift"] = "8"
        slb2["EType"] = ""
        slb2["EMin"] = ""
        slb2["EMax"] = ""
        slb2["NumDirections"] = "32"
        slb2["TravelSound"] = ""
        slb2["HitSound"] = ""
        slb2["ProgOverlay"] = ""
        slb2["CltSubMissile1"] = ""
        slb2["CltHitSubMissile1"] = ""
        slb2["CltHitSubMissile2"] = ""
        slb2["CltHitSubMissile3"] = ""
        slb2["CltHitSubMissile4"] = ""



    # Caltrops (Shock Field, Id 256): the ground patch is physical spikes (HD visual remapped to the fire-spike
    # ground art).  Damage-only: it comes from the Shock Field skill row (Skill = 'Shock Field', physical
    # MinDam/MaxDam, once per second).  (A slow could not be delivered alongside damage: pSrvHitFunc 21 applies an
    # aura state but skips damage, and spawning a twin slow patch never reached monsters.)
    if "shock field on ground" in rows_by_name:
        csg = rows_by_name["shock field on ground"]
        csg["pSrvHitFunc"] = "21"
        csg["Skill"] = "Shock Field"
        csg["CelFile"] = "expansion\\FireSpikesGround"
        csg["AnimLen"] = "8"
        csg["Light"] = ""
        csg["Red"] = "255"
        csg["Green"] = "255"
        csg["Blue"] = "255"
        csg["TravelSound"] = ""
        csg["SrcDamage"] = ""
        csg["EType"] = ""
        csg["EMin"] = ""
        csg["EMax"] = ""
        csg["DmgSymPerCalc"] = ""
        csg["EDmgSymPerCalc"] = ""
        for _k in ("MinDamage", "MaxDamage") + tuple(f"MinLevDam{n}" for n in range(1, 6)) + tuple(
            f"MaxLevDam{n}" for n in range(1, 6)
        ):
            csg[_k] = ""
        csg["HitSubMissile1"] = ""
        csg["CltHitSubMissile1"] = ""
        csg["pSrvHitFunc"] = ""
        csg["SubMissile1"] = ""
        # Duration scales with skill level: 90 frames (3.6s) at Lvl 1 -> 185 frames (7.4s) at Lvl 20 (~2x).
        # Damage per second is unchanged (one hit per NextDelay=25 frames).
        csg["Range"] = "85 + 5*lvl"

    # Shuriken (Inferno Sentry, Id 272): bouncing heavy throwing star, modeled on the reworked Blessed Hammer
    # (Chain Lightning mechanics: srvdofunc 26 / pSrvHitFunc 12).  Reuses the unused 'throwingstar' row, which already
    # has the expansion throwing-star HD visual.  No stun (ResultFlags 4 = GetHit only, no knockback/stun dmg func).
    # Requires Attack Rating (ToHit=1), allows 2H weapons full 75% weapon damage (Half2HSrc=""), and uses NextDelay=10.
    if "throwingstar" in rows_by_name:
        ts_m = rows_by_name["throwingstar"]
        ts_m["pCltDoFunc"] = "1"
        ts_m["pCltHitFunc"] = "16"
        ts_m["pSrvDoFunc"] = "1"
        ts_m["pSrvHitFunc"] = "12"
        ts_m["sHitPar1"] = "0"
        ts_m["cHitPar1"] = "0"
        ts_m["pSrvDmgFunc"] = ""
        ts_m["dParam1"] = ""
        ts_m["dParam2"] = ""
        ts_m["Vel"] = "20"
        ts_m["VelLev"] = "6"
        ts_m["MaxVel"] = "40"
        ts_m["Accel"] = ""
        ts_m["Range"] = "40"
        ts_m["Size"] = "2"
        ts_m["Pierce"] = ""
        ts_m["ToHit"] = "1"
        ts_m["Half2HSrc"] = ""
        ts_m["CollideKill"] = "1"
        ts_m["LastCollide"] = "1"
        ts_m["ClientCol"] = "1"
        ts_m["NextHit"] = "1"
        ts_m["NextDelay"] = "10"
        ts_m["Skill"] = "Inferno Sentry"
        ts_m["ResultFlags"] = "4"
        ts_m["EType"] = ""
        ts_m["TravelSound"] = "assassin_bladefury_throw_1"
        ts_m["HitSound"] = "assassin_bladefury_hit"

    # Blade Fury (Id 266): allow 2H weapons to get full 75% weapon damage (Half2HSrc="") and increase blade velocity
    for _bf_m in ("bladefury1", "bladefury2", "bladefragment1", "bladefragment2"):
        if _bf_m in rows_by_name:
            rows_by_name[_bf_m]["Half2HSrc"] = ""
    for _bf_frag in ("bladefragment1", "bladefragment2"):
        if _bf_frag in rows_by_name:
            rows_by_name[_bf_frag]["Vel"] = "32"
            rows_by_name[_bf_frag]["MaxVel"] = "32"
            rows_by_name[_bf_frag]["Range"] = "30"

# Appended frames 29..54 in data/hd/global/ui/spells/hireables/hrskillicon.sprite (and .lowend.sprite)
# sliced directly from each class's native skillicon.sprite sheet at IconCel.
CUSTOM_MERC_SKILL_ICONS = (
    (29, "weaken",            "necromancer", "neskillicon", 12),
    (30, "life tap",          "necromancer", "neskillicon", 32),
    (31, "lower resist",      "necromancer", "neskillicon", 50),
    (32, "dim vision",        "necromancer", "neskillicon", 10),
    (33, "slow missiles",     "amazon",      "amskillicon", 22),
    (34, "decrepify",         "necromancer", "neskillicon", 42),
    (35, "cloak of shadows",  "assassin",    "asskillicon", 24),
    (36, "amplify damage",    "necromancer", "neskillicon", 0),
    (37, "multiple shot",     "amazon",      "amskillicon", 12),
    (38, "strafe",            "amazon",      "amskillicon", 40),
    (39, "critical strike",   "amazon",      "amskillicon", 6),
    (40, "cleansing",         "paladin",     "paskillicon", 38),
    (41, "meditation",        "paladin",     "paskillicon", 48),
    (42, "salvation",         "paladin",     "paskillicon", 58),
    (43, "vigor",             "paladin",     "paskillicon", 26),
    (44, "sanctuary",         "paladin",     "paskillicon", 46),
    (45, "redemption",        "paladin",     "paskillicon", 56),
    (46, "concentration",     "paladin",     "paskillicon", 34),
    (47, "fanaticism",        "paladin",     "paskillicon", 52),
    (48, "holy fire",         "paladin",     "paskillicon", 20),
    (49, "holy shock",        "paladin",     "paskillicon", 44),
    (50, "fire mastery",      "sorceress",   "soskillicon", 50),
    (51, "cold mastery",      "sorceress",   "soskillicon", 58),
    (52, "lightning mastery", "sorceress",   "soskillicon", 54),
    (53, "battle orders",     "barbarian",   "baskillicon", 46),
    (54, "double swing",      "barbarian",   "baskillicon", 14),
)



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
        # Scale down staffmod / skill cost multipliers (0.06x) and flat cost additions (0.06x)
        # so multi-staffmod Wands/Staves/Scepters/Orbs and Chance-to-Cast proc suffixes cap
        # cleanly within the ~300,000g Hell vendor ceiling.
        if r.get("cost mult"):
            r["cost mult"] = scale_int(r["cost mult"], 0.06, min_val=1)
        if r.get("cost add"):
            r["cost add"] = scale_int(r["cost add"], 0.06, min_val=1)

    d_headers, d_rows = read_excel_tsv("skilldesc.txt")
    by_desc = {r["skilldesc"]: r for r in d_rows if r.get("skilldesc")}

    _apply_paladin_skills(by_name)
    _apply_paladin_skilldesc(by_desc)
    _apply_barbarian_skills(by_name)
    _apply_barbarian_skilldesc(by_desc)

    # Scale Monster/Object Trap Skills (PoisonBallTrap, CursedBallTrapRight/Left, Trap Nova, PrimePoisonNova)
    for t_skill in ("PoisonBallTrap", "CursedBallTrapRight", "CursedBallTrapLeft"):
        if t_skill in by_name:
            ts = by_name[t_skill]
            ts["HitShift"] = "8"
            ts["MinDam"] = "70"
            ts["MinLevDam1"] = "55"
            ts["MinLevDam2"] = "105"
            ts["MinLevDam3"] = "155"
            ts["MinLevDam4"] = "175"
            ts["MinLevDam5"] = "195"
            ts["MaxDam"] = "200"
            ts["MaxLevDam1"] = "170"
            ts["MaxLevDam2"] = "320"
            ts["MaxLevDam3"] = "470"
            ts["MaxLevDam4"] = "530"
            ts["MaxLevDam5"] = "590"

    # Scale Act Boss & SuperUnique Signature Spells (1.40x base + progressive per-level scaling)
    for boss_skill in (
        "PrimeLightning", "PrimeBolt", "MephistoMissile", "MephFrostNova",
        "DiabLight", "DiabCold", "DiabFire",
        "Baal Nova", "Baal Inferno", "Baal Cold Missiles",
    ):
        if boss_skill in by_name:
            bs = by_name[boss_skill]
            for dcol in (
                "MinDam", "MaxDam", "MinLevDam1", "MinLevDam2", "MinLevDam3", "MinLevDam4", "MinLevDam5",
                "MaxLevDam1", "MaxLevDam2", "MaxLevDam3", "MaxLevDam4", "MaxLevDam5",
                "EMin", "EMax", "EMinLev1", "EMinLev2", "EMinLev3", "EMinLev4", "EMinLev5",
                "EMaxLev1", "EMaxLev2", "EMaxLev3", "EMaxLev4", "EMaxLev5",
            ):
                if bs.get(dcol):
                    bs[dcol] = scale_int(bs[dcol], 1.40)

    # Populate HireableIconCel (frames 29..54 in expanded Spells/Hireables/HrSkillIcon) for custom Mercenary skills
    # so HireMenuPanelHD & HirelingInventoryPanelHD render each skill's authentic class skill icon.
    for frame_idx, sdesc_key, _cls_dir, _spr_prefix, _icon_cel in CUSTOM_MERC_SKILL_ICONS:
        if sdesc_key in by_desc:
            by_desc[sdesc_key]["HireableIconCel"] = str(frame_idx)

    # Append universal "Dismiss Aura" (Id 429) so Paladins have an innate 0-mana empty aura
    # in the General Skills row (ListRow=0) to cleanly toggle off active mana-draining auras with Quick Cast!
    if "dismiss aura" not in by_desc:
        new_desc = {h: "" for h in d_headers}
        new_desc["skilldesc"] = "dismiss aura"
        new_desc["SkillPage"] = "0"
        new_desc["SkillRow"] = "0"
        new_desc["SkillColumn"] = "0"
        new_desc["ListRow"] = "3"
        new_desc["IconCel"] = "40"
        new_desc["str name"] = "ModDismissAuraName"
        new_desc["str short"] = "ModDismissAuraDesc"
        new_desc["str long"] = "ModDismissAuraDesc"
        new_desc["str alt"] = "ModDismissAuraName"
        new_desc["*eol"] = "0"
        d_rows.append(new_desc)

    if "Dismiss Aura" not in by_name:
        max_sid = max(parse_int(r.get("*Id", "0"), 0) for r in s_rows)
        new_sk = {h: "" for h in s_headers}
        new_sk["skill"] = "Dismiss Aura"
        new_sk["*Id"] = str(max_sid + 1)
        new_sk["skilldesc"] = "dismiss aura"
        new_sk["srvdofunc"] = "65"
        new_sk["aurafilter"] = "73731"
        new_sk["aurastate"] = "pal_dismiss_aura"
        new_sk["auratargetstate"] = "pal_dismiss_aura"
        new_sk["aurarangecalc"] = "ln12"
        new_sk["aurastat1"] = "maxstamina"
        new_sk["aurastatcalc1"] = "1"
        new_sk["Param1"] = "16"
        new_sk["*Param1 Description"] = "Radius baseline"
        new_sk["Param2"] = "2"
        new_sk["*Param2 Description"] = "Radius per level"
        new_sk["immediate"] = "1"
        new_sk["enhanceable"] = "1"
        new_sk["attackrank"] = "1"
        new_sk["range"] = "none"
        new_sk["monanim"] = "xx"
        new_sk["reqlevel"] = "1"
        new_sk["maxlvl"] = "20"
        new_sk["restrict"] = ""
        new_sk["leftskill"] = "0"
        new_sk["rightskill"] = "1"
        new_sk["minmana"] = "0"
        new_sk["manashift"] = "4"
        new_sk["mana"] = "0"
        new_sk["lvlmana"] = "0"
        new_sk["interrupt"] = "1"
        new_sk["InTown"] = "1"
        new_sk["aura"] = "1"
        new_sk["perdelay"] = "10"
        new_sk["InGame"] = "1"
        new_sk["HitShift"] = "8"
        new_sk["cost mult"] = "15"
        new_sk["cost add"] = "60"
        new_sk["*eol"] = "0"
        s_rows.append(new_sk)

    # Append 4 Barbarian Stamina helper skills (Ids 430, 431, 432, 433):
    #   - 430: Bar Stamina Drain (gated by stat('frenzy'.accr)>0; applies 2-frame bar_stamina_reflex EType=stam on Frenzy swings)
    #   - 431: Battle Trance Pulse (restores Find Item clc1 Stamina via 2-frame staminarecoverybonus surge when hit or on kill)
    #   - 432: Bar Totem Stamina Pulse (pulses stambarblue=1 and +5000% staminarecoverybonus in proximity to Totem of the Ancients)
    #   - 433: Bar Stamina Reflex (applies auraeventfunc=3 Shiver Armor EType=stam reflection to nearby monsters via srvdofunc=30)
    if "Bar Stamina Drain" not in by_name:
        max_sid = max(parse_int(r.get("*Id", "0"), 0) for r in s_rows)
        sk_drain = {h: "" for h in s_headers}
        sk_drain["skill"] = "Bar Stamina Drain"
        sk_drain["*Id"] = str(max_sid + 1)
        sk_drain["srvdofunc"] = "30"
        sk_drain["aurafilter"] = "2"
        sk_drain["auratargetstate"] = "bar_stamina_reflex"
        sk_drain["auralencalc"] = "(stat('frenzy'.accr)>0)?2:0"
        sk_drain["aurarangecalc"] = "5"
        sk_drain["aurastat1"] = ""
        sk_drain["aurastatcalc1"] = ""
        sk_drain["aurastat2"] = ""
        sk_drain["aurastatcalc2"] = ""
        sk_drain["auraevent1"] = "install"
        sk_drain["auraeventfunc1"] = "3"
        sk_drain["range"] = "none"
        sk_drain["monanim"] = "xx"
        sk_drain["ItemEffect"] = "1"
        sk_drain["reqlevel"] = "1"
        sk_drain["InGame"] = "1"
        sk_drain["HitShift"] = "7"
        sk_drain["EType"] = "stam"
        sk_drain["EMin"] = "12"
        sk_drain["EMinLev1"] = "0"
        sk_drain["EMinLev2"] = "0"
        sk_drain["EMinLev3"] = "0"
        sk_drain["EMinLev4"] = "0"
        sk_drain["EMinLev5"] = "0"
        sk_drain["EMax"] = "12"
        sk_drain["EMaxLev1"] = "0"
        sk_drain["EMaxLev2"] = "0"
        sk_drain["EMaxLev3"] = "0"
        sk_drain["EMaxLev4"] = "0"
        sk_drain["EMaxLev5"] = "0"
        sk_drain["*eol"] = "0"
        s_rows.append(sk_drain)

    if "Battle Trance Pulse" not in by_name:
        max_sid = max(parse_int(r.get("*Id", "0"), 0) for r in s_rows)
        sk_trance = {h: "" for h in s_headers}
        sk_trance["skill"] = "Battle Trance Pulse"
        sk_trance["*Id"] = str(max_sid + 1)
        sk_trance["srvdofunc"] = "18"
        sk_trance["srvmissilea"] = "battlecommand"
        sk_trance["aurafilter"] = "73731"
        sk_trance["aurastate"] = "bar_trance_pulse"
        sk_trance["auratargetstate"] = "bar_trance_pulse"
        sk_trance["auralencalc"] = "2"
        sk_trance["aurarangecalc"] = "15"
        sk_trance["aurastat1"] = "staminarecoverybonus"
        sk_trance["aurastatcalc1"] = "(skill('Find Item'.clc1)*7500*256)/max(256,stat('maxstamina'.accr))-100"
        sk_trance["aurastat2"] = "item_staminadrainpct"
        sk_trance["aurastatcalc2"] = "100"
        sk_trance["aurastat3"] = "stamina"
        sk_trance["aurastatcalc3"] = "skill('Find Item'.clc1)*256"
        sk_trance["range"] = "none"
        sk_trance["monanim"] = "xx"
        sk_trance["ItemEffect"] = "1"
        sk_trance["reqlevel"] = "1"
        sk_trance["InGame"] = "1"
        sk_trance["HitShift"] = "8"
        sk_trance["*eol"] = "0"
        s_rows.append(sk_trance)

    if "Bar Totem Stamina Pulse" not in by_name:
        max_sid = max(parse_int(r.get("*Id", "0"), 0) for r in s_rows)
        sk_totem = {h: "" for h in s_headers}
        sk_totem["skill"] = "Bar Totem Stamina Pulse"
        sk_totem["*Id"] = str(max_sid + 1)
        sk_totem["srvdofunc"] = "65"
        sk_totem["srvmissilea"] = "grimwardlarge"
        sk_totem["cltdofunc"] = "25"
        sk_totem["cltmissilea"] = "grimwardlarge"
        sk_totem["aurafilter"] = "73731"
        sk_totem["aurastate"] = "bar_totem_stamina"
        sk_totem["auratargetstate"] = "bar_totem_stamina"
        sk_totem["auralencalc"] = "250"
        sk_totem["aurarangecalc"] = "skill('Grim Ward'.ln12)"
        sk_totem["aurastat1"] = "staminarecoverybonus"
        sk_totem["aurastatcalc1"] = "5000"
        sk_totem["aurastat2"] = "item_staminadrainpct"
        sk_totem["aurastatcalc2"] = "100"
        sk_totem["perdelay"] = "15"
        sk_totem["range"] = "none"
        sk_totem["monanim"] = "xx"
        sk_totem["ItemEffect"] = "1"
        sk_totem["reqlevel"] = "1"
        sk_totem["InGame"] = "1"
        sk_totem["HitShift"] = "8"
        sk_totem["*eol"] = "0"
        s_rows.append(sk_totem)

    if "Bar Stamina Reflex" not in by_name:
        max_sid = max(parse_int(r.get("*Id", "0"), 0) for r in s_rows)
        sk_reflex = {h: "" for h in s_headers}
        sk_reflex["skill"] = "Bar Stamina Reflex"
        sk_reflex["*Id"] = str(max_sid + 1)
        sk_reflex["srvdofunc"] = "30"
        sk_reflex["aurafilter"] = "3"
        sk_reflex["auratargetstate"] = "bar_stamina_reflex"
        sk_reflex["auralencalc"] = "2"
        sk_reflex["aurarangecalc"] = "(lvl==10)?9:((lvl==1)?6:4)"
        sk_reflex["aurastat1"] = ""
        sk_reflex["aurastatcalc1"] = ""
        sk_reflex["aurastat2"] = ""
        sk_reflex["aurastatcalc2"] = ""
        sk_reflex["auraevent1"] = "install"
        sk_reflex["auraeventfunc1"] = "3"
        sk_reflex["auraevent2"] = ""
        sk_reflex["auraeventfunc2"] = ""
        sk_reflex["auraevent3"] = ""
        sk_reflex["auraeventfunc3"] = ""
        sk_reflex["range"] = "none"
        sk_reflex["monanim"] = "xx"
        sk_reflex["ItemEffect"] = "1"
        sk_reflex["reqlevel"] = "1"
        sk_reflex["InGame"] = "1"
        sk_reflex["HitShift"] = "3"
        sk_reflex["EType"] = "stam"
        sk_reflex["EMin"] = "12"
        sk_reflex["EMinLev1"] = "4"
        sk_reflex["EMinLev2"] = "-6"
        sk_reflex["EMinLev3"] = "0"
        sk_reflex["EMinLev4"] = "0"
        sk_reflex["EMinLev5"] = "0"
        sk_reflex["EMax"] = "12"
        sk_reflex["EMaxLev1"] = "4"
        sk_reflex["EMaxLev2"] = "-6"
        sk_reflex["EMaxLev3"] = "0"
        sk_reflex["EMaxLev4"] = "0"
        sk_reflex["EMaxLev5"] = "0"
        sk_reflex["*eol"] = "0"
        s_rows.append(sk_reflex)

    # Test Step 1: Assassin Trap Charge Snapshot + Delayed Charge Consumption on Wake of Fire Sentry (Id 262)
    tot_charges = "(stat('progressive_damage'.accr)+stat('progressive_fire'.accr)+stat('progressive_lightning'.accr)+stat('progressive_cold'.accr)+stat('progressive_steal'.accr)+stat('progressive_other'.accr))"

    if "Ass Trap Charge Consume" not in by_name:
        max_sid = max(parse_int(r.get("*Id", "0"), 0) for r in s_rows)
        sk_consume = {h: "" for h in s_headers}
        sk_consume["skill"] = "Ass Trap Charge Consume"
        sk_consume["*Id"] = str(max_sid + 1)
        sk_consume["srvdofunc"] = "68"
        sk_consume["srvmissilea"] = "bladefury2"
        sk_consume["aurastate"] = "ass_trap_consume"
        sk_consume["auratargetstate"] = "ass_trap_consume"
        sk_consume["auralencalc"] = "10"
        sk_consume["range"] = "none"
        sk_consume["monanim"] = "xx"
        sk_consume["reqlevel"] = "1"
        sk_consume["InGame"] = "1"
        sk_consume["HitShift"] = "8"
        sk_consume["*eol"] = "0"
        s_rows.append(sk_consume)

    charge_up_states = {
        "Tiger Strike": "progressive_damage",
        "Fists of Fire": "progressive_fire",
        "Cobra Strike": "progressive_steal",
        "Claws of Thunder": "progressive_lightning",
        "Blades of Ice": "progressive_cold",
    }
    for sk_name, prog_st in charge_up_states.items():
        if sk_name in by_name:
            cu = by_name[sk_name]
            cu["srvstfunc"] = "23"
            cu["srvdofunc"] = "34"
            cu["aurastate"] = prog_st
            cu["aurastat1"] = prog_st
            cu["weapsel"] = ""
            cu["itypea1"] = "mele"
            cu["anim"] = "A1"
            cu["seqtrans"] = "A1"
            cu["seqnum"] = ""
            # Orb hold duration: 15 minutes (22500 frames @ 25 fps) -> auralencalc = par3 (kept under 16-bit frame limit)
            cu["Param3"] = "22500"
            cu["auralencalc"] = "par3"

    if "Tiger Strike" in by_name:
        ts = by_name["Tiger Strike"]
        ts["prgstack"] = ""
        ts["prgdam"] = ""
        ts["srvprgfunc1"] = "41"
        ts["cltprgfunc1"] = "15"
        ts["prgcalc1"] = "36"
        ts["srvprgfunc2"] = "41"
        ts["cltprgfunc2"] = "15"
        ts["prgcalc2"] = "36"
        ts["srvprgfunc3"] = "41"
        ts["cltprgfunc3"] = "15"
        ts["prgcalc3"] = "36"
        ts["srvmissilea"] = "inferno sentry 1"
        ts["cltmissilea"] = "inferno sentry 1"
        ts["srvmissileb"] = "inferno sentry 2"
        ts["cltmissileb"] = "inferno sentry 2"
        ts["srvmissilec"] = "progressive radius damage"
        ts["cltmissilec"] = "progressive radius damage"
        ts["Param1"] = "6"
        ts["Param2"] = "2"
        ts["calc1"] = (
            "par1 + 2*max(0,lvl-1) + 1*max(0,lvl-8) + 2*max(0,lvl-16) + 4*max(0,lvl-22) + 2*skill('Dragon Talon'.blvl) + 1*skill('Fire Trauma'.blvl)"
        )
        ts["*calc1 desc"] = "Held Charge Damage % per Orb"
        ts["calc2"] = (
            "((4 + 1*max(0,lvl-1) + 1*max(0,lvl-8) + 1*max(0,lvl-16) + 4*max(0,lvl-22) + 5*max(0,lvl-28)) * (100 + clc4)) / 100"
        )
        ts["*calc2 desc"] = "Charge 1 Shockwave Ring Min Physical Damage"
        ts["calc3"] = (
            "((8 + 2*max(0,lvl-1) + 1*max(0,lvl-8) + 2*max(0,lvl-16) + 7*max(0,lvl-22) + 8*max(0,lvl-28)) * (100 + clc4)) / 100"
        )
        ts["*calc3 desc"] = "Charge 1 Shockwave Ring Max Physical Damage"
        ts["calc4"] = (
            "12*skill('Dragon Talon'.blvl) + 6*skill('Fire Trauma'.blvl)"
        )
        ts["*calc4 desc"] = "Total Synergy Bonus (%)"
        ts["calc5"] = "5"
        ts["*calc5 desc"] = "Shockwave Ring Range in Frames (5 @ Vel 6 = 3.75 sub-tiles)"
        ts["calc6"] = (
            "((stat('progressive_damage'.accr) >= 3) ? 3 : ((stat('progressive_damage'.accr) == 2) ? 2 : 1)) * (100 + clc4) - 100"
        )
        ts["*calc6 desc"] = "Charge 1/2/3 Shockwave Ring Total Multiplier (%)"
        ts["aurastat2"] = "damagepercent"
        ts["aurastatcalc2"] = "clc1"
        ts["passivestate"] = ""
        ts["passivestat1"] = ""
        ts["passivecalc1"] = ""

    # Step 2: Tiger Strike (progressive_damage) <-> Shrapnel Sentry (Fire Trauma, Id 251)
    snap_ts = "max(stat('progressive_damage'.accr), stat('item_kickdamage'.accr))"
    ts_m = "skill('Tiger Strike'.blvl)"
    ss_c = "skill('Ass Trap Charge Consume'.blvl)"
    ss_trap_syn = "(skill('Shock Field'.blvl) + skill('Tiger Strike'.blvl))"

    if "Fire Trauma" in by_name:
        ft = by_name["Fire Trauma"]
        ft["srvstfunc"] = "39"
        ft["srvdofunc"] = "45"
        ft["cltdofunc"] = ""
        ft["srvmissile"] = ""
        ft["cltmissile"] = ""
        ft["lob"] = ""
        ft["dosound"] = ""
        ft["aurarangecalc"] = ""
        ft["stsound"] = "assassin_summon"
        ft["summon"] = "infernosentry"
        ft["pettype"] = "phystrap"
        ft["petmax"] = f"1 + (({ss_trap_syn} >= 10) ? 1 : 0) + (({ss_trap_syn} >= 25) ? 1 : 0)"
        ft["summode"] = "S1"
        ft["aurastate"] = "progressive_damage"
        ft["auralencalc"] = "12"
        ft["aurastat1"] = "item_kickdamage"
        ft["aurastatcalc1"] = snap_ts
        ft["aurastat2"] = ""
        ft["aurastatcalc2"] = ""
        ft["passivestat1"] = "item_pierce_damage_immunity"
        ft["passivecalc1"] = "stat('item_pierce_damage_immunity'.accr)"
        ft["passivestat2"] = "item_openwounds"
        ft["passivecalc2"] = f"({snap_ts} >= 3) ? 101 : 0"
        ft["passivestat3"] = "item_ignoretargetac"
        ft["passivecalc3"] = "1"
        ft["passivestat4"] = "tohit"
        ft["passivecalc4"] = "25000"
        ft["passivestat5"] = ""
        ft["passivecalc5"] = ""
        ft["sumskill1"] = "mon inferno sentry"
        ft["sumsk1calc"] = f"({snap_ts} >= 2) ? (9 + {ts_m} / 2) : 1"
        ft["sumskill2"] = "Fire Trauma"
        ft["sumsk2calc"] = "lvl"
        ft["sumskill3"] = "Tiger Strike"
        ft["sumsk3calc"] = ts_m
        ft["sumskill4"] = "Shock Field"
        ft["sumsk4calc"] = "skill('Shock Field'.blvl)"
        ft["sumskill5"] = "Ass Trap Charge Consume"
        ft["sumsk5calc"] = snap_ts
        ft["LineOfSight"] = "4"
        ft["leftskill"] = "0"
        ft["rightskill"] = "1"
        ft["minmana"] = "1"
        ft["manashift"] = "8"
        ft["mana"] = "11"
        ft["lvlmana"] = "0"
        ft["Param1"] = "11"
        ft["*Param1 Description"] = "# of shots"
        ft["HitShift"] = "8"
        ft["EType"] = ""
        ft["EMin"] = ""
        ft["EMinLev1"] = ""
        ft["EMinLev2"] = ""
        ft["EMinLev3"] = ""
        ft["EMinLev4"] = ""
        ft["EMinLev5"] = ""
        ft["EMax"] = ""
        ft["EMaxLev1"] = ""
        ft["EMaxLev2"] = ""
        ft["EMaxLev3"] = ""
        ft["EMaxLev4"] = ""
        ft["EMaxLev5"] = ""
        ft["EDmgSymPerCalc"] = ""
        ft["MinDam"] = "10"
        ft["MinLevDam1"] = "0"
        ft["MinLevDam2"] = "0"
        ft["MinLevDam3"] = "0"
        ft["MinLevDam4"] = "0"
        ft["MinLevDam5"] = "0"
        ft["MaxDam"] = "18"
        ft["MaxLevDam1"] = "0"
        ft["MaxLevDam2"] = "0"
        ft["MaxLevDam3"] = "0"
        ft["MaxLevDam4"] = "0"
        ft["MaxLevDam5"] = "0"
        ft["calc1"] = "100 + 10*max(0,lvl-1) + 6*max(0,lvl-8) + 16*max(0,lvl-16) + 30*max(0,lvl-22)"
        ft["*calc1 desc"] = "Base Physical Damage Level Ramp (%)"
        ft["calc2"] = ""
        ft["*calc2 desc"] = ""
        ft["calc3"] = "4*skill('Shock Field'.blvl) + 4*skill('Tiger Strike'.blvl)"
        ft["*calc3 desc"] = "Total Synergy Bonus (%)"
        ft["DmgSymPerCalc"] = "(clc1 * (100 + clc3)) / 100 - 100"
        ft["aitype"] = "3"

    ss_shots_calc = f"par8 + (({ss_c} >= 1) ? (6 + {ts_m} / 4) : 0)"
    if "mon inferno sentry" in by_name:
        mis = by_name["mon inferno sentry"]
        mis["srvstfunc"] = ""
        mis["srvdofunc"] = ""
        mis["srvmissile"] = "bladefragment3"
        mis["srvmissilea"] = ""
        mis["cltstfunc"] = ""
        mis["cltdofunc"] = ""
        mis["cltmissile"] = "bladefragment3"
        mis["cltmissilea"] = ""
        mis["cltmissileb"] = ""
        mis["cltcalc1"] = ""
        mis["anim"] = "SQ"
        mis["seqtrans"] = "SQ"
        mis["monanim"] = "S2"
        mis["UseAttackRate"] = "1"
        mis["Param8"] = "11"
        mis["calc1"] = "skill('Fire Trauma'.blvl)"
        mis["*calc1 desc"] = "Shrapnel Sentry Level"
        mis["calc2"] = "100 + 10*max(0,clc1-1) + 6*max(0,clc1-8) + 16*max(0,clc1-16) + 30*max(0,clc1-22)"
        mis["*calc2 desc"] = "Base Physical Damage Level Ramp (%)"
        mis["calc3"] = "100 + 4*(skill('Shock Field'.blvl) + skill('Tiger Strike'.blvl))"
        mis["*calc3 desc"] = "Total Synergy Multiplier (%)"
        mis["calc4"] = ss_shots_calc

    if "tiger strike" in by_desc:
        ts_d = by_desc["tiger strike"]
        ts_d["descdam"] = "1"
        ts_d["descline1"] = "75"
        ts_d["desctexta1"] = "ModTigerStrikeOrb3"
        ts_d["desccalca1"] = "3*clc2"
        ts_d["desccalcb1"] = "3*clc3"
        ts_d["descline2"] = "75"
        ts_d["desctexta2"] = "ModTigerStrikeOrb2"
        ts_d["desccalca2"] = "2*clc2"
        ts_d["desccalcb2"] = "2*clc3"
        ts_d["descline3"] = "75"
        ts_d["desctexta3"] = "ModTigerStrikeOrb1"
        ts_d["desccalca3"] = "clc2"
        ts_d["desccalcb3"] = "clc3"
        ts_d["descline4"] = "74"
        ts_d["desctexta4"] = "ModTigerStrikeHoldBuff"
        ts_d["desccalca4"] = "clc1"
        ts_d["descline5"] = "74"
        ts_d["desctexta5"] = "StrSkill22"
        ts_d["desccalca5"] = "toht"
        ts_d["dsc3line1"] = "40"
        ts_d["dsc3texta1"] = "Sksyn"
        ts_d["dsc3textb1"] = "Skillname255"
        ts_d["dsc3calca1"] = "2"
        ts_d["dsc3line2"] = "76"
        ts_d["dsc3texta2"] = "Damplev"
        ts_d["dsc3textb2"] = "Skillname256"
        ts_d["dsc3calca2"] = "12"
        ts_d["dsc3line3"] = "76"
        ts_d["dsc3texta3"] = "Damplev"
        ts_d["dsc3textb3"] = "Skillname252"
        ts_d["dsc3calca3"] = "6"
        ts_d["dsc3line4"] = ""
        ts_d["dsc3texta4"] = ""
        ts_d["dsc3textb4"] = ""
        ts_d["dsc3calca4"] = ""

    if "fire trauma" in by_desc:
        ft_d = by_desc["fire trauma"]
        ft_d["descdam"] = "5"
        ft_d["descline1"] = "75"
        ft_d["desctexta1"] = "StrSkill4"
        ft_d["desccalca1"] = "pnma"
        ft_d["desccalcb1"] = "pxma"
        ft_d["descline2"] = ""
        ft_d["desctexta2"] = ""
        ft_d["desccalca2"] = ""
        ft_d["desccalcb2"] = ""
        ft_d["dsc2line1"] = "36"
        ft_d["dsc2texta1"] = "StrSkill3"
        ft_d["dsc2textb1"] = ""
        ft_d["dsc2calca1"] = "usmc"
        ft_d["dsc2calcb1"] = "256"
        ft_d["dsc2line2"] = "74"
        ft_d["dsc2texta2"] = "ESkillShoots"
        ft_d["dsc2textb2"] = ""
        ft_d["dsc2calca2"] = "par1"
        ft_d["dsc2calcb2"] = ""
        ft_d["dsc2line3"] = "74"
        ft_d["dsc2texta3"] = "ModShrapnelSentryMaxTraps"
        ft_d["dsc2calca3"] = f"1 + (({ss_trap_syn} >= 10) ? 1 : 0) + (({ss_trap_syn} >= 25) ? 1 : 0)"
        ft_d["dsc2line4"] = "74"
        ft_d["dsc2texta4"] = "ModFireSentryChargedShots"
        ft_d["dsc2calca4"] = f"par1 + 6 + {ts_m} / 4"
        ft_d["dsc3line1"] = "40"
        ft_d["dsc3texta1"] = "Sksyn"
        ft_d["dsc3textb1"] = "Skillname252"
        ft_d["dsc3calca1"] = "2"
        ft_d["dsc3line2"] = "76"
        ft_d["dsc3texta2"] = "Damplev"
        ft_d["dsc3textb2"] = "Skillname257"
        ft_d["dsc3calca2"] = "4"
        ft_d["dsc3line3"] = "76"
        ft_d["dsc3texta3"] = "Damplev"
        ft_d["dsc3textb3"] = "Skillname255"
        ft_d["dsc3calca3"] = "4"
        ft_d["dsc3line4"] = ""
        ft_d["dsc3texta4"] = ""
        ft_d["dsc3textb4"] = ""
        ft_d["dsc3calca4"] = ""
        ft_d["dsc3line5"] = ""
        ft_d["dsc3texta5"] = ""
        ft_d["dsc3textb5"] = ""
        ft_d["dsc3calca5"] = ""
        ft_d["dsc3line6"] = ""
        ft_d["dsc3texta6"] = ""
        ft_d["dsc3textb6"] = ""
        ft_d["dsc3calca6"] = ""

    if "Fists of Fire" in by_name:
        fof = by_name["Fists of Fire"]
        fof["prgstack"] = ""
        fof["prgdam"] = ""
        fof["srvprgfunc1"] = "39"
        fof["cltprgfunc1"] = "9"
        fof["prgcalc1"] = "6"
        fof["srvprgfunc2"] = "39"
        fof["cltprgfunc2"] = "9"
        fof["prgcalc2"] = "9"
        fof["srvprgfunc3"] = "40"
        fof["cltprgfunc3"] = "14"
        fof["prgcalc3"] = "9"
        fof["srvmissilea"] = "fistsoffireexplode"
        fof["cltmissilea"] = "fistsoffireexplode"
        fof["srvmissileb"] = "fistsoffirefirewall"
        fof["cltmissileb"] = "fistsoffirefirewall"
        fof["srvmissilec"] = "royalstrikemeteorcenter"
        fof["cltmissilec"] = "royalstrikemeteorcenter"
        fof["calc1"] = "9"
        fof["*calc1 desc"] = "Meteor Explosion Radius"
        fof["calc2"] = "1"
        fof["*calc2 desc"] = "Min Fire Damage per Orb"
        fof["calc3"] = (
            "((2 + (lvl-1)/2 + max(0,lvl-16) + 3*max(0,lvl-20) + 5*max(0,lvl-26)) * (100 + clc4)) / 100"
        )
        fof["*calc3 desc"] = "Min Fire Damage per Orb (Max = 2 * clc3)"
        fof["calc4"] = (
            "12*skill('Wake of Fire Sentry'.blvl) + 6*skill('Blades of Ice'.blvl) + 6*skill('Claws of Thunder'.blvl)"
        )
        fof["*calc4 desc"] = "Total Synergy Bonus (%)"
        fof["EType"] = ""
        fof["EMin"] = ""
        fof["EMinLev1"] = ""
        fof["EMinLev2"] = ""
        fof["EMinLev3"] = ""
        fof["EMinLev4"] = ""
        fof["EMinLev5"] = ""
        fof["EMax"] = ""
        fof["EMaxLev1"] = ""
        fof["EMaxLev2"] = ""
        fof["EMaxLev3"] = ""
        fof["EMaxLev4"] = ""
        fof["EMaxLev5"] = ""
        fof["EDmgSymPerCalc"] = ""
        fof["aurastat2"] = "item_slash_damage"
        fof["aurastatcalc2"] = "clc3"
        fof["passivestate"] = "ass_fof_passive"
        fof["passivestat1"] = "item_absorb_slash"
        fof["passivecalc1"] = "1"
        fof["passivestat2"] = ""
        fof["passivecalc2"] = ""
        fof["aurastat3"] = ""
        fof["aurastatcalc3"] = ""
        fof["aurastat4"] = ""
        fof["aurastatcalc4"] = ""

    # Step 1: Fists of Fire / Flamestrike (progressive_fire) <-> Wake of Fire Sentry / Fire Sentry (Id 262)
    snap_fof = "max(stat('progressive_fire'.accr), stat('item_kickdamage'.accr))"
    fof_m = "skill('Fists of Fire'.blvl)"
    wof_c = "skill('Ass Trap Charge Consume'.blvl)"
    wof_trap_syn = "(skill('Death Sentry'.blvl) + skill('Lightning Sentry'.blvl))"

    if "Wake of Fire Sentry" in by_name:
        wof = by_name["Wake of Fire Sentry"]
        wof["srvstfunc"] = "39"
        wof["pettype"] = "firetrap"
        wof["petmax"] = f"1 + (({wof_trap_syn} >= 10) ? 1 : 0) + (({wof_trap_syn} >= 25) ? 1 : 0)"
        wof["aurastate"] = "progressive_fire"
        wof["auralencalc"] = "12"
        wof["aurastat1"] = "item_kickdamage"
        wof["aurastatcalc1"] = snap_fof
        wof["aurastat2"] = ""
        wof["aurastatcalc2"] = ""
        wof["passivecalc2"] = "stat('passive_fire_pierce'.accr)"
        wof["passivecalc3"] = "stat('passive_fire_mastery'.accr)"
        wof["passivestat4"] = ""
        wof["passivecalc4"] = ""
        wof["sumskill1"] = "Wake Of Destruction Sentry"
        wof["sumsk1calc"] = f"({snap_fof} >= 2) ? (9 + {fof_m} / 2) : 1"
        wof["sumskill2"] = "Wake of Fire Sentry"
        wof["sumsk2calc"] = "lvl"
        wof["sumskill3"] = "Fists of Fire"
        wof["sumsk3calc"] = fof_m
        wof["sumskill4"] = "Fire Trauma"
        wof["sumsk4calc"] = "skill('Death Sentry'.blvl) + skill('Lightning Sentry'.blvl)"
        wof["sumskill5"] = "Ass Trap Charge Consume"
        wof["sumsk5calc"] = snap_fof
        wof["EMin"] = "14"
        wof["EMinLev1"] = "0"
        wof["EMinLev2"] = "0"
        wof["EMinLev3"] = "0"
        wof["EMinLev4"] = "0"
        wof["EMinLev5"] = "0"
        wof["EMax"] = "24"
        wof["EMaxLev1"] = "0"
        wof["EMaxLev2"] = "0"
        wof["EMaxLev3"] = "0"
        wof["EMaxLev4"] = "0"
        wof["EMaxLev5"] = "0"
        wof["calc1"] = "100 + 10*max(0,lvl-1) + 6*max(0,lvl-8) + 18*max(0,lvl-16) + 36*max(0,lvl-22)"
        wof["*calc1 desc"] = "Base Fire Damage Level Ramp (%)"
        wof["calc2"] = ""
        wof["*calc2 desc"] = ""
        wof["calc3"] = "12*skill('Fists of Fire'.blvl) + 6*skill('Death Sentry'.blvl) + 6*skill('Lightning Sentry'.blvl)"
        wof["*calc3 desc"] = "Total Synergy Bonus (%)"
        wof["EDmgSymPerCalc"] = "(clc1 * (100 + clc3)) / 100 - 100"

    if "fists of fire" in by_desc:
        fof_d = by_desc["fists of fire"]
        fof_d["descdam"] = "1"
        fof_d["p1dmelem"] = ""
        fof_d["p1dmmin"] = ""
        fof_d["p1dmmax"] = ""
        fof_d["p2dmelem"] = ""
        fof_d["p2dmmin"] = ""
        fof_d["p2dmmax"] = ""
        fof_d["p3dmelem"] = ""
        fof_d["p3dmmin"] = ""
        fof_d["p3dmmax"] = ""
        fof_d["descmissile1"] = "fistsoffireexplode"
        fof_d["descmissile2"] = "fistsoffirefirewall"
        fof_d["descmissile3"] = "royalstrikemeteor"
        fof_d["descline1"] = "75"
        fof_d["desctexta1"] = "ModFistsOfFireOrb3"
        fof_d["desccalca1"] = "m3en"
        fof_d["desccalcb1"] = "m3ex"
        fof_d["descline2"] = "75"
        fof_d["desctexta2"] = "ModFistsOfFireOrb2"
        fof_d["desccalca2"] = "m2en*25/8"
        fof_d["desccalcb2"] = "m2ex*25/8"
        fof_d["descline3"] = "75"
        fof_d["desctexta3"] = "ModFistsOfFireOrb1"
        fof_d["desccalca3"] = "m1en"
        fof_d["desccalcb3"] = "m1ex"
        fof_d["descline4"] = "75"
        fof_d["desctexta4"] = "ModFistsOfFireHoldBuff"
        fof_d["desccalca4"] = "clc3"
        fof_d["desccalcb4"] = "2*clc3"
        fof_d["descline5"] = "74"
        fof_d["desctexta5"] = "StrSkill22"
        fof_d["desccalca5"] = "toht"
        fof_d["dsc3line1"] = "40"
        fof_d["dsc3texta1"] = "Sksyn"
        fof_d["dsc3textb1"] = "Skillname260"
        fof_d["dsc3calca1"] = "2"
        fof_d["dsc3line2"] = "76"
        fof_d["dsc3texta2"] = "Firedplev"
        fof_d["dsc3textb2"] = "Skillname263"
        fof_d["dsc3calca2"] = "12"
        fof_d["dsc3line3"] = "76"
        fof_d["dsc3texta3"] = "Firedplev"
        fof_d["dsc3textb3"] = "Skillname275"
        fof_d["dsc3calca3"] = "6"
        fof_d["dsc3line4"] = "76"
        fof_d["dsc3texta4"] = "Firedplev"
        fof_d["dsc3textb4"] = "Skillname270"
        fof_d["dsc3calca4"] = "6"

    if "wake of fire sentry" in by_desc:
        wof_d = by_desc["wake of fire sentry"]
        wof_d["dsc2line3"] = "74"
        wof_d["dsc2texta3"] = "ModFireSentryMaxTraps"
        wof_d["dsc2calca3"] = f"1 + (({wof_trap_syn} >= 10) ? 1 : 0) + (({wof_trap_syn} >= 25) ? 1 : 0)"
        wof_d["dsc2line4"] = "74"
        wof_d["dsc2texta4"] = "ModFireSentryChargedShots"
        wof_d["dsc2calca4"] = f"par1 + 3 + {fof_m} / 10"
        wof_d["dsc3line1"] = "40"
        wof_d["dsc3texta1"] = "Sksyn"
        wof_d["dsc3textb1"] = "Skillname263"
        wof_d["dsc3calca1"] = "2"
        wof_d["dsc3line2"] = "76"
        wof_d["dsc3texta2"] = "Firedplev"
        wof_d["dsc3textb2"] = "Skillname260"
        wof_d["dsc3calca2"] = "12"
        wof_d["dsc3line3"] = "76"
        wof_d["dsc3texta3"] = "Firedplev"
        wof_d["dsc3textb3"] = "Skillname277"
        wof_d["dsc3calca3"] = "6"
        wof_d["dsc3line4"] = "76"
        wof_d["dsc3texta4"] = "Firedplev"
        wof_d["dsc3textb4"] = "Skillname272"
        wof_d["dsc3calca4"] = "6"

    wof_shots_calc = f"par8 + (({wof_c} >= 1) ? (3 + {fof_m} / 10) : 0)"
    if "Wake Of Destruction Sentry" in by_name:
        wods = by_name["Wake Of Destruction Sentry"]
        wods["srvdofunc"] = ""
        wods["srvmissile"] = "vampirefireball"
        wods["srvmissilea"] = ""
        wods["cltdofunc"] = ""
        wods["cltmissile"] = "vampirefireball"
        wods["cltmissilea"] = ""
        wods["aurafilter"] = ""
        wods["auratargetstate"] = ""
        wods["auralencalc"] = ""
        wods["aurarangecalc"] = f"({wof_c} >= 3) ? 6 : 0"
        wods["calc1"] = "skill('Wake of Fire Sentry'.blvl)"
        wods["*calc1 desc"] = "Wake of Fire Sentry Level"
        wods["calc2"] = "100 + 10*max(0,clc1-1) + 6*max(0,clc1-8) + 18*max(0,clc1-16) + 36*max(0,clc1-22)"
        wods["*calc2 desc"] = "Base Fire Damage Level Ramp (%)"
        wods["calc3"] = "100 + 12*skill('Fists of Fire'.blvl) + 6*skill('Fire Trauma'.blvl)"
        wods["*calc3 desc"] = "Total Synergy Multiplier (%)"
        wods["calc4"] = wof_shots_calc

    if "VampireFireball" in by_name:
        vfb_sk = by_name["VampireFireball"]
        vfb_sk["srvmissile"] = "desertfireball"
        vfb_sk["cltmissile"] = "desertfireball"

    # Step 3: Cobra Strike (progressive_steal, Id 265) <-> Soul Siphon Sentry (Charged Bolt Sentry, Id 261)
    for tier_idx, hex_name in ((1, "Ass Cobra Hex 1"), (2, "Ass Cobra Hex 2"), (3, "Ass Cobra Hex 3")):
        if hex_name not in by_name:
            max_sid = max(parse_int(r.get("*Id", "0"), 0) for r in s_rows)
            sk_hex = {h: "" for h in s_headers}
            sk_hex["skill"] = hex_name
            sk_hex["*Id"] = str(max_sid + 1)
            sk_hex["aurafilter"] = "98304"
            sk_hex["auratargetstate"] = "ass_cobra_debuff"
            sk_hex["auralencalc"] = "250 + 15 * skill('Cobra Strike'.blvl)"
            sk_hex["aurastat1"] = "armorclass"
            sk_hex["aurastatcalc1"] = f"-{tier_idx} * skill('Cobra Strike'.clc2)"
            sk_hex["aurastat2"] = "skill_armor_percent"
            sk_hex["aurastatcalc2"] = f"-{tier_idx} * skill('Cobra Strike'.clc3)"
            sk_hex["range"] = "none"
            sk_hex["monanim"] = "xx"
            sk_hex["reqlevel"] = "1"
            sk_hex["InGame"] = "1"
            sk_hex["HitShift"] = "8"
            sk_hex["*eol"] = "0"
            s_rows.append(sk_hex)
            by_name[hex_name] = sk_hex

    if "Cobra Strike" in by_name:
        cs = by_name["Cobra Strike"]
        cs["prgstack"] = ""
        cs["prgdam"] = "2"
        cs["srvprgfunc1"] = "41"
        cs["cltprgfunc1"] = "15"
        cs["prgcalc1"] = "36"
        cs["srvprgfunc2"] = "41"
        cs["cltprgfunc2"] = "15"
        cs["prgcalc2"] = "36"
        cs["srvprgfunc3"] = "41"
        cs["cltprgfunc3"] = "15"
        cs["prgcalc3"] = "36"
        cs["srvmissilea"] = "unholybolt2"
        cs["cltmissilea"] = "unholybolt2"
        cs["srvmissileb"] = "unholybolt3"
        cs["cltmissileb"] = "unholybolt3"
        cs["srvmissilec"] = "unholybolt4"
        cs["cltmissilec"] = "unholybolt4"
        cs["Param1"] = "45"
        cs["Param2"] = "6"
        cs["calc1"] = "ln12 + 3*skill('Dragon Claw'.blvl) + 2*skill('Charged Bolt Sentry'.blvl)"
        cs["*calc1 desc"] = "Finisher Life & Mana Steal %"
        cs["calc2"] = (
            "((50 + 15*max(0,lvl-1) + 25*max(0,lvl-8) + 40*max(0,lvl-16) + 55*max(0,lvl-22)) * (100 + clc4)) / 100"
        )
        cs["*calc2 desc"] = "Soul-Hex Wave Flat Defense Shred per Orb"
        cs["calc3"] = "10 + lvl / 2"
        cs["*calc3 desc"] = "Soul-Hex Wave % Defense Shred per Orb"
        cs["calc4"] = "12*skill('Dragon Claw'.blvl) + 6*skill('Charged Bolt Sentry'.blvl)"
        cs["*calc4 desc"] = "Total Synergy Bonus (%)"
        cs["aurastat2"] = "item_damagetargetac"
        cs["aurastatcalc2"] = "-50"
        cs["aurastat3"] = "progressive_tohit"
        cs["aurastatcalc3"] = "par4"
        cs["passivestate"] = ""
        cs["passivestat1"] = ""
        cs["passivecalc1"] = ""

    if "cobra strike" in by_desc:
        cs_d = by_desc["cobra strike"]
        cs_d["descdam"] = "5"
        cs_d["descatt"] = "1"
        cs_d["descline1"] = "75"
        cs_d["desctexta1"] = "ModCobraStrikeOrb3"
        cs_d["desccalca1"] = "2*clc1"
        cs_d["desccalcb1"] = "3*clc2"
        cs_d["descline2"] = "75"
        cs_d["desctexta2"] = "ModCobraStrikeOrb2"
        cs_d["desccalca2"] = "clc1"
        cs_d["desccalcb2"] = "2*clc2"
        cs_d["descline3"] = "75"
        cs_d["desctexta3"] = "ModCobraStrikeOrb1"
        cs_d["desccalca3"] = "clc1"
        cs_d["desccalcb3"] = "clc2"
        cs_d["descline4"] = "74"
        cs_d["desctexta4"] = "ModCobraStrikeHoldBuff"
        cs_d["desccalca4"] = "50"
        cs_d["descline5"] = "74"
        cs_d["desctexta5"] = "StrSkill22"
        cs_d["desccalca5"] = "toht"
        cs_d["dsc3line1"] = "40"
        cs_d["dsc3texta1"] = "Sksyn"
        cs_d["dsc3textb1"] = "Skillname266"
        cs_d["dsc3calca1"] = "2"
        cs_d["dsc3line2"] = "76"
        cs_d["dsc3texta2"] = "ModCobraSynergyPerLev"
        cs_d["dsc3textb2"] = "Skillname261"
        cs_d["dsc3calca2"] = "12"
        cs_d["dsc3line3"] = "76"
        cs_d["dsc3texta3"] = "ModCobraSynergyPerLev"
        cs_d["dsc3textb3"] = "Skillname262"
        cs_d["dsc3calca3"] = "6"
        cs_d["dsc3line4"] = ""
        cs_d["dsc3texta4"] = ""
        cs_d["dsc3textb4"] = ""
        cs_d["dsc3calca4"] = ""

    snap_cs = "max(stat('progressive_steal'.accr), stat('item_kickdamage'.accr))"
    cs_m = "skill('Cobra Strike'.blvl)"
    cs_c = "skill('Ass Trap Charge Consume'.blvl)"
    cs_trap_syn = "(skill('Fire Trauma'.blvl) + skill('Cobra Strike'.blvl))"

    if "Charged Bolt Sentry" in by_name:
        cbs = by_name["Charged Bolt Sentry"]
        cbs["srvstfunc"] = "39"
        cbs["srvdofunc"] = "45"
        cbs["pettype"] = "miasmatrap"
        cbs["petmax"] = f"1 + (({cs_trap_syn} >= 10) ? 1 : 0) + (({cs_trap_syn} >= 25) ? 1 : 0)"
        cbs["aurastate"] = "progressive_steal"
        cbs["auralencalc"] = "12"
        cbs["aurastat1"] = "item_kickdamage"
        cbs["aurastatcalc1"] = snap_cs
        cbs["aurastat2"] = ""
        cbs["aurastatcalc2"] = ""
        cbs["passivestat1"] = "item_pierce_magic_immunity"
        cbs["passivecalc1"] = "stat('item_pierce_magic_immunity'.accr)"
        cbs["passivestat2"] = "passive_mag_pierce"
        cbs["passivecalc2"] = "stat('passive_mag_pierce'.accr)"
        cbs["passivestat3"] = "passive_mag_mastery"
        cbs["passivecalc3"] = "stat('passive_mag_mastery'.accr)"
        cbs["passivestat4"] = ""
        cbs["passivecalc4"] = ""
        cbs["sumskill1"] = "BoltSentry"
        cbs["sumsk1calc"] = f"({snap_cs} >= 3) ? 10 : (({snap_cs} == 2) ? 2 : 1)"
        cbs["sumskill2"] = "Charged Bolt Sentry"
        cbs["sumsk2calc"] = "lvl"
        cbs["sumskill3"] = "Cobra Strike"
        cbs["sumsk3calc"] = cs_m
        cbs["sumskill4"] = "Fire Trauma"
        cbs["sumsk4calc"] = "skill('Fire Trauma'.blvl)"
        cbs["sumskill5"] = "Ass Trap Charge Consume"
        cbs["sumsk5calc"] = snap_cs
        cbs["Param1"] = "9"
        cbs["*Param1 Description"] = "# of shots"
        cbs["HitShift"] = "8"
        cbs["EType"] = "mag"
        cbs["EMin"] = "32"
        cbs["EMinLev1"] = "0"
        cbs["EMinLev2"] = "0"
        cbs["EMinLev3"] = "0"
        cbs["EMinLev4"] = "0"
        cbs["EMinLev5"] = "0"
        cbs["EMax"] = "50"
        cbs["EMaxLev1"] = "0"
        cbs["EMaxLev2"] = "0"
        cbs["EMaxLev3"] = "0"
        cbs["EMaxLev4"] = "0"
        cbs["EMaxLev5"] = "0"
        cbs["calc1"] = "100 + 10*max(0,lvl-1) + 6*max(0,lvl-8) + 14*max(0,lvl-16) + 26*max(0,lvl-22)"
        cbs["*calc1 desc"] = "Base Magic Damage Level Ramp (%)"
        cbs["calc3"] = "15*skill('Cobra Strike'.blvl) + 9*skill('Fire Trauma'.blvl)"
        cbs["*calc3 desc"] = "Total Synergy Bonus (%)"
        cbs["calc4"] = ""
        cbs["EDmgSymPerCalc"] = "(clc1 * (100 + clc3)) / 100 - 100"

    cs_shots_calc = f"par8 + (({cs_c} >= 1) ? (5 + {cs_m} / 4) : 0)"
    if "BoltSentry" in by_name:
        bs_sk = by_name["BoltSentry"]
        bs_sk["srvstfunc"] = ""
        bs_sk["srvdofunc"] = ""
        bs_sk["srvmissile"] = "sentrychargedbolt"
        bs_sk["srvmissilea"] = ""
        bs_sk["cltstfunc"] = ""
        bs_sk["cltdofunc"] = ""
        bs_sk["cltmissile"] = "sentrychargedbolt"
        bs_sk["cltmissilea"] = ""
        bs_sk["anim"] = "SQ"
        bs_sk["seqtrans"] = "SQ"
        bs_sk["monanim"] = "S2"
        bs_sk["UseAttackRate"] = "1"
        bs_sk["aurafilter"] = "3"
        bs_sk["auratargetstate"] = "lifetap"
        bs_sk["auralencalc"] = f"125 + 10 * {cs_m}"
        bs_sk["aurarangecalc"] = "(lvl >= 3) ? 5 : 0"
        bs_sk["auraevent1"] = "damagedinmelee"
        bs_sk["auraeventfunc1"] = "5"
        bs_sk["auraevent2"] = "damagedbymissile"
        bs_sk["auraeventfunc2"] = "5"
        bs_sk["prgoverlay"] = "steallife"
        bs_sk["Param5"] = "50"
        bs_sk["Param6"] = "0"
        bs_sk["Param8"] = "9"
        bs_sk["calc1"] = "ln56"
        bs_sk["*calc1 desc"] = "Damage % returned as healing to attacker"
        bs_sk["calc2"] = (
            "100 + 10*max(0,skill('Charged Bolt Sentry'.blvl)-1) + 6*max(0,skill('Charged Bolt Sentry'.blvl)-8)"
            " + 14*max(0,skill('Charged Bolt Sentry'.blvl)-16) + 26*max(0,skill('Charged Bolt Sentry'.blvl)-22)"
        )
        bs_sk["*calc2 desc"] = "Base Magic Damage Level Ramp (%)"
        bs_sk["calc3"] = "100 + 15*skill('Cobra Strike'.blvl) + 9*skill('Fire Trauma'.blvl)"
        bs_sk["*calc3 desc"] = "Total Synergy Multiplier (%)"
        bs_sk["calc4"] = cs_shots_calc

    if "charged bolt sentry" in by_desc:
        cbs_d = by_desc["charged bolt sentry"]
        cbs_d["descdam"] = "5"
        cbs_d["descline1"] = "75"
        cbs_d["desctexta1"] = "StrSkill39"
        cbs_d["desccalca1"] = "enma"
        cbs_d["desccalcb1"] = "exma"
        cbs_d["descline2"] = ""
        cbs_d["desctexta2"] = ""
        cbs_d["desccalca2"] = ""
        cbs_d["desccalcb2"] = ""
        cbs_d["dsc2line1"] = "36"
        cbs_d["dsc2texta1"] = "StrSkill3"
        cbs_d["dsc2textb1"] = ""
        cbs_d["dsc2calca1"] = "usmc"
        cbs_d["dsc2calcb1"] = "256"
        cbs_d["dsc2line2"] = "74"
        cbs_d["dsc2texta2"] = "ESkillShoots"
        cbs_d["dsc2textb2"] = ""
        cbs_d["dsc2calca2"] = "par1"
        cbs_d["dsc2calcb2"] = ""
        cbs_d["dsc2line3"] = "74"
        cbs_d["dsc2texta3"] = "ModSoulSiphonMaxTraps"
        cbs_d["dsc2calca3"] = f"1 + (({cs_trap_syn} >= 10) ? 1 : 0) + (({cs_trap_syn} >= 25) ? 1 : 0)"
        cbs_d["dsc2line4"] = "74"
        cbs_d["dsc2texta4"] = "ModFireSentryChargedShots"
        cbs_d["dsc2calca4"] = f"par1 + 5 + {cs_m} / 4"
        cbs_d["dsc3line1"] = "40"
        cbs_d["dsc3texta1"] = "Sksyn"
        cbs_d["dsc3textb1"] = "Skillname262"
        cbs_d["dsc3calca1"] = "2"
        cbs_d["dsc3line2"] = "76"
        cbs_d["dsc3texta2"] = "Magdplev"
        cbs_d["dsc3textb2"] = "Skillname266"
        cbs_d["dsc3calca2"] = "15"
        cbs_d["dsc3line3"] = "76"
        cbs_d["dsc3texta3"] = "Magdplev"
        cbs_d["dsc3textb3"] = "Skillname252"
        cbs_d["dsc3calca3"] = "9"
        cbs_d["dsc3line4"] = ""
        cbs_d["dsc3texta4"] = ""
        cbs_d["dsc3textb4"] = ""
        cbs_d["dsc3calca4"] = ""
        cbs_d["dsc3line5"] = ""
        cbs_d["dsc3texta5"] = ""
        cbs_d["dsc3textb5"] = ""
        cbs_d["dsc3calca5"] = ""
        cbs_d["dsc3calcb5"] = ""

    # Step 5: Claws of Thunder (progressive_lightning, Id 269) <-> Lightning Sentry (Id 271)
    if "Claws of Thunder" in by_name:
        cot = by_name["Claws of Thunder"]
        cot["prgstack"] = ""
        cot["prgdam"] = ""
        cot["srvprgfunc1"] = "37"
        cot["cltprgfunc1"] = "11"
        cot["prgcalc1"] = "max(4, 8 - lvl / 5)"
        cot["srvprgfunc2"] = "36"
        cot["cltprgfunc2"] = "10"
        cot["prgcalc2"] = ""
        cot["srvprgfunc3"] = "143"
        cot["cltprgfunc3"] = "83"
        cot["prgcalc3"] = "0"
        cot["srvmissilea"] = "clawsofthunderbolt"
        cot["cltmissilea"] = "clawsofthunderbolt"
        cot["srvmissileb"] = "clawsofthundernova"
        cot["cltmissileb"] = "clawsofthundernova"
        cot["srvmissilec"] = "royalstrikechainlightning"
        cot["cltmissilec"] = "royalstrikechainlightning"
        cot["aurarangecalc"] = "5 + lvl / 4"
        cot["calc1"] = "max(4, 8 - lvl / 5)"
        cot["*calc1 desc"] = "Charged Bolt Spread Step (64 / clc1 bolts)"
        cot["calc2"] = "64 / clc1"
        cot["*calc2 desc"] = "Charge 1 Finisher Charged Bolt Count"
        cot["calc3"] = (
            "((10 + 2*max(0,lvl-1) + 2*max(0,lvl-16) + 8*max(0,lvl-20) + 14*max(0,lvl-26)) * (100 + clc4)) / 100"
        )
        cot["*calc3 desc"] = "Held Max Lightning Damage per Orb (Min = +1, Max = clc3)"
        cot["calc4"] = (
            "12*skill('Lightning Sentry'.blvl) + 6*skill('Fists of Fire'.blvl) + 6*skill('Blades of Ice'.blvl)"
        )
        cot["*calc4 desc"] = "Total Synergy Bonus (%)"
        cot["EType"] = ""
        cot["EMin"] = ""
        cot["EMinLev1"] = ""
        cot["EMinLev2"] = ""
        cot["EMinLev3"] = ""
        cot["EMinLev4"] = ""
        cot["EMinLev5"] = ""
        cot["EMax"] = ""
        cot["EMaxLev1"] = ""
        cot["EMaxLev2"] = ""
        cot["EMaxLev3"] = ""
        cot["EMaxLev4"] = ""
        cot["EMaxLev5"] = ""
        cot["EDmgSymPerCalc"] = ""
        cot["aurastat2"] = "item_thrust_damage_percent"
        cot["aurastatcalc2"] = "clc3"
        cot["aurastat3"] = ""
        cot["aurastatcalc3"] = ""
        cot["aurastat4"] = ""
        cot["aurastatcalc4"] = ""
        cot["passivestate"] = "ass_cot_passive"
        cot["passivestat1"] = "item_absorb_thrust"
        cot["passivecalc1"] = "1"
        cot["passivestat2"] = "lightmindam"
        cot["passivecalc2"] = "1"

    if "claws of thunder" in by_desc:
        cot_d = by_desc["claws of thunder"]
        cot_d["descdam"] = "1"
        cot_d["p1dmelem"] = ""
        cot_d["p1dmmin"] = ""
        cot_d["p1dmmax"] = ""
        cot_d["p2dmelem"] = ""
        cot_d["p2dmmin"] = ""
        cot_d["p2dmmax"] = ""
        cot_d["p3dmelem"] = ""
        cot_d["p3dmmin"] = ""
        cot_d["p3dmmax"] = ""
        cot_d["descmissile1"] = "clawsofthunderbolt"
        cot_d["descmissile2"] = "clawsofthundernova"
        cot_d["descmissile3"] = "royalstrikechainlightning"
        cot_d["descline1"] = "75"
        cot_d["desctexta1"] = "ModClawsOfThunderOrb3"
        cot_d["desccalca1"] = "m3en"
        cot_d["desccalcb1"] = "m3ex"
        cot_d["descline2"] = "75"
        cot_d["desctexta2"] = "ModClawsOfThunderOrb2"
        cot_d["desccalca2"] = "m2en"
        cot_d["desccalcb2"] = "m2ex"
        cot_d["descline3"] = "75"
        cot_d["desctexta3"] = "ModClawsOfThunderOrb1"
        cot_d["desccalca3"] = "m1en"
        cot_d["desccalcb3"] = "m1ex"
        cot_d["descline4"] = "75"
        cot_d["desctexta4"] = "ModClawsOfThunderHoldBuff"
        cot_d["desccalca4"] = "1"
        cot_d["desccalcb4"] = "clc3"
        cot_d["descline5"] = "74"
        cot_d["desctexta5"] = "StrSkill22"
        cot_d["desccalca5"] = "toht"
        cot_d["dsc3line1"] = "40"
        cot_d["dsc3texta1"] = "Sksyn"
        cot_d["dsc3textb1"] = "Skillname270"
        cot_d["dsc3calca1"] = "2"
        cot_d["dsc3line2"] = "76"
        cot_d["dsc3texta2"] = "Ltngdplev"
        cot_d["dsc3textb2"] = "Skillname272"
        cot_d["dsc3calca2"] = "12"
        cot_d["dsc3line3"] = "76"
        cot_d["dsc3texta3"] = "Ltngdplev"
        cot_d["dsc3textb3"] = "Skillname260"
        cot_d["dsc3calca3"] = "6"
        cot_d["dsc3line4"] = "76"
        cot_d["dsc3texta4"] = "Ltngdplev"
        cot_d["dsc3textb4"] = "Skillname275"
        cot_d["dsc3calca4"] = "6"

    snap_cot = "max(stat('progressive_lightning'.accr), stat('item_kickdamage'.accr))"
    cot_m = "skill('Claws of Thunder'.blvl)"
    ls_c = "skill('Ass Trap Charge Consume'.blvl)"
    ls_trap_syn = "(skill('Wake of Fire Sentry'.blvl) + skill('Death Sentry'.blvl))"

    if "Lightning Sentry" in by_name:
        ls = by_name["Lightning Sentry"]
        ls["srvstfunc"] = "39"
        ls["srvdofunc"] = "45"
        ls["pettype"] = "ltngtrap"
        ls["petmax"] = f"1 + (({ls_trap_syn} >= 10) ? 1 : 0) + (({ls_trap_syn} >= 25) ? 1 : 0)"
        ls["aurastate"] = "progressive_lightning"
        ls["auralencalc"] = "12"
        ls["aurastat1"] = "item_kickdamage"
        ls["aurastatcalc1"] = snap_cot
        ls["aurastat2"] = ""
        ls["aurastatcalc2"] = ""
        ls["passivestat1"] = "item_pierce_ltng_immunity"
        ls["passivecalc1"] = "stat('item_pierce_ltng_immunity'.accr)"
        ls["passivestat2"] = "passive_ltng_pierce"
        ls["passivecalc2"] = "stat('passive_ltng_pierce'.accr)"
        ls["passivestat3"] = "passive_ltng_mastery"
        ls["passivecalc3"] = "stat('passive_ltng_mastery'.accr)"
        ls["passivestat4"] = ""
        ls["passivecalc4"] = ""
        ls["sumskill1"] = "sentry lightning"
        ls["sumsk1calc"] = "lvl"
        ls["sumskill2"] = "Lightning Sentry"
        ls["sumsk2calc"] = "lvl"
        ls["sumskill3"] = "Claws of Thunder"
        ls["sumsk3calc"] = cot_m
        ls["sumskill4"] = "Wake of Fire Sentry"
        ls["sumsk4calc"] = "skill('Wake of Fire Sentry'.blvl) + skill('Death Sentry'.blvl)"
        ls["sumskill5"] = "Ass Trap Charge Consume"
        ls["sumsk5calc"] = snap_cot
        ls["Param1"] = "7"
        ls["*Param1 Description"] = "# of shots"
        ls["HitShift"] = "8"
        ls["EType"] = "ltng"
        ls["EMin"] = "1"
        ls["EMinLev1"] = "0"
        ls["EMinLev2"] = "0"
        ls["EMinLev3"] = "0"
        ls["EMinLev4"] = "0"
        ls["EMinLev5"] = "0"
        ls["EMax"] = "64"
        ls["EMaxLev1"] = "0"
        ls["EMaxLev2"] = "0"
        ls["EMaxLev3"] = "0"
        ls["EMaxLev4"] = "0"
        ls["EMaxLev5"] = "0"
        ls["calc1"] = "100 + 10*max(0,lvl-1) + 6*max(0,lvl-8) + 16*max(0,lvl-16) + 32*max(0,lvl-22)"
        ls["*calc1 desc"] = "Base Lightning Damage Level Ramp (%)"
        ls["calc3"] = "12*skill('Claws of Thunder'.blvl) + 6*skill('Wake of Fire Sentry'.blvl) + 6*skill('Death Sentry'.blvl)"
        ls["*calc3 desc"] = "Total Synergy Bonus (%)"
        ls["EDmgSymPerCalc"] = "(clc1 * (100 + clc3)) / 100 - 100"

    ls_shots_calc = f"par8 + (({ls_c} >= 2) ? (4 + {cot_m} / 5) : 0)"
    if "sentry lightning" in by_name:
        sl = by_name["sentry lightning"]
        sl["srvstfunc"] = ""
        sl["srvdofunc"] = ""
        sl["srvmissile"] = "sentrylightningbolt"
        sl["srvmissilea"] = ""
        sl["cltstfunc"] = ""
        sl["cltdofunc"] = ""
        sl["cltmissile"] = "sentrylightningbolt"
        sl["cltmissilea"] = ""
        sl["anim"] = "SQ"
        sl["seqtrans"] = "SQ"
        sl["monanim"] = "S2"
        sl["UseAttackRate"] = "1"
        sl["aurafilter"] = "98304"
        sl["auratargetstate"] = "dimvision"
        sl["auralencalc"] = f"({ls_c} >= 3) ? (100 + 10 * {cot_m}) : 0"
        sl["aurarangecalc"] = ""
        sl["Param8"] = "7"
        sl["calc1"] = "skill('Lightning Sentry'.blvl)"
        sl["*calc1 desc"] = "Lightning Sentry Skill Level"
        sl["calc2"] = "100 + 10*max(0,clc1-1) + 6*max(0,clc1-8) + 16*max(0,clc1-16) + 32*max(0,clc1-22)"
        sl["*calc2 desc"] = "Base Lightning Damage Level Ramp (%)"
        sl["calc3"] = "100 + 12*skill('Claws of Thunder'.blvl) + 6*skill('Wake of Fire Sentry'.blvl)"
        sl["*calc3 desc"] = "Total Synergy Multiplier (%)"
        sl["calc4"] = ls_shots_calc

    if "lightning sentry" in by_desc:
        ls_d = by_desc["lightning sentry"]
        ls_d["descdam"] = "5"
        ls_d["descline1"] = "75"
        ls_d["desctexta1"] = "StrSkill7"
        ls_d["desctextb1"] = ""
        ls_d["desccalca1"] = "1"
        ls_d["desccalcb1"] = "exma"
        ls_d["descline2"] = ""
        ls_d["desctexta2"] = ""
        ls_d["desccalca2"] = ""
        ls_d["desccalcb2"] = ""
        ls_d["dsc2line1"] = "36"
        ls_d["dsc2texta1"] = "StrSkill3"
        ls_d["dsc2textb1"] = ""
        ls_d["dsc2calca1"] = "usmc"
        ls_d["dsc2calcb1"] = "256"
        ls_d["dsc2line2"] = "74"
        ls_d["dsc2texta2"] = "ESkillShoots"
        ls_d["dsc2textb2"] = ""
        ls_d["dsc2calca2"] = "par1"
        ls_d["dsc2calcb2"] = ""
        ls_d["dsc2line3"] = "74"
        ls_d["dsc2texta3"] = "ModLightningSentryMaxTraps"
        ls_d["dsc2calca3"] = f"1 + (({ls_trap_syn} >= 10) ? 1 : 0) + (({ls_trap_syn} >= 25) ? 1 : 0)"
        ls_d["dsc2calcb3"] = ""
        ls_d["dsc2line4"] = "74"
        ls_d["dsc2texta4"] = "ModLightningSentryChargedShots"
        ls_d["dsc2calca4"] = f"par1 + 4 + {cot_m} / 5"
        ls_d["dsc2calcb4"] = ""
        ls_d["dsc3line1"] = "40"
        ls_d["dsc3texta1"] = "Sksyn"
        ls_d["dsc3textb1"] = "Skillname272"
        ls_d["dsc3calca1"] = "2"
        ls_d["dsc3line2"] = "76"
        ls_d["dsc3texta2"] = "Ltngdplev"
        ls_d["dsc3textb2"] = "Skillname270"
        ls_d["dsc3calca2"] = "12"
        ls_d["dsc3calcb2"] = ""
        ls_d["dsc3line3"] = "76"
        ls_d["dsc3texta3"] = "Ltngdplev"
        ls_d["dsc3textb3"] = "Skillname263"
        ls_d["dsc3calca3"] = "6"
        ls_d["dsc3calcb3"] = ""
        ls_d["dsc3line4"] = "76"
        ls_d["dsc3texta4"] = "Ltngdplev"
        ls_d["dsc3textb4"] = "Skillname277"
        ls_d["dsc3calca4"] = "6"
        ls_d["dsc3calcb4"] = ""
        ls_d["dsc3line5"] = ""
        ls_d["dsc3texta5"] = ""
        ls_d["dsc3textb5"] = ""
        ls_d["dsc3calca5"] = ""
        ls_d["dsc3calcb5"] = ""

    # Step 4: Blades of Ice (progressive_cold, Id 274) <-> Ice Sentry (Death Sentry, Id 276)
    if "Blades of Ice" in by_name:
        boi = by_name["Blades of Ice"]
        boi["prgstack"] = ""
        boi["prgdam"] = ""
        boi["srvprgfunc1"] = "39"
        boi["cltprgfunc1"] = "9"
        boi["prgcalc1"] = "6"
        boi["srvprgfunc2"] = "41"
        boi["cltprgfunc2"] = "15"
        boi["prgcalc2"] = "12"
        boi["srvprgfunc3"] = "40"
        boi["cltprgfunc3"] = "14"
        boi["prgcalc3"] = "9"
        boi["srvmissilea"] = "bladesoficeexplode"
        boi["cltmissilea"] = "bladesoficeexplode"
        boi["srvmissileb"] = "royalstrikechaosice"
        boi["cltmissileb"] = "royalstrikechaosice"
        boi["srvmissilec"] = "catapult cold ball on"
        boi["cltmissilec"] = "catapult cold ball on"
        boi["calc1"] = "9"
        boi["*calc1 desc"] = "Frozen Orb Target Offset"
        boi["calc2"] = "1"
        boi["*calc2 desc"] = "Cold Damage Unit per Orb"
        boi["calc3"] = (
            "((3 + (lvl-1)/2 + max(0,lvl-16) + 3*max(0,lvl-20) + 5*max(0,lvl-26)) * (100 + clc4)) / 100"
        )
        boi["*calc3 desc"] = "Held Min Cold Damage per Orb (Max = 2 * clc3)"
        boi["calc4"] = (
            "12*skill('Death Sentry'.blvl) + 6*skill('Fists of Fire'.blvl) + 6*skill('Claws of Thunder'.blvl)"
        )
        boi["*calc4 desc"] = "Total Synergy Bonus (%)"
        boi["EType"] = ""
        boi["EMin"] = ""
        boi["EMinLev1"] = ""
        boi["EMinLev2"] = ""
        boi["EMinLev3"] = ""
        boi["EMinLev4"] = ""
        boi["EMinLev5"] = ""
        boi["EMax"] = ""
        boi["EMaxLev1"] = ""
        boi["EMaxLev2"] = ""
        boi["EMaxLev3"] = ""
        boi["EMaxLev4"] = ""
        boi["EMaxLev5"] = ""
        boi["EDmgSymPerCalc"] = ""
        boi["ELen"] = ""
        boi["ELevLen1"] = ""
        boi["ELevLen2"] = ""
        boi["ELevLen3"] = ""
        boi["aurastat2"] = "item_crush_damage"
        boi["aurastatcalc2"] = "clc3"
        boi["aurastat3"] = ""
        boi["aurastatcalc3"] = ""
        boi["aurastat4"] = ""
        boi["aurastatcalc4"] = ""
        boi["passivestate"] = "ass_boi_passive"
        boi["passivestat1"] = "item_absorb_crush"
        boi["passivecalc1"] = "1"
        boi["passivestat2"] = "coldlength"
        boi["passivecalc2"] = "75"

    if "blades of ice" in by_desc:
        boi_d = by_desc["blades of ice"]
        boi_d["descdam"] = "1"
        boi_d["p1dmelem"] = ""
        boi_d["p1dmmin"] = ""
        boi_d["p1dmmax"] = ""
        boi_d["p2dmelem"] = ""
        boi_d["p2dmmin"] = ""
        boi_d["p2dmmax"] = ""
        boi_d["p3dmelem"] = ""
        boi_d["p3dmmin"] = ""
        boi_d["p3dmmax"] = ""
        boi_d["descmissile1"] = "bladesoficeexplode"
        boi_d["descmissile2"] = "royalstrikechaosice"
        boi_d["descmissile3"] = "catapult cold ball"
        boi_d["descline1"] = "75"
        boi_d["desctexta1"] = "ModBladesOfIceOrb3"
        boi_d["desccalca1"] = "m3en"
        boi_d["desccalcb1"] = "m3ex"
        boi_d["descline2"] = "75"
        boi_d["desctexta2"] = "ModBladesOfIceOrb2"
        boi_d["desccalca2"] = "m2en"
        boi_d["desccalcb2"] = "m2ex"
        boi_d["descline3"] = "75"
        boi_d["desctexta3"] = "ModBladesOfIceOrb1"
        boi_d["desccalca3"] = "m1en"
        boi_d["desccalcb3"] = "m1ex"
        boi_d["descline4"] = "75"
        boi_d["desctexta4"] = "ModBladesOfIceHoldBuff"
        boi_d["desccalca4"] = "clc3"
        boi_d["desccalcb4"] = "2*clc3"
        boi_d["descline5"] = "74"
        boi_d["desctexta5"] = "StrSkill22"
        boi_d["desccalca5"] = "toht"
        boi_d["dsc3line1"] = "40"
        boi_d["dsc3texta1"] = "Sksyn"
        boi_d["dsc3textb1"] = "Skillname275"
        boi_d["dsc3calca1"] = "2"
        boi_d["dsc3line2"] = "76"
        boi_d["dsc3texta2"] = "Colddplev"
        boi_d["dsc3textb2"] = "Skillname277"
        boi_d["dsc3calca2"] = "12"
        boi_d["dsc3line3"] = "76"
        boi_d["dsc3texta3"] = "Colddplev"
        boi_d["dsc3textb3"] = "Skillname260"
        boi_d["dsc3calca3"] = "6"
        boi_d["dsc3line4"] = "76"
        boi_d["dsc3texta4"] = "Colddplev"
        boi_d["dsc3textb4"] = "Skillname270"
        boi_d["dsc3calca4"] = "6"

    snap_boi = "max(stat('progressive_cold'.accr), stat('item_kickdamage'.accr))"
    boi_m = "skill('Blades of Ice'.blvl)"
    ds_c = "skill('Ass Trap Charge Consume'.blvl)"
    ds_trap_syn = "(skill('Wake of Fire Sentry'.blvl) + skill('Lightning Sentry'.blvl))"

    if "Death Sentry" in by_name:
        ds = by_name["Death Sentry"]
        ds["srvstfunc"] = "39"
        ds["srvdofunc"] = "45"
        ds["pettype"] = "deathtrap"
        ds["petmax"] = f"1 + (({ds_trap_syn} >= 10) ? 1 : 0) + (({ds_trap_syn} >= 25) ? 1 : 0)"
        ds["aurastate"] = "progressive_cold"
        ds["auralencalc"] = "12"
        ds["aurastat1"] = "item_kickdamage"
        ds["aurastatcalc1"] = snap_boi
        ds["aurastat2"] = ""
        ds["aurastatcalc2"] = ""
        ds["passivestat1"] = "item_pierce_cold_immunity"
        ds["passivecalc1"] = "stat('item_pierce_cold_immunity'.accr)"
        ds["passivestat2"] = "passive_cold_pierce"
        ds["passivecalc2"] = "stat('passive_cold_pierce'.accr)"
        ds["passivestat3"] = "passive_cold_mastery"
        ds["passivecalc3"] = "stat('passive_cold_mastery'.accr)"
        ds["passivestat4"] = ""
        ds["passivecalc4"] = ""
        ds["passivestat5"] = ""
        ds["passivecalc5"] = ""
        ds["passivestat6"] = ""
        ds["passivecalc6"] = ""
        ds["passivestat7"] = ""
        ds["passivecalc7"] = ""
        ds["sumskill1"] = "mon death sentry"
        ds["sumsk1calc"] = "lvl"
        ds["sumskill2"] = "Death Sentry"
        ds["sumsk2calc"] = "lvl"
        ds["sumskill3"] = "Blades of Ice"
        ds["sumsk3calc"] = boi_m
        ds["sumskill4"] = "Wake of Fire Sentry"
        ds["sumsk4calc"] = "skill('Wake of Fire Sentry'.blvl) + skill('Lightning Sentry'.blvl)"
        ds["sumskill5"] = "Ass Trap Charge Consume"
        ds["sumsk5calc"] = snap_boi
        ds["sumumod"] = ""
        ds["Param1"] = "25"
        ds["*Param1 Description"] = "# of shots"
        ds["HitShift"] = "8"
        ds["EType"] = "cold"
        ds["EMin"] = "10"
        ds["EMinLev1"] = "0"
        ds["EMinLev2"] = "0"
        ds["EMinLev3"] = "0"
        ds["EMinLev4"] = "0"
        ds["EMinLev5"] = "0"
        ds["EMax"] = "16"
        ds["EMaxLev1"] = "0"
        ds["EMaxLev2"] = "0"
        ds["EMaxLev3"] = "0"
        ds["EMaxLev4"] = "0"
        ds["EMaxLev5"] = "0"
        ds["calc1"] = "100 + 10*max(0,lvl-1) + 6*max(0,lvl-8) + 16*max(0,lvl-16) + 32*max(0,lvl-22)"
        ds["*calc1 desc"] = "Base Cold Damage Level Ramp (%)"
        ds["calc3"] = "12*skill('Blades of Ice'.blvl) + 6*skill('Wake of Fire Sentry'.blvl) + 6*skill('Lightning Sentry'.blvl)"
        ds["*calc3 desc"] = "Total Synergy Bonus (%)"
        ds["EDmgSymPerCalc"] = "(clc1 * (100 + clc3)) / 100 - 100"

    ds_shots_calc = f"par8 + (({ds_c} >= 2) ? (15 + {boi_m} / 2) : 0)"
    if "mon death sentry" in by_name:
        mds = by_name["mon death sentry"]
        mds["srvstfunc"] = ""
        mds["srvdofunc"] = ""
        mds["srvmissile"] = "frozenhorror arcticblast1"
        mds["srvmissilea"] = ""
        mds["cltstfunc"] = ""
        mds["cltdofunc"] = ""
        mds["cltmissile"] = "frozenhorror arcticblast1"
        mds["cltmissilea"] = ""
        mds["cltmissileb"] = ""
        mds["cltcalc1"] = ""
        mds["aurarangecalc"] = ""
        mds["prgsound"] = ""
        mds["castoverlay"] = ""
        mds["TargetCorpse"] = ""
        mds["anim"] = "SQ"
        mds["seqtrans"] = "SQ"
        mds["monanim"] = "S2"
        mds["UseAttackRate"] = "1"
        mds["Param8"] = "25"
        mds["calc1"] = "skill('Death Sentry'.blvl)"
        mds["*calc1 desc"] = "Ice Sentry Skill Level"
        mds["calc2"] = "100 + 10*max(0,clc1-1) + 6*max(0,clc1-8) + 16*max(0,clc1-16) + 32*max(0,clc1-22)"
        mds["*calc2 desc"] = "Ice Sentry Level Multiplier (%)"
        mds["calc3"] = "100 + 12*skill('Blades of Ice'.blvl) + 6*skill('Wake of Fire Sentry'.blvl)"
        mds["*calc3 desc"] = "Synergy Multiplier (%)"
        mds["calc4"] = ds_shots_calc

    if "death sentry" in by_desc:
        ds_d = by_desc["death sentry"]
        ds_d["descdam"] = "5"
        ds_d["descline1"] = "75"
        ds_d["desctexta1"] = "StrSkill6"
        ds_d["desctextb1"] = ""
        ds_d["desccalca1"] = "enma"
        ds_d["desccalcb1"] = "exma"
        ds_d["descline2"] = ""
        ds_d["desctexta2"] = ""
        ds_d["desccalca2"] = ""
        ds_d["desccalcb2"] = ""
        ds_d["dsc2line1"] = "36"
        ds_d["dsc2texta1"] = "StrSkill3"
        ds_d["dsc2textb1"] = ""
        ds_d["dsc2calca1"] = "usmc"
        ds_d["dsc2calcb1"] = "256"
        ds_d["dsc2line2"] = "74"
        ds_d["dsc2texta2"] = "ESkillShoots"
        ds_d["dsc2textb2"] = ""
        ds_d["dsc2calca2"] = "par1"
        ds_d["dsc2calcb2"] = ""
        ds_d["dsc2line3"] = "74"
        ds_d["dsc2texta3"] = "ModIceSentryMaxTraps"
        ds_d["dsc2calca3"] = f"1 + (({ds_trap_syn} >= 10) ? 1 : 0) + (({ds_trap_syn} >= 25) ? 1 : 0)"
        ds_d["dsc2calcb3"] = ""
        ds_d["dsc2line4"] = "74"
        ds_d["dsc2texta4"] = "ModIceSentryChargedShots"
        ds_d["dsc2calca4"] = f"par1 + 15 + {boi_m} / 2"
        ds_d["dsc2calcb4"] = ""
        ds_d["dsc3line1"] = "40"
        ds_d["dsc3texta1"] = "Sksyn"
        ds_d["dsc3textb1"] = "Skillname277"
        ds_d["dsc3calca1"] = "2"
        ds_d["dsc3line2"] = "76"
        ds_d["dsc3texta2"] = "Colddplev"
        ds_d["dsc3textb2"] = "Skillname275"
        ds_d["dsc3calca2"] = "12"
        ds_d["dsc3calcb2"] = ""
        ds_d["dsc3line3"] = "76"
        ds_d["dsc3texta3"] = "Colddplev"
        ds_d["dsc3textb3"] = "Skillname263"
        ds_d["dsc3calca3"] = "6"
        ds_d["dsc3calcb3"] = ""
        ds_d["dsc3line4"] = "76"
        ds_d["dsc3texta4"] = "Colddplev"
        ds_d["dsc3textb4"] = "Skillname272"
        ds_d["dsc3calca4"] = "6"
        ds_d["dsc3calcb4"] = ""

    # Step 5b: Omnislash (Royal Strike, Id 280) — Level 40 Martial Arts Capstone standalone Whirlwind (non-finisher)
    #   - Multi-strike weapon finishing move (srvstfunc=39, srvdofunc=1, cltstfunc=1, cltdofunc=1)
    #   - Driven by anim/seqtrans='A2' (AIA2* configured in animdata.d2 with 4 rapid ev=1 melee hit triggers; S3 has no valid Assassin melee mode)
    #   - Usable with all melee weapons (itypea1=mele, weapsel=""): 1H weapons, dual claws (alternating hands via ht2_sequence), and 2H weapons
    #   - Natively releases built-up Martial Arts charges on each hit (3 -> 2 -> 1 -> 0 via srvdofunc=1 + finishing=1, prgchargesconsumed=1)
    #   - Innate Enhanced Damage: 36% + 6%/lvl (RAMP34 -> +150% ED at Lvl 20), applied via srvstfunc=39 self-buff (aurastate='dragonflight')
    #   - Synergies: +8%/lvl from Shuriken (Inferno Sentry, +160% at 20) and +5%/lvl from Dragon Claw (+100% at 20) -> +410% max ED
    #   - Innate Attack Rating: +50% base + 15%/lvl (+335% AR at Lvl 20), applied via aurastat2='item_tohit_percent'
    if "Royal Strike" in by_name:
        rs = by_name["Royal Strike"]
        rs["srvstfunc"] = "37"
        rs["srvdofunc"] = "13"
        rs["cltstfunc"] = "53"
        rs["cltdofunc"] = "21"
        rs["Kick"] = ""
        rs["stsound"] = "assassin_kick_1"
        rs["weaponsnd"] = "1"
        rs["srvprgfunc1"] = ""
        rs["srvprgfunc2"] = ""
        rs["srvprgfunc3"] = ""
        rs["cltprgfunc1"] = ""
        rs["cltprgfunc2"] = ""
        rs["cltprgfunc3"] = ""
        rs["prgcalc1"] = ""
        rs["prgcalc2"] = ""
        rs["prgcalc3"] = ""
        rs["srvmissilea"] = ""
        rs["srvmissileb"] = ""
        rs["srvmissilec"] = ""
        rs["cltmissilea"] = ""
        rs["cltmissileb"] = ""
        rs["cltmissilec"] = ""
        rs["aurastate"] = ""
        rs["auralencalc"] = ""
        rs["aurarangecalc"] = ""
        rs["aurastat1"] = ""
        rs["aurastatcalc1"] = ""
        rs["aurastat2"] = ""
        rs["aurastatcalc2"] = ""
        rs["enhanceable"] = "1"
        rs["attackrank"] = "2"
        rs["range"] = "h2h"
        rs["itypea1"] = "mele"
        rs["weapsel"] = ""
        rs["anim"] = "A2"
        rs["seqtrans"] = "A2"
        rs["monanim"] = "xx"
        rs["seqnum"] = ""
        rs["UseAttackRate"] = "1"
        rs["TargetableOnly"] = "1"
        rs["SearchEnemyXY"] = "1"
        rs["AttackNoMana"] = "1"
        rs["KeepCursorStateOnKill"] = "1"
        rs["leftskill"] = "1"
        rs["rightskill"] = "1"
        rs["minmana"] = "1"
        rs["manashift"] = "8"
        rs["mana"] = "4"
        rs["lvlmana"] = "0"
        rs["interrupt"] = "1"
        rs["progressive"] = ""
        rs["finishing"] = "1"
        rs["prgchargestocast"] = "0"
        rs["prgchargesconsumed"] = "1"
        # srvdofunc=13 (Zeal/Fend engine): weapon damage, Param2 = % anim frame rollback, calc1 = # of hits.
        # NOTE: srvdofunc 13 does not release Martial Arts charges; srvdofunc 42 (multi-hit) hard-codes boot damage.
        rs["Param1"] = ""
        rs["*Param1 Description"] = ""
        rs["Param2"] = "70"
        rs["*Param2 Description"] = "% Anim frame rollback"
        rs["Param3"] = "36"
        rs["*Param3 Description"] = "Damage % baseline"
        rs["Param4"] = "6"
        rs["*Param4 Description"] = "Damage % per level"
        rs["Param5"] = "3"
        rs["*Param5 Description"] = "# of hits Min"
        rs["Param6"] = "6"
        rs["*Param6 Description"] = "# of hits Max"
        rs["Param7"] = "8"
        rs["*Param7 Description"] = "Damage synergy % from Shuriken"
        rs["Param8"] = "5"
        rs["*Param8 Description"] = "Damage synergy % from Dragon Claw"
        rs["calc1"] = "min(par5 + (lvl - 1) / 5, par6)"
        rs["*calc1 desc"] = "# of hits"
        rs["calc2"] = f"{RAMP34} + skill('Inferno Sentry'.blvl)*par7 + skill('Dragon Claw'.blvl)*par8"
        rs["*calc2 desc"] = "Damage %"
        rs["calc3"] = ""
        rs["*calc3 desc"] = ""
        rs["calc4"] = "0"
        rs["*calc4 desc"] = "% Damage Dealt as Elemental"
        rs["ToHit"] = "50"
        rs["LevToHit"] = "15"
        rs["HitShift"] = "8"
        rs["SrcDam"] = "128"

        # --- Omnislash = standalone Whirlwind (neither a charge-up nor a finishing move) ---
        # Role: what the Assassin casts when she does NOT want to release her held orbs.  The held-orb stats
        # (fire / cold / lightning damage, +% damage, etc.) are plain unit stats, so every spin hit carries them.
        # Whirlwind's own start-up applies an orb-aware resistance-shredding debuff to nearby monsters via the
        # same escalation hook the Barbarian Whirlwind uses (srvdofunc 168 casts the hidden skill in calc6).
        for k in ("srvprgfunc1", "srvprgfunc2", "srvprgfunc3", "cltprgfunc1", "cltprgfunc2", "cltprgfunc3",
                  "aurastat1", "aurastatcalc1", "aurastat2", "aurastatcalc2", "aurastat3", "aurastatcalc3",
                  "aurastat4", "aurastatcalc4", "aurastat5", "aurastatcalc5", "aurastat6", "aurastatcalc6",
                  "prgcalc1", "prgcalc2", "prgcalc3", "finishing", "prgchargesconsumed", "prgchargestocast",
                  "progressive", "aurarangecalc", "calc3", "calc4", "calc5", "calc7",
                  "Param5", "Param6", "*Param5 Description", "*Param6 Description"):
            rs[k] = ""
        rs["srvstfunc"] = "38"
        rs["srvdofunc"] = "168"
        rs["srvstopfunc"] = "1"
        rs["cltstfunc"] = "31"
        rs["cltdofunc"] = "45"
        rs["cltstopfunc"] = "1"
        rs["stsuccessonly"] = "1"
        rs["stsound"] = "barbarian_whirlwind"
        rs["aurastate"] = "whirlwind"
        rs["range"] = "none"
        rs["weapsel"] = "2"
        rs["itypea1"] = "mele"
        rs["itypeb1"] = ""
        rs["anim"] = "SQ"
        rs["seqtrans"] = "A1"
        rs["seqnum"] = "10"
        rs["attackrank"] = "3"
        rs["Kick"] = ""
        rs["Param1"] = "36"
        rs["*Param1 Description"] = "Damage % baseline"
        rs["Param2"] = "6"
        rs["*Param2 Description"] = "Damage % per level"
        rs["Param7"] = "8"
        rs["*Param7 Description"] = "Damage synergy % from Shuriken"
        rs["Param8"] = "5"
        rs["*Param8 Description"] = "Damage synergy % from Dragon Claw"
        rs["calc1"] = f"{RAMP34} + skill('Inferno Sentry'.blvl)*par7 + skill('Dragon Claw'.blvl)*par8"
        rs["*calc1 desc"] = "Damage %"
        rs["calc2"] = "2"
        rs["*calc2 desc"] = "Escalation 1 Skill Level"
        rs["calc4"] = "0"
        rs["calc5"] = "0"
        rs["calc7"] = "0"
        rs["*calc3 desc"] = "Chance to Cast Escalation 1 Skill"
        rs["calc3"] = "100"
        rs["*calc4 desc"] = "Escalation 2 Skill Level"
        rs["*calc5 desc"] = "Chance To Cast Escalation 2 Skill"
        rs["*calc7desc"] = "Escalation 2 Skill Id"

        # Hidden skill cast by Whirlwind on every spin tick: temporary elemental resistance shred on nearby enemies.
        #   Each element's shred scales with the points in that element's charge-up skill (x2) plus Whirlwind's
        #   own level (x1) - independent of whether orbs are currently held.
        #   Lasts 3s after the last tick, so it outlives the spin by a few seconds.
        if "Ass Whirl Shred" not in by_name:
            max_sid = max(parse_int(r.get("*Id", "0"), 0) for r in s_rows)
            # Clone the stock Battle Cry row (srvdofunc 68 + 'battlecry' missile): a warcry-style burst around the
            # caster that applies its aura state to every enemy it touches, with no target needed -> castable from
            # Whirlwind's escalation hook.  (Curse-style srvdofunc 30 needs a target and never reached monsters.)
            # Made hidden and class-less.
            sk_shred = dict(by_name["Battle Cry"])
            for k in ("charclass", "skilldesc", "reqskill1", "reqskill2", "reqskill3", "leftskill", "rightskill",
                      "stsound", "stsoundclass", "ItemCastSound", "cost mult", "cost add", "mana", "lvlmana",
                      "localdelay", "globaldelay", "Param1", "Param2", "Param3", "Param4", "Param5", "Param6",
                      "*Param1 Description", "*Param2 Description", "*Param3 Description", "*Param4 Description",
                      "*Param5 Description", "*Param6 Description"):
                if k in sk_shred:
                    sk_shred[k] = ""
            for n_clear in range(1, 7):
                sk_shred[f"aurastat{n_clear}"] = ""
                sk_shred[f"aurastatcalc{n_clear}"] = ""
            sk_shred["skill"] = "Ass Whirl Shred"
            sk_shred["*Id"] = str(max_sid + 1)
            sk_shred["srvdofunc"] = "68"
            sk_shred["srvmissilea"] = "battlecry"
            sk_shred["aurafilter"] = "98304"
            sk_shred["auratargetstate"] = "ass_whirl_shred"
            sk_shred["auralencalc"] = "75"
            sk_shred["aurarangecalc"] = ""
            for n_idx, (res_stat, orb_stat, orb_skill) in enumerate(
                (
                    ("fireresist", "progressive_fire", "Fists of Fire"),
                    ("coldresist", "progressive_cold", "Blades of Ice"),
                    ("lightresist", "progressive_lightning", "Claws of Thunder"),
                ),
                start=1,
            ):
                sk_shred[f"aurastat{n_idx}"] = res_stat
                sk_shred[f"aurastatcalc{n_idx}"] = f"-(skill('{orb_skill}'.blvl) + skill('Royal Strike'.blvl)/2)"
            # Visuals toned down: no client-side Battle Cry burst/overlay; only the state's monster tint remains.
            for k in ("cltdofunc", "cltstfunc", "cltmissilea", "cltmissileb", "cltmissilec", "castoverlay",
                      "srvoverlay", "tgtoverlay", "ItemCastOverlay", "*cltcalc1 desc"):
                if k in sk_shred:
                    sk_shred[k] = ""
            sk_shred["range"] = "none"
            sk_shred["monanim"] = "xx"
            sk_shred["ItemEffect"] = "1"
            sk_shred["reqlevel"] = "1"
            sk_shred["InGame"] = "1"
            sk_shred["HitShift"] = "8"
            sk_shred["*eol"] = "0"
            s_rows.append(sk_shred)
            by_name["Ass Whirl Shred"] = sk_shred
        rs["calc2"] = "10"  # cast level (the cloned Battle Cry row allows levels up to 20)
        rs["calc6"] = by_name["Ass Whirl Shred"]["*Id"]
        rs["*calc6 desc"] = "Escalation 1 Skill Id"

        # Experiment: stop the engine from swapping Whirlwind for a plain attack when the cursor is on a monster.
        rs["TargetableOnly"] = ""
        rs["AttackNoMana"] = ""
        rs["SearchEnemyXY"] = ""

    if "Dragon Tail" in by_name:
        dtl = by_name["Dragon Tail"]
        dtl["Param1"] = "40"
        dtl["Param2"] = "12"

    if "Dragon Flight" in by_name:
        dfl = by_name["Dragon Flight"]
        dfl["Param1"] = "75"
        dfl["Param2"] = "20"

    if "royal strike" in by_desc:
        rs_d = by_desc["royal strike"]
        rs_d["descdam"] = "7"
        rs_d["ddam calc1"] = "clc1"
        rs_d["p1dmelem"] = ""
        rs_d["p1dmmin"] = ""
        rs_d["p1dmmax"] = ""
        rs_d["p2dmelem"] = ""
        rs_d["p2dmmin"] = ""
        rs_d["p2dmmax"] = ""
        rs_d["p3dmelem"] = ""
        rs_d["p3dmmin"] = ""
        rs_d["p3dmmax"] = ""
        rs_d["descatt"] = "2"
        rs_d["descmissile1"] = ""
        rs_d["descmissile2"] = ""
        rs_d["descmissile3"] = ""
        rs_d["descline1"] = "74"
        rs_d["desctexta1"] = "StrSkillDamagePercent"
        rs_d["desctextb1"] = ""
        rs_d["desccalca1"] = "clc1"
        rs_d["desccalcb1"] = ""
        rs_d["descline2"] = "74"
        rs_d["desctexta2"] = "StrSkill22"
        rs_d["desctextb2"] = ""
        rs_d["desccalca2"] = "toht"
        rs_d["desccalcb2"] = ""
        rs_d["descline3"] = "74"
        rs_d["desctexta3"] = "ModWhirlFireShred"
        rs_d["desctextb3"] = ""
        rs_d["desccalca3"] = "skill('Fists of Fire'.blvl) + skill('Royal Strike'.blvl)/2"
        rs_d["desccalcb3"] = ""
        rs_d["descline4"] = "74"
        rs_d["desctexta4"] = "ModWhirlColdShred"
        rs_d["desctextb4"] = ""
        rs_d["desccalca4"] = "skill('Blades of Ice'.blvl) + skill('Royal Strike'.blvl)/2"
        rs_d["desccalcb4"] = ""
        rs_d["descline5"] = "74"
        rs_d["desctexta5"] = "ModWhirlLightShred"
        rs_d["desctextb5"] = ""
        rs_d["desccalca5"] = "skill('Claws of Thunder'.blvl) + skill('Royal Strike'.blvl)/2"
        rs_d["desccalcb5"] = ""
        rs_d["dsc2line1"] = "36"
        rs_d["dsc2texta1"] = "StrSkill3"
        rs_d["dsc2calca1"] = "usmc"
        rs_d["dsc2calcb1"] = "256"
        rs_d["dsc3line1"] = "40"
        rs_d["dsc3texta1"] = "Sksyn"
        rs_d["dsc3textb1"] = "Skillname281"
        rs_d["dsc3calca1"] = "2"
        rs_d["dsc3line2"] = "76"
        rs_d["dsc3texta2"] = "Damplev"
        rs_d["dsc3textb2"] = "Skillname273"
        rs_d["dsc3calca2"] = "par7"
        rs_d["dsc3line3"] = "76"
        rs_d["dsc3texta3"] = "Damplev"
        rs_d["dsc3textb3"] = "Skillname261"
        rs_d["dsc3calca3"] = "par8"
        rs_d["dsc3line4"] = ""
        rs_d["dsc3texta4"] = ""
        rs_d["dsc3textb4"] = ""
        rs_d["dsc3calca4"] = ""
        rs_d["dsc3line5"] = ""
        rs_d["dsc3texta5"] = ""
        rs_d["dsc3textb5"] = ""
        rs_d["dsc3calca5"] = ""

    # Step 5c: Caltrops (Shock Field, Id 256, Lvl 1): physical ground spikes with level-scaled damage.
    #   Damage (missile fields on 'shock field on ground'): 2-5 at Lvl 1 -> ~76-133 per second at Lvl 20.
    #   Damage only (no slow): see the note in apply_skill_missile_updates.
    if "Shock Field" in by_name:
        sf = by_name["Shock Field"]
        for k in ("EType", "EMin", "EMinLev1", "EMinLev2", "EMinLev3", "EMinLev4", "EMinLev5",
                  "EMax", "EMaxLev1", "EMaxLev2", "EMaxLev3", "EMaxLev4", "EMaxLev5", "EDmgSymPerCalc",
                  "Param8", "*Param8 Description"):
            sf[k] = ""
        sf["MinDam"] = "2"
        sf["MaxDam"] = "5"
        for _n, (_mn, _mx) in enumerate(((2, 4), (4, 7), (7, 11), (10, 16), (14, 22)), start=1):
            sf[f"MinLevDam{_n}"] = str(_mn)
            sf[f"MaxLevDam{_n}"] = str(_mx)
        sf["DmgSymPerCalc"] = ""
        for k in ("aurafilter", "auratargetstate", "auralencalc", "aurastat1", "aurastatcalc1"):
            sf[k] = ""

    if "shock field" in by_desc:
        sf_d = by_desc["shock field"]
        sf_d["descdam"] = ""
        sf_d["descmissile1"] = ""
        sf_d["descline2"] = "75"
        sf_d["desctexta2"] = "ModCaltropsDamage"
        sf_d["desccalca2"] = "2 + 2*max(0,min(lvl,8)-1) + 4*max(0,min(lvl,16)-8) + 7*max(0,min(lvl,22)-16) + 10*max(0,min(lvl,28)-22) + 14*max(0,lvl-28)"
        sf_d["desccalcb2"] = "5 + 4*max(0,min(lvl,8)-1) + 7*max(0,min(lvl,16)-8) + 11*max(0,min(lvl,22)-16) + 16*max(0,min(lvl,28)-22) + 22*max(0,lvl-28)"
        sf_d["descline4"] = ""
        sf_d["desctexta4"] = ""
        sf_d["desccalca4"] = ""
        for k in ("dsc3line3", "dsc3texta3", "dsc3textb3", "dsc3calca3",
                  "dsc3line4", "dsc3texta4", "dsc3textb4", "dsc3calca4"):
            sf_d[k] = ""

    # Step 5d: Shuriken (Inferno Sentry, Id 272, Lvl 40 capstone of the Blades line): a heavy, slow-cooldown bouncing
    # throwing star modeled on the reworked Blessed Hammer.
    #   - Chain mechanics: srvdofunc 26 / cltdofunc 27, radius par1 = 20 sub-tiles, hits = ln34/par5 = 6 at Lvl 1 -> 10 at Lvl 20
    #   - No casting delay / cooldown, 20 Mana (+1/lvl)
    #   - 100 percent weapon damage (SrcDam 128) + flat physical 30-45 at Lvl 1 -> ~261-338 at Lvl 20, +6 percent per Blade Sentinel / Blade Fury / Blade Shield level
    #   - No stun.
    if "Inferno Sentry" in by_name:
        sh = by_name["Inferno Sentry"]
        for k in ("srvstfunc", "summon", "pettype", "petmax", "summode", "sumumod", "stsoundclass",
                  "passivestate", "passivestat1", "passivecalc1", "passivestat2", "passivecalc2",
                  "passivestat3", "passivecalc3", "passivestat4", "passivecalc4", "passivestat5", "passivecalc5",
                  "sumskill1", "sumsk1calc", "sumskill2", "sumsk2calc", "sumskill3", "sumsk3calc",
                  "sumskill4", "sumsk4calc", "sumskill5", "sumsk5calc", "LineOfSight", "UseAttackRate",
                  "EType", "EMin", "EMinLev1", "EMinLev2", "EMinLev3", "EMinLev4", "EMinLev5",
                  "EMax", "EMaxLev1", "EMaxLev2", "EMaxLev3", "EMaxLev4", "EMaxLev5", "EDmgSymPerCalc",
                  "Param2", "*Param2 Description", "*Param3 Description", "*Param4 Description"):
            if k in sh:
                sh[k] = ""
        sh["srvdofunc"] = "26"
        sh["srvmissilea"] = "throwingstar"
        sh["srvmissileb"] = "throwingstar"
        sh["srvmissilec"] = "throwingstar"
        sh["cltdofunc"] = "27"
        sh["cltmissilea"] = "throwingstar"
        sh["cltmissileb"] = "throwingstar"
        sh["cltmissilec"] = "throwingstar"
        sh["aurarangecalc"] = "par1"
        sh["stsound"] = "assassin_bladefury_throw_1"
        sh["ItemCastSound"] = "assassin_bladefury_throw_1"
        sh["ItemEffect"] = "1"
        sh["KeepCursorStateOnKill"] = "1"
        sh["range"] = "none"
        sh["anim"] = "S1"
        sh["seqtrans"] = "S1"
        sh["monanim"] = "xx"
        sh["leftskill"] = "1"
        sh["rightskill"] = "1"
        sh["localdelay"] = ""
        sh["manashift"] = "8"
        sh["mana"] = "20"
        sh["lvlmana"] = "1"
        sh["UseAttackRate"] = "1"
        sh["ToHitCalc"] = "lvl*10"
        sh["HitShift"] = "8"
        sh["Param1"] = "20"
        sh["*Param1 Description"] = "Radius of jump to next target"
        sh["Param3"] = "24"
        sh["*Param3 Description"] = "# of target jump hits baseline"
        sh["Param4"] = "1"
        sh["*Param4 Description"] = "# of target jump hits per level"
        sh["Param5"] = "4"
        sh["*Param5 Description"] = "Every # levels, increase target jump"
        sh["Param8"] = "18"
        sh["*Param8 Description"] = "Damage synergy"
        sh["calc1"] = "ln34/par5"
        sh["*calc1 desc"] = "# of target jump hits"
        sh["SrcDam"] = "96"  # 75% weapon damage (96/128 = 75%), matching Blade Fury (including 2H weapons)
        sh["MinDam"] = "16"
        sh["MaxDam"] = "24"
        for _n, (_mn, _mx) in enumerate(zip((4, 6, 11, 15, 20,), (5, 8, 14, 19, 25,)), start=1):
            sh[f"MinLevDam{_n}"] = str(_mn)
            sh[f"MaxLevDam{_n}"] = str(_mx)
        sh["DmgSymPerCalc"] = "skill('Blade Fury'.blvl)*par8"
    if "inferno sentry" in by_desc:
        sh_d = by_desc["inferno sentry"]
        # Same display type Blade Fury uses (descdam 24 = physical skill damage incl. weapon damage, descatt 1 = AR),
        # so the character screen shows both the skill's damage and its Attack Rating.
        sh_d["descdam"] = "24"
        sh_d["descatt"] = "1"
        sh_d["descmissile1"] = ""
        _set_dsc_line(sh_d, "desc", 1, "75", "StrSkill4", "", "pnma", "pxma")
        _set_dsc_line(sh_d, "desc", 2, "74", "StrSkill22", "", "toht", "")
        _set_dsc_line(sh_d, "desc", 3, "74", "StrSkill11", "", "ln34/par5", "")
        _set_dsc_line(sh_d, "desc", 4, "74", "WeapDamsk", "", "96*100/128", "")
        _set_dsc_line(sh_d, "desc", 5, "", "", "", "", "")
        _set_dsc_line(sh_d, "dsc2", 1, "36", "StrSkill3", "", "usmc", "256")
        for _i in range(2, 6):
            _set_dsc_line(sh_d, "dsc2", _i, "", "", "", "", "")
        _clear_dsc3_synergies(sh_d, "Skillname273")
        _set_dsc_line(sh_d, "dsc3", 2, "76", "Damplev", "Skillname267", "par8", "")

    # Blade Sentinel (Id 257) <-> Blade Shield (Id 277) (+20%/lvl each -> +400% max synergy)
    # Blade Fury (Id 266) <-> Shuriken (Inferno Sentry, Id 272) (Blade Fury gets +20%/lvl -> +400% max synergy)
    if "Blade Sentinel" in by_name:
        bsn = by_name["Blade Sentinel"]
        bsn["Param8"] = "20"
        bsn["DmgSymPerCalc"] = "skill('Blade Shield'.blvl)*par8"
    if "blade sentinel" in by_desc:
        bsn_d = by_desc["blade sentinel"]
        _clear_dsc3_synergies(bsn_d, "Skillname258")
        _set_dsc_line(bsn_d, "dsc3", 2, "76", "Damplev", "Skillname278", "par8", "")

    if "Blade Shield" in by_name:
        bsh = by_name["Blade Shield"]
        bsh["Param8"] = "20"
        bsh["DmgSymPerCalc"] = "skill('Blade Sentinel'.blvl)*par8"
    if "blade shield" in by_desc:
        bsh_d = by_desc["blade shield"]
        _clear_dsc3_synergies(bsh_d, "Skillname278")
        _set_dsc_line(bsh_d, "dsc3", 2, "76", "Damplev", "Skillname258", "par8", "")

    if "Blade Fury" in by_name:
        bf = by_name["Blade Fury"]
        bf["Param8"] = "20"
        bf["DmgSymPerCalc"] = "skill('Inferno Sentry'.blvl)*par8"
    if "blade fury" in by_desc:
        bf_d = by_desc["blade fury"]
        _clear_dsc3_synergies(bf_d, "Skillname267")
        _set_dsc_line(bf_d, "dsc3", 2, "76", "Damplev", "Skillname273", "par8", "")

    # Mind Blast (Id 273) — remove leftover vanilla Psychic Hammer (now Flow) conversion synergy
    if "Mind Blast" in by_name:
        mb = by_name["Mind Blast"]
        mb["calc1"] = "dm56"
        mb["Param8"] = ""
        mb["*Param8 Description"] = ""

    # Step 5e: Flow (Psychic Hammer slot, Id 253) - passive chance NOT to consume orbs when using a Finishing Move.
    #   Uses the vanilla (Mosaic) stat item_charge_noconsume: 20% at Lvl 1 -> 50% at Lvl 20 (30/19 per level),
    #   capped at 75% with lots of +skills.  (Trap casts always clear orbs; a trap keep-roll was tried and could not be
    #   made to work.)
    if "Psychic Hammer" in by_name:
        fl = by_name["Psychic Hammer"]
        for k in ("srvstfunc", "srvdofunc", "stsuccessonly", "stsound", "tgtoverlay", "tgtsound", "castoverlay",
                  "cltstfunc", "cltdofunc", "UseAttackRate", "LineOfSight", "TargetableOnly", "SearchEnemyNear",
                  "KeepCursorStateOnKill", "rightskill", "leftskill", "mana", "lvlmana", "minmana", "manashift",
                  "calc1", "*calc1 desc", "calc2", "*calc2 desc", "calc3", "*calc3 desc", "calc4", "*calc4 desc",
                  "Param1", "*Param1 Description", "Param3", "*Param3 Description", "Param4", "*Param4 Description",
                  "Param5", "*Param5 Description", "Param6", "*Param6 Description",
                  "MinDam", "MaxDam", "EType", "EMin", "EMax") + tuple(
                      f"{p}{n}" for p in ("MinLevDam", "MaxLevDam", "EMinLev", "EMaxLev") for n in range(1, 6)):
            if k in fl:
                fl[k] = ""
        fl["range"] = "none"
        fl["passive"] = "1"
        fl["aitype"] = "10"
        fl["UseAttackRate"] = "1"
        fl["leftskill"] = "0"
        fl["rightskill"] = "0"
        fl["minmana"] = "0"
        fl["manashift"] = "8"
        fl["mana"] = "0"
        fl["lvlmana"] = "0"
        fl["passivestate"] = "ass_flow_passive"  # every passive skill in D2R requires a passivestate to attach passivestat1..5
        fl["passivestat1"] = "item_charge_noconsume"
        fl["passivecalc1"] = "min(75, 20 + (lvl-1)*30/19)"
        fl["HitShift"] = "8"
    if "psychic hammer" in by_desc:
        fl_d = by_desc["psychic hammer"]
        fl_d["descdam"] = ""
        _set_dsc_line(fl_d, "desc", 1, "74", "ModFlowNoConsume", "", "min(75, 20 + (lvl-1)*30/19)", "")
        for _i in range(2, 6):
            _set_dsc_line(fl_d, "desc", _i, "", "", "", "", "")
        for _i in range(1, 6):
            _set_dsc_line(fl_d, "dsc2", _i, "", "", "", "", "")

    # Step 5f: Lethality (Claw Mastery slot, Id 252) - universal melee mastery: +Attack Rating % and +Damage % only
    #   (no Critical/Deadly Strike).  Toned down from vanilla Claw Mastery (30+10 AR, 35+4 dmg, 0-25 crit):
    #   +30% AR +8/lvl (182% at 20), +25% damage +4/lvl (101% at 20) -- just under the Barbarian weapon masteries.
    if "Claw Mastery" in by_name:
        lm = by_name["Claw Mastery"]
        lm["passiveitype"] = "mele"  # all melee weapons (claws, daggers, swords, staves, polearms...)
        lm["itypea1"] = ""
        lm["passivestat1"] = "passive_mastery_melee_th"
        lm["passivecalc1"] = "ln12"
        lm["passivestat2"] = "passive_mastery_melee_dmg"
        lm["passivecalc2"] = "ln34"
        lm["passivestat3"] = ""
        lm["passivecalc3"] = ""
        lm["Param1"] = "30"
        lm["Param2"] = "8"
        lm["Param3"] = "25"
        lm["Param4"] = "4"
        for k in ("Param5", "*Param5 Description", "Param6", "*Param6 Description"):
            lm[k] = ""
    if "claw mastery" in by_desc:
        lm_d = by_desc["claw mastery"]
        _set_dsc_line(lm_d, "desc", 1, "74", "StrSkill22", "", "ln12", "")
        _set_dsc_line(lm_d, "desc", 2, "74", "StrSkillDamagePercent", "", "ln34", "")
        for _i in range(3, 6):
            _set_dsc_line(lm_d, "desc", _i, "", "", "", "", "")

    # Step 5g: Burst of Speed (Quickness, Id 258) & Fade (Id 267):
    #   22s (550 frames) at Lvl 1 -> 60s (1500 frames) at Lvl 20 (+2s / 50 frames per level).
    _short_buff_len = "ln56"
    for _sk, _sd in (("Quickness", "quickness"), ("Fade", "fade")):
        if _sk in by_name:
            _b = by_name[_sk]
            _b["Param5"] = "550"
            _b["Param6"] = "50"
            _b["*Param6 Description"] = "Duration per level (frames)"
            _b["auralencalc"] = _short_buff_len
        if _sd in by_desc:
            by_desc[_sd]["desccalca1"] = _short_buff_len

    # Step 5h: Shadow Bind (Shadow Warrior slot, Id 268, Col 2 Row 4) - Pinpoint single-target Shadow Hex that works
    #   on Super Uniques and Act Bosses (aurafilter=3, same as Decrepify). Pins the target nearly in place
    #   (velocitypercent: -60% -> -90%) and slows its Attack/Cast speed and Attack Rating (-25% -> -54%) for 6s -> 13.6s.
    if "Shadow Warrior" in by_name:
        sb = by_name["Shadow Warrior"]
        for k in list(sb.keys()):
            if k.startswith(("aurastat", "passivestat", "passivecalc")) or k in (
                    "srvdofunc", "srvstfunc", "cltdofunc", "cltstfunc", "aurastate", "auralencalc", "summon", "pettype",
                    "petmax", "summode", "sumumod", "sumskill1", "sumsk1calc", "stsound", "LineOfSight", "localdelay",
                    "lvlmana", "mana", "minmana", "InTown", "Param1", "*Param1 Description", "Param2",
                    "*Param2 Description", "Param3", "*Param3 Description", "Param5", "*Param5 Description",
                    "Param6", "*Param6 Description", "passive", "passivestate", "passiveitype",
                    "passivereqweaponcount", "itypea1"):
                sb[k] = ""
        sb["srvdofunc"] = "30"
        sb["cltstfunc"] = "18"
        sb["cltdofunc"] = "30"
        sb["aurafilter"] = "3"  # hits all monsters including Champions, Uniques, Super Uniques, and Act Bosses
        sb["auratargetstate"] = "ass_shadow_bind"
        sb["auralencalc"] = "par3+(lvl-1)*par4"
        sb["aurarangecalc"] = "3"  # tight pinpoint radius (~2 yards) around cursor so it targets a single boss/elite
        sb["aurastat1"] = "velocitypercent"
        sb["aurastatcalc1"] = "-dm12"
        sb["aurastat2"] = "attackrate"
        sb["aurastatcalc2"] = "-dm56"
        sb["aurastat3"] = "other_animrate"
        sb["aurastatcalc3"] = "-dm56"
        sb["aurastat4"] = "item_tohit_percent"
        sb["aurastatcalc4"] = "-dm56"
        sb["stsound"] = "assassin_psychichammer"
        sb["castoverlay"] = "psychic_hammer_curse"
        sb["range"] = "none"
        sb["anim"] = "SC"
        sb["seqtrans"] = "SC"
        sb["monanim"] = "SC"
        sb["UseAttackRate"] = "1"
        sb["LineOfSight"] = "4"
        sb["reqlevel"] = "24"
        sb["reqskill1"] = "Cloak of Shadows"
        sb["reqskill2"] = "Weapon Block"
        sb["leftskill"] = "0"
        sb["rightskill"] = "1"
        sb["minmana"] = "1"
        sb["manashift"] = "8"
        sb["mana"] = "12"
        sb["lvlmana"] = "0"
        sb["interrupt"] = "1"
        sb["Param1"] = "60"
        sb["*Param1 Description"] = "Enemy Move Speed Slow % Min"
        sb["Param2"] = "95"
        sb["*Param2 Description"] = "Enemy Move Speed Slow % Max"
        sb["Param3"] = "150"
        sb["*Param3 Description"] = "Duration baseline (frames)"
        sb["Param4"] = "10"
        sb["*Param4 Description"] = "Duration per level (frames)"
        sb["Param5"] = "25"
        sb["*Param5 Description"] = "Enemy Attack/Cast Speed & AR Slow % Min"
        sb["Param6"] = "60"
        sb["*Param6 Description"] = "Enemy Attack/Cast Speed & AR Slow % Max"
        sb["HitShift"] = "8"
        sb["aitype"] = "2"
    if "shadow warrior" in by_desc:
        sb_d = by_desc["shadow warrior"]
        _set_dsc_line(sb_d, "desc", 1, "74", "ModShadowBindMove", "", "dm12", "")
        _set_dsc_line(sb_d, "desc", 2, "74", "ModShadowBindAttack", "", "dm56", "")
        _set_dsc_line(sb_d, "desc", 3, "74", "ModShadowBindAR", "", "dm56", "")
        _set_dsc_line(sb_d, "desc", 4, "36", "StrSkillDurationSingular", "StrSkill20", "par3+(lvl-1)*par4", "25")
        _set_dsc_line(sb_d, "desc", 5, "", "", "", "", "")
        _set_dsc_line(sb_d, "dsc2", 1, "36", "StrSkill3", "", "usmc", "256")
        for _i in range(2, 6):
            _set_dsc_line(sb_d, "dsc2", _i, "", "", "", "", "")

    # Step 6: Reorganize Assassin Tree 1 (Traps & Blades, SkillPage=1) and Tree 3 (Martial Arts, SkillPage=3)
    # into the Staggered 8-Level Ladder (leaving Tree 2: Shadow Disciplines untouched):
    #   - Tree 3 (Martial Arts, SkillPage=3):
    #       Row 1 (Lvl 1):  Tiger Strike (Col 2), Dragon Talon (Col 3)
    #       Row 2 (Lvl 8):  Fists of Fire (Col 1)
    #       Row 3 (Lvl 16): Blades of Ice (Col 1, req Fists of Fire), Dragon Claw (Col 2, req Tiger Strike)
    #       Row 4 (Lvl 24): Claws of Thunder (Col 1, req Blades of Ice), Dragon Tail (Col 3, req Dragon Talon)
    #       Row 5 (Lvl 32): Cobra Strike (Col 2, req Dragon Claw), Dragon Flight (Col 3, req Dragon Tail)
    #       Row 6 (Lvl 40): Omnislash / Royal Strike (Col 1, req Claws of Thunder & Cobra Strike)
    #   - Tree 1 (Traps & Blades, SkillPage=1):
    #       Row 1 (Lvl 1):  Caltrops / Shock Field (Col 2), Blade Sentinel (Col 3)
    #       Row 2 (Lvl 8):  Shrapnel Sentry / Fire Trauma (Col 2, req Caltrops)
    #       Row 3 (Lvl 16): Fire Sentry / Wake of Fire Sentry (Col 1, req Shrapnel Sentry), Blade Fury (Col 3, req Blade Sentinel)
    #       Row 4 (Lvl 24): Ice Sentry / Death Sentry (Col 1, req Fire Sentry)
    #       Row 5 (Lvl 32): Lightning Sentry (Col 1, req Ice Sentry), Blade Shield (Col 3, req Blade Fury)
    #       Row 6 (Lvl 40): Soul Siphon Sentry / Charged Bolt Sentry (Col 2, req Shrapnel Sentry & Blade Shield),
    #                       Shuriken / Inferno Sentry (Col 3, req Blade Shield)
    ass_tree_layout = [
        # (skill_name, skilldesc_name, reqlevel, page, row, col, reqskill1, reqskill2)
        ("Shock Field", "shock field", "1", "1", "1", "2", "", ""),
        ("Blade Sentinel", "blade sentinel", "1", "1", "1", "3", "", ""),
        ("Fire Trauma", "fire trauma", "8", "1", "2", "2", "Shock Field", ""),
        ("Wake of Fire Sentry", "wake of fire sentry", "16", "1", "3", "1", "Fire Trauma", ""),
        ("Blade Fury", "blade fury", "16", "1", "3", "3", "Blade Sentinel", ""),
        ("Death Sentry", "death sentry", "24", "1", "4", "1", "Wake of Fire Sentry", ""),
        ("Lightning Sentry", "lightning sentry", "32", "1", "5", "1", "Death Sentry", ""),
        ("Blade Shield", "blade shield", "32", "1", "5", "3", "Blade Fury", ""),
        ("Charged Bolt Sentry", "charged bolt sentry", "40", "1", "6", "2", "Fire Trauma", "Blade Shield"),
        ("Inferno Sentry", "inferno sentry", "40", "1", "6", "3", "Blade Shield", ""),
        ("Tiger Strike", "tiger strike", "1", "3", "1", "2", "", ""),
        ("Dragon Talon", "dragon talon", "1", "3", "1", "3", "", ""),
        ("Fists of Fire", "fists of fire", "8", "3", "2", "1", "", ""),
        ("Blades of Ice", "blades of ice", "16", "3", "3", "1", "Fists of Fire", ""),
        ("Dragon Claw", "dragon claw", "16", "3", "3", "2", "Tiger Strike", ""),
        ("Claws of Thunder", "claws of thunder", "24", "3", "4", "1", "Blades of Ice", ""),
        ("Dragon Tail", "dragon tail", "24", "3", "4", "3", "Dragon Talon", ""),
        ("Cobra Strike", "cobra strike", "32", "3", "5", "2", "Dragon Claw", ""),
        ("Dragon Flight", "dragon flight", "32", "3", "5", "3", "Dragon Tail", ""),
        ("Royal Strike", "royal strike", "40", "3", "6", "1", "Claws of Thunder", "Cobra Strike"),
        # Tree 2 (Shadow Disciplines, SkillPage=2):
        ("Claw Mastery", "claw mastery", "1", "2", "1", "3", "", ""),
        ("Cloak of Shadows", "cloak of shadows", "8", "2", "2", "1", "", ""),
        ("Weapon Block", "weapon block", "8", "2", "2", "2", "Claw Mastery", ""),
        ("Shadow Warrior", "shadow warrior", "16", "2", "3", "1", "Cloak of Shadows", ""),
        ("Quickness", "quickness", "16", "2", "3", "3", "Claw Mastery", ""),
        ("Mind Blast", "mind blast", "24", "2", "4", "1", "Shadow Warrior", ""),
        ("Fade", "fade", "32", "2", "5", "2", "Weapon Block", ""),
        ("Venom", "venom", "32", "2", "5", "3", "Quickness", ""),
        ("Shadow Master", "shadow master", "40", "2", "6", "1", "Fade", "Mind Blast"),
        ("Psychic Hammer", "psychic hammer", "40", "2", "6", "3", "Venom", ""),
    ]
    for sk_name, desc_name, req_lvl, pg, s_row, s_col, req1, req2 in ass_tree_layout:
        if sk_name in by_name:
            sk_r = by_name[sk_name]
            sk_r["reqlevel"] = req_lvl
            sk_r["reqskill1"] = req1
            sk_r["reqskill2"] = req2
            sk_r["reqskill3"] = ""
        if desc_name in by_desc:
            d_r = by_desc[desc_name]
            d_r["SkillPage"] = pg
            d_r["SkillRow"] = s_row
            d_r["SkillColumn"] = s_col
            d_r["ListRow"] = pg

    # Step 6b: Assassin Mana Cost Balancing across all 3 trees:
    #   - Physical & Sustain Charge-Ups (Tiger Strike, Cobra Strike): very low flat mana (1 - 1.5)
    #   - Elemental Charge-Ups (Fists of Fire, Blades of Ice, Claws of Thunder): low but higher than physical (2.5->4.9 to 3.5->5.9)
    #   - Physical & Sustain Traps (Caltrops, Shrapnel Sentry, Soul Siphon Sentry): moderate mana (5->9.8 to 10->19.5)
    #   - Elemental Traps (Fire Sentry, Ice Sentry, Lightning Sentry): high mana scaling (18->46.5, 22->50.5, 25->63)
    #   - Blade Skills (Blade Sentinel, Blade Fury, Blade Shield, Shuriken): substantial mana costs
    #   - Short-Term Strategic Bursts (Burst of Speed, Fade, Venom): high mana consumption (25->53.5, 30->68, 25->53.5)
    ass_mana_table = [
        # (skill_name, manashift, mana, lvlmana, minmana)
        # 1. Charge-Ups
        ("Tiger Strike", "8", "1", "0", "1"),           # 1.0 flat
        ("Cobra Strike", "7", "3", "0", "1"),           # 1.5 flat
        ("Fists of Fire", "5", "20", "1", "2"),         # 2.5 at Lvl 1 -> 4.9 at Lvl 20
        ("Blades of Ice", "5", "24", "1", "3"),         # 3.0 at Lvl 1 -> 5.4 at Lvl 20
        ("Claws of Thunder", "5", "28", "1", "3"),      # 3.5 at Lvl 1 -> 5.9 at Lvl 20
        # 2. Finishers
        ("Dragon Claw", "8", "4", "0", "4"),            # 4.0 flat
        ("Dragon Talon", "8", "6", "0", "6"),           # 6.0 flat
        ("Dragon Tail", "8", "10", "0", "10"),          # 10.0 flat
        ("Dragon Flight", "8", "18", "0", "18"),        # 18.0 flat
        ("Royal Strike", "8", "8", "0", "8"),           # 8.0 flat (Omnislash)
        # 3. Physical & Sustain Traps (considerably cheaper than Elemental Traps)
        ("Shock Field", "6", "20", "1", "5"),           # Caltrops: 5.0 at Lvl 1 -> 9.8 at Lvl 20
        ("Fire Trauma", "7", "16", "1", "8"),           # Shrapnel Sentry: 8.0 at Lvl 1 -> 17.5 at Lvl 20
        ("Charged Bolt Sentry", "7", "20", "1", "10"),  # Soul Siphon Sentry: 10.0 at Lvl 1 -> 19.5 at Lvl 20
        # 4. Elemental Traps (require a large mana pool when heavily invested)
        ("Wake of Fire Sentry", "7", "36", "3", "18"),  # Fire Sentry: 18.0 at Lvl 1 -> 46.5 at Lvl 20
        ("Death Sentry", "7", "44", "3", "22"),         # Ice Sentry: 22.0 at Lvl 1 -> 50.5 at Lvl 20
        ("Lightning Sentry", "8", "25", "2", "25"),     # Lightning Sentry: 25.0 at Lvl 1 -> 63.0 at Lvl 20
        # 5. Blade Skills
        ("Blade Sentinel", "8", "12", "1", "12"),       # Blade Sentinel: 12.0 at Lvl 1 -> 31.0 at Lvl 20
        ("Blade Fury", "6", "12", "1", "3"),            # Blade Fury: 3.0/blade (~12.5/s) at Lvl 1 -> 7.8/blade (~32/s) at Lvl 20
        ("Blade Shield", "8", "30", "2", "30"),         # Blade Shield: 30.0 at Lvl 1 -> 68.0 at Lvl 20
        ("Inferno Sentry", "6", "20", "1", "5"),        # Shuriken: 5.0/throw (~18.5/s) at Lvl 1 -> 9.8/throw (~36/s) at Lvl 20
        # 6. Shadow Disciplines Active Skills & Short-Term Bursts
        ("Quickness", "7", "50", "3", "25"),            # Burst of Speed: 25.0 at Lvl 1 -> 53.5 at Lvl 20
        ("Fade", "8", "30", "2", "30"),                 # Fade: 30.0 at Lvl 1 -> 68.0 at Lvl 20
        ("Venom", "7", "50", "3", "25"),                # Venom: 25.0 at Lvl 1 -> 53.5 at Lvl 20
        ("Cloak of Shadows", "7", "30", "1", "15"),     # Cloak of Shadows: 15.0 at Lvl 1 -> 24.5 at Lvl 20
        ("Shadow Warrior", "7", "30", "1", "15"),       # Shadow Bind: 15.0 at Lvl 1 -> 24.5 at Lvl 20
        ("Mind Blast", "7", "36", "1", "18"),           # Mind Blast: 18.0 at Lvl 1 -> 27.5 at Lvl 20
        ("Shadow Master", "8", "40", "1", "40"),        # Shadow Master: 40.0 at Lvl 1 -> 59.0 at Lvl 20
    ]
    for _sk_name, _ms, _m, _lvlm, _minm in ass_mana_table:
        if _sk_name in by_name:
            _r = by_name[_sk_name]
            _r["manashift"] = _ms
            _r["mana"] = _m
            _r["lvlmana"] = _lvlm
            _r["minmana"] = _minm

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
        (61025, "ModActivePctPDR", "Physical Damage Reduced by %d%%"),
        (61026, "StrSkillMagicDamageToYourAttack", "Magic Damage To Your Attack: %d-%d"),
        (61027, "ModActiveFlatMDR", "Magic Damage Reduced by %d"),
        (0, "skillsd124", "aura - restores life and mana after each kill"),
        (0, "skillld124", "when active, aura restores life and mana after each kill\nwhile periodically redeeming nearby slain enemies"),
        (0, "skillxld124", "when active, aura restores life and mana after each kill\nwhile periodically redeeming nearby slain enemies"),
        (0, "skillld112", "hurls an ethereal hammer that bounces between nearby enemies,\ndealing magic damage, knocking back, and stunning targets"),
        (0, "skillld117", "enhances your shield with divine power, increasing blocking\nand reducing physical and magic damage taken"),
        (0, "skillsd111", "cleaving attacks add elemental damage"),
        (0, "skillld111", "cleaves enemies in a frontal arc, adding fire, lightning,\nand cold damage to each successful attack"),
        (0, "skillsd123", "aura - demoralizes and weakens enemies"),
        (0, "skillld123", "when active, aura demoralizes nearby enemies, sapping their speed\nand attack power while shattering their defenses and resistances"),
        (0, "skillxld123", "when active, aura demoralizes nearby enemies, sapping their speed\nand attack power while shattering their defenses and resistances"),
        (0, "skillsd104", "aura - increases defense and reduces physical damage"),
        (0, "skillld104", "when active, aura bolsters the defense of you and your party\nand reduces physical damage taken from attacks"),
        (0, "skillsd115", "aura - increases movement speed and hit recovery"),
        (0, "skillld115", "when active, aura increases movement speed and hit recovery\nfor you and your party to swiftly reposition in battle"),
        (61028, "ModDismissAuraName", "Dismiss Aura"),
        (61029, "ModDismissAuraDesc", "deactivates your current active aura"),
        # Barbarian Stamina Pendulum ("Well-Rested vs. Exhaustion / Last Stand") Strings
        (61030, "ModBarStamRestore", "Stamina Restored: +%d"),
        (61031, "ModBarStamOnHitKill", "Stamina Restored on Hit or Kill: +%d"),
        (61032, "ModBarStamCostJump", "Stamina Cost: %d"),
        (61033, "ModBarStamCostSwing", "Stamina Cost: %d"),
        (61034, "ModBarStamCostSpin", "Stamina Cost per Strike: %d"),
        (61035, "ModBarWellRestedBonus", "Well-Rested Bonus: Up to +%d%% Damage at Full Stamina"),
        (61036, "ModBarExhaustedBonus", "Exhaustion Bonus: Up to +%d%% Damage at Zero Stamina"),
        (61037, "ModBarFHRPassive", "Faster Hit Recovery: +%d%%"),
        (61038, "ModBarMaxStamFlat", "Max Stamina: +%d"),
        (61039, "ModBarBloodlustMaxDmg", "Max Damage Bonus at Zero Stamina: +%d%%"),
        (61040, "ModBarBloodlustCurDmg", "Current Exhaustion Damage Bonus: +%d%%"),
        (61041, "ModBarBloodlustMaxAR", "Max Attack Rating at Zero Stamina: +%d%%"),
        (61042, "ModBarBloodlustCurAR", "Current Exhaustion Attack Rating Bonus: +%d%%"),
        (61043, "ModBarBloodlustDrain", "Life Drained per Second: -%d"),
        (61044, "ModBarShieldBlockDmg", "Shield Block Damage Bonus: +%d%%"),
        (61045, "ModBarShoutFBR", "Faster Block Rate: +%d%%"),
        (61046, "ModBarShockwaveConeDmg", "Shockwave Cone Damage: %d-%d"),
        (61047, "ModBarAttackSpeedPassive", "Attack Speed: +%d%%"),
        (61048, "ModBarPoisonLenRedPassive", "Poison Length Reduced by %d%%"),
        (61049, "ModBarMaxPoisResPassive", "Maximum Poison Resist: +%d%%"),
        (61050, "ModBarLifeRestore", "Life Restored: +%d"),
        (61051, "ModBarWarCryPhysMagBreak", "Enemy Physical & Magic Resistance: %+d%%"),
        (61052, "ModSynFlatPDRPerLev", "%s: +%d Physical Damage Reduced per Level"),
        (61053, "ModSynMaxStamPerLev", "%s: +%d Max Stamina per Level"),
        (61054, "ModSynLifeRestorePerLev", "%s: +%d Life Restored per Level"),
        (61055, "ModSynPhysMagBreakPerLev", "%s: -%d%% Enemy Physical & Magic Resistance per Level"),
        (61056, "ModBarStamDegradePenalty", "Exhaustion Penalty: Down to %d%% Damage at Zero Stamina"),
        # Combat Masteries (127 One-Handed Mastery, 128 Two-Handed Mastery, 135 Throwing Mastery,
        #                   134 Critical Strike, 129 Battle Fervor, 136 Venom Ward)
        (0, "skillname127", "One-Handed Mastery"),
        (0, "skillan127", "One-Handed Mastery"),
        (0, "skillsd127", "passive - improves one-handed melee skill"),
        (0, "skillld127", "passive - improves one-handed melee fighting skill"),
        (0, "skillname128", "Two-Handed Mastery"),
        (0, "skillan128", "Two-Handed Mastery"),
        (0, "skillsd128", "passive - improves two-handed melee skill"),
        (0, "skillld128", "passive - improves two-handed melee fighting skill"),
        (0, "skillsd135", "passive - improves thrown weapon skill"),
        (0, "skillld135", "passive - improves thrown weapon skill"),
        (0, "skillname134", "Critical Strike"),
        (0, "skillan134", "Critical Strike"),
        (0, "skillsd134", "passive - chance to deal double damage"),
        (0, "skillld134", "passive - chance to deal double physical damage"),
        (0, "skillname129", "Battle Fervor"),
        (0, "skillan129", "Battle Fervor"),
        (0, "skillsd129", "passive - increases attack speed"),
        (0, "skillld129", "passive - increases attack speed"),
        (0, "skillname136", "Venom Ward"),
        (0, "skillan136", "Venom Ward"),
        (0, "skillsd136", "passive - reduces poison duration and raises max poison resist"),
        (0, "skillld136", "passive - reduces poison duration and raises max poison resist"),
        # Tactical / Well-Rested Skills (126 Strike, 139 Shield Slam, 144 Concentrate)
        (0, "skillname126", "Strike"),
        (0, "skillan126", "Strike"),
        (0, "skillsd126", "heavy blow - stronger while well-rested"),
        (0, "skillld126", "powerful blow that knocks back target\ndeals more damage with high stamina"),
        (0, "skillname139", "Shield Slam"),
        (0, "skillan139", "Shield Slam"),
        (0, "skillsd139", "requires a shield - charges and stuns target"),
        (0, "skillld139", "requires a shield\ncharges and stuns target; deals more damage with high stamina"),
        (0, "skillname144", "Concentrate"),
        (0, "skillan144", "Concentrate"),
        (0, "skillsd144", "uninterruptible attack - stronger while well-rested"),
        (0, "skillld144", "uninterruptible attack that improves defense\ndeals more damage with high stamina"),
        # Exhaustion / Berserker Skills (133 Flurry, 140 Barrage, 147 Frenzy, 152 Berserk)
        (0, "skillname133", "Flurry"),
        (0, "skillan133", "Flurry"),
        (0, "skillsd133", "attacks with two weapons - stronger while exhausted"),
        (0, "skillld133", "rapidly attacks with two weapons\ndeals more damage as stamina is depleted"),
        (0, "skillname140", "Barrage"),
        (0, "skillan140", "Barrage"),
        (0, "skillsd140", "throws two weapons - stronger while exhausted"),
        (0, "skillld140", "throws both equipped weapons\ndeals more damage as stamina is depleted"),
        (0, "skillname147", "Frenzy"),
        (0, "skillan147", "Frenzy"),
        (0, "skillsd147", "swings two weapons - stronger while exhausted"),
        (0, "skillld147", "swings two weapons and increases speed on hit\ndeals more damage as stamina is depleted"),
        (0, "skillname152", "Berserk"),
        (0, "skillan152", "Berserk"),
        (0, "skillsd152", "two-handed magic attack - stronger while exhausted"),
        (0, "skillld152", "requires a two-handed weapon\nconverts damage to magic and drops defense to zero\ndeals more damage as stamina is depleted"),
        # Stamina Spenders (132 Leap, 143 Leap Attack, 151 Whirlwind)
        (0, "skillsd132", "leaps and knocks back - weakens as stamina falls"),
        (0, "skillld132", "leaps and knocks back nearby enemies\nconsumes stamina; range and speed degrade as stamina is depleted"),
        (0, "skillsd143", "leaps to attack target - weakens as stamina falls"),
        (0, "skillld143", "leaps to attack target and stuns nearby enemies\nconsumes stamina; damage and stun degrade as stamina is depleted"),
        (0, "skillsd151", "whirling attack - weakens as stamina falls"),
        (0, "skillld151", "whirling dance of death\nconsumes stamina; damage degrades as stamina is depleted"),
        # Warcries & Passives (131 Second Wind, 138 Shout, 141 Unflinching, 142 Enduring Cry, 149 Battle Orders, 150 Bloodlust, 154 War Cry, 155 Battle Command)
        (0, "skillname131", "Second Wind"),
        (0, "skillan131", "Second Wind"),
        (0, "skillsd131", "restores stamina"),
        (0, "skillld131", "restores stamina to you and your party"),
        (0, "skillname138", "Shout"),
        (0, "skillan138", "Shout"),
        (0, "skillsd138", "reduces damage taken by you and your party"),
        (0, "skillld138", "reduces damage taken by you and your party"),
        (0, "skillname141", "Unflinching"),
        (0, "skillan141", "Unflinching"),
        (0, "skillsd141", "passive - improves hit recovery speed"),
        (0, "skillld141", "passive - improves hit recovery speed"),
        (0, "skillname142", "Enduring Cry"),
        (0, "skillan142", "Enduring Cry"),
        (0, "skillsd142", "increases maximum stamina for you and your party"),
        (0, "skillld142", "increases maximum stamina for you and your party"),
        (0, "skillsd149", "increases maximum life for you and your party"),
        (0, "skillld149", "increases maximum life for you and your party"),
        (0, "skillname150", "Bloodlust"),
        (0, "skillan150", "Bloodlust"),
        (0, "skillsd150", "boosts exhausted attacks, drains life"),
        (0, "skillld150", "boosts exhausted attacks for you, but drains life"),
        (0, "skillsd154", "stuns nearby enemies and lowers their resistances"),
        (0, "skillld154", "stuns nearby enemies and lowers their\nphysical and magic resistance"),
        (0, "skillsd155", "restores life"),
        (0, "skillld155", "restores life to you and your party"),
        # Assassin Overhaul Strings (Shrapnel Sentry, Tiger Strike, Fire Sentry & Flamestrike)
        (0, "Skillname252", "Shrapnel Sentry"),
        (0, "Skillan252", "Shrapnel Sentry"),
        (0, "Skillsd252", "trap that fires spinning razor blades"),
        (
            0,
            "Skillld252",
            "deploys a sentry that fires spinning razor blades at enemies\nconsumes Tiger Strike charges to increase\nshots, velocity, range, and open wounds",
        ),
        (61059, "ModShrapnelSentryMaxTraps", "Maximum Active Shrapnel Sentries: %d"),
        (0, "Skillsd255", "Charge-up Skill - boosts melee damage and empowers Shrapnel Sentry"),
        (
            0,
            "Skillld255",
            "Charge-up Skill\n\nbuilds up to 3 physical orbs that boost melee damage\nrelease charges with a finishing move or cast Shrapnel Sentry",
        ),
        (61064, "ModTigerStrikeOrb1", "Charge 1 Finisher - Shockwave Ring: %d-%d"),
        (61065, "ModTigerStrikeOrb2", "Charge 2 Finisher - Heavy Shockwave: %d-%d"),
        (61066, "ModTigerStrikeOrb3", "Charge 3 Finisher - Max Shockwave: %d-%d"),
        (61067, "ModTigerStrikeHoldBuff", "Held Charge Bonus: +%d%% Damage per Orb"),
        (0, "Skillname263", "Fire Sentry"),
        (0, "Skillan263", "Fire Sentry"),
        (0, "Skillsd263", "trap that fires exploding fireballs"),
        (
            0,
            "Skillld263",
            "deploys a sentry that fires exploding fireballs\nconsumes Flamestrike charges to increase\nshots, range, velocity, and stun on impact",
        ),
        (61057, "ModFireSentryMaxTraps", "Maximum Active Fire Sentries: %d"),
        (61058, "ModFireSentryChargedShots", "Charged Shots (1+ Orbs): %d"),
        (0, "Skillname260", "Flamestrike"),
        (0, "Skillan260", "Flamestrike"),
        (0, "Skillsd260", "Charge-up Skill - adds fire damage and empowers Fire Sentry"),
        (
            0,
            "Skillld260",
            "Charge-up Skill\n\nbuilds up to 3 fire orbs that add fire damage to melee attacks\nrelease charges with a finishing move or cast Fire Sentry",
        ),
        (61060, "ModFistsOfFireOrb1", "Charge 1 Finisher - Fire Explosion: %d-%d"),
        (61061, "ModFistsOfFireOrb2", "Charge 2 Finisher - Burning Ground: %d-%d per second"),
        (61062, "ModFistsOfFireOrb3", "Charge 3 Finisher - Crashing Meteor: %d-%d"),
        (61063, "ModFistsOfFireHoldBuff", "Held Charge Bonus: +%d-%d Fire Damage per Orb"),
        (0, "Skillname262", "Soul Siphon Sentry"),
        (0, "Skillan262", "Soul Siphon Sentry"),
        (0, "Skillsd262", "trap that fires piercing unholy bolts"),
        (
            0,
            "Skillld262",
            "deploys a sentry that fires piercing unholy bolts\ndealing magic damage to enemies\nconsumes Cobra Strike charges to increase\nshots, velocity, range, and apply small-radius life tap",
        ),
        (0, "Skillsd266", "Charge-up Skill - shreds defense and empowers Soul Siphon Sentry"),
        (
            0,
            "Skillld266",
            "Charge-up Skill\n\nbuilds up to 3 soul orbs that shred monster defense per hit\nrelease charges with a finishing move or cast Soul Siphon Sentry",
        ),
        (61068, "ModCobraStrikeOrb1", "Charge 1 Finisher - Life Steal: %+d%% | Soul-Hex: -%d Defense"),
        (61069, "ModCobraStrikeOrb2", "Charge 2 Finisher - Life & Mana Steal: %+d%% | Soul-Hex: -%d Defense"),
        (61070, "ModCobraStrikeOrb3", "Charge 3 Finisher - Life & Mana Steal: %+d%% | Soul-Hex: -%d Defense"),
        (61071, "ModCobraStrikeHoldBuff", "Held Charge Bonus: -%d to Monster Defense Per Hit per Orb"),
        (61072, "ModSoulSiphonMaxTraps", "Maximum Active Soul Siphon Sentries: %d"),
        (61073, "ModCobraSynergyPerLev", "%s: +%d%% Finisher Leech & Defense Shred per Level"),
        (0, "Skillname277", "Ice Sentry"),
        (0, "Skillan277", "Ice Sentry"),
        (0, "Skillsd277", "trap that fires arctic blast streams"),
        (
            0,
            "Skillld277",
            "deploys a sentry that fires freezing arctic blast streams\nconsumes Blades of Ice charges to increase\nrange, duration, and freeze enemies solid in place",
        ),
        (0, "Skillsd275", "Charge-up Skill - adds cold damage and empowers Ice Sentry"),
        (
            0,
            "Skillld275",
            "Charge-up Skill\n\nbuilds up to 3 ice orbs that add cold damage to melee attacks\nrelease charges with a finishing move or cast Ice Sentry",
        ),
        (61074, "ModBladesOfIceOrb1", "Charge 1 Finisher - Ice Blast: %d-%d"),
        (61075, "ModBladesOfIceOrb2", "Charge 2 Finisher - Ice Blast & Bolts: %d-%d"),
        (61076, "ModBladesOfIceOrb3", "Charge 3 Finisher - Frozen Orb Bolt: %d-%d"),
        (61077, "ModBladesOfIceHoldBuff", "Held Charge Bonus: +%d-%d Cold Damage per Orb"),
        (61078, "ModIceSentryMaxTraps", "Maximum Active Ice Sentries: %d"),
        (61079, "ModIceSentryChargedShots", "Charged Shots (2+ Orbs): %d"),
        (0, "Skillname270", "Electrocute"),
        (0, "Skillan270", "Electrocute"),
        (0, "Skillsd270", "Charge-up Skill - adds lightning damage and empowers Lightning Sentry"),
        (
            0,
            "Skillld270",
            "Charge-up Skill\n\nbuilds up to 3 lightning orbs that add lightning damage to melee attacks\nrelease charges with a finishing move or cast Lightning Sentry",
        ),
        (0, "Skillsd272", "trap that shoots piercing lightning bolts"),
        (
            0,
            "Skillld272",
            "deploys a sentry that shoots piercing lightning bolts\nconsumes Electrocute charges to increase\nrange, duration, and blind enemies with searing flashes",
        ),
        (61080, "ModClawsOfThunderOrb1", "Charge 1 Finisher - Charged Bolts: %d-%d"),
        (61081, "ModClawsOfThunderOrb2", "Charge 2 Finisher - Lightning Nova: %d-%d"),
        (61082, "ModClawsOfThunderOrb3", "Charge 3 Finisher - Chain Lightning: %d-%d"),
        (61083, "ModClawsOfThunderHoldBuff", "Held Charge Bonus: +%d-%d Lightning Damage per Orb"),
        (61084, "ModLightningSentryMaxTraps", "Maximum Active Lightning Sentries: %d"),
        (61085, "ModLightningSentryChargedShots", "Charged Shots (2+ Orbs): %d"),
        (61090, "ModWhirlFireShred", "Nearby Enemies: -%d%% Fire Resistance"),
        (61091, "ModWhirlColdShred", "Nearby Enemies: -%d%% Cold Resistance"),
        (61092, "ModWhirlLightShred", "Nearby Enemies: -%d%% Lightning Resistance"),
        (61093, "ModCaltropsDamage", "Physical Damage per Second: %d-%d"),
        (61094, "ModCaltropsSlow", "Slows Enemies by %d%%"),
        (61095, "ModShurikenDamage", "Adds Physical Damage per Hit: %d-%d"),
        (61096, "ModFlowNoConsume", "Chance Not to Consume Orbs when Using a Finishing Move: %d%%"),
        (0, "Skillname254", "Flow"),
        (0, "Skillan254", "Flow"),
        (0, "Skillsd254", "Passive - chance to keep your orbs when using a finishing move"),
        (0, "Skillld254", "Passive\n\ngives a chance that using a finishing move\ndoes not consume the orbs you are holding"),
        (0, "Skillname253", "Lethality"),
        (0, "Skillan253", "Lethality"),
        (0, "Skillsd253", "Passive - improves attack rating and damage with melee weapons"),
        (0, "Skillld253", "Passive\n\nimproves your attack rating and damage\nwith all melee weapons"),
        (61097, "ModShadowBindMove", "Enemy Movement Speed: -%d%%"),
        (61098, "ModShadowBindAttack", "Enemy Attack and Cast Speed: -%d%%"),
        (61099, "ModShadowBindAR", "Enemy Attack Rating: -%d%%"),
        (0, "Skillname269", "Shadow Bind"),
        (0, "Skillan269", "Shadow Bind"),
        (0, "Skillsd269", "binds a target in shadow, slowing its movement and attacks"),
        (
            0,
            "Skillld269",
            "binds a target in tendrils of shadow\ncrippling its movement speed, attack speed, and accuracy\neffective against unique monsters and bosses",
        ),
        (0, "Skillname257", "Caltrops"),
        (0, "Skillan257", "Caltrops"),
        (0, "Skillsd257", "scatters spiked caltrops that damage enemies"),
        (
            0,
            "Skillld257",
            "throws a cluster of spiked caltrops onto the ground\nthat damage enemies walking over them",
        ),
        (0, "Skillname273", "Shuriken"),
        (0, "Skillan273", "Shuriken"),
        (0, "Skillsd273", "hurls a heavy shuriken that bounces between enemies"),
        (
            0,
            "Skillld273",
            "hurls a heavy razor-sharp shuriken that bounces\nbetween nearby enemies, slicing through each\nfor heavy physical damage",
        ),
        (0, "Skillname281", "Omnislash"),
        (0, "Skillan281", "Omnislash"),
        (0, "Skillsd281", "Spin through nearby enemies while keeping your held orbs"),
        (
            0,
            "Skillld281",
            "Does not release orbs\n\nspin through nearby enemies, striking with your weapon\nand any held orb damage; enemies near you\ntemporarily lose elemental resistance",
        ),
    ]
    entries = upsert_string_entries(entries, updates)
    return write_strings_json("skills.json", entries)


def _build_submenu_skillicon_pair(suffix: str, frame_w: int, frame_h: int) -> str:
    """
    Append frames 40 (normal) and 41 (pressed) to data/hd/global/ui/spells/submenu/skillicon{suffix}
    for "Dismiss Aura" (IconCel=40): a hollow circular aura ring with a carved diagonal X across it.
    """
    import math
    import os
    import struct
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    sub_src = os.path.join(VANILLA_ROOT, f"data/hd/global/ui/spells/submenu/skillicon{suffix}")
    pal_src = os.path.join(VANILLA_ROOT, f"data/hd/global/ui/spells/paladin/paskillicon{suffix}")
    with open(sub_src, "rb") as f:
        sub_data = f.read()
    with open(pal_src, "rb") as f:
        pal_px = f.read()[40:]

    sub_hdr = bytearray(sub_data[:40])
    sub_px = sub_data[40:]
    base_frames = 40
    base_row_bytes = base_frames * frame_w * 4
    pal_row_bytes = 60 * frame_w * 4

    total_frames = 42  # frames 0..39 vanilla + 40 (Dismiss Aura normal) + 41 (Dismiss Aura pressed)
    total_w = total_frames * frame_w
    out_px = bytearray(total_w * frame_h * 4)
    out_row_bytes = total_w * 4

    cx = (frame_w - 1) / 2.0
    cy = frame_h / 2.0
    scale = frame_h / 130.0
    r_inner = 22.0 * scale
    r_ring_in = 33.0 * scale
    r_ring_out = 45.0 * scale
    x_reach = 36.0 * scale
    x_half_w = 5.5 * scale

    for y in range(frame_h):
        dst_row_off = y * out_row_bytes
        src_sub_off = y * base_row_bytes
        out_px[dst_row_off : dst_row_off + base_row_bytes] = sub_px[src_sub_off : src_sub_off + base_row_bytes]

        for idx_offset, pal_cel in ((0, 16), (1, 17)):  # Defiance normal (16) and pressed (17)
            frame_idx = 40 + idx_offset
            p_off_row = y * pal_row_bytes + pal_cel * frame_w * 4
            u_off_row = y * base_row_bytes + (0 + idx_offset) * frame_w * 4  # Kick frame 0/1 for dark stone background
            f_off_row = dst_row_off + frame_idx * frame_w * 4
            press_shift = 2.0 * scale if idx_offset == 1 else 0.0
            dy = y - (cy + press_shift)

            for x in range(frame_w - 1):
                dx = x - cx
                dist = math.hypot(dx, dy)
                px_p = pal_px[p_off_row + x * 4 : p_off_row + (x + 1) * 4]
                r, g, b, a = px_p[0], px_p[1], px_p[2], px_p[3]

                # 1. Replace the inner shield emblem inside the aura circle with the warm brownish plate color of the bounding box
                if dist < r_ring_in:
                    t = max(0.0, min(1.0, (dist - r_inner) / max(1.0, r_ring_in - r_inner)))
                    # Use subtle texture variation from the original pixel mapped onto the warm brownish plate palette (~RGB 72, 48, 32)
                    tex = ((r + g + b) / 765.0 - 0.5) * 18.0
                    pr = max(35, min(110, int(72 + tex)))
                    pg = max(24, min(80, int(48 + tex * 0.75)))
                    pb = max(16, min(58, int(33 + tex * 0.55)))
                    r = int(pr * (1.0 - t) + r * t * 0.90)
                    g = int(pg * (1.0 - t) + g * t * 0.90)
                    b = int(pb * (1.0 - t) + b * t * 0.90)
                elif dist <= r_ring_out + 6.0 * scale:
                    # Subtle silver-gold tone on the circular aura ring itself
                    lum = int(r * 0.35 + g * 0.45 + b * 0.20)
                    r = min(255, int(lum * 1.05 + 15))
                    g = min(255, int(lum * 0.98 + 10))
                    b = min(255, int(lum * 0.88 + 5))

                # 2. Composite a crisp diagonal "X" slash across the aura circle matching the warm gold/ivory of the aura ring
                if abs(dx) <= x_reach and abs(dy) <= x_reach and dist <= r_ring_out + 2.0 * scale:
                    d1 = abs(dx - dy) / 1.41421356
                    d2 = abs(dx + dy) / 1.41421356
                    d_x = min(d1, d2)
                    if d_x <= x_half_w + 1.5 * scale:
                        if d_x <= x_half_w - 1.2 * scale:
                            # Bevelled warm gold / ivory X core matching the Paladin aura ring
                            ridge = max(0.0, 1.0 - (d_x / max(0.5, x_half_w - 1.2 * scale)))
                            xr = min(255, int(175 + 70 * ridge))
                            xg = min(255, int(155 + 75 * ridge))
                            xb = min(255, int(115 + 75 * ridge))
                            r, g, b = xr, xg, xb
                        else:
                            # Dark outline around the X bars for contrast against the aura ring
                            r = int(r * 0.25)
                            g = int(g * 0.22)
                            b = int(b * 0.18)

                out_px[f_off_row + x * 4 : f_off_row + (x + 1) * 4] = bytes((r, g, b, a))

            # Clamp rightmost separator column (frame_w - 1) to match column (frame_w - 2)
            out_px[f_off_row + (frame_w - 1) * 4 : f_off_row + frame_w * 4] = out_px[
                f_off_row + (frame_w - 2) * 4 : f_off_row + (frame_w - 1) * 4
            ]

    struct.pack_into("<I", sub_hdr, 8, total_w)
    struct.pack_into("<I", sub_hdr, 12, frame_h)
    struct.pack_into("<I", sub_hdr, 20, total_frames)
    struct.pack_into("<I", sub_hdr, 32, len(out_px))

    dst_path = os.path.join(MOD_ROOT, f"data/hd/global/ui/spells/submenu/skillicon{suffix}")
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "wb") as f:
        f.write(sub_hdr + out_px)
    return dst_path


def _build_baskillicon_pair(suffix: str, frame_w: int, frame_h: int) -> str:
    """
    Build data/hd/global/ui/spells/barbarian/baskillicon{suffix} with:
      1. Passive Combat Masteries (stamped as recessed brown cutouts on the brushed-silver plate):
         - IconCel  2 (frames  2,  3): One-Handed Mastery (Id 127)
         - IconCel  4 (frames  4,  5): Two-Handed Mastery (Id 128)
         - IconCel  6 (frames  6,  7): Battle Fervor (Id 129)
         - IconCel 16 (frames 16, 17): Critical Strike (Id 134)
         - IconCel 20 (frames 20, 21): Venom Ward (Id 136)
         - IconCel 30 (frames 30, 31): Unflinching (Id 141)
      2. Active Warcries & Combat Skills (stamped in brushed silver on the dark-brown active plate):
         - IconCel 10 (frames 10, 11): Second Wind (Id 131) - Howling Barbarian + 1 '+' sign
         - IconCel 32 (frames 32, 33): Enduring Cry (Id 142) - Howling Barbarian + 3 '+' signs
         - IconCel 48 (frames 48, 49): Bloodlust (Id 150) - Howling Barbarian + shrunk Grim Ward skull & crossbones
         - IconCel 26 (frames 26, 27): Shield Slam (Id 139) - AI-generated minimalist Shield Slam silhouette
    """
    import os
    import subprocess
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    d2r_root = os.path.dirname(MOD_ROOT)
    src_path = os.path.join(VANILLA_ROOT, f"data/hd/global/ui/spells/barbarian/baskillicon{suffix}")
    with open(src_path, "rb") as f:
        raw = f.read()

    hdr = raw[:40]
    out_px = bytearray(raw[40:])
    total_frames = 60
    row_bytes = total_frames * frame_w * 4

    is_hd = frame_h >= 100
    scale_f = 1.0 if is_hd else 0.5
    # Inner brushed-silver plate bounds inside the 4-rivet bronze border
    plate_x0, plate_x1 = (19, 112) if is_hd else (10, 56)
    plate_y0, plate_y1 = (19, 111) if is_hd else (10, 55)
    plate_w = plate_x1 - plate_x0
    plate_h = plate_y1 - plate_y0
    press_shift = 2 if is_hd else 1

    # 1. Reconstruct clean blank normal & pressed silver-plate button templates across vanilla
    #    passive frames (2, 4, 6, 16, 18, 20, 30, 38, 44).
    donor_cels = (2, 4, 6, 16, 18, 20, 30, 38, 44)
    blank_templates = [bytearray(frame_w * frame_h * 4), bytearray(frame_w * frame_h * 4)]
    for pressed in (0, 1):
        tmpl = blank_templates[pressed]
        g_min = 112 if pressed else 136
        g_max = 172 if pressed else 198
        for y in range(frame_h):
            in_plate_y = plate_y0 <= y < plate_y1
            for x in range(frame_w):
                in_plate = in_plate_y and (plate_x0 <= x < plate_x1)
                samples = []
                clean_silver = []
                for dc in donor_cels:
                    soff = y * row_bytes + ((dc + pressed) * frame_w + x) * 4
                    r, g, b, a = raw[40 + soff : 40 + soff + 4]
                    samples.append((r + g + b, r, g, b, a))
                    if in_plate and (r - b) <= 0 and g_min <= g <= g_max:
                        clean_silver.append((r + g + b, r, g, b, a))
                if clean_silver:
                    clean_silver.sort(key=lambda t: t[0])
                    _, r, g, b, a = clean_silver[len(clean_silver) // 2]
                elif in_plate:
                    found = False
                    for mx, my in (
                        (plate_x0 + plate_x1 - 1 - x, y),
                        (x, plate_y0 + plate_y1 - 1 - y),
                        (plate_x0 + 6, plate_y0 + 6),
                    ):
                        msamples = []
                        for dc in donor_cels:
                            soff = my * row_bytes + ((dc + pressed) * frame_w + mx) * 4
                            r, g, b, a = raw[40 + soff : 40 + soff + 4]
                            if (r - b) <= 0 and g_min <= g <= g_max:
                                msamples.append((r + g + b, r, g, b, a))
                        if msamples:
                            msamples.sort(key=lambda t: t[0])
                            _, r, g, b, a = msamples[len(msamples) // 2]
                            found = True
                            break
                    if not found:
                        samples.sort(key=lambda t: t[0])
                        _, r, g, b, a = samples[-3]
                else:
                    samples.sort(key=lambda t: t[0])
                    _, r, g, b, a = samples[-3]
                doff = (y * frame_w + x) * 4
                tmpl[doff : doff + 4] = bytes((r, g, b, a))

    # 2. Stamp the 6 v2 AI-generated passive Combat Mastery icons
    icon_specs = (
        (2, "one_handed_mastery.jpg", 0.10),
        (4, "two_handed_mastery.jpg", 0.08),
        (6, "battle_fervor.jpg", 0.10),
        (16, "critical_strike.jpg", 0.12),
        (20, "venom_ward.jpg", 0.14),
        (30, "unflinching.jpg", 0.10),
    )

    for base_cel, filename, crop_margin in icon_specs:
        img_path = os.path.join(d2r_root, "assets", "skill_icons", filename)
        keep_frac = 1.0 - 2.0 * crop_margin
        art_px = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                img_path,
                "-vf",
                f"crop=iw*{keep_frac:.2f}:ih*{keep_frac:.2f}:iw*{crop_margin:.2f}:ih*{crop_margin:.2f},scale={plate_w}:{plate_h}:flags=lanczos",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ]
        )

        mask = [[0.0] * plate_w for _ in range(plate_h)]
        for py in range(plate_h):
            for px_i in range(plate_w):
                aoff = (py * plate_w + px_i) * 3
                lum = (art_px[aoff] + art_px[aoff + 1] + art_px[aoff + 2]) / (3.0 * 255.0)
                m = max(0.0, min(1.0, (0.72 - lum) / 0.37))
                edge_d = min(px_i, plate_w - 1 - px_i, py, plate_h - 1 - py)
                if edge_d < 2:
                    m = 0.0
                elif edge_d == 2:
                    m *= 0.5
                mask[py][px_i] = m

        for pressed in (0, 1):
            fidx = base_cel + pressed
            tmpl = blank_templates[pressed]
            shift = press_shift if pressed else 0
            bright = 0.84 if pressed else 1.0

            for y in range(frame_h):
                row_off = y * row_bytes + fidx * frame_w * 4
                t_off = y * frame_w * 4
                out_px[row_off : row_off + frame_w * 4] = tmpl[t_off : t_off + frame_w * 4]

            for py in range(plate_h):
                sy = py - shift
                if not (0 <= sy < plate_h):
                    continue
                y = plate_y0 + py
                row_off = y * row_bytes + fidx * frame_w * 4
                for px_i in range(plate_w):
                    sx = px_i - shift
                    if not (0 <= sx < plate_w):
                        continue
                    x = plate_x0 + px_i
                    m = mask[sy][sx]
                    m_tl = mask[max(0, sy - 1)][max(0, sx - 1)]
                    m_br = mask[min(plate_h - 1, sy + 1)][min(plate_w - 1, sx + 1)]

                    px_off = row_off + x * 4
                    sr, sg, sb, sa = out_px[px_off : px_off + 4]

                    if m <= 0.05:
                        if m_tl > 0.55:
                            hl = int(55 * (m_tl - 0.55) / 0.45 * bright)
                            out_px[px_off : px_off + 4] = bytes(
                                (min(255, sr + hl), min(255, sg + hl), min(255, sb + hl), sa)
                            )
                        continue

                    grain = ((sr + sg + sb) / 3.0 - 182.0) * 0.35
                    cr = max(20, min(140, int((68 + grain) * bright)))
                    cg = max(14, min(105, int((48 + grain * 0.75) * bright)))
                    cb = max(10, min(85, int((36 + grain * 0.55) * bright)))

                    if m < 0.65:
                        rim_t = 1.0 - abs(m - 0.40) / 0.40
                        cr = int(cr * (1.0 - 0.72 * rim_t))
                        cg = int(cg * (1.0 - 0.75 * rim_t))
                        cb = int(cb * (1.0 - 0.78 * rim_t))
                    elif m_tl < 0.35:
                        cr = min(255, int(cr + 52 * bright))
                        cg = min(255, int(cg + 34 * bright))
                        cb = min(255, int(cb + 22 * bright))
                    elif m_br < 0.35:
                        cr = int(cr * 0.45)
                        cg = int(cg * 0.42)
                        cb = int(cb * 0.38)

                    r = int(sr * (1.0 - m) + cr * m)
                    g = int(sg * (1.0 - m) + cg * m)
                    b = int(sb * (1.0 - m) + cb * m)
                    out_px[px_off : px_off + 4] = bytes((r, g, b, sa))

    # 3. Reconstruct a spotless dark-brown active skill button template (normal & pressed)
    active_donors = (0, 8, 10, 12, 14, 22, 24, 26, 28, 32, 34, 36, 40, 42, 46, 48, 50, 52, 56, 58)
    brown_templates = [bytearray(frame_w * frame_h * 4), bytearray(frame_w * frame_h * 4)]
    for pressed in (0, 1):
        bt = brown_templates[pressed]
        for y in range(frame_h):
            in_plate_y = plate_y0 <= y < plate_y1
            for x in range(frame_w):
                in_plate = in_plate_y and (plate_x0 <= x < plate_x1)
                samples = []
                brown = []
                for dc in active_donors:
                    off = y * row_bytes + ((dc + pressed) * frame_w + x) * 4
                    r, g, b, a = raw[40 + off : 40 + off + 4]
                    samples.append((r + g + b, r, g, b, a))
                    if (r - b) >= 14 and 20 <= g <= 68:
                        brown.append((r + g + b, r, g, b, a))
                if brown:
                    brown.sort(key=lambda t: t[0])
                    _, r, g, b, a = brown[len(brown) // 2]
                elif in_plate:
                    found = False
                    for mx, my in (
                        (frame_w - 1 - x, y),
                        (x, frame_h - 1 - y),
                        (plate_x0 + 5, plate_y0 + 5),
                    ):
                        mb = []
                        for dc in active_donors:
                            off = my * row_bytes + ((dc + pressed) * frame_w + mx) * 4
                            r, g, b, a = raw[40 + off : 40 + off + 4]
                            if (r - b) >= 14 and 20 <= g <= 68:
                                mb.append((r + g + b, r, g, b, a))
                        if mb:
                            mb.sort(key=lambda t: t[0])
                            _, r, g, b, a = mb[len(mb) // 2]
                            found = True
                            break
                    if not found:
                        samples.sort(key=lambda t: t[0])
                        _, r, g, b, a = samples[len(samples) // 4]
                else:
                    samples.sort(key=lambda t: t[0])
                    _, r, g, b, a = samples[len(samples) // 2]
                bt[(y * frame_w + x) * 4 : (y * frame_w + x) * 4 + 4] = bytes((r, g, b, a))

    # Build clean Howling Barbarian base frame (from Cel 8 Howl, with top-right exclamation marks cleared)
    howl_base = [bytearray(frame_w * frame_h * 4), bytearray(frame_w * frame_h * 4)]
    clear_y0 = int(round(18 * scale_f))
    clear_y1 = int(round(56 * scale_f))
    clear_x0 = int(round(50 * scale_f))
    clear_x1 = int(round(112 * scale_f))
    for pressed in (0, 1):
        hb = howl_base[pressed]
        bt = brown_templates[pressed]
        for y in range(frame_h):
            off = y * row_bytes + ((8 + pressed) * frame_w) * 4
            hb[y * frame_w * 4 : (y + 1) * frame_w * 4] = raw[40 + off : 40 + off + frame_w * 4]
            if clear_y0 <= y <= clear_y1:
                for x in range(clear_x0, clear_x1):
                    p_off = (y * frame_w + x) * 4
                    hb[p_off : p_off + 4] = bt[p_off : p_off + 4]

    def _stamp_silver_fg(base_buf: bytearray, fg_mask, pressed: int) -> bytearray:
        out = bytearray(base_buf)
        st = blank_templates[pressed]
        bright = 0.84 if pressed else 1.0
        for y in range(plate_y0 - 1, plate_y1 + 1):
            for x in range(plate_x0 - 1, plate_x1 + 1):
                m = fg_mask[y][x]
                m_tl = fg_mask[y - 1][x - 1]
                m_br = fg_mask[y + 1][x + 1]
                m_max = max(m, fg_mask[y - 1][x], fg_mask[y + 1][x], fg_mask[y][x - 1], fg_mask[y][x + 1])
                if m_max <= 0.05:
                    continue
                p_off = (y * frame_w + x) * 4
                br_r, br_g, br_b, br_a = out[p_off : p_off + 4]
                if m <= 0.12:
                    t = min(1.0, (m_max - 0.05) / 0.5)
                    out[p_off : p_off + 4] = bytes(
                        (
                            int(br_r * (1.0 - 0.88 * t)),
                            int(br_g * (1.0 - 0.88 * t)),
                            int(br_b * (1.0 - 0.88 * t)),
                            br_a,
                        )
                    )
                    continue
                sr, sg, sb, _ = st[p_off : p_off + 4]
                if m_tl < 0.35:
                    sr = min(255, sr + int(48 * bright))
                    sg = min(255, sg + int(48 * bright))
                    sb = min(255, sb + int(48 * bright))
                elif m_br < 0.35:
                    sr = max(0, sr - int(42 * bright))
                    sg = max(0, sg - int(42 * bright))
                    sb = max(0, sb - int(42 * bright))
                alpha_t = min(1.0, (m - 0.12) / 0.45)
                r = int(br_r * (1.0 - alpha_t) + sr * alpha_t)
                g = int(br_g * (1.0 - alpha_t) + sg * alpha_t)
                b = int(br_b * (1.0 - alpha_t) + sb * alpha_t)
                out[p_off : p_off + 4] = bytes((r, g, b, br_a))
        return out

    def _write_frame_buf(fidx: int, buf: bytearray) -> None:
        for y in range(frame_h):
            row_off = y * row_bytes + fidx * frame_w * 4
            out_px[row_off : row_off + frame_w * 4] = buf[y * frame_w * 4 : (y + 1) * frame_w * 4]

    def _add_plus(mask, cx_hd: float, cy_hd: float, arm_l_hd: float, arm_w_hd: float, shift_px: int) -> None:
        cx = cx_hd * scale_f + shift_px
        cy = cy_hd * scale_f + shift_px
        arm_l = arm_l_hd * scale_f
        arm_w = arm_w_hd * scale_f
        for y in range(plate_y0, plate_y1):
            for x in range(plate_x0, plate_x1):
                dx, dy = abs(x - cx), abs(y - cy)
                d = min(max(dx - arm_l, dy - arm_w), max(dx - arm_w, dy - arm_l))
                val = max(0.0, min(1.0, 0.5 - d * (0.85 / scale_f)))
                if val > mask[y][x]:
                    mask[y][x] = val

    # 3a. Second Wind (IconCel 10, frames 10 & 11): Howling Barbarian + 1 '+' sign
    for pressed in (0, 1):
        shift = press_shift if pressed else 0
        m_sw = [[0.0] * frame_w for _ in range(frame_h)]
        _add_plus(m_sw, cx_hd=80.0, cy_hd=38.0, arm_l_hd=11.0, arm_w_hd=3.6, shift_px=shift)
        _write_frame_buf(10 + pressed, _stamp_silver_fg(howl_base[pressed], m_sw, pressed))

    # 3b. Enduring Cry (IconCel 32, frames 32 & 33): Howling Barbarian + 3 '+' signs
    for pressed in (0, 1):
        shift = press_shift if pressed else 0
        m_ec = [[0.0] * frame_w for _ in range(frame_h)]
        _add_plus(m_ec, cx_hd=71.0, cy_hd=29.0, arm_l_hd=7.5, arm_w_hd=2.6, shift_px=shift)
        _add_plus(m_ec, cx_hd=92.0, cy_hd=33.0, arm_l_hd=7.5, arm_w_hd=2.6, shift_px=shift)
        _add_plus(m_ec, cx_hd=78.0, cy_hd=47.0, arm_l_hd=7.5, arm_w_hd=2.6, shift_px=shift)
        _write_frame_buf(32 + pressed, _stamp_silver_fg(howl_base[pressed], m_ec, pressed))

    # 3c. Bloodlust (IconCel 48, frames 48 & 49): Howling Barbarian + shrunk Grim Ward skull & crossbones
    gw_x0, gw_x1 = int(round(30 * scale_f)), int(round(102 * scale_f))
    gw_y0, gw_y1 = int(round(20 * scale_f)), int(round(108 * scale_f))
    gw_w, gw_h = gw_x1 - gw_x0, gw_y1 - gw_y0
    dst_w, dst_h = max(1, int(round(35 * scale_f))), max(1, int(round(42 * scale_f)))
    for pressed in (0, 1):
        shift = press_shift if pressed else 0
        f_bl = bytearray(howl_base[pressed])
        dst_x0 = int(round(64 * scale_f)) + shift
        dst_y0 = int(round(18 * scale_f)) + shift
        src_cel = 48 + pressed
        for dy in range(dst_h):
            for dx in range(dst_w):
                sx = gw_x0 + shift + (dx + 0.5) * gw_w / dst_w
                sy = gw_y0 + shift + (dy + 0.5) * gw_h / dst_h
                ix, iy = int(sx), int(sy)
                fx, fy = sx - ix, sy - iy
                rgba = [0.0, 0.0, 0.0, 0.0]
                for oy in (0, 1):
                    for ox in (0, 1):
                        wt = ((1.0 - fx) if ox == 0 else fx) * ((1.0 - fy) if oy == 0 else fy)
                        soff = (min(frame_h - 1, iy + oy) * row_bytes) + (src_cel * frame_w + min(frame_w - 1, ix + ox)) * 4
                        for c in range(4):
                            rgba[c] += raw[40 + soff + c] * wt
                sr, sg, sb, _ = [int(round(v)) for v in rgba]
                if ((sr - sb) <= 12 and sg >= (70 if pressed else 85)) or (sg < 32 and (sr + sg + sb) < 95):
                    doff = ((dst_y0 + dy) * frame_w + (dst_x0 + dx)) * 4
                    f_bl[doff : doff + 4] = bytes((sr, sg, sb, 255))
        _write_frame_buf(48 + pressed, f_bl)

    # 3d. Shield Slam (IconCel 26, frames 26 & 27): Minimalist AI-generated Shield Slam silhouette
    ss_path = os.path.join(d2r_root, "assets", "skill_icons", "shield_slam.jpg")
    art_ss = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            ss_path,
            "-vf",
            f"crop=iw*0.80:ih*0.80:iw*0.10:ih*0.10,scale={plate_w}:{plate_h}:flags=lanczos",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ]
    )
    for pressed in (0, 1):
        shift = press_shift if pressed else 0
        m_ss = [[0.0] * frame_w for _ in range(frame_h)]
        for py in range(plate_h):
            sy = py - shift
            if not (0 <= sy < plate_h):
                continue
            for px_i in range(plate_w):
                sx = px_i - shift
                if not (0 <= sx < plate_w):
                    continue
                if min(px_i, plate_w - 1 - px_i, py, plate_h - 1 - py) < 2:
                    continue
                aoff = (sy * plate_w + sx) * 3
                lum = (art_ss[aoff] + art_ss[aoff + 1] + art_ss[aoff + 2]) / (3.0 * 255.0)
                m_ss[plate_y0 + py][plate_x0 + px_i] = max(0.0, min(1.0, (lum - 0.35) / 0.35))
        _write_frame_buf(26 + pressed, _stamp_silver_fg(brown_templates[pressed], m_ss, pressed))

    # 3e. Battle Command (IconCel 58, frames 58 & 59): Left-facing Howling Barbarian + Heart sub-icon
    import math
    for pressed in (0, 1):
        shift = press_shift if pressed else 0
        bcmd_base = bytearray(frame_w * frame_h * 4)
        bt = brown_templates[pressed]
        max_x_clear = int(round((67 + (2 if pressed else 0)) * scale_f))
        max_y_clear = int(round((61 + (2 if pressed else 0)) * scale_f))
        max_xy_clear = int(round((125 + (3 if pressed else 0)) * scale_f))
        for y in range(frame_h):
            off = y * row_bytes + ((58 + pressed) * frame_w) * 4
            bcmd_base[y * frame_w * 4 : (y + 1) * frame_w * 4] = raw[40 + off : 40 + off + frame_w * 4]
            if (plate_y0 - 1) <= y <= max_y_clear:
                for x in range(plate_x0 - 1, min(frame_w, max_x_clear + 1)):
                    if (x + y) <= max_xy_clear:
                        p_off = (y * frame_w + x) * 4
                        bcmd_base[p_off : p_off + 4] = bt[p_off : p_off + 4]

        m_bc = [[0.0] * frame_w for _ in range(frame_h)]
        cx = 50.0 * scale_f + shift
        cy = 38.0 * scale_f + shift
        hr = 7.4 * scale_f
        inv_sqrt2 = 0.7071067811865475

        for y in range(plate_y0, plate_y1):
            for x in range(plate_x0, plate_x1):
                dx = abs(x - cx)
                dy = y - cy
                u = (dx - dy) * inv_sqrt2
                v = (dx + dy) * inv_sqrt2
                if u >= hr or v <= 0.0:
                    d = math.hypot(u - hr, v) - hr
                elif u >= 0.0:
                    d = v - hr
                else:
                    d = math.hypot(u, max(0.0, v - hr)) if v > hr else (v - hr)
                val = max(0.0, min(1.0, 0.5 - d * (0.85 / scale_f)))
                if val > m_bc[y][x]:
                    m_bc[y][x] = val
        _write_frame_buf(58 + pressed, _stamp_silver_fg(bcmd_base, m_bc, pressed))

    dst_path = os.path.join(MOD_ROOT, f"data/hd/global/ui/spells/barbarian/baskillicon{suffix}")
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "wb") as f:
        f.write(hdr + out_px)
    return dst_path


def _build_baskilltree_pair() -> str:
    """
    Build data/hd/global/ui/spells/skill_trees/baskilltree.sprite and .lowend.sprite
    with the reorganized Frame 1 (Barbarian Combat Masteries):
      - Row 1 (y=125): Col 1 (One-Handed Mastery), Col 2 (Two-Handed Mastery), Col 3 (Throwing Mastery)
      - Row 2 (y=304): Col 2 only (Critical Strike, standalone)
      - Left Chain (Col 1, x=109): Row 3 (Unflinching) -> Row 4 (Increased Speed) -> Row 5 (Battle Fervor)
      - Right Chain (Col 3, x=631): Row 4 (Iron Skin) -> Row 5 (Venom Ward) -> Row 6 (Natural Resistance)
    """
    import os
    import subprocess
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    src_hd = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/skill_trees/baskilltree.sprite")
    src_low = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/skill_trees/baskilltree.lowend.sprite")
    with open(src_hd, "rb") as f:
        raw_hd = bytearray(f.read())
    with open(src_low, "rb") as f:
        raw_low = bytearray(f.read())

    hdr_hd = raw_hd[:40]
    px_hd = bytearray(raw_hd[40:])
    W, H, fw = 2691, 1169, 897

    def copy_rect(src_f: int, src_x: int, src_y: int, dst_f: int, dst_x: int, dst_y: int, w: int, h: int) -> None:
        for dy in range(h):
            sy = src_y + dy
            ty = dst_y + dy
            if not (0 <= sy < H and 0 <= ty < H):
                continue
            s_off = (sy * W + src_f * fw + src_x) * 4
            d_off = (ty * W + dst_f * fw + dst_x) * 4
            px_hd[d_off : d_off + w * 4] = raw_hd[40 + s_off : 40 + s_off + w * 4]

    def copy_rect_hflip(
        src_f: int,
        src_x: int,
        src_y: int,
        dst_f: int,
        dst_x: int,
        dst_y: int,
        w: int,
        h: int,
    ) -> None:
        for dy in range(h):
            sy = src_y + dy
            ty = dst_y + dy
            if not (0 <= sy < H and 0 <= ty < H):
                continue
            s_off = (sy * W + src_f * fw + src_x) * 4
            d_off = (ty * W + dst_f * fw + dst_x) * 4
            for dx in range(w):
                sx_rev = w - 1 - dx
                if raw_hd[40 + s_off + sx_rev * 4 + 3] > 0:
                    px_hd[d_off + dx * 4 : d_off + (dx + 1) * 4] = raw_hd[
                        40 + s_off + sx_rev * 4 : 40 + s_off + (sx_rev + 1) * 4
                    ]

    def clear_rect(dst_f: int, dst_x: int, dst_y: int, w: int, h: int) -> None:
        zero = b"\x00" * (w * 4)
        for dy in range(h):
            ty = dst_y + dy
            if 0 <= ty < H:
                d_off = (ty * W + dst_f * fw + dst_x) * 4
                px_hd[d_off : d_off + w * 4] = zero

    # Clear Frame 1 below the top tab header (y = 120..1168)
    clear_rect(1, 0, 120, fw, H - 120)

    # 1. Row 1 (y=125): Col 1 (x=109), Col 2 (x=371), Col 3 (x=631)
    for cx in (109, 371, 631):
        copy_rect(1, 371, 304, 1, cx, 125, 217, 157)

    # 2. Row 2 (y=304): Col 2 (x=371, Critical Strike, standalone)
    copy_rect(1, 371, 304, 1, 371, 304, 217, 157)

    # 3. Left Chain on Col 1 (x=109):
    #    Row 2 (Unflinching, y=304) -> 1-row arrow -> Row 3 (Increased Speed, y=480) -> 2-row arrow -> Row 5 (Battle Fervor, y=840)
    copy_rect(1, 371, 304, 1, 109, 304, 217, 157)
    copy_rect(2, 371, 635, 1, 109, 456, 155, 25)
    # Copy vanilla Frame 1 Col 1 Row 3 -> 2-row arrow -> Row 5 block (y=480..996)
    copy_rect(1, 109, 480, 1, 109, 480, 217, 517)

    # 4. Right Chain on Col 3 (x=631):
    #    Row 3 (Iron Skin, y=480) -> 1-row arrow -> Row 4 (Venom Ward, y=661) -> 2-row arrow -> Row 6 (Natural Resistance, y=1016)
    copy_rect(1, 371, 304, 1, 631, 480, 217, 157)
    copy_rect(2, 371, 635, 1, 631, 635, 155, 26)
    # Copy vanilla Frame 1 Col 3 Row 4 -> 2-row arrow -> Row 6 block (y=661..1168)
    copy_rect(1, 631, 661, 1, 631, 661, 217, 508)

    # -------------------------------------------------------------------------
    # Reorganize Frame 2 (Barbarian Combat Skills, SkillPage=1):
    #   - Col 1 (x=109, Tactical Defensive): Row 1 (Bash) -> Row 3 (Concentrate) -> Row 5 (Shield Slam)
    #   - Col 2 (x=371, Stamina Spenders):   Row 2 (Leap) -> Row 4 (Leap Attack) -> Row 6 (Whirlwind)
    #   - Col 3 (x=631, Exhaustion/Berserk): Row 1 (Double Swing) -> Row 3 (Double Throw) -> Row 5 (Berserk) -> Row 6 (Frenzy)
    #   - Diagonal Arrow: Col 3 Row 5 (Berserk) -> Col 2 Row 6 (Whirlwind)
    # -------------------------------------------------------------------------
    clear_rect(2, 0, 120, fw, H - 120)

    # 1. Col 1 (x=109): Row 1 (y=125) -> 2-row arrow -> Row 3 (y=480) -> 2-row arrow -> Row 5 (y=840)
    #    (Copied from vanilla Frame 0 Col 3, which has the exact Row 1 -> Row 3 -> Row 5 chain!)
    copy_rect(0, 631, 125, 2, 109, 125, 217, 875)

    # 2. Col 2 (x=371): Row 2 (y=304) -> 2-row arrow -> Row 4 (y=661) -> 2-row arrow -> Row 6 (y=1016)
    #    (Copied from vanilla Frame 2 Col 1, which has the exact Row 2 -> Row 4 -> Row 6 chain!)
    copy_rect(2, 109, 304, 2, 371, 304, 217, 865)

    # 3. Col 3 (x=631): Row 1 -> 2-row arrow -> Row 3 -> 2-row arrow -> Row 5 -> 1-row arrow -> Row 6
    copy_rect(0, 631, 125, 2, 631, 125, 217, 715)
    copy_rect(0, 371, 840, 2, 631, 840, 217, 329)

    # 4. Diagonal Arrow from Col 3 Row 5 (Berserk) down-left to Col 2 Row 6 (Whirlwind)
    #    (Copied from vanilla Frame 0's Col 2 Row 5 -> Col 1 Row 6 diagonal arrow at x=262..371, y=890..1016)
    copy_rect(0, 262, 890, 2, 522, 890, 109, 126)

    # -------------------------------------------------------------------------
    # Reorganize Frame 0 (Barbarian Warcries, SkillPage=3):
    #   - Col 1 (x=109): Row 1 (Bulwark) -> Row 4 (Battle Command) -> Row 5 (Battle Orders)
    #   - Col 2 (x=371): Row 2 (Taunt) -> Row 3 (Howl) -> Row 4 (Battle Cry) -> Row 6 (War Cry)
    #   - Col 3 (x=631): Row 1 (Enduring Cry) -> Row 3 (Second Wind) -> Row 5 (Bloodlust)
    #   - Diagonal Arrows into War Cry (Col 2 Row 6):
    #       * Down-right from Battle Orders (Col 1 Row 5)
    #       * Down-left from Bloodlust (Col 3 Row 5)
    # -------------------------------------------------------------------------
    clear_rect(0, 0, 120, fw, H - 120)

    # 1. Col 1 (x=109): Row 1 (y=125) -> 3-row arrow -> Row 4 (y=661) -> 1-row arrow -> Row 5 (y=840)
    #    (Vanilla Frame 0 Col 2 at y=304..839 is Row 2 + 3-row arrow; shifting by -179px aligns Row 1 -> Row 4!)
    copy_rect(0, 371, 304, 0, 109, 125, 217, 536)
    copy_rect(1, 371, 304, 0, 109, 661, 217, 157)
    copy_rect(2, 371, 635, 0, 109, 816, 155, 26)
    copy_rect(1, 109, 840, 0, 109, 840, 217, 157)

    # 2. Col 2 (x=371): Row 2 (y=304) -> 1-row arrow -> Row 3 (y=480) -> 1-row arrow -> Row 4 (y=661) -> 2-row arrow -> Row 6 (y=1016)
    copy_rect(1, 371, 304, 0, 371, 304, 217, 157)
    copy_rect(2, 371, 635, 0, 371, 456, 155, 25)
    copy_rect(1, 371, 304, 0, 371, 480, 217, 157)
    copy_rect(2, 371, 635, 0, 371, 635, 155, 26)
    copy_rect(1, 631, 661, 0, 371, 661, 217, 508)

    # 3. Col 3 (x=631): Row 1 (y=125) -> 2-row arrow -> Row 3 (y=480) -> 2-row arrow -> Row 5 (y=840)
    copy_rect(0, 631, 125, 0, 631, 125, 217, 875)

    # 4. Diagonal Arrows into War Cry (Col 2 Row 6):
    #    - Down-right from Battle Orders (Col 1 Row 5): copied from vanilla Frame 0's Col 1 Row 1 -> Col 2 Row 2 arrow (+715px y-offset)
    copy_rect(0, 262, 170, 0, 262, 885, 118, 132)
    #    - Down-left from Bloodlust (Col 3 Row 5): copied from vanilla Frame 0's Col 2 Row 5 -> Col 1 Row 6 arrow (+260px x-offset)
    copy_rect(0, 262, 890, 0, 522, 890, 109, 126)

    dst_hd = os.path.join(MOD_ROOT, "data/hd/global/ui/spells/skill_trees/baskilltree.sprite")
    os.makedirs(os.path.dirname(dst_hd), exist_ok=True)
    with open(dst_hd, "wb") as f:
        f.write(hdr_hd + px_hd)

    # Downscale all 3 frames (2691x1169 -> 1347x584) into baskilltree.lowend.sprite
    hdr_low = raw_low[:40]
    W_low, H_low = 1347, 584
    px_low = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s",
            f"{W}x{H}",
            "-i",
            "-",
            "-vf",
            f"scale={W_low}:{H_low}:flags=lanczos",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-",
        ],
        input=bytes(px_hd),
    )

    dst_low = os.path.join(MOD_ROOT, "data/hd/global/ui/spells/skill_trees/baskilltree.lowend.sprite")
    with open(dst_low, "wb") as f:
        f.write(hdr_low + px_low)

    return f"{dst_hd}, {dst_low}"


def _build_asskilltree_pair() -> str:
    """
    Build data/hd/global/ui/spells/skill_trees/asskilltree.sprite and .lowend.sprite
    with reorganized Frame 0 (Martial Arts, SkillPage=3) and Frame 2 (Traps & Blades, SkillPage=1),
    leaving Frame 1 (Shadow Disciplines, SkillPage=2) untouched:
      - Frame 0 (Martial Arts, SkillPage=3):
          * Col 1 (x=109): Row 2 (Fists of Fire) -> Row 3 (Blades of Ice) -> Row 4 (Claws of Thunder) -> Row 6 (Omnislash)
          * Col 2 (x=371): Row 1 (Tiger Strike) -> Row 3 (Dragon Claw) -> Row 5 (Cobra Strike) -> diagonal to Row 6 Col 1 (Omnislash)
          * Col 3 (x=631): Row 1 (Dragon Talon) -> Row 4 (Dragon Tail) -> Row 5 (Dragon Flight)
      - Frame 2 (Traps & Blades, SkillPage=1):
          * Col 1 (x=109): Row 3 (Fire Sentry) -> Row 4 (Ice Sentry) -> Row 5 (Lightning Sentry)
          * Col 2 (x=371): Row 1 (Caltrops) -> Row 2 (Shrapnel Sentry) -> Row 6 (Soul Siphon Sentry)
          * Col 3 (x=631): Row 1 (Blade Sentinel) -> Row 3 (Blade Fury) -> Row 5 (Blade Shield) -> Row 6 (Shuriken)
                           plus diagonal from Row 5 Col 3 (Blade Shield) to Row 6 Col 2 (Soul Siphon Sentry)
    """
    import os
    import subprocess
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    src_hd = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/skill_trees/asskilltree.sprite")
    src_low = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/skill_trees/asskilltree.lowend.sprite")
    with open(src_hd, "rb") as f:
        raw_hd = bytearray(f.read())
    with open(src_low, "rb") as f:
        raw_low = bytearray(f.read())

    hdr_hd = raw_hd[:40]
    px_hd = bytearray(raw_hd[40:])
    W, H, fw = 2691, 1169, 897

    ROW_Y = {1: 125, 2: 305, 3: 481, 4: 662, 5: 841, 6: 1017}
    COL_X = {1: 109, 2: 371, 3: 631}

    def copy_rect(
        src_f: int,
        src_x: int,
        src_y: int,
        dst_f: int,
        dst_x: int,
        dst_y: int,
        w: int,
        h: int,
        transparent_skip: bool = False,
    ) -> None:
        for dy in range(h):
            sy = src_y + dy
            ty = dst_y + dy
            if not (0 <= sy < H and 0 <= ty < H):
                continue
            s_off = (sy * W + src_f * fw + src_x) * 4
            d_off = (ty * W + dst_f * fw + dst_x) * 4
            if not transparent_skip:
                px_hd[d_off : d_off + w * 4] = raw_hd[40 + s_off : 40 + s_off + w * 4]
            else:
                for dx in range(w):
                    if raw_hd[40 + s_off + dx * 4 + 3] > 0:
                        px_hd[d_off + dx * 4 : d_off + (dx + 1) * 4] = raw_hd[
                            40 + s_off + dx * 4 : 40 + s_off + (dx + 1) * 4
                        ]

    def copy_rect_hflip(
        src_f: int,
        src_x: int,
        src_y: int,
        dst_f: int,
        dst_x: int,
        dst_y: int,
        w: int,
        h: int,
    ) -> None:
        for dy in range(h):
            sy = src_y + dy
            ty = dst_y + dy
            if not (0 <= sy < H and 0 <= ty < H):
                continue
            s_off = (sy * W + src_f * fw + src_x) * 4
            d_off = (ty * W + dst_f * fw + dst_x) * 4
            for dx in range(w):
                sx_rev = w - 1 - dx
                if raw_hd[40 + s_off + sx_rev * 4 + 3] > 0:
                    px_hd[d_off + dx * 4 : d_off + (dx + 1) * 4] = raw_hd[
                        40 + s_off + sx_rev * 4 : 40 + s_off + (sx_rev + 1) * 4
                    ]

    def clear_rect(dst_f: int, dst_x: int, dst_y: int, w: int, h: int) -> None:
        zero = b"\x00" * (w * 4)
        for dy in range(h):
            ty = dst_y + dy
            if 0 <= ty < H:
                d_off = (ty * W + dst_f * fw + dst_x) * 4
                px_hd[d_off : d_off + w * 4] = zero

    def draw_box(dst_f: int, col: int, row: int) -> None:
        x = COL_X[col]
        y = ROW_Y[row]
        top_h = min(135, H - y)
        copy_rect(0, 371, 125, dst_f, x, y, 217, top_h, transparent_skip=True)
        rem_h = min(21, max(0, H - (y + 135)))
        if rem_h > 0:
            copy_rect(0, 631, 976, dst_f, x, y + 135, 217, rem_h, transparent_skip=True)

    def draw_v_arrow(dst_f: int, col: int, r_start: int, r_end: int) -> None:
        x = COL_X[col] + 40
        y_start = ROW_Y[r_start] + 152
        y_end = ROW_Y[r_end] + 4
        gap = y_end - y_start
        if r_end == r_start + 1:
            copy_rect(0, 149, 845 - gap, dst_f, x, y_start, 75, gap, transparent_skip=True)
        else:
            copy_rect(0, 411, 633, dst_f, x, y_start, 75, 20, transparent_skip=True)
            body_h = (y_end - 25) - (y_start + 20)
            for dy in range(body_h):
                sy = 653 + int(dy * 342 / max(1, body_h - 1))
                copy_rect(0, 411, sy, dst_f, x, y_start + 20 + dy, 75, 1, transparent_skip=True)
            copy_rect(0, 411, 996, dst_f, x, y_end - 25, 75, 25, transparent_skip=True)

    # 1. Rebuild Frame 0 (Martial Arts, SkillPage=3)
    clear_rect(0, 0, 120, fw, H - 120)
    for col, row in [(2, 1), (3, 1), (1, 2), (1, 3), (2, 3), (1, 4), (3, 4), (2, 5), (3, 5), (1, 6)]:
        draw_box(0, col, row)

    draw_v_arrow(0, 1, 2, 3)
    draw_v_arrow(0, 1, 3, 4)
    draw_v_arrow(0, 2, 1, 3)
    draw_v_arrow(0, 2, 3, 5)
    draw_v_arrow(0, 1, 4, 6)
    # Cobra Strike (Col 2, Row 5) -> Omnislash (Col 1, Row 6): down-left diagonal (same art as Frame 2's Blade Shield -> Soul Siphon)
    copy_rect(1, 260, 180, 0, 260, 892, 109, 134, transparent_skip=True)
    draw_v_arrow(0, 3, 1, 4)
    draw_v_arrow(0, 3, 4, 5)

    # 2. Rebuild Frame 1 (Shadow Disciplines, SkillPage=2)
    clear_rect(1, 0, 120, fw, H - 120)
    for col, row in [(3, 1), (1, 2), (2, 2), (1, 3), (3, 3), (1, 4), (2, 5), (3, 5), (1, 6), (3, 6)]:
        draw_box(1, col, row)

    draw_v_arrow(1, 1, 2, 3)  # Cloak of Shadows (c1,r2) -> Shadow Bind (c1,r3)
    draw_v_arrow(1, 1, 3, 4)  # Shadow Bind (c1,r3) -> Mind Blast (c1,r4)
    draw_v_arrow(1, 1, 4, 6)  # Mind Blast (c1,r4) -> Shadow Master (c1,r6)
    draw_v_arrow(1, 2, 2, 5)  # Weapon Block (c2,r2) -> Fade (c2,r5)
    draw_v_arrow(1, 3, 1, 3)  # Lethality (c3,r1) -> Burst of Speed (c3,r3)
    draw_v_arrow(1, 3, 3, 5)  # Burst of Speed (c3,r3) -> Venom (c3,r5)
    draw_v_arrow(1, 3, 5, 6)  # Venom (c3,r5) -> Flow (c3,r6)
    # Lethality (Col 3, Row 1) -> Weapon Block (Col 2, Row 2): down-left diagonal
    copy_rect(1, 260, 180, 1, 522, 180, 109, 134, transparent_skip=True)
    # Fade (Col 2, Row 5) -> Shadow Master (Col 1, Row 6): down-left diagonal
    copy_rect(1, 260, 180, 1, 260, 892, 109, 134, transparent_skip=True)

    # 3. Rebuild Frame 2 (Traps & Blades, SkillPage=1)
    clear_rect(2, 0, 120, fw, H - 120)
    for col, row in [(2, 1), (3, 1), (2, 2), (1, 3), (3, 3), (1, 4), (1, 5), (3, 5), (2, 6), (3, 6)]:
        draw_box(2, col, row)

    draw_v_arrow(2, 1, 3, 4)
    draw_v_arrow(2, 1, 4, 5)
    draw_v_arrow(2, 2, 1, 2)
    draw_v_arrow(2, 2, 2, 6)
    draw_v_arrow(2, 3, 1, 3)
    draw_v_arrow(2, 3, 3, 5)
    draw_v_arrow(2, 3, 5, 6)
    copy_rect(1, 260, 180, 2, 522, 892, 109, 134, transparent_skip=True)
    # Shrapnel Sentry (Col 2, Row 2) -> Fire Sentry (Col 1, Row 3): down-left diagonal
    copy_rect(1, 260, 180, 2, 260, 356, 109, 134, transparent_skip=True)

    dst_hd = os.path.join(MOD_ROOT, "data/hd/global/ui/spells/skill_trees/asskilltree.sprite")
    os.makedirs(os.path.dirname(dst_hd), exist_ok=True)
    with open(dst_hd, "wb") as f:
        f.write(hdr_hd + px_hd)

    hdr_low = raw_low[:40]
    W_low, H_low = 1347, 584
    px_low = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s",
            f"{W}x{H}",
            "-i",
            "-",
            "-vf",
            f"scale={W_low}:{H_low}:flags=lanczos",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-",
        ],
        input=bytes(px_hd),
    )

    dst_low = os.path.join(MOD_ROOT, "data/hd/global/ui/spells/skill_trees/asskilltree.lowend.sprite")
    with open(dst_low, "wb") as f:
        f.write(hdr_low + px_low)

    return f"{dst_hd}, {dst_low}"


def _build_barbarian_state_machine() -> str:
    """Add 3D HD PLRMODE_SEQUENCE (modeId=18) states for Barbarian Shield Charge (skillIndex 139 & 107).

    In vanilla barbarian_state_machine.json, there is no modeId=18 entry for skillIndex 139 (Stun/Shield Charge)
    or 107 (Charge), which caused the 3D HD renderer to remain in PMODE_RUN / PMODE_NEUTRAL / Run_Turn_180
    during Shield Charge without raising the shield or swinging the weapon on impact.
    - stepIndex 0 (Charge_Run): binds 1hs_run / 1ht_run / hth_run (loopCount=0) in modeId=18 so the Barbarian
      immediately cancels any 180-turn pivot and sprints directly at the target.
    - stepIndex 1 (Charge_Attack): binds 1hs_block / 1ht_block / hth_block (loopCount=1) so the Barbarian
      raises and slams his shield into the monster on impact without swinging his weapon.
    """
    import json
    import os
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    src_path = os.path.join(
        VANILLA_ROOT, "data/hd/character/player/barbarian/barbarian_state_machine.json"
    )
    with open(src_path, "r", encoding="utf-8") as f:
        sm = json.load(f)

    charge_run_bindings = {
        "hth": ["hth_run"],
        "bow": ["bow_run"],
        "1hs": ["1hs_run"],
        "1ht": ["1ht_run"],
        "stf": ["stf_run"],
        "2hs": ["2hs_run"],
        "2ht": ["2ht_run"],
        "xbw": ["xbw_run"],
        "1js": ["1js_run"],
        "1jt": ["1jt_run"],
        "1ss": ["1ss_run"],
        "1st": ["1st_run"],
    }
    charge_attack_bindings = {
        "hth": ["hth_block"],
        "1hs": ["1hs_block"],
        "1ht": ["1ht_block"],
        "stf": ["stf_attack1"],
        "2hs": ["2hs_attack1"],
        "2ht": ["2ht_attack1"],
        "1js": ["1js_attack1"],
        "1jt": ["1jt_attack1"],
        "1ss": ["1ss_attack1"],
        "1st": ["1st_attack1"],
    }

    new_states = [
        (66, "AnimationState046", "Charge_Run", 139, 0, 0, charge_run_bindings),
        (67, "AnimationState047", "Charge_Attack", 139, 1, 1, charge_attack_bindings),
        (68, "AnimationState048", "Charge_Run_107", 107, 0, 0, charge_run_bindings),
        (69, "AnimationState049", "Charge_Attack_107", 107, 1, 1, charge_attack_bindings),
    ]
    new_state_ids = [s[0] for s in new_states]

    for state_id, name, internal_name, skill_idx, step_idx, loop_cnt, bindings in new_states:
        sm["states"].append(
            {
                "type": "AnimationState",
                "name": name,
                "_name": internal_name,
                "audioId": "",
                "loopCount": loop_cnt,
                "stateId": state_id,
                "enableVfxAttributes": False,
                "modeId": 18,
                "skillIndex": skill_idx,
                "stepIndex": step_idx,
                "animationBindings": bindings,
                "enterEvents": [],
                "exitEvents": [],
                "exitBlendType": 0,
            }
        )

    all_state_ids = [s["stateId"] for s in sm["states"]]

    # 1. Add fast (0.05s) transitions from every existing state into the new Shield Charge states
    for tg in sm["transitions"]:
        base_name = tg["name"]
        for target_id in new_state_ids:
            tg["settings"].append(
                {
                    "type": "AnimationTransitionItem",
                    "name": f"{base_name}_transition{target_id:03d}",
                    "crossfadeSeconds": 0.05,
                    "to": target_id,
                }
            )

    # 2. Add transition groups from each new Shield Charge state to all states
    fast_return_targets = {1, 2, 3, 7, 8, 9, 64, 65, 66, 67, 68, 69}
    for state_id, name, _, _, _, _, _ in new_states:
        group_name = f"{name}_transitiongroup"
        settings = []
        for idx, to_id in enumerate(all_state_ids):
            t_name = (
                f"{group_name}_transition"
                if idx == 0
                else f"{group_name}_transition{to_id:03d}"
            )
            settings.append(
                {
                    "type": "AnimationTransitionItem",
                    "name": t_name,
                    "crossfadeSeconds": 0.05 if to_id in fast_return_targets else 0.2,
                    "to": to_id,
                }
            )
        sm["transitions"].append(
            {
                "type": "AnimationTransitionGroup",
                "name": group_name,
                "from": state_id,
                "settings": settings,
            }
        )

    dst_path = os.path.join(
        MOD_ROOT, "data/hd/character/player/barbarian/barbarian_state_machine.json"
    )
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(sm, f, indent=2)
        f.write("\n")
    return dst_path


def _build_assassin_state_machine() -> str:
    """Update data/hd/character/player/assassin/assassin_state_machine.json so:
    1. Attack1 (modeId=7) and all 5 Charge-Up skills (plus Dragon Claw) bind 'ht2_sequence' for Dual Claws (ht2)
       while preserving standard 1H/2H melee attack bindings (hth, ht1, 1hs, 1ht, 2hs, 2ht, stf).
    2. Omnislash (skillIndex=280, Zeal/Fend multi-strike finisher) has both stepIndex=0 (FirstAttack, stateId=32)
       and stepIndex=1 (FollowUpAttack, stateId=67) states supporting all weapon types (1H, 2H, and Dual Claws
       alternating between right-hand ht2_attack1/5 and left-hand ht2_attack2/3 slashes).
    """
    import json
    import os
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    src_path = os.path.join(
        VANILLA_ROOT, "data/hd/character/player/assassin/assassin_state_machine.json"
    )
    with open(src_path, "r", encoding="utf-8") as f:
        sm = json.load(f)

    target_skills = {254, 259, 260, 265, 269, 274}
    fallback_bindings = {
        "hth": ["hth_attack1", "hth_attack2"],
        "ht1": ["ht1_attack1", "ht1_attack2"],
        "1hs": ["1hs_attack1", "1hs_attack2"],
        "1ht": ["1ht_attack1", "1ht_attack2"],
        "2hs": ["2hs_attack1", "2hs_attack2"],
        "2ht": ["2ht_attack1", "2ht_attack2"],
        "stf": ["stf_attack1", "stf_attack2"],
    }
    omnislash_first_bindings = {
        "hth": ["hth_attack1", "hth_attack2", "hth_attack3"],
        "ht1": ["ht1_attack1", "ht1_attack2", "ht1_attack3"],
        "ht2": ["ht2_sequence"],
        "1hs": ["1hs_attack1", "1hs_attack2"],
        "1ht": ["1ht_attack1", "1ht_attack2"],
        "2hs": ["2hs_attack1", "2hs_attack2"],
        "2ht": ["2ht_attack1", "2ht_attack2"],
        "stf": ["stf_attack1", "stf_attack2"],
        "bow": ["bow_attack1", "bow_attack2"],
        "xbw": ["xbw_attack1", "xbw_attack2"],
    }
    omnislash_followup_bindings = {
        "hth": ["hth_attack2", "hth_attack3", "hth_attack1"],
        "ht1": ["ht1_attack2", "ht1_attack3", "ht1_attack1"],
        "ht2": ["ht2_attack2", "ht2_attack1", "ht2_attack3", "ht2_attack5"],
        "1hs": ["1hs_attack2", "1hs_attack1"],
        "1ht": ["1ht_attack2", "1ht_attack1"],
        "2hs": ["2hs_attack2", "2hs_attack1"],
        "2ht": ["2ht_attack2", "2ht_attack1"],
        "stf": ["stf_attack2", "stf_attack1"],
        "bow": ["bow_attack2", "bow_attack1"],
        "xbw": ["xbw_attack2", "xbw_attack1"],
    }

    for st in sm["states"]:
        if st.get("modeId") == 13 and st.get("skillIndex") == -1:
            # Bind State_Skill1 (S1, used exclusively by Shuriken) to the Blade Fury throwing clip (<wclass>_bladefury)
            b = st.setdefault("animationBindings", {})
            bladefury_wclasses = {"hth", "bow", "1hs", "1ht", "stf", "2hs", "2ht", "xbw", "ht1", "ht2"}
            for wk in list(b.keys()):
                if wk in bladefury_wclasses:
                    b[wk] = [f"{wk}_bladefury"]
                else:
                    b[wk] = ["1hs_bladefury"]
        elif st.get("modeId") == 7 and st.get("skillIndex") == -1:
            b = st.setdefault("animationBindings", {})
            b["ht2"] = ["ht2_sequence"]
        elif st.get("modeId") == 18 and st.get("skillIndex") in target_skills:
            b = st.setdefault("animationBindings", {})
            b["ht2"] = ["ht2_sequence"]
            for wk, wv in fallback_bindings.items():
                if wk not in b:
                    b[wk] = wv
        elif st.get("modeId") == 18 and st.get("skillIndex") == 280 and st.get("stepIndex") == 0:
            # Whirlwind-engine Omnislash: looping spin (loopCount=0) using the Assassin's claw whirlwind clips;
            # other weapon classes loop their normal attack clips.
            st["loopCount"] = 0
            # The claw whirlwind clips are the only spin clips the Assassin skeleton has; every other weapon
            # class reuses the single-claw spin (weapon is simply held in the posed hand).
            st["animationBindings"] = {
                "hth": ["ht1_whirlwind"],
                "ht1": ["ht1_whirlwind"],
                "ht2": ["ht2_whirlwind"],
                "1hs": ["ht1_whirlwind"],
                "1ht": ["ht1_whirlwind"],
                "2hs": ["ht1_whirlwind"],
                "2ht": ["ht1_whirlwind"],
                "stf": ["ht1_whirlwind"],
            }

    followup_state_id = 67
    followup_state_name = "AnimationState048"
    sm["states"].append(
        {
            "type": "AnimationState",
            "name": followup_state_name,
            "_name": "Omnislash_FollowUpAttack",
            "audioId": "",
            "loopCount": 1,
            "stateId": followup_state_id,
            "enableVfxAttributes": False,
            "modeId": 18,
            "skillIndex": 280,
            "stepIndex": 1,
            "animationBindings": omnislash_followup_bindings,
            "enterEvents": [],
            "exitEvents": [],
            "exitBlendType": 0,
        }
    )

    all_state_ids = [s["stateId"] for s in sm["states"]]
    fast_omnislash_targets = {1, 32, followup_state_id}

    for tg in sm["transitions"]:
        base_name = tg["name"]
        from_id = tg.get("from")
        if from_id == 32:
            for s_item in tg["settings"]:
                if s_item.get("to") in fast_omnislash_targets:
                    s_item["crossfadeSeconds"] = 0.05
        tg["settings"].append(
            {
                "type": "AnimationTransitionItem",
                "name": f"{base_name}_transition{followup_state_id:03d}",
                "crossfadeSeconds": 0.05 if from_id == 32 else 0.2,
                "to": followup_state_id,
            }
        )

    group_name = f"{followup_state_name}_transitiongroup"
    followup_settings = []
    for idx, to_id in enumerate(all_state_ids):
        t_name = (
            f"{group_name}_transition"
            if idx == 0
            else f"{group_name}_transition{to_id:03d}"
        )
        followup_settings.append(
            {
                "type": "AnimationTransitionItem",
                "name": t_name,
                "crossfadeSeconds": 0.05 if to_id in fast_omnislash_targets else 0.2,
                "to": to_id,
            }
        )
    sm["transitions"].append(
        {
            "type": "AnimationTransitionGroup",
            "name": group_name,
            "from": followup_state_id,
            "settings": followup_settings,
        }
    )

    dst_path = os.path.join(
        MOD_ROOT, "data/hd/character/player/assassin/assassin_state_machine.json"
    )
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(sm, f, indent=2)
        f.write("\n")
    return dst_path


def _build_chargeboltsentry_hd() -> str:
    """Replace chargeboltsentry's and deathsentry's 3D lightning-rod turret assets in D2R HD with the
    non-lightning mechanical rotary turret (wakeofdestruction/torso.model + skeleton + animations)
    and preload their respective missile VFX.
    """
    import json
    import os
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    wod_def_path = os.path.join(VANILLA_ROOT, "data/hd/character/enemy/wakeofdestruction.json")
    wod_sm_path = os.path.join(
        VANILLA_ROOT, "data/hd/character/enemy/wakeofdestruction/wakeofdestruction_state_machine.json"
    )
    if not (os.path.exists(wod_def_path) and os.path.exists(wod_sm_path)):
        return ""

    out_files = []
    turret_specs = [
        (
            "chargeboltsentry",
            [("BoltSentry_Seq", 306), ("SentryLightning_Seq", 313)],
            [
                "data/hd/missiles/unholy_bolt.json",
                "data/hd/missiles/bone_spirit_explode.json",
                "data/hd/missiles/sentrylightningbolt.json",
                "data/hd/missiles/lightning_strike.json",
            ],
        ),
        (
            "deathsentry",
            [("DeathSentry_Seq", 312)],
            [
                "data/hd/missiles/expansion_arctic_blast_ice.json",
                "data/hd/missiles/expansion_arctic_blast_ice_2.json",
            ],
        ),
    ]
    for unit_name, seq_specs, preload_missiles in turret_specs:
        with open(wod_def_path, "r", encoding="utf-8") as f:
            u_def = json.load(f)
        u_def["name"] = unit_name
        sm_rel = f"data/hd/character/enemy/{unit_name}/{unit_name}_state_machine.json"
        u_def["dependencies"]["json"] = [{"path": sm_rel}] + [
            {"path": mp} for mp in preload_missiles
        ]
        for ent in u_def.get("entities", []):
            if ent.get("name") == "entity_root":
                for comp in ent.get("components", []):
                    if comp.get("type") == "UnitRootComponent":
                        comp["state_machine_filename"] = sm_rel
                    elif comp.get("type") == "DefinitionPreloadComponent":
                        comp["missiles"] = [
                            {
                                "type": "UnitDefinitionListEntry",
                                "name": f"Root_UnitDefinitionList_Entry{idx + 1}",
                                "filename": mp,
                            }
                            for idx, mp in enumerate(preload_missiles)
                        ]

        with open(wod_sm_path, "r", encoding="utf-8") as f:
            u_sm = json.load(f)
        u_sm["name"] = f"{unit_name}_statemachine"
        new_states = []
        for st in u_sm.get("states", []):
            if st.get("modeId") == 14 and st.get("skillIndex") == 281:
                for seq_name, skill_idx in seq_specs:
                    st_copy = dict(st)
                    st_copy["_name"] = seq_name
                    st_copy["skillIndex"] = skill_idx
                    new_states.append(st_copy)
            else:
                new_states.append(st)
        u_sm["states"] = new_states

        dst_def = os.path.join(MOD_ROOT, f"data/hd/character/enemy/{unit_name}.json")
        dst_sm = os.path.join(MOD_ROOT, sm_rel)
        os.makedirs(os.path.dirname(dst_def), exist_ok=True)
        os.makedirs(os.path.dirname(dst_sm), exist_ok=True)
        with open(dst_def, "w", encoding="utf-8") as f:
            json.dump(u_def, f, indent=2)
            f.write("\n")
        with open(dst_sm, "w", encoding="utf-8") as f:
            json.dump(u_sm, f, indent=2)
            f.write("\n")
        out_files.extend([dst_def, dst_sm])
    return ", ".join(out_files)


def _build_animdata() -> str:
    """Update animdata.d2 and eanimdata.d2 so:
    1. AIA1HT2 has fpc=16, spd=227, and two melee hit triggers (frames 5 and 11, matching the two
       claw slices of ht2_sequence) for Dual-Claw Normal Attack & Charge-Up skills.
    2. AIA2* (AIA2HT2, AIA2HT1, AIA21HS, AIA21HT, AIA22HS, AIA22HT, AIA2STF, AIA2HTH) has fpc=16,
       spd=256, and four rapid melee hit triggers (frames 4, 7, 10, 13) for Omnislash (anim/seqtrans='A2'),
       allowing srvdofunc=1 to execute 4 rapid weapon strikes and release all 3 pending Martial Arts
       charge tiers (Charge 3 -> Charge 2 -> Charge 1) in a single sequence.
    """
    import os
    import struct
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    out_paths = []
    for fname in ("animdata.d2", "eanimdata.d2"):
        src_path = os.path.join(VANILLA_ROOT, f"data/global/{fname}")
        if not os.path.exists(src_path):
            continue
        with open(src_path, "rb") as f:
            data = f.read()

        buckets = []
        pos = 0
        for _ in range(256):
            cnt = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            recs = []
            for _ in range(cnt):
                recs.append(data[pos : pos + 160])
                pos += 160
            buckets.append(recs)

        # 1. Modify AIA1HT2 in-place to fire two melee hit events (frames 5 and 11) for Dual-Claw Normal Attack & Charge-Up skills.
        for target_name in ("AIA1HT2",):
            b_idx = sum(ord(c) for c in target_name) & 0xFF
            name_bytes = target_name.encode("ascii").ljust(8, b"\x00")
            new_recs = []
            for r in buckets[b_idx]:
                if r[:8] == name_bytes:
                    ev_bytes = bytearray(144)
                    ev_bytes[5] = 1
                    ev_bytes[11] = 1
                    r = struct.pack("<8sII", name_bytes, 16, 227) + bytes(ev_bytes)
                new_recs.append(r)
            buckets[b_idx] = new_recs

        # 2. Modify AIS1* (State_Skill1 / S1, used exclusively by Shuriken) to 8 frames at speed=292 (~6.7-7 frames per throw,
        #    ~90% as fast as Blade Fury's 6-frame throw rate) with event=1 at frame 3.
        for wcls in ("1HS", "1HT", "2HS", "2HT", "BOW", "HT1", "HT2", "HTH", "STF", "XBW"):
            target_name = f"AIS1{wcls}"
            b_idx = sum(ord(c) for c in target_name) & 0xFF
            name_bytes = target_name.encode("ascii").ljust(8, b"\x00")
            new_recs = []
            for r in buckets[b_idx]:
                if r[:8] == name_bytes:
                    ev_bytes = bytearray(144)
                    ev_bytes[3] = 1
                    r = struct.pack("<8sII", name_bytes, 8, 292) + bytes(ev_bytes)
                new_recs.append(r)
            buckets[b_idx] = new_recs

        out = bytearray()
        for recs in buckets:
            out += struct.pack("<I", len(recs))
            for r in recs:
                out += r

        dst_path = os.path.join(MOD_ROOT, f"data/global/{fname}")
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        with open(dst_path, "wb") as f:
            f.write(out)
        out_paths.append(dst_path)
    return ", ".join(out_paths)


def build_pettype(cfg: dict) -> str:
    headers, rows = read_excel_tsv("pettype.txt")
    base_trap = None
    existing = set()
    for r in rows:
        pt = r.get("pet type", "")
        existing.add(pt)
        if pt == "assassintrap":
            r["partysend"] = "1"
            base_trap = dict(r)
    if base_trap:
        for new_pt in ("phystrap", "firetrap", "ltngtrap", "miasmatrap", "deathtrap", "bladesentinel"):
            if new_pt not in existing:
                nr = dict(base_trap)
                nr["pet type"] = new_pt
                nr["partysend"] = "1"
                rows.append(nr)
    return write_excel_tsv("pettype.txt", headers, rows)


def _build_asskillicon_pair() -> str:
    """
    Build data/hd/global/ui/spells/assassin/asskillicon.sprite and .lowend.sprite
    with custom normal & pressed frames for the 8 updated Assassin skill icons:
      - IconCel  0 (frames  0,  1): Shrapnel Sentry (Sentry triangle with eye + Blade Fury shuriken on top)
      - IconCel  2 (frames  2,  3): Caltrops (AI-generated spiked caltrops silhouette stamped in silver plate)
      - IconCel  6 (frames  6,  7): Soul Siphon Sentry (Sentry triangle with eye + curled Cobra hood on top)
      - IconCel 12 (frames 12, 13): Lightning Sentry (Vanilla Charged Bolt Sentry icon from Cel 6)
      - IconCel 14 (frames 14, 15): Shuriken (Single large symmetric 8-pointed shuriken + motion arcs)
      - IconCel 16 (frames 16, 17): Ice Sentry (Sentry triangle with eye + radiating frozen bolt on top)
      - IconCel 56 (frames 56, 57): Omnislash (AI-generated rapid multi-sword slash silhouette stamped in silver plate)
      - IconCel 58 (frames 58, 59): Electrocute (Simple white-plate thunderbolt stamped on Assassin dark stone tile)
    """
    import math
    import os
    import subprocess
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    d2r_root = os.path.dirname(MOD_ROOT)
    assets_dir = os.path.join(d2r_root, "assets", "skill_icons")
    ass_src = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/assassin/asskillicon.sprite")
    ass_low_src = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/assassin/asskillicon.lowend.sprite")
    bar_src = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/barbarian/baskillicon.sprite")
    sor_src = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/sorceress/soskillicon.sprite")

    with open(ass_src, "rb") as f:
        raw_hd = f.read()
    with open(ass_low_src, "rb") as f:
        raw_low = f.read()
    with open(bar_src, "rb") as f:
        bar_raw = f.read()[40:]
    with open(sor_src, "rb") as f:
        sor_raw = f.read()[40:]

    hdr_hd = raw_hd[:40]
    ass_raw = raw_hd[40:]
    out_hd = bytearray(ass_raw)

    hdr_low = raw_low[:40]
    out_low = bytearray(raw_low[40:])

    fw, fh, nframes = 132, 130, 60
    row_bytes = nframes * fw * 4
    plate_x0, plate_x1 = 19, 112
    plate_y0, plate_y1 = 19, 111
    plate_w = plate_x1 - plate_x0
    plate_h = plate_y1 - plate_y0

    # 1. Reconstruct clean silver-plate templates (normal & pressed) from Barbarian passive cels
    donor_cels = (2, 4, 6, 16, 18, 20, 30, 38, 44)
    silver_tmpls = [bytearray(fw * fh * 4), bytearray(fw * fh * 4)]
    for pressed in (0, 1):
        st = silver_tmpls[pressed]
        g_min = 112 if pressed else 136
        g_max = 172 if pressed else 198
        for y in range(fh):
            in_plate_y = plate_y0 <= y < plate_y1
            for x in range(fw):
                in_plate = in_plate_y and (plate_x0 <= x < plate_x1)
                clean_silver = []
                samples = []
                for dc in donor_cels:
                    soff = y * row_bytes + ((dc + pressed) * fw + x) * 4
                    r, g, b, a = bar_raw[soff : soff + 4]
                    samples.append((r + g + b, r, g, b, a))
                    if in_plate and (r - b) <= 0 and g_min <= g <= g_max:
                        clean_silver.append((r + g + b, r, g, b, a))
                if clean_silver:
                    clean_silver.sort(key=lambda t: t[0])
                    _, r, g, b, a = clean_silver[len(clean_silver) // 2]
                else:
                    samples.sort(key=lambda t: t[0])
                    _, r, g, b, a = samples[-2]
                st[(y * fw + x) * 4 : (y * fw + x) * 4 + 4] = bytes((r, g, b, a))

    # 2. Reconstruct clean dark-brown stone button templates (normal & pressed) from Assassin cels
    brown_tmpls = [bytearray(fw * fh * 4), bytearray(fw * fh * 4)]
    ass_donors = tuple(range(0, 60, 2))
    for pressed in (0, 1):
        bt = brown_tmpls[pressed]
        for y in range(fh):
            for x in range(fw):
                brown = []
                samples = []
                for dc in ass_donors:
                    soff = y * row_bytes + ((dc + pressed) * fw + x) * 4
                    r, g, b, a = ass_raw[soff : soff + 4]
                    samples.append((r + g + b, r, g, b, a))
                    if (r - b) >= 14 and 20 <= g <= 68:
                        brown.append((r + g + b, r, g, b, a))
                if brown:
                    brown.sort(key=lambda t: t[0])
                    _, r, g, b, a = brown[len(brown) // 2]
                else:
                    samples.sort(key=lambda t: t[0])
                    _, r, g, b, a = samples[len(samples) // 3]
                bt[(y * fw + x) * 4 : (y * fw + x) * 4 + 4] = bytes((r, g, b, a))

    def is_fg_pixel(r: int, g: int, b: int, pressed: int) -> bool:
        g_thr = 56 if pressed else 68
        if (r - b) <= 13 and g >= g_thr:
            return True
        if (r + g + b) < 92 and (r - b) <= 18:
            return True
        return False

    def sample_bilinear(raw_buf: bytes, cel: int, sx: float, sy: float):
        ix, iy = int(math.floor(sx)), int(math.floor(sy))
        fx, fy = sx - ix, sy - iy
        rgba = [0.0, 0.0, 0.0, 0.0]
        for oy in (0, 1):
            for ox in (0, 1):
                cx = max(0, min(fw - 1, ix + ox))
                cy = max(0, min(fh - 1, iy + oy))
                wt = ((1.0 - fx) if ox == 0 else fx) * ((1.0 - fy) if oy == 0 else fy)
                soff = (cy * row_bytes) + (cel * fw + cx) * 4
                for c in range(4):
                    rgba[c] += raw_buf[soff + c] * wt
        return [int(round(v)) for v in rgba]

    def stamp_sentry_triangle(buf: bytearray, pressed: int) -> None:
        sh = 2 if pressed else 0
        for y in range(62 + sh, 108 + sh):
            half_w = (y - (60 + sh)) * 0.72 + 4.0
            for x in range(plate_x0, plate_x1):
                if abs(x - (65.5 + sh)) <= half_w:
                    soff = (y * row_bytes) + ((6 + pressed) * fw + x) * 4
                    r, g, b, _ = ass_raw[soff : soff + 4]
                    if is_fg_pixel(r, g, b, pressed):
                        doff = (y * fw + x) * 4
                        buf[doff : doff + 4] = bytes((r, g, b, 255))

    def stamp_silver_mask(base_buf: bytearray, mask, pressed: int) -> bytearray:
        out = bytearray(base_buf)
        st = silver_tmpls[pressed]
        bright = 0.84 if pressed else 1.0
        for y in range(plate_y0, plate_y1):
            for x in range(plate_x0, plate_x1):
                m = mask[y][x]
                m_tl = mask[y - 1][x - 1]
                m_br = mask[y + 1][x + 1]
                m_max = max(m, mask[y - 1][x], mask[y + 1][x], mask[y][x - 1], mask[y][x + 1])
                if m_max <= 0.05:
                    continue
                p_off = (y * fw + x) * 4
                br_r, br_g, br_b, _ = out[p_off : p_off + 4]
                if m <= 0.12:
                    t = min(1.0, (m_max - 0.05) / 0.5)
                    out[p_off : p_off + 4] = bytes(
                        (
                            int(br_r * (1.0 - 0.88 * t)),
                            int(br_g * (1.0 - 0.88 * t)),
                            int(br_b * (1.0 - 0.88 * t)),
                            255,
                        )
                    )
                    continue
                sr, sg, sb, _ = st[p_off : p_off + 4]
                if m_tl < 0.35:
                    sr = min(255, sr + int(48 * bright))
                    sg = min(255, sg + int(48 * bright))
                    sb = min(255, sb + int(48 * bright))
                elif m_br < 0.35:
                    sr = max(0, sr - int(42 * bright))
                    sg = max(0, sg - int(42 * bright))
                    sb = max(0, sb - int(42 * bright))
                alpha_t = min(1.0, (m - 0.12) / 0.45)
                r = int(br_r * (1.0 - alpha_t) + sr * alpha_t)
                g = int(br_g * (1.0 - alpha_t) + sg * alpha_t)
                b = int(br_b * (1.0 - alpha_t) + sb * alpha_t)
                out[p_off : p_off + 4] = bytes((r, g, b, 255))
        return out

    def stamp_ai_jpg(filename: str, pressed: int, crop_margin: float = 0.06) -> bytearray:
        img_path = os.path.join(assets_dir, filename)
        keep_frac = 1.0 - 2.0 * crop_margin
        art_px = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                img_path,
                "-vf",
                f"crop=iw*{keep_frac:.2f}:ih*{keep_frac:.2f}:iw*{crop_margin:.2f}:ih*{crop_margin:.2f},scale={plate_w}:{plate_h}:flags=lanczos",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ]
        )
        sh = 2 if pressed else 0
        mask = [[0.0] * fw for _ in range(fh)]
        for py in range(plate_h):
            sy = py - sh
            if not (0 <= sy < plate_h):
                continue
            for px_i in range(plate_w):
                sx = px_i - sh
                if not (0 <= sx < plate_w):
                    continue
                if min(px_i, plate_w - 1 - px_i, py, plate_h - 1 - py) < 2:
                    continue
                aoff = (sy * plate_w + sx) * 3
                lum = (art_px[aoff] + art_px[aoff + 1] + art_px[aoff + 2]) / (3.0 * 255.0)
                mask[plate_y0 + py][plate_x0 + px_i] = max(0.0, min(1.0, (lum - 0.35) / 0.35))
        return stamp_silver_mask(brown_tmpls[pressed], mask, pressed)

    fw_low, fh_low = 67, 65
    row_bytes_low = nframes * fw_low * 4

    def write_frame_pair(fidx: int, buf_hd: bytearray) -> None:
        for y in range(fh):
            row_off = y * row_bytes + fidx * fw * 4
            out_hd[row_off : row_off + fw * 4] = buf_hd[y * fw * 4 : (y + 1) * fw * 4]
        buf_low = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgba",
                "-s",
                f"{fw}x{fh}",
                "-i",
                "-",
                "-vf",
                "scale=66:65:flags=lanczos",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgba",
                "-",
            ],
            input=bytes(buf_hd),
        )
        for y in range(fh_low):
            row_off_low = y * row_bytes_low + fidx * fw_low * 4
            out_low[row_off_low : row_off_low + 66 * 4] = buf_low[y * 66 * 4 : (y + 1) * 66 * 4]

    for pressed in (0, 1):
        sh = 2 if pressed else 0

        # 1. Shrapnel Sentry (IconCel 0): Sentry triangle + Blade Fury shuriken over top
        f_shrapnel = bytearray(brown_tmpls[pressed])
        for y in range(19 + sh, 68 + sh):
            for x in range(38 + sh, 94 + sh):
                dx = (x - (65.5 + sh)) * 1.22
                dy = (y - (41.0 + sh)) * 1.22
                if dx > 3.0 and dy > 3.0:
                    dx = -dx
                sx = 46.5 + sh + dx
                sy = 48.0 + sh + dy
                if 18 <= sx <= 76 and 18 <= sy <= 78 and math.hypot(dx, dy) <= 28.5:
                    r, g, b, _ = sample_bilinear(ass_raw, 10 + pressed, sx, sy)
                    if is_fg_pixel(r, g, b, pressed):
                        doff = (y * fw + x) * 4
                        f_shrapnel[doff : doff + 4] = bytes((r, g, b, 255))
        stamp_sentry_triangle(f_shrapnel, pressed)
        write_frame_pair(0 + pressed, f_shrapnel)

        # 2. Caltrops (IconCel 2): AI-generated spiked caltrops silhouette
        write_frame_pair(2 + pressed, stamp_ai_jpg("caltrops.jpg", pressed, crop_margin=0.06))

        # 3. Lightning Sentry (IconCel 12): Copy vanilla Charged Bolt Sentry icon from Cel 6
        f_light = bytearray(fw * fh * 4)
        for y in range(fh):
            soff = (y * row_bytes) + (6 + pressed) * fw * 4
            f_light[y * fw * 4 : (y + 1) * fw * 4] = ass_raw[soff : soff + fw * 4]
        write_frame_pair(12 + pressed, f_light)

        # 4. Soul Siphon Sentry (IconCel 6): Sentry triangle + curled Cobra Strike hood over top
        f_siphon = bytearray(brown_tmpls[pressed])
        for y in range(19 + sh, 80 + sh):
            for x in range(32 + sh, 98 + sh):
                if (y - sh) > 58 and abs((x - sh) - 65.5) > ((y - sh) - 50) * 0.85 + 11.0:
                    continue
                sx = 64.0 + sh + (x - (65.5 + sh)) * 1.18
                sy = 50.0 + sh + (y - (46.0 + sh)) * 1.18
                if 20 <= sx - sh <= 104 and 19 <= sy - sh <= 83:
                    if 28 <= (sy - sh) <= 36 and ((sx - sh) < 51 or (sx - sh) > 75):
                        continue
                    if ((sx - sh) < 34 and (sy - sh) < 61) or ((sx - sh) > 94):
                        continue
                    r, g, b, _ = sample_bilinear(ass_raw, 50 + pressed, sx, sy)
                    if is_fg_pixel(r, g, b, pressed):
                        doff = (y * fw + x) * 4
                        f_siphon[doff : doff + 4] = bytes((r, g, b, 255))
        stamp_sentry_triangle(f_siphon, pressed)
        write_frame_pair(6 + pressed, f_siphon)

        # 5. Shuriken (IconCel 14): Single large symmetric 8-pointed shuriken + motion arcs
        f_shuriken = bytearray(brown_tmpls[pressed])
        for y in range(plate_y0, plate_y1):
            for x in range(plate_x0, plate_x1):
                if ((x - sh) > 76 and (y - sh) < 55) or ((x - sh) < 52 and (y - sh) > 78):
                    soff = (y * row_bytes) + ((10 + pressed) * fw + x) * 4
                    r, g, b, _ = ass_raw[soff : soff + 4]
                    if is_fg_pixel(r, g, b, pressed):
                        doff = (y * fw + x) * 4
                        f_shuriken[doff : doff + 4] = bytes((r, g, b, 255))
        for y in range(plate_y0, plate_y1):
            for x in range(plate_x0, plate_x1):
                dx = (x - (65.5 + sh)) / 1.40
                dy = (y - (65.0 + sh)) / 1.40
                if dx > 3.0 and dy > 3.0:
                    dx = -dx
                sx = 46.5 + sh + dx
                sy = 48.5 + sh + dy
                if 18 <= sx - sh <= 76 and 18 <= sy - sh <= 79 and math.hypot(dx, dy) <= 29.0:
                    r, g, b, _ = sample_bilinear(ass_raw, 10 + pressed, sx, sy)
                    if is_fg_pixel(r, g, b, pressed):
                        doff = (y * fw + x) * 4
                        f_shuriken[doff : doff + 4] = bytes((r, g, b, 255))
        write_frame_pair(14 + pressed, f_shuriken)

        # 6. Ice Sentry (IconCel 16): Sentry triangle + radiating frozen bolt on top
        f_ice = bytearray(brown_tmpls[pressed])
        for y in range(19 + sh, 68 + sh):
            for x in range(34 + sh, 98 + sh):
                sx = 65.5 + sh + (x - (65.5 + sh)) * 1.55
                sy = 65.0 + sh + (y - (41.0 + sh)) * 1.55
                if 20 <= sx - sh <= 110 and 20 <= sy - sh <= 110 and math.hypot(sx - (65.5 + sh), sy - (65.0 + sh)) <= 44.0:
                    r, g, b, _ = sample_bilinear(ass_raw, 52 + pressed, sx, sy)
                    if is_fg_pixel(r, g, b, pressed):
                        doff = (y * fw + x) * 4
                        f_ice[doff : doff + 4] = bytes((r, g, b, 255))
        stamp_sentry_triangle(f_ice, pressed)
        write_frame_pair(16 + pressed, f_ice)

        # 7. Omnislash (IconCel 56): AI-generated multi-sword flurry silhouette
        write_frame_pair(56 + pressed, stamp_ai_jpg("omnislash.jpg", pressed, crop_margin=0.06))

        # 8. Electrocute (IconCel 58): Simple white-plate thunderbolt on Assassin dark brown tile
        f_electro = bytearray(brown_tmpls[pressed])
        for y in range(plate_y0, plate_y1):
            for x in range(plate_x0, plate_x1):
                soff = (y * row_bytes) + ((26 + pressed) * fw + x) * 4
                r, g, b, _ = sor_raw[soff : soff + 4]
                if is_fg_pixel(r, g, b, pressed):
                    doff = (y * fw + x) * 4
                    f_electro[doff : doff + 4] = bytes((r, g, b, 255))
        write_frame_pair(58 + pressed, f_electro)

        # 9. Lethality (IconCel 20): Crossed broadsword and Assassin claw plate
        write_frame_pair(20 + pressed, stamp_ai_jpg("lethality.jpg", pressed, crop_margin=0.06))

        # 10. Flow (IconCel 22): Hooded Assassin silhouette with swirling speed/flow arcs
        write_frame_pair(22 + pressed, stamp_ai_jpg("flow.jpg", pressed, crop_margin=0.06))

        # 11. Shadow Bind (IconCel 38): Monster bound by swirling shadow tendrils around its limbs/feet
        write_frame_pair(38 + pressed, stamp_ai_jpg("shadow_bind.jpg", pressed, crop_margin=0.06))

    dst_hd = os.path.join(MOD_ROOT, "data/hd/global/ui/spells/assassin/asskillicon.sprite")
    dst_low = os.path.join(MOD_ROOT, "data/hd/global/ui/spells/assassin/asskillicon.lowend.sprite")
    os.makedirs(os.path.dirname(dst_hd), exist_ok=True)
    with open(dst_hd, "wb") as f:
        f.write(hdr_hd + out_hd)
    with open(dst_low, "wb") as f:
        f.write(hdr_low + out_low)
    return f"{dst_hd}, {dst_low}"


def build_skills_all(cfg: dict) -> str:
    from mod_builder.affixes import build_itemstatcost
    from mod_builder.common import update_mod_hd_missiles_json
    from mod_builder.weapons_armor import build_missiles

    p0 = build_itemstatcost(cfg)
    p1 = build_states(cfg)
    p2, p3 = build_skills_and_desc(cfg)
    p4 = build_skill_strings(cfg)
    p5 = build_missiles(cfg)
    p6 = _build_submenu_skillicon_pair(".sprite", 132, 130)
    p7 = _build_submenu_skillicon_pair(".lowend.sprite", 67, 65)
    p8 = _build_baskillicon_pair(".sprite", 132, 130)
    p9 = _build_baskillicon_pair(".lowend.sprite", 67, 65)
    p10 = _build_baskilltree_pair()
    p11 = _build_barbarian_state_machine()
    p12 = build_pettype(cfg)
    p13 = _build_assassin_state_machine()
    p14 = _build_animdata()
    p15 = update_mod_hd_missiles_json([
        ("shock field on ground", "expansion_fire_spikes_ground"),
        ("inferno sentry 1", "expansion_shockwave"),
        ("inferno sentry 2", "expansion_shockwave"),
        ("progressive radius damage", "expansion_shockwave"),
        ("unholybolt_2", "null"),
        ("unholybolt_3", "null"),
        ("unholybolt_4", "null"),
        ("sentrychargedbolt", "unholy_bolt"),
        ("catapult cold ball on", "ice_orb"),
        ("catapult cold ball", "ice_bolt"),
        ("catapult cold explosion", "ice_bolt"),
        ("frozenhorror_arcticblast_2", "null"),
        ("sentrylightningbolt_2", "null"),
    ])
    p16 = _build_chargeboltsentry_hd()
    p17 = _build_asskilltree_pair()
    p18 = _build_asskillicon_pair()
    return f"{p0}, {p1}, {p2}, {p3}, {p4}, {p5}, {p6}, {p7}, {p8}, {p9}, {p10}, {p11}, {p12}, {p13}, {p14}, {p15}, {p16}, {p17}, {p18}"

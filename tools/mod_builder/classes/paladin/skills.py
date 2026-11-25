#!/usr/bin/env python3
"""
paladin/skills.py
Paladin 30-Skill Overhaul:
  - Combat Skills (Sacrifice, Smite, Holy Bolt, Zeal, Charge, Vengeance 156-deg Cleave, Blessed Chain Hammer, Conversion, Holy Shield, Fist of the Heavens)
  - Offensive Auras (Might, Holy Fire, Thorns, Blessed Aim, Concentration, Holy Freeze, Holy Shock, Sanctuary, Fanaticism, S-Curve Party Conviction)
  - Defensive Auras (0-Mana Prayer/Meditation/Redemption recovery stances, Resist Fire/Cold/Lightning +Vengeance/Conviction synergies, Defiance, Cleansing, Vigor, Salvation)
"""
from typing import Dict, List, Tuple

from mod_builder.classes.common import (
    COND_ARC,
    COND_COLD_MULT,
    COND_EXP,
    COND_STANCE,
    RAMP12,
    RAMP34,
    RAMP56,
    _clear_dsc3_synergies,
    _curve_lev_brackets,
    _set_dsc_line,
    cond_cold_dur,
    cond_elem_arc,
    cond_elem_exp,
    cond_elem_sta,
    cond_fire_add,
    cond_fire_radius,
    cond_ltng_chain,
    cond_ltng_strike,
    parse_int,
    scale_int,
)

def _apply_paladin_skills(by_name: Dict[str, Dict[str, str]]) -> None:
    """Apply the Paladin Combat, Offensive Aura, and Defensive Aura overhaul to skills.txt."""
    # Universal Castalia Stamina rules:
    #   - Half-Power Rule: physical/speed effects scale linearly from 50% (0% Stamina) -> 100% (Full Stamina)
    #   - Stun Exhaustion Rule: stuns scale linearly 100% -> 33% Stamina, hard cutoff (0) below 33%
    RESTED_PCT = "((stat('stamina'.accr)*100)/max(256,stat('maxstamina'.accr)))"

    # -------------------------------------------------------------------------
    # 1. COMBAT SKILLS
    # -------------------------------------------------------------------------
    # Sacrifice (Id 96): 0 Mana; 300% + 32%/lvl (ramped) ED scaled 50%->100% by Stamina;
    # self-damage 12% scaling down to 4% via blvl + Prayer/Redemption;
    # synergies: Prayer (12%), Redemption (12%), Fanaticism (10%); zero passive bonus
    sac = by_name["Sacrifice"]
    sac["minmana"] = "0"
    sac["mana"] = "0"
    sac["lvlmana"] = "0"
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
    sac["calc1"] = f"(({RAMP12}+(skill('Prayer'.blvl)+skill('Redemption'.blvl))*par8+skill('Fanaticism'.blvl)*par7)*(100+{RESTED_PCT}))/200"
    sac["calc2"] = "max(par6, par5 - blvl/par3 - (skill('Prayer'.blvl)+skill('Redemption'.blvl))/4)"

    # Smite (Id 97): 0 Mana; Boosted innate ED (100% + 45%/lvl ramped -> +955% ED at Lvl 20) scaled 50%->100% by Stamina,
    # 1.0s + 0.24s/lvl stun scaled linearly 100%->33% Stamina (0 stun below 33%), +15%/lvl ED synergy from Charge
    smite = by_name["Smite"]
    smite["minmana"] = "0"
    smite["mana"] = "0"
    smite["lvlmana"] = "0"
    smite["Param1"] = "25"   # Stun Length baseline (1.0s)
    smite["Param2"] = "6"    # Stun Length per level (+0.24s)
    smite["Param3"] = "100"  # Damage % baseline (up from 60%)
    smite["Param4"] = "45"   # Damage % per level (ramped -> +955% ED at Lvl 20)
    smite["Param8"] = "15"   # Charge synergy % (+15%/lvl -> +300% ED at 20 Charge)
    smite["calc1"] = f"(({RAMP34}+skill('Charge'.blvl)*par8)*(100+{RESTED_PCT}))/200"
    smite["calc2"] = f"(({RESTED_PCT})>=33)?min(250,((min(ln12,250)*({RESTED_PCT}))/100*{COND_COLD_MULT})/100):0"

    # Charge (Id 107): 0 Mana; 150% + 32%/lvl (ramped) ED & Charge Speed scaled 50%->100% by Stamina,
    # 12% synergy from Vigor & Might, AND Stuns target on impact (1.4s base + 8%/lvl Smite synergy,
    # scaled linearly 100%->33% Stamina with hard cutoff 0 below 33%)
    chg = by_name["Charge"]
    chg["minmana"] = "0"
    chg["mana"] = "0"
    chg["lvlmana"] = "0"
    chg["Param3"] = "150"  # Damage % baseline
    chg["Param4"] = "32"   # Damage % per level
    chg["Param6"] = "8"    # Stun duration synergy % from Smite
    chg["*Param6 Description"] = "Stun Duration synergy"
    chg["Param8"] = "12"   # Damage synergy % from Vigor & Might
    chg["calc1"] = f"(({RAMP34}+(skill('Vigor'.blvl)+skill('Might'.blvl))*par8)*(100+{RESTED_PCT}))/200"
    chg["calc2"] = f"(par1*(100+{RESTED_PCT}))/200"
    chg["calc4"] = "0"     # 0% physical converted to elemental so 100% stays Physical + Stun
    chg["EType"] = "stun"
    chg["ELen"] = "35"     # 1.4s fixed base stun (only increases with points in Smite)
    chg["ELevLen1"] = "0"
    chg["ELevLen2"] = "0"
    chg["ELevLen3"] = "0"
    chg["ELenSymPerCalc"] = f"(({RESTED_PCT})>=33)?((((100+skill('Smite'.blvl)*par6)*({RESTED_PCT}))/100*{COND_COLD_MULT})/100-100):-100"

    # Zeal (Id 106): 0 Mana; Capped at 5 hits (2 hits Lvl 1-5, 3 hits Lvl 6-11, 4 hits Lvl 12-17, 5 hits Lvl 18+),
    # vanilla 100% rollback (so 4-frame hits strictly require EIAS = 75), 20% + 11%/lvl (ramped -> +229% ED at Lvl 20),
    # +8% Sacrifice synergy (+160% ED at Lvl 20 -> +389% total skill ED), scaled 50%->100% by Stamina.
    zeal = by_name["Zeal"]
    zeal["minmana"] = "0"
    zeal["mana"] = "0"
    zeal["lvlmana"] = "0"
    zeal["Param2"] = "100"  # % Anim frame rollback (100% = full 7 base frames per swing; melee rangeadder prevents whiffing)
    zeal["Param3"] = "20"   # Damage % baseline
    zeal["Param4"] = "11"   # Damage % per level (20 + 19*11 = 229% at Lvl 20)
    zeal["Param5"] = "2"    # # of hits Min
    zeal["Param6"] = "5"    # # of hits Max (vanilla 5-hit cap; degrades 5->4->3->2 with Stamina)
    zeal["Param8"] = "8"    # Sacrifice synergy %
    zeal["calc1"] = cond_ltng_strike(f"max(2,(min(par5+lvl/6,par6)*(100+{RESTED_PCT}))/200)")
    zeal["calc2"] = f"(({RAMP34}+skill('Sacrifice'.blvl)*par8)*(100+{RESTED_PCT}))/200"
    zeal["ToHit"] = "20"
    zeal["LevToHit"] = "12"

    # Vengeance (Id 111): Frontal Arc Cleave (srvstfunc=35 + srvdofunc=164, 156-degree arc via calc5=13, calc6=30, +0 range bonus),
    # halved standalone base scaling: 45% at Lvl 1 -> 159% Fire/Cold/Ltng damage at Lvl 20 (Param1=45, Param2=6 via RAMP12),
    # synergized ONLY by individual Resist Fire / Resist Cold / Resist Lightning auras (+23%/lvl -> +460% at 20 pts, reaching +619% in chosen elements).
    veng = by_name["Vengeance"]
    veng["srvdofunc"] = "164"
    veng["cltdofunc"] = "103"
    veng["aurafilter"] = "41347"
    veng["tgtoverlay"] = "fire_hit"
    veng["srvoverlay"] = "fire_hit"
    veng["manashift"] = "6"
    veng["mana"] = "12"
    veng["lvlmana"] = "1"
    veng["Param1"] = "45"   # Damage % baseline (45% at Lvl 1, halved from 90%)
    veng["Param2"] = "6"    # Damage % per level (ramped -> 45 + 19*6 = 159% at Lvl 20)
    veng["Param7"] = ""
    veng["Param8"] = "23"   # +23%/lvl to specific element from Resist Fire / Resist Cold / Resist Lightning (+460% at 20 pts -> 619% total)
    veng["calc1"] = f"{RAMP12}+skill('Resist Fire'.blvl)*par8"
    veng["calc2"] = f"{RAMP12}+skill('Resist Cold'.blvl)*par8"
    veng["calc3"] = f"{RAMP12}+skill('Resist Lightning'.blvl)*par8"
    veng["calc5"] = f"13 + (({COND_STANCE} >= 1) ? (({COND_EXP} * 7) / 50) : 0)"    # 156 deg -> 240 deg scaled by Expansion
    veng["calc6"] = "30"
    veng["calc7"] = f"({COND_STANCE} >= 1) ? (({COND_EXP} * 2) / 50) : 0"          # +0 -> +2 sub-tiles reach scaled by Expansion
    veng["ELenSymPerCalc"] = cond_elem_sta(3, 100)                                  # up to 2x Cold chill under Cold Conduction (Stasis)
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
    bham["aurarangecalc"] = cond_fire_add("par1", 4)
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
    bham["calc1"] = cond_ltng_chain("ln34/par5")
    bham["*calc1 desc"] = "# of target jump hits"
    bham["calc4"] = "min(250," + cond_cold_dur("par2*(100+skill('Smite'.blvl)*par6)/100") + ")"
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
    conv["auralencalc"] = cond_cold_dur("300+(lvl-1)*25/2")
    conv["ToHit"] = "50"
    conv["LevToHit"] = "15"
    conv["SrcDam"] = "64"

    # Holy Shield (Id 117): Tactical defensive bastion cast before engaging dangerous packs/bosses:
    #   - Removed bonus Smite damage entirely (refocused as a pure defensive skill)
    #   - 0% innate Defense bonus; 100% of its Defense bonus comes from Defiance synergy (+15%/lvl -> up to +300% Defense)
    #   - Vanilla Block % chance restored (Param5 = 10, Param6 = 40 -> +14% at sLvl 1, +25% at sLvl 5, +31% at sLvl 10, +35% at sLvl 20)
    #   - Grants flat Physical Damage Reduced & Magic Damage Reduced (calc2 = 5 at sLvl 1 -> 22 at sLvl 10 -> 62 at sLvl 20)
    #   - Bumped duration: 25s + 3s/lvl (Param1 = 625, Param2 = 75 -> 25s at sLvl 1, 52s at sLvl 10, 82s at sLvl 20)
    #   - Higher Mana cost: 40 + 2/lvl (40 Mana at sLvl 1 -> 78 Mana at sLvl 20)
    hshd = by_name["Holy Shield"]
    hshd["mana"] = "40"
    hshd["lvlmana"] = "2"
    hshd["Param1"] = "625"  # 25s baseline duration (bumped from 15s)
    hshd["Param2"] = "75"   # +3s per level (bumped from +2s/lvl -> 82s at Lvl 20)
    hshd["auralencalc"] = cond_cold_dur("ln12")
    hshd["Param3"] = "0"    # 0% base Defense
    hshd["Param4"] = "0"    # 0% Defense per level
    hshd["Param5"] = "10"   # Vanilla Block % Min (restored to 10)
    hshd["Param6"] = "40"   # Vanilla Block % Max (restored to 40 -> +14% at Lvl 1, +35% at Lvl 20)
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
    foh["calc4"] = f"par1+(lvl-1)/4+(({COND_STANCE}==2)?(({COND_ARC}>=55)?2:(({COND_ARC}>=25)?1:0)):0)"
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
    hfire["aurarangecalc"] = f"{elem_aura_range} + {cond_elem_exp(1, 4)}"
    hfire["perdelay"] = f"50 - {cond_elem_arc(1, 15)}"
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
    hfrz["aurarangecalc"] = f"{elem_aura_range} + {cond_elem_exp(3, 4)}"
    hfrz["perdelay"] = f"50 - {cond_elem_arc(3, 15)}"
    hfrz["aurastatcalc1"] = f"0 - (dm34 + {cond_elem_sta(3, 15)})"
    hfrz["aurastatcalc2"] = f"0 - (dm34 + {cond_elem_sta(3, 15)})"
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
    hshk["aurarangecalc"] = f"{elem_aura_range} + {cond_elem_exp(2, 4)}"
    hshk["perdelay"] = f"50 - {cond_elem_arc(2, 15)}"
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
    fana["aurastatcalc1"] = "dm34"
    fana["aurastatcalc3"] = "ln56*2/3"

    # Conviction (Id 123):
    # Reworked into a friendly party aura (srvdofunc=65, aurafilter=73731, matching Might/Fanaticism/Salvation)
    # that buffs the Paladin, all party members, and all hirelings/summons along a true logistic S-curve:
    #   clc1 = min(lvl-1,4)+3*max(0,min(lvl-5,10))+max(0,min(lvl-15,5))+max(0,lvl-20)/2
    #   (climbs slowly Lvl 1..5 [0 -> 4], rapidly Lvl 5..15 [4 -> 34], and tapers off Lvl 15..20+ [34 -> 39])
    # Because Levels 1..5 sit on the flat bottom toe of the S-curve, a 1-point Conviction (even with +3..4 All Skills)
    # grants very little (+3% at Lvl 1 -> +15% at Lvl 5 w/ 20 Resist); the Paladin must invest hard points into BOTH
    # Conviction (to climb Levels 6..15) AND the corresponding Resist aura:
    #   - aurastat1 = passive_fire_mastery: min(50,(skill('Resist Fire'.blvl)*(2+clc1*6/5))/20)  (+2% Lvl 1 -> +6% Lvl 5 -> +24% Lvl 10 -> +42% Lvl 15 -> +48% Lvl 20, hard-capped at +50%)
    #   - aurastat2 = passive_cold_mastery: min(50,(skill('Resist Cold'.blvl)*(2+clc1*6/5))/20)
    #   - aurastat3 = passive_ltng_mastery: min(50,(skill('Resist Lightning'.blvl)*(2+clc1*6/5))/20)
    #   - aurastat4 = item_damagetargetac:  -clc2, where clc2 = 60+clc1*18 (-60 at Lvl 1 -> -132 at Lvl 5 -> -402 at Lvl 10 -> -672 at Lvl 15 -> -762 at Lvl 20)
    #   - aurastat5 = item_slow:            clc3,  where clc3 = 4+(clc1*4)/5 (4% at Lvl 1 -> 7% at Lvl 5 -> 19% at Lvl 10 -> 31% at Lvl 15 -> 35% at Lvl 20)
    # - perdelay = 10 (0.4s tick) with active mana upkeep (manashift=4, mana=4, lvlmana=1 -> 1.2/sec at Lvl 1, 7.1/sec at Lvl 20).
    convic = by_name["Conviction"]
    convic["srvdofunc"] = "65"
    convic["aurafilter"] = "73731"
    convic["aurastate"] = "conviction"
    convic["auratargetstate"] = "conviction"
    convic["immediate"] = "1"
    convic["perdelay"] = "10"
    convic["minmana"] = "0"
    convic["manashift"] = "4"
    convic["mana"] = "4"
    convic["lvlmana"] = "1"
    convic["calc1"] = "min(lvl-1,4)+3*max(0,min(lvl-5,10))+max(0,min(lvl-15,5))+max(0,lvl-20)/2"
    convic["*calc1 desc"] = "Logistic S-curve index (0 at Lvl 1 -> 4 at Lvl 5 -> 34 at Lvl 15 -> 39 at Lvl 20)"
    convic["calc2"] = "60+clc1*18"
    convic["*calc2 desc"] = "-Monster Defense Per Hit magnitude"
    convic["calc3"] = "4+(clc1*4)/5"
    convic["*calc3 desc"] = "Slows Target %"
    convic["aurastat1"] = "passive_fire_mastery"
    convic["aurastatcalc1"] = "(min(50,(skill('Resist Fire'.blvl)*(2+clc1*6/5))/20)*2)/3"
    convic["aurastat2"] = "passive_cold_mastery"
    convic["aurastatcalc2"] = "(min(50,(skill('Resist Cold'.blvl)*(2+clc1*6/5))/20)*2)/3"
    convic["aurastat3"] = "passive_ltng_mastery"
    convic["aurastatcalc3"] = "(min(50,(skill('Resist Lightning'.blvl)*(2+clc1*6/5))/20)*2)/3"
    convic["aurastat4"] = "item_damagetargetac"
    convic["aurastatcalc4"] = "-clc2"
    convic["aurastat5"] = "item_slow"
    convic["aurastatcalc5"] = "clc3"
    convic["aurastat6"] = ""
    convic["aurastatcalc6"] = ""
    convic["passivestate"] = ""
    convic["passivestat1"] = "passive_fire_mastery"
    convic["passivecalc1"] = "min(50,(skill('Resist Fire'.blvl)*(2+clc1*6/5))/20)"
    convic["passivestat2"] = "passive_cold_mastery"
    convic["passivecalc2"] = "min(50,(skill('Resist Cold'.blvl)*(2+clc1*6/5))/20)"
    convic["passivestat3"] = "passive_ltng_mastery"
    convic["passivecalc3"] = "min(50,(skill('Resist Lightning'.blvl)*(2+clc1*6/5))/20)"

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
    pray["minmana"] = "0"
    pray["manashift"] = "7"
    pray["mana"] = "0"
    pray["lvlmana"] = "0"
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

    # -------------------------------------------------------------------------
    # 4. UNIVERSAL PALADIN AURA MANA DEVOTION CURVE (all 17 Mana-Upkeep Auras)
    #    Excludes the 3 zero-mana Recovery Stances (Prayer, Meditation, Redemption).
    #    Smooth plateau curve stored in calc5 (Mana %) & calc6 (Devotion % 0..100):
    #      - 50%..100% Mana -> 100% full aura power
    #      - 25%..50%  Mana -> 75%..100%
    #      - 10%..25%  Mana -> 50%..75%
    #      -  0%..10%  Mana ->  0%..50% (extinguished at 0% Mana!)
    # -------------------------------------------------------------------------
    # Fire Conduction (Expansion): +33% radius on all non-elemental Paladin auras (+4 sub-tiles on Sanctuary)
    _ELEM_PAL_AURAS = {"Holy Fire", "Holy Freeze", "Holy Shock"}
    for sk_row in by_name.values():
        if sk_row.get("charclass") != "pal" or sk_row.get("aura") != "1":
            continue
        sk_name = sk_row.get("skill", "")
        if sk_name in _ELEM_PAL_AURAS:
            continue
        ar = sk_row.get("aurarangecalc", "").strip()
        if ar:
            if sk_name == "Sanctuary":
                sk_row["aurarangecalc"] = cond_fire_add(ar, 4)
            else:
                sk_row["aurarangecalc"] = cond_fire_radius(ar)

    _MANA_PCT = "((stat('mana'.accr)*100)/max(256,stat('maxmana'.accr)))"
    _DEVOTION_PCT = "min(100,min(50+clc5,min(33+(clc5*17)/10,clc5*5)))"
    for sk_row in by_name.values():
        if sk_row.get("charclass") != "pal" or sk_row.get("aura") != "1":
            continue
        if int(sk_row.get("mana") or "0") <= 0:
            continue
        sk_row["calc5"] = _MANA_PCT
        sk_row["*calc5 desc"] = "Current Mana %"
        sk_row["calc6"] = _DEVOTION_PCT
        sk_row["*calc6 desc"] = "Aura Mana Devotion % (50-100%:100%, 25%:75%, 10%:50%, 0%:0%)"
        for ai in range(1, 7):
            ac = sk_row.get(f"aurastatcalc{ai}", "").strip()
            if sk_row.get(f"aurastat{ai}", "").strip() and ac:
                sk_row[f"aurastatcalc{ai}"] = f"(({ac})*clc6)/100"
        if sk_row.get("skill") in ("Fanaticism", "Conviction"):
            for pi in range(1, 4):
                pc = sk_row.get(f"passivecalc{pi}", "").strip()
                if sk_row.get(f"passivestat{pi}", "").strip() and pc:
                    sk_row[f"passivecalc{pi}"] = f"(({pc})*clc6)/100"
        ar = sk_row.get("aurarangecalc", "").strip()
        if ar:
            sk_row["aurarangecalc"] = f"(({ar})*clc6)/100"
        if sk_row.get("skill") in ("Holy Fire", "Holy Freeze", "Holy Shock", "Sanctuary"):
            ed = sk_row.get("EDmgSymPerCalc", "").strip()
            if ed:
                sk_row["EDmgSymPerCalc"] = f"((100+({ed}))*clc6)/100-100"
            else:
                sk_row["EDmgSymPerCalc"] = "clc6-100"



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
    smite["desccalca1"] = "clc2"
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
    _set_dsc_line(hfire, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", f"(min(20,par1+(lvl-1)*3/4)+{cond_elem_exp(1, 4)})*2", "3")
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
    _set_dsc_line(hfrz, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", f"(min(20,par1+(lvl-1)*3/4)+{cond_elem_exp(3, 4)})*2", "3")
    _set_dsc_line(hfrz, "desc", 3, "74", "StrSkill77", "", f"dm34+{cond_elem_sta(3, 15)}", "")
    _set_dsc_line(hfrz, "desc", 4, "75", "StrSkill6", "", "enma", "exma*((100+par6)/100)")
    _set_dsc_line(hfrz, "desc", 5, "75", "StrSkillColdDamageToYourAttack", "", "edns*par5/256", "edxs*par5/256")
    _set_dsc_line(hfrz, "dsc2", 2, "", "", "", "", "")

    hshk = by_desc["holy shock"]
    _set_dsc_line(hshk, "desc", 1, "36", "StrSkill34", "", "usmc", "512")
    _set_dsc_line(hshk, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", f"(min(20,par1+(lvl-1)*3/4)+{cond_elem_exp(2, 4)})*2", "3")
    _set_dsc_line(hshk, "desc", 3, "75", "StrSkill7", "", "enma", "exma*((100+par6)/100)")
    _set_dsc_line(hshk, "desc", 4, "75", "strEskilllighttoattack", "", "edns/256", "edxs*par5/256")
    _set_dsc_line(hshk, "dsc2", 2, "", "", "", "", "")

    fana = by_desc["fanaticism"]
    _set_dsc_line(fana, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(fana, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(fana, "desc", 3, "74", "StrSkill106", "", "(dm34*clc6)/100", "")
    _set_dsc_line(fana, "desc", 4, "74", "PartDam", "", "((ln56*2/3)*clc6)/100", "")
    _set_dsc_line(fana, "desc", 5, "74", "FanYDam", "", "(ln56*clc6)/100", "")
    _set_dsc_line(fana, "desc", 6, "74", "StrSkill22", "", "(toht*clc6)/100", "")
    _set_dsc_line(fana, "dsc2", 1, "", "", "", "", "")

    convic = by_desc["conviction"]
    _set_dsc_line(convic, "desc", 1, "36", "StrSkill34", "", "usmc*5", "256")
    _set_dsc_line(convic, "desc", 2, "36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3")
    _set_dsc_line(convic, "desc", 3, "74", "ModConvicDefPerHit", "", "clc2", "")
    _set_dsc_line(convic, "desc", 4, "74", "Cgslow", "", "clc3", "")
    _set_dsc_line(convic, "desc", 5, "", "", "", "", "")
    _set_dsc_line(convic, "desc", 6, "", "", "", "", "")
    _set_dsc_line(convic, "dsc2", 1, "75", "ModConvicFireDmg", "", "min(50,(skill('Resist Fire'.blvl)*(2+clc1*6/5))/20)", "(min(50,(skill('Resist Fire'.blvl)*(2+clc1*6/5))/20)*2)/3")
    _set_dsc_line(convic, "dsc2", 2, "75", "ModConvicColdDmg", "", "min(50,(skill('Resist Cold'.blvl)*(2+clc1*6/5))/20)", "(min(50,(skill('Resist Cold'.blvl)*(2+clc1*6/5))/20)*2)/3")
    _set_dsc_line(convic, "dsc2", 3, "75", "ModConvicLtngDmg", "", "min(50,(skill('Resist Lightning'.blvl)*(2+clc1*6/5))/20)", "(min(50,(skill('Resist Lightning'.blvl)*(2+clc1*6/5))/20)*2)/3")
    _clear_dsc3_synergies(convic, "skillname123")
    _set_dsc_line(convic, "dsc3", 2, "76", "Firedplev", "skillname100", "min(50,2+clc1*6/5)/20", "")
    _set_dsc_line(convic, "dsc3", 3, "76", "Colddplev", "skillname105", "min(50,2+clc1*6/5)/20", "")
    _set_dsc_line(convic, "dsc3", 4, "76", "Ltngdplev", "skillname110", "min(50,2+clc1*6/5)/20", "")

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
    _set_dsc_line(vig, "desc", 3, "74", "StrSkill89", "", "(dm56*clc6)/100", "")
    _set_dsc_line(vig, "desc", 4, "74", "ModStr4p", "", "(clc1*clc6)/100", "")
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

    # Scale active upkeep-aura tooltip lines by clc6 (Aura Mana Devotion %) so tooltips update live with Mana
    # (Passive-only lines and Vigor/Fanaticism, already scaled above, are left intact.)
    _aura_tooltip_scales = {
        "might": ("desccalca2", "desccalca3"),
        "resist fire": ("desccalca2", "desccalca4", "desccalca5"),
        "resist cold": ("desccalca2", "desccalca4", "desccalca5"),
        "resist lightning": ("desccalca2", "desccalca4", "desccalca5"),
        "holy fire": ("desccalca2",),
        "holy shock": ("desccalca2",),
        "sanctuary": ("desccalca2",),
        "thorns": ("desccalca2", "desccalca3", "desccalca4", "desccalca5"),
        "defiance": ("desccalca2", "desccalca3", "desccalca4"),
        "blessed aim": ("desccalca2", "desccalca4"),
        "cleansing": ("desccalca2", "desccalca3"),
        "concentration": ("desccalca2", "desccalca3", "dsc2calca1"),
        "holy freeze": ("desccalca2", "desccalca3"),
        "vigor": ("desccalca2",),
        "fanaticism": ("desccalca2",),
        "conviction": (
            "desccalca2", "desccalca3", "desccalca4",
            "dsc2calca1", "dsc2calca2", "dsc2calca3",
            "dsc2calcb1", "dsc2calcb2", "dsc2calcb3",
        ),
        "salvation": ("desccalca2", "desccalca3"),
    }
    for sd_key, cols in _aura_tooltip_scales.items():
        sd_row = by_desc.get(sd_key)
        if not sd_row:
            continue
        for col in cols:
            cur = sd_row.get(col, "").strip()
            if cur and "clc6" not in cur:
                sd_row[col] = f"(({cur})*clc6)/100"




def apply_paladin_missiles(
    rows_by_name: Dict[str, Dict[str, str]],
    rows: list = None,
) -> None:
    """Apply Paladin Holy Bolt, Blessed Chain Hammer, and Fist of the Heavens missile updates."""
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

    # 3. Fist of the Heavens Lightning Conduction (skill_enchant == 2):
    #    Keep fistoftheheavensdelay 100% pristine vanilla (pSrvDoFunc=1, pSrvHitFunc=22) so dwParam
    #    (target monster GUID) is never clobbered. Instead, attach a proven trail emitter (pSrvDoFunc=2 /
    #    pCltDoFunc=3, SrvCalc1=5, CltCalc1=5) onto the moving fistoftheheavensbolt missiles so each
    #    radiating Holy Bolt emits bright electric_nova arcs (foh_conduction_nova, NextDelay=12) that
    #    damage ALL nearby monsters (including non-demons) when skill_enchant == 2, and Range=0 in solo.
    if "fistoftheheavensbolt" in rows_by_name and "nova" in rows_by_name and rows is not None:
        fohb = rows_by_name["fistoftheheavensbolt"]
        fohb["pSrvDoFunc"] = "2"
        fohb["SrvCalc1"] = "5"
        fohb["SubMissile1"] = "foh_conduction_nova"
        fohb["pCltDoFunc"] = "3"
        fohb["CltCalc1"] = "5"
        fohb["CltSubMissile1"] = "foh_conduction_nova"

        next_id = max(int(r.get("*ID") or 0) for r in rows) + 1

        if "foh_conduction_nova" not in rows_by_name:
            fnova = dict(rows_by_name["nova"])
            fnova["Missile"] = "foh_conduction_nova"
            fnova["*ID"] = str(next_id)
            fnova["pCltHitFunc"] = ""
            fnova["ClientCol"] = "1"
            fnova["ClientSend"] = "1"
            fnova["Range"] = f"({COND_STANCE} == 2) ? max(3, ({COND_EXP} * 10) / 50) : 0"
            fnova["LevRange"] = ""
            fnova["Vel"] = "14"
            fnova["MaxVel"] = "14"
            fnova["Accel"] = ""
            fnova["Size"] = "3"
            fnova["Skill"] = ""
            fnova["EType"] = "ltng"
            fnova["ApplyMastery"] = "1"
            fnova["HitShift"] = "8"
            fnova["HitClass"] = "64"
            fnova["NextHit"] = "1"
            fnova["NextDelay"] = "12"
            fnova["EMin"] = "110"
            fnova["MinELev1"] = "18"
            fnova["MinELev2"] = "52"
            fnova["MinELev3"] = "97"
            fnova["MinELev4"] = "110"
            fnova["MinELev5"] = "125"
            fnova["EMax"] = "150"
            fnova["MaxELev1"] = "20"
            fnova["MaxELev2"] = "57"
            fnova["MaxELev3"] = "102"
            fnova["MaxELev4"] = "115"
            fnova["MaxELev5"] = "130"
            fnova["EDmgSymPerCalc"] = "skill('Holy Shock'.blvl)*18"
            rows.append(fnova)
            rows_by_name["foh_conduction_nova"] = fnova




PALADIN_STRING_UPDATES: List[Tuple[int, str, str]] = [
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
        (61028, "ModConvicFireDmg", "Your / Party Fire Damage: +%d%% / +%d%%"),
        (61029, "ModConvicColdDmg", "Your / Party Cold Damage: +%d%% / +%d%%"),
        (61100, "ModConvicLtngDmg", "Your / Party Lightning Damage: +%d%% / +%d%%"),
        (61101, "ModConvicDefPerHit", "-%d to Monster Defense Per Hit"),
        (0, "skillsd124", "aura - restores life and mana after each kill"),
        (0, "skillld124", "when active, aura restores life and mana after each kill\nwhile periodically redeeming nearby slain enemies"),
        (0, "skillxld124", "when active, aura restores life and mana after each kill\nwhile periodically redeeming nearby slain enemies"),
        (0, "skillld112", "hurls an ethereal hammer that bounces between nearby enemies,\ndealing magic damage, knocking back, and stunning targets"),
        (0, "skillld117", "enhances your shield with divine power, increasing blocking\nand reducing physical and magic damage taken"),
        (0, "skillsd111", "cleaving attacks add elemental damage"),
        (0, "skillld111", "cleaves enemies in a frontal arc, adding fire, lightning,\nand cold damage to each successful attack"),
        (0, "skillsd123", "aura - empowers party elemental damage and crippling strikes"),
        (0, "skillld123", "when active, aura empowers you and your party with\nfire, cold, and lightning damage based on points in each Resistance Aura\nwhile attacks slow enemies and shred monster defense per hit"),
        (0, "skillxld123", "when active, aura empowers you and your party with\nfire, cold, and lightning damage based on points in each Resistance Aura\nwhile attacks slow enemies and shred monster defense per hit"),
        (0, "skillsd104", "aura - increases defense and reduces physical damage"),
        (0, "skillld104", "when active, aura bolsters the defense of you and your party\nand reduces physical damage taken from attacks"),
        (0, "skillsd115", "aura - increases movement speed and hit recovery"),
        (0, "skillld115", "when active, aura increases movement speed and hit recovery\nfor you and your party to swiftly reposition in battle"),
]

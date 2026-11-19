#!/usr/bin/env python3
"""
barbarian/skills.py
Barbarian 30-Skill Overhaul ("The Stamina Pendulum"):
  - Well-Rested Skills (Strike, Shield Slam, Concentrate) scaling UP with current Stamina %
  - Stamina Spenders (Leap, Leap Attack, Whirlwind) draining Stamina via Bar Stamina Reflex (Id 433) and degrading at low Stamina
  - Exhaustion / Last Stand Skills (Flurry, Barrage, Berserk, Frenzy) scaling UP with missing Stamina %
  - Combat Masteries (One-Handed, Two-Handed, Throwing, Critical Strike, Unflinching, Increased Speed, Battle Fervor, Iron Skin, Venom Ward, Natural Resistance)
  - In-Combat Warcries (3.0s shared CD: Shout vs Enduring Cry, Battle Orders vs Bloodlust, Battle Command heal, Second Wind stamina heal, Howl, Taunt, Battle Cry, War Cry)
"""
from typing import Dict, List, Tuple

from mod_builder.classes.common import (
    RAMP12,
    RAMP34,
    RAMP56,
    _clear_dsc3_synergies,
    _curve_lev_brackets,
    _set_dsc_line,
    parse_int,
    scale_int,
)

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




def apply_barbarian_missiles(rows_by_name: Dict[str, Dict[str, str]]) -> None:
    """Apply Barbarian Leap, Leap Attack, War Cry, and Stamina Reflex missile updates."""
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




def append_barbarian_helper_skills(s_headers: List[str], s_rows: List[Dict[str, str]], by_name: Dict[str, Dict[str, str]]) -> None:
    """Append hidden Barbarian Stamina helper skills (Ids 430..433)."""
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




BARBARIAN_STRING_UPDATES: List[Tuple[int, str, str]] = [
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
]

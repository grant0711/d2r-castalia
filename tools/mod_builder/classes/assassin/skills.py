#!/usr/bin/env python3
"""
assassin/skills.py
Assassin 30-Skill Overhaul:
  - All-Weapon Charge-Ups (Tiger Strike, Flamestrike, Blades of Ice, Electrocute, Cobra Strike) with 15-minute held orb buffs
  - Melee Finishers (Dragon Talon, Dragon Claw, Dragon Tail, Dragon Flight) & non-consuming Whirlwind Capstone (Omnislash)
  - Selective-Consumption Sentry Traps (Shrapnel, Fire, Ice, Lightning, Soul Siphon Sentries) + Caltrops & Bouncing Shuriken
  - Shadow Disciplines (Lethality, Weapon Block, Burst of Speed, Fade, Flow, Cloak of Shadows, Shadow Bind, Mind Blast, Venom, Shadow Master)
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


def apply_assassin_missiles(rows_by_name: Dict[str, Dict[str, str]]) -> None:
    """Apply Assassin Charge-Up Finisher, Sentry Trap, Caltrops, and Shuriken missile updates."""
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




def apply_assassin_skills_and_desc(
    s_headers: List[str],
    s_rows: List[Dict[str, str]],
    by_name: Dict[str, Dict[str, str]],
    d_headers: List[str],
    d_rows: List[Dict[str, str]],
    by_desc: Dict[str, Dict[str, str]],
) -> None:
    """Apply Assassin Charge-Ups, Finishers, Traps, Blades, and Shadow Disciplines to skills.txt and skilldesc.txt."""
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
        cs["calc5"] = "60 + 10*max(0,lvl-1) + 10*max(0,lvl-8) + 15*max(0,lvl-16)"
        cs["*calc5 desc"] = "Held-Orb -Monster Defense Per Hit per Orb (-60 at Lvl 1 -> -410 at Lvl 20; 3 orbs = -180 -> -1230)"
        cs["aurastat2"] = "item_damagetargetac"
        cs["aurastatcalc2"] = "-clc5"
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
        cs_d["desccalca4"] = "clc5"
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
        bs_sk["aurastat1"] = "skill_armor_percent"
        bs_sk["aurastatcalc1"] = f"-(25 + 2 * {cs_m})"
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

        # Hidden skill cast by Whirlwind on every spin tick: slows nearby enemies' movement and attack speed
        # for 3.0s (75 frames) while spinning through them (replacing elemental resistance shred).
        if "Ass Whirl Shred" not in by_name:
            max_sid = max(parse_int(r.get("*Id", "0"), 0) for r in s_rows)
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
            sk_shred["aurastat1"] = "velocitypercent"
            sk_shred["aurastatcalc1"] = "-min(65, 20 + skill('Royal Strike'.lvl)*2)"
            sk_shred["aurastat2"] = "attackrate"
            sk_shred["aurastatcalc2"] = "-min(65, 20 + skill('Royal Strike'.lvl)*2)"
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
        rs_d["desctexta3"] = "Cgslow"
        rs_d["desctextb3"] = ""
        rs_d["desccalca3"] = "min(65, 20 + lvl*2)"
        rs_d["desccalcb3"] = ""
        rs_d["descline4"] = "36"
        rs_d["desctexta4"] = "StrSkillDurationSingular"
        rs_d["desctextb4"] = "StrSkill20"
        rs_d["desccalca4"] = "75"
        rs_d["desccalcb4"] = "25"
        rs_d["descline5"] = ""
        rs_d["desctexta5"] = ""
        rs_d["desctextb5"] = ""
        rs_d["desccalca5"] = ""
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




ASSASSIN_STRING_UPDATES: List[Tuple[int, str, str]] = [
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
            "Does not release orbs\n\nspin through nearby enemies, striking with your weapon\nand any held orb damage while slowing the movement\nand attack speed of enemies in your wake",
        ),
]

ASSASSIN_HD_MISSILE_PAIRS: List[Tuple[str, str]] = [
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
]

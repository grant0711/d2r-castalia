#!/usr/bin/env python3
"""
affixes.py
Step 7: Build itemstatcost.txt, magicprefix.txt, magicsuffix.txt, and item-nameaffixes.json:
- Enable Signed = 1 on core attributes & life/mana/regen in itemstatcost.txt (preserving Save Bits/Save Add)
- Boost Magic-only (rare != 1) apex prefixes and suffixes by ~1.33x
- Enforce maxlevel cutoffs on low-tier Rare-eligible affixes so high-level Rares don't roll Act 1 junk
- Add progressive Quiver & Bolt (bowq, xboq) affixes:
  * Single & All Resistances
  * Fire / Lightning / Cold / Magic Damage progression
  * Increased Attack Speed (10% -> 40%)
  * Piercing Attack, Open Wounds, Deadly Strike, Crushing Blow, Slows Target, Knockback
"""
from typing import Dict, List

from mod_builder.common import (
    read_excel_tsv,
    update_mod_strings_json,
    write_excel_tsv,
)


def _add_itypes(row: Dict[str, str], new_types: List[str]) -> None:
    existing = [row.get(f"itype{i}", "") for i in range(1, 8) if row.get(f"itype{i}", "")]
    for nt in new_types:
        if nt not in existing and len(existing) < 7:
            existing.append(nt)
    for i in range(1, 8):
        row[f"itype{i}"] = existing[i - 1] if i - 1 < len(existing) else ""


def _add_etypes(row: Dict[str, str], new_types: List[str]) -> None:
    existing = [row.get(f"etype{i}", "") for i in range(1, 6) if row.get(f"etype{i}", "")]
    for nt in new_types:
        if nt not in existing and len(existing) < 5:
            existing.append(nt)
    for i in range(1, 6):
        row[f"etype{i}"] = existing[i - 1] if i - 1 < len(existing) else ""


def _scale_mod_val(val_str: str, mult: float) -> str:
    if not val_str:
        return val_str
    try:
        v = int(val_str)
    except ValueError:
        return val_str
    if v <= 0:
        return val_str
    return str(max(1, int(round(v * mult))))


def build_itemstatcost(cfg: dict) -> str:
    headers, rows = read_excel_tsv("itemstatcost.txt")
    signed_stats = {
        "strength", "energy", "dexterity", "vitality",
        "hitpoints", "mana", "stamina",
        "maxhp", "maxmana", "maxstamina", "hpregen", "manarecovery",
    }
    # Normalize vendor transaction cost multipliers (Multiply / 1024 of base cost + Add)
    # so that against our normalized 50,000g Elite base cost (weapons.txt / armor.txt):
    # - Jeweler's Sacred Armor of the Whale (4 sockets + 133 Life) -> ~256,000g
    # - Godly Sacred Armor of the Whale (+266% ED + 133 Life)      -> ~310,000g
    # - Cruel Colossus Blade of Quickness (+400% ED + 40% IAS)     -> ~314,000g
    # - +2 Class Skills / +3 Skill Tab + Staffmods                 -> ~275,000g - 315,000g
    cost_tuning = {
        # Zero out base/op=13 target stats so base Defense/Damage/Durability and %ED op=13 never double-count
        "armorclass": ("0", "0"),
        "mindamage": ("0", "0"),
        "maxdamage": ("0", "0"),
        "secondary_mindamage": ("0", "0"),
        "secondary_maxdamage": ("0", "0"),
        "item_throw_mindamage": ("0", "0"),
        "item_throw_maxdamage": ("0", "0"),
        "maxdurability": ("0", "0"),
        # Core %ED, Sockets, Life, Mana, Resists, Attributes
        "item_numsockets": ("512", "2000"),          # 4 sockets = +102,000g on 50k base
        "maxhp": ("14", "50"),                       # +133 Life = +91,000g on 50k base
        "maxmana": ("14", "50"),                     # +160 Mana = +109,000g on 50k base
        "item_armor_percent": ("9", "35"),           # +266% Defense (Godly) = +117,000g on 50k base
        "item_maxdamage_percent": ("3", "20"),       # Applied alongside item_mindamage_percent (3+3=6 combined)
        "item_mindamage_percent": ("3", "20"),       # +399% Weapon ED (Cruel) = +117,000g on 50k base
        "tohit": ("3", "10"),                        # +598 AR (Weird) = +88,000g; Grandmaster's = +136,000g
        "strength": ("45", "100"),                   # +30 Str = +66,000g
        "dexterity": ("45", "100"),                  # +40 Dex = +88,000g
        "energy": ("45", "100"),                     # +30 Enr = +66,000g
        "vitality": ("45", "100"),
        "fireresist": ("14", "30"),                  # +40% Single Res = +27,000g; +40% All Res (Chromatic) = +109,000g
        "lightresist": ("14", "30"),
        "coldresist": ("14", "30"),
        "poisonresist": ("14", "30"),
        # Speed, Block, FHR, Leech, Regen, DR, MF, GF
        "item_fasterattackrate": ("32", "500"),      # +40% IAS = +63,000g on 50k base
        "item_fastermovevelocity": ("32", "500"),    # +40% FRW = +63,000g
        "item_fastercastrate": ("48", "500"),        # +20% FCR = +47,000g
        "item_fastergethitrate": ("48", "500"),      # +24% FHR = +57,000g
        "toblock": ("48", "100"),                    # +20% Block + 30% FBR (of Deflecting) = +94,000g
        "item_fasterblockrate": ("32", "200"),
        "lifedrainmindam": ("180", "500"),           # 9% Life Steal = +80,000g
        "manadrainmindam": ("180", "500"),           # 9% Mana Steal = +80,000g
        "hpregen": ("80", "250"),                    # +20 Replenish Life = +78,000g
        "normal_damage_reduction": ("55", "150"),    # 33 PDR (of Life Everlasting) = +89,000g
        "magic_damage_reduction": ("160", "200"),    # 8 MDR = +63,000g
        "item_magicbonus": ("40", "300"),            # 47% MF (of Luck) = +92,000g
        "item_goldbonus": ("24", "150"),             # 40% GF (of Wealth) = +47,000g
        "item_attackertakesdamage": ("64", "100"),   # 27 Thorns (of Swords) = +84,000g
        "item_staminadrainpct": ("10", "50"),        # 90% Heal Stamina = +44,000g
        # Elemental, Poison & Magic Damage
        "firemindam": ("6", "10"),                   # Scorching (170-240) = +120,000g
        "firemaxdam": ("6", "15"),
        "lightmindam": ("5", "10"),                  # Shocking (1-480) = +117,000g
        "lightmaxdam": ("5", "15"),
        "magicmindam": ("6", "25"),                  # Astral (210-210) = +123,000g
        "magicmaxdam": ("6", "25"),
        "coldmindam": ("12", "25"),                  # Hibernal (45-140) = +118,000g (replaces vanilla Mult=512/340)
        "coldmaxdam": ("12", "25"),
        "coldlength": ("2", "25"),
        "poisonmindam": ("2", "10"),                 # Pestilent (470) = +115,000g (replaces vanilla Mult=28/34)
        "poisonmaxdam": ("2", "10"),
        "poisonlength": ("1", "0"),
        # Vs Demon / Vs Undead
        "item_demon_tohit": ("2", "10"),             # Celestial (400 AR, 300% Dmg) = +112,000g
        "item_demondamage_percent": ("5", "15"),
        "item_undead_tohit": ("2", "10"),            # Divine (450 AR, 350% Dmg) = +129,000g
        "item_undeaddamage_percent": ("5", "15"),
        # Tactical Suffixes & Binaries
        "item_pierce": ("32", "500"),                # 40% Pierce (of Skewering) = +63,000g (replaces vanilla Mult=2048)
        "item_openwounds": ("32", "300"),            # 40% Open Wounds (of Hemorrhage) = +63,000g
        "item_deadlystrike": ("40", "300"),          # 32% Deadly Strike (of Execution) = +63,000g
        "item_crushingblow": ("48", "300"),          # 25% Crushing Blow (of Crushing) = +59,000g
        "item_slow": ("40", "300"),                  # 30% Slows Target (of Crippling) = +59,000g
        "item_ignoretargetac": ("1024", "1000"),     # Ignore Target's Defense = +51,000g
        "item_halffreezeduration": ("512", "1000"),  # Half Freeze Duration = +26,000g
        "item_cannotbefrozen": ("1024", "5000"),     # Cannot Be Frozen = +55,000g
        "item_replenish_durability": ("128", "100"),
        "item_replenish_quantity": ("128", "100"),
        # Skills, Staffmods, Procs & Charges
        "item_addclassskills": ("1024", "10000"),    # +2 Class Skills = +110,000g on 50k base
        "item_addskill_tab": ("512", "5000"),        # +3 Skill Tab = +80,000g on 50k base
        "item_singleskill": ("96", "100"),           # Staffmods
        "item_nonclassskill": ("128", "100"),
        "item_skillonattack": ("8", "100"),          # Chance-to-Cast Procs (Encode=2)
        "item_skillonhit": ("8", "100"),
        "item_skillongethit": ("8", "100"),
        "item_charged_skill": ("1", "10"),           # Skill Charges (Encode=3)
        "item_maxhp_percent": ("128", "4000"),       # Replaces vanilla's 32,093 flat Add
        "item_maxmana_percent": ("128", "4000"),     # Replaces vanilla's 56,452 flat Add
    }
    for r in rows:
        st = r.get("Stat", "")
        if st in signed_stats:
            r["Signed"] = "1"
        if st in ("hpregen", "manarecovery", "item_healafterkill", "item_damagetomana"):
            r["Send Bits"] = "16"
        if st == "item_slash_damage_percent":
            r["Signed"] = "1"
            r["Send Bits"] = "16"
            r["op"] = "11"
            r["op stat1"] = "mindamage"
            r["op stat2"] = "secondary_mindamage"
            r["op stat3"] = "item_throw_mindamage"
        elif st == "item_crush_damage_percent":
            r["Signed"] = "1"
            r["Send Bits"] = "16"
            r["op"] = "11"
            r["op stat1"] = "maxdamage"
            r["op stat2"] = "secondary_maxdamage"
            r["op stat3"] = "item_throw_maxdamage"
        elif st == "item_absorb_slash":
            # Constant 1 base stat on Fists of Fire (ass_fof_passive) for item_slash_damage (op=2)
            r["Signed"] = "1"
            r["Send Bits"] = "8"
        elif st == "item_slash_damage":
            # Stored inside progressive_fire (aurastat2) so firemindam (+1x) and firemaxdam (+2x) scale per orb and clear on state removal
            r["Signed"] = "1"
            r["Send Bits"] = "16"
            r["op"] = "2"
            r["op param"] = "0"
            r["op base"] = "item_absorb_slash"
            r["op stat1"] = "firemindam"
            r["op stat2"] = "firemaxdam"
            r["op stat3"] = "firemaxdam"
        elif st == "item_absorb_crush":
            # Constant 1 base stat on Blades of Ice (ass_boi_passive) for item_crush_damage (op=2)
            r["Signed"] = "1"
            r["Send Bits"] = "8"
        elif st == "item_crush_damage":
            # Stored inside progressive_cold (aurastat2) so coldmindam (+1x) and coldmaxdam (+2x) scale per orb and clear on state removal
            r["Signed"] = "1"
            r["Send Bits"] = "16"
            r["op"] = "2"
            r["op param"] = "0"
            r["op base"] = "item_absorb_crush"
            r["op stat1"] = "coldmindam"
            r["op stat2"] = "coldmaxdam"
            r["op stat3"] = "coldmaxdam"
        elif st == "item_absorb_thrust":
            # Constant 1 base stat on Claws of Thunder (ass_cot_passive) for item_thrust_damage_percent (op=2)
            r["Signed"] = "1"
            r["Send Bits"] = "8"
        elif st == "item_thrust_damage_percent":
            # Stored inside progressive_lightning (aurastat2) so lightmaxdam (+7*clc3 per orb) scales per orb and clears on state removal
            r["Signed"] = "1"
            r["Send Bits"] = "16"
            r["op"] = "2"
            r["op param"] = "0"
            r["op base"] = "item_absorb_thrust"
            r["op stat1"] = "lightmaxdam"
            r["op stat2"] = ""
            r["op stat3"] = ""
        elif st == "item_pierce":
            # Enable Send Other so trap pets (infernosentry at 3 Tiger Strike charges) sync 33% Pierce to the client
            r["Send Other"] = "1"
        elif st == "item_damagetargetac":
            # Allow -50 / -100 / -150 Monster Defense Per Hit on Cobra Strike (progressive_steal)
            # without overflowing 8-bit signed Send Bits (-128..+127) or getting wiped by weapon-only damagerelated=1
            r["Signed"] = "1"
            r["Send Bits"] = "16"
            r["Save Bits"] = "10"
            r["Save Add"] = "512"
            r["1.09-Save Bits"] = "10"
            r["1.09-Save Add"] = "512"
            r["damagerelated"] = ""
        elif st == "item_attackertakesdamage":
            # Revert Patch 2.4's attackedinmelee back to damagedinmelee so missed and blocked
            # swings do NOT trigger Thorns; only landed melee hits reflect damage.
            r["itemevent1"] = "damagedinmelee"
        elif st == "item_levelreq":
            # Allow negative item_levelreq (-5) on Gem+Rune Crafted items in cubemain.txt
            # to soften D2R's hardcoded Crafted +10 + 3*N_affixes levelreq penalty directly,
            # so Magic & Rare affixes keep their authentic Vanilla levelreq without under-leveling drops.
            r["Signed"] = "1"
            r["Save Bits"] = "8"
            r["Save Add"] = "32"
            r["1.09-Save Bits"] = "8"
            r["1.09-Save Add"] = "32"
        elif st == "item_lightradius":
            # Vanilla Save Bits=4 / Save Add=4 only stores -4..+11, causing -6 Light Radius on
            # Greathelm/Winged Helm/Spired Helm (automagic 321) to underflow to +10/+11!
            # Expand to Save Bits=5 / Save Add=10 (-10..+21) and Send Bits=6.
            r["Signed"] = "1"
            r["Send Bits"] = "6"
            r["Save Bits"] = "5"
            r["Save Add"] = "10"
            r["1.09-Save Bits"] = "5"
            r["1.09-Save Add"] = "10"
        elif st == "skill_armor_percent":
            # Global % Defense modifier (same stat as Shout / Lightning Stance);
            # enables universal Topaz crafting bust (-Total Defense %) on ALL slots including 0-def weapons & jewelry.
            r["Signed"] = "1"
            r["Send Bits"] = "16"
            r["Save Bits"] = "9"
            r["Save Add"] = "100"
            r["1.09-Save Bits"] = "9"
            r["1.09-Save Add"] = "100"
            r["descpriority"] = "74"
            r["descfunc"] = "29"
            r["descstrpos"] = "ModTotalDefPos"
            r["descstrneg"] = "ModTotalDefNeg"
        elif st == "magic_damage_reduction":
            # Support negative Magic Damage Reduced on Amethyst-crafted items (-2..-15)
            # descfunc=29 passes abs(val) to sprintf so negative values display "Elemental/Magic Damage Received +15"
            r["Signed"] = "1"
            r["Save Bits"] = "7"
            r["Save Add"] = "30"
            r["1.09-Save Bits"] = "7"
            r["1.09-Save Add"] = "30"
            r["descfunc"] = "29"
            r["descstrneg"] = "ModStr2tNegative"
        elif st == "item_maxhp_percent":
            # descfunc=29 passes abs(val) to sprintf so Emerald crafting bust displays "Decrease Maximum Life 9%"
            r["descfunc"] = "29"
            r["descstrneg"] = "ModStr2gNegative"
        elif st == "item_maxmana_percent":
            # descfunc=29 passes abs(val) to sprintf so Diamond crafting bust displays "Decrease Maximum Mana 9%"
            r["descfunc"] = "29"
            r["descstrneg"] = "ModStr2hNegative"
        elif st == "skill_channeling_tick":
            # Used by Frenzy (Id 147, aurastat3=skill_channeling_tick) so srvdofunc=9 registers
            # domeleeattack -> 36 (sWarHexOnAttack -> installs bar_stamina_reflex + Param1=3 Shiver Armor)
            # and domeleedamage -> 1 (spawns srvmissilea=grimwardsmallstart -> grimwardsmall pSrvDoFunc=14, Param2=30)
            r["Signed"] = "1"
            r["Send Bits"] = "8"
            r["fCallback"] = "1"
            r["itemevent1"] = "domeleeattack"
            r["itemeventfunc1"] = "36"
            r["itemevent2"] = "domeleedamage"
            r["itemeventfunc2"] = "1"
        elif st == "skill_cooldown":
            r["Signed"] = "1"
            r["Send Bits"] = "8"
            r["fCallback"] = "1"
            r["itemevent1"] = "domeleedamage"
            r["itemeventfunc1"] = "36"
            r["itemevent2"] = "domeleeattack"
            r["itemeventfunc2"] = "1"
        elif st == "skill_conviction":
            # Unused vanilla stat (ID 167): hidden Stamina Fatigue melee combat trigger
            # itemevent1=attackedinmelee (func 21) + itemevent2=domeleeattack (func 20), zero tooltip
            r["Signed"] = "1"
            r["Send Bits"] = "7"
            r["Send Param Bits"] = "16"
            r["fCallback"] = "1"
            r["Encode"] = "2"
            r["Add"] = "0"
            r["Multiply"] = "0"
            r["1.09-Save Bits"] = "21"
            r["1.09-Save Add"] = "0"
            r["Save Bits"] = "7"
            r["Save Add"] = "0"
            r["Save Param Bits"] = "16"
            r["op"] = ""
            r["op stat1"] = ""
            r["itemevent1"] = "attackedinmelee"
            r["itemeventfunc1"] = "21"
            r["itemevent2"] = "domeleeattack"
            r["itemeventfunc2"] = "20"
            r["descfunc"] = ""
            r["descstrpos"] = ""
            r["descstrneg"] = ""
        elif st == "skill_bypass_demons":
            # Unused vanilla stat (ID 104): hidden melee-attack Stun Fatigue stack trigger
            # itemevent1=domeleeattack (func 20), Encode=2, zero tooltip
            r["Signed"] = "1"
            r["Send Bits"] = "7"
            r["Send Param Bits"] = "16"
            r["fCallback"] = "1"
            r["Encode"] = "2"
            r["Add"] = "0"
            r["Multiply"] = "0"
            r["1.09-Save Bits"] = "21"
            r["1.09-Save Add"] = "0"
            r["Save Bits"] = "7"
            r["Save Add"] = "0"
            r["Save Param Bits"] = "16"
            r["itemevent1"] = "domeleeattack"
            r["itemeventfunc1"] = "20"
            r["descfunc"] = ""
            r["descstrpos"] = ""
            r["descstrneg"] = ""
        elif st == "skill_passive_staminapercent":
            # Unused vanilla stat (ID 163): hidden Stun Fatigue reset trigger (on being attacked in melee OR on kill)
            # itemevent1=attackedinmelee (func 21) + itemevent2=kill (func 20), Encode=2, zero tooltip
            r["Signed"] = "1"
            r["Send Bits"] = "7"
            r["Send Param Bits"] = "16"
            r["fCallback"] = "1"
            r["Encode"] = "2"
            r["Add"] = "0"
            r["Multiply"] = "0"
            r["1.09-Save Bits"] = "21"
            r["1.09-Save Add"] = "0"
            r["Save Bits"] = "7"
            r["Save Add"] = "0"
            r["Save Param Bits"] = "16"
            r["op"] = ""
            r["op stat1"] = ""
            r["itemevent1"] = "attackedinmelee"
            r["itemeventfunc1"] = "21"
            r["itemevent2"] = "kill"
            r["itemeventfunc2"] = "20"
            r["descfunc"] = ""
            r["descstrpos"] = ""
            r["descstrneg"] = ""
        elif st == "skill_bypass_beasts":
            # Unused vanilla stat (ID 106): hidden Stamina Fatigue missile combat trigger
            # itemevent1=hitbymissile (func 21) + itemevent2=domissileattack (func 20), zero tooltip
            r["Signed"] = "1"
            r["Send Bits"] = "7"
            r["Send Param Bits"] = "16"
            r["fCallback"] = "1"
            r["Encode"] = "2"
            r["Add"] = "0"
            r["Multiply"] = "0"
            r["1.09-Save Bits"] = "21"
            r["1.09-Save Add"] = "0"
            r["Save Bits"] = "7"
            r["Save Add"] = "0"
            r["Save Param Bits"] = "16"
            r["damagerelated"] = "1"
            r["itemevent1"] = "damagedbymissile"
            r["itemeventfunc1"] = "21"
            r["itemevent2"] = "domissileattack"
            r["itemeventfunc2"] = "20"
            r["descfunc"] = ""
            r["descstrpos"] = ""
            r["descstrneg"] = ""
        if st in cost_tuning:
            mult_val, add_val = cost_tuning[st]
            r["Multiply"] = mult_val
            r["Add"] = add_val
    from mod_builder.sorc import engine as sorc_engine

    sorc_engine.apply_table_patches("itemstatcost.txt", headers, rows)
    return write_excel_tsv("itemstatcost.txt", headers, rows)


def build_magicprefix(cfg: dict) -> str:
    headers, rows = read_excel_tsv("magicprefix.txt")

    scalable_mods = {
        "ac", "ac%", "dmg%", "dmg-min", "dmg-max", "att", "mana",
        "res-all", "res-cold", "res-fire", "res-ltng", "res-pois",
        "fire-min", "fire-max", "ltng-max", "cold-min", "cold-max",
        "pois-min", "pois-max", "mag%",
    }
    # Expansion (version >= 1) core prefix groups for low/mid-tier maxlevel cutoffs
    cutoff_groups = {
        "101", "105", "108", "109", "110", "111", "112", "115",
        "116", "117", "118", "119", "120",
        "137", "138", "139", "140", "142",
    }
    # Expansion (version >= 1) Resistance & Elemental Damage groups for Quivers (bowq, xboq)
    quiver_prefix_groups = {"116", "117", "118", "119", "120", "137", "138", "139", "140"}

    # Reworked/retired skills that must never spawn as charged/oskill/proc magic affixes:
    # - 126..155: Reworked Barbarian skills
    # - 54 / "Teleport": Retired Teleport (planned stance-specific refactor)
    # - 91 / "Lower Resist": Removed from item charges/oskills/procs (no elemental pierce on items)
    # - 37, 38, 40, 43, 46, 50, 52, 58, 60, 61, 63, 65: Reworked Sorceress stances, stance-gated skills, passives & Heaven's Wrath capstone
    retired_affix_skill_refs = {
        "37", "38", "40", "43", "46", "50", "52", "54", "58", "60", "61", "63", "65", "91",
        "Teleport", "Lower Resist", "Warmth", "Charged Bolt", "Frozen Armor", "Telekinesis", "Blaze", "Shiver Armor",
        "Enchant", "Energy Shield", "Chilling Armor", "Fire Mastery", "Lightning Mastery", "Cold Mastery",
    }

    for r in rows:
        # Disable all charged/oskill/proc prefixes referencing reworked Barbarian/Sorceress skills, Teleport, Lower Resist, or pierce-*
        m1c = r.get("mod1code", "").strip()
        if m1c in ("pierce-fire", "pierce-cold", "pierce-ltng", "pierce-pois", "pierce-mag", "pierce-dmg"):
            r["spawnable"] = "0"
            continue
        if m1c in ("charged", "oskill", "skill", "att-skill", "hit-skill", "gethit-skill"):
            m1p = r.get("mod1param", "").strip()
            if m1p in retired_affix_skill_refs or (m1p.isdigit() and 126 <= int(m1p) <= 155):
                r["spawnable"] = "0"
                continue

        if r.get("spawnable") != "1" or r.get("version") == "0":
            continue
        # Fix vanilla D2R typo: 'staff' -> 'staf' so Sorceress +1/+2/+3 Skill Tab prefixes spawn on Staves!
        for _idx in range(1, 8):
            if r.get(f"itype{_idx}", "").strip() == "staff":
                r[f"itype{_idx}"] = "staf"
        grp = r.get("group", "")
        # Strip vs-Demon, vs-Undead, and flat melee weapon elemental damage prefixes from Staves, Orbs & Wands
        if grp in ("123", "142", "137", "138", "139", "140"):
            _add_etypes(r, ["staf", "orb", "wand"])
        # Allow All Resistances (grp 116: Shimmering -> Chromatic) on 2H Staves
        if grp == "116" and r.get("mod1code") == "res-all":
            _add_itypes(r, ["staf"])
        it1 = r.get("itype1", "")
        itypes_all = {r.get(f"itype{i}", "").strip() for i in range(1, 8)}
        is_charm_or_jewel = it1 in ("lcha", "mcha", "scha", "jewl") or "jewl" in itypes_all

        # Ensure all Jewel (jewl) prefixes have level >= 2 so lvl=1 Crafted Jewels ("jew,crf")
        # produced by Unique/Set Distillation roll zero random magic affixes.
        if "jewl" in itypes_all and int(r.get("level") or "1") <= 1:
            r["level"] = "2"

        # 1. Scale Magic-only (rare != "1") numeric apex prefixes by 1.33x
        if r.get("rare") != "1":
            for m_idx in (1, 2, 3):
                mcode = r.get(f"mod{m_idx}code", "")
                if mcode in scalable_mods:
                    r[f"mod{m_idx}min"] = _scale_mod_val(r.get(f"mod{m_idx}min", ""), 1.33)
                    r[f"mod{m_idx}max"] = _scale_mod_val(r.get(f"mod{m_idx}max", ""), 1.33)

        # 2. (Progressive maxlevel cutoffs are applied via _apply_smart_maxlevel_cutoffs at the end of build_magicprefix
        #     so no top-tier Rare affix ever drops off on any item slot!)

        # 3. Tune Group 105 (% ED) & Group 111 (% ED + AR) high-tier weights for exciting endgame Rare/Craft chases
        if r.get("rare") == "1" and not is_charm_or_jewel:
            name = r.get("Name", "")
            if grp == "105":
                if name == "Ferocious":
                    r["frequency"] = "5"
                elif name == "Cruel":
                    r["frequency"] = "3"
                elif name == "Gritty":  # "Grinding" (+Max Dmg/lvl) — keep at w=2 so it doesn't crowd out Ferocious/Cruel
                    r["frequency"] = "2"
            elif grp == "111":
                if name == "Knight's":
                    r["maxlevel"] = "68"
                elif name == "Lord's":
                    r["frequency"] = "3"
                elif name == "King's":
                    r["frequency"] = "3"
                elif name == "Master's":
                    r["frequency"] = "3"
                elif name == "Trump":  # "Fool's" (+Max Dmg/lvl & +AR/lvl) — keep at w=3 alongside Master's/Grandmaster's
                    r["frequency"] = "3"

        # 4. Expose progressive Resistance & Elemental Damage prefixes to Quivers (bowq, xboq)
        if grp in quiver_prefix_groups and not is_charm_or_jewel:
            _add_itypes(r, ["bowq", "xboq"])
            if r.get("Name") in ("Azure", "Crimson", "Tangerine", "Beryl") and r.get("maxlevel") == "4":
                r["level"] = "1"
                r["levelreq"] = "1"

        # 4b. Clear redundant row multiply/add on Group 116 (res-all) so All-Res prefixes are priced
        #     solely via fireresist + lightresist + coldresist + poisonresist in itemstatcost.txt
        if grp == "116":
            r["multiply"] = "0"
            r["add"] = "0"

        # 4c. Bone Caster Armor ('bcas' = 'bhlm' Bone Helms/Masks + 'bshd' Bone Shields) Prefix Isolation:
        #     - Exclude %ED / +Defense (Grp 101), Visionary %AR/lvl (Grp 111), and class Skill Tabs (Grp 125)
        #     - Unlock Vulpine Dmg-to-Mana (Grp 107) and All Resistances (Grp 116) on 'bhlm' ('shld' already has both)
        #     - Unlock full flat Mana progression (Grp 115: Snake's..Bahamut's) and Mana After Kill (Grp 121) on 'bcas'
        if not is_charm_or_jewel:
            if grp == "101" and ({"armo", "helm", "shld"} & itypes_all):
                _add_etypes(r, ["bcas"])
            elif grp == "111" and ("helm" in itypes_all):
                _add_etypes(r, ["bhlm"])
            elif grp == "125" and ({"helm", "shld"} & itypes_all):
                _add_etypes(r, ["bcas"])
            elif grp == "107" and ("shld" in itypes_all):
                _add_itypes(r, ["bhlm"])
            elif grp == "115" and ("circ" in itypes_all):
                if "shld" in itypes_all:
                    _add_itypes(r, ["bhlm"])
                else:
                    _add_itypes(r, ["bcas"])
            elif grp == "116" and ("circ" in itypes_all):
                _add_itypes(r, ["bhlm"])
            elif grp == "121" and ("circ" in itypes_all):
                _add_itypes(r, ["bcas"])

    # 4d. Clone top-tier 31-40% Single Resistance prefixes (Sapphire/Ruby/Amber/Emerald, lvl=25, Grps 117..120)
    #     for 'bcas' (since the original 'circ' rows use all 7 itype columns once bowq/xboq are added)
    bcas_res_clones = []
    for r in rows:
        if (
            r.get("spawnable") == "1"
            and r.get("version") != "0"
            and r.get("group") in ("117", "118", "119", "120")
            and r.get("Name") in ("Sapphire", "Ruby", "Amber", "Emerald")
            and r.get("itype1") == "rod"
        ):
            cr = dict(r)
            cr["itype1"] = "bcas"
            for i in range(2, 8):
                cr[f"itype{i}"] = ""
            bcas_res_clones.append(cr)
    rows.extend(bcas_res_clones)

    # 5. Add Rare-eligible Grandmaster's (Group 111, lvl=69, lreq=61, 151-200% ED + 251-300 AR, freq=3)
    gm = {h: "" for h in headers}
    gm["Name"] = "Grandmaster's"
    gm["version"] = "100"
    gm["spawnable"] = "1"
    gm["rare"] = "1"
    gm["level"] = "69"
    gm["levelreq"] = "61"
    gm["frequency"] = "3"
    gm["group"] = "111"
    gm["mod1code"] = "att"
    gm["mod1min"] = "251"
    gm["mod1max"] = "300"
    gm["mod2code"] = "dmg%"
    gm["mod2min"] = "151"
    gm["mod2max"] = "200"
    gm["transformcolor"] = "dgld"
    gm["itype1"] = "weap"
    gm["etype1"] = "staf"
    gm["etype2"] = "wand"
    gm["etype3"] = "orb"
    gm["multiply"] = "0"
    gm["add"] = "0"
    rows.append(gm)

    # 6. Add Progressive Magic Damage Prefixes (Group 145) for Quivers (bowq, xboq) & Weapons (weap)
    # Non-overlapping maxlevel on Rare tiers and low frequency (2 -> 1 -> 1 -> 1) so it stays a special roll
    magic_dmg_tiers = [
        ("Arcane", "1", "1", "23", "1", "2", "4", "12"),
        ("Mystic", "1", "24", "43", "18", "1", "20", "45"),
        ("Eldritch", "1", "44", "", "33", "1", "50", "105"),
        ("Astral", "", "64", "", "48", "1", "110", "210"),
    ]
    for name, is_rare, lvl, maxlvl, lreq, freq, dmin, dmax in magic_dmg_tiers:
        nr = {h: "" for h in headers}
        nr["Name"] = name
        nr["version"] = "100"
        nr["spawnable"] = "1"
        nr["rare"] = is_rare
        nr["level"] = lvl
        nr["maxlevel"] = maxlvl
        nr["levelreq"] = lreq
        nr["frequency"] = freq
        nr["group"] = "145"
        nr["mod1code"] = "dmg-mag"
        nr["mod1min"] = dmin
        nr["mod1max"] = dmax
        nr["itype1"] = "bowq"
        nr["itype2"] = "xboq"
        nr["itype3"] = "weap"
        nr["etype1"] = "staf"
        nr["etype2"] = "orb"
        nr["etype3"] = "wand"
        nr["multiply"] = "0"
        nr["add"] = "0"
        rows.append(nr)

    # 7b. Narrowly extend 2H Staff-only caster prefixes (Skills, Mana & +% Elemental Skill Damage above 1H Orbs)
    staff_extra_prefixes = [
        # (Name, rare, level, levelreq, freq, grp, mcode, mparam, mmin, mmax)
        ("Seraph's",    "",  "72", "65", "1", "125", "sor",        "",  "3",   "3"),
        ("Hellfire",    "",  "76", "68", "1", "125", "skilltab",   "3", "4",   "4"),
        ("Tempest",     "",  "76", "68", "1", "125", "skilltab",   "4", "4",   "4"),
        ("Frostbound",  "",  "76", "68", "1", "125", "skilltab",   "5", "4",   "4"),
        ("Leviathan's", "1", "65", "55", "2", "115", "mana",       "",  "121", "180"),
        # Staff-only +% Elemental Skill Damage (grp 147, unlocks lvl 32; Rare 8-15%, Magic-only apex 16-25%)
        ("Burning",     "1", "32", "32", "2", "147", "extra-fire", "",  "8",   "15"),
        ("Volcanic",    "",  "55", "48", "1", "147", "extra-fire", "",  "16",  "25"),
        ("Sparking",    "1", "32", "32", "2", "147", "extra-ltng", "",  "8",   "15"),
        ("Powered",     "",  "55", "48", "1", "147", "extra-ltng", "",  "16",  "25"),
        ("Chilling",    "1", "32", "32", "2", "147", "extra-cold", "",  "8",   "15"),
        ("Glacial",     "",  "55", "48", "1", "147", "extra-cold", "",  "16",  "25"),
    ]
    for pname, prare, plvl, plreq, pfreq, pgrp, pmcode, pmparam, pmin, pmax in staff_extra_prefixes:
        sp = {h: "" for h in headers}
        sp["Name"] = pname
        sp["version"] = "100"
        sp["spawnable"] = "1"
        sp["rare"] = prare
        sp["level"] = plvl
        sp["levelreq"] = plreq
        sp["frequency"] = pfreq
        sp["group"] = pgrp
        sp["mod1code"] = pmcode
        sp["mod1param"] = pmparam
        sp["mod1min"] = pmin
        sp["mod1max"] = pmax
        sp["itype1"] = "staf"
        sp["multiply"] = "0"
        sp["add"] = "0"
        rows.append(sp)

    # 7. Add level=1 prefix for Blacksmith's Malus (malu) so Gamble rolls cleanly
    mp = {h: "" for h in headers}
    mp["Name"] = "Forgemaster's"
    mp["version"] = "100"
    mp["spawnable"] = "1"
    mp["rare"] = "1"
    mp["level"] = "1"
    mp["levelreq"] = "0"
    mp["frequency"] = "1"
    mp["group"] = "146"
    mp["mod1code"] = "light"
    mp["mod1min"] = "1"
    mp["mod1max"] = "1"
    mp["itype1"] = "malu"
    mp["multiply"] = "0"
    mp["add"] = "0"
    rows.append(mp)

    _apply_prefix_archetype_weights(headers, rows)
    _apply_smart_maxlevel_cutoffs(rows, cutoff_groups, max_lvl_threshold=32, window=28)

    # Re-level Magic-only apex prefixes buffed by Castalia (+33%) so they sit cleanly
    # above their weaker Rare counterparts, and fill missing Vanilla Lucky charm levelreqs.
    for r in rows:
        if r.get("spawnable") != "1" or r.get("version") == "0":
            continue
        name = r.get("Name", "")
        grp = r.get("group", "")
        if r.get("rare") != "1":
            if name == "Cruel" and grp == "105" and r.get("mod1code") == "dmg%":
                r["level"] = "62"
                r["levelreq"] = "54"
            elif name == "Godly" and grp == "101" and r.get("mod1code") == "ac%":
                r["level"] = "55"
                r["levelreq"] = "47"
            elif name == "Lucky" and grp == "114" and not r.get("levelreq"):
                lvl_i = int(r.get("level") or "0")
                if lvl_i >= 20:
                    r["levelreq"] = str(int(round(lvl_i * 0.75)))
            elif name == "Chromatic" and grp == "116" and r.get("mod1min") != "33":
                # Generic Chromatic (28-40%): strip redundant 'shld' from itypes (Shields use dedicated 33-40% row)
                kept = [r.get(f"itype{i}", "").strip() for i in range(1, 8) if r.get(f"itype{i}", "").strip() and r.get(f"itype{i}", "").strip() != "shld"]
                for i in range(1, 8):
                    r[f"itype{i}"] = kept[i - 1] if i - 1 < len(kept) else ""
        if int(r.get("levelreq") or "0") > 74:
            r["levelreq"] = "74"

    return write_excel_tsv("magicprefix.txt", headers, rows)


def _clone_affix_for_types(
    src: Dict[str, str],
    itypes: List[str],
    freq: str = None,
    etypes: List[str] = None,
    maxlevel: str = None,
) -> Dict[str, str]:
    nr = dict(src)
    for i in range(1, 8):
        nr[f"itype{i}"] = itypes[i - 1] if i <= len(itypes) else ""
    if etypes is not None:
        for i in range(1, 6):
            nr[f"etype{i}"] = etypes[i - 1] if i <= len(etypes) else ""
    if freq is not None:
        nr["frequency"] = freq
    if maxlevel is not None:
        nr["maxlevel"] = maxlevel
    return nr


def _apply_prefix_archetype_weights(headers: List[str], rows: List[Dict[str, str]]) -> None:
    """Apply weapon & armor family probability biasing, shield resistance tier buffs, and cleanups."""
    extra_rows: List[Dict[str, str]] = []

    for r in rows:
        if r.get("spawnable") != "1" or r.get("version") == "0":
            continue
        grp = r.get("group", "")
        it1 = r.get("itype1", "").strip()
        itypes_all = {r.get(f"itype{i}", "").strip() for i in range(1, 8) if r.get(f"itype{i}", "").strip()}
        if it1 in ("lcha", "mcha", "scha", "jewl") or "jewl" in itypes_all:
            continue
        mod1 = r.get("mod1code", "")
        name = r.get("Name", "")
        freq_i = int(r.get("frequency") or "1")

        # 1. Strip obsolete stack size (grp 141) from auto-replenishing Throwing Weapons
        if grp == "141" and ({"thro", "jave", "taxe", "tkni"} & itypes_all):
            r["spawnable"] = "0"
            continue

        # 2. Strip Dmg vs Demon / Undead from Wands (matching Staves & Orbs)
        if grp in ("123", "142"):
            _add_etypes(r, ["wand"])

        # 3. Shield Resistance Tier Buffs (exclude shld from generic armo/shld res rows; emit dedicated buffed shld rows below)
        if grp in ("116", "117", "118", "119", "120") and ({"armo", "shld"} & itypes_all):
            _add_etypes(r, ["shld"])

        # 4. Weapon %ED (grp 105, Rare high tiers): boost Blunt (club/mace/hamm), Axes, Polearms, Crossbows; soften Daggers
        if grp == "105" and mod1 == "dmg%" and "weap" in itypes_all and r.get("rare") == "1" and int(r.get("level") or "0") >= 30:
            # Base row already has etype1..3 = wand/staf/orb; only 2 etype slots left, so boost favored types cleanly
            _add_etypes(r, ["knif"])
            extra_rows.append(_clone_affix_for_types(r, ["blun", "axe", "pole", "xbow"], freq="3", etypes=["staf", "wand", "orb"]))
            extra_rows.append(_clone_affix_for_types(r, ["knif"], freq=str(max(1, freq_i - 2)), etypes=[]))

        # 5. Weapon %ED+AR (grp 111, Rare high tiers): boost Swords & Spears; soften Blunt & Axes
        if grp == "111" and mod1 == "att" and "weap" in itypes_all and r.get("rare") == "1" and int(r.get("level") or "0") >= 30:
            _add_etypes(r, ["blun", "axe"])
            extra_rows.append(_clone_affix_for_types(r, ["swor", "spea"], freq="2", etypes=[]))
            extra_rows.append(_clone_affix_for_types(r, ["blun", "axe"], freq=str(max(1, freq_i - 1)), etypes=["staf", "wand", "orb"]))

        # 6. Dmg vs Undead (grp 142): 3x weight on Blunt & Scepters
        if grp == "142" and "weap" in itypes_all and int(r.get("level") or "0") >= 15:
            _add_etypes(r, ["blun", "scep"])
            extra_rows.append(_clone_affix_for_types(r, ["blun", "scep"], freq=str(min(9, max(3, freq_i * 3))), etypes=["staf", "wand", "orb"]))

        # 7. Dmg vs Demons (grp 123): boost Axes & Crossbows
        if grp == "123" and "weap" in itypes_all and int(r.get("level") or "0") >= 20:
            _add_etypes(r, ["axe", "xbow"])
            extra_rows.append(_clone_affix_for_types(r, ["axe", "xbow"], freq=str(min(9, freq_i + 2)), etypes=[]))

        # 8. Poison Dmg (grp 140): 3x weight on Daggers & Throwing Knives
        if grp == "140" and "weap" in itypes_all and int(r.get("level") or "0") >= 15:
            _add_etypes(r, ["knif", "tkni"])
            extra_rows.append(_clone_affix_for_types(r, ["knif", "tkni"], freq=str(min(9, max(3, freq_i * 3))), etypes=[]))

        # 9. Elemental Dmg (grps 137, 138, 139): boost Bows, Claws, Bow Quivers (bowq); soften Crossbows (xbow)
        if grp in ("137", "138", "139") and "weap" in itypes_all and int(r.get("level") or "0") >= 25:
            _add_etypes(r, ["bow", "h2h", "xbow"])
            extra_rows.append(_clone_affix_for_types(r, ["bow", "h2h", "bowq"], freq=str(min(9, freq_i + 2)), etypes=[]))
            extra_rows.append(_clone_affix_for_types(r, ["xbow"], freq="1", etypes=[]))

        # 10. Hit Causes Monster to Flee (howl, grp 113): slash on Claws & Scepters
        if grp == "113" and ({"weap", "mele", "blun", "h2h", "scep"} & itypes_all):
            _add_etypes(r, ["h2h", "scep"])

        # 11. Armor %EDef (grp 101, ac%, Rare high tiers): cleanly partition armo so Light (freq=1), Med (freq=2), Heavy (freq=4)
        #     never overflow etype1..5! Base row covers non-weight-split slots (helm, belt, circ, head) at balanced freq.
        #     Caster Body Armor ('ctor': Light/Mage/Archon Plate) gets low freq=1 alongside Light armor.
        if grp == "101" and mod1 == "ac%" and "armo" in itypes_all and r.get("rare") == "1" and int(r.get("level") or "0") >= 25:
            for idx, it in enumerate(["helm", "belt", "circ", "head"], start=1):
                r[f"itype{idx}"] = it
            for idx in range(5, 8):
                r[f"itype{idx}"] = ""
            r["frequency"] = str(min(3, freq_i))
            extra_rows.append(_clone_affix_for_types(r, ["ltor", "ctor", "lshi", "lash", "lglv", "lbot"], freq="1", etypes=["bcas"]))
            extra_rows.append(_clone_affix_for_types(r, ["mtor", "mshi", "mash", "mglv", "mbot"], freq="2", etypes=["bcas"]))
            extra_rows.append(_clone_affix_for_types(r, ["htor", "hshi", "hash", "hglv", "hbot"], freq="4", etypes=["bcas"]))

        # 12. Flat Mana (grp 115, high tiers): boost on Light/Caster Armor, Light Shields, Wands, Necro Heads
        if grp == "115" and mod1 == "mana" and r.get("rare") == "1" and int(r.get("level") or "0") >= 25:
            if "wand" in itypes_all or "rod" in itypes_all:
                r["frequency"] = str(min(6, freq_i + 2))
            if "circ" in itypes_all or "armo" in itypes_all:
                extra_rows.append(_clone_affix_for_types(r, ["ltor", "ctor", "lshi", "lash", "head"], freq="3", etypes=[]))

        # 12b. Dedicated Caster Body Armor ('ctor': Light/Mage/Archon Plate) prefixes:
        #      Unlock All Res (grp 116), MAEK (grp 121), and Vulpine Dmg-to-Mana (grp 107)
        if grp == "116" and mod1 == "res-all" and "circ" in itypes_all:
            extra_rows.append(_clone_affix_for_types(r, ["ctor"], freq=str(max(2, freq_i)), etypes=[]))
        if grp == "121" and "circ" in itypes_all:
            extra_rows.append(_clone_affix_for_types(r, ["ctor"], freq=str(freq_i), etypes=[]))
        if grp == "107" and "shld" in itypes_all:
            extra_rows.append(_clone_affix_for_types(r, ["ctor"], freq=str(freq_i), etypes=[]))

        # 13. Modest All Res (Shimmering 5-10 / Rainbow 8-11) on Medium Body Armor (mtor)
        if grp == "116" and mod1 == "res-all" and name in ("Shimmering", "Rainbow") and "circ" in itypes_all:
            extra_rows.append(_clone_affix_for_types(r, ["mtor"], freq="2", etypes=[], maxlevel=""))

        # 14. Rebalance Circlet +Skill prefix saturation slightly so Res/Mana/Sockets also roll
        if grp == "125" and "circ" in itypes_all and freq_i >= 2:
            r["frequency"] = str(max(1, freq_i - 1))

        # 15. Crossbow Quivers (xboq): enable %ED + AR flavor (modest high-tier prefix)
        if grp == "111" and name in ("Lord's", "King's", "Master's") and "weap" in itypes_all:
            extra_rows.append(_clone_affix_for_types(r, ["xboq"], freq="2", etypes=[]))

    # 16. Append Buffed Shield Resistance Prefixes (all 'shld' = shie, ashd, head)
    # Single-Element Resistances: 8-15 / 16-25 / 26-37 / 38-50% (Rare+Magic) + 51-65% (5th Magic-only apex tier)
    shld_single_res = [
        ("117", "res-cold", [
            ("Azure",    "1", "5",  "33", "3",  "3", "8",  "15"),
            ("Lapis",    "1", "12", "40", "9",  "4", "16", "25"),
            ("Cobalt",   "1", "18", "46", "13", "4", "26", "37"),
            ("Sapphire", "1", "25", "",   "18", "4", "38", "50"),
            ("Cerulean", "",  "45", "",   "36", "2", "51", "65"),
        ]),
        ("118", "res-fire", [
            ("Crimson",  "1", "5",  "33", "3",  "3", "8",  "15"),
            ("Russet",   "1", "12", "40", "9",  "4", "16", "25"),
            ("Garnet",   "1", "18", "46", "13", "4", "26", "37"),
            ("Ruby",     "1", "25", "",   "18", "4", "38", "50"),
            ("Infernal", "",  "45", "",   "36", "2", "51", "65"),
        ]),
        ("119", "res-ltng", [
            ("Tangerine", "1", "5",  "33", "3",  "3", "8",  "15"),
            ("Ocher",     "1", "12", "40", "9",  "4", "16", "25"),
            ("Coral",     "1", "18", "46", "13", "4", "26", "37"),
            ("Amber",     "1", "25", "",   "18", "4", "38", "50"),
            ("Voltaic",   "",  "45", "",   "36", "2", "51", "65"),
        ]),
        ("120", "res-pois", [
            ("Beryl",    "1", "5",  "33", "3",  "3", "8",  "15"),
            ("Viridian", "1", "12", "40", "9",  "4", "16", "25"),
            ("Jade",     "1", "18", "46", "13", "4", "26", "37"),
            ("Emerald",  "1", "25", "",   "18", "4", "38", "50"),
            ("Verdant",  "",  "45", "",   "36", "2", "51", "65"),
        ]),
    ]
    for grp_id, mcode, tiers in shld_single_res:
        for tname, trare, tlvl, tmaxl, tlreq, tfreq, tmin, tmax in tiers:
            sr = {h: "" for h in headers}
            sr["Name"] = tname
            sr["version"] = "100"
            sr["spawnable"] = "1"
            sr["rare"] = trare
            sr["level"] = tlvl
            sr["maxlevel"] = tmaxl
            sr["levelreq"] = tlreq
            sr["frequency"] = tfreq
            sr["group"] = grp_id
            sr["mod1code"] = mcode
            sr["mod1min"] = tmin
            sr["mod1max"] = tmax
            sr["itype1"] = "shld"
            sr["multiply"] = "0"
            sr["add"] = "0"
            extra_rows.append(sr)

    # All Resistances on Shields ('shld'): 6-10 / 11-17 / 18-24 / 25-32 / 33-40% (magic-only top tier 40%)
    shld_all_res = [
        ("Shimmering",    "1", "6",  "34", "4",  "3", "6",  "10"),
        ("Rainbow",       "1", "18", "46", "13", "3", "11", "17"),
        ("Scintillating", "1", "28", "56", "21", "3", "18", "24"),
        ("Prismatic",     "1", "39", "",   "31", "4", "25", "32"),
        ("Chromatic",     "",  "50", "",   "42", "2", "33", "40"),
    ]
    for tname, trare, tlvl, tmaxl, tlreq, tfreq, tmin, tmax in shld_all_res:
        ar = {h: "" for h in headers}
        ar["Name"] = tname
        ar["version"] = "100"
        ar["spawnable"] = "1"
        ar["rare"] = trare
        ar["level"] = tlvl
        ar["maxlevel"] = tmaxl
        ar["levelreq"] = tlreq
        ar["frequency"] = tfreq
        ar["group"] = "116"
        ar["mod1code"] = "res-all"
        ar["mod1min"] = tmin
        ar["mod1max"] = tmax
        ar["itype1"] = "shld"
        ar["multiply"] = "0"
        ar["add"] = "0"
        extra_rows.append(ar)

    # 17. Append NM/Hell Rare & Magic-only Apex Stamina (grp 109) and Stamina Regen (grp 108) prefixes
    stamina_extra_prefixes = [
        # (Name, rare, lvl, lreq, freq, grp, mod1code, min, max, itypes)
        ("Enduring",   "1", "34", "26", "3", "109", "stam",       "31", "50",  ["boot", "belt", "ltor", "mtor", "ring", "amul", "circ"]),
        ("Relentless", "1", "52", "44", "3", "109", "stam",       "51", "75",  ["boot", "belt", "ltor", "mtor"]),
        ("Boundless",  "",  "64", "56", "2", "109", "stam",       "76", "110", ["boot", "belt", "ltor", "mtor"]),
        ("Untiring",   "1", "36", "28", "3", "108", "regen-stam", "65", "85",  ["boot", "belt", "ltor", "mtor"]),
        ("Ceaseless",  "",  "54", "46", "2", "108", "regen-stam", "90", "125", ["boot", "belt", "ltor", "mtor"]),
    ]
    for tname, trare, tlvl, tlreq, tfreq, grp_id, mcode, tmin, tmax, its in stamina_extra_prefixes:
        sr = {h: "" for h in headers}
        sr["Name"] = tname
        sr["version"] = "100"
        sr["spawnable"] = "1"
        sr["rare"] = trare
        sr["level"] = tlvl
        sr["levelreq"] = tlreq
        sr["frequency"] = tfreq
        sr["group"] = grp_id
        sr["mod1code"] = mcode
        sr["mod1min"] = tmin
        sr["mod1max"] = tmax
        for idx, it in enumerate(its[:7], start=1):
            sr[f"itype{idx}"] = it
        sr["multiply"] = "0"
        sr["add"] = "0"
        extra_rows.append(sr)

    rows.extend(extra_rows)


def build_magicsuffix(cfg: dict) -> str:
    headers, rows = read_excel_tsv("magicsuffix.txt")

    scalable_mods = {
        "red-dmg", "red-mag", "thorns", "dmg-min", "dmg-max",
        "dex", "str", "hp", "mana", "lifesteal", "manasteal",
        "mag%", "regen",
    }
    # Expansion (version >= 1) core suffix groups for low/mid-tier maxlevel cutoffs
    cutoff_groups = {
        "1", "2", "7", "10", "12", "13", "14", "15", "16",
        "17", "19", "21", "22", "23", "26", "27", "28", "33",
    }
    # Expansion (version >= 1) Quiver suffix groups:
    # 7 = IAS (swing1..3), 10 = Cold Dmg, 12 = Fire Dmg, 13 = Ltng Dmg, 16 = Pois Dmg (NO Knockback on Quivers!)
    quiver_suffix_groups = {"7", "10", "12", "13", "16"}

    # Reworked/retired skills that must never spawn as charged/oskill/proc magic affixes:
    # - 126..155: Reworked Barbarian skills
    # - 54 / "Teleport": Retired Teleport (planned stance-specific refactor)
    # - 91 / "Lower Resist": Removed from item charges/oskills/procs (no elemental pierce on items)
    # - 37, 38, 40, 43, 46, 50, 52, 58, 60, 61, 63, 65: Reworked Sorceress stances, stance-gated skills, passives & Heaven's Wrath capstone
    retired_affix_skill_refs = {
        "37", "38", "40", "43", "46", "50", "52", "54", "58", "60", "61", "63", "65", "91",
        "Teleport", "Lower Resist", "Warmth", "Charged Bolt", "Frozen Armor", "Telekinesis", "Blaze", "Shiver Armor",
        "Enchant", "Energy Shield", "Chilling Armor", "Fire Mastery", "Lightning Mastery", "Cold Mastery",
    }

    for r in rows:
        # Disable all charged/oskill/proc prefixes referencing reworked Barbarian/Sorceress skills, Teleport, Lower Resist, or pierce-*
        m1c = r.get("mod1code", "").strip()
        if m1c in ("pierce-fire", "pierce-cold", "pierce-ltng", "pierce-pois", "pierce-mag", "pierce-dmg"):
            r["spawnable"] = "0"
            continue
        if m1c in ("charged", "oskill", "skill", "att-skill", "hit-skill", "gethit-skill"):
            m1p = r.get("mod1param", "").strip()
            if m1p in retired_affix_skill_refs or (m1p.isdigit() and 126 <= int(m1p) <= 155):
                r["spawnable"] = "0"
                continue

        if r.get("spawnable") != "1" or r.get("version") == "0":
            continue
        grp = r.get("group", "")
        # Strip dead melee suffixes (Ignore Target AC, IAS, flat melee elem/pois dmg, Knockback, Light+AR, LL, ML)
        # and melee-triggered Chance-to-Cast on Attack / Striking procs (att-skill, hit-skill) plus melee-only
        # charged skills (Sacrifice/Zeal) from Staves, Orbs & Wands so caster sticks roll clean caster affixes.
        if grp in ("4", "7", "10", "12", "13", "16", "24", "25", "27", "28") or m1c in ("att-skill", "hit-skill"):
            _add_etypes(r, ["staf", "orb", "wand"])
        if m1c == "charged" and r.get("itype1") == "mele":
            _add_etypes(r, ["staf", "orb", "wand"])
        it1 = r.get("itype1", "")
        itypes_all = {r.get(f"itype{i}", "").strip() for i in range(1, 8)}
        is_charm_or_jewel = it1 in ("lcha", "mcha", "scha", "jewl") or "jewl" in itypes_all
        # Allow +Life (grp 26, hp — tors progression up to of the Whale) and Faster Hit Recovery
        # (grp 18, balance1..3 — 10/17/24% FHR) on 2H Staves (compensating for no Shield)
        if not is_charm_or_jewel and grp == "26" and r.get("mod1code") == "hp" and ("tors" in itypes_all):
            _add_itypes(r, ["staf"])
        if not is_charm_or_jewel and grp == "18" and r.get("mod1code", "").startswith("balance") and ("armo" in itypes_all or "tors" in itypes_all):
            _add_itypes(r, ["staf"])

        # Ensure all Jewel (jewl) prefixes have level >= 2 so lvl=1 Crafted Jewels ("jew,crf")
        # produced by Unique/Set Distillation roll zero random magic affixes.
        if "jewl" in itypes_all and int(r.get("level") or "1") <= 1:
            r["level"] = "2"

        # 1. Scale Magic-only (rare != "1") numeric apex suffixes by 1.33x
        if r.get("rare") != "1":
            for m_idx in (1, 2, 3):
                mcode = r.get(f"mod{m_idx}code", "")
                if mcode in scalable_mods:
                    r[f"mod{m_idx}min"] = _scale_mod_val(r.get(f"mod{m_idx}min", ""), 1.33)
                    r[f"mod{m_idx}max"] = _scale_mod_val(r.get(f"mod{m_idx}max", ""), 1.33)

        # 1b. Compress % Extra Gold (gold%) suffixes by 0.50x so Gold Find cannot trivialize late-game economy
        for m_idx in (1, 2, 3):
            if r.get(f"mod{m_idx}code", "") == "gold%":
                r[f"mod{m_idx}min"] = _scale_mod_val(r.get(f"mod{m_idx}min", ""), 0.50)
                r[f"mod{m_idx}max"] = _scale_mod_val(r.get(f"mod{m_idx}max", ""), 0.50)

        # 2. (Progressive maxlevel cutoffs are applied via _apply_smart_maxlevel_cutoffs at the end of build_magicsuffix
        #     so no top-tier Rare affix ever drops off on any item slot!)

        # 3. Expose primary weapon IAS (group 7), Elemental Damage (10, 12, 13, 16), and Knockback (24) to Quivers
        if grp in quiver_suffix_groups and it1 in ("weap", "mele"):
            _add_itypes(r, ["bowq", "xboq"])
            if r.get("Name") in ("of Readiness", "of Frost", "of Flame", "of Shock", "of Blight") and int(r.get("level") or "99") <= 5:
                r["level"] = "1"
                r["levelreq"] = "1"

        # 3b. Price flat +Max Damage (Group 14) and +Min Damage (Group 15) suffixes directly via row
        #     multiply/add so mindamage/maxdamage/secondary_maxdamage/item_throw_maxdamage can remain 0
        #     in itemstatcost.txt without base weapon damage or %ED (op=13) double-counting
        if not is_charm_or_jewel and grp in ("14", "15"):
            mx_val = int(r.get("mod1max") or "1")
            if grp == "14":
                r["multiply"] = str(mx_val * 20)
                r["add"] = str(mx_val * 25)
            else:
                r["multiply"] = str(mx_val * 50)
                r["add"] = str(mx_val * 50)

        # 3c. Bone Caster Armor ('bcas' = 'bhlm' Bone Helms/Masks + 'bshd' Bone Shields) Suffix Isolation:
        #     - Exclude Thorns (Grp 6), +Max Damage (Grp 14), and +Strength (Grp 31) from Bone Shields ('bshd')
        #     - Unlock Faster Cast Rate (Grp 9: of the Apprentice 10% FCR, of the Magus 20% FCR) on 'bcas'
        #     - Unlock full Energy progression (Grp 23: of Energy..of Wizardry..of Enlightenment) on 'bcas'
        #     - Unlock Magic Damage Reduced (Grp 2: of Warding..of Negation) on 'bhlm' ('shld' already has it)
        #     - Unlock full Replenish Life progression (Grp 19: of Regeneration..of Revivification) on 'bcas'
        if not is_charm_or_jewel:
            if grp in ("6", "14", "31") and ("shld" in itypes_all):
                _add_etypes(r, ["bshd"])
            elif grp == "9" and ("circ" in itypes_all):
                _add_itypes(r, ["bcas"])
            elif grp == "23":
                if "helm" in itypes_all:
                    _add_etypes(r, ["bhlm"])
                elif "circ" in itypes_all:
                    _add_itypes(r, ["bcas"])
            elif grp == "2" and ("shld" in itypes_all):
                _add_itypes(r, ["bhlm"])
            elif grp == "19":
                if "shld" in itypes_all:
                    _add_etypes(r, ["bshd"])
                elif "circ" in itypes_all:
                    _add_itypes(r, ["bcas"])

    # 4. Tactical suffix groups 60..64 (Pierce, Open Wounds, Deadly Strike, Crushing Blow, Slows Target)
    # are intentionally omitted from magic/rare rolls so they stay exclusive to Uniques, Sets, Runes, and Crafts!

    # 4b. Narrowly extend 2H Staff-only FCR suffixes (30% Rare-eligible, 40% Magic-only vs 1H Orb max 20%)
    for sname, srare, slvl, slreq, sfreq, sval in (
        ("of the Archmage",  "1", "52", "44", "2", "30"),
        ("of the Ascendant", "",  "68", "60", "1", "40"),
    ):
        sf = {h: "" for h in headers}
        sf["Name"] = sname
        sf["version"] = "100"
        sf["spawnable"] = "1"
        sf["rare"] = srare
        sf["level"] = slvl
        sf["levelreq"] = slreq
        sf["frequency"] = sfreq
        sf["group"] = "9"
        sf["mod1code"] = "cast1"
        sf["mod1min"] = sval
        sf["mod1max"] = sval
        sf["itype1"] = "staf"
        sf["multiply"] = "0"
        sf["add"] = "0"
        rows.append(sf)

    # 5. Add level=1 suffix for Blacksmith's Malus (malu) so Gamble rolls cleanly
    ms = {h: "" for h in headers}
    ms["Name"] = "of Socketing"
    ms["version"] = "100"
    ms["spawnable"] = "1"
    ms["rare"] = "1"
    ms["level"] = "1"
    ms["levelreq"] = "0"
    ms["frequency"] = "1"
    ms["group"] = "65"
    ms["mod1code"] = "light"
    ms["mod1min"] = "1"
    ms["mod1max"] = "1"
    ms["itype1"] = "malu"
    ms["multiply"] = "0"
    ms["add"] = "0"
    rows.append(ms)

    _apply_suffix_archetype_weights(headers, rows)
    _apply_smart_maxlevel_cutoffs(rows, cutoff_groups, max_lvl_threshold=28, window=26)
    _stabilize_block_suffixes(headers, rows, target_pct=0.15)
    _rebalance_charged_suffixes(rows)

    # Re-level Magic-only apex suffixes buffed by Castalia (+33%) so they don't overpower Act 4 Norm / Act 1 NM
    # and cap all spawnable affix levelreqs at 74 (so 4-affix Crafted items with -5 offset cap at 91).
    for r in rows:
        if r.get("spawnable") != "1" or r.get("version") == "0":
            continue
        if r.get("rare") != "1":
            name = r.get("Name", "")
            grp = r.get("group", "")
            if name == "of Butchery" and grp == "14" and r.get("mod1code") == "dmg-max":
                r["level"] = "42"
                r["levelreq"] = "34"
            elif name == "of Evisceration" and grp == "14" and r.get("mod1code") == "dmg-max":
                r["level"] = "55"
                r["levelreq"] = "47"
            elif name == "of the Whale" and grp == "26" and r.get("mod1code") == "hp":
                r["level"] = "55"
                r["levelreq"] = "47"
            elif name == "of Life Everlasting" and grp == "1" and r.get("mod1code") == "red-dmg":
                r["level"] = "52"
                r["levelreq"] = "44"
        if int(r.get("levelreq") or "0") > 74:
            r["levelreq"] = "74"

    return write_excel_tsv("magicsuffix.txt", headers, rows)


def _apply_suffix_archetype_weights(headers: List[str], rows: List[Dict[str, str]]) -> None:
    """Apply weapon & armor family suffix probability biasing, Light/Med/Heavy splits, and cleanups."""
    extra_rows: List[Dict[str, str]] = []

    for r in rows:
        if r.get("spawnable") != "1" or r.get("version") == "0":
            continue
        grp = r.get("group", "")
        it1 = r.get("itype1", "").strip()
        itypes_all = {r.get(f"itype{i}", "").strip() for i in range(1, 8) if r.get(f"itype{i}", "").strip()}
        if it1 in ("lcha", "mcha", "scha", "jewl") or "jewl" in itypes_all:
            continue
        mod1 = r.get("mod1code", "")
        name = r.get("Name", "")
        freq_i = int(r.get("frequency") or "1")

        # 1. Strip dead melee suffixes from Wands (LL, ML, KB, ITD)
        if grp in ("27", "28", "24", "4"):
            _add_etypes(r, ["wand"])

        # 2. Strip obsolete Replenish Quantity (indestruct, grp 39) from auto-replenishing Throwing Weapons
        if grp == "39" and ({"thro", "jave", "taxe", "tkni"} & itypes_all):
            r["spawnable"] = "0"
            continue

        # 3. Weapon & Glove IAS (grp 7):
        #    - Hammers & Maces capped at 20% (excluded from Swiftness 30% & Quickness 40%), low weight (freq=2)
        #    - Scepters capped at 30% (excluded from Quickness 40%)
        #    - Bows unlock Swiftness (30%); Crossbows capped at Alacrity (20%) with low weight (freq=1)
        #    - Daggers, Swords, Claws boosted; Crossbow Quivers (xboq) lowered vs Bow Quivers (bowq)
        #    - Gloves split: Light (lglv) boosted, Medium (mglv) balanced, Heavy (hglv) lowered
        if grp == "7":
            if name == "of Alacrity" and "weap" in itypes_all:
                # Base row keeps remaining weap/bowq; replace etypes cleanly within 5 slots
                r["itype1"], r["itype2"], r["itype3"] = "mele", "", ""
                for idx in range(1, 6):
                    r[f"etype{idx}"] = ""
                _add_etypes(r, ["staf", "orb", "wand", "hamm", "mace"])
                extra_rows.append(_clone_affix_for_types(r, ["hamm", "mace"], freq="2", etypes=[], maxlevel=""))
                extra_rows.append(_clone_affix_for_types(r, ["xbow"], freq="1", etypes=[], maxlevel=""))
                extra_rows.append(_clone_affix_for_types(r, ["bow"], freq="4", etypes=[], maxlevel=""))
                extra_rows.append(_clone_affix_for_types(r, ["bowq"], freq="2", etypes=[], maxlevel=""))
                extra_rows.append(_clone_affix_for_types(r, ["xboq"], freq="1", etypes=[], maxlevel=""))
            elif name == "of Swiftness" and "mele" in itypes_all:
                # Cap Hammers/Maces at 20%; keep xboq lower; unlock 30% on Bows; boost fast blades modestly
                r["itype1"], r["itype2"], r["itype3"] = "mele", "", ""
                for idx in range(1, 6):
                    r[f"etype{idx}"] = ""
                _add_etypes(r, ["staf", "orb", "wand", "hamm", "mace"])
                extra_rows.append(_clone_affix_for_types(r, ["knif", "swor", "h2h", "bow"], freq="2", etypes=[]))
                extra_rows.append(_clone_affix_for_types(r, ["bowq"], freq="2", etypes=[]))
                extra_rows.append(_clone_affix_for_types(r, ["xboq"], freq="1", etypes=[]))
            elif name == "of Quickness" and "mele" in itypes_all:
                # Cap Hammers/Maces at 20%, Scepters at 30%; keep xboq lower; boost fast blades modestly
                r["itype1"], r["itype2"], r["itype3"] = "mele", "", ""
                for idx in range(1, 6):
                    r[f"etype{idx}"] = ""
                _add_etypes(r, ["rod", "orb", "hamm", "mace"])
                extra_rows.append(_clone_affix_for_types(r, ["knif", "swor", "h2h"], freq="2", etypes=[]))
                extra_rows.append(_clone_affix_for_types(r, ["bowq"], freq="2", etypes=[]))
                extra_rows.append(_clone_affix_for_types(r, ["xboq"], freq="1", etypes=[]))
            elif "glov" in itypes_all:
                r["itype1"] = "mglv"
                for idx in range(2, 8):
                    r[f"itype{idx}"] = ""
                extra_rows.append(_clone_affix_for_types(r, ["lglv"], freq=str(min(9, freq_i + 3)), etypes=[]))
                extra_rows.append(_clone_affix_for_types(r, ["hglv"], freq="1", etypes=[]))

        # 4. Knockback (grp 24):
        #    - Strip from Daggers, Claws, and Quivers (already removed from quiver_suffix_groups)
        #    - Boost 2x on Blunt (club/mace/hamm); enable on Crossbows (xbow); lower on Swords & Spears
        if grp == "24" and ({"mele", "blun", "weap"} & itypes_all):
            _add_etypes(r, ["knif", "h2h", "bowq", "xboq", "swor", "spea", "blun"])
            extra_rows.append(_clone_affix_for_types(r, ["blun", "xbow"], freq=str(min(9, max(4, freq_i * 2))), etypes=["staf", "wand", "orb"]))
            extra_rows.append(_clone_affix_for_types(r, ["swor", "spea"], freq="1", etypes=[]))

        # 5. FCR (grp 9):
        #    - Unlock 10% FCR (of the Apprentice) on Light Gloves (lglv ONLY!) and Necromancer Heads (head)
        #    - Unlock 10% & 20% FCR (Apprentice & Magus) on Caster Body Armor ('ctor': Light/Mage/Archon Plate)
        #    - Boost FCR on Wands, Scepters, Circlets
        if grp == "9" and mod1 == "cast1":
            if name == "of the Apprentice" and "circ" in itypes_all:
                extra_rows.append(_clone_affix_for_types(r, ["lglv", "head", "ctor"], freq="4", etypes=[]))
            elif name == "of the Magus" and "circ" in itypes_all:
                extra_rows.append(_clone_affix_for_types(r, ["ctor"], freq="3", etypes=[]))
            if "wand" in itypes_all or "scep" in itypes_all or "circ" in itypes_all:
                r["frequency"] = str(min(9, freq_i + 2))

        # 5b. Dedicated Caster Body Armor ('ctor') suffixes:
        #     Unlock Energy (grp 23) & MDR (grp 2); exclude Thorns (grp 6), PDR (grp 1), and +Str (grp 31)
        if grp == "23" and "circ" in itypes_all:
            extra_rows.append(_clone_affix_for_types(r, ["ctor"], freq=str(freq_i), etypes=[]))
        if grp == "2" and "shld" in itypes_all:
            extra_rows.append(_clone_affix_for_types(r, ["ctor"], freq=str(freq_i), etypes=[]))
        if grp in ("6", "1", "31") and ({"armo", "tors"} & itypes_all):
            _add_etypes(r, ["ctor"])

        # 6. Weapon Min/Max Damage (grp 14, 15, 16): boost Axes (Max), Blunt & Crossbows & xboq (Min/Max), Spears (Min)
        if grp in ("14", "15", "16") and "weap" in itypes_all and r.get("rare") == "1" and int(r.get("level") or "0") >= 20:
            extra_rows.append(_clone_affix_for_types(r, ["blun", "xbow", "xboq"], freq=str(min(6, freq_i + 1)), etypes=["staf", "wand", "orb"]))
            if grp in ("14", "16"):
                extra_rows.append(_clone_affix_for_types(r, ["axe"], freq=str(min(6, freq_i + 2)), etypes=[]))
            if grp == "15":
                extra_rows.append(_clone_affix_for_types(r, ["spea"], freq=str(min(6, freq_i + 1)), etypes=[]))

        # 7. Prevent Monster Heal (grp 20) & Ignore Target Defense (grp 4): boost Daggers & Spears
        if grp == "20" and "weap" in itypes_all:
            extra_rows.append(_clone_affix_for_types(r, ["knif"], freq=str(min(8, freq_i * 2)), etypes=[]))
        if grp == "4" and "weap" in itypes_all:
            extra_rows.append(_clone_affix_for_types(r, ["knif", "spea"], freq=str(min(8, max(3, freq_i * 2))), etypes=[]))

        # 8. Life/Mana Leech (grp 27, 28): boost Swords, Polearms (LL), Gloves; unlock mid-tier leech on Bows/Crossbows (miss)
        if grp == "27" and "mele" in itypes_all and int(r.get("level") or "0") >= 25:
            extra_rows.append(_clone_affix_for_types(r, ["swor", "pole"], freq="2", etypes=[]))
            if name == "of the Locust":
                extra_rows.append(_clone_affix_for_types(r, ["miss"], freq="3", etypes=[]))
        if grp == "28" and "mele" in itypes_all and name == "of the Wraith":
            extra_rows.append(_clone_affix_for_types(r, ["miss"], freq="3", etypes=[]))
        if grp in ("27", "28") and "glov" in itypes_all:
            r["frequency"] = str(min(8, freq_i + 1))

        # 9. Boots FRW (grp 35, move1..3): differentiate Light (lbot high), Med (mbot balanced), Heavy (hbot low); boost Circlets
        if grp == "35":
            if "boot" in itypes_all and r.get("rare") == "1" and int(r.get("level") or "0") >= 15:
                _add_etypes(r, ["lbot", "mbot", "hbot"])
                extra_rows.append(_clone_affix_for_types(r, ["lbot"], freq=str(min(9, freq_i + 3)), etypes=[]))
                extra_rows.append(_clone_affix_for_types(r, ["mbot"], freq=str(freq_i), etypes=[]))
                extra_rows.append(_clone_affix_for_types(r, ["hbot"], freq="1", etypes=[]))
            elif "circ" in itypes_all:
                r["frequency"] = str(min(9, freq_i + 2))

        # 10. Thorns (grp 6): strip from Circlets; slash on Light Armor/Shields, Necro Heads, Belts; boost on Heavy Armor/Shields
        if grp == "6" and ({"armo", "tors", "shld", "belt", "circ"} & itypes_all):
            _add_etypes(r, ["circ", "ltor", "lshi", "lash", "head", "htor", "hshi", "hash"])
            extra_rows.append(_clone_affix_for_types(r, ["htor", "hshi", "hash"], freq=str(min(9, freq_i + 2)), etypes=["bcas"]))
            extra_rows.append(_clone_affix_for_types(r, ["ltor", "lshi", "lash", "head"], freq="1", etypes=["bcas"]))
            if "belt" in itypes_all and freq_i >= 2:
                r["frequency"] = str(max(1, freq_i // 2))

        # 11. Flat PDR (grp 1) & MDR (grp 2): boost Heavy Armor/Shields/Gloves/Boots; lower on Light Armor/Shields & Necro Heads
        if grp in ("1", "2") and ({"armo", "tors", "shld"} & itypes_all) and r.get("rare") == "1" and int(r.get("level") or "0") >= 15:
            _add_etypes(r, ["ltor", "lshi", "lash", "head", "htor", "hshi", "hash"])
            extra_rows.append(_clone_affix_for_types(r, ["htor", "hshi", "hash", "hglv", "hbot"], freq=str(min(9, max(4, freq_i * 2))), etypes=["bcas"]))
            extra_rows.append(_clone_affix_for_types(r, ["ltor", "lshi", "lash", "head"], freq="1", etypes=["bcas"]))

        # 12. FHR (grp 18, balance1..3): boost Medium Body Armor/Shields, Heavy Shields/Boots, Helms/Barb Helms/Pelts
        if grp == "18" and r.get("rare") == "1" and int(r.get("level") or "0") >= 10:
            if "armo" in itypes_all or "tors" in itypes_all or "shld" in itypes_all:
                extra_rows.append(_clone_affix_for_types(r, ["mtor", "mshi", "mash", "hshi", "hash", "hbot", "helm"], freq="3", etypes=[]))

        # 13. Block/FBR (grp 8): handled via _stabilize_block_suffixes for constant ~15% rate across all levels & shield types

        # 14. Life (grp 26): boost Heavy Armor/Shields/Gloves, Medium Armor, Belts, Circlets, Necro Heads, Blunt
        if grp == "26" and r.get("rare") == "1" and int(r.get("level") or "0") >= 20:
            if "belt" in itypes_all or "circ" in itypes_all or "shld" in itypes_all or "tors" in itypes_all:
                extra_rows.append(_clone_affix_for_types(r, ["htor", "mtor", "hshi", "hash", "hglv", "belt", "head"], freq="3", etypes=[]))

        # 15. Strength (grp 31): boost Heavy Armor/Shields/Gloves/Boots, Barb Helms, Belts (modest so Str doesn't crowd out)
        if grp == "31" and r.get("rare") == "1" and int(r.get("level") or "0") >= 20:
            if "armo" in itypes_all or "tors" in itypes_all or "shld" in itypes_all or "belt" in itypes_all:
                extra_rows.append(_clone_affix_for_types(r, ["htor", "hshi", "hash", "hglv", "hbot", "phlm"], freq="2", etypes=["bcas"]))

        # 16. Dexterity (grp 17) & MF (grp 22): boost Light Armor/Gloves/Boots + Arrows (bowq)
        if grp == "17" and r.get("rare") == "1" and int(r.get("level") or "0") >= 15:
            if "armo" in itypes_all or "glov" in itypes_all or "boot" in itypes_all:
                extra_rows.append(_clone_affix_for_types(r, ["ltor", "lglv", "lbot", "bowq"], freq="3", etypes=[]))
        if grp == "22" and r.get("rare") == "1" and int(r.get("level") or "0") >= 15:
            if "glov" in itypes_all or "boot" in itypes_all or "circ" in itypes_all:
                extra_rows.append(_clone_affix_for_types(r, ["ltor", "lglv", "lbot"], freq="3", etypes=[]))

        # 17. Trim clutter: hit-skill (grp 44) on Gloves/Circlets/Shields/Heads/Caster Rods, rep-dur (grp 37) on Helms/Boots, light (grp 25) on Helms
        if grp == "44" and ({"glov", "circ", "shld", "head", "ashd", "wand", "staf", "orb", "weap"} & itypes_all) and freq_i >= 2:
            r["frequency"] = str(max(1, freq_i // 2))
        if grp == "37" and ({"helm", "boot", "phlm", "pelt"} & itypes_all) and freq_i >= 2:
            r["frequency"] = str(max(1, freq_i // 2))
        if grp == "25" and ({"helm", "phlm", "pelt"} & itypes_all) and freq_i >= 2:
            r["frequency"] = str(max(1, freq_i // 2))

    rows.extend(extra_rows)


def _apply_smart_maxlevel_cutoffs(
    rows: List[Dict[str, str]],
    cutoff_groups: set,
    max_lvl_threshold: int,
    window: int,
) -> None:
    """
    Apply progressive maxlevel cutoffs (lvl + window) ONLY to Rare-eligible rows whose group has a
    strictly higher Rare-eligible tier covering EVERY item type on the row. This phases out low-tier
    clutter while guaranteeing ZERO affix groups ever drop off in Nightmare/Hell on any item type!
    """
    # Build minimal parent hierarchy for common umbrella item types
    ancestors = {
        "tors": {"armo"}, "ltor": {"tors", "armo"}, "mtor": {"tors", "armo"}, "htor": {"tors", "armo"}, "ctor": {"tors", "armo"},
        "shie": {"shld", "armo"}, "lshi": {"shie", "shld", "armo"}, "mshi": {"shie", "shld", "armo"}, "hshi": {"shie", "shld", "armo"},
        "ashd": {"shld", "armo"}, "lash": {"ashd", "shld", "armo"}, "mash": {"ashd", "shld", "armo"}, "hash": {"ashd", "shld", "armo"},
        "head": {"shld", "armo"}, "shld": {"armo"},
        "helm": {"armo"}, "phlm": {"helm", "armo"}, "pelt": {"helm", "armo"}, "circ": {"armo"},
        "glov": {"armo"}, "lglv": {"glov", "armo"}, "mglv": {"glov", "armo"}, "hglv": {"glov", "armo"},
        "boot": {"armo"}, "lbot": {"boot", "armo"}, "mbot": {"boot", "armo"}, "hbot": {"boot", "armo"},
        "belt": {"armo"},
        "mele": {"weap"}, "miss": {"weap"}, "blun": {"mele", "weap"}, "rod": {"blun", "mele", "weap"},
        "swor": {"mele", "weap"}, "axe": {"mele", "weap"}, "knif": {"mele", "weap"},
        "club": {"blun", "mele", "weap"}, "mace": {"blun", "mele", "weap"}, "hamm": {"blun", "mele", "weap"},
        "pole": {"mele", "weap"}, "spea": {"mele", "weap"}, "h2h": {"mele", "weap"}, "h2h2": {"h2h", "mele", "weap"},
        "scep": {"rod", "blun", "mele", "weap"}, "wand": {"rod", "blun", "mele", "weap"}, "staf": {"rod", "blun", "mele", "weap"},
        "orb": {"weap"}, "bow": {"miss", "weap"}, "xbow": {"miss", "weap"},
        "jave": {"thro", "mele", "weap"}, "taxe": {"thro", "mele", "weap"}, "tkni": {"thro", "mele", "weap"},
        "thro": {"weap"}, "bhlm": {"bcas", "helm", "armo"}, "bshd": {"bcas", "shie", "shld", "armo"},
    }
    def get_anc(c: str) -> set:
        return {c} | ancestors.get(c, set())

    by_grp: Dict[str, List[Dict[str, str]]] = {}
    for r in rows:
        if r.get("spawnable") == "1" and r.get("version") != "0" and r.get("rare") == "1":
            it1 = r.get("itype1", "").strip()
            if it1 in ("lcha", "mcha", "scha", "jewl"):
                continue
            by_grp.setdefault(r.get("group", ""), []).append(r)

    split_rows: List[Dict[str, str]] = []
    for grp in cutoff_groups:
        gr = by_grp.get(grp, [])
        if len(gr) < 2:
            continue
        for r in gr:
            if r.get("maxlevel"):
                continue
            lvl = int(r.get("level") or "1")
            if lvl > max_lvl_threshold:
                continue
            r_its = [r.get(f"itype{i}", "").strip() for i in range(1, 8) if r.get(f"itype{i}", "").strip()]
            if not r_its:
                continue
            covered_its: List[str] = []
            uncovered_its: List[str] = []
            for it in r_its:
                it_anc = get_anc(it)
                has_higher = False
                for r2 in gr:
                    if int(r2.get("level") or "1") <= lvl:
                        continue
                    r2_its = {r2.get(f"itype{i}", "").strip() for i in range(1, 8) if r2.get(f"itype{i}", "").strip()}
                    r2_ets = {r2.get(f"etype{i}", "").strip() for i in range(1, 6) if r2.get(f"etype{i}", "").strip()}
                    if (r2_its & it_anc) and not (r2_ets & it_anc):
                        has_higher = True
                        break
                if has_higher:
                    covered_its.append(it)
                else:
                    uncovered_its.append(it)
            if covered_its and not uncovered_its:
                r["maxlevel"] = str(lvl + window)
            elif covered_its and uncovered_its:
                # Split mixed-slot row: keep uncovered slots uncapped, phase out covered slots cleanly!
                for idx in range(1, 8):
                    r[f"itype{idx}"] = uncovered_its[idx - 1] if idx <= len(uncovered_its) else ""
                split_rows.append(_clone_affix_for_types(r, covered_its, maxlevel=str(lvl + window)))
    rows.extend(split_rows)


def _stabilize_block_suffixes(
    headers: List[str],
    rows: List[Dict[str, str]],
    target_pct: float = 0.15,
) -> None:
    """
    Replace flat group-8 (of Blocking / of Deflecting) shield rows with 4 non-overlapping alvl brackets
    whose integer frequencies are auto-calibrated against live non-block TotW so every shield family
    (Light/Med/Heavy Standard & Paladin Shields, Necro Heads, Bone Shields) rolls ~target_pct (15%)
    at Normal, Nightmare, and Hell!
    """
    ancestors = {
        "lshi": {"shie", "shld", "armo"}, "mshi": {"shie", "shld", "armo"}, "hshi": {"shie", "shld", "armo"},
        "lash": {"ashd", "shld", "armo"}, "mash": {"ashd", "shld", "armo"}, "hash": {"ashd", "shld", "armo"},
        "head": {"shld", "armo"}, "bshd": {"bcas", "shie", "shld", "armo"},
    }
    tpl_blk = None
    tpl_def = None
    for r in rows:
        if r.get("spawnable") == "1" and r.get("version") != "0" and r.get("group") == "8":
            if "Deflect" in r.get("Name", "") and tpl_def is None:
                tpl_def = dict(r)
            elif "Block" in r.get("Name", "") and tpl_blk is None:
                tpl_blk = dict(r)
            r["spawnable"] = "0"
    if not tpl_blk or not tpl_def:
        return

    # Each bucket: (representative_code, itypes_list)
    buckets = [
        ("lshi", ["lshi", "lash"]),
        ("mshi", ["mshi", "mash"]),
        ("hshi", ["hshi", "hash"]),
        ("head", ["head"]),
        ("bshd", ["bshd"]),
    ]
    # Non-overlapping alvl brackets: (min_lvl, max_lvl, sample_alvl, deflecting_share)
    # Act 1-3 Normal (1-24): 100% Blocking | Act 4-5 Normal (25-44): 35% Deflecting |
    # Nightmare (45-64): 50% Deflecting | Hell (65+): 67% Deflecting (~2/3)
    brackets = [
        ("1",  "24", 12, 0.00),
        ("25", "44", 30, 0.35),
        ("45", "64", 50, 0.50),
        ("65", "",   75, 0.67),
    ]

    new_rows: List[Dict[str, str]] = []
    for rep, its in buckets:
        a = {rep} | ancestors[rep]
        for min_l, max_l, sample_alvl, defl_share in brackets:
            other_w = 0
            for r in rows:
                if r.get("spawnable") != "1" or r.get("version") == "0" or r.get("rare") != "1":
                    continue
                if r.get("group") == "8":
                    continue
                if not (int(r.get("level") or 0) <= sample_alvl <= int(r.get("maxlevel") or 999)):
                    continue
                r_its = {r.get(f"itype{i}", "").strip() for i in range(1, 8) if r.get(f"itype{i}", "").strip()}
                r_ets = {r.get(f"etype{i}", "").strip() for i in range(1, 6) if r.get(f"etype{i}", "").strip()}
                if (r_its & a) and not (r_ets & a):
                    other_w += int(r.get("frequency") or 0)
            target_w = max(2, int(round(other_w * target_pct / (1.0 - target_pct))))
            w_def = int(round(target_w * defl_share)) if defl_share > 0.0 else 0
            w_blk = max(1, target_w - w_def)

            rb = _clone_affix_for_types(tpl_blk, its, freq=str(w_blk), etypes=[], maxlevel=max_l)
            rb["level"] = min_l
            rb["levelreq"] = "1"
            rb["spawnable"] = "1"
            new_rows.append(rb)

            if w_def > 0:
                rd = _clone_affix_for_types(tpl_def, its, freq=str(w_def), etypes=[], maxlevel=max_l)
                rd["level"] = min_l
                rd["levelreq"] = "18"
                rd["spawnable"] = "1"
                new_rows.append(rd)

    rows.extend(new_rows)


def _rebalance_charged_suffixes(rows: List[Dict[str, str]]) -> None:
    """
    Overhaul spawnable `charged` suffixes in magicsuffix.txt:
    1) Disable dead-weight late-game (alvl 48-72) off-class unsynergized nuke charges that
       dilute Hell Magic/Rare jewelry, weapon, and glove pools.
    2) Keep all 10 Amazon Bow/Spear attack charges on Gloves (`glov`), bringing their absurd
       Vanilla alvl (40-94) down to match their actual skill tier (req 10-44) with fixed slvl 6-8
       so cross-class Bow/Spear + Stance builds can genuinely use them during playthrough.
    3) Sync all remaining class & utility charged suffixes so `levelreq >= skill_reqlevel`
       (Castalia's 1/8/16/24/32/40 tiers) and replace Vanilla's negative scaling `mod1max`
       (which always rolled slvl 1 at unlock) with fixed playthrough-viable skill levels (5-8).
    """
    # Map charged suffix Name -> (sk_req, is_utility, is_ama_glov_atk)
    # Keyed by Name so it is completely immune to Sorceress skill ID permutation order.
    sk_meta = {
        # Amazon Bow/Spear attacks & utility
        "of Magic Arrows":     (1, False, True),
        "of Fire Arrows":      (1, False, True),
        "of Inner Sight":      (1, True, False),
        "of Cold Arrows":      (8, False, True),
        "of Multiple Shot":    (8, False, True),
        "of Power Strike":     (8, False, True),
        "of Exploding Arrows": (16, False, True),
        "of Ice Arrows":       (24, False, True),
        "of Charged Strike":   (24, False, True),
        "of Freezing Arrows":  (40, False, True),
        "of Lightning Strike": (40, False, True),
        # Sorceress
        "of Fire Bolts":       (1, False, False),
        "of Fire Balls":       (8, False, False),
        "of Meteors":          (24, False, False),
        "of Lightning":        (1, False, False),
        "of Novas":            (8, False, False),
        "of Chain Lightning":  (24, False, False),
        "of Ice Bolts":        (1, False, False),
        "of Frost Novas":      (8, True, False),
        "of Ice Blasts":       (16, False, False),
        "of Glacial Spikes":   (32, False, False),
        "of Blizzards":        (32, False, False),
        "of Frozen Orbs":      (40, False, False),
        # Necromancer
        "of Teeth":            (1, False, False),
        "of Dim Vision":       (8, True, False),
        "of Weaken":           (8, True, False),
        "of Poison Dagger":    (8, False, False),
        "of Terror":           (16, True, False),
        "of Confusion":        (24, True, False),
        "of Life Tap":         (24, True, False),
        "of Bone Spears":      (24, False, False),
        "of Attraction":       (32, True, False),
        "of Poison Novas":     (40, False, False),
        "of Bone Spirits":     (40, False, False),
        # Paladin
        "of Sacrifice":        (1, False, False),
        "of Holy Bolts":       (8, False, False),
        "of Zeal":             (16, False, False),
        "of Vengeance":        (24, False, False),
        "of Blessed Hammers":  (24, False, False),
        # Druid
        "of Firestorms":       (1, False, False),
        "of Eruption":         (16, False, False),
        "of Twister":          (24, False, False),
        "of Volcano":          (32, False, False),
        "of Tornado":          (32, False, False),
        # Warlock
        "of Miasma Bolt":      (1, False, False),
        "of Lethargy":         (8, True, False),
        "of Rancor":           (16, True, False),
        "of Apocalypse":       (40, False, False),
    }

    # Dead-weight late-game off-class unsynergized nuke charges to disable
    dead_offclass_nukes = {
        ("of Frozen Orbs", "knif"),
        ("of Bone Spirits", "amul"),
        ("of Poison Novas", "glov"),
        ("of Apocalypse", "glov"),
        ("of Blizzards", "knif"),
        ("of Meteors", "knif"),
        ("of Tornado", "amul"),
        ("of Volcano", "hamm"),
        ("of Blessed Hammers", "hamm"),
        ("of Bone Spears", "spea"),
        ("of Chain Lightning", "spea"),
        ("of Glacial Spikes", "knif"),
        ("of Twister", "amul"),
        ("of Vengeance", "swor"),
    }

    # Tier -> (fixed_slvl_class, fixed_slvl_glov, glov_alvl, glov_req, chg_cls, chg_off, chg_high)
    # Progressive total charges (~2x Vanilla baseline) scaled cleanly by skill tier (all <= 140, well below 8-bit 255 cap)
    tier_cfg = {
        1:  (6, 6, 12, 10,  50, 40,  80),
        8:  (6, 6, 18, 15,  65, 50,  95),
        16: (6, 6, 24, 21,  80, 60, 110),
        24: (6, 7, 32, 28,  95, 70, 120),
        32: (7, 7, 40, 36, 110, 80, 130),
        40: (8, 8, 48, 44, 120, 80, 140),
    }

    for r in rows:
        if r.get("spawnable") != "1" or r.get("version") == "0" or r.get("mod1code") != "charged":
            continue
        name = r.get("Name", "")
        it1 = r.get("itype1", "").strip()
        if (name, it1) in dead_offclass_nukes:
            r["spawnable"] = "0"
            continue

        if name not in sk_meta:
            continue
        sk_req, is_util, is_ama_atk = sk_meta[name]
        slvl_cls, slvl_glov, glov_alvl, glov_req, chg_cls, chg_off, chg_high = tier_cfg.get(
            sk_req, (6, 6, 24, 20, 80, 60, 110)
        )

        # Preserve Vanilla's relative pool sizing (high-charge -60 rows vs standard -30 vs off-class -20)
        orig_chg = abs(int(r.get("mod1min") or "30"))
        if orig_chg >= 55:
            target_chg = chg_high
        elif orig_chg <= 22:
            target_chg = chg_off
        else:
            target_chg = chg_cls

        # Amazon Bow/Spear attack charges on Gloves: align alvl/req to skill tier + fixed slvl 6-8
        if is_ama_atk and it1 == "glov":
            r["level"] = str(glov_alvl)
            r["levelreq"] = str(glov_req)
            r["mod1min"] = str(chg_off)
            r["mod1max"] = str(slvl_glov)
            continue

        # Inner Sight on Gloves: bring down from alvl 50 / req 42 to alvl 16 / req 14
        if name == "of Inner Sight" and it1 == "glov":
            r["level"] = "16"
            r["levelreq"] = "14"
            r["mod1min"] = str(chg_off)
            r["mod1max"] = "6"
            continue

        # Ensure no charged suffix unlocks earlier than its skill's reqlevel
        cur_lvl = int(r.get("level") or "1")
        cur_req = int(r.get("levelreq") or "1")
        min_req = max(cur_req, sk_req + 2 if sk_req >= 24 else sk_req)
        min_lvl = max(cur_lvl, min_req)
        r["level"] = str(min_lvl)
        r["levelreq"] = str(min_req)
        r["mod1min"] = str(target_chg)

        # Replace negative scaling slvl (which starts at slvl 1 on unlock) with fixed playthrough-viable slvl
        if is_util:
            r["mod1max"] = "6" if sk_req <= 16 else "5"
        else:
            r["mod1max"] = str(slvl_cls)


def build_affix_strings(cfg: dict) -> str:
    updates = [
        (60060, "Arcane", "Arcane"),
        (60061, "Mystic", "Mystic"),
        (60062, "Eldritch", "Eldritch"),
        (60063, "Astral", "Astral"),
        (60064, "of Puncturing", "of Puncturing"),
        (60065, "of Impaling", "of Impaling"),
        (60066, "of Skewering", "of Skewering"),
        (60067, "of Bleeding", "of Bleeding"),
        (60068, "of Laceration", "of Laceration"),
        (60069, "of Hemorrhage", "of Hemorrhage"),
        (60070, "of Precision", "of Precision"),
        (60071, "of Lethality", "of Lethality"),
        (60072, "of Execution", "of Execution"),
        (60073, "of Impact", "of Impact"),
        (60074, "of Battering", "of Battering"),
        (60075, "of Crushing", "of Crushing"),
        (60076, "of Snaring", "of Snaring"),
        (60077, "of Entangling", "of Entangling"),
        (60078, "of Crippling", "of Crippling"),
        (60079, "Forgemaster's", ""),
        (60080, "of Socketing", ""),
        (60081, "Seraph's", "Seraph's"),
        (60082, "Hellfire", "Hellfire"),
        (60083, "Tempest", "Tempest"),
        (60084, "Frostbound", "Frostbound"),
        (60085, "Leviathan's", "Leviathan's"),
        (60086, "of the Archmage", "of the Archmage"),
        (60087, "of the Ascendant", "of the Ascendant"),
        (60088, "Cerulean", "Cerulean"),
        (60089, "Infernal", "Infernal"),
        (60090, "Voltaic", "Voltaic"),
        (60091, "Verdant", "Verdant"),
        (60092, "Enduring", "Enduring"),
        (60093, "Relentless", "Relentless"),
        (60094, "Boundless", "Boundless"),
        (60095, "Untiring", "Untiring"),
        (60096, "Ceaseless", "Ceaseless"),
    ]
    return update_mod_strings_json("item-nameaffixes.json", updates)


def build_properties_txt(cfg: dict) -> str:
    headers, rows = read_excel_tsv("properties.txt")
    if not any(r.get("code") == "skull-curse" for r in rows):
        max_id = max((int(r["*Id"]) for r in rows if (r.get("*Id") or "").isdigit()), default=283)
        nr = {h: "" for h in headers}
        nr["code"] = "skull-curse"
        nr["*Id"] = str(max_id + 1)
        nr["*Enabled"] = "1"
        # func 15 applies mod min (Drain Life hpregen, e.g. -10..-2);
        # func 16 applies mod max (-Light Radius item_lightradius, e.g. -3..-1).
        # Since hpregen <= light_radius for all tiers, min <= max always holds cleanly.
        nr["func1"] = "15"
        nr["stat1"] = "hpregen"
        nr["func2"] = "16"
        nr["stat2"] = "item_lightradius"
        nr["*Tooltip"] = "Drain Life & -Light Radius"
        nr["*Min"] = "Drain Life"
        nr["*Max"] = "Light Radius"
        nr["*Notes"] = "Castalia Skull crafting bust compound property"
        nr["*eol"] = "0"
        rows.append(nr)
    if not any(r.get("code") == "total-ac%" for r in rows):
        max_id = max((int(r["*Id"]) for r in rows if (r.get("*Id") or "").isdigit()), default=283)
        nr = {h: "" for h in headers}
        nr["code"] = "total-ac%"
        nr["*Id"] = str(max_id + 1)
        nr["*Enabled"] = "1"
        nr["func1"] = "1"
        nr["stat1"] = "skill_armor_percent"
        nr["*Tooltip"] = "Total Defense +/-#%"
        nr["*Min"] = "Min %"
        nr["*Max"] = "Max %"
        nr["*Notes"] = "Castalia Topaz crafting bust (global % defense)"
        nr["*eol"] = "0"
        rows.append(nr)
    if not any(r.get("code") == "stamina-fatigue" for r in rows):
        max_id = max((int(r["*Id"]) for r in rows if (r.get("*Id") or "").isdigit()), default=283)
        nr = {h: "" for h in headers}
        nr["code"] = "stamina-fatigue"
        nr["*Id"] = str(max_id + 1)
        nr["*Enabled"] = "1"
        nr["func1"] = "11"
        nr["stat1"] = "skill_conviction"
        nr["uiRangeType"] = "7"
        nr["*Tooltip"] = "Hidden Stamina Exhaustion melee proc"
        nr["*Parameter"] = "Skill"
        nr["*Min"] = "% Chance"
        nr["*Max"] = "Skill Level"
        nr["*Notes"] = "Castalia hidden melee stamina exhaustion stat"
        nr["*eol"] = "0"
        rows.append(nr)
    if not any(r.get("code") == "stamina-fatigue-r" for r in rows):
        max_id = max((int(r["*Id"]) for r in rows if (r.get("*Id") or "").isdigit()), default=283)
        nr = {h: "" for h in headers}
        nr["code"] = "stamina-fatigue-r"
        nr["*Id"] = str(max_id + 1)
        nr["*Enabled"] = "1"
        nr["func1"] = "11"
        nr["stat1"] = "skill_bypass_beasts"
        nr["uiRangeType"] = "7"
        nr["*Tooltip"] = "Hidden Stamina Exhaustion missile proc"
        nr["*Parameter"] = "Skill"
        nr["*Min"] = "% Chance"
        nr["*Max"] = "Skill Level"
        nr["*Notes"] = "Castalia hidden ranged/missile stamina exhaustion stat"
        nr["*eol"] = "0"
        rows.append(nr)
    if not any(r.get("code") == "stun-fatigue" for r in rows):
        max_id = max((int(r["*Id"]) for r in rows if (r.get("*Id") or "").isdigit()), default=283)
        nr = {h: "" for h in headers}
        nr["code"] = "stun-fatigue"
        nr["*Id"] = str(max_id + 1)
        nr["*Enabled"] = "1"
        nr["func1"] = "11"
        nr["stat1"] = "skill_bypass_demons"
        nr["uiRangeType"] = "7"
        nr["*Tooltip"] = "Hidden Stun Fatigue melee stack proc"
        nr["*Parameter"] = "Skill"
        nr["*Min"] = "% Chance"
        nr["*Max"] = "Skill Level"
        nr["*Notes"] = "Castalia hidden domeleeattack trigger incrementing stun_fatigue"
        nr["*eol"] = "0"
        rows.append(nr)
    if not any(r.get("code") == "stun-reset" for r in rows):
        max_id = max((int(r["*Id"]) for r in rows if (r.get("*Id") or "").isdigit()), default=283)
        nr = {h: "" for h in headers}
        nr["code"] = "stun-reset"
        nr["*Id"] = str(max_id + 1)
        nr["*Enabled"] = "1"
        nr["func1"] = "11"
        nr["stat1"] = "skill_passive_staminapercent"
        nr["uiRangeType"] = "7"
        nr["*Tooltip"] = "Hidden Stun Fatigue reset on kill or melee hit"
        nr["*Parameter"] = "Skill"
        nr["*Min"] = "% Chance"
        nr["*Max"] = "Skill Level"
        nr["*Notes"] = "Castalia hidden attackedinmelee/kill trigger clearing stun_fatigue"
        nr["*eol"] = "0"
        rows.append(nr)
    return write_excel_tsv("properties.txt", headers, rows)


def build_affixes_all(cfg: dict) -> str:
    p1 = build_itemstatcost(cfg)
    p1b = build_properties_txt(cfg)
    p2 = build_magicprefix(cfg)
    p3 = build_magicsuffix(cfg)
    p4 = build_affix_strings(cfg)
    return f"{p1}, {p1b}, {p2}, {p3}, {p4}"


def print_affix_summary(cfg: dict) -> str:
    import os
    from mod_builder.common import MOD_ROOT

    def read_mod_tsv(name: str):
        path = os.path.join(MOD_ROOT, "data/global/excel", name)
        with open(path, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\r\n") for line in f if line.strip()]
        hdr = lines[0].split("\t")
        rows = []
        for ln in lines[1:]:
            parts = ln.split("\t")
            rows.append({hdr[i]: (parts[i] if i < len(parts) else "") for i in range(len(hdr))})
        return rows

    it_rows = read_mod_tsv("itemtypes.txt")
    mp_rows = read_mod_tsv("magicprefix.txt")
    ms_rows = read_mod_tsv("magicsuffix.txt")

    parents = {}
    for r in it_rows:
        c = r.get("Code", "").strip()
        if c:
            parents[c] = [p for p in (r.get("Equiv1", "").strip(), r.get("Equiv2", "").strip()) if p]

    def get_ancestors(code: str):
        visited = set()
        stack = [code]
        while stack:
            cur = stack.pop()
            if cur and cur not in visited:
                visited.add(cur)
                stack.extend(parents.get(cur, []))
        return visited

    def analyze_pool(rows, item_code: str, alvl: int, rare_only: bool):
        anc = get_ancestors(item_code)
        eligible = []
        for r in rows:
            if r.get("spawnable") != "1" or not r.get("frequency"):
                continue
            if r.get("classspecific"):
                continue
            if rare_only and r.get("rare") != "1":
                continue
            lvl = int(r.get("level") or "1")
            maxlvl_s = r.get("maxlevel", "").strip()
            if alvl < lvl:
                continue
            if maxlvl_s and alvl > int(maxlvl_s):
                continue
            itypes = {r.get(f"itype{i}", "").strip() for i in range(1, 8) if r.get(f"itype{i}", "").strip()}
            etypes = {r.get(f"etype{i}", "").strip() for i in range(1, 6) if r.get(f"etype{i}", "").strip()}
            if not (itypes & anc):
                continue
            if etypes & anc:
                continue
            freq = int(r.get("frequency") or "0")
            if freq > 0:
                eligible.append((r, freq))
        total_w = sum(f for _, f in eligible)
        by_grp = {}
        for r, f in eligible:
            g = r.get("group", "")
            by_grp.setdefault(g, []).append((r, f))
        return total_w, by_grp

    slots = [
        ("swor", "Melee Weapon (Sword)"),
        ("bow", "Ranged Weapon (Bow)"),
        ("bowq", "Quiver (Arrows)"),
        ("glov", "Gloves"),
        ("amul", "Amulet"),
    ]
    tactical_grps = {
        "60": "Pierce",
        "61": "Open Wounds",
        "62": "Deadly Strike",
        "63": "Crushing Blow",
        "64": "Slows Target",
        "7": "Attack Speed (IAS)",
        "24": "Knockback",
    }

    for scode, slabel in slots:
        print(f"\n==================== SUFFIX POOL: {slabel} ({scode}) ====================")
        for mode_lbl, rare_only in [("RARE / CRAFTED (rare=1)", True), ("MAGIC (All Spawnable)", False)]:
            print(f"  --- {mode_lbl} ---")
            for alvl in (12, 30, 50, 75):
                tot_w, by_grp = analyze_pool(ms_rows, scode, alvl, rare_only)
                tac_total_w = sum(sum(f for _, f in by_grp.get(g, [])) for g in ("60", "61", "62", "63", "64"))
                tac_pct = (100.0 * tac_total_w / tot_w) if tot_w else 0.0
                details = []
                for g in ("60", "61", "62", "63", "64", "7", "24"):
                    if g in by_grp:
                        gw = sum(f for _, f in by_grp[g])
                        gpct = 100.0 * gw / tot_w
                        tiers_str = ", ".join(f"{r['Name']}(w={f},{100.0*f/gw:.0f}%)" for r, f in by_grp[g])
                        details.append(f"Grp {g} {tactical_grps[g]}: {gpct:.2f}% [w={gw}/{tot_w}: {tiers_str}]")
                print(f"    alvl={alvl:2d} | TotalSuffixWeight={tot_w:3d} | All 5 New Tactical Combined={tac_pct:5.2f}% (w={tac_total_w})")
                for d in details:
                    print(f"      -> {d}")

    print("\n==================== WEAPON PREFIX POOL: %ED (Grp 105), %ED+AR (Grp 111), Magic Dmg (Grp 145) ====================")
    for scode, slabel in [("swor", "Melee Weapon"), ("bowq", "Quiver")]:
        for mode_lbl, rare_only in [("RARE / CRAFTED", True), ("MAGIC", False)]:
            print(f"  {slabel} [{mode_lbl}]:")
            for alvl in (12, 30, 50, 75):
                tot_w, by_grp = analyze_pool(mp_rows, scode, alvl, rare_only)
                for g, glbl in [("105", "%ED"), ("111", "%ED+AR"), ("145", "MagicDmg")]:
                    if g in by_grp:
                        gw = sum(f for _, f in by_grp[g])
                        gpct = (100.0 * gw / tot_w) if tot_w else 0.0
                        tiers_str = ", ".join(f"{r['Name']}(w={f},{100.0*f/gw:.0f}%)" for r, f in by_grp[g])
                        print(f"    alvl={alvl:2d} | TotW={tot_w:3d} | Grp {g} {glbl:<8}: {gpct:5.2f}% [w={gw:2d}: {tiers_str}]")

    return "affix_summary"

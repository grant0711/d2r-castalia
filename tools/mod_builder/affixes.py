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
        elif st == "item_attackertakesdamage":
            # Revert Patch 2.4's attackedinmelee back to damagedinmelee so missed and blocked
            # swings do NOT trigger Thorns; only landed melee hits reflect damage.
            r["itemevent1"] = "damagedinmelee"
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
        if st in cost_tuning:
            mult_val, add_val = cost_tuning[st]
            r["Multiply"] = mult_val
            r["Add"] = add_val
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
        "101", "105", "109", "110", "111", "112", "115",
        "116", "117", "118", "119", "120",
        "137", "138", "139", "140", "142",
    }
    # Expansion (version >= 1) Resistance & Elemental Damage groups for Quivers (bowq, xboq)
    quiver_prefix_groups = {"116", "117", "118", "119", "120", "137", "138", "139", "140"}

    for r in rows:
        # Disable all charged suffixes referencing reworked Barbarian skills (IDs 126..155)
        if r.get("mod1code") == "charged":
            m1p = r.get("mod1param", "").strip()
            if m1p.isdigit() and 126 <= int(m1p) <= 155:
                r["spawnable"] = "0"
                continue

        if r.get("spawnable") != "1" or r.get("version") == "0":
            continue
        grp = r.get("group", "")
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

        # 2. Enforce progressive maxlevel cutoffs on low/mid-tier Rare-eligible prefixes (lvl <= 32 -> lvl + 28)
        if r.get("rare") == "1" and grp in cutoff_groups and not r.get("maxlevel") and not is_charm_or_jewel:
            lvl = int(r.get("level") or "1")
            if lvl <= 32:
                r["maxlevel"] = str(lvl + 28)

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
        nr["multiply"] = "0"
        nr["add"] = "0"
        rows.append(nr)

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

    return write_excel_tsv("magicprefix.txt", headers, rows)


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
    # 7 = IAS (swing1..3), 10 = Cold Dmg, 12 = Fire Dmg, 13 = Ltng Dmg, 16 = Pois Dmg, 24 = Knockback
    quiver_suffix_groups = {"7", "10", "12", "13", "16", "24"}

    for r in rows:
        # Disable all charged suffixes referencing reworked Barbarian skills (IDs 126..155)
        if r.get("mod1code") == "charged":
            m1p = r.get("mod1param", "").strip()
            if m1p.isdigit() and 126 <= int(m1p) <= 155:
                r["spawnable"] = "0"
                continue

        if r.get("spawnable") != "1" or r.get("version") == "0":
            continue
        grp = r.get("group", "")
        it1 = r.get("itype1", "")
        itypes_all = {r.get(f"itype{i}", "").strip() for i in range(1, 8)}
        is_charm_or_jewel = it1 in ("lcha", "mcha", "scha", "jewl") or "jewl" in itypes_all

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

        # 2. Enforce progressive maxlevel cutoffs on low/mid-tier Rare-eligible suffixes (lvl <= 28 -> lvl + 26)
        if r.get("rare") == "1" and grp in cutoff_groups and not r.get("maxlevel") and not is_charm_or_jewel:
            lvl = int(r.get("level") or "1")
            if lvl <= 28:
                r["maxlevel"] = str(lvl + 26)

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

    # 4. Add Progressive Tactical Suffix Groups (60..64) for Pierce, Open Wounds, Deadly, Crushing, Slow
    # Strict frequency = "1" and non-overlapping maxlevel on Rare tiers so these are genuinely rare chase rolls!
    new_suffixes = [
        # Group 60: Piercing Attack (pierce)
        ("of Puncturing", "1", "10", "27", "7", "60", "pierce", "10", "15", ["bowq", "xboq", "miss", "jave"]),
        ("of Impaling", "1", "28", "", "21", "60", "pierce", "16", "25", ["bowq", "xboq", "miss", "jave"]),
        ("of Skewering", "", "48", "", "36", "60", "pierce", "26", "40", ["bowq", "xboq", "miss", "jave"]),
        # Group 61: Open Wounds (openwounds)
        ("of Bleeding", "1", "10", "25", "7", "61", "openwounds", "10", "15", ["bowq", "xboq", "weap"]),
        ("of Laceration", "1", "26", "", "19", "61", "openwounds", "16", "25", ["bowq", "xboq", "weap"]),
        ("of Hemorrhage", "", "46", "", "35", "61", "openwounds", "26", "40", ["bowq", "xboq", "weap"]),
        # Group 62: Deadly Strike (deadly)
        ("of Precision", "1", "12", "29", "9", "62", "deadly", "8", "12", ["bowq", "xboq", "weap", "amul"]),
        ("of Lethality", "1", "30", "", "22", "62", "deadly", "13", "20", ["bowq", "xboq", "weap", "amul"]),
        ("of Execution", "", "50", "", "38", "62", "deadly", "21", "32", ["bowq", "xboq", "weap", "helm", "amul"]),
        # Group 63: Crushing Blow (crush)
        ("of Impact", "1", "14", "33", "10", "63", "crush", "5", "10", ["bowq", "xboq", "weap", "glov"]),
        ("of Battering", "1", "34", "", "25", "63", "crush", "11", "16", ["bowq", "xboq", "weap", "glov"]),
        ("of Crushing", "", "54", "", "40", "63", "crush", "17", "25", ["bowq", "xboq", "weap", "glov", "boot"]),
        # Group 64: Slows Target (slow)
        ("of Snaring", "1", "12", "31", "9", "64", "slow", "10", "15", ["bowq", "xboq", "miss"]),
        ("of Entangling", "1", "32", "", "24", "64", "slow", "16", "22", ["bowq", "xboq", "miss"]),
        ("of Crippling", "", "52", "", "39", "64", "slow", "23", "30", ["bowq", "xboq", "miss"]),
    ]
    for name, is_rare, lvl, maxlvl, lreq, grp, mcode, vmin, vmax, itypes in new_suffixes:
        nr = {h: "" for h in headers}
        nr["Name"] = name
        nr["version"] = "100"
        nr["spawnable"] = "1"
        nr["rare"] = is_rare
        nr["level"] = lvl
        nr["maxlevel"] = maxlvl
        nr["levelreq"] = lreq
        nr["frequency"] = "1"
        nr["group"] = grp
        nr["mod1code"] = mcode
        nr["mod1min"] = vmin
        nr["mod1max"] = vmax
        for idx, it in enumerate(itypes[:7], start=1):
            nr[f"itype{idx}"] = it
        nr["multiply"] = "0"
        nr["add"] = "0"
        rows.append(nr)

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

    return write_excel_tsv("magicsuffix.txt", headers, rows)


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
        (60079, "Forgemaster's", "Forgemaster's"),
        (60080, "of Socketing", "of Socketing"),
    ]
    return update_mod_strings_json("item-nameaffixes.json", updates)


def build_affixes_all(cfg: dict) -> str:
    p1 = build_itemstatcost(cfg)
    p2 = build_magicprefix(cfg)
    p3 = build_magicsuffix(cfg)
    p4 = build_affix_strings(cfg)
    return f"{p1}, {p2}, {p3}, {p4}"


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

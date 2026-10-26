#!/usr/bin/env python3
"""
gems_runes.py
Step 3c: Complete Gem, Skull & 33-Rune Semantic Overhaul (gems.txt, item-runes.json):
- 7 Gem & Skull families: strictly 1 affix per slot (Mod1 only, Mod2/Mod3 cleared), zero overlap with Runes
- 33 Semantic Runes (r01..r33): strictly 1 affix per slot (Mod1 only, Mod2/Mod3 cleared), zero nofreeze
- Rename r01..r33 and r01L..r33L in item-runes.json to semantic names
"""
from typing import Dict, List, Tuple

from mod_builder.common import (
    read_excel_tsv,
    read_strings_json,
    upsert_string_entries,
    write_excel_tsv,
    write_strings_json,
)

# (code, weapon_mod, helm_mod, shield_mod)
# Each mod tuple is (Mod1Code, Mod1Param, Mod1Min, Mod1Max)
GEM_SPECS: List[Tuple[str, Tuple[str, str, str, str], Tuple[str, str, str, str], Tuple[str, str, str, str]]] = [
    # Ruby (Fire): Weapon Flat Fire Dmg (dmg-fire) | Armor/Helm Fire Res | Shield Fire Res
    ("gcr", ("dmg-fire", "", "3", "5"), ("res-fire", "", "12", "12"), ("res-fire", "", "16", "16")),
    ("gfr", ("dmg-fire", "", "8", "13"), ("res-fire", "", "18", "18"), ("res-fire", "", "24", "24")),
    ("gsr", ("dmg-fire", "", "20", "32"), ("res-fire", "", "25", "25"), ("res-fire", "", "34", "34")),
    ("glr", ("dmg-fire", "", "45", "70"), ("res-fire", "", "34", "34"), ("res-fire", "", "46", "46")),
    ("gpr", ("dmg-fire", "", "85", "130"), ("res-fire", "", "45", "45"), ("res-fire", "", "60", "60")),
    # Sapphire (Cold): Weapon Flat Cold Dmg (dmg-cold, 3s-7s chill) | Armor/Helm Cold Res | Shield Cold Res
    ("gcb", ("dmg-cold", "75", "2", "4"), ("res-cold", "", "12", "12"), ("res-cold", "", "16", "16")),
    ("gfb", ("dmg-cold", "100", "6", "10"), ("res-cold", "", "18", "18"), ("res-cold", "", "24", "24")),
    ("gsb", ("dmg-cold", "125", "15", "24"), ("res-cold", "", "25", "25"), ("res-cold", "", "34", "34")),
    ("glb", ("dmg-cold", "150", "34", "54"), ("res-cold", "", "34", "34"), ("res-cold", "", "46", "46")),
    ("gpb", ("dmg-cold", "175", "60", "95"), ("res-cold", "", "45", "45"), ("res-cold", "", "60", "60")),
    # Topaz (Lightning): Weapon Flat Light Dmg (dmg-ltng) | Armor/Helm Light Res | Shield Light Res
    ("gcy", ("dmg-ltng", "", "1", "8"), ("res-ltng", "", "12", "12"), ("res-ltng", "", "16", "16")),
    ("gfy", ("dmg-ltng", "", "1", "22"), ("res-ltng", "", "18", "18"), ("res-ltng", "", "24", "24")),
    ("gsy", ("dmg-ltng", "", "1", "52"), ("res-ltng", "", "25", "25"), ("res-ltng", "", "34", "34")),
    ("gly", ("dmg-ltng", "", "1", "115"), ("res-ltng", "", "34", "34"), ("res-ltng", "", "46", "46")),
    ("gpy", ("dmg-ltng", "", "1", "215"), ("res-ltng", "", "45", "45"), ("res-ltng", "", "60", "60")),
    # Emerald (Poison): Weapon Flat Pois Dmg over 3s (75 frames, bit-rate = total * 256 / 75) | Armor/Helm Pois Res | Shield Pois Res
    ("gcg", ("dmg-pois", "75", "34", "34"), ("res-pois", "", "12", "12"), ("res-pois", "", "16", "16")),
    ("gfg", ("dmg-pois", "75", "96", "96"), ("res-pois", "", "18", "18"), ("res-pois", "", "24", "24")),
    ("gsg", ("dmg-pois", "75", "222", "222"), ("res-pois", "", "25", "25"), ("res-pois", "", "34", "34")),
    ("glg", ("dmg-pois", "75", "478", "478"), ("res-pois", "", "34", "34"), ("res-pois", "", "46", "46")),
    ("gpg", ("dmg-pois", "75", "887", "887"), ("res-pois", "", "45", "45"), ("res-pois", "", "60", "60")),
    # Diamond (Arcane/Magic): Weapon Flat Magic Dmg (dmg-mag) | Armor/Helm Magic Res | Shield Magic Res
    ("gcw", ("dmg-mag", "", "2", "4"), ("res-mag", "", "5", "5"), ("res-mag", "", "7", "7")),
    ("gfw", ("dmg-mag", "", "6", "11"), ("res-mag", "", "8", "8"), ("res-mag", "", "11", "11")),
    ("gsw", ("dmg-mag", "", "16", "26"), ("res-mag", "", "12", "12"), ("res-mag", "", "16", "16")),
    ("glw", ("dmg-mag", "", "38", "60"), ("res-mag", "", "18", "18"), ("res-mag", "", "24", "24")),
    ("gpw", ("dmg-mag", "", "70", "110"), ("res-mag", "", "25", "25"), ("res-mag", "", "35", "35")),
    # Amethyst (Physical): Weapon +% Enhanced Dmg (dmg%) | Armor/Helm +Flat Defense (ac) | Shield +Flat Defense (ac)
    ("gcv", ("dmg%", "", "8", "8"), ("ac", "", "20", "20"), ("ac", "", "30", "30")),
    ("gfv", ("dmg%", "", "16", "16"), ("ac", "", "40", "40"), ("ac", "", "60", "60")),
    ("gsv", ("dmg%", "", "30", "30"), ("ac", "", "70", "70"), ("ac", "", "100", "100")),
    ("gzv", ("dmg%", "", "50", "50"), ("ac", "", "110", "110"), ("ac", "", "150", "150")),
    ("gpv", ("dmg%", "", "80", "80"), ("ac", "", "160", "160"), ("ac", "", "220", "220")),
    # Skull (Death, Attrition & Bone Armor): Weapon -Monster Def Per Hit (dmg-ac) | Armor/Helm Flat PDR (red-dmg) | Shield Flat PDR (red-dmg)
    ("skc", ("dmg-ac", "", "-10", "-10"), ("red-dmg", "", "4", "4"), ("red-dmg", "", "6", "6")),
    ("skf", ("dmg-ac", "", "-22", "-22"), ("red-dmg", "", "8", "8"), ("red-dmg", "", "12", "12")),
    ("sku", ("dmg-ac", "", "-40", "-40"), ("red-dmg", "", "14", "14"), ("red-dmg", "", "20", "20")),
    ("skl", ("dmg-ac", "", "-65", "-65"), ("red-dmg", "", "22", "22"), ("red-dmg", "", "32", "32")),
    ("skz", ("dmg-ac", "", "-100", "-100"), ("red-dmg", "", "32", "32"), ("red-dmg", "", "45", "45")),
]

# (code, semantic_name, weapon_mod, helm_mod, shield_mod)
RUNE_SPECS: List[Tuple[str, str, Tuple[str, str, str, str], Tuple[str, str, str, str], Tuple[str, str, str, str]]] = [
    # Tier 1 (r01-r11, lvl 4-24 Normal)
    ("r01", "Accuracy", ("att%", "", "20", "20"), ("att", "", "50", "50"), ("att", "", "50", "50")),
    ("r02", "Featherweight", ("ease", "", "-20", "-20"), ("ease", "", "-15", "-15"), ("ease", "", "-15", "-15")),
    ("r03", "Siphoning", ("mana-kill", "", "2", "2"), ("mana-kill", "", "1", "1"), ("mana-kill", "", "1", "1")),
    ("r04", "Reaping", ("heal-kill", "", "3", "3"), ("heal-kill", "", "2", "2"), ("heal-kill", "", "2", "2")),
    ("r05", "Mighty", ("str", "", "10", "10"), ("str", "", "10", "10"), ("str", "", "10", "10")),
    ("r06", "Deft", ("dex", "", "10", "10"), ("dex", "", "10", "10"), ("dex", "", "10", "10")),
    ("r07", "Stalwart", ("vit", "", "10", "10"), ("vit", "", "10", "10"), ("vit", "", "10", "10")),
    ("r08", "Mystic", ("enr", "", "10", "10"), ("enr", "", "10", "10"), ("enr", "", "10", "10")),
    ("r09", "Prosperous", ("gold%", "", "25", "25"), ("gold%", "", "15", "15"), ("gold%", "", "15", "15")),
    ("r10", "Fortuitous", ("mag%", "", "20", "20"), ("mag%", "", "15", "15"), ("mag%", "", "15", "15")),
    ("r11", "Fortified", ("ac", "", "50", "50"), ("ac%", "", "35", "35"), ("ac%", "", "35", "35")),
    # Tier 2 (r12-r22, lvl 26-46 Nightmare)
    ("r12", "Tempered", ("dmg-min", "", "9", "9"), ("dmg-min", "", "6", "6"), ("dmg-min", "", "7", "7")),
    ("r13", "Honed", ("dmg-max", "", "15", "15"), ("dmg-max", "", "10", "10"), ("dmg-max", "", "8", "8")),
    ("r14", "Vampiric", ("lifesteal", "", "7", "7"), ("lifesteal", "", "4", "4"), ("lifesteal", "", "4", "4")),
    ("r15", "Leeching", ("manasteal", "", "7", "7"), ("manasteal", "", "4", "4"), ("manasteal", "", "4", "4")),
    ("r16", "Alacrity", ("swing2", "", "15", "15"), ("move2", "", "15", "15"), ("block2", "", "20", "20")),
    ("r17", "Poise", ("knock", "", "1", "1"), ("balance2", "", "20", "20"), ("block", "", "10", "10")),
    ("r18", "Channeling", ("cast2", "", "10", "10"), ("cast2", "", "8", "8"), ("cast2", "", "8", "8")),
    ("r19", "Rending", ("openwounds", "", "20", "20"), ("openwounds", "", "10", "10"), ("openwounds", "", "10", "10")),
    ("r20", "Crippling", ("slow", "", "15", "15"), ("slow", "", "8", "8"), ("slow", "", "10", "10")),
    ("r21", "Piercing", ("pierce", "", "20", "20"), ("pierce", "", "10", "10"), ("pierce", "", "10", "10")),
    ("r22", "Vital", ("hp", "", "40", "40"), ("hp%", "", "6", "6"), ("hp%", "", "6", "6")),
    # Tier 3 (r23-r33, lvl 48-70 Late Nightmare & Hell)
    ("r23", "Lethal", ("deadly", "", "15", "15"), ("deadly", "", "8", "8"), ("deadly", "", "8", "8")),
    ("r24", "Crushing", ("crush", "", "15", "15"), ("crush", "", "8", "8"), ("crush", "", "8", "8")),
    ("r25", "Prismatic", ("res-all", "", "12", "12"), ("res-all", "", "12", "12"), ("res-all", "", "18", "18")),
    ("r26", "Scorching", ("pierce-fire", "", "10", "10"), ("extra-fire", "", "8", "8"), ("res-fire-max", "", "4", "4")),
    ("r27", "Glacial", ("pierce-cold", "", "10", "10"), ("extra-cold", "", "8", "8"), ("res-cold-max", "", "4", "4")),
    ("r28", "Tempest", ("pierce-ltng", "", "10", "10"), ("extra-ltng", "", "8", "8"), ("res-ltng-max", "", "4", "4")),
    ("r29", "Virulent", ("pierce-pois", "", "10", "10"), ("extra-pois", "", "8", "8"), ("res-pois-max", "", "4", "4")),
    ("r30", "Eldritch", ("extra-mag", "", "10", "10"), ("extra-mag", "", "8", "8"), ("extra-mag", "", "8", "8")),
    ("r31", "Unerring", ("ignore-ac", "", "1", "1"), ("reduce-ac", "", "15", "15"), ("reduce-ac", "", "15", "15")),
    ("r32", "Bulwark", ("indestruct", "", "1", "1"), ("red-dmg%", "", "6", "6"), ("red-dmg%", "", "6", "6")),
    ("r33", "Sovereign", ("allskills", "", "1", "1"), ("allskills", "", "1", "1"), ("allskills", "", "1", "1")),
]


def _apply_single_slot_mods(
    row: Dict[str, str],
    wmod: Tuple[str, str, str, str],
    hmod: Tuple[str, str, str, str],
    smod: Tuple[str, str, str, str],
) -> None:
    for prefix, mod in [("weapon", wmod), ("helm", hmod), ("shield", smod)]:
        row[f"{prefix}Mod1Code"] = mod[0]
        row[f"{prefix}Mod1Param"] = mod[1]
        row[f"{prefix}Mod1Min"] = mod[2]
        row[f"{prefix}Mod1Max"] = mod[3]
        for idx in (2, 3):
            row[f"{prefix}Mod{idx}Code"] = ""
            row[f"{prefix}Mod{idx}Param"] = ""
            row[f"{prefix}Mod{idx}Min"] = ""
            row[f"{prefix}Mod{idx}Max"] = ""


def build_gems_txt(cfg: dict) -> str:
    headers, rows = read_excel_tsv("gems.txt")
    rows_by_code = {r["code"]: r for r in rows if r.get("code")}

    for code, wmod, hmod, smod in GEM_SPECS:
        _apply_single_slot_mods(rows_by_code[code], wmod, hmod, smod)

    for code, sem_name, wmod, hmod, smod in RUNE_SPECS:
        row = rows_by_code[code]
        row["name"] = f"{sem_name} Rune"
        _apply_single_slot_mods(row, wmod, hmod, smod)

    return write_excel_tsv("gems.txt", headers, rows)


def build_item_runes_json(cfg: dict) -> str:
    entries = read_strings_json("item-runes.json")
    updates: List[Tuple[int, str, str]] = []
    for code, sem_name, _, _, _ in RUNE_SPECS:
        updates.append((0, code, f"{sem_name} Rune"))
        updates.append((0, f"{code}L", sem_name))
    entries = upsert_string_entries(entries, updates)
    return write_strings_json("item-runes.json", entries)


def build_gems_runes(cfg: dict) -> str:
    p1 = build_gems_txt(cfg)
    p2 = build_item_runes_json(cfg)
    return f"{p1}, {p2}"

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
    # Ruby (Fire): Weapon Flat Fire Dmg (dmg-fire) | Armor/Helm Fire Res (8..30%) | Shield Fire Res (12..45%)
    ("gcr", ("dmg-fire", "", "3", "5"), ("res-fire", "", "8", "8"), ("res-fire", "", "12", "12")),
    ("gfr", ("dmg-fire", "", "10", "16"), ("res-fire", "", "12", "12"), ("res-fire", "", "18", "18")),
    ("gsr", ("dmg-fire", "", "28", "45"), ("res-fire", "", "17", "17"), ("res-fire", "", "26", "26")),
    ("glr", ("dmg-fire", "", "65", "100"), ("res-fire", "", "23", "23"), ("res-fire", "", "35", "35")),
    ("gpr", ("dmg-fire", "", "120", "180"), ("res-fire", "", "30", "30"), ("res-fire", "", "45", "45")),
    # Sapphire (Cold): Weapon Flat Cold Dmg (dmg-cold, 3s-7s chill) | Armor/Helm Cold Res (8..30%) | Shield Cold Res (12..45%)
    ("gcb", ("dmg-cold", "75", "2", "4"), ("res-cold", "", "8", "8"), ("res-cold", "", "12", "12")),
    ("gfb", ("dmg-cold", "100", "7", "12"), ("res-cold", "", "12", "12"), ("res-cold", "", "18", "18")),
    ("gsb", ("dmg-cold", "125", "20", "32"), ("res-cold", "", "17", "17"), ("res-cold", "", "26", "26")),
    ("glb", ("dmg-cold", "150", "45", "70"), ("res-cold", "", "23", "23"), ("res-cold", "", "35", "35")),
    ("gpb", ("dmg-cold", "175", "85", "130"), ("res-cold", "", "30", "30"), ("res-cold", "", "45", "45")),
    # Topaz (Lightning): Weapon Flat Light Dmg (dmg-ltng) | Armor/Helm Light Res (8..30%) | Shield Light Res (12..45%)
    ("gcy", ("dmg-ltng", "", "1", "8"), ("res-ltng", "", "8", "8"), ("res-ltng", "", "12", "12")),
    ("gfy", ("dmg-ltng", "", "1", "26"), ("res-ltng", "", "12", "12"), ("res-ltng", "", "18", "18")),
    ("gsy", ("dmg-ltng", "", "1", "72"), ("res-ltng", "", "17", "17"), ("res-ltng", "", "26", "26")),
    ("gly", ("dmg-ltng", "", "1", "165"), ("res-ltng", "", "23", "23"), ("res-ltng", "", "35", "35")),
    ("gpy", ("dmg-ltng", "", "1", "300"), ("res-ltng", "", "30", "30"), ("res-ltng", "", "45", "45")),
    # Emerald (Poison): Weapon Flat Pois Dmg over 3s (75 frames, bit-rate = total * 256 / 75) | Armor/Helm Pois Res (8..30%) | Shield Pois Res (12..45%)
    ("gcg", ("dmg-pois", "75", "34", "34"), ("res-pois", "", "8", "8"), ("res-pois", "", "12", "12")),
    ("gfg", ("dmg-pois", "75", "109", "109"), ("res-pois", "", "12", "12"), ("res-pois", "", "18", "18")),
    ("gsg", ("dmg-pois", "75", "273", "273"), ("res-pois", "", "17", "17"), ("res-pois", "", "26", "26")),
    ("glg", ("dmg-pois", "75", "597", "597"), ("res-pois", "", "23", "23"), ("res-pois", "", "35", "35")),
    ("gpg", ("dmg-pois", "75", "1018", "1018"), ("res-pois", "", "30", "30"), ("res-pois", "", "45", "45")),
    # Diamond (Arcane/Magic): Weapon Flat Magic Dmg (dmg-mag) | Armor/Helm Magic Res (5..20%) | Shield Magic Res (7..30%)
    ("gcw", ("dmg-mag", "", "2", "4"), ("res-mag", "", "5", "5"), ("res-mag", "", "7", "7")),
    ("gfw", ("dmg-mag", "", "8", "14"), ("res-mag", "", "8", "8"), ("res-mag", "", "11", "11")),
    ("gsw", ("dmg-mag", "", "22", "36"), ("res-mag", "", "11", "11"), ("res-mag", "", "16", "16")),
    ("glw", ("dmg-mag", "", "50", "80"), ("res-mag", "", "15", "15"), ("res-mag", "", "22", "22")),
    ("gpw", ("dmg-mag", "", "95", "145"), ("res-mag", "", "20", "20"), ("res-mag", "", "30", "30")),
    # Amethyst (Physical): Weapon +% Enhanced Dmg (dmg% 10..60%) | Armor/Helm +Flat Defense (ac) | Shield +Flat Defense (ac)
    ("gcv", ("dmg%", "", "10", "10"), ("ac", "", "20", "20"), ("ac", "", "30", "30")),
    ("gfv", ("dmg%", "", "20", "20"), ("ac", "", "45", "45"), ("ac", "", "65", "65")),
    ("gsv", ("dmg%", "", "30", "30"), ("ac", "", "85", "85"), ("ac", "", "120", "120")),
    ("gzv", ("dmg%", "", "45", "45"), ("ac", "", "140", "140"), ("ac", "", "195", "195")),
    ("gpv", ("dmg%", "", "60", "60"), ("ac", "", "210", "210"), ("ac", "", "290", "290")),
    # Skull (Death, Attrition & Bone Armor): Weapon -Monster Def Per Hit (dmg-ac -15..-250, SaveBits=10 SaveAdd=512) | Armor/Helm Flat PDR (red-dmg 2..12) | Shield Flat PDR (red-dmg 3..20)
    ("skc", ("dmg-ac", "", "-15", "-15"), ("red-dmg", "", "2", "2"), ("red-dmg", "", "3", "3")),
    ("skf", ("dmg-ac", "", "-30", "-30"), ("red-dmg", "", "4", "4"), ("red-dmg", "", "6", "6")),
    ("sku", ("dmg-ac", "", "-50", "-50"), ("red-dmg", "", "6", "6"), ("red-dmg", "", "10", "10")),
    ("skl", ("dmg-ac", "", "-125", "-125"), ("red-dmg", "", "9", "9"), ("red-dmg", "", "15", "15")),
    ("skz", ("dmg-ac", "", "-250", "-250"), ("red-dmg", "", "12", "12"), ("red-dmg", "", "20", "20")),
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
    ("r21", "Clarity", ("regen-mana", "", "45", "45"), ("regen-mana", "", "20", "20"), ("regen-mana", "", "30", "30")),
    ("r22", "Vital", ("hp", "", "40", "40"), ("hp%", "", "6", "6"), ("hp%", "", "6", "6")),
    # Tier 3 (r23-r33, lvl 48-70 Late Nightmare & Hell)
    ("r23", "Lethal", ("deadly", "", "15", "15"), ("deadly", "", "8", "8"), ("deadly", "", "8", "8")),
    ("r24", "Crushing", ("crush", "", "15", "15"), ("crush", "", "8", "8"), ("crush", "", "8", "8")),
    ("r25", "Prismatic", ("res-all", "", "12", "12"), ("res-all", "", "12", "12"), ("res-all", "", "18", "18")),
    ("r26", "Scorching", ("extra-fire", "", "10", "10"), ("res-fire-max", "", "4", "4"), ("abs-fire%", "", "5", "5")),
    ("r27", "Glacial", ("extra-cold", "", "10", "10"), ("res-cold-max", "", "4", "4"), ("abs-cold%", "", "5", "5")),
    ("r28", "Tempest", ("extra-ltng", "", "10", "10"), ("res-ltng-max", "", "4", "4"), ("abs-ltng%", "", "5", "5")),
    ("r29", "Virulent", ("extra-pois", "", "10", "10"), ("res-pois-max", "", "4", "4"), ("res-pois-len", "", "25", "25")),
    ("r30", "Eldritch", ("extra-mag", "", "10", "10"), ("res-mag-max", "", "4", "4"), ("abs-mag%", "", "5", "5")),
    ("r31", "Adamant", ("ignore-ac", "", "1", "1"), ("red-dmg%", "", "6", "6"), ("red-dmg%", "", "6", "6")),
    ("r32", "Eternal", ("indestruct", "", "1", "1"), ("indestruct", "", "1", "1"), ("indestruct", "", "1", "1")),
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

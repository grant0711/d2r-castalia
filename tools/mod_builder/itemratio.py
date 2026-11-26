#!/usr/bin/env python3
"""
itemratio.py (Step 1)
Transforms itemratio.txt from vanilla-reference into my-mod/data/global/excel/itemratio.txt:
  - Eliminates all White, Superior (HiQuality), and Cracked/LowQuality monster equipment drops
    by setting Magic = 1, MagicDivisor = 1, MagicMin = 1 across all rows (100% floor at Magic quality).
  - Scales Unique, Set, and Rare base ratios and minimums using mod_config.json (scaled by austerity_level).
"""
from .common import load_config, read_excel_tsv, write_excel_tsv


def build_itemratio(cfg: dict = None) -> str:
    if cfg is None:
        cfg = load_config()
    austerity = float(cfg.get("austerity_level", 1.0))
    econ = cfg.get("economy", {})

    unique_scale = float(econ.get("unique_ratio_scale", 0.65)) * austerity
    set_scale = float(econ.get("set_ratio_scale", 0.65)) * austerity
    rare_scale = float(econ.get("rare_ratio_scale", 0.75)) * austerity
    zero_white = bool(econ.get("zero_white_monster_drops", True))

    headers, rows = read_excel_tsv("itemratio.txt")
    for row in rows:
        # Scale Unique, Set, and Rare ratios & minimum floors (lower value = higher drop probability)
        row["Unique"] = str(max(1, round(int(row["Unique"]) * unique_scale)))
        row["UniqueMin"] = str(max(128, round(int(row["UniqueMin"]) * unique_scale)))

        row["Set"] = str(max(1, round(int(row["Set"]) * set_scale)))
        row["SetMin"] = str(max(128, round(int(row["SetMin"]) * set_scale)))

        row["Rare"] = str(max(1, round(int(row["Rare"]) * rare_scale)))
        row["RareMin"] = str(max(128, round(int(row["RareMin"]) * rare_scale)))

        if zero_white:
            # D2R quality check: denom = Base - (ilvl - qlvl) / Divisor.
            # Using Divisor = 1000 (instead of 1) guarantees (ilvl - qlvl) / 1000 == 0 even when
            # ilvl < qlvl (e.g. Blood Moor mlvl 1 / Cold Plains mlvl 2 dropping qlvl 3 Hand Axes),
            # preventing negative division from inflating denom and leaking Cracked/White/Socketed drops!
            row["Magic"] = "1"
            row["MagicDivisor"] = "1000"
            row["MagicMin"] = "1"
            row["HiQuality"] = "1000000"
            row["HiQualityDivisor"] = "1000000"
            row["Normal"] = "1"
            row["NormalDivisor"] = "1000"

    return write_excel_tsv("itemratio.txt", headers, rows)

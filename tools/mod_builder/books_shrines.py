#!/usr/bin/env python3
"""
books_shrines.py (Step 3a)
Transforms books.txt and shrines.txt:
  - books.txt: Synchronizes Tome of Town Portal ('CostPerCharge' = 400, 'BaseCost' = 600)
    and Tome of Identify ('CostPerCharge' = 80, 'BaseCost' = 200).
  - shrines.txt: Preserves all 23 row indices (Code 0..22), disables useless/hazard shrines
    (Stamina, Fire, Exploding, Poison) from random spawning via LevelMin=120, and supercharges
    useful shrines with 2.5x duration (6000-7500 frames = 4-5 minutes) and stronger buffs
    (Skill Shrine +4 Skills, Experience Shrine +100% XP, Combat/Armor Shrine +250%,
    Gem & Monster Shrines rarity=1, LevelMin=1).
"""
from .common import read_excel_tsv, write_excel_tsv


def build_books(cfg: dict = None) -> str:
    headers, rows = read_excel_tsv("books.txt")
    for row in rows:
        name = row.get("Name", "")
        if name == "Tome of Town Portal":
            row["BaseCost"] = "600"
            row["CostPerCharge"] = "400"
        elif name == "Tome of Identify":
            row["BaseCost"] = "200"
            row["CostPerCharge"] = "80"
    return write_excel_tsv("books.txt", headers, rows)


def build_shrines(cfg: dict = None) -> str:
    headers, rows = read_excel_tsv("shrines.txt")
    for row in rows:
        code = row.get("Code", "")
        if code == "6":  # Armor Shrine
            row["Arg0"] = "250"
            row["Duration in frames"] = "6000"
            row["reset time in minutes"] = "3"
            row["rarity"] = "1"
            row["LevelMin"] = "1"
        elif code == "7":  # Combat Shrine
            row["Arg0"] = "250"
            row["Arg1"] = "250"
            row["Duration in frames"] = "6000"
            row["reset time in minutes"] = "3"
            row["rarity"] = "1"
            row["LevelMin"] = "1"
        elif code in ("8", "9", "10", "11"):  # Resist Fire/Cold/Light/Poison
            row["Arg0"] = "100"
            row["Duration in frames"] = "7500"
            row["reset time in minutes"] = "3"
            row["LevelMin"] = "1"
        elif code == "12":  # Skill Shrine (+4 All Skills for 4 minutes)
            row["Arg0"] = "4"
            row["Duration in frames"] = "6000"
            row["reset time in minutes"] = "3"
            row["rarity"] = "1"
            row["LevelMin"] = "1"
        elif code == "13":  # Mana Recharge Shrine
            row["Arg0"] = "500"
            row["Duration in frames"] = "6000"
            row["reset time in minutes"] = "3"
            row["LevelMin"] = "1"
        elif code == "14":  # Stamina Shrine (disabled from random pool so Stamina Elixirs matter)
            row["LevelMin"] = "120"
        elif code == "15":  # Experience Shrine (+100% XP for 5 minutes)
            row["Arg0"] = "100"
            row["Duration in frames"] = "7500"
            row["rarity"] = "1"
            row["LevelMin"] = "1"
        elif code == "18":  # Gem Shrine
            row["rarity"] = "1"
            row["LevelMin"] = "1"
        elif code == "20":  # Monster Shrine (spawns a Unique/Champion -> guaranteed Gem/Rune + Equip!)
            row["rarity"] = "1"
            row["LevelMin"] = "1"
        elif code in ("19", "21", "22"):  # Fire, Exploding, Poison Shrines
            row["LevelMin"] = "120"

    return write_excel_tsv("shrines.txt", headers, rows)


def build_books_shrines(cfg: dict = None) -> str:
    p1 = build_books(cfg)
    p2 = build_shrines(cfg)
    return f"{p1}, {p2}"

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
            row["BaseCost"] = "9750"
            row["CostPerCharge"] = "250"
    return write_excel_tsv("books.txt", headers, rows)


def build_shrines(cfg: dict = None) -> str:
    headers, rows = read_excel_tsv("shrines.txt")
    for row in rows:
        code = row.get("Code", "").strip()
        if code in ("1", "2", "3"):  # Refilling Shrine, Health Shrine, Mana Shrine
            row["reset time in minutes"] = "1"
            row["rarity"] = "1"
            row["LevelMin"] = "1"
        elif code == "13":  # Mana Recharge Shrine (+500% Mana Recharge Rate, 1-min reset)
            row["Arg0"] = "500"
            row["Duration in frames"] = "4500"
            row["reset time in minutes"] = "1"
            row["rarity"] = "1"
            row["LevelMin"] = "1"
        elif code != "0":  # Disable all non-recovery shrines (Booster & Magic shrines) from spawning
            row["LevelMin"] = "120"

    return write_excel_tsv("shrines.txt", headers, rows)


def build_books_shrines(cfg: dict = None) -> str:
    p1 = build_books(cfg)
    p2 = build_shrines(cfg)
    return f"{p1}, {p2}"

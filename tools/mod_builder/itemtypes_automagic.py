#!/usr/bin/env python3
"""
itemtypes_automagic.py
Step 5: Build itemtypes.txt and automagic.txt:
- Enable sockets on Javelins (jave, ajav) and Throwing Weapons (tkni, taxe):
  MaxSockets1 = 2, MaxSockets2 = 3, MaxSockets3 = 3
- Enable Magic & Rare Quivers on bowq (Arrows) and xboq (Bolts):
  Magic = "", Rare = "1", Normal = "0", AutoStack = "0"
- Add group 307 (Self-Replenishing, rep-quant = 10) to automagic.txt and also add
  mod2code = rep-quant (10) to group 302 rows so Amazon Javelins (am5, ama, amf)
  and all generic Throwing Weapons (group 307) automatically replenish stack quantity!
"""
from typing import Dict, List

from mod_builder.common import read_excel_tsv, write_excel_tsv


def build_itemtypes(cfg: dict) -> str:
    headers, rows = read_excel_tsv("itemtypes.txt")
    by_code = {r["Code"]: r for r in rows if r.get("Code")}

    # 1. Enable sockets on Javelins (jave, ajav) and Throwing Knives/Axes (tkni, taxe)
    for tcode in ("tkni", "taxe", "jave", "ajav"):
        if tcode in by_code:
            row = by_code[tcode]
            row["MaxSockets1"] = "2"
            row["MaxSocketsLevelThreshold1"] = "25"
            row["MaxSockets2"] = "3"
            row["MaxSocketsLevelThreshold2"] = "40"
            row["MaxSockets3"] = "3"

    # 2. Enable Magic-only Quivers on bowq and xboq (Normal=0, Magic="", Rare="":
    # vendors still sell Normal white quivers via CharsiMin/Max, while monster drops roll Magic-only)
    for qcode in ("bowq", "xboq"):
        if qcode in by_code:
            row = by_code[qcode]
            row["Magic"] = ""
            row["Rare"] = ""
            row["Normal"] = "0"
            row["AutoStack"] = "0"

    # 3. Add dedicated 'malu' item type for Blacksmith's Malus (bml) so it can be gambled in gamble.txt
    # without inheriting from 'weap' (preventing monsters from ever dropping it in Weap TCs).
    if "malu" not in by_code and "hamm" in by_code:
        malu = dict(by_code["hamm"])
        malu["ItemType"] = "Malus"
        malu["Code"] = "malu"
        malu["Equiv1"] = ""
        malu["Equiv2"] = ""
        malu["Body"] = "0"
        malu["BodyLoc1"] = ""
        malu["BodyLoc2"] = ""
        malu["Magic"] = "1"
        malu["Rare"] = "1"
        malu["Normal"] = "0"
        malu["MaxSockets1"] = "0"
        malu["MaxSockets2"] = "0"
        malu["MaxSockets3"] = "0"
        rows.append(malu)

    # 4. Add Crafting Slot Umbrella ItemTypes ('gljw' for Gloves/Ring/Amulet and 'btbl' for Boots/Belt)
    # so cubemain.txt can evaluate 'gljw' and 'btbl' before the 'armo' catch-all!
    if "gljw" not in by_code and "misc" in by_code:
        gljw = dict(by_code["misc"])
        gljw["ItemType"] = "Glove or Jewelry"
        gljw["Code"] = "gljw"
        gljw["Equiv1"] = ""
        gljw["Equiv2"] = ""
        rows.append(gljw)
    for c in ("glov", "ring", "amul"):
        if c in by_code:
            by_code[c]["Equiv2"] = "gljw"

    if "btbl" not in by_code and "armo" in by_code:
        btbl = dict(by_code["armo"])
        btbl["ItemType"] = "Boots or Belt"
        btbl["Code"] = "btbl"
        btbl["Equiv1"] = "armo"
        btbl["Equiv2"] = ""
        rows.append(btbl)
    for c in ("boot", "belt"):
        if c in by_code:
            by_code[c]["Equiv2"] = "btbl"

    return write_excel_tsv("itemtypes.txt", headers, rows)


def build_automagic(cfg: dict) -> str:
    headers, rows = read_excel_tsv("automagic.txt")

    # 1. Add rep-quant (10 = 1 every 10s) as mod2 on group 302 (Amazon Javelins / Spears)
    # Note: on Amazon Spears (which aren't stackable), rep-quant is a harmless no-op,
    # or we can scope group 302 / add group 307 for generic throwing weapons.
    for r in rows:
        if r.get("group") == "302":
            r["mod2code"] = "rep-quant"
            r["mod2param"] = "10"
            r["mod2min"] = ""
            r["mod2max"] = ""

    # 2. Add group 307 row for generic Throwing Weapons (jave, tkni, taxe)
    base_row = dict(rows[0])
    for k in headers:
        base_row[k] = ""
    base_row["Name"] = "Fletcher's"  # Uses existing valid affix string key in item-nameaffixes.json
    base_row["version"] = "100"
    base_row["spawnable"] = "1"
    base_row["rare"] = "1"
    base_row["level"] = "1"
    base_row["levelreq"] = "1"
    base_row["frequency"] = "1"
    base_row["group"] = "307"
    base_row["mod1code"] = "rep-quant"
    base_row["mod1param"] = "10"
    base_row["itype1"] = "thro"
    base_row["itype2"] = "misl"
    base_row["multiply"] = "0"
    base_row["add"] = "0"

    rows.append(base_row)
    return write_excel_tsv("automagic.txt", headers, rows)


def build_itemtypes_automagic(cfg: dict) -> str:
    p1 = build_itemtypes(cfg)
    p2 = build_automagic(cfg)
    return f"{p1}, {p2}"

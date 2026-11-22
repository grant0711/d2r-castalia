#!/usr/bin/env python3
"""
weapons_armor.py
Step 6: Build weapons.txt, armor.txt, and missiles.txt (plus HD item asset and string updates):
- Exaggerated weapon archetype StrBonus / DexBonus, speed (1.5x), 2-handed 1.65x damage bonus,
  and signature damage spreads (1-High on Axes/Flails, 85%-115% on Blunt/Crossbows, 60%-140% on Swords)
- Bow (1.70x) & Crossbow (2.60x high-floor) damage scaling
- Socketable (up to 3 sockets), auto-replenishing, non-destructible Throwing Weapons & Javelins (2.0x missile damage)
- 3-Tier Tactical Crowd-Control Alchemical Grenades (opl/opm/ops Concussion Bombs & gpl/gpm/gps Choking Miasmas)
- Exaggerated Light (0.85x AC, 0 spd) / Medium (1.45x AC, 12 spd) / Heavy (2.20x AC, 22 spd, +10 shield block) Armor
- Dedicated non-spawnable (spawnable=0) base weapons & armors for 4-Tier Valkyrie & Shadow Warrior/Master loadouts
"""
from typing import Dict, List, Tuple

from mod_builder.common import (
    read_excel_tsv,
    update_mod_hd_items_json,
    update_mod_strings_json,
    write_excel_tsv,
)

VENDORS = [
    "Charsi", "Gheed", "Akara", "Fara", "Lysander", "Drognan",
    "Hratli", "Alkor", "Ormus", "Elzix", "Asheara", "Cain",
    "Halbu", "Malah", "Larzuk", "Anya", "Jamella",
]


def _clear_vendors(row: Dict[str, str]) -> None:
    for v in VENDORS:
        if f"{v}Min" in row:
            row[f"{v}Min"] = ""
        if f"{v}Max" in row:
            row[f"{v}Max"] = ""
        if f"{v}MagicMin" in row:
            row[f"{v}MagicMin"] = ""
        if f"{v}MagicMax" in row:
            row[f"{v}MagicMax"] = ""
        if f"{v}MagicLvl" in row:
            row[f"{v}MagicLvl"] = "255"


def _set_vendor_stock(row: Dict[str, str], vendor_list: List[str], vmin: str = "1", vmax: str = "1") -> None:
    for v in vendor_list:
        row[f"{v}Min"] = vmin
        row[f"{v}Max"] = vmax


def _set_vendor_magic(row: Dict[str, str], vendor_list: List[str], mmin: str = "0", mmax: str = "1", mlvl: str = "1") -> None:
    for v in vendor_list:
        if f"{v}MagicMin" in row:
            row[f"{v}MagicMin"] = mmin
        if f"{v}MagicMax" in row:
            row[f"{v}MagicMax"] = mmax
        if f"{v}MagicLvl" in row:
            row[f"{v}MagicLvl"] = mlvl


# Strictly partitioned Act 1..5 Normal base item codes (code == normcode), plus curated
# Caster Attire & 12-Act Circlet Progression across Akara, Drognan, Ormus, Jamella & Malah.
# Each entry maps base_code -> List[(vendor_name, magic_min, magic_max)].
ARMOR_VENDOR_BY_CODE: Dict[str, List[Tuple[str, str, str]]] = {
    # === ACT 1: Charsi (Convent Blacksmith) vs. Gheed (Caravaneer, Outlaw & Class Broker) ===
    # Note: Akara has NO armor in Act 1 Normal (she unlocks Circlets starting in Nightmare!).
    # Charsi: Standard Armor, Caps & Shields (6 bases x 1..2 = ~9 items)
    "qui": [("Charsi", "1", "2")],
    "hla": [("Charsi", "1", "2")],
    "cap": [("Charsi", "1", "2")],
    "skp": [("Charsi", "1", "2")],
    "buc": [("Charsi", "1", "2")],
    "sml": [("Charsi", "1", "2")],
    # Gheed: Rogue Leather/Studded Gear, Gloves/Boots/Belts & All Act 1 Class-Specific Armor (10 bases x 1..2 = ~15 items)
    "lea": [("Gheed", "1", "2")],
    "stu": [("Gheed", "1", "2")],
    "lgl": [("Gheed", "1", "2")],
    "lbt": [("Gheed", "1", "2")],
    "lbl": [("Gheed", "1", "2")],
    "dr1": [("Gheed", "1", "2")],
    "ba1": [("Gheed", "1", "2")],
    "pa1": [("Gheed", "1", "2")],
    "ne1": [("Gheed", "1", "2")],
    "wa1": [("Gheed", "1", "2")],

    # === ACT 2: Fara (Templar Armorer) | Elzix (Outlaw & Class Broker) | Drognan (Bone Helms & Bone Shields) ===
    "rng": [("Fara", "1", "2")],
    "scl": [("Fara", "1", "2")],
    "chn": [("Fara", "1", "2")],
    "brs": [("Fara", "1", "2")],
    "hlm": [("Fara", "1", "2")],
    "fhl": [("Fara", "1", "2")],
    "lrg": [("Fara", "1", "2")],
    "spk": [("Fara", "1", "2")],
    "vgl": [("Fara", "1", "2")],
    "vbt": [("Fara", "1", "2")],
    "vbl": [("Fara", "1", "2")],
    "pa2": [("Fara", "1", "2")],
    # Elzix: Outlaw & Exotic Class-Specific Relics/Totems (4 bases x 1..2 = ~6 items)
    "dr2": [("Elzix", "1", "2")],
    "ba2": [("Elzix", "1", "2")],
    "ne2": [("Elzix", "1", "2")],
    "wa2": [("Elzix", "1", "2")],
    # Drognan: Exclusively Bone Helms & Bone Shields (2..3 of each -> Grim Helm / Grim Shield -> Bone Visage / Troll Nest)
    "bhm": [("Drognan", "2", "3")],

    # === ACT 3: Hratli (Forged Plate) | Asheara (Class Commander) | Ormus (Masks & Bone Shields) ===
    "spl": [("Hratli", "1", "2")],
    "plt": [("Hratli", "1", "2")],
    "kit": [("Hratli", "1", "2")],
    "mgl": [("Hratli", "1", "2")],
    "mbt": [("Hratli", "1", "2")],
    "mbl": [("Hratli", "1", "2")],
    # Asheara: Act 3 Class-Specific Armor & Totems (5 bases x 1..2 = ~7-8 items, down from 20!)
    "dr3": [("Asheara", "1", "2")],
    "ba3": [("Asheara", "1", "2")],
    "pa3": [("Asheara", "1", "2")],
    "ne3": [("Asheara", "1", "2")],
    "wa3": [("Asheara", "1", "2")],
    # Bone Shield (bsh): Drognan (2..3) & Ormus (2..3)
    "bsh": [("Drognan", "2", "3"), ("Ormus", "2", "3")],
    # Mask (msk): Ormus (2..3) & Jamella (1..2)
    "msk": [("Ormus", "2", "3"), ("Jamella", "1", "2")],

    # === ACT 4: Halbu (Fortress Weaponsmith) | Jamella (Light Plates, Masks, Circlets & Esoteric Relics) ===
    "fld": [("Halbu", "1", "2")],
    "gth": [("Halbu", "1", "2")],
    "ghm": [("Halbu", "1", "2")],
    "tow": [("Halbu", "1", "2")],
    "tgl": [("Halbu", "1", "2")],
    "tbt": [("Halbu", "1", "2")],
    "tbl": [("Halbu", "1", "2")],
    "ba4": [("Halbu", "1", "2")],
    "pa4": [("Halbu", "1", "2")],
    # Light Plate (ltp): Jamella (1..2) & Malah (1..2) -> Mage Plate -> Archon Plate
    "ltp": [("Jamella", "1", "2"), ("Malah", "1", "2")],
    "dr4": [("Jamella", "1", "2")],
    "ne4": [("Jamella", "1", "2")],
    "wa4": [("Jamella", "1", "2")],

    # === ACT 5: Larzuk (Siege Blacksmith) | Anya (Exotic Class Broker) | Malah (Light Plates & Circlets) ===
    "ful": [("Larzuk", "1", "2")],
    "aar": [("Larzuk", "1", "2")],
    "crn": [("Larzuk", "1", "2")],
    "gts": [("Larzuk", "1", "2")],
    "hgl": [("Larzuk", "1", "2")],
    "hbt": [("Larzuk", "1", "2")],
    "hbl": [("Larzuk", "1", "2")],
    "ba5": [("Larzuk", "1", "2")],
    "pa5": [("Larzuk", "1", "2")],
    "dr5": [("Anya", "1", "2")],
    "ne5": [("Anya", "1", "2")],
    "wa5": [("Anya", "1", "2")],

    # === 12-ACT ARCANE CIRCLET PROGRESSION (Starting in Act 4 Normal across all 5 Arcane Vendors) ===
    # Note on D2Game.dll Normal shop ilvl caps:
    #   Act 1 = 12, Act 2 = 20, Act 3 = 28, Act 4 = 36, Act 5 = uncapped (clvl + 5).
    # - ci0 (Circlet, qlvl=30 -> NightmareUpgrade=ci1 Coronet, HellUpgrade=ci2 Tiara):
    #     * Normal Act 1-3 (shop ilvl cap <= 28 < 30): 0 Circlets (strictly blocked in Normal Act 1-3!)
    #     * Normal Act 4 Jamella (shop ilvl cap 36 >= 30): 0..1 Circlet (Entry point: max 1!)
    #     * Normal Act 5 Malah (clvl >= 25 -> ilvl >= 30): 0..1 Circlet (+ 0..1 Coronet below = 0..2 total)
    #     * Nightmare Akara/Drognan/Ormus/Jamella/Malah:   upgrades to Coronet (ci1, qlvl=39)
    #     * Hell Akara/Drognan/Ormus/Jamella/Malah:        upgrades to Tiara (ci2, qlvl=60)
    "ci0": [
        ("Akara", "0", "1"),
        ("Drognan", "0", "1"),
        ("Ormus", "1", "2"),
        ("Jamella", "0", "1"),
        ("Malah", "0", "1"),
    ],
    # - ci1 (Coronet, qlvl=39 -> NightmareUpgrade=ci2 Tiara, HellUpgrade=ci3 Diadem):
    #     * Normal Act 1-4 (shop ilvl cap <= 36 < 39): 0 Coronets (strictly blocked in Normal Act 1-4!)
    #     * Normal Act 5 Malah (clvl >= 34 -> ilvl >= 39): 0..1 Coronet (combined with ci0 -> 0..2 total)
    #     * Nightmare Act 1-5 Arcane Vendors: upgrades to Tiara (ci2, qlvl=52), scaling total to 1..3
    #     * Hell Act 1-5 Arcane Vendors: upgrades to Diadem (ci3), scaling total to 2..4 in Act 4/5 Hell!
    "ci1": [
        ("Akara", "0", "1"),
        ("Drognan", "1", "1"),
        ("Ormus", "0", "1"),
        ("Jamella", "1", "2"),
        ("Malah", "0", "1"),
    ],
    # - ci2 (Tiara, qlvl=52 -> NightmareUpgrade=xxx, HellUpgrade=ci3 Diadem):
    #     * Normal & Early Nightmare (clvl < 47 -> ilvl < 52): 0 Tiaras
    #     * Mid/Late Nightmare & Hell Jamella/Malah (clvl >= 47): adds +0..1 Tiara (NM) / +0..1 Diadem (Hell),
    #       bringing Jamella & Malah up to 1..4 (up to 4 max) Circlet-family items in late NM & Hell!
    "ci2": [
        ("Jamella", "0", "1"),
        ("Malah", "0", "1"),
    ],
}

WEAPON_VENDOR_BY_CODE: Dict[str, Tuple[str, str, str]] = {
    # === ACT 1: Charsi (Martial Melee) | Gheed (Ranged, Thrown, Rogue & Claws) | Akara (Caster) ===
    "hax": ("Charsi", "1", "2"),
    "lax": ("Charsi", "1", "2"),
    "ssd": ("Charsi", "1", "2"),
    "scm": ("Charsi", "1", "2"),
    "sbr": ("Charsi", "1", "2"),
    "clb": ("Charsi", "1", "2"),
    "spc": ("Charsi", "1", "2"),
    "spr": ("Charsi", "1", "2"),
    "bar": ("Charsi", "1", "2"),
    "dgr": ("Gheed", "1", "2"),
    "sbw": ("Gheed", "1", "2"),
    "hbw": ("Gheed", "1", "2"),
    "lxb": ("Gheed", "1", "2"),
    "jav": ("Gheed", "1", "2"),
    "tkf": ("Gheed", "1", "2"),
    "ktr": ("Gheed", "1", "2"),
    "sst": ("Akara", "3", "6"),
    "wnd": ("Akara", "3", "6"),
    "scp": ("Akara", "3", "6"),
    "ob1": ("Akara", "3", "6"),

    # === ACT 2: Fara (Templar Melee) | Elzix (Ranged, Thrown, Outlaw & Claws) | Drognan (Caster) ===
    "axe": ("Fara", "1", "2"),
    "bax": ("Fara", "1", "2"),
    "flc": ("Fara", "1", "2"),
    "crs": ("Fara", "1", "2"),
    "2hs": ("Fara", "1", "2"),
    "mac": ("Fara", "1", "2"),
    "mst": ("Fara", "1", "2"),
    "tri": ("Fara", "1", "2"),
    "vou": ("Fara", "1", "2"),
    "dir": ("Elzix", "1", "2"),
    "lbw": ("Elzix", "1", "2"),
    "cbw": ("Elzix", "1", "2"),
    "mxb": ("Elzix", "1", "2"),
    "pil": ("Elzix", "1", "2"),
    "tax": ("Elzix", "1", "2"),
    "bkf": ("Elzix", "1", "2"),
    "wrb": ("Elzix", "1", "2"),
    "axf": ("Elzix", "1", "2"),
    "lst": ("Drognan", "3", "6"),
    "ywn": ("Drognan", "3", "6"),
    "ob2": ("Drognan", "3", "6"),

    # === ACT 3: Hratli (Forged Melee) | Asheara (Ranged, Thrown, Amazon & Claws) | Ormus (Caster) ===
    "2ax": ("Hratli", "1", "2"),
    "btx": ("Hratli", "1", "2"),
    "bsd": ("Hratli", "1", "2"),
    "lsd": ("Hratli", "1", "2"),
    "clm": ("Hratli", "1", "2"),
    "fla": ("Hratli", "1", "2"),
    "brn": ("Hratli", "1", "2"),
    "scy": ("Hratli", "1", "2"),
    "kri": ("Asheara", "1", "2"),
    "sbb": ("Asheara", "1", "2"),
    "am1": ("Asheara", "1", "2"),
    "am3": ("Asheara", "1", "2"),
    "ssp": ("Asheara", "1", "2"),
    "bal": ("Asheara", "1", "2"),
    "ces": ("Asheara", "1", "2"),
    "clw": ("Asheara", "1", "2"),
    "cst": ("Ormus", "3", "6"),
    "bwn": ("Ormus", "3", "6"),
    "gsc": ("Ormus", "3", "6"),
    "ob3": ("Ormus", "3", "6"),

    # === ACT 4: Halbu (Martial Melee, Bows & Thrown) | Jamella (Caster, Claws & Amazon Javelins) ===
    "mpi": ("Halbu", "1", "2"),
    "gax": ("Halbu", "1", "2"),
    "gis": ("Halbu", "1", "2"),
    "bsw": ("Halbu", "1", "2"),
    "wsd": ("Halbu", "1", "2"),
    "mau": ("Halbu", "1", "2"),
    "whm": ("Halbu", "1", "2"),
    "bld": ("Halbu", "1", "2"),
    "spt": ("Halbu", "1", "2"),
    "pax": ("Halbu", "1", "2"),
    "lbb": ("Halbu", "1", "2"),
    "swb": ("Halbu", "1", "2"),
    "hxb": ("Halbu", "1", "2"),
    "glv": ("Halbu", "1", "2"),
    "am5": ("Jamella", "1", "2"),
    "btl": ("Jamella", "1", "2"),
    "bst": ("Jamella", "3", "6"),
    "wsp": ("Jamella", "3", "6"),
    "ob4": ("Jamella", "3", "6"),

    # === ACT 5: Larzuk (Siege Melee) | Anya (Ranged, Thrown, Amazon & Claws) | Malah (Caster) ===
    "wax": ("Larzuk", "1", "2"),
    "gix": ("Larzuk", "1", "2"),
    "flb": ("Larzuk", "1", "2"),
    "gsd": ("Larzuk", "1", "2"),
    "gma": ("Larzuk", "1", "2"),
    "pik": ("Larzuk", "1", "2"),
    "hal": ("Larzuk", "1", "2"),
    "wsc": ("Larzuk", "1", "2"),
    "lwb": ("Anya", "1", "2"),
    "am2": ("Anya", "1", "2"),
    "am4": ("Anya", "1", "2"),
    "rxb": ("Anya", "1", "2"),
    "tsp": ("Anya", "1", "2"),
    "skr": ("Anya", "1", "2"),
    "wst": ("Malah", "3", "6"),
    "gwn": ("Malah", "3", "6"),
    "ob5": ("Malah", "3", "6"),
}


def _spread_bounds(avg: float, low_pct: float, high_pct: float) -> Tuple[str, str]:
    lo = max(1, int(round(avg * low_pct)))
    hi = max(lo + 1, int(round(avg * high_pct)))
    if hi > 255:
        lo = max(1, min(254, int(round(2.0 * avg - 255.0))))
        hi = 255
    return str(lo), str(hi)


def _scale_pair(row: Dict[str, str], min_col: str, max_col: str, mult: float, low_pct: float, high_pct: float) -> None:
    if not row.get(min_col) or not row.get(max_col):
        return
    vmin = int(row[min_col])
    vmax = int(row[max_col])
    avg = ((vmin + vmax) / 2.0) * mult
    lo, hi = _spread_bounds(avg, low_pct, high_pct)
    row[min_col] = lo
    row[max_col] = hi


def _scale_axe_pair(row: Dict[str, str], min_col: str, max_col: str, mult: float) -> None:
    """
    Scale Axe damage with a wide ~1:5 min-to-max spread (33.8% to 166.2% of scaled average)
    anchored so the highest-damage Axe in the game (Decapitator, 7bt, avg=153.45) hits
    exactly 255 max damage (52-255) and every other Axe scales proportionally below 255.
    """
    if not row.get(min_col) or not row.get(max_col):
        return
    vmin = int(row[min_col])
    vmax = int(row[max_col])
    avg = ((vmin + vmax) / 2.0) * mult
    high_pct = 255.0 / 153.45  # 1.661779... -> Decapitator (avg 153.45) = 255 max
    low_pct = 2.0 - high_pct   # 0.338221... -> preserves 100% of scaled average damage
    lo, hi = _spread_bounds(avg, low_pct, high_pct)
    row[min_col] = lo
    row[max_col] = hi


def _scale_flail_pair(row: Dict[str, str], min_col: str, max_col: str, mult: float) -> None:
    if not row.get(min_col) or not row.get(max_col):
        return
    vmin = int(row[min_col])
    vmax = int(row[max_col])
    avg = ((vmin + vmax) / 2.0) * mult
    hi = min(255, max(3, int(round(2.0 * avg - 1.0))))
    row[min_col] = "1"
    row[max_col] = str(hi)


def _compute_normalized_base_cost(level: int, slot_weight: float, stack_divisor: int = 1) -> str:
    """
    Smoothly curve weapon and armor base cost by qlvl (1..85) and slot_weight (1.0 for 2H/Body Armor,
    0.75 for 1H/Helm/Shield/Class, 0.60 for Gloves/Boots/Belt) so Normal -> Exceptional -> Elite
    Magic vendor items progress cleanly and apex Hell vendor rolls top out around ~300,000 Gold.
    """
    lvl = max(1, min(85, level))
    t = (lvl - 1) / 84.0
    raw = (160.0 + 6200.0 * t + 43640.0 * (t ** 2.35)) * slot_weight
    if stack_divisor > 1:
        return str(max(2, int(round(raw / stack_divisor))))
    return str(max(25, int(round(raw))))


def build_weapons(cfg: dict) -> str:
    headers, rows = read_excel_tsv("weapons.txt")
    rows_by_code = {r["code"]: r for r in rows if r.get("code")}

    # Alchemical Grenades stocked exclusively at each Act's Alchemist/Mystic
    alchemists = ["Akara", "Lysander", "Alkor", "Jamella", "Malah"]

    for row in rows:
        code = row.get("code", "")
        wtype = row.get("type", "")
        if not code or not wtype:
            continue

        # 1. Alchemical Grenades (tpot: opl, opm, ops, gpl, gpm, gps)
        if wtype == "tpot":
            _clear_vendors(row)
            row["PermStoreItem"] = "1"
            row["maxstack"] = "5"
            row["spawnstack"] = "5"
            row["minstack"] = "5"
            if code == "opl":
                row["name"] = "Minor Concussion Bomb"
                row["cost"] = "300"
                row["minmisdam"] = "1"
                row["maxmisdam"] = "3"
                _set_vendor_stock(row, alchemists, "1", "1")
                row["NightmareUpgrade"] = "opm"
                row["HellUpgrade"] = "ops"
            elif code == "opm":
                row["name"] = "Greater Concussion Bomb"
                row["cost"] = "1200"
                row["minmisdam"] = "8"
                row["maxmisdam"] = "15"
                row["NightmareUpgrade"] = "xxx"
                row["HellUpgrade"] = "ops"
            elif code == "ops":
                row["name"] = "Supreme Concussion Bomb"
                row["cost"] = "4000"
                row["minmisdam"] = "25"
                row["maxmisdam"] = "45"
                row["NightmareUpgrade"] = "xxx"
                row["HellUpgrade"] = "xxx"
            elif code == "gpl":
                row["name"] = "Minor Choking Miasma"
                row["cost"] = "300"
                row["minmisdam"] = "1"
                row["maxmisdam"] = "3"
                _set_vendor_stock(row, alchemists, "1", "1")
                row["NightmareUpgrade"] = "gpm"
                row["HellUpgrade"] = "gps"
            elif code == "gpm":
                row["name"] = "Greater Choking Miasma"
                row["cost"] = "1200"
                row["minmisdam"] = "8"
                row["maxmisdam"] = "14"
                row["NightmareUpgrade"] = "xxx"
                row["HellUpgrade"] = "gps"
            elif code == "gps":
                row["name"] = "Supreme Choking Miasma"
                row["cost"] = "4000"
                row["minmisdam"] = "25"
                row["maxmisdam"] = "40"
                row["NightmareUpgrade"] = "xxx"
                row["HellUpgrade"] = "xxx"
            continue

        # Skip quest-only non-spawnable items (Horadric Staff, Khalim's Will, Decoy Gidbinn, etc.)
        if row.get("spawnable") != "1":
            _clear_vendors(row)
            continue

        # 1b. Strictly partitioned Act 1..5 Magic-only vendor stocking & ubercode/ultracode upgrades
        _clear_vendors(row)
        if code == row.get("normcode"):
            uber = row.get("ubercode", "")
            ultra = row.get("ultracode", "")
            row["NightmareUpgrade"] = uber if (uber and uber != code) else "xxx"
            row["HellUpgrade"] = ultra if (ultra and ultra != code) else "xxx"
            v_spec = WEAPON_VENDOR_BY_CODE.get(code)
            if v_spec is not None:
                v_name, m_min, m_max = v_spec
                _set_vendor_magic(row, [v_name], m_min, m_max, "1")
        else:
            row["NightmareUpgrade"] = "xxx"
            row["HellUpgrade"] = "xxx"

        # 2. Exaggerate non-zero weapon speed by 1.5x (clamped to [-60, 40])
        if row.get("speed"):
            spd = int(row["speed"])
            if spd != 0:
                new_spd = max(-60, min(40, int(round(spd * 1.5))))
                row["speed"] = str(new_spd)

        is_2h = row.get("2handed") == "1"
        is_1or2h = row.get("1or2handed") == "1"

        # 2b. Bump close-range melee weapons (rangeadder 0 -> 1, 1 -> 2) so 1H melee never whiffs at range 0
        if wtype not in ("bow", "abow", "xbow", "spea", "aspe", "pole", "jave", "ajav"):
            cur_ra = int(row.get("rangeadder") or "0")
            if cur_ra <= 1:
                row["rangeadder"] = str(cur_ra + 1)

        # 3. Archetype StrBonus / DexBonus & Damage Spreads
        if wtype == "hamm":
            if is_2h:
                row["StrBonus"] = "250"
                row["DexBonus"] = ""
                _scale_pair(row, "2handmindam", "2handmaxdam", 1.65, 0.85, 1.15)
            else:
                row["StrBonus"] = "175"
                row["DexBonus"] = ""
                _scale_pair(row, "mindam", "maxdam", 1.15, 0.85, 1.15)

        elif wtype == "axe":
            if is_2h:
                row["StrBonus"] = "220"
                row["DexBonus"] = ""
                _scale_axe_pair(row, "2handmindam", "2handmaxdam", 1.65)
            else:
                row["StrBonus"] = "175"
                row["DexBonus"] = ""
                _scale_axe_pair(row, "mindam", "maxdam", 1.15)

        elif wtype in ("mace", "club", "scep"):
            row["StrBonus"] = "175"
            row["DexBonus"] = ""
            if code in ("fla", "9fl", "7fl"):
                _scale_flail_pair(row, "mindam", "maxdam", 1.15)
            else:
                _scale_pair(row, "mindam", "maxdam", 1.15, 0.85, 1.15)

        elif wtype == "swor":
            if is_1or2h or is_2h:
                row["1or2handed"] = ""
                row["mindam"] = ""
                row["maxdam"] = ""
                row["wclass"] = "2hs"
                row["StrBonus"] = "160"
                row["DexBonus"] = "100"
                _scale_pair(row, "2handmindam", "2handmaxdam", 1.60, 0.60, 1.40)
            else:
                row["StrBonus"] = "125"
                row["DexBonus"] = "100"
                _scale_pair(row, "mindam", "maxdam", 1.10, 0.60, 1.40)

        elif wtype == "knif":
            row["StrBonus"] = "25"
            row["DexBonus"] = "225"
            _scale_pair(row, "mindam", "maxdam", 1.15, 0.70, 1.30)

        elif wtype in ("spea", "aspe"):
            row["StrBonus"] = "130"
            row["DexBonus"] = "130"
            row["rangeadder"] = "5" if code in ("pik", "9p9", "7p7") else "4"
            _scale_pair(row, "2handmindam", "2handmaxdam", 1.65, 0.65, 1.35)

        elif wtype == "pole":
            row["StrBonus"] = "200"
            row["DexBonus"] = "40"
            row["rangeadder"] = "4"
            _scale_pair(row, "2handmindam", "2handmaxdam", 1.65, 0.50, 1.50)

        elif wtype == "staf":
            row["StrBonus"] = "150"
            row["DexBonus"] = ""
            _scale_pair(row, "2handmindam", "2handmaxdam", 1.65, 0.80, 1.20)

        elif wtype in ("h2h", "h2h2"):
            row["StrBonus"] = "110"
            row["DexBonus"] = "110"
            _scale_pair(row, "mindam", "maxdam", 1.20, 0.65, 1.35)

        elif wtype in ("bow", "abow"):
            row["StrBonus"] = ""
            row["DexBonus"] = "250"
            _scale_pair(row, "2handmindam", "2handmaxdam", 1.70, 0.55, 1.45)

        elif wtype == "xbow":
            row["StrBonus"] = "160"
            row["DexBonus"] = "160"
            _scale_pair(row, "2handmindam", "2handmaxdam", 2.60, 0.85, 1.15)

        elif wtype in ("jave", "ajav", "tkni", "taxe"):
            ilvl = int(row.get("level") or "1")
            if code == row.get("normcode"):
                # Normal tier: 1.0x in Act 1 Blood Moor (lvl <= 7) ramping to 1.35x by Act 4/5 (lvl 29)
                if ilvl <= 7:
                    mis_mult = 1.00
                    mel_mult = 1.00
                else:
                    t = min(1.0, (ilvl - 7) / 22.0)
                    mis_mult = 1.05 + 0.30 * t
                    mel_mult = 1.05 + 0.15 * t
            elif code == row.get("ubercode"):
                # Exceptional tier (Nightmare): 1.50x ramping to 1.80x
                t = min(1.0, max(0.0, (ilvl - 30) / 21.0))
                mis_mult = 1.50 + 0.30 * t
                mel_mult = 1.25 + 0.15 * t
            else:
                # Elite tier (Hell): 1.95x ramping to 2.25x
                t = min(1.0, max(0.0, (ilvl - 54) / 31.0))
                mis_mult = 1.95 + 0.30 * t
                mel_mult = 1.40 + 0.15 * t

            row["nodurability"] = "1"
            row["hasinv"] = "1"
            row["gemsockets"] = "3"
            row["gemapplytype"] = "0"

            if code == row.get("normcode"):
                j_spawn, j_max = "25", "40"
                k_spawn, k_max = "35", "50"
                a_spawn, a_max = "30", "45"
            elif code == row.get("ubercode"):
                j_spawn, j_max = "45", "65"
                k_spawn, k_max = "55", "80"
                a_spawn, a_max = "50", "70"
            else:
                j_spawn, j_max = "65", "90"
                k_spawn, k_max = "80", "110"
                a_spawn, a_max = "70", "100"

            if wtype in ("jave", "ajav"):
                row["StrBonus"] = "50"
                row["DexBonus"] = "220"
                row["rangeadder"] = "3" if code in ("glv", "9gl", "7gl", "tsp", "9ts", "7ts") else "2"
                _scale_pair(row, "mindam", "maxdam", mel_mult, 0.65, 1.35)
                _scale_pair(row, "minmisdam", "maxmisdam", mis_mult, 0.65, 1.35)
                row["maxstack"] = j_max
                row["spawnstack"] = j_spawn
                if wtype == "jave":
                    row["auto prefix"] = "307"
                elif wtype == "ajav":
                    row["auto prefix"] = "308"
            elif wtype == "tkni":
                row["StrBonus"] = "25"
                row["DexBonus"] = "225"
                _scale_pair(row, "mindam", "maxdam", mel_mult, 0.70, 1.30)
                _scale_pair(row, "minmisdam", "maxmisdam", mis_mult, 0.70, 1.30)
                row["maxstack"] = k_max
                row["spawnstack"] = k_spawn
                row["auto prefix"] = "307"
            elif wtype == "taxe":
                row["StrBonus"] = "175"
                row["DexBonus"] = ""
                _scale_axe_pair(row, "mindam", "maxdam", mel_mult)
                _scale_axe_pair(row, "minmisdam", "maxmisdam", mis_mult)
                row["maxstack"] = a_max
                row["spawnstack"] = a_spawn
                row["auto prefix"] = "307"

        # 3b. Attach automagic 'skill-rand' staffmod groups (310=sor, 311=nec, 312=pal, 315=ass)
        weapon_staffmod_group = {
            "staf": "310",
            "wand": "311",
            "scep": "312",
            "h2h": "315",
            "h2h2": "315",
        }
        if wtype in weapon_staffmod_group:
            row["auto prefix"] = weapon_staffmod_group[wtype]

        # Tag all 2-handed melee weapons with type2='2hml' and all strictly 1-handed melee weapons with type2='1hml'
        # so skills and masteries (One-Handed Mastery, Two-Handed Mastery, Desperate Berserk) cleanly partition 1H vs. 2H!
        if (is_2h or is_1or2h) and wtype in ("swor", "axe", "hamm", "pole", "spea", "staf", "aspe"):
            row["type2"] = "2hml"
        elif not is_2h and not is_1or2h and wtype in ("swor", "axe", "mace", "club", "hamm", "scep", "knif", "wand", "orb", "h2h", "h2h2"):
            row["type2"] = "1hml"

        # 3c. Scale weapon durability by 2x (clamped to 255 save-bit limit) so per-point weapon
        #     repair cost is half that of armor against npc.txt rep mult = 768
        w_dur = int(row.get("durability") or "0")
        if w_dur > 0 and row.get("nodurability") != "1":
            row["durability"] = str(min(255, w_dur * 2))

        # 3d. Normalize weapon base cost by progression level (1..85) and slot weight
        w_lvl = int(row.get("level") or "1")
        if wtype in ("jave", "ajav", "tkni", "taxe"):
            s_div = max(1, int(row.get("maxstack") or "25"))
            row["cost"] = _compute_normalized_base_cost(w_lvl, 0.75, stack_divisor=s_div)
        else:
            w_slot_weight = 1.0 if (is_2h or is_1or2h) else 0.75
            row["cost"] = _compute_normalized_base_cost(w_lvl, w_slot_weight)

    # 4. Add Blacksmith's Malus (bml) to weapons.txt so gamble.txt finds normcode/ubercode/ultracode
    # and D2R HD graphics resolves weapon/hammer/horadric_malus cleanly!
    bml = dict(rows_by_code["whm"])
    bml["name"] = "Blacksmith's Malus"
    bml["type"] = "malu"
    bml["code"] = "bml"
    bml["alternategfx"] = "whm"
    bml["namestr"] = "bml"
    bml["version"] = "100"
    bml["compactsave"] = "0"
    bml["rarity"] = "0"
    bml["spawnable"] = "1"
    bml["mindam"] = "1"
    bml["maxdam"] = "2"
    bml["reqstr"] = "0"
    bml["reqdex"] = "0"
    bml["durability"] = "20"
    bml["nodurability"] = "1"
    bml["level"] = "1"
    bml["levelreq"] = "0"
    bml["cost"] = "2500"
    bml["gamble cost"] = ""
    bml["normcode"] = "bml"
    bml["ubercode"] = "bml"
    bml["ultracode"] = "bml"
    bml["invwidth"] = "1"
    bml["invheight"] = "2"
    bml["flippyfile"] = "flphmr"
    bml["invfile"] = "invhmr"
    bml["uniqueinvfile"] = "invhmr"
    bml["setinvfile"] = "invhmr"
    bml["hasinv"] = "0"
    bml["gemsockets"] = "0"
    bml["NightmareUpgrade"] = "xxx"
    bml["HellUpgrade"] = "xxx"
    _clear_vendors(bml)
    rows.append(bml)

    # 4b. Add Untempered Malus (um1) to weapons.txt:
    # - Sold ONLY by Charsi as a permanent White item (CharsiMin=1, CharsiMax=1, PermStoreItem=1)
    #   for 100,000 Gold in Normal, Nightmare, and Hell (PermStoreItem=1 prevents the ilvl >= 25
    #   vendor Magic-forcing rule from turning it into a Magic item in NM/Hell).
    # - Because it is the ONLY White weapon/armor in the entire mod (and type='umal' inherits from 'weap'
    #   with Rare=1), it is the ONLY item accepted by Charsi's "Temper Malus" (Imbue) quest reward!
    # - Tempering it at Charsi transforms it into a Rare Malus (um1,rar), which can then be transmuted
    #   with any Normal or Exceptional Weapon/Armor (Magic, Rare, Set, Unique, or Crafted) to upgrade its
    #   base tier (Normal -> Exceptional -> Elite), strictly capped at 3 upgrades per character playthrough!
    um1 = dict(bml)
    um1["name"] = "Untempered Malus"
    um1["type"] = "umal"
    um1["code"] = "um1"
    um1["namestr"] = "um1"
    um1["level"] = "1"
    um1["cost"] = "100000"
    um1["normcode"] = "xxx"
    um1["ubercode"] = "xxx"
    um1["ultracode"] = "um1"
    um1["PermStoreItem"] = "1"
    um1["NightmareUpgrade"] = "xxx"
    um1["HellUpgrade"] = "xxx"
    _clear_vendors(um1)
    um1["CharsiMin"] = "1"
    um1["CharsiMax"] = "1"
    rows.append(um1)

    # 5. Add Dedicated Summon-Only Base Weapons (spawnable=0) for Valkyrie & Shadow Warrior/Master
    summon_weapons = [
        # (new_code, template_code, name)
        ("vk1", "spr", "Valkyrie Bronze Spear"),
        ("vk2", "9sr", "Valkyrie Waravelin"),
        ("vk3", "9p9", "Valkyrie Halberd Lance"),
        ("vk4", "7p7", "Valkyrie Archon Pike"),
        ("sw1", "ces", "Shadow Initiate Katar"),
        ("sw2", "9ar", "Shadow Adept Quhab"),
        ("sw3", "7ar", "Shadow Master Suwayyah"),
        ("sw4", "7qr", "Shadow Grandmaster Scissors"),
        ("so1", "btl", "Shadow Initiate Blade Talons"),
        ("so2", "9cs", "Shadow Adept Hand Scythe"),
        ("so3", "7cs", "Shadow Master Battle Cestus"),
        ("so4", "7tw", "Shadow Grandmaster Runic Talons"),
    ]
    for new_code, tmpl_code, wname in summon_weapons:
        wrow = dict(rows_by_code[tmpl_code])
        wrow["name"] = wname
        wrow["code"] = new_code
        wrow["namestr"] = new_code
        wrow["spawnable"] = "0"
        wrow["rarity"] = "0"
        wrow["level"] = "1"
        wrow["levelreq"] = "1"
        wrow["normcode"] = new_code
        wrow["ubercode"] = new_code
        wrow["ultracode"] = new_code
        _clear_vendors(wrow)
        rows.append(wrow)

    return write_excel_tsv("weapons.txt", headers, rows)


def build_armor(cfg: dict) -> str:
    headers, rows = read_excel_tsv("armor.txt")
    rows_by_code = {r["code"]: r for r in rows if r.get("code")}

    for row in rows:
        if row.get("spawnable") != "1":
            _clear_vendors(row)
            continue
        code = row.get("code", "")
        atype = row.get("type", "")
        _clear_vendors(row)
        if code == "bhm":
            # Lower Bone Helm qlvl from 22 -> 18 so Drognan in Act 2 Normal (shop ilvl cap = 20) can spawn it!
            row["level"] = "18"
            row["NightmareUpgrade"] = "xh9"
            row["HellUpgrade"] = "uh9"
        elif code == "ci0":
            # Circlet (qlvl=30, levelreq=16, magic lvl=3 -> blocked in Act 1-3 Normal [cap<=28], first spawns in Act 4 Normal [cap=36];
            # upgrades to Coronet in NM and Tiara in Hell)
            row["level"] = "30"
            row["levelreq"] = "16"
            row["NightmareUpgrade"] = "ci1"
            row["HellUpgrade"] = "ci2"
        elif code == "ci1":
            # Coronet (qlvl=39, levelreq=32, magic lvl=8 -> blocked in Act 1-4 Normal [cap<=36], first spawns in Act 5 Normal;
            # upgrades to Tiara in NM and Diadem in Hell)
            row["level"] = "39"
            row["levelreq"] = "32"
            row["NightmareUpgrade"] = "ci2"
            row["HellUpgrade"] = "ci3"
        elif code == "ci2":
            # Tiara (qlvl=52, levelreq=46, magic lvl=13 -> first spawns in NM; upgrades to Diadem in Hell)
            row["level"] = "52"
            row["levelreq"] = "46"
            row["NightmareUpgrade"] = "xxx"
            row["HellUpgrade"] = "ci3"
        elif code == "ci3":
            # Diadem (qlvl=64, levelreq=60, magic lvl=18 -> spawns via HellUpgrade on ci1/ci2 in Hell Act 1-5)
            row["level"] = "64"
            row["levelreq"] = "60"
            row["NightmareUpgrade"] = "xxx"
            row["HellUpgrade"] = "xxx"
        elif code == row.get("normcode"):
            uber = row.get("ubercode", "")
            ultra = row.get("ultracode", "")
            row["NightmareUpgrade"] = uber if (uber and uber != code) else "xxx"
            row["HellUpgrade"] = ultra if (ultra and ultra != code) else "xxx"
        else:
            row["NightmareUpgrade"] = "xxx"
            row["HellUpgrade"] = "xxx"

        v_specs = ARMOR_VENDOR_BY_CODE.get(code)
        if v_specs is not None:
            for v_name, m_min, m_max in v_specs:
                _set_vendor_magic(row, [v_name], m_min, m_max, "1")
        spd = row.get("speed", "0")
        minac = int(row["minac"]) if row.get("minac") else 0
        maxac = int(row["maxac"]) if row.get("maxac") else 0

        # Promote Ancient Armor / Ornate Plate / Sacred Armor (highest Str body armor line) to Heavy (speed=10)
        if code in ("aar", "xar", "uar"):
            spd = "10"

        if atype == "tors":
            if spd == "10":
                row["minac"] = str(max(1, int(round(minac * 2.20))))
                row["maxac"] = str(max(2, int(round(maxac * 2.20))))
                row["speed"] = "15"
                row["type2"] = "htor"
            elif spd == "5":
                row["minac"] = str(max(1, int(round(minac * 1.45))))
                row["maxac"] = str(max(2, int(round(maxac * 1.45))))
                row["speed"] = "8"
                row["type2"] = "mtor"
            else:
                row["minac"] = str(max(1, int(round(minac * 0.85))))
                row["maxac"] = str(max(2, int(round(maxac * 0.85))))
                row["speed"] = "0"
                row["type2"] = "ltor"

        # 3-Tier Weight Class Progression for Shields (shie & ashd):
        # Light (spd=0): low AC, modest lower Block Chance (14%-24%), +15% Faster Block Rate (auto prefix 316 / 318)
        # Medium (spd=5): medium-high AC, balanced Block Chance (18%-28%), neutral Block Rate (no auto / 304)
        # Heavy (spd=10/12): massive AC, modest higher Block Chance (24%-30%), -15% Faster Block Rate (auto prefix 317 / 319)
        # Smite damage is aligned between Standard & Paladin Shields (Light < Med < Heavy),
        # while Spiked Shield (10-18) / Barbed Shield (32-60) / Blade Barrier (58-92) lead as #1 Smite shields!
        shield_specs = {
            # Light Shields (spd=0, auto=316)
            "buc": ("0", "14", 1.10, (3, 7), "316"),   "xuc": ("0", "16", 1.10, (13, 21), "316"), "uuc": ("0", "18", 1.05, (30, 50), "316"),
            "sml": ("0", "16", 1.10, (3, 7), "316"),   "xml": ("0", "18", 1.10, (13, 21), "316"), "uml": ("0", "20", 1.05, (30, 50), "316"),
            "bsh": ("0", "18", 1.00, (3, 7), "316"),   "xsh": ("0", "20", 1.00, (13, 21), "316"), "ush": ("0", "22", 1.00, (30, 50), "316"),
            # Medium Shields (spd=5, auto="")
            "lrg": ("5", "20", 1.55, (4, 9), ""),      "xrg": ("5", "22", 1.55, (17, 25), ""),    "urg": ("5", "24", 1.55, (34, 54), ""),
            "kit": ("5", "20", 1.55, (4, 9), ""),      "xit": ("5", "22", 1.55, (17, 25), ""),    "uit": ("5", "24", 1.55, (34, 54), ""),
            "spk": ("5", "18", 1.55, (10, 18), ""),    "xpk": ("5", "20", 1.55, (32, 60), ""),    "upk": ("5", "22", 1.55, (58, 92), ""),
            # Heavy Shields (spd=10..12, auto=317)
            "gts": ("10", "24", 2.40, (5, 11), "317"), "xts": ("10", "26", 2.40, (22, 32), "317"), "uts": ("10", "28", 2.40, (38, 58), "317"),
            "tow": ("12", "26", 2.75, (5, 11), "317"), "xow": ("12", "28", 2.75, (22, 32), "317"), "uow": ("12", "30", 2.75, (38, 58), "317"),
            # Paladin Shields (ashd): Light=318 (+15% FBR), Med=304 (neutral), Heavy=319 (-15% FBR)
            "pa1": ("0", "18", 1.05, (3, 7), "318"),   "pa6": ("0", "20", 1.05, (13, 21), "318"), "pab": ("0", "22", 1.05, (30, 50), "318"),
            "pa2": ("0", "20", 1.10, (3, 7), "318"),   "pa7": ("0", "22", 1.10, (13, 21), "318"), "pac": ("0", "24", 1.10, (30, 50), "318"),
            "pa3": ("5", "22", 1.55, (4, 9), "304"),   "pa8": ("5", "24", 1.55, (17, 25), "304"), "pad": ("5", "26", 1.55, (34, 54), "304"),
            "pa4": ("5", "24", 1.65, (4, 9), "304"),   "pa9": ("5", "26", 1.65, (17, 25), "304"), "pae": ("5", "28", 1.65, (34, 54), "304"),
            "pa5": ("10", "26", 2.35, (5, 11), "319"), "paa": ("10", "28", 2.35, (22, 32), "319"), "paf": ("10", "30", 2.35, (38, 58), "319"),
        }
        if code in shield_specs:
            s_spd, s_blk, s_ac_mult, s_smite, s_auto = shield_specs[code]
            row["speed"] = s_spd
            row["block"] = s_blk
            row["minac"] = str(max(1, int(round(minac * s_ac_mult))))
            row["maxac"] = str(max(2, int(round(maxac * s_ac_mult))))
            row["auto prefix"] = s_auto
            if s_smite is not None:
                row["mindam"] = str(s_smite[0])
                row["maxdam"] = str(s_smite[1])
            if atype == "shie":
                row["type2"] = "lshi" if s_spd == "0" else ("mshi" if s_spd == "5" else "hshi")
            elif atype == "ashd":
                row["type2"] = "lash" if s_spd == "0" else ("mash" if s_spd == "5" else "hash")

        # Helms & Circlets Weight/Defense/Strength & Enclosed Vision (auto prefix 320 / 321) Progression:
        helm_specs = {
            # Circlets (Ultralight: spd=0, 0 Str)
            "ci0": ("0", "0", 15, 25, ""), "ci1": ("0", "0", 22, 32, ""), "ci2": ("0", "0", 30, 42, ""), "ci3": ("0", "0", 40, 55, ""),
            # Light Helms (spd=0; Mask line has -2 Light Radius via group 320)
            "cap": ("0", "0", 4, 7, ""), "xap": ("0", "20", 42, 52, ""), "uap": ("0", "50", 85, 110, ""),
            "skp": ("0", "15", 9, 13, ""), "xkp": ("0", "43", 50, 62, ""), "ukp": ("0", "84", 100, 130, ""),
            "msk": ("0", "20", 12, 22, "320"), "xsk": ("0", "50", 54, 74, "320"), "usk": ("0", "90", 105, 135, "320"),
            "bhm": ("0", "25", 24, 30, ""), "xh9": ("0", "58", 68, 90, ""), "uh9": ("0", "100", 120, 150, ""),
            # Medium Helms (spd=3..4; Full Helm line has -2 Light Radius via group 320)
            "hlm": ("3", "30", 18, 24, ""), "xlm": ("3", "68", 82, 100, ""), "ulm": ("3", "120", 170, 210, ""),
            "fhl": ("4", "45", 28, 36, "320"), "xhl": ("4", "90", 105, 128, "320"), "uhl": ("4", "148", 215, 265, "320"),
            # Heavy Helms (spd=6; Great/Winged/Spired Helm line has -3 Light Radius via group 321)
            "crn": ("6", "60", 38, 50, ""), "xrn": ("6", "115", 130, 160, ""), "urn": ("6", "174", 270, 330, ""),
            "ghm": ("6", "70", 45, 58, "321"), "xhm": ("6", "130", 150, 185, "321"), "uhm": ("6", "192", 310, 380, "321"),
        }
        if code in helm_specs:
            h_spd, h_str, h_minac, h_maxac, h_auto = helm_specs[code]
            row["speed"] = h_spd
            row["reqstr"] = h_str
            row["minac"] = str(h_minac)
            row["maxac"] = str(h_maxac)
            row["auto prefix"] = h_auto

        # Assign secondary Bone Caster Armor type tags via 'type2' ('bhlm' -> 'bcas', 'bshd' -> 'bcas')
        # while keeping primary 'type' as 'helm' / 'shie' so D2R's 3D shield/helm attachment orientation is untouched!
        if code in ("bhm", "xh9", "uh9", "msk", "xsk", "usk"):
            row["type2"] = "bhlm"
        elif code in ("bsh", "xsh", "ush"):
            row["type2"] = "bshd"
        elif code in ("ltp", "xtp", "utp"):
            row["type2"] = "ctor"

        # Gloves (glov) 5-Tier Light -> Heavy Progression:
        glove_specs = {
            "lgl": ("0", "0", 3, 5), "xlg": ("0", "20", 25, 32), "ulg": ("0", "45", 45, 55),
            "vgl": ("0", "12", 6, 9), "xvg": ("0", "30", 33, 42), "uvg": ("0", "60", 60, 75),
            "mgl": ("2", "28", 12, 16), "xmg": ("2", "60", 52, 65), "umg": ("2", "106", 100, 122),
            "tgl": ("3", "48", 19, 25), "xtg": ("3", "90", 74, 90), "utg": ("3", "148", 140, 170),
            "hgl": ("5", "70", 28, 36), "xhg": ("5", "125", 105, 130), "uhg": ("5", "185", 195, 240),
        }
        if code in glove_specs:
            g_spd, g_str, g_minac, g_maxac = glove_specs[code]
            row["speed"] = g_spd
            row["reqstr"] = g_str
            row["minac"] = str(g_minac)
            row["maxac"] = str(g_maxac)
            row["type2"] = "lglv" if g_spd == "0" else ("mglv" if g_spd in ("2", "3") else "hglv")

        # Boots (boot) 5-Tier Light -> Heavy Progression (Defense, Speed, Str & Kick Damage):
        boot_specs = {
            "lbt": ("0", "0", 3, 5, 3, 8), "xlb": ("0", "20", 25, 32, 22, 38), "ulb": ("0", "45", 45, 55, 50, 80),
            "vbt": ("0", "18", 6, 9, 5, 11), "xvb": ("0", "42", 33, 42, 28, 48), "uvb": ("0", "70", 60, 75, 65, 105),
            "mbt": ("2", "32", 12, 16, 8, 15), "xmb": ("2", "65", 52, 65, 35, 60), "umb": ("2", "115", 100, 122, 85, 135),
            "tbt": ("3", "52", 19, 25, 12, 22), "xtb": ("3", "95", 74, 90, 45, 78), "utb": ("3", "155", 140, 170, 110, 175),
            "hbt": ("5", "75", 28, 36, 18, 32), "xhb": ("5", "130", 105, 130, 60, 105), "uhb": ("5", "195", 195, 240, 145, 230),
        }
        if code in boot_specs:
            bt_spd, bt_str, bt_minac, bt_maxac, bt_mindm, bt_maxdm = boot_specs[code]
            row["speed"] = bt_spd
            row["reqstr"] = bt_str
            row["minac"] = str(bt_minac)
            row["maxac"] = str(bt_maxac)
            row["mindam"] = str(bt_mindm)
            row["maxdam"] = str(bt_maxdm)
            row["type2"] = "lbot" if bt_spd == "0" else ("mbot" if bt_spd in ("2", "3") else "hbot")

        # Attach automagic 'skill-rand' staffmod groups:
        # 313=open Barb Helms, 322=enclosed Barb Helms (ba4/ba5 lines: -2 Light Radius),
        # 314=open Druid Pelts, 323=enclosed Druid Pelts (dr4/dr5 lines: -2 Light Radius)
        norm = row.get("normcode", "")
        if atype == "phlm":
            row["auto prefix"] = "322" if norm in ("ba4", "ba5") else "313"
        elif atype == "pelt":
            row["auto prefix"] = "323" if norm in ("dr4", "dr5") else "314"

        # Enforce 4 / 8 / 12 Belt Slot Progression, Strength, Speed & Defense across Normal, NM, and Hell:
        belt_progression_specs = {
            "lbl": ("2", "0", "0", 3, 5),
            "zlb": ("2", "20", "0", 25, 32),
            "ulc": ("2", "50", "0", 45, 55),
            "vbl": ("2", "0", "0", 6, 9),
            "zvb": ("2", "20", "0", 32, 40),
            "uvc": ("2", "50", "0", 60, 72),
            "mbl": ("1", "35", "2", 12, 16),
            "zmb": ("1", "65", "2", 50, 62),
            "umc": ("1", "106", "2", 95, 115),
            "tbl": ("1", "50", "3", 18, 24),
            "ztb": ("1", "88", "3", 70, 86),
            "utc": ("1", "145", "3", 135, 165),
            "hbl": ("0", "100", "5", 28, 36),
            "zhb": ("0", "140", "5", 100, 125),
            "uhc": ("0", "185", "5", 190, 235),
        }
        if code in belt_progression_specs:
            b_idx, b_str, b_spd, b_minac, b_maxac = belt_progression_specs[code]
            row["belt"] = b_idx
            row["reqstr"] = b_str
            row["speed"] = b_spd
            row["minac"] = str(b_minac)
            row["maxac"] = str(b_maxac)

        # Normalize armor base cost by progression level (1..85) and slot weight
        a_lvl = int(row.get("level") or "1")
        if atype == "tors":
            a_slot_weight = 1.0
        elif atype in ("glov", "boot", "belt"):
            a_slot_weight = 0.60
        else:
            a_slot_weight = 0.75
        row["cost"] = _compute_normalized_base_cost(a_lvl, a_slot_weight)

    # Add Dedicated Summon-Only Base Armors (spawnable=0) for Valkyrie & Shadow Warrior/Master
    summon_armors = [
        ("va1", "ful", "Valkyrie Bronze Cuirass"),
        ("va2", "xpl", "Valkyrie Battle Harness"),
        ("va3", "xul", "Valkyrie Templar Plate"),
        ("va4", "uar", "Valkyrie Archon Aegis"),
        ("vh1", "ci0", "Valkyrie Initiate Circlet"),
        ("vh2", "ci1", "Valkyrie War Coronet"),
        ("vh3", "ci2", "Valkyrie Golden Tiara"),
        ("vh4", "ci3", "Valkyrie Divine Diadem"),
        ("sa1", "stu", "Shadow Initiate Brigandine"),
        ("sa2", "xtu", "Shadow Adept Trellised Mail"),
        ("sa3", "utu", "Shadow Master Wire Fleece"),
        ("sa4", "uar", "Shadow Grandmaster Shroud"),
        ("sh1", "msk", "Shadow Initiate Guise"),
        ("sh2", "xsk", "Shadow Adept Death Mask"),
        ("sh3", "ci2", "Shadow Master Crest"),
        ("sh4", "ci3", "Shadow Grandmaster Crown"),
    ]
    for new_code, tmpl_code, aname in summon_armors:
        arow = dict(rows_by_code[tmpl_code])
        arow["type2"] = ""
        arow["name"] = aname
        arow["code"] = new_code
        arow["namestr"] = new_code
        arow["spawnable"] = "0"
        arow["rarity"] = "0"
        arow["level"] = "1"
        arow["levelreq"] = "1"
        arow["normcode"] = new_code
        arow["ubercode"] = new_code
        arow["ultracode"] = new_code
        _clear_vendors(arow)
        rows.append(arow)

    return write_excel_tsv("armor.txt", headers, rows)


def build_missiles(cfg: dict) -> str:
    headers, rows = read_excel_tsv("missiles.txt")
    rows_by_id = {r["*ID"]: r for r in rows if r.get("*ID")}

    # Enable ApplyMastery = 1 on all 6 throwing potion missiles and 3 gas clouds
    for mid in ("44", "45", "46", "47", "48", "49", "222", "223", "224"):
        rows_by_id[mid]["ApplyMastery"] = "1"

    # Orange Flasks: Concussion Bombs (Knockback + Native 'stun' Elemental State + Light Blast)
    # 44 = oilpotion (fired by opl, Tier 1 Normal)
    # 45 = explosivepotion (fired by opm, Tier 2 Nightmare)
    # 46 = fulminatingpotion (fired by ops, Tier 3 Hell)
    orange_specs = [
        ("44", "4", "50", "1", "3"),
        ("45", "5", "75", "8", "15"),
        ("46", "6", "100", "25", "45"),
    ]
    for mid, radius, stun_len, dmg_min, dmg_max in orange_specs:
        r = rows_by_id[mid]
        r["sHitPar1"] = radius
        r["pCltHitFunc"] = "1"
        r["cHitPar1"] = radius
        r["cHitPar2"] = "1"
        r["ExplosionMissile"] = "explodingarrowexp"
        r["CltHitSubMissile1"] = "fireexplosion2"
        r["KnockBack"] = "100"
        r["pSrvDmgFunc"] = "7"
        r["dParam1"] = stun_len
        r["ProgOverlay"] = "doubledamage1"
        r["MinDamage"] = dmg_min
        r["MaxDamage"] = dmg_max
        r["EType"] = "stun"
        r["EMin"] = "1"
        r["EMax"] = "2"
        r["ELen"] = stun_len
        r["GetHit"] = "1"

    # Green Flasks: Choking Miasmas (Compact Icy Blue/White Frost Mist + Chill + Hit-Recovery Stagger)
    # 47 + 222 = rancidgasepotion + rancidgascloud (fired by gpl, Tier 1 Normal)
    # 48 + 223 = chokinggaspoition + chokinggascloud (fired by gpm, Tier 2 Nightmare)
    # 49 + 224 = stranglinggaspotion + stranglinggascloud (fired by gps, Tier 3 Hell)
    green_specs = [
        ("47", "222", "1", "65", "1", "75", "1", "2", "35"),
        ("48", "223", "1", "90", "2", "110", "8", "14", "50"),
        ("49", "224", "2", "115", "2", "150", "25", "40", "75"),
    ]
    for pot_id, cloud_id, hit_rad, cloud_rng, cloud_sz, chill_len, emin, emax, kb in green_specs:
        pot = rows_by_id[pot_id]
        pot["sHitPar1"] = hit_rad
        pot["cHitPar1"] = hit_rad
        pot["ExplosionMissile"] = "freezingarrowexp1"
        pot["HitSound"] = "sorceress_iceblast_impact_1"
        pot["EType"] = "cold"
        pot["ELen"] = chill_len
        pot["EMin"] = emin
        pot["EMax"] = emax
        pot["KnockBack"] = kb
        pot["GetHit"] = "1"

        cloud = rows_by_id[cloud_id]
        cloud["Range"] = cloud_rng
        cloud["Size"] = cloud_sz
        cloud["Red"] = "81"
        cloud["Green"] = "140"
        cloud["Blue"] = "255"
        cloud["CelFile"] = "ChillBloodPuff"
        cloud["AnimLen"] = "26"
        cloud["NumDirections"] = "1"
        cloud["SubLoop"] = ""
        cloud["SubStart"] = ""
        cloud["SubStop"] = ""
        cloud["TravelSound"] = "druid_arcticblast_1"
        cloud["CltSubMissile1"] = "chillbloodpuff"
        cloud["EType"] = "cold"
        cloud["ELen"] = chill_len
        cloud["EMin"] = emin
        cloud["EMax"] = emax
        cloud["KnockBack"] = kb
        cloud["GetHit"] = "1"

    rows_by_name = {r["Missile"]: r for r in rows if r.get("Missile")}
    from mod_builder.skills import apply_skill_missile_updates

    apply_skill_missile_updates(rows_by_name, rows)

    from mod_builder.sorc import engine as sorc_engine

    sorc_engine.apply_table_patches("missiles.txt", headers, rows)
    return write_excel_tsv("missiles.txt", headers, rows)


def build_weapons_armor_assets_and_strings(cfg: dict) -> Tuple[str, str]:
    hd_additions = [
        ("um1", "hammer/horadric_malus"),
        ("vk1", "spear/spear"),
        ("vk2", "spear/spear"),
        ("vk3", "spear/pike"),
        ("vk4", "spear/pike"),
        ("sw1", "h2h/hatchet_hands"),
        ("sw2", "h2h/katar"),
        ("sw3", "h2h/katar"),
        ("sw4", "h2h/scissors_katar"),
        ("so1", "h2h/claws"),
        ("so2", "h2h/hatchet_hands"),
        ("so3", "h2h/hatchet_hands"),
        ("so4", "h2h/claws"),
        ("va1", "armor/full_plate_mail"),
        ("va2", "armor/field_plate"),
        ("va3", "armor/full_plate_mail"),
        ("va4", "armor/ancient_armor"),
        ("vh1", "circlet/circlet"),
        ("vh2", "circlet/coronet"),
        ("vh3", "circlet/tiara"),
        ("vh4", "circlet/diadem"),
        ("sa1", "armor/studded_leather"),
        ("sa2", "armor/studded_leather"),
        ("sa3", "armor/studded_leather"),
        ("sa4", "armor/ancient_armor"),
        ("sh1", "helm/mask"),
        ("sh2", "helm/mask"),
        ("sh3", "circlet/tiara"),
        ("sh4", "circlet/diadem"),
    ]
    hd_path = update_mod_hd_items_json(hd_additions)

    string_updates = [
        (61995, "um1", "Untempered Malus"),
        (0, "opl", "Minor Concussion Bomb"),
        (0, "opm", "Greater Concussion Bomb"),
        (0, "ops", "Supreme Concussion Bomb"),
        (0, "gpl", "Minor Choking Miasma"),
        (0, "gpm", "Greater Choking Miasma"),
        (0, "gps", "Supreme Choking Miasma"),
        (60025, "vk1", "Valkyrie Bronze Spear"),
        (60026, "vk2", "Valkyrie Waravelin"),
        (60027, "vk3", "Valkyrie Halberd Lance"),
        (60028, "vk4", "Valkyrie Archon Pike"),
        (60029, "sw1", "Shadow Initiate Katar"),
        (60030, "sw2", "Shadow Adept Quhab"),
        (60031, "sw3", "Shadow Master Suwayyah"),
        (60032, "sw4", "Shadow Grandmaster Scissors"),
        (60033, "so1", "Shadow Initiate Blade Talons"),
        (60034, "so2", "Shadow Adept Hand Scythe"),
        (60035, "so3", "Shadow Master Battle Cestus"),
        (60036, "so4", "Shadow Grandmaster Runic Talons"),
        (60037, "va1", "Valkyrie Bronze Cuirass"),
        (60038, "va2", "Valkyrie Battle Harness"),
        (60039, "va3", "Valkyrie Templar Plate"),
        (60040, "va4", "Valkyrie Archon Aegis"),
        (60041, "vh1", "Valkyrie Initiate Circlet"),
        (60042, "vh2", "Valkyrie War Coronet"),
        (60043, "vh3", "Valkyrie Golden Tiara"),
        (60044, "vh4", "Valkyrie Divine Diadem"),
        (60045, "sa1", "Shadow Initiate Brigandine"),
        (60046, "sa2", "Shadow Adept Trellised Mail"),
        (60047, "sa3", "Shadow Master Wire Fleece"),
        (60048, "sa4", "Shadow Grandmaster Shroud"),
        (60049, "sh1", "Shadow Initiate Guise"),
        (60050, "sh2", "Shadow Adept Death Mask"),
        (60051, "sh3", "Shadow Master Crest"),
        (60052, "sh4", "Shadow Grandmaster Crown"),
    ]
    str_path = update_mod_strings_json("item-names.json", string_updates)
    return hd_path, str_path


def build_weapons_armor_all(cfg: dict) -> str:
    p1 = build_weapons(cfg)
    p2 = build_armor(cfg)
    p3 = build_missiles(cfg)
    p4, p5 = build_weapons_armor_assets_and_strings(cfg)
    return f"{p1}, {p2}, {p3}, {p4}, {p5}"

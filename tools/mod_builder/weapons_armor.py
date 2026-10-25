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


# Strictly partitioned Act 1..5 Normal base item codes (code == normcode).
# Each Act's vendors sell ONLY that Act's progression tier as Magic items (0-1 per refresh, ~50% full tabs),
# with NightmareUpgrade = ubercode and HellUpgrade = ultracode so Nightmare/Hell vendors upgrade cleanly
# within their Act's dedicated item slice (e.g., Hell Charsi -> Dusk Shroud/Wyrmhide; NM Larzuk -> Ornate Plate).
ARMOR_VENDORS_BY_ACT = {
    1: ["Charsi", "Gheed"],
    2: ["Fara", "Elzix"],
    3: ["Hratli", "Asheara"],
    4: ["Halbu", "Jamella"],
    5: ["Larzuk", "Anya"],
}

ARMOR_ACT_BY_CODE = {
    # Body Armor (tors, 15)
    "qui": 1, "lea": 1, "hla": 1, "stu": 1,
    "rng": 2, "scl": 2, "chn": 2, "brs": 2,
    "spl": 3, "plt": 3, "ltp": 3,
    "fld": 4, "gth": 4,
    "ful": 5, "aar": 5,
    # Helms (helm + circ, 10)
    "cap": 1, "skp": 1,
    "hlm": 2, "fhl": 2,
    "msk": 3, "bhm": 3,
    "ghm": 4, "ci0": 4,
    "crn": 5, "ci1": 5,
    # Shields (shie, 8)
    "buc": 1, "sml": 1,
    "lrg": 2, "spk": 2,
    "kit": 3, "bsh": 3,
    "tow": 4,
    "gts": 5,
    # Gloves (glov, 5)
    "lgl": 1, "vgl": 2, "mgl": 3, "tgl": 4, "hgl": 5,
    # Boots (boot, 5)
    "lbt": 1, "vbt": 2, "mbt": 3, "tbt": 4, "hbt": 5,
    # Belts (belt, 5)
    "lbl": 1, "vbl": 2, "mbl": 3, "tbl": 4, "hbl": 5,
    # Druid Pelts (pelt, 5)
    "dr1": 1, "dr2": 2, "dr3": 3, "dr4": 4, "dr5": 5,
    # Barbarian Primal Helms (phlm, 5)
    "ba1": 1, "ba2": 2, "ba3": 3, "ba4": 4, "ba5": 5,
    # Paladin Auric Shields (ashd, 5)
    "pa1": 1, "pa2": 2, "pa3": 3, "pa4": 4, "pa5": 5,
    # Necromancer Shrunken Heads (head, 5)
    "ne1": 1, "ne2": 2, "ne3": 3, "ne4": 4, "ne5": 5,
    # Grimoires (grim, 5)
    "wa1": 1, "wa2": 2, "wa3": 3, "wa4": 4, "wa5": 5,
}

PHYS_WEAPON_VENDORS_BY_ACT = {
    1: ["Charsi", "Gheed"],
    2: ["Fara", "Elzix"],
    3: ["Hratli", "Asheara"],
    4: ["Halbu"],
    5: ["Larzuk", "Anya"],
}

CASTER_WEAPON_VENDORS_BY_ACT = {
    1: ["Akara"],
    2: ["Drognan"],
    3: ["Ormus"],
    4: ["Jamella"],
    5: ["Malah"],
}

WEAPON_ACT_BY_CODE = {
    # Axes (axe, 10: 1x 1H + 1x 2H per Act)
    "hax": 1, "lax": 1,
    "axe": 2, "bax": 2,
    "2ax": 3, "btx": 3,
    "mpi": 4, "gax": 4,
    "wax": 5, "gix": 5,
    # Swords (swor, 14)
    "ssd": 1, "scm": 1, "sbr": 1,
    "flc": 2, "crs": 2, "2hs": 2,
    "bsd": 3, "lsd": 3, "clm": 3,
    "gis": 4, "bsw": 4, "wsd": 4,
    "flb": 5, "gsd": 5,
    # Clubs, Maces & Hammers (club + mace + hamm, 8)
    "clb": 1, "spc": 1,
    "mac": 2, "mst": 2,
    "fla": 3,
    "mau": 4, "whm": 4,
    "gma": 5,
    # Daggers (knif, 4)
    "dgr": 1, "dir": 2, "kri": 3, "bld": 4,
    # Spears & Amazon Spears (spea + aspe, 7)
    "spr": 1,
    "tri": 2,
    "brn": 3, "am3": 3,
    "spt": 4,
    "pik": 5, "am4": 5,
    # Polearms (pole, 6)
    "bar": 1,
    "vou": 2,
    "scy": 3,
    "pax": 4,
    "hal": 5, "wsc": 5,
    # Bows & Amazon Bows (bow + abow, 10)
    "sbw": 1, "hbw": 1,
    "lbw": 2, "cbw": 2,
    "sbb": 3, "am1": 3,
    "lbb": 4, "swb": 4,
    "lwb": 5, "am2": 5,
    # Crossbows (xbow, 4)
    "lxb": 1, "mxb": 2, "hxb": 4, "rxb": 5,
    # Javelins & Amazon Javelins (jave + ajav, 6)
    "jav": 1,
    "pil": 2,
    "ssp": 3,
    "glv": 4, "am5": 4,
    "tsp": 5,
    # Throwing Knives & Axes (tkni + taxe, 4)
    "tkf": 1,
    "tax": 2, "bkf": 2,
    "bal": 3,
    # Assassin Claws (h2h, 7)
    "ktr": 1,
    "wrb": 2, "axf": 2,
    "ces": 3, "clw": 3,
    "btl": 4,
    "skr": 5,
    # Caster Weapons: Staves (staf, 5), Wands (wand, 4), Scepters (scep, 3), Sorceress Orbs (orb, 5)
    "sst": 1, "wnd": 1, "scp": 1, "ob1": 1,
    "lst": 2, "ywn": 2, "ob2": 2,
    "cst": 3, "bwn": 3, "gsc": 3, "ob3": 3,
    "bst": 4, "wsp": 4, "ob4": 4,
    "wst": 5, "gwn": 5, "ob5": 5,
}


def _spread_bounds(avg: float, low_pct: float, high_pct: float) -> Tuple[str, str]:
    lo = max(1, int(round(avg * low_pct)))
    hi = max(lo + 1, int(round(avg * high_pct)))
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
    if not row.get(min_col) or not row.get(max_col):
        return
    vmin = int(row[min_col])
    vmax = int(row[max_col])
    avg = ((vmin + vmax) / 2.0) * mult
    hi = max(3, int(round(2.0 * avg - 1.0)))
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
            act_num = WEAPON_ACT_BY_CODE.get(code)
            if act_num is not None:
                v_list = (
                    CASTER_WEAPON_VENDORS_BY_ACT[act_num]
                    if wtype in ("staf", "wand", "scep", "orb")
                    else PHYS_WEAPON_VENDORS_BY_ACT[act_num]
                )
                _set_vendor_magic(row, v_list, "0", "1", "1")
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
                _scale_axe_pair(row, "mindam", "maxdam", 1.15)
            else:
                _scale_pair(row, "mindam", "maxdam", 1.15, 0.85, 1.15)

        elif wtype == "swor":
            if is_1or2h or is_2h:
                row["StrBonus"] = "160"
                row["DexBonus"] = "100"
                _scale_pair(row, "mindam", "maxdam", 1.10, 0.60, 1.40)
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

        # 3b. Normalize weapon base cost by progression level (1..85) and slot weight
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
    # - Sold ONLY by Charsi as a single depleting White item (CharsiMin=1, CharsiMax=1, PermStoreItem=0)
    #   for 100,000 Gold in Normal, Nightmare, and Hell.
    # - Setting level=1 ensures Charsi's Act 1 Normal shop (ilvl cap = 12) can spawn it, while
    #   HiQuality=1000000 in itemratio.txt guarantees it always rolls Normal (White) rather than Superior!
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
    um1["normcode"] = "um1"
    um1["ubercode"] = "um1"
    um1["ultracode"] = "um1"
    um1["PermStoreItem"] = "0"
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
        if code == row.get("normcode"):
            uber = row.get("ubercode", "")
            ultra = row.get("ultracode", "")
            row["NightmareUpgrade"] = uber if (uber and uber != code) else "xxx"
            row["HellUpgrade"] = ultra if (ultra and ultra != code) else "xxx"
            act_num = ARMOR_ACT_BY_CODE.get(code)
            if act_num is not None:
                _set_vendor_magic(row, ARMOR_VENDORS_BY_ACT[act_num], "0", "1", "1")
        else:
            row["NightmareUpgrade"] = "xxx"
            row["HellUpgrade"] = "xxx"
        spd = row.get("speed", "0")
        minac = int(row["minac"]) if row.get("minac") else 0
        maxac = int(row["maxac"]) if row.get("maxac") else 0

        if spd == "10":
            # Heavy Armor / Heavy Shield: 2.20x AC, speed = 15 (2.5x stamina drain), +10% block on shields
            row["minac"] = str(max(1, int(round(minac * 2.20))))
            row["maxac"] = str(max(2, int(round(maxac * 2.20))))
            row["speed"] = "15"
            if atype in ("shie", "ashd", "head") and row.get("block"):
                row["block"] = str(int(row["block"]) + 10)
        elif spd == "5":
            # Medium Armor / Medium Shield: 1.45x AC, speed = 8 (1.8x stamina drain)
            row["minac"] = str(max(1, int(round(minac * 1.45))))
            row["maxac"] = str(max(2, int(round(maxac * 1.45))))
            row["speed"] = "8"
        elif spd == "0" and atype in ("tors", "shie", "ashd", "head"):
            # Light Body Armor / Light Shield: 0.85x AC, speed = 0
            row["minac"] = str(max(1, int(round(minac * 0.85))))
            row["maxac"] = str(max(2, int(round(maxac * 0.85))))
            row["speed"] = "0"

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

    apply_skill_missile_updates(rows_by_name)

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

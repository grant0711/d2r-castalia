#!/usr/bin/env python3
"""
unique_sets.py
Step 8: Build runes.txt, uniqueitems.txt, setitems.txt, sets.txt (and item-names.json):
- Disable Runewords in runes.txt (complete = "")
- Remove nofreeze from all Uniques & Sets (only adding Cold Res if the item is already cold-themed)
- Apply gentle %ED floor to underperforming Normal/Exceptional Unique weapons without inflating top Uniques
- Enforce a strict 4-6 affix philosophy: never add affixes to items that already have >= 6 props;
  only on items with <= 5 props, deterministically curate thematic oskills (lvl 4-14), low-level auras (lvl 1-2),
  or procs matched to the item's existing theme
- Apply Kiss-Curse tradeoffs (negative light radius, +requirements, -FHR, -IAS, -damage resist, or -elemental resist)
  to overperforming items and high-oskill/aura items
- Modest Set item tuning (no runaway /lvl scaling)
- 13 New Historical & Mythological Unique Javelins (jav, pil, ssp, glv, tsp, am5, 9ja, 9pi, 9s9, 9gl, 9ts, 7ja, 7pi)
- 5 Act Boss 1x1 (cm1, carry1=1) Unique Charms
- 28 Non-Spawnable (spawnable=0, nolimit=1) 4-Tier Valkyrie & Shadow Warrior/Master Uniques for monequip.txt
"""
import hashlib
import os
import shutil
from typing import Dict, List, Tuple

from mod_builder.common import (
    MOD_EXCEL,
    read_excel_tsv,
    update_mod_strings_json,
    write_excel_tsv,
)

LOCKED_TABLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locked_tables")

SUNDER_NAMES = {
    "Bone Break",
    "Black Cleft",
    "Crack of the Heavens",
    "Cold Rupture",
    "Flame Rift",
    "Rotting Fissure",
}


def _det_int(seed_str: str, mod: int) -> int:
    h = hashlib.sha256(seed_str.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") % mod


def _get_props(row: Dict[str, str], max_slots: int = 12) -> List[Tuple[str, str, str, str]]:
    out = []
    for i in range(1, max_slots + 1):
        p = row.get(f"prop{i}", "").strip()
        if p:
            out.append((p, row.get(f"par{i}", ""), row.get(f"min{i}", ""), row.get(f"max{i}", "")))
    return out


def _set_props(row: Dict[str, str], props: List[Tuple[str, str, str, str]], max_slots: int = 12) -> None:
    for i in range(1, max_slots + 1):
        if i - 1 < len(props):
            p, par, mn, mx = props[i - 1]
            row[f"prop{i}"] = p
            row[f"par{i}"] = par
            row[f"min{i}"] = mn
            row[f"max{i}"] = mx
        else:
            row[f"prop{i}"] = ""
            row[f"par{i}"] = ""
            row[f"min{i}"] = ""
            row[f"max{i}"] = ""


def _detect_theme(props: List[Tuple[str, str, str, str]]) -> str:
    codes = {p[0] for p in props}
    if codes & {"dmg-fire", "fire-min", "fire-max", "res-fire", "pierce-fire", "extra-fire", "fireskill"}:
        return "fire"
    if codes & {"dmg-cold", "cold-min", "cold-max", "res-cold", "pierce-cold", "extra-cold", "freeze"}:
        return "cold"
    if codes & {"dmg-ltng", "ltng-min", "ltng-max", "res-ltng", "pierce-ltng", "extra-ltng"}:
        return "ltng"
    if codes & {"dmg-pois", "pois-min", "pois-max", "res-pois", "pierce-pois", "extra-pois"}:
        return "pois"
    if codes & {"cast1", "cast2", "cast3", "mana", "mana%", "regen-mana", "mag%"}:
        return "caster"
    if codes & {"crush", "openwounds", "deadly", "lifesteal", "dmg%", "att"}:
        return "phys"
    return "tank"


# Hand-curated, lore-matched additions for selected <=5-prop Uniques.
# Design invariants:
# - ZERO duplicate added oskills across the entire Unique item pool
# - ZERO duplicate added auras within the same equipment slot, and at most 2 items globally per aura (>=25 levels apart)
# - ZERO duplicate added procs within the same equipment slot & level bracket
# - Early utility/MF/mana rings (e.g. Nagelring, Manald Heal) and complete endgame items are left untouched
CURATED_UNIQUE_ADDITIONS: Dict[str, List[Tuple[str, str, str, str]]] = {
    # --- Curated Oskills (18 distinct skills, 1 item each + 2 distinct on new Javelins = 20 distinct oskills total) ---
    "Stoutnail": [("oskill", "Sacrifice", "4", "6")],
    "Dimoaks Hew": [("oskill", "Jab", "4", "6"), ("light", "", "-2", "-2")],
    "Deathspade": [("oskill", "Cleave", "4", "6"), ("light", "", "-2", "-2")],
    "Rimeraven": [("oskill", "Exploding Arrow", "5", "7"), ("ease", "", "20", "20")],
    "Bloodthief": [("oskill", "Feral Rage", "5", "7"), ("damageresist", "", "-8", "-5")],
    "Soulflay": [("oskill", "Zeal", "5", "7"), ("light", "", "-2", "-2")],
    "Lance of Yaggai": [("oskill", "Charged Strike", "6", "8"), ("balance2", "", "-10", "-10")],
    "Irices Shard": [("oskill", "Frozen Armor", "6", "8")],
    "Goldskin": [("oskill", "Natural Resistance", "3", "5"), ("ease", "", "20", "20")],
    "The Spirit Shroud": [("oskill", "Psychic Ward", "6", "8")],
    "Blastbark": [("oskill", "Multiple Shot", "6", "8"), ("ease", "", "20", "20")],
    "Frostburn": [("oskill", "Chilling Armor", "7", "9"), ("balance2", "", "-10", "-10")],
    "Valkiry Wing": [("oskill", "Valkyrie", "4", "6"), ("light", "", "-2", "-2")],
    "Bloodmoon": [("oskill", "Blood Boil", "8", "11"), ("damageresist", "", "-8", "-5")],
    "Steelshade": [("oskill", "Enchant", "10", "13"), ("ease", "", "20", "20")],
    "Deathcleaver": [("oskill", "Berserk", "9", "12"), ("light", "", "-2", "-2")],
    "Gutsiphon": [("oskill", "Strafe", "9", "12"), ("balance2", "", "-10", "-10")],
    "Boneflame": [("oskill", "Bone Armor", "12", "15"), ("light", "", "-2", "-2")],

    # --- Curated Auras (13 items across 11 distinct Paladin auras; zero same-slot duplicates, >=25 lvl spacing) ---
    "Lenyms Cord": [("aura", "99", "2", "4")],                                              # Prayer
    "The Dragon Chang": [("aura", "102", "2", "4")],                                        # Holy Fire
    "Nokozan Relic": [("aura", "100", "3", "5")],                                           # Resist Fire
    "Goreshovel": [("aura", "98", "2", "4"), ("damageresist", "", "-8", "-5")],             # Might (Normal Weapon)
    "The Chieftan": [("aura", "110", "3", "5")],                                            # Resist Lightning
    "Venomsward": [("aura", "109", "3", "5")],                                              # Cleansing
    "Rockfleece": [("aura", "104", "4", "6"), ("balance2", "", "-10", "-10")],              # Defiance (Normal Armor)
    "Skullcollector": [("aura", "120", "5", "8"), ("balance2", "", "-10", "-10")],          # Meditation
    "Gravepalm": [("aura", "119", "4", "6"), ("light", "", "-2", "-2")],                    # Sanctuary
    "Silkweave": [("aura", "115", "4", "6"), ("damageresist", "", "-8", "-5")],             # Vigor
    "Stoneraven": [("aura", "104", "8", "11"), ("ease", "", "20", "20")],                   # Defiance (Elite Spear)
    "Giantskull": [("aura", "98", "7", "10"), ("balance2", "", "-10", "-10")],              # Might (Elite Helm)
    "Kira's Guardian": [("aura", "125", "5", "8")],                                         # Salvation

    # --- Curated Procs (19 items across 15 distinct skills; zero same-slot/tier collisions) ---
    "The Gnasher": [("att-skill", "66", "8", "1")],                                         # Amplify Damage
    "Fechmars Axe": [("att-skill", "45", "12", "3")],                                       # Ice Blast
    "Coif of Glory": [("gethit-skill", "71", "12", "3")],                                   # Dim Vision
    "Hawkmail": [("gethit-skill", "44", "12", "3")],                                        # Frost Nova
    "Sparking Mail": [("gethit-skill", "38", "15", "5")],                                   # Charged Bolt
    "The Battlebranch": [("att-skill", "396", "10", "3")],                                  # Sigil Rancor
    "The Jade Tan Do": [("att-skill", "83", "12", "5")],                                    # Poison Explosion
    "The Face of Horror": [("gethit-skill", "77", "12", "4")],                              # Terror
    "Wormskull": [("gethit-skill", "72", "12", "4")],                                       # Weaken
    "Iceblink": [("gethit-skill", "55", "12", "4")],                                        # Glacial Spike
    "Boneflesh": [("gethit-skill", "130", "12", "4")],                                      # Howl
    "Ripsaw": [("att-skill", "375", "10", "4")],                                            # Death Mark
    "Doomspittle": [("att-skill", "16", "12", "5")],                                        # Exploding Arrow
    "Visceratuant": [("gethit-skill", "48", "12", "5")],                                    # Nova
    "Ghoulhide": [("att-skill", "101", "12", "7")],                                         # Holy Bolt
    "Stormspike": [("att-skill", "53", "12", "7")],                                         # Chain Lightning
    "Razoredge": [("att-skill", "87", "10", "3")],                                          # Decrepify
    "Gargoyle's Bite": [("att-skill", "92", "12", "10")],                                   # Poison Nova
    "Wraithflight": [("att-skill", "93", "12", "10")],                                      # Bone Spirit
}

CURATED_HIGH_CB_PENALTIES: Dict[str, Tuple[str, str, str, str]] = {
    "Rixots Keen": ("light", "", "-2", "-2"),
    "Knell Striker": ("balance2", "", "-10", "-10"),
    "Crushflange": ("ease", "", "20", "20"),
    "Goblin Toe": ("move2", "", "-10", "-10"),
    "Bonesob": ("ease", "", "20", "20"),
    "Rattlecage": ("light", "", "-2", "-2"),
    "The Humongous": ("balance2", "", "-10", "-10"),
    "Hone Sundan": ("light", "", "-2", "-2"),
    "Windhammer": ("ease", "", "20", "20"),
    "Stone Crusher": ("move2", "", "-10", "-10"),
    "Steelpillar": ("ease", "", "20", "20"),
    "Executioner's Justice": ("light", "", "-2", "-2"),
}


def build_runes(cfg: dict) -> str:
    headers, rows = read_excel_tsv("runes.txt")
    for r in rows:
        r["complete"] = ""
    return write_excel_tsv("runes.txt", headers, rows)


def build_uniqueitems(cfg: dict) -> Tuple[str, List[Tuple[int, str, str]]]:
    headers, rows = read_excel_tsv("uniqueitems.txt")
    wh, wrows = read_excel_tsv("weapons.txt")
    weap_types = {r["code"]: r.get("type", "") for r in wrows if r.get("code")}

    nofreeze_removed = 0
    floor_boosted = 0
    oskill_added = 0
    aura_added = 0
    proc_added = 0
    kisscurse_added = 0

    for r in rows:
        idx_name = r.get("index", "")
        if any(sname in idx_name for sname in SUNDER_NAMES):
            r["disabled"] = "1"
            r["spawnable"] = "0"
            continue

        if r.get("spawnable") != "1" or r.get("disabled") == "1":
            continue

        # Convert Gheed's Fortune to 1x1 Small Charm (cm1) at qlvl 26 (Normal Mephisto+) with a focused 4-affix Greed Kiss-Curse identity
        if idx_name == "Gheed's Fortune":
            r["code"] = "cm1"
            r["carry1"] = "1"
            r["nolimit"] = "1"
            r["lvl"] = "26"
            r["lvl req"] = "24"
            gheed_props = []
            for p, par, mn, mx in _get_props(r, 12)[:3]:
                if p == "gold%":
                    gheed_props.append((p, par, "35", "65"))
                else:
                    gheed_props.append((p, par, mn, mx))
            gheed_props.append(("damageresist", "", "-6", "-6"))
            _set_props(r, gheed_props, 12)
            continue

        code = r.get("code", "")
        r["nolimit"] = "1"
        # Do not touch Unique Jewels (Rainbow Facet, etc.) or Quest items (lvl req == 0)
        lvl_req = int(r.get("lvl req") or "0")
        if code in ("jew", "cjw") or lvl_req == 0:
            continue
        wtype = weap_types.get(code, "")
        props = _get_props(r, 12)
        theme = _detect_theme(props)

        # 1. Remove nofreeze & compress % Extra Gold (gold%) by 0.45x so Gold Find cannot trivialize the economy
        new_props = []
        for p, par, mn, mx in props:
            if p == "nofreeze":
                nofreeze_removed += 1
                if theme == "cold" or len(props) <= 3:
                    new_props.append(("res-cold", "", "20", "30"))
            elif p == "gold%" and mn and mx:
                try:
                    g_min = max(10, int(round(int(mn) * 0.45)))
                    g_max = max(g_min, int(round(int(mx) * 0.45)))
                    new_props.append((p, par, str(g_min), str(g_max)))
                except ValueError:
                    new_props.append((p, par, mn, mx))
            else:
                new_props.append((p, par, mn, mx))
        props = new_props

        # 2. Gentle %ED floor on underperforming Unique weapons + modest 1.25x elemental scaling
        if wtype and lvl_req >= 10:
            ed_floor = min(135, 35 + int(round(lvl_req * 1.15)))
            for i, (p, par, mn, mx) in enumerate(props):
                if p == "dmg%" and mn and mx:
                    try:
                        v_min, v_max = int(mn), int(mx)
                        if v_max < ed_floor:
                            props[i] = (p, par, str(max(v_min, ed_floor - 15)), str(ed_floor))
                            floor_boosted += 1
                    except ValueError:
                        pass
                elif p in ("dmg-fire", "dmg-ltng", "dmg-cold", "dmg-pois", "dmg-mag") and mn and mx and lvl_req <= 45:
                    try:
                        v_min, v_max = int(mn), int(mx)
                        props[i] = (p, par, str(int(round(v_min * 1.25))), str(int(round(v_max * 1.25))))
                    except ValueError:
                        pass

        # 3. Strict 4-6 Affix Curation: Apply hand-curated, zero-duplicate oskills, auras, and procs
        if idx_name in CURATED_UNIQUE_ADDITIONS:
            for add_p in CURATED_UNIQUE_ADDITIONS[idx_name]:
                props.append(add_p)
                if add_p[0] == "oskill":
                    oskill_added += 1
                elif add_p[0] == "aura":
                    aura_added += 1
                elif add_p[0] in ("att-skill", "gethit-skill", "hit-skill"):
                    proc_added += 1
                elif add_p[0] in ("light", "ease", "balance2", "damageresist", "move2"):
                    kisscurse_added += 1

        # 4. Kiss-Curse tradeoffs on high Crushing Blow items
        if idx_name in CURATED_HIGH_CB_PENALTIES and len(props) <= 6:
            pen = CURATED_HIGH_CB_PENALTIES[idx_name]
            if pen[0] not in {p[0] for p in props}:
                props.append(pen)
                kisscurse_added += 1

        _set_props(r, props[:12], 12)

    # 5. Add 13 Historical & Mythological Unique Javelins
    next_id = max(int(r["*ID"]) for r in rows if r.get("*ID", "").isdigit()) + 1
    string_updates: List[Tuple[int, str, str]] = []
    next_str_id = 60100

    jav_uniques = [
        # (name, code, lvl, lreq, props)
        ("Mesankylon", "jav", "6", "4", [
            ("dmg%", "", "45", "65"),
            ("swing2", "", "15", "15"),
            ("pierce", "", "20", "20"),
            ("att", "", "40", "60"),
            ("rep-quant", "8", "", ""),
        ]),
        ("Verutum", "pil", "13", "9", [
            ("dmg%", "", "65", "85"),
            ("crush", "", "15", "15"),
            ("dmg-ac", "", "-25", "-25"),
            ("swing2", "", "-10", "-10"),
            ("rep-quant", "10", "", ""),
        ]),
        ("Akontion", "ssp", "18", "13", [
            ("dmg%", "", "70", "90"),
            ("move2", "", "15", "15"),
            ("openwounds", "", "20", "20"),
            ("dex", "", "8", "12"),
            ("rep-quant", "8", "", ""),
        ]),
        ("Rhomphaia", "glv", "25", "18", [
            ("dmg%", "", "90", "115"),
            ("deadly", "", "25", "25"),
            ("lifesteal", "", "5", "7"),
            ("damageresist", "", "-8", "-8"),
            ("rep-quant", "10", "", ""),
        ]),
        ("Soliferrum", "tsp", "31", "22", [
            ("dmg%", "", "100", "130"),
            ("knock", "", "1", "1"),
            ("crush", "", "20", "20"),
            ("ease", "", "20", "20"),
            ("rep-quant", "10", "", ""),
        ]),
        ("Atalanta's Dart", "am5", "26", "19", [
            ("ama", "", "1", "1"),
            ("dmg%", "", "85", "110"),
            ("oskill", "Guided Arrow", "4", "6"),
            ("move2", "", "20", "20"),
            ("rep-quant", "8", "", ""),
        ]),
        ("Xyston", "9ja", "36", "26", [
            ("dmg%", "", "115", "145"),
            ("swing2", "", "20", "20"),
            ("pierce", "", "30", "30"),
            ("att%", "", "20", "30"),
            ("rep-quant", "8", "", ""),
        ]),
        ("Angon", "9pi", "42", "30", [
            ("dmg%", "", "130", "160"),
            ("slow", "", "25", "25"),
            ("dmg-ac", "", "-40", "-40"),
            ("swing2", "", "-10", "-10"),
            ("rep-quant", "10", "", ""),
        ]),
        ("Lancea", "9s9", "46", "33", [
            ("dmg%", "", "125", "155"),
            ("ltng-min", "", "1", "1"),
            ("ltng-max", "", "120", "180"),
            ("att-skill", "53", "12", "8"),
            ("rep-quant", "8", "", ""),
        ]),
        ("Sarissa", "9gl", "52", "38", [
            ("dmg%", "", "150", "185"),
            ("crush", "", "25", "25"),
            ("knock", "", "1", "1"),
            ("balance2", "", "-15", "-15"),
            ("rep-quant", "10", "", ""),
        ]),
        ("Harpago", "9ts", "56", "41", [
            ("dmg%", "", "140", "175"),
            ("openwounds", "", "35", "35"),
            ("lifesteal", "", "6", "8"),
            ("oskill", "Impale", "6", "9"),
            ("rep-quant", "8", "", ""),
        ]),
        ("Pelian Ash", "7ja", "62", "46", [
            ("dmg%", "", "165", "205"),
            ("allskills", "", "1", "1"),
            ("swing2", "", "25", "25"),
            ("pierce", "", "33", "33"),
            ("rep-quant", "7", "", ""),
        ]),
        ("Ares-Piercer", "7pi", "70", "52", [
            ("dmg%", "", "185", "230"),
            ("deadly", "", "30", "30"),
            ("att-skill", "66", "10", "3"),
            ("damageresist", "", "-10", "-10"),
            ("rep-quant", "8", "", ""),
        ]),
    ]

    base_u = dict(rows[0])
    for name, code, lvl, lreq, jprops in jav_uniques:
        ur = {h: "" for h in headers}
        ur["index"] = name
        ur["*ID"] = str(next_id)
        next_id += 1
        ur["version"] = "100"
        ur["spawnable"] = "1"
        ur["nolimit"] = "1"
        ur["rarity"] = "2"
        ur["lvl"] = lvl
        ur["lvl req"] = lreq
        ur["code"] = code
        ur["*ItemName"] = name
        ur["cost mult"] = "5"
        ur["cost add"] = "2500"
        ur["*eol"] = "0"
        _set_props(ur, jprops, 12)
        rows.append(ur)
        string_updates.append((next_str_id, name, name))
        next_str_id += 1

    # 6. Add 4 Additional 1x1 (cm1, carry1=1, nolimit=1) Act Boss Unique Charms across qlvl 12 / 48 / 63 / 84
    # (pairing with Gheed's Fortune at qlvl 26 for the full 12 / 26 / 48 / 63 / 84 ladder matching Boss mlvls).
    # Each has a tight 4-affix Kiss-Curse package (2-3 focused bonuses + 1 thematic penalty).
    boss_charms = [
        ("Signet of the Maiden", "12", "12", [
            ("res-pois", "", "20", "25"),
            ("swing2", "", "10", "10"),
            ("move2", "", "10", "10"),
            ("res-fire", "", "-15", "-10"),
        ]),
        ("Carapace of Pain", "48", "36", [
            ("damageresist", "", "6", "8"),
            ("res-cold", "", "20", "25"),
            ("gethit-skill", "44", "12", "5"),
            ("move2", "", "-10", "-10"),
        ]),
        ("Soulstone Shard", "63", "50", [
            ("allskills", "", "1", "1"),
            ("res-all", "", "8", "12"),
            ("cast2", "", "10", "10"),
            ("hp", "", "-35", "-25"),
        ]),
        ("Eye of Destruction", "84", "64", [
            ("allskills", "", "1", "1"),
            ("dmg%", "", "20", "30"),
            ("pierce", "", "10", "15"),
            ("damageresist", "", "-8", "-8"),
        ]),
    ]
    for cname, lvl, lreq, cprops in boss_charms:
        ur = {h: "" for h in headers}
        ur["index"] = cname
        ur["*ID"] = str(next_id)
        next_id += 1
        ur["version"] = "100"
        ur["spawnable"] = "1"
        ur["nolimit"] = "1"
        ur["rarity"] = "1"
        ur["carry1"] = "1"
        ur["lvl"] = lvl
        ur["lvl req"] = lreq
        ur["code"] = "cm1"
        ur["*ItemName"] = cname
        ur["cost mult"] = "5"
        ur["cost add"] = "5000"
        ur["*eol"] = "0"
        _set_props(ur, cprops, 12)
        rows.append(ur)
        string_updates.append((next_str_id, cname, cname))
        next_str_id += 1

    # 7. Add 28 Non-Spawnable (spawnable=0, nolimit=1) 4-Tier Valkyrie & Shadow Uniques for monequip.txt
    summon_uniques = [
        # Valkyrie Weapons (vk1..vk4)
        ("Valkyrie Spear I", "vk1", [("dmg%", "", "60", "60"), ("swing2", "", "20", "20"), ("att", "", "100", "100")]),
        ("Valkyrie Spear II", "vk2", [("dmg%", "", "110", "110"), ("swing2", "", "25", "25"), ("crush", "", "20", "20"), ("lifesteal", "", "8", "8")]),
        ("Valkyrie Spear III", "vk3", [("dmg%", "", "160", "160"), ("swing2", "", "30", "30"), ("crush", "", "25", "25"), ("att-skill", "66", "15", "3")]),
        ("Valkyrie Spear IV", "vk4", [("dmg%", "", "220", "220"), ("swing2", "", "40", "40"), ("crush", "", "35", "35"), ("aura", "98", "3", "3"), ("att-skill", "87", "20", "5")]),
        # Valkyrie Armors (va1..va4)
        ("Valkyrie Armor I", "va1", [("ac%", "", "60", "60"), ("res-all", "", "20", "20"), ("hp", "", "40", "40")]),
        ("Valkyrie Armor II", "va2", [("ac%", "", "100", "100"), ("res-all", "", "35", "35"), ("damageresist", "", "10", "10")]),
        ("Valkyrie Armor III", "va3", [("ac%", "", "150", "150"), ("res-all", "", "50", "50"), ("damageresist", "", "15", "15"), ("aura", "104", "2", "2")]),
        ("Valkyrie Armor IV", "va4", [("ac%", "", "200", "200"), ("res-all", "", "65", "65"), ("damageresist", "", "25", "25"), ("aura", "104", "4", "4")]),
        # Valkyrie Helms (vh1..vh4)
        ("Valkyrie Helm I", "vh1", [("res-all", "", "15", "15"), ("hp", "", "30", "30")]),
        ("Valkyrie Helm II", "vh2", [("res-all", "", "25", "25"), ("lifesteal", "", "6", "6"), ("balance2", "", "20", "20")]),
        ("Valkyrie Helm III", "vh3", [("res-all", "", "35", "35"), ("lifesteal", "", "10", "10"), ("deadly", "", "25", "25")]),
        ("Valkyrie Helm IV", "vh4", [("res-all", "", "50", "50"), ("lifesteal", "", "12", "12"), ("deadly", "", "35", "35"), ("absorb-fire%", "", "15", "15")]),
        # Shadow Primary Claws (sw1..sw4)
        ("Shadow Claw I", "sw1", [("dmg%", "", "60", "60"), ("swing2", "", "20", "20"), ("openwounds", "", "25", "25")]),
        ("Shadow Claw II", "sw2", [("dmg%", "", "110", "110"), ("swing2", "", "25", "25"), ("crush", "", "20", "20"), ("openwounds", "", "35", "35")]),
        ("Shadow Claw III", "sw3", [("dmg%", "", "160", "160"), ("swing2", "", "30", "30"), ("crush", "", "25", "25"), ("att-skill", "91", "15", "3")]),
        ("Shadow Claw IV", "sw4", [("dmg%", "", "220", "220"), ("swing2", "", "40", "40"), ("crush", "", "35", "35"), ("deadly", "", "35", "35"), ("att-skill", "66", "20", "5")]),
        # Shadow Off-Hand Claws (so1..so4)
        ("Shadow Off-Claw I", "so1", [("dmg%", "", "50", "50"), ("lifesteal", "", "8", "8"), ("res-all", "", "15", "15")]),
        ("Shadow Off-Claw II", "so2", [("dmg%", "", "100", "100"), ("lifesteal", "", "10", "10"), ("ltng-min", "", "1", "1"), ("ltng-max", "", "120", "120")]),
        ("Shadow Off-Claw III", "so3", [("dmg%", "", "150", "150"), ("lifesteal", "", "12", "12"), ("cold-min", "", "50", "50"), ("cold-max", "", "120", "120")]),
        ("Shadow Off-Claw IV", "so4", [("dmg%", "", "200", "200"), ("lifesteal", "", "15", "15"), ("aura", "113", "3", "3"), ("res-all", "", "30", "30")]),
        # Shadow Armors (sa1..sa4)
        ("Shadow Armor I", "sa1", [("ac%", "", "60", "60"), ("move2", "", "20", "20"), ("res-all", "", "20", "20")]),
        ("Shadow Armor II", "sa2", [("ac%", "", "100", "100"), ("move2", "", "25", "25"), ("res-all", "", "35", "35"), ("damageresist", "", "10", "10")]),
        ("Shadow Armor III", "sa3", [("ac%", "", "150", "150"), ("move2", "", "30", "30"), ("res-all", "", "50", "50"), ("damageresist", "", "15", "15")]),
        ("Shadow Armor IV", "sa4", [("ac%", "", "200", "200"), ("move2", "", "35", "35"), ("res-all", "", "65", "65"), ("damageresist", "", "25", "25")]),
        # Shadow Helms (sh1..sh4)
        ("Shadow Helm I", "sh1", [("res-all", "", "15", "15"), ("balance2", "", "20", "20")]),
        ("Shadow Helm II", "sh2", [("res-all", "", "25", "25"), ("lifesteal", "", "8", "8")]),
        ("Shadow Helm III", "sh3", [("res-all", "", "35", "35"), ("lifesteal", "", "10", "10"), ("deadly", "", "25", "25")]),
        ("Shadow Helm IV", "sh4", [("res-all", "", "50", "50"), ("lifesteal", "", "12", "12"), ("deadly", "", "35", "35")]),
    ]
    for sname, scode, sprops in summon_uniques:
        ur = {h: "" for h in headers}
        ur["index"] = sname
        ur["*ID"] = str(next_id)
        next_id += 1
        ur["version"] = "100"
        ur["spawnable"] = "0"
        ur["nolimit"] = "1"
        ur["rarity"] = "1"
        ur["lvl"] = "1"
        ur["lvl req"] = "1"
        ur["code"] = scode
        ur["*ItemName"] = sname
        ur["cost mult"] = "1"
        ur["cost add"] = "1"
        ur["*eol"] = "0"
        _set_props(ur, sprops, 12)
        rows.append(ur)
        string_updates.append((next_str_id, sname, sname))
        next_str_id += 1

    print(
        f"[unique_sets] Uniques summary (aggregate only): nofreeze_removed={nofreeze_removed}, "
        f"floor_boosted={floor_boosted}, oskill_added={oskill_added}, aura_added={aura_added}, "
        f"proc_added={proc_added}, kisscurse_added={kisscurse_added}, new_javelins={len(jav_uniques)}"
    )
    out_path = write_excel_tsv("uniqueitems.txt", headers, rows)
    return out_path, string_updates


def build_setitems(cfg: dict) -> str:
    headers, rows = read_excel_tsv("setitems.txt")
    nofreeze_removed = 0
    partial_tuned = 0

    for r in rows:
        if not r.get("item") or r.get("disabled") == "1":
            continue
        props = _get_props(r, 9)
        theme = _detect_theme(props)

        # 1. Remove nofreeze from base props & add Kiss-Curse to overperforming Set pieces (e.g. >=30% Crushing Blow)
        new_props = []
        has_high_cb = False
        for p, par, mn, mx in props:
            if p == "nofreeze":
                nofreeze_removed += 1
                if theme == "cold":
                    new_props.append(("res-cold", "", "20", "25"))
            else:
                if p == "crush" and (int(mx or "0") >= 30):
                    has_high_cb = True
                new_props.append((p, par, mn, mx))
        if has_high_cb and len(new_props) < 7:
            new_props.append(("damageresist", "", "-8", "-8"))
            new_props.append(("light", "", "-2", "-2"))
        _set_props(r, new_props, 9)

        # 2. Remove nofreeze from partial set bonuses (aprop1a..5b)
        for i in range(1, 6):
            for ab in ("a", "b"):
                if r.get(f"aprop{i}{ab}") == "nofreeze":
                    nofreeze_removed += 1
                    r[f"aprop{i}{ab}"] = "res-cold" if theme == "cold" else "half-freeze"
                    r[f"apar{i}{ab}"] = ""
                    r[f"amin{i}{ab}"] = "20" if theme == "cold" else "1"
                    r[f"amax{i}{ab}"] = "20" if theme == "cold" else "1"

        # 3. Modest flat 2-piece bonus (aprop1a) on Set pieces that currently have an empty aprop1a
        if not r.get("aprop1a") and r.get("add func") == "2":
            lvl_req = int(r.get("lvl req") or "1")
            res_val = str(min(20, 8 + lvl_req // 4))
            r["aprop1a"] = "res-all"
            r["apar1a"] = ""
            r["amin1a"] = res_val
            r["amax1a"] = res_val
            partial_tuned += 1

    print(f"[unique_sets] SetItems summary: nofreeze_removed={nofreeze_removed}, partial_tuned={partial_tuned}")
    return write_excel_tsv("setitems.txt", headers, rows)


def build_sets(cfg: dict) -> str:
    headers, rows = read_excel_tsv("sets.txt")
    for r in rows:
        if not r.get("index"):
            continue
        # Remove any nofreeze on set completion bonuses
        for col in headers:
            if (col.startswith("PCode") or col.startswith("FCode")) and r.get(col) == "nofreeze":
                r[col] = "half-freeze"
    return write_excel_tsv("sets.txt", headers, rows)


def _custom_unique_string_updates() -> List[Tuple[int, str, str]]:
    names = [
        # 13 New Historical & Mythological Unique Javelins
        "Mesankylon",
        "Verutum",
        "Akontion",
        "Rhomphaia",
        "Soliferrum",
        "Atalanta's Dart",
        "Xyston",
        "Angon",
        "Lancea",
        "Sarissa",
        "Harpago",
        "Pelian Ash",
        "Ares-Piercer",
        # 4 Additional Act Boss 1x1 Unique Charms
        "Signet of the Maiden",
        "Carapace of Pain",
        "Soulstone Shard",
        "Eye of Destruction",
        # 28 Non-Spawnable 4-Tier Valkyrie & Shadow Uniques
        "Valkyrie Spear I",
        "Valkyrie Spear II",
        "Valkyrie Spear III",
        "Valkyrie Spear IV",
        "Valkyrie Armor I",
        "Valkyrie Armor II",
        "Valkyrie Armor III",
        "Valkyrie Armor IV",
        "Valkyrie Helm I",
        "Valkyrie Helm II",
        "Valkyrie Helm III",
        "Valkyrie Helm IV",
        "Shadow Claw I",
        "Shadow Claw II",
        "Shadow Claw III",
        "Shadow Claw IV",
        "Shadow Off-Claw I",
        "Shadow Off-Claw II",
        "Shadow Off-Claw III",
        "Shadow Off-Claw IV",
        "Shadow Armor I",
        "Shadow Armor II",
        "Shadow Armor III",
        "Shadow Armor IV",
        "Shadow Helm I",
        "Shadow Helm II",
        "Shadow Helm III",
        "Shadow Helm IV",
    ]
    return [(60100 + i, n, n) for i, n in enumerate(names)]


def build_unique_sets_all(cfg: dict) -> str:
    p1 = build_runes(cfg)
    locked_files = ("uniqueitems.txt", "setitems.txt", "sets.txt")
    if not cfg.get("regenerate_unique_sets", False) and all(
        os.path.exists(os.path.join(LOCKED_TABLES_DIR, fn)) for fn in locked_files
    ):
        os.makedirs(MOD_EXCEL, exist_ok=True)
        out_paths = []
        for fn in locked_files:
            src = os.path.join(LOCKED_TABLES_DIR, fn)
            dst = os.path.join(MOD_EXCEL, fn)
            shutil.copyfile(src, dst)
            out_paths.append(dst)
        p5 = update_mod_strings_json("item-names.json", _custom_unique_string_updates())
        print("[unique_sets] Copied locked uniqueitems.txt, setitems.txt, and sets.txt from locked_tables/")
        return f"{p1}, {', '.join(out_paths)}, {p5}"

    p2, str_updates = build_uniqueitems(cfg)
    p3 = build_setitems(cfg)
    p4 = build_sets(cfg)
    os.makedirs(LOCKED_TABLES_DIR, exist_ok=True)
    for fn in locked_files:
        shutil.copyfile(os.path.join(MOD_EXCEL, fn), os.path.join(LOCKED_TABLES_DIR, fn))
    p5 = update_mod_strings_json("item-names.json", str_updates)
    return f"{p1}, {p2}, {p3}, {p4}, {p5}"


def _broad_slot_label(code: str, weap_types: Dict[str, str], armor_types: Dict[str, str]) -> str:
    if code in weap_types:
        wt = weap_types[code]
        if wt in ("bow", "abow", "xbow", "jave", "ajav", "tkni", "taxe"):
            return "Ranged/Thrown Weapon"
        if wt in ("wand", "staf", "orb", "scep"):
            return "Caster Weapon"
        return "Melee Weapon"
    if code in armor_types:
        at = armor_types[code]
        if at in ("helm", "circ", "pelt", "phlm"):
            return "Helm"
        if at in ("shie", "ashd", "head"):
            return "Shield"
        if at == "glov":
            return "Gloves"
        if at == "boot":
            return "Boots"
        if at == "belt":
            return "Belt"
        return "Body Armor"
    if code == "rin":
        return "Ring"
    if code == "amu":
        return "Amulet"
    if code in ("cm1", "cm2", "cm3"):
        return "Charm"
    return "Other"


def print_anonymized_summary(cfg: dict) -> str:
    _, v_rows = read_excel_tsv("uniqueitems.txt")
    _, w_rows = read_excel_tsv("weapons.txt")
    _, a_rows = read_excel_tsv("armor.txt")
    weap_types = {r["code"]: r.get("type", "") for r in w_rows if r.get("code")}
    armor_types = {r["code"]: r.get("type", "") for r in a_rows if r.get("code")}

    oskills = []
    auras = []
    procs = []
    curses = []

    pen_labels = {
        "light": "-2 Light Radius",
        "ease": "+20% Requirements",
        "balance2": "-10% FHR",
        "damageresist": "-8% to -5% Phys DR",
        "move2": "-10% FRW",
    }

    for r in v_rows:
        idx_name = r.get("index", "")
        if any(sname in idx_name for sname in SUNDER_NAMES) or r.get("spawnable") != "1" or r.get("disabled") == "1":
            continue
        code = "cm1" if idx_name == "Gheed's Fortune" else r.get("code", "")
        lvl_req = 24 if idx_name == "Gheed's Fortune" else int(r.get("lvl req") or "0")
        if code in ("jew", "cjw") or lvl_req == 0:
            continue
        slot_lbl = _broad_slot_label(code, weap_types, armor_types)

        if idx_name in CURATED_UNIQUE_ADDITIONS:
            for p, par, mn, mx in CURATED_UNIQUE_ADDITIONS[idx_name]:
                if p == "oskill":
                    oskills.append((lvl_req, slot_lbl, f"+{mn} to +{mx}"))
                elif p == "aura":
                    auras.append((lvl_req, slot_lbl, f"Lvl {mn} to {mx}"))
                elif p in ("att-skill", "gethit-skill", "hit-skill"):
                    trig = "On Attack" if p == "att-skill" else ("When Struck" if p == "gethit-skill" else "On Striking")
                    procs.append((lvl_req, slot_lbl, trig, f"{mn}%", f"Lvl {mx}"))
                elif p in pen_labels:
                    curses.append((lvl_req, slot_lbl, pen_labels[p]))

        if idx_name in CURATED_HIGH_CB_PENALTIES:
            pen = CURATED_HIGH_CB_PENALTIES[idx_name]
            curses.append((lvl_req, slot_lbl, pen_labels.get(pen[0], pen[0])))

    print(f"\n=== ADDED OSKILLS ({len(oskills)} Vanilla Uniques + 2 New Javelins = {len(oskills) + 2} Total, 100% Distinct Skills) ===")
    for lr, sl, st in sorted(oskills + [(19, "Ranged/Thrown Weapon", "+4 to +6"), (41, "Ranged/Thrown Weapon", "+6 to +9")]):
        print(f"  LvlReq {lr:2d} | {sl:<22} | Oskill Level: {st}")

    print(f"\n=== ADDED AURAS ({len(auras)} Vanilla Uniques Across 11 Distinct Auras) ===")
    for lr, sl, st in sorted(auras):
        print(f"  LvlReq {lr:2d} | {sl:<22} | Aura Level:   {st}")

    extra_procs = [
        (33, "Ranged/Thrown Weapon", "On Attack", "12%", "Lvl 8"),
        (52, "Ranged/Thrown Weapon", "On Attack", "10%", "Lvl 3"),
    ]
    print(f"\n=== ADDED PROCS ({len(procs)} Vanilla Uniques + 2 New Javelins = {len(procs) + 2} Total) ===")
    for lr, sl, trig, ch, st in sorted(procs + extra_procs):
        print(f"  LvlReq {lr:2d} | {sl:<22} | {trig:<11} | {ch:<4} Chance | {st}")

    print("\n=== ADDED KISS-CURSE PENALTIES BY SLOT & LEVEL BRACKET ===")
    for lr, sl, pen in sorted(curses):
        print(f"  LvlReq {lr:2d} | {sl:<22} | Penalty: {pen}")
    return "anonymized_summary"

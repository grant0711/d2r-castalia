#!/usr/bin/env python3
"""
misc_items.py
Step 3b: Build misc.txt, data/hd/items/items.json, and string tables
(item-names.json, item-modifiers.json):
- 3-Tier Blacksmith's Malus (bml / bm2 / bm3) stocked at blacksmith vendors
- 5-Tier Instantaneous 100% Capped Health (hp1..hp5) & Mana (mp1..mp5) Potions
- 3-Tier 5-Minute (7500 frames) Preparation Elixirs:
    Thawing (wms -> wm2 -> wm3), Antidote (yps -> yp2 -> yp3), Stamina (vps -> vp2 -> vp3)
- Strategic Town Portal & Identify Scrolls/Tomes (tsc, tbk, isc, ibk)
- Gem & Skull levelreq = 6 / 12 / 18 / 30 / 45
- Rune r01..r33 levelreq = 4, 6, 8, ..., 70
"""
import json
import os
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
        row[f"{v}Min"] = ""
        row[f"{v}Max"] = ""
        row[f"{v}MagicMin"] = ""
        row[f"{v}MagicMax"] = ""
        row[f"{v}MagicLvl"] = "255"


def _set_vendor_stock(row: Dict[str, str], vendor_list: List[str], vmin: str = "1", vmax: str = "1") -> None:
    for v in vendor_list:
        row[f"{v}Min"] = vmin
        row[f"{v}Max"] = vmax


def build_misc(cfg: dict) -> str:
    headers, rows = read_excel_tsv("misc.txt")
    rows_by_code = {r["code"]: r for r in rows if r.get("code")}

    # 1. 3-Second Burst Health & Mana Potions with 3-Second Cooldown Lockout (hp1..hp5, mp1..mp5)
    hp_caps = [250, 500, 750, 1000, 2000]
    pot_costs = [500, 1500, 3500, 7500, 16000]
    act1_3_pot_vendors = ["Akara", "Lysander", "Drognan", "Ormus"]
    act4_5_pot_vendors = ["Jamella", "Malah"]

    for idx in range(5):
        tier = idx + 1
        cap = hp_caps[idx]
        cost = str(pot_costs[idx])

        # Health Potion hp1..hp5: uses pSpell=6 with custom state `hp_cooldown` (75 frames = 3.0s)
        # so the engine does NOT cancel the state early when HP hits 100%, enforcing a true 3.0s
        # cooldown AND continuing to heal over the full 3.0s if new damage is taken.
        hcode = f"hp{tier}"
        hrow = rows_by_code[hcode]
        hrow["cost"] = cost
        hrow["pSpell"] = "6"
        hrow["state"] = "hp_cooldown"
        hrow["cstate1"] = ""
        hrow["cstate2"] = ""
        hrow["len"] = "75"
        hrow["stat1"] = "hpregen"
        hrow["calc1"] = str(int(round(cap * 256 / 75)))
        hrow["spelldesc"] = "1"
        hrow["spelldescstr"] = f"ModHpPotDesc{tier}"
        hrow["spelldesccalc"] = ""
        hrow["UsageConditionCalc"] = "(stat('hpregen'.accr)<500)"
        _clear_vendors(hrow)
        if tier == 1:
            _set_vendor_stock(hrow, act1_3_pot_vendors, "1", "1")
            hrow["NightmareUpgrade"] = "hp3"
            hrow["HellUpgrade"] = "hp5"
        elif tier == 2:
            _set_vendor_stock(hrow, act4_5_pot_vendors, "1", "1")
            hrow["NightmareUpgrade"] = "hp4"
            hrow["HellUpgrade"] = "hp5"
        else:
            hrow["NightmareUpgrade"] = "xxx"
            hrow["HellUpgrade"] = "xxx"

        # Mana Potion mp1..mp5: restores up to `cap` over 75 frames (3.0s) and blocks re-drinking while active
        mcode = f"mp{tier}"
        mrow = rows_by_code[mcode]
        mrow["cost"] = cost
        mrow["pSpell"] = "3"
        mrow["state"] = "manapot"
        mrow["cstate1"] = ""
        mrow["cstate2"] = ""
        mrow["len"] = "75"
        mrow["stat1"] = "manarecovery"
        mrow["calc1"] = str(cap)
        mrow["spelldesc"] = "1"
        mrow["spelldescstr"] = f"ModMpPotDesc{tier}"
        mrow["spelldesccalc"] = ""
        mrow["UsageConditionCalc"] = "(stat('manarecovery'.accr)<500)"
        _clear_vendors(mrow)
        if tier == 1:
            _set_vendor_stock(mrow, act1_3_pot_vendors, "1", "1")
            mrow["NightmareUpgrade"] = "mp3"
            mrow["HellUpgrade"] = "mp5"
        elif tier == 2:
            _set_vendor_stock(mrow, act4_5_pot_vendors, "1", "1")
            mrow["NightmareUpgrade"] = "mp4"
            mrow["HellUpgrade"] = "mp5"
        else:
            mrow["NightmareUpgrade"] = "xxx"
            mrow["HellUpgrade"] = "xxx"

    # 2. Strategic Town Portal & Identify Scrolls/Tomes
    tsc = rows_by_code["tsc"]
    tsc["cost"] = "400"

    tbk = rows_by_code["tbk"]
    tbk["cost"] = "600"
    tbk["maxstack"] = "5"
    tbk["spawnstack"] = "2"

    isc = rows_by_code["isc"]
    isc["cost"] = "80"

    ibk = rows_by_code["ibk"]
    ibk["cost"] = "200"
    ibk["maxstack"] = "50"
    ibk["spawnstack"] = "10"

    # 3. Gem & Skull levelreq (6 / 12 / 18 / 30 / 45)
    gem_families = [
        ["gcv", "gfv", "gsv", "gzv", "gpv"],
        ["gcy", "gfy", "gsy", "gly", "gpy"],
        ["gcb", "gfb", "gsb", "glb", "gpb"],
        ["gcg", "gfg", "gsg", "glg", "gpg"],
        ["gcr", "gfr", "gsr", "glr", "gpr"],
        ["gcw", "gfw", "gsw", "glw", "gpw"],
        ["skc", "skf", "sku", "skl", "skz"],
    ]
    gem_lvlreqs = ["6", "12", "18", "30", "45"]
    for fam in gem_families:
        for code, lreq in zip(fam, gem_lvlreqs):
            rows_by_code[code]["levelreq"] = lreq

    # 4. Rune r01..r33 levelreq (4, 6, 8, ..., 70)
    for i in range(1, 34):
        rcode = f"r{i:02d}"
        lreq = str(2 + 2 * i)
        rows_by_code[rcode]["levelreq"] = lreq

    # 5. 3-Tier 5-Minute (7500 frames) Preparation Elixirs
    # Remove any Existing custom codes if re-running on already modified list (though we read vanilla)
    new_rows: List[Dict[str, str]] = []

    # 5a. Thawing Elixir (wms -> wm2 -> wm3)
    wms = rows_by_code["wms"]
    wms["name"] = "Minor Thawing Elixir"
    wms["cost"] = "600"
    wms["len"] = "7500"
    wms["stat1"] = "coldresist"
    wms["calc1"] = "25"
    wms["stat2"] = "maxcoldresist"
    wms["calc2"] = "4"
    wms["NightmareUpgrade"] = "wm2"
    wms["HellUpgrade"] = "wm3"

    wm2 = dict(wms)
    wm2["name"] = "Greater Thawing Elixir"
    wm2["code"] = "wm2"
    wm2["namestr"] = "wm2"
    wm2["cost"] = "2500"
    wm2["calc1"] = "40"
    wm2["calc2"] = "7"
    _clear_vendors(wm2)
    wm2["NightmareUpgrade"] = "xxx"
    wm2["HellUpgrade"] = "wm3"

    wm3 = dict(wms)
    wm3["name"] = "Supreme Thawing Elixir"
    wm3["code"] = "wm3"
    wm3["namestr"] = "wm3"
    wm3["cost"] = "8000"
    wm3["calc1"] = "50"
    wm3["calc2"] = "10"
    _clear_vendors(wm3)
    wm3["NightmareUpgrade"] = "xxx"
    wm3["HellUpgrade"] = "xxx"
    new_rows.extend([wm2, wm3])

    # 5b. Antidote Elixir (yps -> yp2 -> yp3)
    yps = rows_by_code["yps"]
    yps["name"] = "Minor Antidote Elixir"
    yps["cost"] = "600"
    yps["len"] = "7500"
    yps["stat1"] = "poisonresist"
    yps["calc1"] = "25"
    yps["stat2"] = "maxpoisonresist"
    yps["calc2"] = "4"
    yps["NightmareUpgrade"] = "yp2"
    yps["HellUpgrade"] = "yp3"

    yp2 = dict(yps)
    yp2["name"] = "Greater Antidote Elixir"
    yp2["code"] = "yp2"
    yp2["namestr"] = "yp2"
    yp2["cost"] = "2500"
    yp2["calc1"] = "40"
    yp2["calc2"] = "7"
    _clear_vendors(yp2)
    yp2["NightmareUpgrade"] = "xxx"
    yp2["HellUpgrade"] = "yp3"

    yp3 = dict(yps)
    yp3["name"] = "Supreme Antidote Elixir"
    yp3["code"] = "yp3"
    yp3["namestr"] = "yp3"
    yp3["cost"] = "8000"
    yp3["calc1"] = "50"
    yp3["calc2"] = "10"
    _clear_vendors(yp3)
    yp3["NightmareUpgrade"] = "xxx"
    yp3["HellUpgrade"] = "xxx"
    new_rows.extend([yp2, yp3])

    # 5c. Stamina Elixir (vps -> vp2 -> vp3)
    # Uses valid itemstatcost.txt stats:
    # - stat1: staminarecoverybonus (+75% / +110% / +150% -> 7.0s / 5.8s / 4.9s standing refill breather)
    # - stat2: item_staminadrainpct (60% / 70% / 80% slower stamina drain -> 2.5x / 3.33x / 5.0x run duration)
    # - stat3: skill_staminapercent (+50% / +75% / +100% Max Stamina -> 1.5x / 1.75x / 2.0x stamina pool)
    vps = rows_by_code["vps"]
    vps["name"] = "Minor Stamina Elixir"
    vps["cost"] = "600"
    vps["len"] = "7500"
    vps["stat1"] = "staminarecoverybonus"
    vps["calc1"] = "75"
    vps["stat2"] = "item_staminadrainpct"
    vps["calc2"] = "60"
    vps["stat3"] = "skill_staminapercent"
    vps["calc3"] = "50"
    vps["NightmareUpgrade"] = "vp2"
    vps["HellUpgrade"] = "vp3"

    vp2 = dict(vps)
    vp2["name"] = "Greater Stamina Elixir"
    vp2["code"] = "vp2"
    vp2["namestr"] = "vp2"
    vp2["cost"] = "2500"
    vp2["calc1"] = "110"
    vp2["calc2"] = "70"
    vp2["calc3"] = "75"
    _clear_vendors(vp2)
    vp2["NightmareUpgrade"] = "xxx"
    vp2["HellUpgrade"] = "vp3"

    vp3 = dict(vps)
    vp3["name"] = "Supreme Stamina Elixir"
    vp3["code"] = "vp3"
    vp3["namestr"] = "vp3"
    vp3["cost"] = "8000"
    vp3["calc1"] = "150"
    vp3["calc2"] = "80"
    vp3["calc3"] = "100"
    _clear_vendors(vp3)
    vp3["NightmareUpgrade"] = "xxx"
    vp3["HellUpgrade"] = "xxx"
    new_rows.extend([vp2, vp3])

    # Preserve vanilla 'gamble cost' on Ring (rin = 50,000g) and Amulet (amu = 63,000g)
    # since the C++ engine hardcodes spawning 1 'rin' and 1 'amu' into the Gamble UI.
    # Remove Keys (key) from all vendors since locked chests are removed from the mod.
    if "key" in rows_by_code:
        krow = rows_by_code["key"]
        _clear_vendors(krow)
        krow["PermStoreItem"] = "0"
        krow["spawnable"] = "0"
        krow["NightmareUpgrade"] = "xxx"
        krow["HellUpgrade"] = "xxx"

    # Enable Magic-only affix rolling on Arrows (aqv) and Bolts (cqv) from monster drops,
    # set 255 stack size (8-bit nostalgia), and clear vendor MagicMin/MagicMax so town vendors sell White quivers.
    for qcode in ("aqv", "cqv"):
        qrow = rows_by_code[qcode]
        qrow["level"] = "1"
        qrow["magic lvl"] = "1"
        qrow["compactsave"] = "0"
        qrow["minstack"] = "255"
        qrow["spawnstack"] = "255"
        qrow["maxstack"] = "255"
        for v in VENDORS:
            qrow[f"{v}MagicMin"] = ""
            qrow[f"{v}MagicMax"] = ""

    rows.extend(new_rows)
    return write_excel_tsv("misc.txt", headers, rows)


def build_hd_items_json(cfg: dict) -> str:
    additions = [
        ("wm2", "potion/thawing_potion"),
        ("wm3", "potion/thawing_potion"),
        ("yp2", "potion/antidote_potion"),
        ("yp3", "potion/antidote_potion"),
        ("vp2", "potion/stamina_potion"),
        ("vp3", "potion/stamina_potion"),
        ("bml", "hammer/horadric_malus"),
        ("bm2", "hammer/horadric_malus"),
        ("bm3", "hammer/horadric_malus"),
    ]
    return update_mod_hd_items_json(additions)


def build_misc_strings(cfg: dict) -> Tuple[str, str]:
    # 1. item-names.json
    name_updates = [
        (0, "wms", "Minor Thawing Elixir"),
        (60001, "wm2", "Greater Thawing Elixir"),
        (60002, "wm3", "Supreme Thawing Elixir"),
        (0, "yps", "Minor Antidote Elixir"),
        (60003, "yp2", "Greater Antidote Elixir"),
        (60004, "yp3", "Supreme Antidote Elixir"),
        (0, "vps", "Minor Stamina Elixir"),
        (60005, "vp2", "Greater Stamina Elixir"),
        (60006, "vp3", "Supreme Stamina Elixir"),
        (60007, "bml", "Blacksmith's Malus"),
    ]
    out_names = update_mod_strings_json("item-names.json", name_updates)

    # 2. item-modifiers.json
    mod_updates = [
        (60010, "ModHpPotDesc1", "Restores 250 Life over 3 Seconds (3s Cooldown)"),
        (60011, "ModHpPotDesc2", "Restores 500 Life over 3 Seconds (3s Cooldown)"),
        (60012, "ModHpPotDesc3", "Restores 750 Life over 3 Seconds (3s Cooldown)"),
        (60013, "ModHpPotDesc4", "Restores 1000 Life over 3 Seconds (3s Cooldown)"),
        (60014, "ModHpPotDesc5", "Restores 2000 Life over 3 Seconds (3s Cooldown)"),
        (60015, "ModMpPotDesc1", "Restores 250 Mana over 3 Seconds (3s Cooldown)"),
        (60016, "ModMpPotDesc2", "Restores 500 Mana over 3 Seconds (3s Cooldown)"),
        (60017, "ModMpPotDesc3", "Restores 750 Mana over 3 Seconds (3s Cooldown)"),
        (60018, "ModMpPotDesc4", "Restores 1000 Mana over 3 Seconds (3s Cooldown)"),
        (60019, "ModMpPotDesc5", "Restores 2000 Mana over 3 Seconds (3s Cooldown)"),
        (60020, "ModMalusDesc1", "Transmute with Socketable Gear + Perfect Skull to Add 1-2 Sockets"),
    ]
    out_mods = update_mod_strings_json("item-modifiers.json", mod_updates)
    return out_names, out_mods


def build_stamina_state(cfg: dict) -> str:
    """Delegate to skills.build_states so states.txt always includes both staminapot and custom skill states."""
    from mod_builder.skills import build_states

    return build_states(cfg)


def build_misc_all(cfg: dict) -> str:
    from mod_builder.affixes import build_itemstatcost

    p1 = build_misc(cfg)
    p2 = build_hd_items_json(cfg)
    p3, p4 = build_misc_strings(cfg)
    p5 = build_stamina_state(cfg)
    p6 = build_itemstatcost(cfg)
    return f"{p1}, {p2}, {p3}, {p4}, {p5}, {p6}"

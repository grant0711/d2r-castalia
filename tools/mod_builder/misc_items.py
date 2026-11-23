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
- Gem & Skull levelreq = 1 / 15 / 30 / 45 / 60
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
    # In Act 2, Lysander is the dedicated Alchemist/Apothecary (Health + Mana Potions & Elixirs),
    # while Drognan is the Vizjerei Sage (Caster Weapons, Tomes/Scrolls & Mana Potions only).
    # In Act 3, Alkor is the Kurast Alchemist (Health + Mana Potions, Elixirs, Grenades & Lockbox Keys),
    # while Ormus is the Skatsimi Mage (Caster Weapons, Caster Armor, Tomes/Scrolls, Mana Potions & Lockbox Keys).
    hp_caps = [120, 250, 400, 800, 1500]
    mp_caps = [80, 165, 270, 530, 1000]
    pot_costs = [500, 1200, 2500, 5000, 9000]
    act1_3_hp_vendors = ["Akara", "Lysander", "Alkor"]
    act1_3_mp_vendors = ["Akara", "Lysander", "Drognan", "Alkor", "Ormus"]
    act4_5_pot_vendors = ["Jamella", "Malah"]
    all_hp_vendors = act1_3_hp_vendors + act4_5_pot_vendors
    all_mp_vendors = act1_3_mp_vendors + act4_5_pot_vendors
    potion_helper_rows: List[Dict[str, str]] = []

    for idx in range(5):
        tier = idx + 1
        hp_cap = hp_caps[idx]
        mp_cap = mp_caps[idx]
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
        hrow["calc1"] = str(int(round(hp_cap * 256 / 75)))
        hrow["spelldesc"] = "1"
        hrow["spelldescstr"] = f"ModHpPotDesc{tier}"
        hrow["spelldesccalc"] = ""
        hrow["UsageConditionCalc"] = "(stat('hpregen'.accr)<300)"
        _clear_vendors(hrow)
        hrow["NightmareUpgrade"] = "xxx"
        hrow["HellUpgrade"] = "xxx"
        if tier == 1:
            # Slot 1: Minor Healing Potion stays stocked at all 5 Acts across Normal, Nightmare, and Hell
            _set_vendor_stock(hrow, all_hp_vendors, "1", "1")
        elif tier == 2:
            # Slot 2 (Act 4-5): Light Healing Potion unlocked in Normal Act 4-5 and stays in NM & Hell
            _set_vendor_stock(hrow, act4_5_pot_vendors, "1", "1")

        # Mana Potion mp1..mp5: restores ~2/3 of HP potion cap over 75 frames (3.0s) and blocks re-drinking while active
        mcode = f"mp{tier}"
        mrow = rows_by_code[mcode]
        mrow["cost"] = cost
        mrow["pSpell"] = "3"
        mrow["state"] = "manapot"
        mrow["cstate1"] = ""
        mrow["cstate2"] = ""
        mrow["len"] = "75"
        mrow["stat1"] = "manarecovery"
        mrow["calc1"] = str(mp_cap)
        mrow["spelldesc"] = "1"
        mrow["spelldescstr"] = f"ModMpPotDesc{tier}"
        mrow["spelldesccalc"] = ""
        mrow["UsageConditionCalc"] = "(stat('manarecovery'.accr)<200)"
        _clear_vendors(mrow)
        mrow["NightmareUpgrade"] = "xxx"
        mrow["HellUpgrade"] = "xxx"
        if tier == 1:
            _set_vendor_stock(mrow, all_mp_vendors, "1", "1")
        elif tier == 2:
            _set_vendor_stock(mrow, act4_5_pot_vendors, "1", "1")

    # Build 5-slot cumulative vendor potion helper rows so each newly unlocked tier appears
    # alongside all previously unlocked cheaper tiers (mirroring the Lockbox Key slot matrix):
    # - Act 1-3 Normal: 5x Tier 1 -> NM: Tier 1, 2, 3 -> Hell: Tier 1, 2, 3, 4, 5
    # - Act 4-5 Normal: Tier 1 + 4x Tier 2 -> NM: Tier 1, 2, 3, 4 -> Hell: Tier 1, 2, 3, 4, 5
    act1_3_slot_specs = [
        ("a", "2", "2"),  # Slot 2 (Act 1-3): Minor in Normal -> Light in NM & Hell
        ("b", "3", "3"),  # Slot 3 (Act 1-3): Minor in Normal -> Standard in NM & Hell
        ("c", "3", "4"),  # Slot 4 (Act 1-3): Minor in Normal -> Standard in NM -> Greater in Hell
        ("d", "3", "5"),  # Slot 5 (Act 1-3): Minor in Normal -> Standard in NM -> Super in Hell
    ]
    for sfx, nm_t, hell_t in act1_3_slot_specs:
        hr = dict(rows_by_code["hp1"])
        hr["code"] = f"h1{sfx}"
        hr["namestr"] = f"h1{sfx}"
        _clear_vendors(hr)
        _set_vendor_stock(hr, act1_3_hp_vendors, "1", "1")
        hr["NightmareUpgrade"] = f"hp{nm_t}"
        hr["HellUpgrade"] = f"hp{hell_t}"
        potion_helper_rows.append(hr)

        mr = dict(rows_by_code["mp1"])
        mr["code"] = f"m1{sfx}"
        mr["namestr"] = f"m1{sfx}"
        _clear_vendors(mr)
        _set_vendor_stock(mr, act1_3_mp_vendors, "1", "1")
        mr["NightmareUpgrade"] = f"mp{nm_t}"
        mr["HellUpgrade"] = f"mp{hell_t}"
        potion_helper_rows.append(mr)

    act4_5_slot_specs = [
        ("b", "3", "3"),  # Slot 3 (Act 4-5): Light in Normal -> Standard in NM & Hell
        ("c", "4", "4"),  # Slot 4 (Act 4-5): Light in Normal -> Greater in NM & Hell
        ("d", "4", "5"),  # Slot 5 (Act 4-5): Light in Normal -> Greater in NM -> Super in Hell
    ]
    for sfx, nm_t, hell_t in act4_5_slot_specs:
        hr = dict(rows_by_code["hp2"])
        hr["code"] = f"h2{sfx}"
        hr["namestr"] = f"h2{sfx}"
        _clear_vendors(hr)
        _set_vendor_stock(hr, act4_5_pot_vendors, "1", "1")
        hr["NightmareUpgrade"] = f"hp{nm_t}"
        hr["HellUpgrade"] = f"hp{hell_t}"
        potion_helper_rows.append(hr)

        mr = dict(rows_by_code["mp2"])
        mr["code"] = f"m2{sfx}"
        mr["namestr"] = f"m2{sfx}"
        _clear_vendors(mr)
        _set_vendor_stock(mr, act4_5_pot_vendors, "1", "1")
        mr["NightmareUpgrade"] = f"mp{nm_t}"
        mr["HellUpgrade"] = f"mp{hell_t}"
        potion_helper_rows.append(mr)

    # 2. Identify Scrolls/Tomes (sold exclusively by each Act's Mystic/Sage);
    # Town Portal Scroll (tsc) and Tome of Town Portal (tbk) removed from all vendors
    scroll_vendors = ["Akara", "Drognan", "Ormus", "Jamella", "Malah"]
    tsc = rows_by_code["tsc"]
    tsc["cost"] = "400"
    _clear_vendors(tsc)

    tbk = rows_by_code["tbk"]
    tbk["cost"] = "600"
    tbk["maxstack"] = "5"
    tbk["spawnstack"] = "0"
    _clear_vendors(tbk)

    isc = rows_by_code["isc"]
    isc["cost"] = "250"
    _clear_vendors(isc)
    _set_vendor_stock(isc, scroll_vendors, "1", "1")

    ibk = rows_by_code["ibk"]
    ibk["cost"] = "10000"
    ibk["maxstack"] = "10"
    ibk["spawnstack"] = "1"
    _clear_vendors(ibk)
    _set_vendor_stock(ibk, scroll_vendors, "1", "1")

    # 3. Gem & Skull levelreq (1 / 15 / 30 / 45 / 60)
    gem_families = [
        ["gcv", "gfv", "gsv", "gzv", "gpv"],
        ["gcy", "gfy", "gsy", "gly", "gpy"],
        ["gcb", "gfb", "gsb", "glb", "gpb"],
        ["gcg", "gfg", "gsg", "glg", "gpg"],
        ["gcr", "gfr", "gsr", "glr", "gpr"],
        ["gcw", "gfw", "gsw", "glw", "gpw"],
        ["skc", "skf", "sku", "skl", "skz"],
    ]
    gem_lvlreqs = ["1", "15", "30", "45", "60"]
    for fam in gem_families:
        for code, lreq in zip(fam, gem_lvlreqs):
            rows_by_code[code]["levelreq"] = lreq

    # 4. Rune r01..r33 levelreq (4, 6, 8, ..., 70)
    for i in range(1, 34):
        rcode = f"r{i:02d}"
        lreq = str(2 + 2 * i)
        rows_by_code[rcode]["levelreq"] = lreq

    # 5. 3-Tier 5-Minute (7500 frames) Preparation Elixirs
    # Stocked exclusively at each Act's Alchemist/Mystic (Akara, Lysander, Alkor, Jamella, Malah)
    elixir_vendors = ["Akara", "Lysander", "Alkor", "Jamella", "Malah"]
    new_rows: List[Dict[str, str]] = list(potion_helper_rows)

    # 5a. Thawing Elixir (wms -> wm2 -> wm3)
    wms = rows_by_code["wms"]
    wms["name"] = "Minor Thawing Elixir"
    wms["cost"] = "600"
    wms["autobelt"] = "1"
    wms["len"] = "7500"
    wms["stat1"] = "coldresist"
    wms["calc1"] = "25"
    wms["stat2"] = "maxcoldresist"
    wms["calc2"] = "4"
    _clear_vendors(wms)
    _set_vendor_stock(wms, elixir_vendors, "1", "1")
    wms["NightmareUpgrade"] = "wm2"
    wms["HellUpgrade"] = "wm3"

    wm2 = dict(wms)
    wm2["name"] = "Greater Thawing Elixir"
    wm2["code"] = "wm2"
    wm2["namestr"] = "wm2"
    wm2["cost"] = "2000"
    wm2["calc1"] = "40"
    wm2["calc2"] = "7"
    _clear_vendors(wm2)
    wm2["NightmareUpgrade"] = "xxx"
    wm2["HellUpgrade"] = "wm3"

    wm3 = dict(wms)
    wm3["name"] = "Supreme Thawing Elixir"
    wm3["code"] = "wm3"
    wm3["namestr"] = "wm3"
    wm3["cost"] = "5000"
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
    yps["autobelt"] = "1"
    yps["len"] = "7500"
    yps["stat1"] = "poisonresist"
    yps["calc1"] = "25"
    yps["stat2"] = "maxpoisonresist"
    yps["calc2"] = "4"
    _clear_vendors(yps)
    _set_vendor_stock(yps, elixir_vendors, "1", "1")
    yps["NightmareUpgrade"] = "yp2"
    yps["HellUpgrade"] = "yp3"

    yp2 = dict(yps)
    yp2["name"] = "Greater Antidote Elixir"
    yp2["code"] = "yp2"
    yp2["namestr"] = "yp2"
    yp2["cost"] = "2000"
    yp2["calc1"] = "40"
    yp2["calc2"] = "7"
    _clear_vendors(yp2)
    yp2["NightmareUpgrade"] = "xxx"
    yp2["HellUpgrade"] = "yp3"

    yp3 = dict(yps)
    yp3["name"] = "Supreme Antidote Elixir"
    yp3["code"] = "yp3"
    yp3["namestr"] = "yp3"
    yp3["cost"] = "5000"
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
    vps["autobelt"] = "1"
    vps["len"] = "7500"
    vps["stat1"] = "staminarecoverybonus"
    vps["calc1"] = "75"
    vps["stat2"] = "item_staminadrainpct"
    vps["calc2"] = "60"
    vps["stat3"] = "skill_staminapercent"
    vps["calc3"] = "50"
    _clear_vendors(vps)
    _set_vendor_stock(vps, elixir_vendors, "1", "1")
    vps["NightmareUpgrade"] = "vp2"
    vps["HellUpgrade"] = "vp3"

    vp2 = dict(vps)
    vp2["name"] = "Greater Stamina Elixir"
    vp2["code"] = "vp2"
    vp2["namestr"] = "vp2"
    vp2["cost"] = "2000"
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
    vp3["cost"] = "5000"
    vp3["calc1"] = "150"
    vp3["calc2"] = "80"
    vp3["calc3"] = "100"
    _clear_vendors(vp3)
    vp3["NightmareUpgrade"] = "xxx"
    vp3["HellUpgrade"] = "xxx"
    new_rows.extend([vp2, vp3])

    # Preserve vanilla 'gamble cost' on Ring (rin = 50,000g) and Amulet (amu = 63,000g)
    # since the C++ engine hardcodes spawning 1 'rin' and 1 'amu' into the Gamble UI.
    # 6. Configure 3-Tier Lockbox Keys (key = 1,000g, ky2 = 5,000g, ky3 = 10,000g)
    # Stocked at 1 vendor per Act:
    # Act 1: Gheed, Act 2: Elzix, Act 3: Hratli, Act 4: Jamella, Act 5: Anya.
    from mod_builder.lockboxes import LOCKBOX_TIER_INFO, get_lockbox_registry

    key_vendors = ["Gheed", "Elzix", "Hratli", "Jamella", "Anya"]
    krow = rows_by_code["key"]
    _clear_vendors(krow)
    krow["name"] = LOCKBOX_TIER_INFO[1]["key_name"]
    krow["type"] = "key"
    krow["cost"] = LOCKBOX_TIER_INFO[1]["key_cost"]
    krow["level"] = "1"
    krow["spawnable"] = "1"
    krow["stackable"] = "0"
    krow["minstack"] = ""
    krow["maxstack"] = ""
    krow["spawnstack"] = ""
    krow["multibuy"] = "0"
    krow["PermStoreItem"] = "1"
    krow["NightmareUpgrade"] = "xxx"
    krow["HellUpgrade"] = "xxx"
    krow["spelldesc"] = "1"
    krow["spelldescstr"] = "ModKeyDesc1"
    krow["spelldesccolor"] = "8"

    # Slot 1 (key): Crude Lockbox Key in Normal, Nightmare, and Hell
    _set_vendor_stock(krow, key_vendors, "1", "1")

    # Slot 2 (ky0): Crude Lockbox Key in Normal -> upgrades to Iron Lockbox Key (ky2) in Nightmare & Hell
    ky0 = dict(krow)
    ky0["code"] = "ky0"
    ky0["namestr"] = "ky0"
    ky0["NightmareUpgrade"] = "ky2"
    ky0["HellUpgrade"] = "ky2"
    new_rows.append(ky0)

    # Slot 3 (ky1): Crude Lockbox Key in Normal & Nightmare -> upgrades to Ornate Lockbox Key (ky3) in Hell
    ky1 = dict(krow)
    ky1["code"] = "ky1"
    ky1["namestr"] = "ky1"
    ky1["NightmareUpgrade"] = "xxx"
    ky1["HellUpgrade"] = "ky3"
    new_rows.append(ky1)

    for ktier in (2, 3):
        ktinfo = LOCKBOX_TIER_INFO[ktier]
        knew = dict(krow)
        _clear_vendors(knew)
        knew["name"] = ktinfo["key_name"]
        knew["code"] = ktinfo["key_code"]
        knew["namestr"] = ktinfo["key_code"]
        knew["cost"] = ktinfo["key_cost"]
        knew["PermStoreItem"] = "1"
        knew["NightmareUpgrade"] = "xxx"
        knew["HellUpgrade"] = "xxx"
        knew["spelldescstr"] = f"ModKeyDesc{ktier}"
        new_rows.append(knew)

    # Generate the 536 2x2 Lockbox rows (1 per spawnable Unique & Set item)
    box_template = dict(rows_by_code["hrb"])
    _clear_vendors(box_template)
    box_template["version"] = "100"
    box_template["compactsave"] = "1"
    box_template["rarity"] = "1"
    box_template["spawnable"] = "1"
    box_template["level"] = "1"
    box_template["levelreq"] = "0"
    box_template["nodurability"] = "1"
    box_template["cost"] = "0"
    box_template["alternategfx"] = "box"
    box_template["component"] = "16"
    box_template["invwidth"] = "2"
    box_template["invheight"] = "2"
    box_template["flippyfile"] = "flpbox"
    box_template["invfile"] = "invbox"
    box_template["type"] = "ques"
    box_template["dropsound"] = "item_rare"
    box_template["dropsfxframe"] = "12"
    box_template["usesound"] = "item_rare"
    box_template["PermStoreItem"] = "0"
    box_template["NightmareUpgrade"] = "xxx"
    box_template["HellUpgrade"] = "xxx"
    box_template["spelldesc"] = "1"
    box_template["spelldesccolor"] = "4"

    for entry in get_lockbox_registry():
        bcode = str(entry["code"])
        btier = int(entry["tier"])
        bsound = str(entry["box_sound"])
        brow = dict(box_template)
        brow["name"] = str(entry["box_name"])
        brow["code"] = bcode
        brow["namestr"] = bcode
        brow["dropsound"] = bsound
        brow["usesound"] = bsound
        brow["spelldescstr"] = f"ModLockboxDesc{btier}"
        new_rows.append(brow)

    # Enable Magic-only affix rolling on Arrows (aqv) and Bolts (cqv) from monster drops,
    # set 255 stack size (8-bit nostalgia), and stock White quivers exclusively on each Act's
    # Ranged/Broker vendor (Gheed, Elzix, Asheara, Halbu, Anya).
    quiver_vendors = ["Gheed", "Elzix", "Asheara", "Halbu", "Anya"]
    for qcode in ("aqv", "cqv"):
        qrow = rows_by_code[qcode]
        qrow["level"] = "1"
        qrow["magic lvl"] = "1"
        qrow["compactsave"] = "0"
        qrow["minstack"] = "255"
        qrow["spawnstack"] = "255"
        qrow["maxstack"] = "255"
        _clear_vendors(qrow)
        _set_vendor_stock(qrow, quiver_vendors, "1", "2")

    rows.extend(new_rows)
    return write_excel_tsv("misc.txt", headers, rows)


def build_hd_items_json(cfg: dict) -> str:
    from mod_builder.lockboxes import ELIXIR_SPRITE_INFO, LOCKBOX_TIER_INFO, build_lockbox_sprites, get_lockbox_registry

    additions = [
        ("h1a", "potion/lesser_healing_potion"),
        ("h1b", "potion/lesser_healing_potion"),
        ("h1c", "potion/lesser_healing_potion"),
        ("h1d", "potion/lesser_healing_potion"),
        ("h2b", "potion/light_healing_potion"),
        ("h2c", "potion/light_healing_potion"),
        ("h2d", "potion/light_healing_potion"),
        ("m1a", "potion/lesser_mana_potion"),
        ("m1b", "potion/lesser_mana_potion"),
        ("m1c", "potion/lesser_mana_potion"),
        ("m1d", "potion/lesser_mana_potion"),
        ("m2b", "potion/light_mana_potion"),
        ("m2c", "potion/light_mana_potion"),
        ("m2d", "potion/light_mana_potion"),
        ("wm2", ELIXIR_SPRITE_INFO["wm2"]["asset"]),
        ("wm3", ELIXIR_SPRITE_INFO["wm3"]["asset"]),
        ("yp2", ELIXIR_SPRITE_INFO["yp2"]["asset"]),
        ("yp3", ELIXIR_SPRITE_INFO["yp3"]["asset"]),
        ("vp2", ELIXIR_SPRITE_INFO["vp2"]["asset"]),
        ("vp3", ELIXIR_SPRITE_INFO["vp3"]["asset"]),
        ("bml", "hammer/horadric_malus"),
        ("bm2", "hammer/horadric_malus"),
        ("bm3", "hammer/horadric_malus"),
        ("um1", "hammer/horadric_malus"),
        ("key", LOCKBOX_TIER_INFO[1]["key_asset"]),
        ("ky0", LOCKBOX_TIER_INFO[1]["key_asset"]),
        ("ky1", LOCKBOX_TIER_INFO[1]["key_asset"]),
        ("ky2", LOCKBOX_TIER_INFO[2]["key_asset"]),
        ("ky3", LOCKBOX_TIER_INFO[3]["key_asset"]),
    ]
    for entry in get_lockbox_registry():
        additions.append((str(entry["code"]), str(entry["box_asset"])))

    build_lockbox_sprites()
    return update_mod_hd_items_json(additions)


def build_misc_strings(cfg: dict) -> Tuple[str, str]:
    from mod_builder.lockboxes import LOCKBOX_TIER_INFO, get_lockbox_registry

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
        (61995, "um1", "Untempered Malus"),
        (0, "key", LOCKBOX_TIER_INFO[1]["key_name"]),
        (61993, "ky0", LOCKBOX_TIER_INFO[1]["key_name"]),
        (61994, "ky1", LOCKBOX_TIER_INFO[1]["key_name"]),
        (60008, "ky2", LOCKBOX_TIER_INFO[2]["key_name"]),
        (60009, "ky3", LOCKBOX_TIER_INFO[3]["key_name"]),
        (61970, "h1a", "Minor Healing Potion"),
        (61971, "h1b", "Minor Healing Potion"),
        (61972, "h1c", "Minor Healing Potion"),
        (61973, "h1d", "Minor Healing Potion"),
        (61974, "h2b", "Light Healing Potion"),
        (61975, "h2c", "Light Healing Potion"),
        (61976, "h2d", "Light Healing Potion"),
        (61977, "m1a", "Minor Mana Potion"),
        (61978, "m1b", "Minor Mana Potion"),
        (61979, "m1c", "Minor Mana Potion"),
        (61980, "m1d", "Minor Mana Potion"),
        (61981, "m2b", "Light Mana Potion"),
        (61982, "m2c", "Light Mana Potion"),
        (61983, "m2d", "Light Mana Potion"),
    ]
    next_lb_id = 62000
    for entry in get_lockbox_registry():
        name_updates.append((next_lb_id, str(entry["code"]), str(entry["box_display_name"])))
        next_lb_id += 1
    out_names = update_mod_strings_json("item-names.json", name_updates)

    # 2. item-modifiers.json
    mod_updates = [
        (60010, "ModHpPotDesc1", "Restores 120 Life over 3 Seconds (3s Cooldown)"),
        (60011, "ModHpPotDesc2", "Restores 250 Life over 3 Seconds (3s Cooldown)"),
        (60012, "ModHpPotDesc3", "Restores 400 Life over 3 Seconds (3s Cooldown)"),
        (60013, "ModHpPotDesc4", "Restores 800 Life over 3 Seconds (3s Cooldown)"),
        (60014, "ModHpPotDesc5", "Restores 1500 Life over 3 Seconds (3s Cooldown)"),
        (60015, "ModMpPotDesc1", "Restores 80 Mana over 3 Seconds (3s Cooldown)"),
        (60016, "ModMpPotDesc2", "Restores 165 Mana over 3 Seconds (3s Cooldown)"),
        (60017, "ModMpPotDesc3", "Restores 270 Mana over 3 Seconds (3s Cooldown)"),
        (60018, "ModMpPotDesc4", "Restores 530 Mana over 3 Seconds (3s Cooldown)"),
        (60019, "ModMpPotDesc5", "Restores 1000 Mana over 3 Seconds (3s Cooldown)"),
        (60020, "ModMalusDesc1", "Transmute with Gear + Perfect Skull to Add Sockets (Magic 2-3, Rare/Craft 1-2, Unique/Set 1)"),
        (60021, "ModKeyDesc1", "Unlocks Crude Wooden Lockbox"),
        (60022, "ModKeyDesc2", "Unlocks Reinforced Iron Lockbox"),
        (60023, "ModKeyDesc3", "Unlocks Ornate Gilded Lockbox"),
        (60024, "ModLockboxDesc1", "Requires Crude Lockbox Key"),
        (61991, "ModLockboxDesc2", "Requires Iron Lockbox Key"),
        (61992, "ModLockboxDesc3", "Requires Ornate Lockbox Key"),
        (0, "ModStr2t", "Elemental/Magic Damage Received -%d"),
        (61995, "ModStr2tNegative", "Elemental/Magic Damage Received +%d"),
        (61996, "ModTotalDefPos", "Total Defense Increased by %d%%"),
        (61997, "ModTotalDefNeg", "Total Defense Reduced by %d%%"),
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

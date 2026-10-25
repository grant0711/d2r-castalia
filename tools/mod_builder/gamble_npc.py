#!/usr/bin/env python3
"""
gamble_npc.py (Step 2)
Transforms npc.txt and gamble.txt:
  - npc.txt: Lowers NPC player-sell-back multiplier ('buy mult': 512 -> 128) and caps
    'max buy' / 'max buy (N)' / 'max buy (H)' at 500 / 1000 / 1500 Gold so Gold comes from
    slaying monsters rather than hauling equipment back to town. Slightly increases 'rep mult'
    (128 -> 192) so repairing and recharging item skill charges is a strategic Gold sink.
  - gamble.txt: Replaces equipment rows with a single non-equip row (Scroll of Identify 'isc')
    so nGambleRecords >= 1 (avoiding divide-by-zero in D2Common) while preventing equipment gambling.
"""
from .common import load_config, read_excel_tsv, update_mod_strings_json, write_excel_tsv


def build_npc(cfg: dict = None) -> str:
    if cfg is None:
        cfg = load_config()
    econ = cfg.get("economy", {})
    cap_n = int(econ.get("vendor_sell_cap_normal", 500))
    cap_nm = int(econ.get("vendor_sell_cap_nm", 1000))
    cap_h = int(econ.get("vendor_sell_cap_hell", 1500))

    headers, rows = read_excel_tsv("npc.txt")
    for row in rows:
        row["buy mult"] = "128"
        row["rep mult"] = "192"
        row["max buy"] = str(cap_n)
        row["max buy (N)"] = str(cap_nm)
        row["max buy (H)"] = str(cap_h)

    return write_excel_tsv("npc.txt", headers, rows)


def build_gamble(cfg: dict = None) -> str:
    headers, _ = read_excel_tsv("gamble.txt")
    rows = [{"name": "Blacksmith's Malus", "code": "bml"}]
    p_gamble = write_excel_tsv("gamble.txt", headers, rows)
    p_ui = update_mod_strings_json(
        "ui.json",
        [
            (3398, "gamble", "crafting"),
            (11168, "respec", ""),
            (3343, "TransactionMenu1f", "Place an Untempered Malus to temper"),
            (4017, "Upgrade", "Temper Malus"),
        ],
    )
    p_quests = update_mod_strings_json(
        "quests.json",
        [
            (3757, "qstsa1q32b", "Charsi will temper an Untempered Malus with Horadric power."),
        ],
    )
    return f"{p_gamble}, {p_ui}, {p_quests}"


def build_gamble_npc(cfg: dict = None) -> str:
    p1 = build_npc(cfg)
    p2 = build_gamble(cfg)
    return f"{p1}, {p2}"

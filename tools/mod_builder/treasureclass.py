#!/usr/bin/env python3
"""
treasureclass.py
Step 4: Build treasureclassex.txt implementing the 4-tier deterministic loot hierarchy:
- Strip health/mana/throwing/elixir potion ground clutter (keeping only rvs/rvl)
- Remove random magic charms (cm1, cm2, cm3) from Jewelry A/B/C
- Disable Sunder Charms & Pandemonium Keys (pk1, pk2, pk3)
- Flatten Rune cascade (Runes 1..17) so mid/high Runes are realistic solo crafting materials
- Multiply monster Gold drops by gold_pile_multiplier (~1280)
- Create Act X GemRune sub-tables (50% Gem / 50% Rune scaled to Act/Difficulty)
- Tier 1 (Normal Monsters): high gold piles, ~12-15% Magic+ equipment, Good TCs
- Tier 2 (Zone Uniques & Champions): Picks = -2, NoDrop = 0 -> 1 Guaranteed Gem/Rune + 1 Guaranteed Equipment
- Tier 3 (SuperUniques): Picks = -3 (or -4), NoDrop = 0 -> 1 Guaranteed Gem/Rune + 2 Guaranteed High-Quality Equipment (Countess: 2 Runes + 2 Equip)
- Tier 4 (Act Bosses: Andariel, Duriel, Mephisto, Diablo, Baal & q variants): Picks = -6, NoDrop = 0 ->
  2 Guaranteed Gem/Rune + 3 Guaranteed Boss Equip + 1 Dedicated Unique Boss Charm roll
"""
from typing import Dict, List, Tuple

from mod_builder.common import read_excel_tsv, write_excel_tsv

ACTS = [
    # (act_prefix, gem_primary, gem_secondary, rune_tc_early, rune_tc_late, equip_fallback)
    # Aligned with Gem levelreqs: Chipped (6), Flawed (12), Normal (18), Flawless (30), Perfect (45)
    ("Act 1", "Chipped Gem", "Chipped Gem", "Runes 1", "Runes 2", "Act 1 Equip B"),
    ("Act 2", "Flawed Gem", "Chipped Gem", "Runes 2", "Runes 3", "Act 2 Equip B"),
    ("Act 3", "Normal Gem", "Flawed Gem", "Runes 4", "Runes 5", "Act 3 Equip B"),
    ("Act 4", "Normal Gem", "Flawed Gem", "Runes 6", "Runes 7", "Act 4 Equip B"),
    ("Act 5", "Flawless Gem", "Normal Gem", "Runes 7", "Runes 8", "Act 5 Equip B"),
    ("Act 1 (N)", "Flawless Gem", "Normal Gem", "Runes 8", "Runes 9", "Act 1 (N) Equip B"),
    ("Act 2 (N)", "Flawless Gem", "Perfect Gem", "Runes 9", "Runes 10", "Act 2 (N) Equip B"),
    ("Act 3 (N)", "Perfect Gem", "Flawless Gem", "Runes 10", "Runes 11", "Act 3 (N) Equip B"),
    ("Act 4 (N)", "Perfect Gem", "Flawless Gem", "Runes 11", "Runes 12", "Act 4 (N) Equip B"),
    ("Act 5 (N)", "Perfect Gem", "Flawless Gem", "Runes 12", "Runes 13", "Act 5 (N) Equip B"),
    ("Act 1 (H)", "Perfect Gem", "Flawless Gem", "Runes 13", "Runes 14", "Act 1 (H) Equip B"),
    ("Act 2 (H)", "Perfect Gem", "Flawless Gem", "Runes 14", "Runes 15", "Act 2 (H) Equip B"),
    ("Act 3 (H)", "Perfect Gem", "Flawless Gem", "Runes 15", "Runes 16", "Act 3 (H) Equip B"),
    ("Act 4 (H)", "Perfect Gem", "Flawless Gem", "Runes 16", "Runes 17", "Act 4 (H) Equip B"),
    ("Act 5 (H)", "Perfect Gem", "Flawless Gem", "Runes 16", "Runes 17", "Act 5 (H) Equip C"),
]


def _clear_items(row: Dict[str, str]) -> None:
    for i in range(1, 11):
        row[f"Item{i}"] = ""
        row[f"Prob{i}"] = ""


def _set_items(row: Dict[str, str], items: List[Tuple[str, str]]) -> None:
    _clear_items(row)
    for idx, (item, prob) in enumerate(items[:10], start=1):
        row[f"Item{idx}"] = item
        row[f"Prob{idx}"] = prob


def _make_blank_row(headers: List[str], tc_name: str) -> Dict[str, str]:
    r = {h: "" for h in headers}
    r["Treasure Class"] = tc_name
    r["*eol"] = "0"
    return r


def build_treasureclass(cfg: dict) -> str:
    headers, rows = read_excel_tsv("treasureclassex.txt")
    by_tc = {r["Treasure Class"]: r for r in rows if r.get("Treasure Class")}

    econ = cfg.get("economy", {})
    gold_mult = int(round(256 * float(econ.get("gold_pile_multiplier", 4.8))))
    gold_item = f'"gld,mul={gold_mult}"'

    # 1. Remove random charms (cm1, cm2, cm3) from Jewelry A, B, C (45% Ring / 30% Amulet / 25% Jewel)
    for jtc in ("Jewelry A", "Jewelry B", "Jewelry C"):
        if jtc in by_tc:
            _set_items(by_tc[jtc], [("rin", "9"), ("amu", "6"), ("jew", "5")])

    # Ensure Ammo (aqv / cqv) always rolls Magic-only when dropped by monsters
    if "Ammo" in by_tc:
        by_tc["Ammo"]["Magic"] = "1024"
        by_tc["Ammo"]["Rare"] = ""

    # 2. Strip ALL potions (including rvs/rvl) from Potion/Hpotion/Cpot/Misc/Magic/Junk TCs
    for i in range(1, 7):
        for prefix in ("Hpotion", "Potion"):
            tc = f"{prefix} {i}"
            if tc in by_tc:
                _set_items(by_tc[tc], [(gold_item, "4"), ("isc", "2"), ("tsc", "1")])

    for i in range(3):
        tc = f"Misc {i}"
        if tc in by_tc:
            _set_items(by_tc[tc], [(gold_item, "2"), ("tsc", "1"), ("isc", "3")])

    # Remove mp1..mp5 and rvs/rvl from Act X Magic A/B/C and Cpot
    for r in rows:
        tc = r["Treasure Class"]
        if "Magic " in tc and r.get("group") == "4":
            _set_items(r, [("tsc", "1"), ("isc", "3")])
        elif r.get("group") == "12":  # Cpot
            _set_items(r, [(gold_item, "1")])

    # Update Act X Junk to clean gold/ammo only (zero potions, 5% Ammo / 95% Gold)
    for r in rows:
        tc = r["Treasure Class"]
        if tc.endswith("Junk"):
            _set_items(r, [(gold_item, "19"), ("Ammo", "1")])

    # Catch-all sweep: ensure zero potion or key item codes exist anywhere in treasureclassex.txt
    banned_potions = {
        "key",
        "rvs", "rvl",
        "hp1", "hp2", "hp3", "hp4", "hp5",
        "mp1", "mp2", "mp3", "mp4", "mp5",
        "wms", "yps", "vps",
        "opl", "opm", "ops", "gpl", "gpm", "gps",
    }
    for r in rows:
        for i in range(1, 11):
            if r.get(f"Item{i}") in banned_potions:
                r[f"Item{i}"] = gold_item

    # 3. Disable Sunder Charms & remove references
    if "Sunder Charms" in by_tc:
        _set_items(by_tc["Sunder Charms"], [(gold_item, "1")])
        by_tc["Sunder Charms"]["ConditionCalc"] = "0"

    for r in rows:
        for i in range(1, 11):
            if r.get(f"Item{i}") in ("Sunder Charms", "pk1", "pk2", "pk3"):
                r[f"Item{i}"] = gold_item

    # 4. Flatten Runes 1..17 cascade
    cascade_probs = {
        2: "2",
        3: "3",
        4: "4",
        5: "5",
        6: "6",
        7: "7",
        8: "8",
        9: "9",
        10: "10",
        11: "11",
        12: "12",
        13: "13",
        14: "14",
        15: "15",
        16: "16",
        17: "8",
    }
    for r_idx, c_prob in cascade_probs.items():
        rtc = f"Runes {r_idx}"
        if rtc in by_tc:
            row = by_tc[rtc]
            if r_idx < 17:
                row["Prob3"] = c_prob
            else:
                row["Prob2"] = c_prob

    # Boost Rune weights in Act X Good TCs
    for act_prefix, g1, g2, r1, r2, _ in ACTS:
        gtc = f"{act_prefix} Good"
        if gtc in by_tc:
            _set_items(
                by_tc[gtc],
                [
                    ("Jewelry C" if act_prefix != "Act 1" else "Jewelry A", "30"),
                    (g1, "15"),
                    (g2, "25"),
                    (r1, "20"),
                    (r2, "20"),
                ],
            )

    # 5. Create custom sub-tables: Act X GemRune & Staged Act Boss Unique Charm 1..5
    # Like Annihilus in ROP (H), Act Boss Charm TCs reference the exact Unique Charm index names
    # directly (never the base item code 'cm1'), so it is physically impossible for a Magic Charm
    # to ever drop. Each has NoDrop=85 and total Unique Charm weight=15 (15% drop chance).
    custom_rows: List[Dict[str, str]] = []
    for act_prefix, g1, g2, r1, r2, _ in ACTS:
        gr_name = f"{act_prefix} GemRune"
        if gr_name not in by_tc:
            gr_row = _make_blank_row(headers, gr_name)
            gr_row["Picks"] = "1"
            gr_row["NoDrop"] = "0"
            _set_items(gr_row, [(g1, "15"), (g2, "35"), (r1, "25"), (r2, "25")])
            custom_rows.append(gr_row)
            by_tc[gr_name] = gr_row

    boss_charm_tcs = [
        ("Act Boss Charm 1", [("Signet of the Maiden", "15")]),
        ("Act Boss Charm 2", [("Signet of the Maiden", "5"), ("Gheed's Fortune", "10")]),
        ("Act Boss Charm 3", [("Signet of the Maiden", "3"), ("Gheed's Fortune", "5"), ("Carapace of Pain", "7")]),
        ("Act Boss Charm 4", [("Gheed's Fortune", "3"), ("Carapace of Pain", "5"), ("Soulstone Shard", "7")]),
        ("Act Boss Charm 5", [("Carapace of Pain", "3"), ("Soulstone Shard", "5"), ("Eye of Destruction", "7")]),
    ]
    for ctc_name, ctc_items in boss_charm_tcs:
        if ctc_name not in by_tc:
            charm_row = _make_blank_row(headers, ctc_name)
            charm_row["Picks"] = "1"
            charm_row["Unique"] = "1024"
            charm_row["NoDrop"] = "85"
            _set_items(charm_row, ctc_items)
            custom_rows.append(charm_row)
            by_tc[ctc_name] = charm_row

    # Insert custom sub-tables right after Runes 17 so they are defined before use!
    runes17_idx = next(i for i, r in enumerate(rows) if r["Treasure Class"] == "Runes 17")
    for offset, crow in enumerate(custom_rows):
        rows.insert(runes17_idx + 1 + offset, crow)

    # 6. Tier 1 — Normal Monster TCs (H2H, Cast, Miss, Wraith, Quill, Swarm, Cow)
    # Halve equipment drop weights and increase NoDrop by 1.5x, while preserving full 'Good'
    # (Jewelry/Gem/Rune) weights so normal monsters periodically drop Rings, Amulets, Gems, and Runes.
    for r in rows:
        grp = r.get("group", "")
        tc = r["Treasure Class"]
        if grp in ("7", "8", "9", "10", "16", "17") or tc.startswith("Cow"):
            if r.get("NoDrop"):
                try:
                    r["NoDrop"] = str(int(round(int(r["NoDrop"]) * 1.5)))
                except ValueError:
                    pass
            for i in range(1, 11):
                item_val = r.get(f"Item{i}", "")
                prob_val = r.get(f"Prob{i}", "")
                if item_val == "gld":
                    r[f"Item{i}"] = gold_item
                elif (
                    item_val
                    and not item_val.startswith('"gld')
                    and not item_val.endswith("Junk")
                    and not item_val.endswith("Good")
                ):
                    if prob_val:
                        try:
                            r[f"Prob{i}"] = str(max(1, int(int(prob_val) * 0.5)))
                        except ValueError:
                            pass

    # 7. Tier 2 — Zone Uniques (Act X Unique A/B/C) & Champions (Act X Champ A/B/C)
    # Configure Uitem (Guaranteed 100% roll: 65% Equip / 25% GemRune / 10% Jewelry),
    # Citem (Champion Guaranteed 100% roll: 65% Equip / 25% GemRune / 10% Jewelry),
    # and Cpot (50% Bonus roll: NoDrop=20, 65% Equip / 25% GemRune / 10% Jewelry when it hits).
    for act_prefix, _, _, _, _, equip_fallback in ACTS:
        gr_name = f"{act_prefix} GemRune"
        j_tc = "Jewelry A" if act_prefix == "Act 1" else "Jewelry C"
        for letter in ("A", "B", "C"):
            eq_tc = f"{act_prefix} Equip {letter}"
            if eq_tc not in by_tc:
                eq_tc = equip_fallback

            uitem = f"{act_prefix} Uitem {letter}"
            if uitem in by_tc:
                r = by_tc[uitem]
                r["Picks"] = "1"
                r["Unique"] = "850"
                r["Set"] = "850"
                r["Rare"] = "950"
                r["Magic"] = "1024"
                r["NoDrop"] = "0"
                _set_items(r, [(eq_tc, "13"), (gr_name, "5"), (j_tc, "2")])

            citem = f"{act_prefix} Citem {letter}"
            if citem in by_tc:
                r = by_tc[citem]
                r["Picks"] = "1"
                r["Unique"] = "820"
                r["Set"] = "820"
                r["Rare"] = "920"
                r["Magic"] = "1024"
                r["NoDrop"] = "0"
                _set_items(r, [(eq_tc, "13"), (gr_name, "5"), (j_tc, "2")])

            cpot = f"{act_prefix} Cpot {letter}"
            if cpot in by_tc:
                r = by_tc[cpot]
                r["Picks"] = "1"
                r["Unique"] = "850"
                r["Set"] = "850"
                r["Rare"] = "950"
                r["Magic"] = "1024"
                r["NoDrop"] = "20"  # 20 / (13 + 5 + 2 + 20) = 50% chance for bonus drop
                _set_items(r, [(eq_tc, "13"), (gr_name, "5"), (j_tc, "2")])

    # Also update any Shard Uitem/Citem rows
    for tc_shard, eq_shard, gr_shard in [
        ("Act 1 (H) Citem A Shard", "Act 1 (H) Equip A", "Act 1 (H) GemRune"),
        ("Act 1 (H) Uitem A Shard", "Act 1 (H) Equip A", "Act 1 (H) GemRune"),
    ]:
        if tc_shard in by_tc:
            r = by_tc[tc_shard]
            r["Picks"] = "1"
            r["Unique"] = "850"
            r["Set"] = "850"
            r["Rare"] = "950"
            r["Magic"] = "1024"
            r["NoDrop"] = "0"
            _set_items(r, [(eq_shard, "13"), (gr_shard, "5"), ("Jewelry C", "2")])

    # Wire Tier 2 (Uniques & Champions): 1 Guaranteed Roll + 1 Bonus (50%) Roll = 1-2 drops (75% Item / 25% GemRune)
    for act_prefix, _, _, _, _, _ in ACTS:
        for letter in ("A", "B", "C"):
            uitem = f"{act_prefix} Uitem {letter}"
            if uitem not in by_tc:
                uitem = f"{act_prefix} Uitem B"
            citem = f"{act_prefix} Citem {letter}"
            if citem not in by_tc:
                citem = f"{act_prefix} Citem B"
            cpot = f"{act_prefix} Cpot {letter}"
            if cpot not in by_tc:
                cpot = f"{act_prefix} Cpot B"

            utc = f"{act_prefix} Unique {letter}"
            if utc in by_tc:
                row = by_tc[utc]
                row["Picks"] = "-2"
                row["Unique"] = "850"
                row["Set"] = "850"
                row["Rare"] = "950"
                row["Magic"] = "1024"
                row["NoDrop"] = "0"
                _set_items(row, [(uitem, "1"), (cpot, "1")])

            ctc = f"{act_prefix} Champ {letter}"
            if ctc in by_tc:
                row = by_tc[ctc]
                row["Picks"] = "-2"
                row["Unique"] = "820"
                row["Set"] = "820"
                row["Rare"] = "920"
                row["Magic"] = "1024"
                row["NoDrop"] = "0"
                _set_items(row, [(citem, "1"), (cpot, "1")])

    # 8. Tier 3 — SuperUniques: 2 Guaranteed Rolls + 1 Bonus (50%) Roll = 2-3 drops (75% Item / 25% GemRune)
    for act_prefix, _, _, _, _, _ in ACTS:
        for suffix in ("A", "B", "C", "Ax", "Bx", "Cx"):
            stc = f"{act_prefix} Super {suffix}"
            letter = suffix[0]
            uitem = f"{act_prefix} Uitem {letter}"
            if uitem not in by_tc:
                uitem = f"{act_prefix} Uitem B"
            cpot = f"{act_prefix} Cpot {letter}"
            if cpot not in by_tc:
                cpot = f"{act_prefix} Cpot B"
            if stc in by_tc:
                row = by_tc[stc]
                row["Picks"] = "-3"
                row["Unique"] = "920"
                row["Set"] = "920"
                row["Rare"] = "980"
                row["Magic"] = "1024"
                row["NoDrop"] = "0"
                _set_items(row, [(uitem, "2"), (cpot, "1")])

    # Named SuperUniques: Blood Raven, Griswold, Smith, Radament, Summoner, Council, Izual, Haphesto, Nihlathak, Cow King
    named_supers = [
        ("Blood Raven", "Act 1"),
        ("Griswold", "Act 1"),
        ("Smith", "Act 1"),
        ("Radament", "Act 2"),
        ("Summoner", "Act 2"),
        ("Council", "Act 3"),
        ("Izual", "Act 4"),
        ("Haphesto", "Act 4"),
        ("Nihlathak", "Act 5"),
        ("Cow King", "Act 1"),
    ]
    for base_name, base_act in named_supers:
        for diff_suffix in ("", " (N)", " (H)"):
            act_key = f"{base_act}{diff_suffix}"
            uitem = f"{act_key} Uitem C" if f"{act_key} Uitem C" in by_tc else f"{act_key} Uitem B"
            cpot = f"{act_key} Cpot C" if f"{act_key} Cpot C" in by_tc else f"{act_key} Cpot B"
            for r in rows:
                tc = r["Treasure Class"]
                if tc == f"{base_name}{diff_suffix}" or (
                    tc.startswith(f"{base_name}{diff_suffix} Desecrated")
                    and r.get("Picks") != "-1"
                ) or tc.startswith(f"{base_name} Item{diff_suffix}"):
                    r["Picks"] = "-3"
                    r["Unique"] = "920"
                    r["Set"] = "920"
                    r["Rare"] = "980"
                    r["Magic"] = "1024"
                    r["NoDrop"] = "0"
                    _set_items(r, [(uitem, "2"), (cpot, "1")])

    # Countess: 1 Guaranteed Rune + 1-2 Drops (75% Item / 25% GemRune) = 2-3 total drops
    for diff_suffix, rune_tc, act_key in [
        ("", "Runes 4", "Act 1"),
        (" (N)", "Runes 9", "Act 1 (N)"),
        (" (H)", "Runes 14", "Act 1 (H)"),
    ]:
        cr_tc = f"Countess Rune{diff_suffix}"
        if cr_tc in by_tc:
            by_tc[cr_tc]["Picks"] = "1"
            by_tc[cr_tc]["NoDrop"] = "0"
            _set_items(by_tc[cr_tc], [(rune_tc, "1")])
        uitem = f"{act_key} Uitem C"
        cpot = f"{act_key} Cpot C"
        for r in rows:
            tc = r["Treasure Class"]
            if tc == f"Countess Item{diff_suffix}" or tc.startswith(f"Countess Item{diff_suffix} Desecrated"):
                r["Picks"] = "-2"
                r["Unique"] = "920"
                r["Set"] = "920"
                r["Rare"] = "980"
                r["Magic"] = "1024"
                r["NoDrop"] = "0"
                _set_items(r, [(uitem, "1"), (cpot, "1")])

    # 9. Tier 4 — Act Bosses (Andariel, Duriel, Mephisto, Diablo, Baal + q & Desecrated):
    # 3 Guaranteed Rolls + 1 Bonus (50%) Roll = 3-4 drops (75% Item / 25% GemRune) + 1 Unique Boss Charm roll
    boss_configs = [
        ("Andariel", ("", "Act 2 Uitem A", "Act 2 Cpot A", "Act Boss Charm 1"), (" (N)", "Act 2 (N) Uitem A", "Act 2 (N) Cpot A", "Act Boss Charm 3"), (" (H)", "Act 2 (H) Uitem A", "Act 2 (H) Cpot A", "Act Boss Charm 4")),
        ("Duriel", ("", "Act 3 Uitem A", "Act 3 Cpot A", "Act Boss Charm 1"), (" (N)", "Act 3 (N) Uitem A", "Act 3 (N) Cpot A", "Act Boss Charm 3"), (" (H)", "Act 3 (H) Uitem A", "Act 3 (H) Cpot A", "Act Boss Charm 5")),
        ("Mephisto", ("", "Act 4 Uitem A", "Act 4 Cpot A", "Act Boss Charm 2"), (" (N)", "Act 4 (N) Uitem A", "Act 4 (N) Cpot A", "Act Boss Charm 3"), (" (H)", "Act 4 (H) Uitem A", "Act 4 (H) Cpot A", "Act Boss Charm 5")),
        ("Diablo", ("", "Act 5 Uitem A", "Act 5 Cpot A", "Act Boss Charm 2"), (" (N)", "Act 5 (N) Uitem A", "Act 5 (N) Cpot A", "Act Boss Charm 4"), (" (H)", "Act 5 (H) Uitem A", "Act 5 (H) Cpot A", "Act Boss Charm 5")),
        ("Baal", ("", "Act 1 (N) Uitem A", "Act 1 (N) Cpot A", "Act Boss Charm 2"), (" (N)", "Act 1 (H) Uitem A", "Act 1 (H) Cpot A", "Act Boss Charm 4"), (" (H)", "Act 5 (H) Uitem C", "Act 5 (H) Cpot C", "Act Boss Charm 5")),
    ]
    for boss, cfg_n, cfg_nm, cfg_h in boss_configs:
        for diff_suffix, boss_uitem, boss_cpot, boss_charm_tc in (cfg_n, cfg_nm, cfg_h):
            for r in rows:
                tc = r["Treasure Class"]
                is_match = (
                    tc in (f"{boss}{diff_suffix}", f"{boss}q{diff_suffix}", f"{boss}{diff_suffix} - Base", f"{boss}q{diff_suffix} - Base")
                    or (tc.startswith(f"{boss}{diff_suffix} Desecrated") and r.get("Picks") != "-1")
                    or (tc.startswith(f"{boss}q{diff_suffix} Desecrated") and r.get("Picks") != "-1")
                    or tc.startswith(f"{boss} Item{diff_suffix}")
                    or tc.startswith(f"{boss}q Item{diff_suffix}")
                    or tc.startswith(f"{boss}{diff_suffix} - Base Desecrated")
                )
                if is_match:
                    r["Picks"] = "-5"
                    r["Unique"] = "985"
                    r["Set"] = "985"
                    r["Rare"] = "1024"
                    r["Magic"] = "1024"
                    r["NoDrop"] = "0"
                    _set_items(
                        r,
                        [
                            (boss_uitem, "3"),
                            (boss_cpot, "1"),
                            (boss_charm_tc, "1"),
                        ],
                    )

    # 10. Strip all equipment/gems/potions from Chest TCs (Gold-only fallback)
    for r in rows:
        tc = r["Treasure Class"]
        if "Chest" in tc:
            r["Picks"] = "1"
            r["NoDrop"] = "0"
            _set_items(r, [(gold_item, "1")])

    # TEMPORARY QA BOOST: Make Act 1 Blood Moor monsters drop Horadric Cube + Gems + Runes + Uniques
    if econ.get("qa_blood_moor_boost", False):
        if "QA Craft Kit" not in by_tc:
            qac = _make_blank_row(headers, "QA Craft Kit")
            qac["Picks"] = "-6"
            qac["NoDrop"] = "0"
            qac["Unique"] = "1024"
            _set_items(
                qac,
                [
                    ("box", "1"),
                    ("Chipped Gem", "1"),
                    ("Perfect Gem", "1"),
                    ("Runes 3", "2"),
                    ("Act 1 Equip B", "1"),
                ],
            )
            r17_idx = next(i for i, r in enumerate(rows) if r["Treasure Class"] == "Runes 17")
            rows.insert(r17_idx + 1, qac)
            by_tc["QA Craft Kit"] = qac
        for qa_tc in ("Act 1 H2H A", "Act 1 H2H B", "Act 1 Cast A", "Act 1 Miss A", "Quill 1"):
            if qa_tc in by_tc:
                by_tc[qa_tc]["Picks"] = "1"
                by_tc[qa_tc]["NoDrop"] = "0"
                _set_items(by_tc[qa_tc], [("QA Craft Kit", "1")])

    tc_path = write_excel_tsv("treasureclassex.txt", headers, rows)
    obj_path = build_objects(cfg)
    return f"{tc_path}, {obj_path}"


def build_objects(cfg: dict) -> str:
    """
    Disable generic non-quest loot containers (Chests, Caskets, Urns, Barrels, Crates/Rocks/Logs/Corpses,
    Armor Stands, Weapon Racks, Bookshelves, Jungle Stashes) in objects.txt while preserving all
    Quest Chests/Objects, Shrines, Wells, Doors, Portals, and Waypoints.
    """
    headers, rows = read_excel_tsv("objects.txt")
    generic_container_ops = {"1", "3", "4", "5", "7", "14", "19", "20", "26", "30", "33", "51"}
    preserve_ids = {"383", "384", "385"}  # TrappedSoul / Cain start position
    for r in rows:
        if r.get("OperateFn") in generic_container_ops and r.get("*ID") not in preserve_ids:
            r["Selectable0"] = "0"
            r["PopulateFn"] = "0"
    return write_excel_tsv("objects.txt", headers, rows)

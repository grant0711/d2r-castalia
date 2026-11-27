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
    # (act_prefix, gem_minority_30pct, gem_majority_70pct, rune_tc_early, rune_tc_late, equip_fallback)
    # Aligned with Gem levelreqs: Chipped (1), Flawed (15), Normal (30), Flawless (45), Perfect (60)
    # Each higher gem tier first debuts as the minority drop (g1: 15/50 = 30% in GemRune, 15/40 = 37.5% in Good)
    # right when monster levels approach its levelreq, then becomes the majority staple drop (g2: 62.5-70%)
    # in the next Act once players reach that level requirement:
    # - Act 1 (mlvl 1..12): 100% Chipped (req 1)
    # - Act 2 (mlvl 12..18): Flawed (req 15) debuts at 30-37.5% alongside Chipped
    # - Act 3 (mlvl 21..25): Flawed becomes 62.5-70% staple alongside Chipped
    # - Act 4 (mlvl 26..28): Normal (req 30) debuts at 30-37.5% alongside Flawed
    # - Act 5 (mlvl 24..43): Normal becomes 62.5-70% staple alongside Flawed (0% Flawless in Normal)
    # - Act 1 (N) (mlvl 36..43): Flawless (req 45) debuts at 30-37.5% alongside Normal
    # - Act 2 (N) (mlvl 43..49): Flawless becomes 62.5-70% staple alongside Normal (0% Perfect in Act 2 NM)
    # - Act 3..5 (N) (mlvl 49..66): Perfect (req 60) debuts in Act 3 NM at 30-37.5% alongside Flawless
    # - Act 1..5 (H) (mlvl 67..85): Perfect becomes 62.5-70% staple alongside Flawless
    ("Act 1", "Chipped Gem", "Chipped Gem", "Runes 1", "Runes 2", "Act 1 Equip B"),
    ("Act 2", "Flawed Gem", "Chipped Gem", "Runes 2", "Runes 3", "Act 2 Equip B"),
    ("Act 3", "Chipped Gem", "Flawed Gem", "Runes 4", "Runes 5", "Act 3 Equip B"),
    ("Act 4", "Normal Gem", "Flawed Gem", "Runes 6", "Runes 7", "Act 4 Equip B"),
    ("Act 5", "Flawed Gem", "Normal Gem", "Runes 7", "Runes 8", "Act 5 Equip B"),
    ("Act 1 (N)", "Flawless Gem", "Normal Gem", "Runes 8", "Runes 9", "Act 1 (N) Equip B"),
    ("Act 2 (N)", "Normal Gem", "Flawless Gem", "Runes 9", "Runes 10", "Act 2 (N) Equip B"),
    ("Act 3 (N)", "Perfect Gem", "Flawless Gem", "Runes 10", "Runes 11", "Act 3 (N) Equip B"),
    ("Act 4 (N)", "Perfect Gem", "Flawless Gem", "Runes 11", "Runes 12", "Act 4 (N) Equip B"),
    ("Act 5 (N)", "Perfect Gem", "Flawless Gem", "Runes 12", "Runes 13", "Act 5 (N) Equip B"),
    ("Act 1 (H)", "Flawless Gem", "Perfect Gem", "Runes 13", "Runes 14", "Act 1 (H) Equip B"),
    ("Act 2 (H)", "Flawless Gem", "Perfect Gem", "Runes 14", "Runes 15", "Act 2 (H) Equip B"),
    ("Act 3 (H)", "Flawless Gem", "Perfect Gem", "Runes 15", "Runes 16", "Act 3 (H) Equip B"),
    ("Act 4 (H)", "Flawless Gem", "Perfect Gem", "Runes 16", "Runes 17", "Act 4 (H) Equip B"),
    ("Act 5 (H)", "Flawless Gem", "Perfect Gem", "Runes 16", "Runes 17", "Act 5 (H) Equip C"),
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
    gold_mult = int(round(256 * float(econ.get("gold_pile_multiplier", 2.4))))
    gold_mult_nm = int(round(256 * float(econ.get("gold_pile_multiplier_nm", 4.0))))
    gold_mult_h = int(round(256 * float(econ.get("gold_pile_multiplier_hell", 7.0))))
    gold_item = f'"gld,mul={gold_mult}"'
    gold_item_nm = f'"gld,mul={gold_mult_nm}"'
    gold_item_h = f'"gld,mul={gold_mult_h}"'

    def _gold_for_tc(tc_str: str) -> str:
        if "(H)" in tc_str:
            return gold_item_h
        if "(N)" in tc_str:
            return gold_item_nm
        return gold_item

    # 1. Remove random charms (cm1, cm2, cm3) from Jewelry A, B, C (45% Ring / 30% Amulet / 25% Jewel)
    for jtc in ("Jewelry A", "Jewelry B", "Jewelry C"):
        if jtc in by_tc:
            _set_items(by_tc[jtc], [("rin", "9"), ("amu", "6"), ("jew", "5")])

    # Ensure Ammo (aqv / cqv) always rolls Magic-only when dropped by monsters
    if "Ammo" in by_tc:
        by_tc["Ammo"]["Magic"] = "1024"
        by_tc["Ammo"]["Rare"] = ""

    # 2. Strip ALL potions (including rvs/rvl) and Town Portal scrolls (tsc) from Potion/Hpotion/Cpot/Misc/Magic/Junk TCs
    for i in range(1, 7):
        for prefix in ("Hpotion", "Potion"):
            tc = f"{prefix} {i}"
            if tc in by_tc:
                _set_items(by_tc[tc], [(gold_item, "5"), ("isc", "2")])

    for i in range(3):
        tc = f"Misc {i}"
        if tc in by_tc:
            _set_items(by_tc[tc], [(gold_item, "3"), ("isc", "3")])

    # Remove mp1..mp5, rvs/rvl, and tsc from Act X Magic A/B/C and Cpot
    for r in rows:
        tc = r["Treasure Class"]
        if "Magic " in tc and r.get("group") == "4":
            _set_items(r, [(_gold_for_tc(tc), "1"), ("isc", "3")])
        elif r.get("group") == "12":  # Cpot
            _set_items(r, [(_gold_for_tc(tc), "1")])

    # Act-scaled potion/elixir table (shared by Act X Potion and Act X Chest Roll; zero Rejuvs)
    act_potions_by_act = {
        "Act 1": ("hp1", "mp1", "wms", "yps", "vps"),
        "Act 2": ("hp1", "mp1", "wms", "yps", "vps"),
        "Act 3": ("hp1", "mp1", "wms", "yps", "vps"),
        "Act 4": ("hp2", "mp2", "wms", "yps", "vps"),
        "Act 5": ("hp2", "mp2", "wms", "yps", "vps"),
        "Act 1 (N)": ("hp3", "mp3", "wm2", "yp2", "vp2"),
        "Act 2 (N)": ("hp3", "mp3", "wm2", "yp2", "vp2"),
        "Act 3 (N)": ("hp4", "mp4", "wm2", "yp2", "vp2"),
        "Act 4 (N)": ("hp4", "mp4", "wm2", "yp2", "vp2"),
        "Act 5 (N)": ("hp4", "mp4", "wm2", "yp2", "vp2"),
        "Act 1 (H)": ("hp5", "mp5", "wm3", "yp3", "vp3"),
        "Act 2 (H)": ("hp5", "mp5", "wm3", "yp3", "vp3"),
        "Act 3 (H)": ("hp5", "mp5", "wm3", "yp3", "vp3"),
        "Act 4 (H)": ("hp5", "mp5", "wm3", "yp3", "vp3"),
        "Act 5 (H)": ("hp5", "mp5", "wm3", "yp3", "vp3"),
    }

    # Update Act X Junk to clean Gold / light Potion trickle / Ammo (85% Gold / 10% Potion / 5% Ammo)
    for r in rows:
        tc = r["Treasure Class"]
        if tc.endswith("Junk"):
            act_p = tc[: -len(" Junk")]
            if act_p in act_potions_by_act:
                _set_items(r, [(_gold_for_tc(tc), "17"), (f"{act_p} Potion", "2"), ("Ammo", "1")])
            else:
                _set_items(r, [(_gold_for_tc(tc), "19"), ("Ammo", "1")])

    # Catch-all sweep: ensure zero potion, key, or Town Portal item codes exist anywhere in treasureclassex.txt
    banned_potions = {
        "key",
        "tsc", "tbk",
        "rvs", "rvl",
        "hp1", "hp2", "hp3", "hp4", "hp5",
        "mp1", "mp2", "mp3", "mp4", "mp5",
        "wms", "yps", "vps",
        "opl", "opm", "ops", "gpl", "gpm", "gps",
    }
    for r in rows:
        tc = r["Treasure Class"]
        for i in range(1, 11):
            if r.get(f"Item{i}") in banned_potions:
                r[f"Item{i}"] = _gold_for_tc(tc)

    # 3. Disable Sunder Charms & remove references
    if "Sunder Charms" in by_tc:
        _set_items(by_tc["Sunder Charms"], [(gold_item, "1")])
        by_tc["Sunder Charms"]["ConditionCalc"] = "0"

    for r in rows:
        tc = r["Treasure Class"]
        for i in range(1, 11):
            if r.get(f"Item{i}") in ("Sunder Charms", "pk1", "pk2", "pk3"):
                r[f"Item{i}"] = _gold_for_tc(tc)

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

    # 5. Create custom sub-tables: Act X GemRune, Skeleton-biased Gem/Good/GemRune tables, & Staged Act Boss Unique Charm 1..5
    # Like Annihilus in ROP (H), Act Boss Charm TCs reference the exact Unique Charm index names
    # directly (never the base item code 'cm1'), so it is physically impossible for a Magic Charm
    # to ever drop. Each has NoDrop=85 and total Unique Charm weight=15 (15% drop chance).
    custom_rows: List[Dict[str, str]] = []
    for gem_tc_name in ("Chipped Gem", "Flawed Gem", "Normal Gem", "Flawless Gem", "Perfect Gem"):
        skel_gem_tc = f"{gem_tc_name} Skel"
        if gem_tc_name in by_tc and skel_gem_tc not in by_tc:
            sg_row = dict(by_tc[gem_tc_name])
            sg_row["Treasure Class"] = skel_gem_tc
            # Bump Skull weight (Item7: skc..skz) from 2 (10.0%) to 6 (6/24 = 25.0% of Gem drops)
            # so Skeletons remain 75% regular gems while subtly favoring Skulls by 2.5x!
            sg_row["Prob7"] = "6"
            custom_rows.append(sg_row)
            by_tc[skel_gem_tc] = sg_row

    for act_prefix, g1, g2, r1, r2, _ in ACTS:
        gr_name = f"{act_prefix} GemRune"
        if gr_name not in by_tc:
            gr_row = _make_blank_row(headers, gr_name)
            gr_row["Picks"] = "1"
            gr_row["NoDrop"] = "0"
            _set_items(gr_row, [(g1, "15"), (g2, "35"), (r1, "25"), (r2, "25")])
            custom_rows.append(gr_row)
            by_tc[gr_name] = gr_row

        gr_skel_name = f"{act_prefix} GemRune Skel"
        if gr_skel_name not in by_tc:
            grs_row = _make_blank_row(headers, gr_skel_name)
            grs_row["Picks"] = "1"
            grs_row["NoDrop"] = "0"
            _set_items(grs_row, [(f"{g1} Skel", "15"), (f"{g2} Skel", "35"), (r1, "25"), (r2, "25")])
            custom_rows.append(grs_row)
            by_tc[gr_skel_name] = grs_row

        good_skel_name = f"{act_prefix} Good Skel"
        if good_skel_name not in by_tc:
            gds_row = _make_blank_row(headers, good_skel_name)
            gds_row["Picks"] = "1"
            gds_row["NoDrop"] = "0"
            _set_items(
                gds_row,
                [
                    ("Jewelry C" if act_prefix != "Act 1" else "Jewelry A", "30"),
                    (f"{g1} Skel", "18"),
                    (f"{g2} Skel", "32"),
                    (r1, "20"),
                    (r2, "20"),
                ],
            )
            custom_rows.append(gds_row)
            by_tc[good_skel_name] = gds_row

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

    # 5b. Build cascading Lockbox TCs (Act 1 Lockbox .. Act 5 (H) Lockbox) across all 536 Unique/Set Lockboxes:
    # - Normal (Act 1..5 Lockbox): drops only Tier 1 ("Crude Wooden Lockbox")
    # - Nightmare (Act 1 (N)..Act 5 (N) Lockbox): cascades across Tier 2 ("Reinforced Iron Lockbox") & Tier 1
    # - Hell (Act 1 (H)..Act 5 (H) Lockbox): cascades across Tier 3 ("Ornate Gilded Lockbox"), Tier 2, & Tier 1
    from mod_builder.lockboxes import get_lockbox_registry

    lb_registry = get_lockbox_registry()
    lb_by_act: Dict[str, List[Tuple[str, int]]] = {act_p: [] for act_p, _, _, _, _, _ in ACTS}
    for entry in lb_registry:
        lb_by_act[str(entry["act_prefix"])].append((str(entry["code"]), int(entry["weight"])))

    prev_lockbox_tc = ""
    for act_idx, (act_p, _, _, _, _, _) in enumerate(ACTS):
        act_items = lb_by_act[act_p]
        leaf_entries: List[Tuple[str, str]] = []
        # Chunk into groups of <= 8 items per leaf TC (since TreasureClassEx has 10 item slots)
        for chunk_i in range(0, len(act_items), 8):
            chunk = act_items[chunk_i : chunk_i + 8]
            leaf_name = f"{act_p} Lockbox Leaf {chunk_i // 8 + 1}"
            leaf_row = _make_blank_row(headers, leaf_name)
            leaf_row["Picks"] = "1"
            leaf_row["NoDrop"] = "0"
            _set_items(leaf_row, [(c, str(w)) for c, w in chunk])
            custom_rows.append(leaf_row)
            by_tc[leaf_name] = leaf_row
            chunk_weight = sum(w for _, w in chunk)
            leaf_entries.append((leaf_name, str(chunk_weight)))

        pool_name = f"{act_p} Lockbox Pool"
        pool_row = _make_blank_row(headers, pool_name)
        pool_row["Picks"] = "1"
        pool_row["NoDrop"] = "0"
        _set_items(pool_row, leaf_entries)
        custom_rows.append(pool_row)
        by_tc[pool_name] = pool_row

        lb_tc_name = f"{act_p} Lockbox"
        lb_row = _make_blank_row(headers, lb_tc_name)
        lb_row["Picks"] = "1"
        lb_row["NoDrop"] = "0"
        if act_idx == 0:
            _set_items(lb_row, [(pool_name, "100")])
        else:
            _set_items(lb_row, [(pool_name, "65"), (prev_lockbox_tc, "35")])
        custom_rows.append(lb_row)
        by_tc[lb_tc_name] = lb_row
        prev_lockbox_tc = lb_tc_name

    # Act X Potion sub-tables (38.5% HP / 38.5% MP / 23.1% Elixirs, zero Rejuvs)
    for act_p, (hp_c, mp_c, wm_c, yp_c, vp_c) in act_potions_by_act.items():
        pot_tc_name = f"{act_p} Potion"
        pot_row = _make_blank_row(headers, pot_tc_name)
        pot_row["Picks"] = "1"
        pot_row["NoDrop"] = "0"
        _set_items(pot_row, [(hp_c, "10"), (mp_c, "10"), (wm_c, "2"), (yp_c, "2"), (vp_c, "2")])
        custom_rows.append(pot_row)
        by_tc[pot_tc_name] = pot_row

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
                if item_val == "gld" or item_val.startswith('"gld'):
                    r[f"Item{i}"] = _gold_for_tc(tc)
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
                r["NoDrop"] = "20"  # 20 / (20 + 20) = 50% at P1, 75% at P2, 87.5% at P3, 96.9% at P5
                _set_items(r, [(eq_tc, "13"), (gr_name, "5"), (j_tc, "2")])

                # Co-op scaling 25% bonus roll for Champions & Zone Uniques:
                # 20 / (20 + 60) = 25% at P1 -> 43.75% at P2 -> 57.8% at P3 -> 76.3% at P5
                cpot25 = f"{act_prefix} Cpot25 {letter}"
                if cpot25 not in by_tc:
                    r25 = dict(r)
                    r25["Treasure Class"] = cpot25
                    r25["group"] = ""
                    r25["level"] = ""
                    r25["NoDrop"] = "60"
                    idx_cpot = rows.index(r)
                    rows.insert(idx_cpot + 1, r25)
                    by_tc[cpot25] = r25

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

    # Wire Tier 2 (Uniques & Champions): 1 Guaranteed Roll + 2x Cpot25 (25% at P1 -> 43.75% P2 -> 76.3% P5) + 1 Gold + 1 Potion
    # Preserves exact P1 mean of 1.50 loot rolls (1 + 2*0.25) while scaling smoothly to 1.88 (P2) .. 2.53 (P5)
    for act_prefix, _, _, _, _, _ in ACTS:
        act_gold = _gold_for_tc(act_prefix)
        act_pot = f"{act_prefix} Potion"
        for letter in ("A", "B", "C"):
            uitem = f"{act_prefix} Uitem {letter}"
            if uitem not in by_tc:
                uitem = f"{act_prefix} Uitem B"
            citem = f"{act_prefix} Citem {letter}"
            if citem not in by_tc:
                citem = f"{act_prefix} Citem B"
            cpot25 = f"{act_prefix} Cpot25 {letter}"
            if cpot25 not in by_tc:
                cpot25 = f"{act_prefix} Cpot25 B"

            utc = f"{act_prefix} Unique {letter}"
            if utc in by_tc:
                row = by_tc[utc]
                row["Picks"] = "-5"
                row["Unique"] = "850"
                row["Set"] = "850"
                row["Rare"] = "950"
                row["Magic"] = "1024"
                row["NoDrop"] = "0"
                _set_items(row, [(uitem, "1"), (cpot25, "2"), (act_gold, "1"), (act_pot, "1")])

            ctc = f"{act_prefix} Champ {letter}"
            if ctc in by_tc:
                row = by_tc[ctc]
                row["Picks"] = "-5"
                row["Unique"] = "820"
                row["Set"] = "820"
                row["Rare"] = "920"
                row["Magic"] = "1024"
                row["NoDrop"] = "0"
                _set_items(row, [(citem, "1"), (cpot25, "2"), (act_gold, "1"), (act_pot, "1")])

    # 8. Tier 3 — SuperUniques: 1 Guaranteed Roll + 3x Cpot (50% at P1 -> 75% P2 -> 96.9% P5) + 1 Gold + 1 Potion
    # Preserves exact P1 mean of 2.50 loot rolls (1 + 3*0.50) while scaling smoothly to 3.25 (P2) .. 3.91 (P5)
    for act_prefix, _, _, _, _, _ in ACTS:
        act_gold = _gold_for_tc(act_prefix)
        act_pot = f"{act_prefix} Potion"
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
                row["Picks"] = "-6"
                row["Unique"] = "920"
                row["Set"] = "920"
                row["Rare"] = "980"
                row["Magic"] = "1024"
                row["NoDrop"] = "0"
                _set_items(row, [(uitem, "1"), (cpot, "3"), (act_gold, "1"), (act_pot, "1")])

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
            act_gold = _gold_for_tc(act_key)
            act_pot = f"{act_key} Potion"
            uitem = f"{act_key} Uitem C" if f"{act_key} Uitem C" in by_tc else f"{act_key} Uitem B"
            cpot = f"{act_key} Cpot C" if f"{act_key} Cpot C" in by_tc else f"{act_key} Cpot B"
            for r in rows:
                tc = r["Treasure Class"]
                if tc == f"{base_name}{diff_suffix}" or (
                    tc.startswith(f"{base_name}{diff_suffix} Desecrated")
                    and r.get("Picks") != "-1"
                ) or tc.startswith(f"{base_name} Item{diff_suffix}"):
                    r["Picks"] = "-6"
                    r["Unique"] = "920"
                    r["Set"] = "920"
                    r["Rare"] = "980"
                    r["Magic"] = "1024"
                    r["NoDrop"] = "0"
                    _set_items(r, [(uitem, "1"), (cpot, "3"), (act_gold, "1"), (act_pot, "1")])

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
        act_gold = _gold_for_tc(act_key)
        for r in rows:
            tc = r["Treasure Class"]
            if tc == f"Countess Item{diff_suffix}" or tc.startswith(f"Countess Item{diff_suffix} Desecrated"):
                r["Picks"] = "-3"
                r["Unique"] = "920"
                r["Set"] = "920"
                r["Rare"] = "980"
                r["Magic"] = "1024"
                r["NoDrop"] = "0"
                _set_items(r, [(uitem, "1"), (cpot, "1"), (act_gold, "1")])

    # 9. Tier 4 — Act Bosses (Andariel, Duriel, Mephisto, Diablo, Baal + q & Desecrated):
    # 3 Guaranteed Rolls + 1 Bonus (50%) Roll + 1 Unique Boss Charm roll + 1 Guaranteed Gold Pile
    boss_configs = [
        ("Andariel", ("", "Act 2 Uitem A", "Act 2 Cpot A", "Act Boss Charm 1"), (" (N)", "Act 2 (N) Uitem A", "Act 2 (N) Cpot A", "Act Boss Charm 3"), (" (H)", "Act 2 (H) Uitem A", "Act 2 (H) Cpot A", "Act Boss Charm 4")),
        ("Duriel", ("", "Act 3 Uitem A", "Act 3 Cpot A", "Act Boss Charm 1"), (" (N)", "Act 3 (N) Uitem A", "Act 3 (N) Cpot A", "Act Boss Charm 3"), (" (H)", "Act 3 (H) Uitem A", "Act 3 (H) Cpot A", "Act Boss Charm 5")),
        ("Mephisto", ("", "Act 4 Uitem A", "Act 4 Cpot A", "Act Boss Charm 2"), (" (N)", "Act 4 (N) Uitem A", "Act 4 (N) Cpot A", "Act Boss Charm 3"), (" (H)", "Act 4 (H) Uitem A", "Act 4 (H) Cpot A", "Act Boss Charm 5")),
        ("Diablo", ("", "Act 5 Uitem A", "Act 5 Cpot A", "Act Boss Charm 2"), (" (N)", "Act 5 (N) Uitem A", "Act 5 (N) Cpot A", "Act Boss Charm 4"), (" (H)", "Act 5 (H) Uitem A", "Act 5 (H) Cpot A", "Act Boss Charm 5")),
        ("Baal", ("", "Act 1 (N) Uitem A", "Act 1 (N) Cpot A", "Act Boss Charm 2"), (" (N)", "Act 1 (H) Uitem A", "Act 1 (H) Cpot A", "Act Boss Charm 4"), (" (H)", "Act 5 (H) Uitem C", "Act 5 (H) Cpot C", "Act Boss Charm 5")),
    ]
    for boss, cfg_n, cfg_nm, cfg_h in boss_configs:
        for diff_suffix, boss_uitem, boss_cpot, boss_charm_tc in (cfg_n, cfg_nm, cfg_h):
            act_gold = _gold_for_tc(diff_suffix)
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
                    r["Picks"] = "-6"
                    r["Unique"] = "985"
                    r["Set"] = "985"
                    r["Rare"] = "1024"
                    r["Magic"] = "1024"
                    r["NoDrop"] = "0"
                    _set_items(
                        r,
                        [
                            (boss_uitem, "2"),
                            (boss_cpot, "3"),
                            (boss_charm_tc, "1"),
                        ],
                    )

    # 10. Configure Chest & Super Chest TCs (Act X Chest A/B/C) to drop ONLY:
    # Gold, Runes, Jewelry, Gems (via Act X Good), and Act-scaled Modified Potions
    # (NEVER weapons/armor, rejuvs, keys, or deprecated junk)
    chest_potions_by_act = {
        "Act 1": ("hp1", "mp1", "wms", "yps", "vps"),
        "Act 2": ("hp1", "mp1", "wms", "yps", "vps"),
        "Act 3": ("hp1", "mp1", "wms", "yps", "vps"),
        "Act 4": ("hp2", "mp2", "wms", "yps", "vps"),
        "Act 5": ("hp2", "mp2", "wms", "yps", "vps"),
        "Act 1 (N)": ("hp3", "mp3", "wm2", "yp2", "vp2"),
        "Act 2 (N)": ("hp3", "mp3", "wm2", "yp2", "vp2"),
        "Act 3 (N)": ("hp4", "mp4", "wm2", "yp2", "vp2"),
        "Act 4 (N)": ("hp4", "mp4", "wm2", "yp2", "vp2"),
        "Act 5 (N)": ("hp4", "mp4", "wm2", "yp2", "vp2"),
        "Act 1 (H)": ("hp5", "mp5", "wm3", "yp3", "vp3"),
        "Act 2 (H)": ("hp5", "mp5", "wm3", "yp3", "vp3"),
        "Act 3 (H)": ("hp5", "mp5", "wm3", "yp3", "vp3"),
        "Act 4 (H)": ("hp5", "mp5", "wm3", "yp3", "vp3"),
        "Act 5 (H)": ("hp5", "mp5", "wm3", "yp3", "vp3"),
    }
    QA_FORCE_CHEST_LOCKBOX = False
    chest_anchor_idx = next(
        i for i, r in enumerate(rows) if r["Treasure Class"] == "Act 1 Chest A"
    )
    for act_p, (hp_c, mp_c, wm_c, yp_c, vp_c) in chest_potions_by_act.items():
        jewelry_tc = "Jewelry A" if act_p == "Act 1" else "Jewelry C"
        chest_Pool = [
            (_gold_for_tc(act_p), "160"),
            (f"{act_p} GemRune", "30"),
            (jewelry_tc, "20"),
            (hp_c, "7"),
            (mp_c, "7"),
            (wm_c, "2"),
            (yp_c, "2"),
            (vp_c, "2"),
            (f"{act_p} Lockbox", "10"),
        ]
        roll_tc_name = f"{act_p} Chest Roll"
        if roll_tc_name not in by_tc:
            roll_row = _make_blank_row(headers, roll_tc_name)
            roll_row["Picks"] = "1"
            roll_row["NoDrop"] = "0"
            _set_items(roll_row, chest_Pool)
            rows.insert(chest_anchor_idx, roll_row)
            by_tc[roll_tc_name] = roll_row
            chest_anchor_idx += 1

        pair_tc_name = f"{act_p} Chest Pair"
        if pair_tc_name not in by_tc:
            pair_row = _make_blank_row(headers, pair_tc_name)
            pair_row["Picks"] = "2"
            pair_row["NoDrop"] = "240"
            _set_items(pair_row, chest_Pool)
            rows.insert(chest_anchor_idx, pair_row)
            by_tc[pair_tc_name] = pair_row
            chest_anchor_idx += 1

    for r in rows:
        tc = r["Treasure Class"]
        if "Chest" in tc and not tc.endswith(("Chest Roll", "Chest Pair")):
            matched_act = next(
                (act_p for act_p in chest_potions_by_act if tc.startswith(f"{act_p} Chest")),
                "Act 1",
            )
            if QA_FORCE_CHEST_LOCKBOX:
                r["Picks"] = "2"
                r["NoDrop"] = "0"
                _set_items(r, [(f"{matched_act} Lockbox", "100")])
            else:
                # Picks = -6 with 2x 'Act X Chest Roll' (1 guaranteed drop each = 2 floor)
                # + 4x 'Act X Chest Pair' (2 picks at 50% NoDrop each = 0..8 bonus drops, mean 4.0 at P1)
                # Preserves exact P1 mean of 6.00 drops while scaling to 8.00 (P2) .. 9.75 (P5) in co-op.
                r["Picks"] = "-6"
                r["NoDrop"] = "0"
                _set_items(
                    r,
                    [
                        (f"{matched_act} Chest Roll", "2"),
                        (f"{matched_act} Chest Pair", "4"),
                    ],
                )

    # 10b. Align Nightmare & Hell (group, level) TC auto-upgrade thresholds in Groups 2..5, 7..15, 18..19, 36..37
    # with actual levels.txt MonLvlEx(N) / MonLvlEx(H) boundaries so monsters in Nightmare Acts 1-2
    # (and Champion +2 / Unique +3 bosses) never prematurely auto-upgrade into higher-Act Gem/Rune TCs:
    # - Act 1 (N): MonLvlEx(N)=36..43 (Champ 38..45, Unique 39..46) -> Normal TCs 36/39/42, Champ/Unique/Super TCs 39/42/45
    # - Act 2 (N): MonLvlEx(N)=43..49 (Champ 45..51, Unique 46..52) -> Normal TCs 44/46/48, Champ/Unique/Super TCs 47/49/51
    # - Act 3 (N): MonLvlEx(N)=49..55 (Champ 51..57, Unique 52..58) -> Normal TCs 50/52/54, Champ/Unique/Super TCs 53/55/57
    # - Act 4 (N): MonLvlEx(N)=56..58 (Champ 58..60, Unique 59..61) -> Normal TCs 56/57/58, Champ/Unique/Super TCs 59/60/61
    # - Act 5 (N): MonLvlEx(N)=58..66 (Champ 60..68, Unique 61..69) -> Normal TCs 60/63/66, Champ/Unique/Super TCs 62/65/68
    # - Act 1 (H): MonLvlEx(H)=67..73 (Champ 69..75, Unique 70..76) -> Normal TCs 68/70/72, Champ/Unique TCs 70/72/74
    # - Act 2 (H): MonLvlEx(H)=74..80 -> Normal TCs 74/76/78, Champ/Unique TCs 76/78/80
    # - Act 3 (H): MonLvlEx(H)=79..83 -> Normal TCs 79/80/81, Champ/Unique TCs 81/82/83
    # - Act 4 (H): MonLvlEx(H)=82..85 -> Normal TCs 82/83/84, Champ/Unique TCs 84/85/86
    # - Act 5 (H): MonLvlEx(H)=80..85 -> Normal TCs 84/85/86, Champ/Unique TCs 86/87/88
    normal_tc_levels = {
        "Act 1 (N)": ("36", "39", "42"),
        "Act 2 (N)": ("44", "46", "48"),
        "Act 3 (N)": ("50", "52", "54"),
        "Act 4 (N)": ("56", "57", "58"),
        "Act 5 (N)": ("60", "63", "66"),
        "Act 1 (H)": ("68", "70", "72"),
        "Act 2 (H)": ("74", "76", "78"),
        "Act 3 (H)": ("79", "80", "81"),
        "Act 4 (H)": ("82", "83", "84"),
        "Act 5 (H)": ("84", "85", "86"),
    }
    elite_tc_levels = {
        "Act 1 (N)": ("39", "42", "45"),
        "Act 2 (N)": ("47", "49", "51"),
        "Act 3 (N)": ("53", "55", "57"),
        "Act 4 (N)": ("59", "60", "61"),
        "Act 5 (N)": ("62", "65", "68"),
        "Act 1 (H)": ("70", "72", "74"),
        "Act 2 (H)": ("76", "78", "80"),
        "Act 3 (H)": ("81", "82", "83"),
        "Act 4 (H)": ("84", "85", "86"),
        "Act 5 (H)": ("86", "87", "88"),
    }
    if "Act 1 (H) Uitem A Shard" in by_tc:
        by_tc["Act 1 (H) Uitem A Shard"]["level"] = "70"
    for r in rows:
        grp = r.get("group", "")
        tc = r["Treasure Class"]
        if grp == "5":
            for act_p, (la, _, _) in normal_tc_levels.items():
                if tc == f"{act_p} Good":
                    r["level"] = la
                    break
        elif grp in ("2", "3", "4", "7", "8", "9", "10"):
            for act_p, (la, lb, lc) in normal_tc_levels.items():
                if tc.startswith(f"{act_p} "):
                    if tc.endswith(" A"):
                        r["level"] = la
                    elif tc.endswith(" B"):
                        r["level"] = lb
                    elif tc.endswith(" C"):
                        r["level"] = lc
                    break
        elif grp in ("11", "12", "13", "14", "15", "36", "37") or (grp in ("18", "19") and "(N)" in tc):
            for act_p, (la, lb, lc) in elite_tc_levels.items():
                if tc.startswith(f"{act_p} "):
                    if tc.endswith((" A", " Ax", " A Desecrated")):
                        r["level"] = la
                    elif tc.endswith((" B", " Bx", " B Desecrated")):
                        r["level"] = lb
                    elif tc.endswith((" C", " Cx", " C Desecrated")):
                        r["level"] = lc
                    break

    # 11. Skeleton Monster TCs (<TC> Skel) & Optional Exploration Dungeon TCs (<TC> Opt / <TC> Skel Opt)
    # First create Skeleton Uitem/Citem/Cpot sub-tables and clone monster TC groups (7, 8, 9, 13, 15, 36, 37)
    # into contiguous Skeleton TC groups (+100) that reference 'Act X Good Skel' and 'Act X GemRune Skel'.
    cpot_last_idx = max(i for i, r in enumerate(rows) if r.get("group") == "12")
    skel_item_rows: List[Dict[str, str]] = []
    for act_prefix, _, _, _, _, equip_fallback in ACTS:
        gr_skel = f"{act_prefix} GemRune Skel"
        j_tc = "Jewelry A" if act_prefix == "Act 1" else "Jewelry C"
        for letter in ("A", "B", "C"):
            eq_tc = f"{act_prefix} Equip {letter}"
            if eq_tc not in by_tc:
                eq_tc = equip_fallback
            for sub_kind in ("Uitem", "Citem", "Cpot", "Cpot25"):
                base_sub = f"{act_prefix} {sub_kind} {letter}"
                skel_sub = f"{base_sub} Skel"
                if base_sub in by_tc and skel_sub not in by_tc:
                    srow = dict(by_tc[base_sub])
                    srow["Treasure Class"] = skel_sub
                    srow["group"] = ""
                    srow["level"] = ""
                    _set_items(srow, [(eq_tc, "13"), (gr_skel, "5"), (j_tc, "2")])
                    skel_item_rows.append(srow)
                    by_tc[skel_sub] = srow

    # Create dedicated 'Act X Cpot A/B/C Opt' & 'Act X Cpot A/B/C Skel Opt' sub-tables with NoDrop=1 (20/21 = 95.24% bonus drop rate
    # vs 50% on standard Cpot, increasing Champion/Unique expected item/gem/rune yield from 1.50 -> 1.952 = +30.2%)
    cpot_opt_rows: List[Dict[str, str]] = list(skel_item_rows)
    for act_prefix, _, _, _, _, _ in ACTS:
        for letter in ("A", "B", "C"):
            for sfx_skel in ("", " Skel"):
                cpot_name = f"{act_prefix} Cpot {letter}{sfx_skel}"
                cpot_opt_name = f"{cpot_name} Opt"
                if cpot_name in by_tc and cpot_opt_name not in by_tc:
                    corow = dict(by_tc[cpot_name])
                    corow["Treasure Class"] = cpot_opt_name
                    corow["group"] = ""
                    corow["level"] = ""
                    corow["Unique"] = "950"
                    corow["Set"] = "950"
                    corow["Rare"] = "990"
                    corow["Magic"] = "1024"
                    corow["NoDrop"] = "1"
                    cpot_opt_rows.append(corow)
                    by_tc[cpot_opt_name] = corow
    for offset, corow in enumerate(cpot_opt_rows):
        rows.insert(cpot_last_idx + 1 + offset, corow)

    # Clone Skeleton monster TC groups (7, 8, 9, 13, 15, 36, 37 -> +100) before Optional Dungeon cloning
    skel_tc_groups = ("7", "8", "9", "13", "15", "36", "37")
    skel_cloned_rows: List[Dict[str, str]] = []
    for grp in skel_tc_groups:
        grp_rows = [r for r in rows if r.get("group") == grp]
        new_grp = str(int(grp) + 100)
        for r in grp_rows:
            sr = dict(r)
            tc_orig = r["Treasure Class"]
            tc_skel = f"{tc_orig} Skel"
            sr["Treasure Class"] = tc_skel
            sr["group"] = new_grp
            if grp in ("7", "8", "9"):
                for i in range(1, 11):
                    iv = sr.get(f"Item{i}", "").strip()
                    if iv.endswith(" Good") and f"{iv} Skel" in by_tc:
                        sr[f"Item{i}"] = f"{iv} Skel"
            elif grp in ("13", "15"):
                for i in (1, 2):
                    iv = sr.get(f"Item{i}", "").strip()
                    if iv and f"{iv} Skel" in by_tc:
                        sr[f"Item{i}"] = f"{iv} Skel"
            elif grp in ("36", "37"):
                iv = sr.get("Item1", "").strip()
                if iv and f"{iv} Skel" in by_tc:
                    sr["Item1"] = f"{iv} Skel"
            skel_cloned_rows.append(sr)
            by_tc[tc_skel] = sr
    rows.extend(skel_cloned_rows)

    # Clone monster TC groups (7..10, 13, 15..19, 36..39 and Skeleton groups 107..109, 113, 115, 136, 137)
    # into contiguous Optional Dungeon TC groups (+50) so D2R's (group, level) auto-upgrading in Nightmare/Hell
    # works identically while delivering +30% rewards.
    opt_tc_groups = (
        "7", "8", "9", "10", "13", "15", "16", "17", "18", "19", "36", "37", "38", "39",
        "107", "108", "109", "113", "115", "136", "137",
    )
    opt_cloned_rows: List[Dict[str, str]] = []
    for grp in opt_tc_groups:
        grp_rows = [r for r in rows if r.get("group") == grp]
        new_grp = str(int(grp) + 50)
        for r in grp_rows:
            opt_r = dict(r)
            tc_orig = r["Treasure Class"]
            tc_opt = f"{tc_orig} Opt"
            opt_r["Treasure Class"] = tc_opt
            opt_r["group"] = new_grp
            if grp in ("7", "8", "9", "10", "16", "17", "107", "108", "109"):
                # Normal Monster Opt TCs: reduce NoDrop so total denominator (W_items + NoDrop) shrinks by 1/1.30,
                # increasing per-kill drop probability of Equip, Good (Gems/Runes/Jewelry), and Gold by +30% (1.30x)
                w_items = sum(
                    int(opt_r.get(f"Prob{i}") or "0")
                    for i in range(1, 11)
                    if opt_r.get(f"Item{i}", "").strip()
                )
                nd_std = int(opt_r.get("NoDrop") or "0")
                if nd_std > 0 and w_items > 0:
                    nd_opt = max(0, int(round((nd_std - 0.30 * w_items) / 1.30)))
                    opt_r["NoDrop"] = str(nd_opt)
                opt_r["Unique"] = "300"
                opt_r["Set"] = "300"
                opt_r["Rare"] = "400"
                opt_r["Magic"] = "600"
            elif grp in ("13", "15", "113", "115"):
                # Champion & Unique Opt TCs: upgrade 2x Cpot25 (25%) -> 2x Cpot (50%) -> 2.00 vs 1.50 drops at P1 (+33%), 2.50 P2, 2.94 P5
                it2 = opt_r.get("Item2", "").strip()
                if " Cpot25 " in it2:
                    upgraded = it2.replace(" Cpot25 ", " Cpot ")
                    if upgraded in by_tc:
                        opt_r["Item2"] = upgraded
                elif it2 and f"{it2} Opt" in by_tc:
                    opt_r["Item2"] = f"{it2} Opt"
                opt_r["Unique"] = "950" if grp in ("15", "115") else "920"
                opt_r["Set"] = "950" if grp in ("15", "115") else "920"
                opt_r["Rare"] = "990" if grp in ("15", "115") else "970"
            elif grp in ("18", "19"):
                # SuperUnique Opt TCs: 1 Uitem + 1 Cpot Opt (95.2%) + 3 Cpot (50%) + 1 Gold = 3.45 at P1 -> 4.25 P2 -> 4.91 P5
                uitem_tc = opt_r.get("Item1", "").strip()
                cpot_tc = opt_r.get("Item2", "").strip()
                gold_tc = opt_r.get("Item3", "").strip()
                cpot_opt_tc = f"{cpot_tc} Opt" if f"{cpot_tc} Opt" in by_tc else cpot_tc
                opt_r["Picks"] = "-6"
                opt_r["Unique"] = "960"
                opt_r["Set"] = "960"
                opt_r["Rare"] = "1000"
                opt_r["Magic"] = "1024"
                opt_r["NoDrop"] = "0"
                _set_items(opt_r, [(uitem_tc, "1"), (cpot_opt_tc, "1"), (cpot_tc, "3"), (gold_tc, "1")])
            elif grp in ("36", "37", "38", "39", "136", "137"):
                # Desecrated Opt TCs: point base TC in Item1 to <BaseTC> Opt
                base_ref = opt_r.get("Item1", "").strip()
                if base_ref and f"{base_ref} Opt" in by_tc:
                    opt_r["Item1"] = f"{base_ref} Opt"
            opt_cloned_rows.append(opt_r)
            by_tc[tc_opt] = opt_r
    rows.extend(opt_cloned_rows)

    # TEMPORARY QA BOOST: Make Act 1 Blood Moor monsters drop all 5 Gem/Skull tiers + Tier Runes in equal proportions
    if econ.get("qa_blood_moor_boost", False):
        if "QA Tier Kit Pool" not in by_tc:
            qa_sub_tcs = [
                ("QA Gems 1", [("gcr", "1"), ("gcb", "1"), ("gcy", "1"), ("gcg", "1"), ("gcv", "1"), ("gcw", "1"), ("skc", "2")]),
                ("QA Gems 2", [("gfr", "1"), ("gfb", "1"), ("gfy", "1"), ("gfg", "1"), ("gfv", "1"), ("gfw", "1"), ("skf", "2")]),
                ("QA Gems 3", [("gsr", "1"), ("gsb", "1"), ("gsy", "1"), ("gsg", "1"), ("gsv", "1"), ("gsw", "1"), ("sku", "2")]),
                ("QA Gems 4", [("glr", "1"), ("glb", "1"), ("gly", "1"), ("glg", "1"), ("gzv", "1"), ("glw", "1"), ("skl", "2")]),
                ("QA Gems 5", [("gpr", "1"), ("gpb", "1"), ("gpy", "1"), ("gpg", "1"), ("gpv", "1"), ("gpw", "1"), ("skz", "2")]),
                ("QA Runes A", [("r01", "1"), ("r02", "1"), ("r03", "2"), ("r04", "1"), ("r05", "2"), ("r06", "1"), ("r07", "1"), ("r08", "1"), ("r10", "1"), ("r12", "1")]),
                ("QA Runes B", [("r13", "1"), ("r14", "1"), ("r15", "1"), ("r16", "1"), ("r17", "1"), ("r18", "2"), ("r21", "1"), ("r22", "1")]),
                ("QA Runes C", [("r23", "2"), ("r24", "2"), ("r25", "2"), ("r31", "1"), ("r33", "2")]),
            ]
            r17_idx = next(i for i, r in enumerate(rows) if r["Treasure Class"] == "Runes 17")
            insert_offset = 1
            for sub_name, sub_items in qa_sub_tcs:
                sub_row = _make_blank_row(headers, sub_name)
                sub_row["Picks"] = "1"
                sub_row["NoDrop"] = "0"
                _set_items(sub_row, sub_items)
                rows.insert(r17_idx + insert_offset, sub_row)
                by_tc[sub_name] = sub_row
                insert_offset += 1

            qac = _make_blank_row(headers, "QA Tier Kit Pool")
            qac["Picks"] = "6"
            qac["NoDrop"] = "0"
            _set_items(
                qac,
                [
                    ("QA Gems 1", "8"),
                    ("QA Gems 2", "8"),
                    ("QA Gems 3", "8"),
                    ("QA Gems 4", "8"),
                    ("QA Gems 5", "8"),
                    ("QA Runes A", "12"),
                    ("QA Runes B", "9"),
                    ("QA Runes C", "9"),
                ],
            )
            rows.insert(r17_idx + insert_offset, qac)
            by_tc["QA Tier Kit Pool"] = qac

        for qa_tc in ("Act 1 H2H A", "Act 1 H2H B", "Act 1 Cast A", "Act 1 Miss A", "Act 1 Champ A", "Act 1 Unique A", "Quill 1"):
            if qa_tc in by_tc:
                by_tc[qa_tc]["Picks"] = "1"
                by_tc[qa_tc]["NoDrop"] = "0"
                _set_items(by_tc[qa_tc], [("QA Tier Kit Pool", "1")])

    # Cap recursive Equipment TC downgrade probability at 85% (down from Vanilla's 95-98%) so Nightmare
    # feels like the Exceptional era (51-74% Exc) and Hell feels like the Elite era (42-86% Elite)
    # while still allowing a trickle of lower-tier bases & Uniques/Sets to drop!
    max_equip_downgrade = 0.85
    for r in rows:
        tc_name = r.get("Treasure Class", "")
        if not (tc_name.startswith("Act ") and "Equip" in tc_name):
            continue
        curr_tot = 0
        down_idxs = []
        down_tot = 0
        for i in range(1, 11):
            it = r.get(f"Item{i}", "").strip()
            pr_s = r.get(f"Prob{i}", "").strip()
            if not it or not pr_s.isdigit():
                continue
            pr = int(pr_s)
            if it.startswith("Act ") and "Equip" in it:
                down_idxs.append((i, pr))
                down_tot += pr
            else:
                curr_tot += pr
        if curr_tot > 0 and down_tot > 0 and (down_tot / (curr_tot + down_tot)) > max_equip_downgrade:
            target_down = max(len(down_idxs), int(round(curr_tot * max_equip_downgrade / (1.0 - max_equip_downgrade))))
            for idx, pr in down_idxs:
                r[f"Prob{idx}"] = str(max(1, int(round(target_down * pr / down_tot))))

    tc_path = write_excel_tsv("treasureclassex.txt", headers, rows)
    obj_path = build_objects(cfg)
    return f"{tc_path}, {obj_path}"


def build_objects(cfg: dict) -> str:
    """
    Disable generic non-quest loot containers (Caskets, Urns, Barrels, Crates/Rocks/Logs/Corpses,
    Armor Stands, Weapon Racks, Bookshelves, Jungle Stashes) and disable random chest scattering
    (PopulateFn = 0) in objects.txt, while keeping preset Super Chests, Sparkly Chests, Quest Chests,
    and the Horadric Malus stand (OperateFn=21) clickable (Selectable0 = 1) and unlocked (Lockable = 0).
    """
    headers, rows = read_excel_tsv("objects.txt")
    generic_container_ops = {"1", "3", "4", "5", "7", "14", "19", "20", "26", "30", "33", "51"}
    preserve_ids = {"383", "384", "385"}  # TrappedSoul / Cain start position
    for r in rows:
        is_real_chest = (
            r.get("OperateFn") == "4"
            and r.get("Lockable") == "1"
            and r.get("Selectable0") == "1"
        )
        # Never allow any chest to spawn locked since keys are removed from the mod
        if r.get("Lockable") == "1":
            r["Lockable"] = "0"

        if is_real_chest:
            # Keep preset chests clickable, prevent random map scattering (PopulateFn=0),
            # and keep native OperateFn=4 with InitFn=3, Damage=100 so chests:
            #   1) Properly execute D2Game.dll's chest trap handler on open (OperateFn=4 + InitFn=3),
            #   2) Roll a ~20-25% chance to be trapped on room load (freshly re-seeded via -resetofflinemaps),
            #   3) Roll a 75% chance of calling 'Act X Chest A/B/C' (25% empty chest roll),
            #   4) Never invoke hardcoded SUnit_SparklyChest (0 unscaled hp3/mp3 potions).
            r["Selectable0"] = "1"
            r["PopulateFn"] = "0"
            r["OperateFn"] = "4"
            r["InitFn"] = "3"
            r["Damage"] = "100"
        elif r.get("OperateFn") == "22":
            # Fast-regenerating Nox-style Wells: 10s recharge (250 frames) and 100% full Life/Mana/Stamina restore (256)
            r["Parm0"] = "250"
            r["Parm1"] = "256"
        elif r.get("OperateFn") == "2" and r.get("InitFn") == "1":
            # Convert all Magic/Booster shrine pedestals (Parm0=3) into Health (Parm0=1) or Mana (Parm0=2) recovery shrines
            if r.get("Parm0") not in ("1", "2"):
                obj_id = int(r.get("*ID") or "0")
                r["Parm0"] = "1" if (obj_id % 2 == 0) else "2"
        elif r.get("OperateFn") in generic_container_ops and r.get("*ID") not in preserve_ids:
            r["Selectable0"] = "0"
            r["PopulateFn"] = "0"
    obj_out = write_excel_tsv("objects.txt", headers, rows)

    # Also rewrite objpreset.txt so that DS1 map presets that reference Sparkly / Super Chest
    # spawners (PlaceUniqueChest ID=584, ConsolationChest ID=397, SpecialChest100 ID=455,
    # PlaceRandomTreasureChest ID=585) instead spawn each Act's standard InitFn=3 Large Chest!
    # Why? Because D2Game.dll hardcodes Object IDs 397/455/584 to run SUnit_SparklyChest
    # (which forcibly drops 5 Gold piles + 2 hp3 + 2 mp3 = 9 hardcoded items in Act 3 Normal
    # on top of 4 calls to Act X Chest!). Mapping them to the Act's standard Large Chest
    # guarantees 1 clean call to 'Act X Chest A/B/C' (6 items total) and 0 hardcoded hp3/mp3 drops.
    preset_headers, preset_rows = read_excel_tsv("objpreset.txt")
    act_standard_chest = {
        "1": "LargeChestR",
        "2": "TombChest1",
        "3": "SewerChestLargeLeft",
        "4": "ArcaneChest1",
        "5": "WoodChestL",
    }
    sparkly_or_super_classes = {
        "PlaceUniqueChest",
        "ConsolationChest",
        "SpecialChest100",
        "PlaceRandomTreasureChest",
    }
    for pr in preset_rows:
        if pr.get("ObjectClass") in sparkly_or_super_classes:
            act_num = pr.get("Act", "1").strip()
            pr["ObjectClass"] = act_standard_chest.get(act_num, "LargeChestR")
    preset_out = write_excel_tsv("objpreset.txt", preset_headers, preset_rows)
    return f"{obj_out}, {preset_out}"

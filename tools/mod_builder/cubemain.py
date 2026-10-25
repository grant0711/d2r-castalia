#!/usr/bin/env python3
"""
cubemain.py
Step 9: Build cubemain.txt:
- Keep core Quest recipes (Horadric Staff, Khalim's Will, Token of Absolution; NO Cow Level, NO Pandemonium/Ubers)
- 2 -> 1 Gem & Skull Upgrade recipes (28 rows)
- 2 -> 1 Rune Upgrade recipes (32 rows, r01 -> r33 without extra gem requirements)
- Socket Punching (weap,nos / armo,nos + Blacksmith's Malus bml + Perfect Skull skz -> 1-2 sockets) & Clear Sockets
- Unique / Set / Boss Charm -> Jewel Distillation (~545 rows, using 0.50 * lvl / 100 formula)
- One-Step Gem Pact + 3-Rune Slot-Specific Crafting across all 5 Slot Groups
  (weap -> gljw -> btbl -> shld -> armo), all 35 Gems/Skulls (Chipped -> Perfect), and 3-Rune combinations!
"""
import os
from typing import Dict, List, Tuple

from mod_builder.common import MOD_ROOT, read_excel_tsv
from mod_builder.gems_runes import GEM_SPECS, RUNE_SPECS

# 7 Gem/Skull families ordered by tier (0=Chipped, 1=Flawed, 2=Standard, 3=Flawless, 4=Perfect)
# Curse is the opposing element/stat weakness scaled across the 5 tiers:
#   Ruby (Fire)     -> -Cold Resist (res-cold)
#   Sapphire (Cold) -> -Fire Resist (res-fire)
#   Topaz (Ltng)    -> -Poison Resist (res-pois)
#   Emerald (Pois)  -> -Lightning Resist (res-ltng)
#   Diamond (Mag)   -> -Physical Damage Resist % (damageresist)
#   Amethyst (Phys) -> -Magic Resist (res-mag)
#   Skull (Bone)    -> -Flat Life (hp)
GEM_CURSES: Dict[str, Tuple[str, str, str, str]] = {
    # Ruby -> -Cold Res
    "gcr": ("res-cold", "", "-8", "-6"),
    "gfr": ("res-cold", "", "-12", "-9"),
    "gsr": ("res-cold", "", "-16", "-12"),
    "glr": ("res-cold", "", "-20", "-15"),
    "gpr": ("res-cold", "", "-25", "-18"),
    # Sapphire -> -Fire Res
    "gcb": ("res-fire", "", "-8", "-6"),
    "gfb": ("res-fire", "", "-12", "-9"),
    "gsb": ("res-fire", "", "-16", "-12"),
    "glb": ("res-fire", "", "-20", "-15"),
    "gpb": ("res-fire", "", "-25", "-18"),
    # Topaz -> -Poison Res
    "gcy": ("res-pois", "", "-8", "-6"),
    "gfy": ("res-pois", "", "-12", "-9"),
    "gsy": ("res-pois", "", "-16", "-12"),
    "gly": ("res-pois", "", "-20", "-15"),
    "gpy": ("res-pois", "", "-25", "-18"),
    # Emerald -> -Lightning Res
    "gcg": ("res-ltng", "", "-8", "-6"),
    "gfg": ("res-ltng", "", "-12", "-9"),
    "gsg": ("res-ltng", "", "-16", "-12"),
    "glg": ("res-ltng", "", "-20", "-15"),
    "gpg": ("res-ltng", "", "-25", "-18"),
    # Diamond -> -Physical Damage Resist %
    "gcw": ("damageresist", "", "-4", "-3"),
    "gfw": ("damageresist", "", "-6", "-4"),
    "gsw": ("damageresist", "", "-8", "-5"),
    "glw": ("damageresist", "", "-10", "-7"),
    "gpw": ("damageresist", "", "-12", "-8"),
    # Amethyst -> -Magic Resist
    "gcv": ("res-mag", "", "-5", "-3"),
    "gfv": ("res-mag", "", "-8", "-5"),
    "gsv": ("res-mag", "", "-11", "-7"),
    "gzv": ("res-mag", "", "-14", "-9"),
    "gpv": ("res-mag", "", "-18", "-12"),
    # Skull -> -Flat Life
    "skc": ("hp", "", "-12", "-8"),
    "skf": ("hp", "", "-20", "-14"),
    "sku": ("hp", "", "-30", "-20"),
    "skl": ("hp", "", "-42", "-28"),
    "skz": ("hp", "", "-55", "-38"),
}

# Gem Tier output level rules:
# Chipped -> lvl=12, Flawed -> lvl=24, Standard -> lvl=36, Flawless -> lvl=50, Perfect -> plvl=100 (100% of clvl)
GEM_LEVEL_RULES: Dict[str, Tuple[str, str]] = {
    "gcr": ("12", ""), "gfr": ("24", ""), "gsr": ("36", ""), "glr": ("50", ""), "gpr": ("", "100"),
    "gcb": ("12", ""), "gfb": ("24", ""), "gsb": ("36", ""), "glb": ("50", ""), "gpb": ("", "100"),
    "gcy": ("12", ""), "gfy": ("24", ""), "gsy": ("36", ""), "gly": ("50", ""), "gpy": ("", "100"),
    "gcg": ("12", ""), "gfg": ("24", ""), "gsg": ("36", ""), "glg": ("50", ""), "gpg": ("", "100"),
    "gcw": ("12", ""), "gfw": ("24", ""), "gsw": ("36", ""), "glw": ("50", ""), "gpw": ("", "100"),
    "gcv": ("12", ""), "gfv": ("24", ""), "gsv": ("36", ""), "gzv": ("50", ""), "gpv": ("", "100"),
    "skc": ("12", ""), "skf": ("24", ""), "sku": ("36", ""), "skl": ("50", ""), "skz": ("", "100"),
}

GEM_UPGRADE_CHAINS = [
    ["gcv", "gfv", "gsv", "gzv", "gpv"],
    ["gcr", "gfr", "gsr", "glr", "gpr"],
    ["gcb", "gfb", "gsb", "glb", "gpb"],
    ["gcy", "gfy", "gsy", "gly", "gpy"],
    ["gcg", "gfg", "gsg", "glg", "gpg"],
    ["gcw", "gfw", "gsw", "glw", "gpw"],
    ["skc", "skf", "sku", "skl", "skz"],
]

NON_DISTILLABLE_PROPS = {
    "aura", "oskill", "charged", "hit-skill", "gethit-skill", "att-skill",
    "kill-skill", "death-skill", "levelup-skill", "sock", "indestruct",
    "ethereal", "rep-dur", "rep-quant", "stack", "light", "ease",
}

BINARY_OR_SKILL_PROPS = {
    "allskills", "ama", "pal", "nec", "sor", "bar", "dru", "ass", "war",
    "fireskill", "skill", "skilltab", "knock", "ignore-ac", "noheal",
    "half-freeze", "rip", "pierce-immunity-cold", "pierce-immunity-fire",
    "pierce-immunity-light", "pierce-immunity-poison", "pierce-immunity-damage",
    "pierce-immunity-magic",
}


def _scale_craft_mod(
    mod: Tuple[str, str, str, str],
    slot_scale: float,
    synergy_mult: float = 1.0,
    is_gljw: bool = False,
) -> Tuple[str, str, str, str]:
    """
    Compute (code, param, min_str, max_str) for a Gem Boon or Rune craft modifier.
    - Base craft roll is ~45%-65% of the socket value for 1x Rune (or ~80%-110% of socket value for Gem Boon),
      scaled by slot_scale (1.0 for weap/shld/armo, 0.60 for gljw/btbl) and synergy_mult (1.0, 2.25, 3.75).
    """
    code, param, mn_s, mx_s = mod
    # Fallback weapon-only binary properties on Gloves/Rings/Amulets (gljw) to sensible numeric stats
    if is_gljw:
        if code == "ignore-ac":
            code, param, mn_s, mx_s = ("reduce-ac", "", "20", "20")
        elif code == "indestruct":
            code, param, mn_s, mx_s = ("red-dmg%", "", "8", "8")

    if code in ("knock", "ignore-ac", "indestruct", "half-freeze", "noheal", "rip"):
        return (code, param, "1", "1")

    try:
        mn_v = int(mn_s)
        mx_v = int(mx_s)
    except ValueError:
        return (code, param, mn_s, mx_s)

    if code == "allskills":
        # 1x r33 = +1, 2x r33 = +1..2, 3x r33 = +2
        if synergy_mult >= 3.0:
            return (code, param, "2", "2")
        elif synergy_mult >= 2.0:
            return (code, param, "1", "2")
        return (code, param, "1", "1")

    sign = -1 if mn_v < 0 or mx_v < 0 else 1
    abs_mn = abs(mn_v)
    abs_mx = abs(mx_v)

    low_f = abs_mn * 0.45 * slot_scale * synergy_mult
    high_f = abs_mx * 0.65 * slot_scale * synergy_mult

    low_i = max(1, int(round(low_f)))
    high_i = max(low_i, int(round(high_f)))

    if sign < 0:
        return (code, param, str(-high_i), str(-low_i))
    return (code, param, str(low_i), str(high_i))


def _scale_gem_boon(
    mod: Tuple[str, str, str, str],
    slot_scale: float,
) -> Tuple[str, str, str, str]:
    code, param, mn_s, mx_s = mod
    try:
        mn_v = int(mn_s)
        mx_v = int(mx_s)
    except ValueError:
        return (code, param, mn_s, mx_s)

    if code == "dmg-norm":
        # Keep min == max on dmg-norm so it displays cleanly as "+XX to Minimum/Maximum Damage" (or Damage +XX)
        val_i = max(1, int(round(((mn_v + mx_v) / 2.0) * 0.90 * slot_scale)))
        return (code, param, str(val_i), str(val_i))

    sign = -1 if mn_v < 0 or mx_v < 0 else 1
    abs_mn = abs(mn_v)
    abs_mx = abs(mx_v)
    low_i = max(1, int(round(abs_mn * 0.75 * slot_scale)))
    high_i = max(low_i, int(round(abs_mx * 1.05 * slot_scale)))
    if code == "dmg-ac":
        high_i = min(120, high_i)
        low_i = min(low_i, high_i)
    if sign < 0:
        return (code, param, str(-high_i), str(-low_i))
    return (code, param, str(low_i), str(high_i))


def _make_row_str(
    num_cols: int,
    col_idx: Dict[str, int],
    fields: Dict[str, str],
) -> str:
    arr = [""] * num_cols
    arr[col_idx["*eol"]] = "0"
    for k, v in fields.items():
        arr[col_idx[k]] = v
    return "\t".join(arr)


def _build_distillation_rows(
    num_cols: int,
    col_idx: Dict[str, int],
) -> List[str]:
    """
    Generate Unique, Set & Unique Charm -> Jewel Distillation recipes:
    input 1 = Specific Unique or Set item (by index name)
    input 2 = bml (Blacksmith's Malus)
    output  = "jew,nor" (lvl=0, plvl=0, ilvl=0 -> zero random affixes)
    mod 1..5 = Top 5 distillable properties scaled by 0.50 * (lvl / 100)
    """
    out_lines: List[str] = []

    # Read our modded uniqueitems.txt and setitems.txt from MOD_ROOT
    u_path = os.path.join(MOD_ROOT, "data/global/excel/uniqueitems.txt")
    s_path = os.path.join(MOD_ROOT, "data/global/excel/setitems.txt")

    for path, max_p in [(u_path, 12), (s_path, 9)]:
        with open(path, "r", encoding="utf-8") as f:
            raw_lines = [line.rstrip("\r\n") for line in f if line.strip()]
        hdr = raw_lines[0].split("\t")
        for line in raw_lines[1:]:
            parts = line.split("\t")
            row = {hdr[i]: (parts[i] if i < len(parts) else "") for i in range(len(hdr))}
            idx_name = row.get("index", "").strip()
            if not idx_name or idx_name == "Expansion":
                continue
            if row.get("disabled") == "1" or row.get("spawnable") == "0":
                continue
            lvl = max(1, int(row.get("lvl") or "1"))
            distilled_mods: List[Tuple[str, str, str, str, str]] = []  # (code, chance, param, min, max)

            for i in range(1, max_p + 1):
                pcode = row.get(f"prop{i}", "").strip()
                if not pcode or pcode in NON_DISTILLABLE_PROPS:
                    continue
                ppar = row.get(f"par{i}", "").strip()
                pmin = row.get(f"min{i}", "").strip()
                pmax = row.get(f"max{i}", "").strip()
                try:
                    v_min = int(pmin) if pmin else 0
                    v_max = int(pmax) if pmax else v_min
                except ValueError:
                    continue
                stat_val = (v_min + v_max) / 2.0
                if stat_val <= 0:
                    continue
                scaled = stat_val * 0.50 * (lvl / 100.0)
                if pcode in BINARY_OR_SKILL_PROPS or scaled < 1.0:
                    chance = max(1, int(round(scaled * 100)))
                    if pcode == "allskills":
                        chance = min(8, chance)
                    elif pcode in BINARY_OR_SKILL_PROPS:
                        chance = min(15, chance)
                    else:
                        chance = min(95, chance)
                    distilled_mods.append((pcode, str(chance), ppar, "1", "1"))
                else:
                    val_str = str(max(1, int(round(scaled))))
                    distilled_mods.append((pcode, "100", ppar, val_str, val_str))
                if len(distilled_mods) >= 5:
                    break

            if not distilled_mods:
                continue

            fields = {
                "description": f"Distill {idx_name} -> Jewel",
                "enabled": "1",
                "version": "100",
                "numinputs": "2",
                "input 1": f'"{idx_name}"' if (" " in idx_name or "," in idx_name) else idx_name,
                "input 2": "bml",
                "output": '"jew,nor"',
                "lvl": "0",
                "plvl": "0",
                "ilvl": "0",
            }
            for m_idx, (mc, mch, mpar, mmn, mmx) in enumerate(distilled_mods, start=1):
                fields[f"mod {m_idx}"] = mc
                fields[f"mod {m_idx} chance"] = mch
                fields[f"mod {m_idx} param"] = mpar
                fields[f"mod {m_idx} min"] = mmn
                fields[f"mod {m_idx} max"] = mmx

            out_lines.append(_make_row_str(num_cols, col_idx, fields))

    return out_lines


def build_cubemain(cfg: dict) -> str:
    headers, _ = read_excel_tsv("cubemain.txt")
    num_cols = len(headers)
    col_idx = {h: i for i, h in enumerate(headers)}

    lines: List[str] = ["\t".join(headers)]

    # 1. Core Quest Recipes (Horadric Staff, Khalim's Will ONLY — no Token of Absolution, no legacy crafts)
    lines.append(_make_row_str(num_cols, col_idx, {
        "description": "Staff of Kings + Amulet of the Viper -> Horadric Staff",
        "enabled": "1", "version": "0", "op": "28", "numinputs": "2",
        "input 1": "msf", "input 2": "vip", "output": "hst",
    }))
    lines.append(_make_row_str(num_cols, col_idx, {
        "description": "Khalim's Flail + Khalim's Heart + Khalim's Eye + Khalim's Brain -> Khalim's Will",
        "enabled": "1", "version": "0", "op": "28", "numinputs": "4",
        "input 1": "qf1", "input 2": "qhr", "input 3": "qey", "input 4": "qbr", "output": "qf2",
    }))

    # 2. 2 -> 1 Gem & Skull Upgrades (28 rows)
    for chain in GEM_UPGRADE_CHAINS:
        for i in range(len(chain) - 1):
            src, dst = chain[i], chain[i + 1]
            lines.append(_make_row_str(num_cols, col_idx, {
                "description": f"2 {src} -> {dst}",
                "enabled": "1", "version": "0", "numinputs": "2",
                "input 1": f'"{src},qty=2"', "output": dst,
            }))

    # 3. 2 -> 1 Rune Upgrades (32 rows, r01 -> r33)
    for r_idx in range(1, 33):
        src = f"r{r_idx:02d}"
        dst = f"r{r_idx + 1:02d}"
        lines.append(_make_row_str(num_cols, col_idx, {
            "description": f"2 {src} -> {dst}",
            "enabled": "1", "version": "100", "numinputs": "2",
            "input 1": f'"{src},qty=2"', "output": dst,
        }))

    # 4. Socket Punching (weap,nos / armo,nos + bml + skz -> 1-2 sockets); no socket clearing recipe
    for itype, label in [("weap", "Weapon"), ("armo", "Armor")]:
        lines.append(_make_row_str(num_cols, col_idx, {
            "description": f"Unsocketed {label} + Blacksmith's Malus + Perfect Skull -> 1-2 Sockets",
            "enabled": "1", "version": "100", "numinputs": "3",
            "input 1": f'"{itype},nos"', "input 2": "bml", "input 3": "skz",
            "output": "useitem",
            "mod 1": "sock", "mod 1 min": "1", "mod 1 max": "2",
        }))

    # 4b. Tempered Malus (um1,rar) Base-Tier Upgrades:
    # Upgrades ANY quality (Magic, Rare, Set, Unique, or Crafted) Weapon or Armor from
    # Normal -> Exceptional (with +5 levelreq) or Exceptional -> Elite (with +7 levelreq).
    # Because um1,rar can ONLY be produced by Charsi's "Temper Malus" (Imbue) quest reward,
    # a character can only ever perform 3 base-tier upgrades across an entire playthrough!
    for itype, label in [("weap", "Weapon"), ("armo", "Armor")]:
        lines.append(_make_row_str(num_cols, col_idx, {
            "description": f"Normal {label} (Any Quality) + Tempered Malus (um1,rar) -> Exceptional {label}",
            "enabled": "1", "version": "100", "numinputs": "2",
            "input 1": f'"{itype},bas"', "input 2": '"um1,rar"',
            "output": '"useitem,mod,exc"',
            "mod 1": "levelreq", "mod 1 min": "5", "mod 1 max": "5",
        }))
        lines.append(_make_row_str(num_cols, col_idx, {
            "description": f"Exceptional {label} (Any Quality) + Tempered Malus (um1,rar) -> Elite {label}",
            "enabled": "1", "version": "100", "numinputs": "2",
            "input 1": f'"{itype},exc"', "input 2": '"um1,rar"',
            "output": '"useitem,mod,eli"',
            "mod 1": "levelreq", "mod 1 min": "7", "mod 1 max": "7",
        }))

    # QA Throwaway Recipe (only when qa_cube_starter_kit is enabled in mod_config.json)
    if cfg.get("economy", {}).get("qa_cube_starter_kit", False):
        for itype, label in [("weap", "Weapon"), ("armo", "Armor")]:
            lines.append(_make_row_str(num_cols, col_idx, {
                "description": f"QA: Any {label} alone -> Ethereal Magic {label}",
                "enabled": "1", "version": "100", "numinputs": "1",
                "input 1": itype,
                "output": '"usetype,mag,eth"',
                "ilvl": "100",
            }))

    # 5. Unique / Set / Boss Charm -> Jewel Distillation (~545 rows)
    distill_lines = _build_distillation_rows(num_cols, col_idx)
    lines.extend(distill_lines)

    # 5b. 3-Tier Lockbox + Paired Lockbox Key -> Guaranteed Unique or Set Item
    from mod_builder.lockboxes import get_lockbox_registry

    for entry in get_lockbox_registry():
        bcode = str(entry["code"])
        kcode = str(entry["key_code"])
        idx_name = str(entry["index"])
        bname = str(entry["box_name"])
        valid_keys = ("key", "ky0", "ky1") if kcode == "key" else (kcode,)
        for kc in valid_keys:
            lines.append(_make_row_str(num_cols, col_idx, {
                "description": f"Unlock {bname} ({bcode}) + {kc} -> {idx_name}",
                "enabled": "1",
                "version": "100",
                "numinputs": "2",
                "input 1": bcode,
                "input 2": kc,
                "output": idx_name,
                "lvl": "99",
            }))

    # 6. Case B Full Cartesian 1-Step Gem Pact + 3-Rune Slot-Specific Crafting (1,145,375 rows):
    # Evaluated top-to-bottom across our 5 Slot Groups:
    #   1) weap (100% Weapon spec)
    #   2) gljw (60% Weapon spec -> Gloves, Rings, Amulets)
    #   3) btbl (60% Armor/Helm spec -> Boots, Belts)
    #   4) shld (100% Shield spec -> Shields, Paladin Shields, Necro Heads)
    #   5) armo (100% Armor/Helm spec catch-all -> Body Armor, Helms, Pelts, Primal Helms, Circlets)
    slot_groups = [
        ("weap", 0, 1.0, False),
        ("gljw", 0, 0.60, True),
        ("btbl", 1, 0.60, False),
        ("shld", 2, 1.0, False),
        ("armo", 1, 1.0, False),
    ]

    # Precompute scaled Rune mods for each (slot_idx, rune_idx, mult_key)
    # slot_idx in 0..4, rune_idx in 0..32, mult_key in (1, 2, 3)
    mult_map = {1: 1.0, 2: 2.25, 3: 3.75}
    rune_codes = [r[0] for r in RUNE_SPECS]
    rune_slot_mods: List[List[Dict[int, Tuple[str, str, str, str]]]] = []
    for s_idx, (_, gem_col_idx, s_scale, is_gljw) in enumerate(slot_groups):
        s_list = []
        for r_idx, r_spec in enumerate(RUNE_SPECS):
            # r_spec = (code, sem_name, wmod, hmod, smod)
            raw_mod = r_spec[2 + gem_col_idx]
            m_dict = {}
            for cnt, m_val in mult_map.items():
                m_dict[cnt] = _scale_craft_mod(raw_mod, s_scale, m_val, is_gljw=is_gljw)
            s_list.append(m_dict)
        rune_slot_mods.append(s_list)

    # Precompute all 6,545 3-Rune combinations per slot_idx as ready-to-join tab strings!
    # In cubemain.txt headers:
    # 0:description, 1:enabled, 2:firstLadderSeason, 3:lastLadderSeason, 4:min diff, 5:version,
    # 6:op, 7:param, 8:value, 9:class, 10:numinputs, 11:input 1, 12:input 2, 13:input 3, 14:input 4, 15:input 5,
    # 16:input 6, 17:input 7, 18:output, 19:lvl, 20:plvl, 21:ilvl,
    # 22:mod 1, 23:mod 1 chance, 24:mod 1 param, 25:mod 1 min, 26:mod 1 max,
    # 27:mod 2, 28:mod 2 chance, 29:mod 2 param, 30:mod 2 min, 31:mod 2 max,
    # 32..46: mod 3..mod 5 (15 columns), 47..102: output b/c (56 columns), 103:*eol ("0")
    tail_empty = "\t" * (num_cols - 47 - 1) + "\t0"

    slot_rune_Data: List[List[Tuple[str, str]]] = []
    # Each element in slot_rune_Data[s_idx] is (inputs_3_to_5_tab_str, mods_3_to_5_tab_str)
    for s_idx in range(len(slot_groups)):
        combos: List[Tuple[str, str]] = []
        rmods = rune_slot_mods[s_idx]

        # A) 3 identical runes: "rXX,qty=3" (33 combos)
        for i in range(33):
            rc = rune_codes[i]
            inp_str = f'"{rc},qty=3"\t\t'
            m3 = rmods[i][3]
            mod_str = f"{m3[0]}\t\t{m3[1]}\t{m3[2]}\t{m3[3]}\t\t\t\t\t\t\t\t\t\t"
            combos.append((inp_str, mod_str))

        # B) 2 identical + 1 different: "rXX,qty=2" + rYY (33 * 32 = 1,056 combos)
        for i in range(33):
            rc1 = rune_codes[i]
            m3 = rmods[i][2]
            for j in range(33):
                if i == j:
                    continue
                rc2 = rune_codes[j]
                m4 = rmods[j][1]
                inp_str = f'"{rc1},qty=2"\t{rc2}\t'
                mod_str = f"{m3[0]}\t\t{m3[1]}\t{m3[2]}\t{m3[3]}\t{m4[0]}\t\t{m4[1]}\t{m4[2]}\t{m4[3]}\t\t\t\t\t"
                combos.append((inp_str, mod_str))

        # C) 3 different runes: rXX + rYY + rZZ, i < j < k (5,456 combos)
        for i in range(33):
            rc1 = rune_codes[i]
            m3 = rmods[i][1]
            for j in range(i + 1, 33):
                rc2 = rune_codes[j]
                m4 = rmods[j][1]
                for k in range(j + 1, 33):
                    rc3 = rune_codes[k]
                    m5 = rmods[k][1]
                    inp_str = f"{rc1}\t{rc2}\t{rc3}"
                    mod_str = (
                        f"{m3[0]}\t\t{m3[1]}\t{m3[2]}\t{m3[3]}\t"
                        f"{m4[0]}\t\t{m4[1]}\t{m4[2]}\t{m4[3]}\t"
                        f"{m5[0]}\t\t{m5[1]}\t{m5[2]}\t{m5[3]}"
                    )
                    combos.append((inp_str, mod_str))

        slot_rune_Data.append(combos)

    out_path = os.path.join(MOD_ROOT, "data/global/excel/cubemain.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    craft_count = 0
    with open(out_path, "wb") as f:
        # Write header + non-craft recipes first
        f.write(("\r\n".join(lines) + "\r\n").encode("utf-8"))

        # Stream-write the 5 Slot Groups x 35 Gems x 6,545 Rune combinations:
        # First pass for each slot group: Ethereal Magic base ("<slot_code>,mag,eth" -> "usetype,crf,eth")
        # Second pass for each slot group: Non-Ethereal Magic base ("<slot_code>,mag" -> "usetype,crf")
        # Because cubemain.txt evaluates top-to-bottom, an Ethereal Magic item matches the ",eth" row first!
        for s_idx, (slot_code, gem_col_idx, s_scale, _) in enumerate(slot_groups):
            combos = slot_rune_Data[s_idx]
            for is_eth in (True, False):
                inp1_str = f'"{slot_code},mag,eth"' if is_eth else f'"{slot_code},mag"'
                out_str = '"usetype,crf,eth"' if is_eth else '"usetype,crf"'
                desc_tag = "EthCraft" if is_eth else "Craft"

                for g_spec in GEM_SPECS:
                    g_code = g_spec[0]
                    raw_boon = g_spec[1 + gem_col_idx]
                    boon = _scale_gem_boon(raw_boon, s_scale)
                    curse = GEM_CURSES[g_code]
                    lvl_s, plvl_s = GEM_LEVEL_RULES[g_code]

                    prefix_0_12 = f"{desc_tag} {slot_code} {g_code}\t1\t\t\t\t100\t\t\t\t\t5\t{inp1_str}\t{g_code}\t"
                    mid_16_31 = (
                        f"\t\t\t{out_str}\t{lvl_s}\t{plvl_s}\t\t"
                        f"{boon[0]}\t\t{boon[1]}\t{boon[2]}\t{boon[3]}\t"
                        f"{curse[0]}\t\t{curse[1]}\t{curse[2]}\t{curse[3]}\t"
                    )

                    chunk: List[str] = []
                    for inp_3_5, mod_3_5 in combos:
                        chunk.append(f"{prefix_0_12}{inp_3_5}{mid_16_31}{mod_3_5}{tail_empty}")
                    f.write(("\r\n".join(chunk) + "\r\n").encode("utf-8"))
                    craft_count += len(chunk)

    print(
        f"[cubemain] Wrote {len(lines) - 1} utility/distill rows "
        f"({len(distill_lines)} distillations) + {craft_count} crafting rows "
        f"= {len(lines) - 1 + craft_count} total rows"
    )
    return out_path

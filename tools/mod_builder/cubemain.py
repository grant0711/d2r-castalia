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

# Gem Tier output level rules (N - 1 of next Gem tier req, with Perfect = plvl 100):
# Chipped (req 1) -> lvl=14, Flawed (req 15) -> lvl=29, Standard (req 30) -> lvl=44,
# Flawless (req 45) -> lvl=59, Perfect (req 60) -> plvl=100 (100% of clvl)
GEM_LEVEL_RULES: Dict[str, Tuple[str, str]] = {
    "gcr": ("14", ""), "gfr": ("29", ""), "gsr": ("44", ""), "glr": ("59", ""), "gpr": ("", "100"),
    "gcb": ("14", ""), "gfb": ("29", ""), "gsb": ("44", ""), "glb": ("59", ""), "gpb": ("", "100"),
    "gcy": ("14", ""), "gfy": ("29", ""), "gsy": ("44", ""), "gly": ("59", ""), "gpy": ("", "100"),
    "gcg": ("14", ""), "gfg": ("29", ""), "gsg": ("44", ""), "glg": ("59", ""), "gpg": ("", "100"),
    "gcw": ("14", ""), "gfw": ("29", ""), "gsw": ("44", ""), "glw": ("59", ""), "gpw": ("", "100"),
    "gcv": ("14", ""), "gfv": ("29", ""), "gsv": ("44", ""), "gzv": ("59", ""), "gpv": ("", "100"),
    "skc": ("14", ""), "skf": ("29", ""), "sku": ("44", ""), "skl": ("59", ""), "skz": ("", "100"),
}

# Gem Tier multipliers for Rune Affixes (capped at 0.90x-1.00x for Perfect Gems, no negative bust):
# Tier 0 (Chipped):  0.20x - 0.30x
# Tier 1 (Flawed):   0.35x - 0.45x
# Tier 2 (Standard): 0.55x - 0.65x
# Tier 3 (Flawless): 0.75x - 0.85x
# Tier 4 (Perfect):  0.90x - 1.00x
GEM_TIER_MULTS: List[Tuple[float, float]] = [
    (0.20, 0.30),
    (0.35, 0.45),
    (0.55, 0.65),
    (0.75, 0.85),
    (0.90, 1.00),
]

GEM_TIER_INDEX: Dict[str, int] = {
    "gcr": 0, "gfr": 1, "gsr": 2, "glr": 3, "gpr": 4,
    "gcb": 0, "gfb": 1, "gsb": 2, "glb": 3, "gpb": 4,
    "gcy": 0, "gfy": 1, "gsy": 2, "gly": 3, "gpy": 4,
    "gcg": 0, "gfg": 1, "gsg": 2, "glg": 3, "gpg": 4,
    "gcw": 0, "gfw": 1, "gsw": 2, "glw": 3, "gpw": 4,
    "gcv": 0, "gfv": 1, "gsv": 2, "gzv": 3, "gpv": 4,
    "skc": 0, "skf": 1, "sku": 2, "skl": 3, "skz": 4,
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
    "aura", "oskill", "charged", "*charged", "hit-skill", "gethit-skill", "Gethit-skill",
    "att-skill", "kill-skill", "death-skill", "levelup-skill", "reanimate",
    "sock", "indestruct", "ethereal", "rep-dur", "rep-quant", "stack", "dur",
    "pierce-immunity-cold", "pierce-immunity-fire", "pierce-immunity-light",
    "pierce-immunity-poison", "pierce-immunity-damage", "pierce-immunity-magic",
    "cannotbefrozen", "nofreeze", "*enr", "*hp",
}

PER_LEVEL_PROPS = {
    "gold%/lvl", "deadly/lvl", "mag%/lvl", "dmg%/lvl", "dmg/lvl", "ac/lvl",
    "abs-fire/lvl", "abs-cold/lvl", "res-ltng/lvl", "att%/lvl", "att/lvl",
    "dmg-dem/lvl", "dmg-und/lvl", "att-dem/lvl", "att-und/lvl", "hp/lvl",
    "mana/lvl", "str/lvl", "dex/lvl", "vit/lvl", "thorns/lvl", "stam/lvl",
    "regen-stam/lvl",
}

RANGE_DAMAGE_PROPS = {
    "dmg-norm", "dmg-fire", "dmg-ltng", "dmg-cold", "dmg-pois", "dmg-mag", "dmg-elem",
}

BINARY_OR_SKILL_PROPS = {
    "allskills", "randclassskill", "ama", "pal", "nec", "sor", "bar", "dru", "ass", "war",
    "fireskill", "skill", "skill-rand", "skilltab", "skilltab-war",
    "knock", "ignore-ac", "noheal", "half-freeze", "rip",
    "roguesbow-affix1",
}

# Explicit hardcoded (min_cap, max_cap) bounds for every non-binary distillable property
DISTILL_AFFIX_CAPS: Dict[str, Tuple[int, int]] = {
    # Tier 1: Gold Find, Combat Mechanics, Pierce & Skill Damage
    "gold%": (3, 30),
    "gold%/lvl": (1, 6),
    "crush": (1, 12),
    "deadly": (1, 15),
    "deadly/lvl": (1, 3),
    "openwounds": (2, 15),
    "pierce-fire": (1, 6),
    "pierce-ltng": (1, 6),
    "pierce-cold": (1, 6),
    "pierce-pois": (1, 6),
    "pierce-mag": (1, 6),
    "pierce-dmg": (1, 6),
    "extra-fire": (1, 6),
    "extra-ltng": (1, 6),
    "extra-cold": (1, 6),
    "extra-pois": (1, 6),
    "extra-mag": (1, 6),
    "pierce": (2, 15),
    "slow": (2, 12),
    "freeze": (1, 2),
    "stupidity": (1, 2),
    "howl": (3, 20),
    "magicarrow": (1, 5),
    "explosivearrow": (1, 5),
    # Tier 2: Experience, Magic Find & Vendor Economy
    "addxp": (1, 3),
    "mag%": (2, 20),
    "mag%/lvl": (1, 3),
    "cheap": (1, 5),
    # Tier 3: Primary Offense, Speed Breakpoints & Damage Reduction %
    "dmg%": (4, 45),
    "dmg%/lvl": (1, 4),
    "dmg": (1, 15),
    "dmg/lvl": (1, 4),
    "dmg-norm": (1, 20),
    "dmg-max": (1, 20),
    "dmg-min": (1, 12),
    "red-dmg%": (1, 8),
    "damageresist": (1, 8),
    "swing1": (1, 15),
    "swing2": (1, 15),
    "swing3": (1, 15),
    "cast1": (1, 10),
    "cast2": (1, 10),
    "cast3": (1, 10),
    "move1": (1, 10),
    "move2": (1, 10),
    "move3": (1, 10),
    "reduce-ac": (2, 12),
    "dmg-ac": (-35, -4),
    "lifesteal": (1, 5),
    "manasteal": (1, 5),
    "balance1": (1, 10),
    "balance2": (1, 10),
    "balance3": (1, 10),
    "block": (1, 10),
    "block2": (1, 12),
    "block3": (1, 12),
    # Tier 4: Resistances, Absorb & Enhanced Defense
    "res-all": (1, 15),
    "res-all-max": (1, 4),
    "res-fire-max": (1, 4),
    "res-ltng-max": (1, 4),
    "res-cold-max": (1, 4),
    "res-pois-max": (1, 4),
    "abs-fire%": (1, 5),
    "abs-ltng%": (1, 5),
    "abs-cold%": (1, 5),
    "absorb-fire%": (1, 5),
    "abs-fire": (1, 6),
    "abs-ltng": (1, 6),
    "abs-cold": (1, 6),
    "abs-fire/lvl": (1, 2),
    "abs-cold/lvl": (1, 2),
    "ac%": (4, 50),
    "ac/lvl": (1, 6),
    "res-fire": (2, 25),
    "res-ltng": (2, 25),
    "res-cold": (2, 25),
    "res-pois": (2, 25),
    "res-mag": (2, 25),
    "res-ltng/lvl": (1, 3),
    "red-dmg": (1, 7),
    "red-mag": (1, 7),
    "res-pois-len": (4, 25),
    # Tier 5: Elemental Attack Damage, Sustain & Attack Rating
    "dmg-elem": (1, 90),
    "dmg-mag": (1, 90),
    "magdam-rand": (1, 2),
    "dmg-fire": (1, 90),
    "dmg-ltng": (1, 90),
    "dmg-cold": (1, 90),
    "dmg-pois": (4, 160),
    "heal-kill": (1, 5),
    "demon-heal": (1, 5),
    "mana-kill": (1, 5),
    "dmg-to-mana": (2, 15),
    "att%": (2, 25),
    "att%/lvl": (1, 2),
    "att": (5, 100),
    "att/lvl": (1, 6),
    "dmg-demon": (5, 60),
    "dmg-dem/lvl": (1, 6),
    "dmg-undead": (5, 60),
    "dmg-und/lvl": (1, 6),
    "att-demon": (8, 80),
    "att-dem/lvl": (1, 6),
    "att-undead": (8, 80),
    "att-und/lvl": (1, 6),
    # Tier 6: Attributes, Life/Mana, Regeneration & Requirements
    "all-stats": (1, 5),
    "hp%": (1, 8),
    "mana%": (1, 8),
    "hp": (2, 30),
    "hp/lvl": (1, 4),
    "mana": (2, 30),
    "mana/lvl": (1, 4),
    "str": (1, 10),
    "str/lvl": (1, 2),
    "dex": (1, 10),
    "dex/lvl": (1, 2),
    "vit": (1, 10),
    "vit/lvl": (1, 2),
    "enr": (1, 10),
    "regen": (1, 7),
    "regen-mana": (2, 15),
    "ease": (-25, -4),
    # Tier 8: Low-Priority Flat Defense, Thorns, Stamina & Flavor
    "ac": (2, 60),
    "ac-miss": (3, 60),
    "ac-hth": (3, 60),
    "thorns": (1, 20),
    "thorns/lvl": (1, 3),
    "light-thorns": (1, 20),
    "stam": (3, 30),
    "stam/lvl": (1, 3),
    "regen-stam": (3, 20),
    "regen-stam/lvl": (1, 3),
    "stamdrain": (3, 20),
    "light": (1, 3),
    "bloody": (1, 3),
}

# Explicit 50-rank Affix Priority Table (Tier 1 = Highest Priority -> Tier 8 = Lowest Priority)
_AFFIX_PRIORITY_TIERS: List[Tuple[int, List[str]]] = [
    # Tier 1: Signature Combat Mechanics, Pierce & Gold Find (Ranks 1-13)
    (1, ["gold%", "gold%/lvl"]),
    (2, ["crush"]),
    (3, ["deadly", "deadly/lvl"]),
    (4, ["openwounds"]),
    (5, ["pierce-fire", "pierce-ltng", "pierce-cold", "pierce-pois", "pierce-mag", "pierce-dmg"]),
    (6, ["extra-fire", "extra-ltng", "extra-cold", "extra-pois", "extra-mag"]),
    (7, ["ignore-ac"]),
    (8, ["pierce"]),
    (9, ["slow"]),
    (10, ["freeze"]),
    (11, ["half-freeze"]),
    (12, ["noheal", "rip"]),
    (13, ["knock", "stupidity", "howl", "magicarrow", "explosivearrow", "roguesbow-affix1"]),
    # Tier 2: Experience, Magic Find & Vendor Economy (Ranks 14-16)
    (14, ["addxp"]),
    (15, ["mag%", "mag%/lvl"]),
    (16, ["cheap"]),
    # Tier 3: Primary Offense, Speed Breakpoints & Damage Reduction % (Ranks 17-25)
    (17, ["dmg%", "dmg%/lvl"]),
    (18, ["dmg", "dmg/lvl", "dmg-norm", "dmg-max", "dmg-min"]),
    (19, ["red-dmg%", "damageresist"]),
    (20, ["swing1", "swing2", "swing3"]),
    (21, ["cast1", "cast2", "cast3"]),
    (22, ["move1", "move2", "move3"]),
    (23, ["reduce-ac", "dmg-ac"]),
    (24, ["lifesteal", "manasteal"]),
    (25, ["balance1", "balance2", "balance3", "block", "block2", "block3"]),
    # Tier 4: Resistances, Absorb & Enhanced Defense (Ranks 26-32)
    (26, ["res-all"]),
    (27, ["res-all-max", "res-fire-max", "res-ltng-max", "res-cold-max", "res-pois-max"]),
    (28, ["abs-fire%", "abs-ltng%", "abs-cold%", "absorb-fire%", "abs-fire", "abs-ltng", "abs-cold", "abs-fire/lvl", "abs-cold/lvl"]),
    (29, ["ac%", "ac/lvl"]),
    (30, ["res-fire", "res-ltng", "res-cold", "res-pois", "res-mag", "res-ltng/lvl"]),
    (31, ["red-dmg", "red-mag"]),
    (32, ["res-pois-len"]),
    # Tier 5: Elemental Attack Damage, Sustain & Attack Rating (Ranks 33-37)
    (33, ["dmg-elem", "dmg-mag", "magdam-rand", "dmg-fire", "dmg-ltng", "dmg-cold", "dmg-pois"]),
    (34, ["heal-kill", "demon-heal", "mana-kill", "dmg-to-mana"]),
    (35, ["att%", "att%/lvl", "att", "att/lvl"]),
    (36, ["dmg-demon", "dmg-dem/lvl", "dmg-undead", "dmg-und/lvl"]),
    (37, ["att-demon", "att-dem/lvl", "att-undead", "att-und/lvl"]),
    # Tier 6: Attributes, Life/Mana, Regeneration & Requirements (Ranks 38-42)
    (38, ["all-stats"]),
    (39, ["hp%", "mana%", "hp", "hp/lvl", "mana", "mana/lvl"]),
    (40, ["str", "str/lvl", "dex", "dex/lvl", "vit", "vit/lvl", "enr"]),
    (41, ["regen", "regen-mana"]),
    (42, ["ease"]),
    # Tier 7: Skill Levels (Ranks 43-45)
    (43, ["allskills", "randclassskill"]),
    (44, ["ama", "pal", "nec", "sor", "bar", "dru", "ass", "war", "skilltab", "skilltab-war", "fireskill"]),
    (45, ["skill", "skill-rand"]),
    # Tier 8: Low-Priority Flat Defense, Thorns, Stamina & Flavor (Ranks 46-50)
    (46, ["ac", "ac-miss", "ac-hth"]),
    (47, ["thorns", "thorns/lvl", "light-thorns"]),
    (48, ["stam", "stam/lvl", "regen-stam", "regen-stam/lvl", "stamdrain"]),
    (49, ["light"]),
    (50, ["bloody"]),
]

AFFIX_PRIORITY_RANK: Dict[str, int] = {
    code: rank
    for rank, codes in _AFFIX_PRIORITY_TIERS
    for code in codes
}


def _scale_craft_mod(
    mod: Tuple[str, str, str, str],
    slot_scale: float,
    gem_tier_mult: Tuple[float, float],
    rune_count: int = 1,
) -> Tuple[str, str, str, str]:
    """
    Compute (code, param, min_str, max_str) for a Rune craft modifier:
    - Binary properties (knock, ignore-ac, indestruct, etc.) always roll ("1", "1").
    - allskills rolls equal to the number of r33 runes used ("1" for 1x, "2" for 2x) across all gem tiers.
    - All numeric properties scale by:
        base_value * rune_count * slot_scale * [gem_min_mult, gem_max_mult]
    """
    code, param, mn_s, mx_s = mod

    if code in ("knock", "ignore-ac", "indestruct", "half-freeze", "noheal", "rip"):
        return (code, param, "1", "1")

    try:
        mn_v = int(mn_s)
        mx_v = int(mx_s)
    except ValueError:
        return (code, param, mn_s, mx_s)

    if code == "allskills":
        val_s = str(max(1, int(rune_count)))
        return (code, param, val_s, val_s)

    sign = -1 if mn_v < 0 or mx_v < 0 else 1
    abs_mn = abs(mn_v)
    abs_mx = abs(mx_v)

    g_min, g_max = gem_tier_mult
    low_f = abs_mn * rune_count * slot_scale * g_min
    high_f = abs_mx * rune_count * slot_scale * g_max

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


def _scale_gem_curse(
    curse: Tuple[str, str, str, str],
    slot_scale: float,
) -> Tuple[str, str, str, str]:
    code, param, mn_s, mx_s = curse
    try:
        mn_v = int(mn_s)
        mx_v = int(mx_s)
    except ValueError:
        return curse
    abs_lo = abs(mx_v)
    abs_hi = abs(mn_v)
    scaled_lo = max(1, int(round(abs_lo * slot_scale)))
    scaled_hi = max(scaled_lo, int(round(abs_hi * slot_scale)))
    return (code, param, str(-scaled_hi), str(-scaled_lo))


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


def _extract_and_consolidate_props(
    row: Dict[str, str],
    max_p: int,
) -> List[Tuple[int, int, str, str, float, float]]:
    """
    Extract raw properties from prop1..prop{max_p}, consolidate split damage columns
    (fire-min/max -> dmg-fire, ltng-min/max -> dmg-ltng, cold-min/max/len -> dmg-cold,
    pois-min/max/len -> dmg-pois, dmg-min+dmg-max -> dmg-norm), merge duplicate (pcode, ppar)
    entries, filter out non-distillable or penalty stats, and return sorted candidate list:
      [(priority_rank, first_col_idx, pcode, ppar, v_min, v_max), ...]
    """
    split_parts: Dict[str, Tuple[int, float, float]] = {}
    raw_entries: List[Tuple[int, str, str, float, float]] = []

    SPLIT_KEYS = {
        "fire-min", "fire-max",
        "ltng-min", "ltng-max",
        "cold-min", "cold-max", "cold-len",
        "pois-min", "pois-max", "pois-len",
    }

    has_dmg_min = any(row.get(f"prop{i}", "").strip() == "dmg-min" for i in range(1, max_p + 1))
    has_dmg_max = any(row.get(f"prop{i}", "").strip() == "dmg-max" for i in range(1, max_p + 1))
    consolidate_phys = has_dmg_min and has_dmg_max

    for i in range(1, max_p + 1):
        pcode = row.get(f"prop{i}", "").strip()
        if not pcode or pcode in NON_DISTILLABLE_PROPS:
            continue
        if pcode.endswith("-Affix1") or pcode.endswith("-Affix2") or pcode.endswith("-Affix3") or pcode.endswith("-Affix4") or pcode.endswith("-Affix5") or pcode.endswith("-Affix6"):
            continue
        ppar = row.get(f"par{i}", "").strip()
        pmin = row.get(f"min{i}", "").strip()
        pmax = row.get(f"max{i}", "").strip()

        if pcode in PER_LEVEL_PROPS:
            try:
                par_v = float(ppar) if ppar else float(pmin)
            except ValueError:
                continue
            if par_v <= 0:
                continue
            raw_entries.append((i, pcode, "", par_v, par_v))
            continue

        try:
            v_min = float(pmin) if pmin else 0.0
            v_max = float(pmax) if pmax else v_min
        except ValueError:
            continue

        if pcode in SPLIT_KEYS or (consolidate_phys and pcode in ("dmg-min", "dmg-max")):
            if pcode in split_parts:
                old_idx, old_mn, old_mx = split_parts[pcode]
                split_parts[pcode] = (old_idx, old_mn + v_min, old_mx + v_max)
            else:
                split_parts[pcode] = (i, v_min, v_max)
            continue

        if pcode in ("dmg%", "ignore-ac"):
            ppar = ""

        raw_entries.append((i, pcode, ppar, v_min, v_max))

    # Consolidate split elemental & physical damage components
    if "fire-min" in split_parts or "fire-max" in split_parts:
        idx = min(split_parts[k][0] for k in ("fire-min", "fire-max") if k in split_parts)
        mn = (split_parts["fire-min"][1] + split_parts["fire-min"][2]) / 2.0 if "fire-min" in split_parts else 1.0
        mx = (split_parts["fire-max"][1] + split_parts["fire-max"][2]) / 2.0 if "fire-max" in split_parts else mn
        raw_entries.append((idx, "dmg-fire", "", mn, max(mn, mx)))

    if "ltng-min" in split_parts or "ltng-max" in split_parts:
        idx = min(split_parts[k][0] for k in ("ltng-min", "ltng-max") if k in split_parts)
        mn = (split_parts["ltng-min"][1] + split_parts["ltng-min"][2]) / 2.0 if "ltng-min" in split_parts else 1.0
        mx = (split_parts["ltng-max"][1] + split_parts["ltng-max"][2]) / 2.0 if "ltng-max" in split_parts else mn
        raw_entries.append((idx, "dmg-ltng", "", mn, max(mn, mx)))

    if "cold-min" in split_parts or "cold-max" in split_parts:
        idx = min(split_parts[k][0] for k in ("cold-min", "cold-max") if k in split_parts)
        mn = (split_parts["cold-min"][1] + split_parts["cold-min"][2]) / 2.0 if "cold-min" in split_parts else 1.0
        mx = (split_parts["cold-max"][1] + split_parts["cold-max"][2]) / 2.0 if "cold-max" in split_parts else mn
        clen = str(max(25, int(round((split_parts["cold-len"][1] + split_parts["cold-len"][2]) / 2.0)))) if "cold-len" in split_parts else "50"
        raw_entries.append((idx, "dmg-cold", clen, mn, max(mn, mx)))

    if "pois-min" in split_parts or "pois-max" in split_parts:
        idx = min(split_parts[k][0] for k in ("pois-min", "pois-max") if k in split_parts)
        mn = (split_parts["pois-min"][1] + split_parts["pois-min"][2]) / 2.0 if "pois-min" in split_parts else 1.0
        mx = (split_parts["pois-max"][1] + split_parts["pois-max"][2]) / 2.0 if "pois-max" in split_parts else mn
        plen = str(max(25, int(round((split_parts["pois-len"][1] + split_parts["pois-len"][2]) / 2.0)))) if "pois-len" in split_parts else "50"
        raw_entries.append((idx, "dmg-pois", plen, mn, max(mn, mx)))

    if consolidate_phys and ("dmg-min" in split_parts or "dmg-max" in split_parts):
        idx = min(split_parts[k][0] for k in ("dmg-min", "dmg-max") if k in split_parts)
        mn = (split_parts["dmg-min"][1] + split_parts["dmg-min"][2]) / 2.0
        mx = (split_parts["dmg-max"][1] + split_parts["dmg-max"][2]) / 2.0
        raw_entries.append((idx, "dmg-norm", "", mn, max(mn, mx)))

    # Merge duplicate (pcode, ppar) on the same item
    merged: Dict[Tuple[str, str], Tuple[int, float, float]] = {}
    for idx, pcode, ppar, v_min, v_max in raw_entries:
        key = (pcode, ppar)
        if key in merged:
            old_idx, old_mn, old_mx = merged[key]
            merged[key] = (min(old_idx, idx), old_mn + v_min, old_mx + v_max)
        else:
            merged[key] = (idx, v_min, v_max)

    candidates: List[Tuple[int, int, str, str, float, float]] = []
    for (pcode, ppar), (idx, v_min, v_max) in merged.items():
        stat_val = (v_min + v_max) / 2.0
        if pcode in ("ease", "dmg-ac"):
            # Negative values are beneficial for ease (Requirements -%) and dmg-ac (-Monster Defense per Hit)
            if stat_val >= 0:
                continue
        else:
            if stat_val <= 0:
                continue

        rank = AFFIX_PRIORITY_RANK.get(pcode, 99)
        candidates.append((rank, idx, pcode, ppar, v_min, v_max))

    candidates.sort(key=lambda x: (x[0], x[1]))
    return candidates


def _build_distillation_rows(
    num_cols: int,
    col_idx: Dict[str, int],
) -> List[str]:
    """
    Generate Unique, Set & Unique Charm -> Crafted Jewel Distillation recipes:
    - Strictly requires 3 inputs: Unique/Set item + Blacksmith's Malus (bml) + Magic Jewel ("jew,mag")
    - Also emits base-code fallback ("<code>,uni" / "<code>,set") for all single-item base codes
    - output  = "jew,crf" with lvl=1 (below minimum jewel affix level=2 -> zero random magic affixes!)
    - mod 1..4 = Top 4 priority distillable properties scaled by 0.50 * (lvl / 100)
    """
    out_lines: List[str] = []

    # Read our modded uniqueitems.txt and setitems.txt from MOD_ROOT
    u_path = os.path.join(MOD_ROOT, "data/global/excel/uniqueitems.txt")
    s_path = os.path.join(MOD_ROOT, "data/global/excel/setitems.txt")

    for path, max_p, code_col, qual_tag in [
        (u_path, 12, "code", "uni"),
        (s_path, 9, "item", "set"),
    ]:
        with open(path, "r", encoding="utf-8") as f:
            raw_lines = [line.rstrip("\r\n") for line in f if line.strip()]
        hdr = raw_lines[0].split("\t")
        parsed_rows: List[Dict[str, str]] = []
        code_counts: Dict[str, int] = {}
        for line in raw_lines[1:]:
            parts = line.split("\t")
            row = {hdr[i]: (parts[i] if i < len(parts) else "") for i in range(len(hdr))}
            idx_name = row.get("index", "").strip()
            if not idx_name or idx_name == "Expansion":
                continue
            if row.get("disabled") == "1" or row.get("spawnable") == "0":
                continue
            raw_lvl = int(row.get("lvl") or "0")
            if raw_lvl <= 0:
                # Exclude Act Quest items (lvl=0) from distillation
                continue
            if qual_tag == "set" and raw_lvl >= 100:
                continue
            bcode = row.get(code_col, "").strip()
            if bcode in ("jew", "cjw", "cm1", "cm2", "cm3", "cs2"):
                # Exclude Unique Jewels and Unique Charms from Jewel Distillation
                continue
            if bcode:
                code_counts[bcode] = code_counts.get(bcode, 0) + 1
            parsed_rows.append(row)

        for row in parsed_rows:
            idx_name = row.get("index", "").strip()
            bcode = row.get(code_col, "").strip()
            lvl = max(1, int(row.get("lvl") or "1"))
            lvl_req = max(1, int(row.get("lvl req") or str(lvl)))
            eff_lvl = min(100, max(lvl, lvl_req))
            # 15%-25% scaling curve (15% at eff_lvl=0 -> 25% at eff_lvl=100) with +/-25% roll variability
            scale_factor = 0.15 + 0.10 * (eff_lvl / 100.0)
            low_factor = scale_factor * 0.75
            high_factor = scale_factor * 1.25
            binary_scale = 0.50 * (eff_lvl / 100.0)
            distilled_mods: List[Tuple[str, str, str, str, str]] = []  # (code, chance, param, min, max)

            candidates = _extract_and_consolidate_props(row, max_p)
            for _rank, _idx, pcode, ppar, v_min, v_max in candidates[:4]:
                stat_val = (v_min + v_max) / 2.0
                c_min, c_max = DISTILL_AFFIX_CAPS.get(pcode, (1, 100))

                if pcode in BINARY_OR_SKILL_PROPS:
                    chance = max(1, int(round(stat_val * binary_scale * 100)))
                    if pcode == "allskills":
                        chance = min(8, chance)
                    else:
                        chance = min(15, chance)
                    distilled_mods.append((pcode, str(chance), ppar, "1", "1"))
                elif pcode in PER_LEVEL_PROPS:
                    scaled_par = int(round(stat_val * scale_factor))
                    clamped_par = max(c_min, min(c_max, scaled_par))
                    distilled_mods.append((pcode, "100", str(clamped_par), "", ""))
                elif pcode in ("ease", "dmg-ac"):
                    abs_lo_cap = abs(c_max)  # e.g. 4
                    abs_hi_cap = abs(c_min)  # e.g. 25 or 35
                    lo_mag = max(abs_lo_cap, min(abs_hi_cap, int(round(abs(v_min) * low_factor))))
                    hi_mag = max(lo_mag, min(abs_hi_cap, int(round(abs(v_max) * high_factor))))
                    if hi_mag == abs_hi_cap and lo_mag > int(round(abs_hi_cap * 0.75)):
                        lo_mag = max(abs_lo_cap, min(abs_hi_cap - 1, int(round(abs_hi_cap * 0.75))))
                    if hi_mag == lo_mag and abs_lo_cap < abs_hi_cap:
                        if hi_mag < abs_hi_cap:
                            hi_mag += 1
                        else:
                            lo_mag -= 1
                    distilled_mods.append((pcode, "100", ppar, str(-hi_mag), str(-lo_mag)))
                elif pcode in RANGE_DAMAGE_PROPS:
                    if pcode == "dmg-ltng" and int(round(v_min)) == 1:
                        s_min = 1
                    else:
                        s_min = max(c_min, min(c_max, int(round(v_min * low_factor))))
                    s_max = max(s_min, min(c_max, int(round(v_max * high_factor))))
                    if s_max == c_max and s_min > int(round(c_max * 0.75)):
                        s_min = max(c_min, min(c_max - 1, int(round(c_max * 0.75))))
                    if s_max == s_min and c_min < c_max:
                        if s_max < c_max:
                            s_max += 1
                        else:
                            s_min -= 1
                    if pcode in ("dmg-cold", "dmg-pois", "dmg-elem") and not ppar:
                        ppar = "50"
                    distilled_mods.append((pcode, "100", ppar, str(s_min), str(s_max)))
                else:
                    lo_val = max(c_min, min(c_max, int(round(v_min * low_factor))))
                    hi_val = max(lo_val, min(c_max, int(round(v_max * high_factor))))
                    if hi_val == c_max and lo_val > int(round(c_max * 0.75)):
                        lo_val = max(c_min, min(c_max - 1, int(round(c_max * 0.75))))
                    if hi_val == lo_val and c_min < c_max:
                        if hi_val < c_max:
                            hi_val += 1
                        else:
                            lo_val -= 1
                    distilled_mods.append((pcode, "100", ppar, str(lo_val), str(hi_val)))

            if not distilled_mods:
                continue

            input_specs: List[Tuple[str, str]] = [
                (f'"{idx_name}"' if "," in idx_name else idx_name, idx_name),
            ]
            if bcode and code_counts.get(bcode, 0) == 1:
                input_specs.append((f'"{bcode},{qual_tag}"', f"{idx_name} ({bcode},{qual_tag})"))

            for in1_val, desc_lbl in input_specs:
                fields = {
                    "description": f"Distill {desc_lbl} + Magic Jewel -> Crafted Jewel",
                    "enabled": "1",
                    "version": "100",
                    "numinputs": "3",
                    "input 1": in1_val,
                    "input 2": "bml",
                    "input 3": '"jew,mag"',
                    "output": '"jew,crf"',
                    "lvl": "1",
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

    # 3b. 5-Tier Gem-Assisted Rune Splitting (160 rows, r02..r33 + gem0..gem4 -> 50%..100% value recovery)
    for n in range(2, 34):
        src = f"r{n:02d}"
        r_m1 = f"r{n - 1:02d}"
        r_m2 = f"r{max(1, n - 2):02d}"
        r_m3 = f"r{max(1, n - 3):02d}"
        if n == 2:
            # r02 (worth 2 x r01): Chipped/Flawed/Standard -> 1 x r01; Flawless/Perfect -> 2 x r01
            tier_outputs = [
                ("gem0", r_m1, "", ""),
                ("gem1", r_m1, "", ""),
                ("gem2", r_m1, "", ""),
                ("gem3", r_m1, r_m1, ""),
                ("gem4", r_m1, r_m1, ""),
            ]
        elif n == 3:
            # r03 (worth 2 x r02 = 4 x r01): 50% -> 75% -> 75% -> 100% -> 100%
            tier_outputs = [
                ("gem0", r_m1, "", ""),
                ("gem1", r_m1, r_m2, ""),
                ("gem2", r_m1, r_m2, ""),
                ("gem3", r_m1, r_m2, r_m2),
                ("gem4", r_m1, r_m1, ""),
            ]
        else:
            # r04..r33: 50% (gem0) -> 62.5% (gem1) -> 75% (gem2) -> 87.5% (gem3) -> 100% (gem4)
            tier_outputs = [
                ("gem0", r_m1, "", ""),
                ("gem1", r_m1, r_m3, ""),
                ("gem2", r_m1, r_m2, ""),
                ("gem3", r_m1, r_m2, r_m3),
                ("gem4", r_m1, r_m1, ""),
            ]
        for gem_type, out_a, out_b, out_c in tier_outputs:
            outs_lbl = " + ".join(x for x in (out_a, out_b, out_c) if x)
            row_fields = {
                "description": f"Split {src} + {gem_type} -> {outs_lbl}",
                "enabled": "1", "version": "100", "numinputs": "2",
                "input 1": src, "input 2": gem_type,
                "output": out_a,
            }
            if out_b:
                row_fields["output b"] = out_b
            if out_c:
                row_fields["output c"] = out_c
            lines.append(_make_row_str(num_cols, col_idx, row_fields))

    # 4. Socket Punching & Socket Clearing (bml + skz):
    # - Unsocketed (weap,nos / armo,nos) + bml + skz -> punches 1-2 sockets
    # - Socketed   (weap,sock / armo,sock) + bml + skz -> clears sockets ("useitem,uns", destroying socketed contents)
    for itype, label in [("weap", "Weapon"), ("armo", "Armor")]:
        lines.append(_make_row_str(num_cols, col_idx, {
            "description": f"Unsocketed {label} + Blacksmith's Malus + Perfect Skull -> 1-2 Sockets",
            "enabled": "1", "version": "100", "numinputs": "3",
            "input 1": f'"{itype},nos"', "input 2": "bml", "input 3": "skz",
            "output": "useitem",
            "mod 1": "sock", "mod 1 min": "1", "mod 1 max": "2",
        }))
        lines.append(_make_row_str(num_cols, col_idx, {
            "description": f"Socketed {label} + Blacksmith's Malus + Perfect Skull -> Clear Sockets",
            "enabled": "1", "version": "100", "numinputs": "3",
            "input 1": f'"{itype},sock"', "input 2": "bml", "input 3": "skz",
            "output": '"useitem,uns"',
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

    # 6. 1-Step Gem + 2-Rune Slot-Specific Crafting across all 8 Disjoint Slot Groups
    # and all 35 Gems/Skulls (Chipped -> Perfect), with zero negative busts:
    #   1) weap (1.00x Weapon spec, Eth + Non-Eth)
    #   2) glov (0.60x Weapon spec, Eth + Non-Eth; omits r31 Ignore Target's Defense)
    #   3) ring (0.50x Weapon spec -> Rings, Non-Eth only; omits r31 Ignore Target's Defense & r32 Indestructible)
    #   4) amul (0.50x Armor/Helm spec -> Amulets, Non-Eth only; follows Armor/Helm Gem & Rune slot; omits r32 Indestructible)
    #   5) btbl (0.60x Armor/Helm spec -> Boots & Belts, Eth + Non-Eth)
    #   6) helm (0.75x Armor/Helm spec -> Helms, Circlets, Pelts, Primal Helms, Eth + Non-Eth)
    #   7) shld (1.00x Shield spec -> Shields, Paladin Shields, Necro Heads, Grimoires, Eth + Non-Eth)
    #   8) tors (1.00x Armor/Helm spec -> Body Armor, Eth + Non-Eth)
    slot_groups = [
        ("weap", 0, 1.00, True, set()),
        ("glov", 0, 0.60, True, {"r31"}),
        ("ring", 0, 0.50, False, {"r31", "r32"}),
        ("amul", 1, 0.50, False, {"r32"}),
        ("btbl", 1, 0.60, True, set()),
        ("helm", 1, 0.75, True, set()),
        ("shld", 2, 1.00, True, set()),
        ("tors", 1, 1.00, True, set()),
    ]

    rune_codes = [r[0] for r in RUNE_SPECS]
    tail_empty = "\t" * (num_cols - 47 - 1) + "\t0"

    # Flat -5 item_levelreq perk stamped into mod 4 of each Gem+Rune Crafted recipe to
    # soften D2R's hardcoded Crafted penalty (+10 + 3*N_affixes) without dropping high-req
    # bases more than 5 levels below their base requirement.
    gem_craft_levelreq_offsets = ("-5", "-5", "-5", "-5", "-5")

    # Precompute 2-Rune combinations per (slot_idx, gem_tier_idx)
    # slot_tier_combos[s_idx][t_idx] = List[(inp_3_5_str, mod_2_5_str)]
    slot_tier_combos: List[List[List[Tuple[str, str]]]] = []
    for s_idx, (_, gem_col_idx, s_scale, _, forbidden_runes) in enumerate(slot_groups):
        tier_list: List[List[Tuple[str, str]]] = []
        for t_idx, g_mult in enumerate(GEM_TIER_MULTS):
            req_off = gem_craft_levelreq_offsets[t_idx]
            rmods_1: List[Tuple[str, str, str, str]] = []
            rmods_2: List[Tuple[str, str, str, str]] = []
            for r_spec in RUNE_SPECS:
                raw_mod = r_spec[2 + gem_col_idx]
                rmods_1.append(_scale_craft_mod(raw_mod, s_scale, g_mult, rune_count=1))
                rmods_2.append(_scale_craft_mod(raw_mod, s_scale, g_mult, rune_count=2))

            combos: List[Tuple[str, str]] = []
            # A) 2 identical runes: "rXX,qty=2" -> mod 2 (cols 27..31), mod 3 empty (32..36), mod 4 = levelreq (37..41), mod 5 empty (42..46)
            for i in range(33):
                rc = rune_codes[i]
                if rc in forbidden_runes:
                    continue
                inp_str = f'"{rc},qty=2"\t\t'
                m2 = rmods_2[i]
                mod_str = f"{m2[0]}\t\t{m2[1]}\t{m2[2]}\t{m2[3]}\t\t\t\t\t\tlevelreq\t\t\t{req_off}\t{req_off}\t\t\t\t\t"
                combos.append((inp_str, mod_str))

            # B) 2 different runes: rXX + rYY (i < j) -> mod 2 (27..31), mod 3 (32..36), mod 4 = levelreq (37..41), mod 5 empty (42..46)
            for i in range(33):
                rc1 = rune_codes[i]
                if rc1 in forbidden_runes:
                    continue
                m2 = rmods_1[i]
                for j in range(i + 1, 33):
                    rc2 = rune_codes[j]
                    if rc2 in forbidden_runes:
                        continue
                    m3 = rmods_1[j]
                    inp_str = f"{rc1}\t{rc2}\t"
                    mod_str = f"{m2[0]}\t\t{m2[1]}\t{m2[2]}\t{m2[3]}\t{m3[0]}\t\t{m3[1]}\t{m3[2]}\t{m3[3]}\tlevelreq\t\t\t{req_off}\t{req_off}\t\t\t\t\t"
                    combos.append((inp_str, mod_str))

            tier_list.append(combos)
        slot_tier_combos.append(tier_list)

    out_path = os.path.join(MOD_ROOT, "data/global/excel/cubemain.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    craft_count = 0
    with open(out_path, "wb") as f:
        # Write header + non-craft recipes first
        f.write(("\r\n".join(lines) + "\r\n").encode("utf-8"))

        for s_idx, (slot_code, gem_col_idx, s_scale, allow_eth, _) in enumerate(slot_groups):
            eth_variants = (True, False) if allow_eth else (False,)
            for is_eth in eth_variants:
                inp1_str = f'"{slot_code},mag,eth"' if is_eth else f'"{slot_code},mag"'
                out_str = '"usetype,crf,eth"' if is_eth else '"usetype,crf"'
                desc_tag = "EthCraft" if is_eth else "Craft"

                for g_spec in GEM_SPECS:
                    g_code = g_spec[0]
                    t_idx = GEM_TIER_INDEX[g_code]
                    combos = slot_tier_combos[s_idx][t_idx]
                    raw_boon = g_spec[1 + gem_col_idx]
                    boon = _scale_gem_boon(raw_boon, s_scale)
                    lvl_s, plvl_s = GEM_LEVEL_RULES[g_code]

                    prefix_0_12 = f"{desc_tag} {slot_code} {g_code}\t1\t\t\t\t100\t\t\t\t\t4\t{inp1_str}\t{g_code}\t"
                    mid_16_26 = (
                        f"\t\t\t{out_str}\t{lvl_s}\t{plvl_s}\t\t"
                        f"{boon[0]}\t\t{boon[1]}\t{boon[2]}\t{boon[3]}\t"
                    )

                    chunk: List[str] = []
                    for inp_3_5, mod_2_5 in combos:
                        chunk.append(f"{prefix_0_12}{inp_3_5}{mid_16_26}{mod_2_5}{tail_empty}")
                    f.write(("\r\n".join(chunk) + "\r\n").encode("utf-8"))
                    craft_count += len(chunk)

    print(
        f"[cubemain] Wrote {len(lines) - 1} utility/distill rows "
        f"({len(distill_lines)} distillations) + {craft_count} crafting rows "
        f"= {len(lines) - 1 + craft_count} total rows"
    )
    return out_path

#!/usr/bin/env python3
"""
balance.py — Data-driven Progression, TTK & Area Clear Balance Simulator for Castalia (D2R Mod).

Reads the actual built mod Excel tables (skills.txt, missiles.txt, monstats.txt, monlvl.txt,
levels.txt) and pristine vanilla tables (for comparison), then simulates character progression
from Normal Act 1 (lvl 1) through Hell Act 5 (lvl 82) against our mod's 10/20/30% baseline
resistances.

Usage:
    ./bin/d2r-balance sorc fire
    ./bin/d2r-balance sorc lightning
    ./bin/d2r-balance sorc fire --preset undergeared
"""
import argparse
import csv
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from mod_builder import common


EXCEL_DIR = getattr(common, "EXCEL_DIR", None) or common.MOD_EXCEL
VANILLA_EXCEL = common.VANILLA_EXCEL


@dataclass(frozen=True)
class Checkpoint:
    label: str
    diff: str          # "N", "NM", "H"
    clvl: int
    level_name: str    # levels.txt Name
    quest_pts: int
    gear_skills: int
    fcr: int           # Sorceress FCR -> cast frames
    base_res: int      # Mod baseline elemental resistance (10 / 20 / 30)


# Progression milestones covering every Sorc unlock tier (1/8/16/24/32/40) + mid-act leveling + NM + Hell endgame
CHECKPOINTS: List[Checkpoint] = [
    # Normal (10% res)
    Checkpoint("N-A1  L1 ", "N",   1, "Act 1 - Wilderness 1",  0,  0,   0, 10),  # Blood Moor
    Checkpoint("N-A1  L5 ", "N",   5, "Act 1 - Wilderness 4",  1,  0,   0, 10),  # Dark Wood
    Checkpoint("N-A1  L8 ", "N",   8, "Act 1 - Barracks",      1,  1,  10, 10),  # Barracks
    Checkpoint("N-A2  L15", "N",  15, "Act 2 - Desert 3",      2,  1,  20, 10),  # Far Oasis
    Checkpoint("N-A2  L16", "N",  16, "Act 2 - Tomb Tal 1",    2,  1,  20, 10),  # Tal Rasha's Tomb
    Checkpoint("N-A3  L21", "N",  21, "Act 3 - Jungle 3",      2,  2,  20, 10),  # Flayer Jungle
    Checkpoint("N-A3  L24", "N",  24, "Act 3 - Travincal",     2,  2,  37, 10),  # Travincal
    Checkpoint("N-A4  L27", "N",  27, "Act 4 - Mesa 3",        2,  2,  37, 10),  # City of the Damned
    Checkpoint("N-A4  L32", "N",  32, "Act 4 - Diablo 1",      4,  2,  37, 10),  # Chaos Sanctuary
    Checkpoint("N-A5  L34", "N",  34, "Act 5 - Siege 1",       4,  3,  37, 10),  # Bloody Foothills
    Checkpoint("N-A5  L40", "N",  40, "Act 5 - Baal Temple 2", 4,  3,  63, 10),  # WSK 2
    # Nightmare (20% res)
    Checkpoint("NM-A1 L41", "NM", 41, "Act 1 - Wilderness 4",  5,  4,  63, 20),  # Dark Wood
    Checkpoint("NM-A1 L42", "NM", 42, "Act 1 - Barracks",      5,  4,  63, 20),  # Barracks
    Checkpoint("NM-A2 L46", "NM", 46, "Act 2 - Desert 3",      6,  5,  63, 20),  # Far Oasis
    Checkpoint("NM-A2 L48", "NM", 48, "Act 2 - Tomb Tal 1",    6,  5,  63, 20),  # Tal Rasha's Tomb
    Checkpoint("NM-A3 L51", "NM", 51, "Act 3 - Jungle 3",      6,  5,  63, 20),  # Flayer Jungle
    Checkpoint("NM-A3 L54", "NM", 54, "Act 3 - Travincal",     6,  6,  63, 20),  # Travincal
    Checkpoint("NM-A4 L57", "NM", 57, "Act 4 - Mesa 3",        6,  6,  63, 20),  # City of the Damned
    Checkpoint("NM-A5 L58", "NM", 58, "Act 5 - Siege 1",       8,  7,  63, 20),  # Bloody Foothills
    Checkpoint("NM-A5 L60", "NM", 60, "Act 5 - Baal Temple 2", 8,  7,  63, 20),  # WSK 2
    # Hell (30% res)
    Checkpoint("H-A1  L65", "H",  65, "Act 1 - Wilderness 4",  9,  8, 105, 30),  # Dark Wood
    Checkpoint("H-A1  L67", "H",  67, "Act 1 - Barracks",      9,  8, 105, 30),  # Barracks
    Checkpoint("H-A2  L71", "H",  71, "Act 2 - Desert 3",     10,  9, 105, 30),  # Far Oasis
    Checkpoint("H-A3  L74", "H",  74, "Act 3 - Jungle 3",     10, 10, 105, 30),  # Flayer Jungle
    Checkpoint("H-A3  L75", "H",  75, "Act 3 - Travincal",    10, 10, 105, 30),  # Travincal
    Checkpoint("H-A4  L78", "H",  78, "Act 4 - Mesa 3",       10, 11, 105, 30),  # City of the Damned
    Checkpoint("H-A5  L80", "H",  80, "Act 5 - Siege 1",      12, 11, 105, 30),  # Bloody Foothills
    Checkpoint("H-A5  L82", "H",  82, "Act 5 - Baal Temple 2",12, 12, 105, 30),  # WSK 2
]

GEAR_PRESETS = {
    "competent": (1.0, 0),    # (gear_skills multiplier, fcr offset)
    "undergeared": (0.5, -20),
    "high": (1.35, 30),
}


def sorc_cast_frames(fcr: int) -> int:
    """Standard D2R Sorceress casting frames (25 fps)."""
    for bp, frames in [(200, 7), (105, 8), (63, 9), (37, 10), (20, 11), (9, 12)]:
        if fcr >= bp:
            return frames
    return 13


def _read_tsv(directory: str, filename: str) -> List[Dict[str, str]]:
    with open(os.path.join(directory, filename), newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _int(val: str, default: int = 0) -> int:
    try:
        return int(val.strip())
    except (ValueError, AttributeError):
        return default


def eval_edmg_base(row: Dict[str, str], slvl: int, is_missile: bool = False) -> Tuple[float, float]:
    """Exact D2R piecewise-linear elemental damage (EMin..EMax + EMinLev1..5) scaled by HitShift."""
    if slvl <= 0:
        return 0.0, 0.0
    emin = _int(row.get("EMin", "0"))
    emax = _int(row.get("EMax", "0"))
    if is_missile:
        min_cols = [f"MinELev{i}" for i in range(1, 6)]
        max_cols = [f"MaxELev{i}" for i in range(1, 6)]
    else:
        min_cols = [f"EMinLev{i}" for i in range(1, 6)]
        max_cols = [f"EMaxLev{i}" for i in range(1, 6)]

    # D2R level brackets: 2..8 (7 lvls), 9..16 (8 lvls), 17..22 (6 lvls), 23..28 (6 lvls), 29+ (rest)
    brackets = [
        (min(max(slvl - 1, 0), 7), 0),
        (min(max(slvl - 8, 0), 8), 1),
        (min(max(slvl - 16, 0), 6), 2),
        (min(max(slvl - 22, 0), 6), 3),
        (max(slvl - 28, 0), 4),
    ]
    for count, idx in brackets:
        if count > 0:
            emin += count * _int(row.get(min_cols[idx], "0"))
            emax += count * _int(row.get(max_cols[idx], "0"))

    hitshift = _int(row.get("HitShift", "8"), 8)
    scale = 2.0 ** (hitshift - 8)
    return emin * scale, emax * scale


def eval_mana_cost(srow: Dict[str, str], slvl: int) -> float:
    mana = _int(srow.get("mana", "0"))
    lvlmana = _int(srow.get("lvlmana", "0"))
    manashift = _int(srow.get("manashift", "8"), 8)
    minmana = _int(srow.get("minmana", "0"))
    raw = (mana + max(0, slvl - 1) * lvlmana) * (2.0 ** (manashift - 8))
    return max(float(minmana), raw)


class ModWorldData:
    """Loads area monster pools and computes Trash/Elite/Boss/Area eHP at each checkpoint."""

    def __init__(self, excel_dir: str):
        self.skills = {r["skill"]: r for r in _read_tsv(excel_dir, "skills.txt") if r.get("skill")}
        self.missiles = {r["Missile"]: r for r in _read_tsv(excel_dir, "missiles.txt") if r.get("Missile")}
        self.monstats = {r["Id"]: r for r in _read_tsv(excel_dir, "monstats.txt") if r.get("Id")}
        self.monlvl = {_int(r.get("Level", "0")): r for r in _read_tsv(excel_dir, "monlvl.txt") if r.get("Level")}
        self.levels = {r["Name"]: r for r in _read_tsv(excel_dir, "levels.txt") if r.get("Name")}

    def area_metrics(self, cp: Checkpoint) -> Dict[str, float]:
        lrow = self.levels[cp.level_name]
        alvl_col = {"N": "MonLvlEx", "NM": "MonLvlEx(N)", "H": "MonLvlEx(H)"}[cp.diff]
        den_col = {"N": "MonDen", "NM": "MonDen(N)", "H": "MonDen(H)"}[cp.diff]
        lhp_col = {"N": "L-HP", "NM": "L-HP(N)", "H": "L-HP(H)"}[cp.diff]
        mhp_cols = {
            "N": ("minHP", "maxHP"),
            "NM": ("MinHP(N)", "MaxHP(N)"),
            "H": ("MinHP(H)", "MaxHP(H)"),
        }[cp.diff]

        alvl = max(1, _int(lrow.get(alvl_col, "1"), 1))
        den = max(100, _int(lrow.get(den_col, "400"), 400))
        base_lhp = _int(self.monlvl.get(alvl, self.monlvl[85]).get(lhp_col, "100"), 100)

        mon_prefix = "mon" if cp.diff == "N" else "nmon"
        mon_ids = [lrow.get(f"{mon_prefix}{i}", "").strip() for i in range(1, 11)]
        mon_ids = [m for m in mon_ids if m and m in self.monstats]

        hps = []
        for mid in mon_ids:
            mrow = self.monstats[mid]
            lo = _int(mrow.get(mhp_cols[0], "100"), 100)
            hi = _int(mrow.get(mhp_cols[1], "100"), 100)
            if lo > 0 and hi > 0:
                hps.append(base_lhp * (lo + hi) / 200.0)
        avg_hp = sum(hps) / len(hps) if hps else float(base_lhp)

        res_mult = 1.0 / (1.0 - cp.base_res / 100.0)
        trash_ehp = avg_hp * res_mult
        boss_ehp = trash_ehp * 10.0  # Act-representative unique/mini-boss benchmark
        # Standardized area clear pool: normalized ~40 trash equivalents * (density / 400)
        area_ehp = trash_ehp * 40.0 * (den / 400.0)
        return {
            "alvl": float(alvl),
            "den": float(den),
            "trash_hp": avg_hp,
            "trash_ehp": trash_ehp,
            "boss_ehp": boss_ehp,
            "area_ehp": area_ehp,
        }


def _alloc_skill_points(
    clvl: int,
    quest_pts: int,
    req_level: int,
    syn_reqs: List[int],
    stance_req: int,
    unlock_only: bool = False,
) -> Tuple[int, List[int], int]:
    """Realistic player skill point allocation at a given clvl."""
    if clvl < req_level:
        return 0, [0] * len(syn_reqs), 0
    if unlock_only:
        # Just unlocked: 1 hard point in skill, leftover earlier points in earlier synergies/stance
        budget = max(0, clvl - 1 + quest_pts - 4)  # reserve ~4 pts for prereqs/1-pt passives
        main_blvl = 1
        budget = max(0, budget - 1)
        stance_blvl = 1 if (clvl >= stance_req and budget > 0) else 0
        budget = max(0, budget - stance_blvl)
        syn_blvls = []
        for sr in syn_reqs:
            if clvl >= sr and budget > 0:
                cap = min(20, clvl - sr + 1)
                put = min(budget, cap)
                syn_blvls.append(put)
                budget -= put
            else:
                syn_blvls.append(0)
        return main_blvl, syn_blvls, stance_blvl

    budget = max(1, clvl - 1 + quest_pts - 4)
    main_blvl = min(20, clvl - req_level + 1, budget)
    budget -= main_blvl

    # Put 1 pt in stance when unlocked, then max synergies, then pump stance
    stance_blvl = 0
    if clvl >= stance_req and budget > 0:
        stance_blvl = 1
        budget -= 1

    syn_blvls = [0] * len(syn_reqs)
    for idx, sr in enumerate(syn_reqs):
        if clvl >= sr and budget > 0:
            cap = min(20, clvl - sr + 1)
            put = min(budget, cap)
            syn_blvls[idx] = put
            budget -= put

    if clvl >= stance_req and budget > 0:
        cap = min(20, clvl - stance_req + 1)
        add = min(budget, max(0, cap - stance_blvl))
        stance_blvl += add
        budget -= add

    return main_blvl, syn_blvls, stance_blvl


def stance_elem_bonus(stance_slvl: int) -> float:
    """Our reworked Sorc stances grant +5% -> +30% elemental damage (5 + (lvl-1)*25/19)."""
    if stance_slvl <= 0:
        return 0.0
    return 5.0 + (stance_slvl - 1) * 25.0 / 19.0


def stance_fcr_bonus(stance_slvl: int) -> int:
    """Conflagration grants +5% -> +40% FCR (5 + (lvl-1)*35/19)."""
    if stance_slvl <= 0:
        return 0
    return int(5 + (stance_slvl - 1) * 35 // 19)


# ---------------------------------------------------------------------------
# Sorceress Fire Tree DPS Models (reads live built skills.txt + missiles.txt)
# ---------------------------------------------------------------------------
def eval_fire_skill(
    world: ModWorldData,
    slug: str,
    cp: Checkpoint,
    gear_skills: int,
    fcr: int,
    in_stance: bool,
    unlock_only: bool = False,
) -> Optional[Dict[str, float]]:
    """Return single-target & pack effective DPS (pre-res raw DPS; res handled by eHP)."""
    # (vname, reqlevel, syn_specs=[(vname, reqlevel, pct_per_lvl), ...], role, pack_targets_neutral, pack_targets_stance)
    SPEC = {
        "cinder_lance":    ("Fire Bolt",  1, [("Fire Ball", 8, 10), ("Inferno", 32, 10)],   "Line 1", 1.0, 2.2),
        "pyroclasm":       ("Fire Ball",  8, [("Fire Bolt", 1, 10), ("Inferno", 32, 10)],   "AoE 1",  4.0, 5.5),
        "backdraft":       ("Fire Wall",  8, [("Meteor", 24, 18), ("Fire Ball", 8, 6)],     "Combo",  4.5, 6.0),
        "skyfall":         ("Meteor",    24, [("Fire Wall", 8, 18), ("Fire Ball", 8, 6)],   "AoE 2",  5.0, 6.5),
        "brimstone_lance": ("Inferno",   32, [("Fire Ball", 8, 10), ("Hydra", 40, 10)],     "Line 2", 2.8, 3.5),
        "pyre_hydra":      ("Hydra",     40, [("Inferno", 32, 10), ("Fire Ball", 8, 10)],   "Cap",    2.0, 4.5),
    }
    vname, req_lvl, syns, role, pack_n, pack_s = SPEC[slug]
    if cp.clvl < req_lvl:
        return None

    main_blvl, syn_blvls, stance_blvl = _alloc_skill_points(
        cp.clvl, cp.quest_pts, req_lvl, [s[1] for s in syns], stance_req=16, unlock_only=unlock_only
    )
    slvl = main_blvl + gear_skills
    stance_slvl = (stance_blvl + gear_skills) if (in_stance and stance_blvl > 0) else 0

    srow = world.skills[vname]
    sym_pct = sum(blvl * pct for blvl, (_, _, pct) in zip(syn_blvls, syns))
    elem_mult = 1.0 + (stance_elem_bonus(stance_slvl) / 100.0 if in_stance else 0.0)
    syn_mult = 1.0 + sym_pct / 100.0

    eff_fcr = fcr + (stance_fcr_bonus(stance_slvl) if in_stance else 0)
    cast_sec = sorc_cast_frames(eff_fcr) / 25.0
    cd_frames = _int(srow.get("localdelay", "0"))
    cycle_sec = max(cast_sec, cd_frames / 25.0) if cd_frames > 0 else cast_sec
    mana_cost = eval_mana_cost(srow, slvl)
    mana_per_sec = mana_cost / cycle_sec

    lo, hi = eval_edmg_base(srow, slvl, is_missile=False)
    avg_hit = 0.5 * (lo + hi) * syn_mult * elem_mult

    if slug == "cinder_lance":
        st_dps = avg_hit / cast_sec
        pack_dps = st_dps * (pack_s if in_stance else pack_n)

    elif slug == "pyroclasm":
        st_dps = avg_hit / cast_sec
        pack_dps = st_dps * (pack_s if in_stance else pack_n)

    elif slug == "backdraft":
        # Vortex burns for ~2.0s (50 frames) via backdraft_center + explodes once via backdraft_explode
        # Avg effective damage per 2s cooldown cast = explosion + ~1.5s of vortex fire
        mrow = world.missiles.get("backdraft_explode", srow)
        mlo, mhi = eval_edmg_base(mrow, slvl, is_missile=True)
        expl_avg = 0.5 * (mlo + mhi) * syn_mult * elem_mult if mhi > 0 else avg_hit
        st_dps = (expl_avg + avg_hit * 0.6) / cycle_sec
        pack_dps = st_dps * (pack_s if in_stance else pack_n)

    elif slug == "skyfall":
        # Impact + burning crater (skyfall_fire: HitShift=3 -> 1/8 per frame * 25 fps * 3 stacking tiles avg)
        frow = world.missiles["skyfall_fire"]
        flo, fhi = eval_edmg_base(frow, slvl, is_missile=True)
        crater_dps = 0.5 * (flo + fhi) * 25.0 * 1.5 * syn_mult * elem_mult
        st_dps = (avg_hit / cycle_sec) + crater_dps
        pack_dps = st_dps * (pack_s if in_stance else pack_n)

    elif slug == "brimstone_lance":
        # Piercing direct hit + brimstone_wake (HitShift=4 -> 1/16 per frame * 25 fps)
        wrow = world.missiles["brimstone_wake"]
        wlo, whi = eval_edmg_base(wrow, slvl, is_missile=True)
        wake_dps_per_sec = 0.5 * (wlo + whi) * 25.0 * syn_mult * elem_mult
        # In Conflagration wake lasts ~2.6s (2-3 overlapping wakes on boss); neutral ~0.3s
        wake_contrib = wake_dps_per_sec * (1.8 if in_stance else 0.3)
        st_dps = (avg_hit / cast_sec) + wake_contrib
        pack_dps = (avg_hit / cast_sec) * (pack_s if in_stance else pack_n) + wake_contrib * (3.0 if in_stance else 1.5)

    elif slug == "pyre_hydra":
        # 1/2/3 clusters (lvl 1-12 / 13-25 / 26+) * 3 heads * ~1.25 bolts/sec/head
        # Hydra bolt scales via HydraMissile clc3 piecewise curve on Hydra's effective slvl (passed via sumsk2calc=lvl)!
        clusters = 1 + (1 if slvl > 12 else 0) + (1 if slvl > 25 else 0)
        b = slvl
        base_scale = (
            100
            + 12 * max(0, b - 1)
            + 12 * max(0, b - 8)
            + 45 * max(0, b - 16)
            + 108 * max(0, b - 22)
            + 147 * max(0, b - 28)
        ) / 100.0
        # Hydra missile base EMin=32, EMax=44
        bolt_avg = 38.0 * base_scale * syn_mult * elem_mult
        shots_per_sec = clusters * 3.0 * 1.25
        # In Conflagration: 6 scaled pyre_hydra_blast sub-bolts (~42% dmg each) add ~40% ST and ~2.2x pack coverage
        st_dps = bolt_avg * shots_per_sec * (1.40 if in_stance else 1.0)
        pack_dps = bolt_avg * shots_per_sec * (pack_s if in_stance else pack_n)
    else:
        return None

    return {
        "slug": slug,
        "role": role,
        "slvl": float(slvl),
        "blvl": float(main_blvl),
        "sym_pct": float(sym_pct),
        "st_dps": st_dps,
        "pack_dps": pack_dps,
        "mana_s": mana_per_sec,
    }


def eval_lightning_skill(
    world: ModWorldData,
    slug: str,
    cp: Checkpoint,
    gear_skills: int,
    fcr: int,
    in_stance: bool,
    unlock_only: bool = False,
) -> Optional[Dict[str, float]]:
    """Return single-target & pack effective DPS for Sorceress Lightning skills (pre-res raw DPS)."""
    # (vname, reqlevel, syn_specs=[(vname, reqlevel, pct_per_lvl), ...], role, pack_n, pack_s)
    # Read live Param8 from skills.txt so tuning synergies immediately reflects in the simulator.
    def _p8(vn: str) -> int:
        return _int(world.skills[vn].get("Param8", "6"), 6)

    SPEC = {
        "static_lance":  ("Lightning",       1,  [("Chain Lightning", 24, _p8("Lightning")), ("Charged Bolt", 40, _p8("Lightning"))], "Line 1", 1.5, 3.2),
        "pulse_ring":    ("Nova",            8,  [("Thunder Storm", 24, _p8("Nova")), ("Static Field", 16, 6)], "AoE 1", 4.0, 5.5),
        "sunderbolt":    ("Static Field",    16, [("Nova", 8, _p8("Static Field")), ("Thunder Storm", 24, _p8("Static Field"))], "Util", 4.0, 5.5),
        "spearbolt":     ("Chain Lightning", 24, [("Charged Bolt", 40, _p8("Chain Lightning")), ("Lightning", 1, _p8("Chain Lightning"))], "Line 2", 3.5, 5.5),
        "stormcall":     ("Thunder Storm",   24, [("Nova", 8, _p8("Thunder Storm")), ("Static Field", 16, 6)], "AoE 2", 4.5, 6.5),
        "heavens_wrath": ("Charged Bolt",    40, [("Chain Lightning", 24, _p8("Charged Bolt")), ("Lightning", 1, _p8("Charged Bolt"))], "Cap", 4.5, 7.0),
    }
    vname, req_lvl, syns, role, pack_n, pack_s = SPEC[slug]
    if cp.clvl < req_lvl:
        return None

    # Overcharge (Lightning Stance) unlocks at reqlevel 32
    main_blvl, syn_blvls, stance_blvl = _alloc_skill_points(
        cp.clvl, cp.quest_pts, req_lvl, [s[1] for s in syns], stance_req=32, unlock_only=unlock_only
    )
    slvl = main_blvl + gear_skills
    stance_slvl = (stance_blvl + gear_skills) if (in_stance and stance_blvl > 0) else 0

    srow = world.skills[vname]
    sym_pct = sum(blvl * pct for blvl, (_, _, pct) in zip(syn_blvls, syns))
    elem_mult = 1.0 + (stance_elem_bonus(stance_slvl) / 100.0 if in_stance else 0.0)
    syn_mult = 1.0 + sym_pct / 100.0

    # Overcharge grants FRW/FHR/FBR (no FCR bonus)
    cast_sec = sorc_cast_frames(fcr) / 25.0
    cd_frames = _int(srow.get("localdelay", "0"))
    cycle_sec = max(cast_sec, cd_frames / 25.0) if cd_frames > 0 else cast_sec
    mana_cost = eval_mana_cost(srow, slvl)
    mana_per_sec = mana_cost / cycle_sec

    lo, hi = eval_edmg_base(srow, slvl, is_missile=False)
    avg_hit = 0.5 * (lo + hi) * syn_mult * elem_mult

    if slug == "static_lance":
        # Overcharge fires 4 bolts (NextDelay=6 limits ST to ~1.2x, packs take ~3.2x)
        st_mult = 1.20 if in_stance else 1.0
        st_dps = (avg_hit * st_mult) / cast_sec
        pack_dps = (avg_hit / cast_sec) * (pack_s if in_stance else pack_n)

    elif slug == "pulse_ring":
        st_dps = avg_hit / cast_sec
        pack_dps = st_dps * (pack_s if in_stance else pack_n)

    elif slug == "sunderbolt":
        # 2.0s CD AoE shock/blind + %HP static pulse; model base skill hit per CD cycle
        st_dps = avg_hit / cycle_sec
        pack_dps = st_dps * (pack_s if in_stance else pack_n)

    elif slug == "spearbolt":
        # Piercing lance + spearbolt_wake (NextDelay=6) + chain jumps
        wrow = world.missiles["spearbolt_wake"]
        wlo, whi = eval_edmg_base(wrow, slvl, is_missile=True)
        wake_avg = 0.5 * (wlo + whi) * syn_mult * elem_mult
        # Neutral wake 15f (~0.8 hits/cast); Overcharge wake 50f (~2.2 overlapping hits/cast)
        st_hit = avg_hit + wake_avg * (2.2 if in_stance else 0.8)
        st_dps = st_hit / cast_sec
        pack_dps = (avg_hit / cast_sec) * (pack_s if in_stance else pack_n) + (wake_avg / cast_sec) * (3.5 if in_stance else 1.2)

    elif slug == "stormcall":
        # 1.6s CD storm: 7 bolts/3s neutral (~2.0 ST hits/cast), 16 bolts/4s Overcharge (~4.2 ST hits/cast)
        st_hits = 4.2 if in_stance else 2.0
        st_dps = (avg_hit * st_hits) / cycle_sec
        pack_dps = (avg_hit * (st_hits * 0.7)) / cycle_sec * (pack_s if in_stance else pack_n)

    elif slug == "heavens_wrath":
        # Periodic sky-strike buff (perdelay: max(10, 22 - lvl*0.5) Overcharge / max(14, 30 - lvl*0.7) Neutral)
        # Each strike fires bolt + chain bounces (~1.35 ST hits neutral / ~1.85 Overcharge)
        per_f = max(10.0, 22.0 - slvl * 0.5) if in_stance else max(14.0, 30.0 - slvl * 0.7)
        strikes_per_sec = 25.0 / per_f
        st_hits = 1.85 if in_stance else 1.35
        st_dps = avg_hit * st_hits * strikes_per_sec
        pack_dps = avg_hit * strikes_per_sec * (pack_s if in_stance else pack_n)
        mana_per_sec = mana_cost / 60.0  # long-duration buff, cast once per ~1-3 min
    else:
        return None

    return {
        "slug": slug,
        "role": role,
        "slvl": float(slvl),
        "blvl": float(main_blvl),
        "sym_pct": float(sym_pct),
        "lo_hit": lo * syn_mult * elem_mult,
        "hi_hit": hi * syn_mult * elem_mult,
        "st_dps": st_dps,
        "pack_dps": pack_dps,
        "mana_s": mana_per_sec,
    }


def eval_vanilla_fireball(vanilla: ModWorldData, cp: Checkpoint, gear_skills: int, fcr: int) -> Dict[str, float]:
    """Vanilla D2R Fireball (lvl 12+) / Fire Bolt (lvl 1-11) benchmark on the exact same checkpoints."""
    cast_sec = sorc_cast_frames(fcr) / 25.0
    if cp.clvl < 12:
        blvl = min(20, cp.clvl)
        slvl = blvl + gear_skills
        srow = vanilla.skills["Fire Bolt"]
        lo, hi = eval_edmg_base(srow, slvl)
        st = 0.5 * (lo + hi) / cast_sec
        return {"st_dps": st, "pack_dps": st}
    # Fire Ball (req 12) + Fire Bolt (req 1, 14%/lvl) + Fire Mastery (req 30, 30%+7%/lvl)
    budget = max(1, cp.clvl - 1 + cp.quest_pts - 2)
    fb_b = min(20, cp.clvl - 12 + 1, budget)
    budget -= fb_b
    fm_b = 1 if (cp.clvl >= 30 and budget > 0) else 0
    budget -= fm_b
    syn_b = min(20, budget)
    budget -= syn_b
    if cp.clvl >= 30 and budget > 0:
        add = min(budget, 20 - fm_b)
        fm_b += add

    fb_s = fb_b + gear_skills
    fm_s = (fm_b + gear_skills) if fm_b > 0 else 0
    fm_mult = 1.0 + ((30.0 + (fm_s - 1) * 7.0) / 100.0 if fm_s > 0 else 0.0)
    syn_mult = 1.0 + (syn_b * 14.0) / 100.0
    lo, hi = eval_edmg_base(vanilla.skills["Fire Ball"], fb_s)
    st = 0.5 * (lo + hi) * syn_mult * fm_mult / cast_sec
    return {"st_dps": st, "pack_dps": st * 3.5}


def run_sorc_fire_report(preset: str = "competent") -> None:
    world = ModWorldData(EXCEL_DIR)
    vanilla = ModWorldData(VANILLA_EXCEL)
    sk_mult, fcr_off = GEAR_PRESETS[preset]

    print(f"====================================================================================================")
    print(f"  CASTALIA BALANCE AUDIT — SORCERESS FIRE TREE  (Gear Preset: {preset})")
    print(f"====================================================================================================\n")

    # 1. Area eHP Progression
    print("1. AREA PROGRESSION & MONSTER eHP CURVE (Mod 10% / 20% / 30% Baseline Res)")
    print(f"  {'Checkpoint':10s} | {'Area':22s} | {'alvl':>4s} | {'TrashHP':>7s} | {'Trash eHP':>9s} | {'Boss eHP':>9s} | {'Area eHP':>10s} | {'VanFB TTK':>9s}")
    print("  " + "-" * 96)
    cp_metrics = {}
    van_refs = {}
    for cp in CHECKPOINTS:
        m = world.area_metrics(cp)
        cp_metrics[cp.label] = m
        gsk = int(round(cp.gear_skills * sk_mult))
        fcr = max(0, cp.fcr + fcr_off)
        vref = eval_vanilla_fireball(vanilla, cp, gsk, fcr)
        van_refs[cp.label] = vref
        v_ttk = m["trash_ehp"] / max(1.0, vref["st_dps"])
        print(
            f"  {cp.label:10s} | {cp.level_name:22s} | {int(m['alvl']):4d} | "
            f"{m['trash_hp']:7.0f} | {m['trash_ehp']:9.0f} | {m['boss_ehp']:9.0f} | "
            f"{m['area_ehp']:10.0f} | {v_ttk:8.2f}s"
        )

    # 2. Unlock Viability Check (clvl == reqlevel, 1 hard pt in new skill)
    print("\n2. UNLOCK VIABILITY CHECK (At exact reqlevel, 1 hard pt + expected gear, In-Stance if >=16)")
    cp_by_clvl = {cp.clvl: cp for cp in CHECKPOINTS}
    unlock_checks = [
        ("cinder_lance",    cp_by_clvl[1]),
        ("pyroclasm",       cp_by_clvl[8]),
        ("backdraft",       cp_by_clvl[8]),
        ("skyfall",         cp_by_clvl[24]),
        ("brimstone_lance", cp_by_clvl[32]),
        ("pyre_hydra",      cp_by_clvl[40]),
    ]
    print(f"  {'Skill':16s} | {'Unlock':10s} | {'slvl':>4s} | {'ST DPS':>8s} | {'Pack DPS':>8s} | {'Trash TTK':>9s} | {'Area Sec':>8s} | {'vs VanFB':>8s}")
    print("  " + "-" * 88)
    for slug, cp in unlock_checks:
        gsk = int(round(cp.gear_skills * sk_mult))
        fcr = max(0, cp.fcr + fcr_off)
        res = eval_fire_skill(world, slug, cp, gsk, fcr, in_stance=(cp.clvl >= 16), unlock_only=True)
        m = cp_metrics[cp.label]
        v = van_refs[cp.label]
        ttk = m["trash_ehp"] / max(1.0, res["st_dps"])
        area_s = m["area_ehp"] / max(1.0, res["pack_dps"])
        ratio = res["pack_dps"] / max(1.0, v["pack_dps"])
        flag = "  <-- LOW!" if ttk > 3.5 else ""
        print(
            f"  {slug:16s} | {cp.label:10s} | {int(res['slvl']):4d} | "
            f"{res['st_dps']:8.1f} | {res['pack_dps']:8.1f} | {ttk:8.2f}s | {area_s:7.1f}s | {ratio:7.2f}x{flag}"
        )

    # 3. Full Progression Matrix (In-Stance when >=16, plus Neutral comparison in Hell)
    skills_order = ["cinder_lance", "pyroclasm", "backdraft", "skyfall", "brimstone_lance", "pyre_hydra"]
    print("\n3. FULL PROGRESSION — TRASH TTK (sec) / AREA COMBAT TIME (sec)  [In-Stance >= lvl 16]")
    hdr = f"  {'Checkpoint':10s} |" + "".join(f" {s[:10]:>12s} |" for s in skills_order) + f" {'VanFB':>10s}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    red_flags: List[str] = []
    for cp in CHECKPOINTS:
        gsk = int(round(cp.gear_skills * sk_mult))
        fcr = max(0, cp.fcr + fcr_off)
        m = cp_metrics[cp.label]
        v = van_refs[cp.label]
        row_cells = []
        results_by_slug = {}
        for slug in skills_order:
            r = eval_fire_skill(world, slug, cp, gsk, fcr, in_stance=(cp.clvl >= 16))
            if r is None:
                row_cells.append(f"{'---':>12s}")
            else:
                results_by_slug[slug] = r
                ttk = m["trash_ehp"] / max(1.0, r["st_dps"])
                area_s = m["area_ehp"] / max(1.0, r["pack_dps"])
                row_cells.append(f"{ttk:4.2f}s/{area_s:4.0f}s")
        v_ttk = m["trash_ehp"] / max(1.0, v["st_dps"])
        v_area = m["area_ehp"] / max(1.0, v["pack_dps"])
        print(f"  {cp.label:10s} | " + " | ".join(row_cells) + f" | {v_ttk:4.2f}s/{v_area:3.0f}s")

        # Role differentiation check at lvl 40+
        if cp.clvl >= 40 and "brimstone_lance" in results_by_slug and "skyfall" in results_by_slug:
            if results_by_slug["brimstone_lance"]["st_dps"] < results_by_slug["pyroclasm"]["st_dps"]:
                red_flags.append(f"[{cp.label}] Role inversion: Pyroclasm ST DPS ({results_by_slug['pyroclasm']['st_dps']:.0f}) > Brimstone Lance ST DPS ({results_by_slug['brimstone_lance']['st_dps']:.0f})")
            if results_by_slug["skyfall"]["pack_dps"] < results_by_slug["cinder_lance"]["pack_dps"]:
                red_flags.append(f"[{cp.label}] Role inversion: Cinder Lance Pack DPS > Skyfall Pack DPS")

    # 4. Hell A5 Endgame Snapshot (Neutral vs Conflagration + Boss TTK + Mana/sec)
    print("\n4. HELL A5 ENDGAME SNAPSHOT (clvl 82, mlvl 85, 30% Fire Res — Boss eHP =", f"{cp_metrics['H-A5  L82']['boss_ehp']:.0f})")
    cp_end = CHECKPOINTS[-1]
    gsk = int(round(cp_end.gear_skills * sk_mult))
    fcr = max(0, cp_end.fcr + fcr_off)
    m_end = cp_metrics[cp_end.label]
    print(f"  {'Skill':16s} | {'Role':6s} | {'Neut ST':>8s} | {'Stnc ST':>8s} | {'BossTTK':>7s} | {'PackTTK':>7s} | {'Mana/s':>6s} | {'vs VanFB':>8s}")
    print("  " + "-" * 86)
    v_end = van_refs[cp_end.label]
    for slug in skills_order:
        rn = eval_fire_skill(world, slug, cp_end, gsk, fcr, in_stance=False)
        rs = eval_fire_skill(world, slug, cp_end, gsk, fcr, in_stance=True)
        boss_ttk = m_end["boss_ehp"] / max(1.0, rs["st_dps"])
        area_s = m_end["area_ehp"] / max(1.0, rs["pack_dps"])
        ratio = rs["st_dps"] / max(1.0, v_end["st_dps"])
        print(
            f"  {slug:16s} | {rs['role']:6s} | {rn['st_dps']:8.0f} | {rs['st_dps']:8.0f} | "
            f"{boss_ttk:6.2f}s | {area_s:6.1f}s | {rs['mana_s']:6.1f} | {ratio:7.2f}x"
        )
    print(f"  {'[Vanilla FireBall]':16s} | {'Ref':6s} | {v_end['st_dps']:8.0f} | {v_end['st_dps']:8.0f} | {m_end['boss_ehp']/v_end['st_dps']:6.2f}s | {m_end['area_ehp']/v_end['pack_dps']:6.1f}s | {'--':>6s} |   1.00x")

    print("\n5. AUTOMATED RED FLAGS")
    if not red_flags:
        print("  None — all role differentiation checks passed!")
    else:
        for rf in red_flags:
            print("  !", rf)


def run_sorc_lightning_report(preset: str = "competent") -> None:
    world = ModWorldData(EXCEL_DIR)
    vanilla = ModWorldData(VANILLA_EXCEL)
    sk_mult, fcr_off = GEAR_PRESETS[preset]

    print("====================================================================================================")
    print(f"  CASTALIA BALANCE AUDIT — SORCERESS LIGHTNING TREE  (Gear Preset: {preset})")
    print("====================================================================================================\n")

    cp_metrics = {}
    van_refs = {}
    fire_refs = {}
    for cp in CHECKPOINTS:
        cp_metrics[cp.label] = world.area_metrics(cp)
        gsk = int(round(cp.gear_skills * sk_mult))
        fcr = max(0, cp.fcr + fcr_off)
        van_refs[cp.label] = eval_vanilla_fireball(vanilla, cp, gsk, fcr)
        # Fire benchmark at same checkpoint: best primary spam/line skill (Cinder <8, Pyroclasm 8-31, Brimstone 32+)
        f_slug = "cinder_lance" if cp.clvl < 8 else ("pyroclasm" if cp.clvl < 32 else "brimstone_lance")
        fire_refs[cp.label] = eval_fire_skill(world, f_slug, cp, gsk, fcr, in_stance=(cp.clvl >= 16))

    # 1. Unlock Viability Check
    print("1. UNLOCK VIABILITY CHECK (At exact reqlevel, 1 hard pt + expected gear, Overcharge if >=32)")
    cp_by_clvl = {cp.clvl: cp for cp in CHECKPOINTS}
    unlock_checks = [
        ("static_lance",  cp_by_clvl[1]),
        ("pulse_ring",    cp_by_clvl[8]),
        ("sunderbolt",    cp_by_clvl[16]),
        ("spearbolt",     cp_by_clvl[24]),
        ("stormcall",     cp_by_clvl[24]),
        ("heavens_wrath", cp_by_clvl[40]),
    ]
    print(f"  {'Skill':16s} | {'Unlock':10s} | {'slvl':>4s} | {'ST DPS':>8s} | {'Pack DPS':>8s} | {'Trash TTK':>9s} | {'Area Sec':>8s} | {'vs Fire':>8s}")
    print("  " + "-" * 88)
    for slug, cp in unlock_checks:
        gsk = int(round(cp.gear_skills * sk_mult))
        fcr = max(0, cp.fcr + fcr_off)
        res = eval_lightning_skill(world, slug, cp, gsk, fcr, in_stance=(cp.clvl >= 32), unlock_only=True)
        m = cp_metrics[cp.label]
        fref = fire_refs[cp.label]
        ttk = m["trash_ehp"] / max(1.0, res["st_dps"])
        area_s = m["area_ehp"] / max(1.0, res["pack_dps"])
        ratio = res["st_dps"] / max(1.0, fref["st_dps"])
        flag = "  <-- LOW!" if ttk > 3.5 else ""
        print(
            f"  {slug:16s} | {cp.label:10s} | {int(res['slvl']):4d} | "
            f"{res['st_dps']:8.1f} | {res['pack_dps']:8.1f} | {ttk:8.2f}s | {area_s:7.1f}s | {ratio:7.2f}x{flag}"
        )

    # 2. Full Progression Matrix
    skills_order = ["static_lance", "pulse_ring", "sunderbolt", "spearbolt", "stormcall", "heavens_wrath"]
    print("\n2. FULL PROGRESSION — TRASH TTK (sec) / AREA COMBAT TIME (sec)  [Overcharge >= lvl 32]")
    hdr = f"  {'Checkpoint':10s} |" + "".join(f" {s[:10]:>12s} |" for s in skills_order) + f" {'FireRef':>10s}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for cp in CHECKPOINTS:
        gsk = int(round(cp.gear_skills * sk_mult))
        fcr = max(0, cp.fcr + fcr_off)
        m = cp_metrics[cp.label]
        fref = fire_refs[cp.label]
        row_cells = []
        for slug in skills_order:
            r = eval_lightning_skill(world, slug, cp, gsk, fcr, in_stance=(cp.clvl >= 32))
            if r is None:
                row_cells.append(f"{'---':>12s}")
            else:
                ttk = m["trash_ehp"] / max(1.0, r["st_dps"])
                area_s = m["area_ehp"] / max(1.0, r["pack_dps"])
                row_cells.append(f"{ttk:4.2f}s/{area_s:4.0f}s")
        f_ttk = m["trash_ehp"] / max(1.0, fref["st_dps"])
        f_area = m["area_ehp"] / max(1.0, fref["pack_dps"])
        print(f"  {cp.label:10s} | " + " | ".join(row_cells) + f" | {f_ttk:4.2f}s/{f_area:3.0f}s")

    # 3. Hell A5 Endgame Snapshot vs Fire Tree (Target: Lightning ~1.10x Fire on average)
    cp_end = CHECKPOINTS[-1]
    gsk = int(round(cp_end.gear_skills * sk_mult))
    fcr = max(0, cp_end.fcr + fcr_off)
    m_end = cp_metrics[cp_end.label]
    print(f"\n3. HELL A5 ENDGAME SNAPSHOT (clvl 82, mlvl 85, 30% Res — Boss eHP = {m_end['boss_ehp']:.0f})")
    print(f"  {'Skill':16s} | {'Role':6s} | {'Neut ST':>8s} | {'Stnc ST':>8s} | {'Pack DPS':>9s} | {'BossTTK':>7s} | {'Mana/s':>6s} | {'vs FireEq':>9s}")
    print("  " + "-" * 94)

    fire_equiv = {
        "static_lance":  "cinder_lance",
        "pulse_ring":    "pyroclasm",
        "sunderbolt":    "backdraft",
        "spearbolt":     "brimstone_lance",
        "stormcall":     "skyfall",
        "heavens_wrath": "pyre_hydra",
    }
    ratios = []
    for slug in skills_order:
        rn = eval_lightning_skill(world, slug, cp_end, gsk, fcr, in_stance=False)
        rs = eval_lightning_skill(world, slug, cp_end, gsk, fcr, in_stance=True)
        fe = eval_fire_skill(world, fire_equiv[slug], cp_end, gsk, fcr, in_stance=True)
        boss_ttk = m_end["boss_ehp"] / max(1.0, rs["st_dps"])
        ratio = rs["st_dps"] / max(1.0, fe["st_dps"])
        ratios.append(ratio)
        print(
            f"  {slug:16s} | {rs['role']:6s} | {rn['st_dps']:8.0f} | {rs['st_dps']:8.0f} | "
            f"{rs['pack_dps']:9.0f} | {boss_ttk:6.2f}s | {rs['mana_s']:6.1f} | {ratio:8.2f}x"
        )
    print("  " + "-" * 94)
    print(f"  Average Lightning ST DPS vs Fire Role-Equivalent: {sum(ratios)/len(ratios):.2f}x  (Target: ~1.10x)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Castalia Data-Driven Balance Simulator")
    parser.add_argument("char_class", choices=["sorc"], help="Class to audit")
    parser.add_argument("tree", choices=["fire", "lightning"], help="Skill tree to audit")
    parser.add_argument("--preset", choices=list(GEAR_PRESETS), default="competent", help="Expected gear preset")
    args = parser.parse_args()
    if args.char_class == "sorc" and args.tree == "fire":
        run_sorc_fire_report(preset=args.preset)
    elif args.char_class == "sorc" and args.tree == "lightning":
        run_sorc_lightning_report(preset=args.preset)


if __name__ == "__main__":
    main()

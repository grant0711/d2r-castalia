"""
skill_order.py
Final skill-ID permutation that makes every reworked class's skill tiers contiguous ID ranges again.

WHY
---
In vanilla, each class's 30 skill IDs are ordered by tier (5 skills per reqlevel tier), so every
"unlocked tiers 1..k" pool is ONE contiguous [lo, hi] range and one automagic.txt `skill-rand` row covers it.
The Sorceress, Barbarian and Assassin overhauls moved skills between tiers WITHOUT moving their IDs, which
scattered each tier across the ID range. automagic.txt then needed one row per sub-range per combo and grew to
2,676 rows -- past the 11-bit (max 2047) automagic ID stored per item in .d2s saves, so items whose auto-affix
row index was >= 2048 (shields, helms, claws, pelts) were silently deleted on Save & Exit.

HOW
---
Every class builder (classes/*, sorc/*) keeps authoring against the ORIGINAL ("source") vanilla row layout:
row names, *Id values and numeric skill params all mean what they always meant. This module is applied at the
very last moment, on write:

  * skills.txt               -> the 30 rows of each permuted class are physically re-ordered so tier k occupies
                                the k-th contiguous block, and *Id is rewritten. Row NAMES travel with their
                                content, so every name-based reference (missiles, monstats, hireling, charstats,
                                reqskill, skill('X'.blvl) formulas, uniques/runes by name) stays correct for free.
  * every other excel table  -> numeric skill params of skill-type properties (skill, oskill, charged, aura,
                                hit-skill, gethit-skill, ...) are remapped old -> new.
  * HD state machines        -> `skillIndex` bindings (player classes, mercs, monsters) are remapped old -> new.

Within a tier's block, a skill whose source ID already lies inside that block keeps its ID (minimal moves).
automagic.txt `skill-rand` ranges are generated directly in the FINAL ID space (see final_tier_ranges()).

IDEMPOTENCY: builders always read pristine vanilla inputs (old ID space) and write the mod (new ID space), so the
write hook runs exactly once per generated table. Tables copied verbatim from tools/mod_builder/locked_tables/
are stored in the NEW ID space already.
"""
import glob
import json
import os
from functools import lru_cache
from typing import Dict, List, Tuple

TIER_LEVELS = [1, 8, 16, 24, 32, 40]

# First vanilla *Id of each permuted class's 30-skill block.
PERMUTED_CLASSES: Dict[str, int] = {"sor": 36, "bar": 126, "ass": 251}
# Sorceress is ordered by (Tree, Tier) -> 36..45 Fire, 46..55 Lightning, 56..65 Cold
# so staff/orb automagic can emit element-matched & same-tree skill-rand ranges in 1 interval per tier!
SORC_TREE_ORDER: Tuple[str, ...] = ("fire", "lightning", "cold")

# Source (pre-permutation) vanilla IDs per tier for the hand-authored overhauls.
# The Sorceress tiers come from the 1:1 slot map (sorc/registry.py).
_SOURCE_TIERS_STATIC: Dict[str, List[List[int]]] = {
    "bar": [
        [126, 127, 128, 133, 135, 138, 142],  # Tier 1 (reqlevel  1)
        [132, 134, 137, 141],                 # Tier 2 (reqlevel  8)
        [130, 131, 140, 144, 145, 148],       # Tier 3 (reqlevel 16)
        [136, 143, 146, 155],                 # Tier 4 (reqlevel 24)
        [129, 139, 149, 150, 152],            # Tier 5 (reqlevel 32)
        [147, 151, 153, 154],                 # Tier 6 (reqlevel 40)
    ],
    "ass": [
        [252, 254, 255, 256, 257],            # Tier 1 (reqlevel  1)
        [251, 259, 263, 264],                 # Tier 2 (reqlevel  8)
        [258, 260, 262, 266, 268, 274],       # Tier 3 (reqlevel 16)
        [269, 270, 273, 276],                 # Tier 4 (reqlevel 24)
        [265, 267, 271, 275, 277, 278],       # Tier 5 (reqlevel 32)
        [253, 261, 272, 279, 280],            # Tier 6 (reqlevel 40)
    ],
}

# itemstatcost stats whose property param is a skill id (or skill name).
_SKILL_PARAM_STATS = {
    "item_singleskill", "item_nonclassskill", "item_aura", "item_charged_skill",
    "item_skillonattack", "item_skillonhit", "item_skillongethit", "item_skillonkill",
    "item_skillondeath", "item_skillonlevelup", "item_skillonstrike",
}

STATE_MACHINE_GLOB = "data/hd/character/**/*state_machine*.json"


def source_tiers() -> Dict[str, List[List[int]]]:
    from mod_builder.sorc.registry import SLOTS as _SORC_SLOTS

    tiers = {"sor": [sorted(s["vid"] for s in _SORC_SLOTS if s["row"] == k) for k in range(1, 7)]}
    tiers.update({k: [list(t) for t in v] for k, v in _SOURCE_TIERS_STATIC.items()})
    for cls, base in PERMUTED_CLASSES.items():
        flat = sorted(i for t in tiers[cls] for i in t)
        if flat != list(range(base, base + 30)):
            raise RuntimeError(f"skill_order: {cls} source tiers must cover ids {base}..{base + 29} exactly once")
    return tiers


@lru_cache(maxsize=None)
def _compute() -> Tuple[Dict[int, int], Dict[str, Tuple[Tuple[int, int], ...]], Dict[str, Tuple[Tuple[int, int], ...]]]:
    from mod_builder.sorc.registry import SLOTS as _SORC_SLOTS

    perm: Dict[int, int] = {}
    ranges: Dict[str, Tuple[Tuple[int, int], ...]] = {}
    sorc_tree_tiers: Dict[str, Tuple[Tuple[int, int], ...]] = {}

    # Sorceress: contiguous (Tree, Tier) blocks: Fire 36..45, Lightning 46..55, Cold 56..65
    pos = PERMUTED_CLASSES["sor"]
    for tree in SORC_TREE_ORDER:
        t_ranges = []
        for k in range(1, 7):
            members = sorted(s["vid"] for s in _SORC_SLOTS if s["tree"] == tree and s["row"] == k)
            if not members:
                t_ranges.append((-1, -1))
                continue
            block = list(range(pos, pos + len(members)))
            pos += len(members)
            t_ranges.append((block[0], block[-1]))
            stay = [i for i in members if i in block]
            movers = sorted(i for i in members if i not in block)
            free = [p for p in block if p not in stay]
            for i in stay:
                perm[i] = i
            for i, p in zip(movers, free):
                perm[i] = p
        sorc_tree_tiers[tree] = tuple(t_ranges)
    # Keep ranges["sor"] populated with the 3 tree blocks for any generic caller
    ranges["sor"] = tuple((36 + idx * 10, 45 + idx * 10) for idx in range(3))

    for cls, tiers in source_tiers().items():
        if cls == "sor":
            continue
        pos = PERMUTED_CLASSES[cls]
        cls_ranges = []
        for members in tiers:
            block = list(range(pos, pos + len(members)))
            pos += len(members)
            cls_ranges.append((block[0], block[-1]))
            stay = [i for i in members if i in block]
            movers = sorted(i for i in members if i not in block)
            free = [p for p in block if p not in stay]
            for i in stay:
                perm[i] = i
            for i, p in zip(movers, free):
                perm[i] = p
        ranges[cls] = tuple(cls_ranges)
    assert sorted(perm) == sorted(perm.values()), "skill_order: permutation is not a bijection"
    return perm, ranges, sorc_tree_tiers


def permutation() -> Dict[int, int]:
    """old (source) skill id -> new (final) skill id, for every permuted class skill."""
    return dict(_compute()[0])


def remap_id(skill_id: int) -> int:
    return _compute()[0].get(skill_id, skill_id)


def final_tier_ranges(cls: str) -> List[Tuple[int, int]]:
    """Final contiguous (lo, hi) id range of each tier 1..6 for a permuted class."""
    return list(_compute()[1][cls])


def final_sorc_tree_tier_ranges() -> Dict[str, List[Tuple[int, int]]]:
    """Final contiguous (lo, hi) id range per tier (1..6, or (-1,-1) if empty) for each Sorceress tree."""
    return {tree: list(trs) for tree, trs in _compute()[2].items()}


def final_tier_ids(cls: str) -> List[List[int]]:
    return [list(range(lo, hi + 1)) for lo, hi in final_tier_ranges(cls)]


# --------------------------------------------------------------------------------------------- excel tables


@lru_cache(maxsize=None)
def _skill_param_props() -> frozenset:
    from mod_builder.common import read_excel_tsv

    _, rows = read_excel_tsv("properties.txt")
    out = set()
    for r in rows:
        if any(r.get(f"stat{n}", "") in _SKILL_PARAM_STATS for n in range(1, 8)):
            out.add(r["code"])
    return frozenset(out)


def _code_param_pairs(headers: List[str]) -> List[Tuple[str, str]]:
    hs = set(headers)
    pairs = []
    for h in headers:
        for cand in (h.replace("prop", "par"), h.replace("Code", "Param"), h.replace("code", "param"),
                     h + " param" if h.startswith("mod ") else h):
            if cand != h and cand in hs:
                pairs.append((h, cand))
                break
    return pairs


def _permute_skills_rows(headers: List[str], rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    perm = permutation()
    tiers = source_tiers()
    out = list(rows)
    for cls, base in PERMUTED_CLASSES.items():
        tier_of = {i: k for k, members in enumerate(tiers[cls]) for i in members}
        for i in range(base, base + 30):
            r = rows[i]
            if r.get("*Id") != str(i) or r.get("charclass") != cls:
                raise RuntimeError(f"skill_order: skills.txt row {i} is {r.get('skill')!r} "
                                   f"(*Id={r.get('*Id')}, class={r.get('charclass')}); expected {cls} id {i}")
            want = str(TIER_LEVELS[tier_of[i]])
            if r.get("reqlevel") != want:
                raise RuntimeError(
                    f"skill_order: {r['skill']!r} (id {i}) has reqlevel {r.get('reqlevel')} but is declared in "
                    f"tier {tier_of[i] + 1} (reqlevel {want}). Update skill_order source tiers "
                    f"(or sorc/registry.py) so tiers and reqlevels agree.")
        for i in range(base, base + 30):
            moved = dict(rows[i])
            moved["*Id"] = str(perm[i])
            out[perm[i]] = moved
    return out


def remap_table_rows(filename: str, headers: List[str], rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Write hook: convert a freshly built table from source ids to final ids."""
    if filename == "skills.txt":
        return _permute_skills_rows(headers, rows)
    pairs = _code_param_pairs(headers)
    if not pairs:
        return rows
    props = _skill_param_props()
    perm = permutation()
    out = []
    for r in rows:
        r = dict(r)
        for code_col, par_col in pairs:
            if r.get(code_col) in props:
                v = r.get(par_col, "").strip()
                if v.isdigit() and int(v) in perm:
                    r[par_col] = str(perm[int(v)])
        out.append(r)
    return out


def remap_raw_rows(filename: str, headers: List[str], rows: List[List[str]]) -> List[List[str]]:
    if len(set(headers)) != len(headers):
        if filename == "skills.txt" or _code_param_pairs(headers):
            raise RuntimeError(f"skill_order: cannot remap {filename}: duplicate headers")
        return rows
    dict_rows = [dict(zip(headers, (str(c) for c in r))) for r in rows]
    dict_rows = remap_table_rows(filename, headers, dict_rows)
    return [[d.get(h, "") for h in headers] for d in dict_rows]


# ------------------------------------------------------------------------------------- HD state machines


def remap_state_machine(sm: dict) -> int:
    perm = permutation()
    n = 0
    for st in sm.get("states", []):
        si = st.get("skillIndex")
        if isinstance(si, int) and si in perm and perm[si] != si:
            st["skillIndex"] = perm[si]
            n += 1
    return n


def remap_state_machines(run_started_at: float) -> List[str]:
    """
    Remap skillIndex in every HD state machine that references a permuted skill.

    * Mod state machines written by a builder during this run (mtime >= run_started_at) were generated from
      vanilla in the source id space -> remapped in place.
    * Mod state machines NOT rewritten this run are left alone if no vanilla counterpart exists (mod-only) or
      were produced by an earlier run of this function from vanilla -> regenerated from vanilla (idempotent).
    * Vanilla state machines with no mod copy that reference a moved skill -> copied from vanilla and remapped.
    """
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    perm = permutation()
    moved = {k for k, v in perm.items() if k != v}
    written = []
    rels = set()
    for root in (VANILLA_ROOT, MOD_ROOT):
        for p in glob.glob(os.path.join(root, STATE_MACHINE_GLOB), recursive=True):
            rels.add(os.path.normpath(os.path.relpath(p, root)))
    for rel in sorted(rels):
        mod_path = os.path.join(MOD_ROOT, rel)
        van_path = os.path.join(VANILLA_ROOT, rel)
        fresh = os.path.exists(mod_path) and os.path.getmtime(mod_path) >= run_started_at
        if fresh:
            src = mod_path
        elif os.path.exists(van_path):
            src = van_path
        else:
            continue  # mod-only file not regenerated this run: leave untouched
        with open(src, "r", encoding="utf-8-sig") as f:
            sm = json.load(f)
        if not any(st.get("skillIndex") in moved for st in sm.get("states", [])):
            continue
        remap_state_machine(sm)
        os.makedirs(os.path.dirname(mod_path), exist_ok=True)
        with open(mod_path, "w", encoding="utf-8") as f:
            json.dump(sm, f, indent=2)
            f.write("\n")
        written.append(mod_path)
    return written

"""
Sorceress experiment engine.

Layers (applied in this order, later wins):
  1. registry.py      -> layout, names, req level, tooltip text for all 30 skills (always applied)
  2. specs/<slug>.json -> the ACTIVE variant of each skill: patches to game tables
  3. specs/_shared.json -> shared helper rows (states, itemstatcost, helper skills) used by several skills
State (which variant is active, status) lives in state.json. Everything is plain JSON/py in git, so
reverting a skill is `git checkout` of one small file, and a new idea is just a new variant.

Variant JSON schema (all keys optional except description):
    {
      "description": "what this variant tests (change ONE variable per variant)",
      "tables": {
        "skills.txt":        {"<skill row name>": {"<column>": "<value>", ...}},
        "skilldesc.txt":     {"<skilldesc key>":  {...}},
        "missiles.txt":      {"<missile name>":   {...}},
        "states.txt":        {"<state name>":     {...}},
        "itemstatcost.txt":  {"<stat name>":      {...}}
      },
      "strings": {"name": "...", "short": "...", "long": "..."}
    }
A key that does not exist yet creates a NEW row and must give "_clone": "<existing key>" (columns
are copied, the key/*Id are set automatically). Unknown columns raise an error (no silent typos).
"""
import copy
import json
import os
import re
from typing import Dict, List, Tuple

from mod_builder.sorc.registry import (
    BY_SLUG, PAGE, SLOTS, check_registry, slot_level,
)

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC_DIR = os.path.join(HERE, "specs")
STATE_PATH = os.path.join(HERE, "state.json")

TABLE_KEYS = {
    "skills.txt": "skill",
    "skilldesc.txt": "skilldesc",
    "missiles.txt": "Missile",
    "states.txt": "state",
    "itemstatcost.txt": "Stat",
}
STATUSES = ("stub", "wip", "tested", "done")
STRING_ID_BASE = 63000  # 63000..63089 (3 per slot): verified unused in all vanilla string files


# ---------------------------------------------------------------------- state / specs
def load_state() -> Dict[str, dict]:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {}


def save_state(state: Dict[str, dict]) -> None:
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def spec_path(slug: str) -> str:
    return os.path.join(SPEC_DIR, f"{slug}.json")


def default_spec(slug: str) -> dict:
    return {"slug": slug, "variants": {"baseline": {
        "description": "new name/layout only; behaviour is still the vanilla row (stub)"}}}


def load_spec(slug: str) -> dict:
    p = spec_path(slug)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return default_spec(slug)


def save_spec(slug: str, spec: dict) -> None:
    os.makedirs(SPEC_DIR, exist_ok=True)
    with open(spec_path(slug), "w") as f:
        json.dump(spec, f, indent=2)
        f.write("\n")


def env_overrides() -> Dict[str, str]:
    out = {}
    for part in os.environ.get("SORC_VARIANTS", "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def active_variant(slug: str, state: Dict[str, dict] = None) -> str:
    state = load_state() if state is None else state
    env = env_overrides()
    if slug in env:
        return env[slug]
    return state.get(slug, {}).get("variant", "baseline")


def status_of(slug: str, state: Dict[str, dict] = None) -> str:
    state = load_state() if state is None else state
    return state.get(slug, {}).get("status", "stub")


def active_blocks() -> List[Tuple[str, str, dict]]:
    """(slug, variant_name, variant_dict) for every active variant, shared first."""
    state = load_state()
    blocks = []
    for slug in ["_shared"] + [s["slug"] for s in SLOTS]:
        spec = load_spec(slug) if slug != "_shared" else (
            load_spec("_shared") if os.path.exists(spec_path("_shared")) else {"variants": {"baseline": {}}})
        var = active_variant(slug, state)
        if var not in spec["variants"]:
            raise KeyError(f"{slug}: variant '{var}' not found (have {list(spec['variants'])})")
        blocks.append((slug, var, spec["variants"][var]))
    return blocks


# ---------------------------------------------------------------------- table patching
def _id_col(headers: List[str]) -> str:
    for h in headers:
        if re.fullmatch(r"\*?id", h, re.I):
            return h
    return ""


def apply_table_patches(table: str, headers: List[str], rows: List[Dict[str, str]]) -> int:
    """Apply every active variant's patches for `table` in place. Returns patched-row count."""
    key_col = TABLE_KEYS[table]
    by_key = {r[key_col]: r for r in rows if r.get(key_col)}
    id_col = _id_col(headers)
    count = 0
    deferred = []  # (row, col, template) for values using {id:<key>} placeholders
    for slug, var, block in active_blocks():
        for key, patch in block.get("tables", {}).get(table, {}).items():
            patch = dict(patch)
            clone = patch.pop("_clone", None)
            if key in by_key:
                row = by_key[key]
            else:
                if not clone or clone not in by_key:
                    raise KeyError(f"[{slug}:{var}] {table}: '{key}' is new and needs a valid '_clone'")
                row = dict(by_key[clone])
                row[key_col] = key
                if id_col:
                    nums = [int(r[id_col]) for r in rows if r.get(id_col, "").lstrip("-").isdigit()]
                    row[id_col] = str(max(nums) + 1)
                rows.append(row)
                by_key[key] = row
            for col, val in patch.items():
                if col not in headers:
                    raise KeyError(f"[{slug}:{var}] {table}/{key}: unknown column '{col}'")
                row[col] = str(val)
                if "{id:" in row[col]:
                    deferred.append((row, col, row[col]))
            count += 1
    for row, col, tmpl in deferred:  # resolve '{id:<row key>}' to that row's id (rows may be created later)
        def _sub(m):
            return by_key[m.group(1)][id_col]
        row[col] = re.sub(r"\{id:([^}]+)\}", _sub, tmpl)
    return count


# ---------------------------------------------------------------------- layout + strings
def _string_keys(slug: str) -> Tuple[str, str, str]:
    return (f"ModSorc_{slug}_name", f"ModSorc_{slug}_short", f"ModSorc_{slug}_long")


def slot_texts(slot: dict, variant: str, status: str, override: dict) -> Tuple[str, str, str]:
    name = override.get("name", slot["name"])
    if status == "stub":
        short = override.get("short", f"[stub] {slot['role']} - acts as vanilla {slot['vname']}")
        long = override.get("long", f"STUB: still behaves as vanilla {slot['vname']}.\n\n"
                                     f"Design intent ({slot['role']}):\n{slot['design']}")
    else:
        short = override.get("short", slot["role"])
        long = override.get("long", slot["design"])
    if variant != "baseline":
        long += f"\n\n[test variant: {variant}]"
    return name, short, long


def apply_layout(by_name: Dict[str, dict], by_desc: Dict[str, dict]) -> None:
    problems = check_registry()
    if problems:
        raise RuntimeError("sorc registry invalid: " + "; ".join(problems))
    for s in SLOTS:
        row = by_name.get(s["vname"])
        if row is None or row.get("*Id") != str(s["vid"]) or row.get("charclass") != "sor":
            raise RuntimeError(f"sorc map: row '{s['vname']}' is not Sorceress id {s['vid']}")
        row["reqlevel"] = str(slot_level(s))
        for c in ("reqskill1", "reqskill2", "reqskill3"):
            row[c] = ""
        d = by_desc[row["skilldesc"]]
        d["SkillPage"] = str(PAGE[s["tree"]])
        d["SkillRow"] = str(s["row"])
        d["SkillColumn"] = str(s["col"])
        k_name, k_short, k_long = _string_keys(s["slug"])
        d["str name"], d["str short"], d["str long"], d["str alt"] = k_name, k_short, k_long, k_name


def string_updates() -> List[Tuple[int, str, str]]:
    state = load_state()
    out = []
    for i, s in enumerate(SLOTS):
        slug = s["slug"]
        var = active_variant(slug, state)
        spec = load_spec(slug)
        override = spec["variants"].get(var, {}).get("strings", {})
        name, short, long = slot_texts(s, var, status_of(slug, state), override)
        k_name, k_short, k_long = _string_keys(slug)
        base = STRING_ID_BASE + i * 3
        out += [(base, k_name, name), (base + 1, k_short, short), (base + 2, k_long, long)]
    return out


def manifest() -> List[dict]:
    state = load_state()
    return [{"slug": s["slug"], "name": s["name"], "variant": active_variant(s["slug"], state),
             "status": status_of(s["slug"], state)} for s in SLOTS]


def hd_missile_pairs() -> List[Tuple[str, str]]:
    """(missile name, HD effect) pairs declared by active variants under "hd_missiles".
    New missile rows need an HD entry; "null" makes them invisible."""
    pairs = []
    for _slug, _var, block in active_blocks():
        pairs += [(k, v) for k, v in block.get("hd_missiles", {}).items()]
    return pairs


def animdata_speeds() -> Dict[str, object]:
    """{animdata record name prefix: playback speed} from active variants' "animdata" key
    (256 = normal; 128 = half speed, i.e. the animation takes twice as long)."""
    out: Dict[str, object] = {}
    for _slug, _var, block in active_blocks():
        for prefix, cfg in block.get("animdata", {}).items():
            out[prefix] = cfg  # int speed, or {"fpc": N, "spd": S, "events": "scale"}
    return out


def state_machine_defs() -> List[dict]:
    """Sequence-state definitions from active variants' "state_machine" key:
    [{"skillIndex": 58, "steps": [{"binding": "cast", "loop": 1}, ...]}]"""
    defs: List[dict] = []
    for _slug, _var, block in active_blocks():
        defs += block.get("state_machine", [])
    return defs

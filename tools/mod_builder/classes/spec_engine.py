"""
Shared declarative per-skill JSON spec engine for all Castalia classes.

Every class under `tools/mod_builder/classes/<class>/` uses the same structure:
  - registry.py         -> 30-slot 1:1 vanilla row map (layout, names, reqlevel, prereqs, role, design)
  - state.json          -> per-skill status (stub|wip|tested|done) and active variant name
  - specs/_shared.json  -> shared helper rows (states, helper skills, missiles, strings, macros)
  - specs/<slug>.json   -> per-skill named variants patching game tables

Variant JSON schema (all keys optional except description):
    {
      "description": "what this variant does / tests",
      "macros": {"NAME": "expanded D2R formula text"},
      "tables": {
        "skills.txt":        {"<skill row name>": {"<column>": "<value>", ...}},
        "skilldesc.txt":     {"<skilldesc key>":  {...}},
        "missiles.txt":      {"<missile name>":   {...}},
        "states.txt":        {"<state name>":     {...}},
        "itemstatcost.txt":  {"<stat name>":      {...}}
      },
      "strings": {"name": "...", "short": "...", "long": "..."},
      "strings_extra": {"<key>": "<text>"},
      "string_entries": [[<id>, "<key>", "<text>"], ...],
      "hd_missiles": {"<missile name>": "<hd effect>"},
      "animdata": {"<prefix>": <speed_or_cfg>},
      "state_machine": [{"skillIndex": <id>, "steps": [...]}]
    }

A key that does not exist yet creates a NEW row and must specify:
  - "_clone": "<existing key>"  -> copy columns from an existing row, then apply overrides
  - "_clone": "__blank__"       -> start from an empty row (auto-assigns *Id and *eol="0")
"""
import importlib
import json
import os
import re
from typing import Dict, List, Optional, Tuple

TABLE_KEYS = {
    "skills.txt": "skill",
    "skilldesc.txt": "skilldesc",
    "missiles.txt": "Missile",
    "states.txt": "state",
    "itemstatcost.txt": "Stat",
}
STATUSES = ("stub", "wip", "tested", "done")


def _id_col(headers: List[str]) -> str:
    for h in headers:
        if re.fullmatch(r"\*?id", h, re.I):
            return h
    return ""


def _expand_macros(val: str, macros: Dict[str, str]) -> str:
    if not macros or "${" not in val:
        return val
    return re.sub(r"\$\{([A-Za-z0-9_]+)\}", lambda m: macros.get(m.group(1), m.group(0)), val)


class ClassSpecEngine:
    def __init__(
        self,
        cls_key: str,
        charclass: str,
        class_dir: str,
        registry_module: str,
        *,
        env_var: str = "",
        auto_strings: bool = False,
        string_prefix: str = "",
        string_id_base: int = 0,
    ) -> None:
        self.cls_key = cls_key
        self.charclass = charclass
        self.class_dir = class_dir
        self.spec_dir = os.path.join(class_dir, "specs")
        self.state_path = os.path.join(class_dir, "state.json")
        self.registry_module = registry_module
        self.env_var = env_var or f"{charclass.upper()}_VARIANTS"
        self.auto_strings = auto_strings
        self.string_prefix = string_prefix
        self.string_id_base = string_id_base
        self._reg = None

    @property
    def registry(self):
        if self._reg is None:
            self._reg = importlib.import_module(self.registry_module)
        return self._reg

    # ------------------------------------------------------------------ state / specs
    def load_state(self) -> Dict[str, dict]:
        if os.path.exists(self.state_path):
            with open(self.state_path) as f:
                return json.load(f)
        return {}

    def save_state(self, state: Dict[str, dict]) -> None:
        with open(self.state_path, "w") as f:
            json.dump(state, f, indent=2, sort_keys=True)
            f.write("\n")

    def spec_path(self, slug: str) -> str:
        return os.path.join(self.spec_dir, f"{slug}.json")

    def default_spec(self, slug: str) -> dict:
        return {
            "slug": slug,
            "variants": {
                "baseline": {
                    "description": "new name/layout only; behaviour is still the vanilla row (stub)"
                }
            },
        }

    def load_spec(self, slug: str) -> dict:
        p = self.spec_path(slug)
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
        return self.default_spec(slug)

    def save_spec(self, slug: str, spec: dict) -> None:
        os.makedirs(self.spec_dir, exist_ok=True)
        with open(self.spec_path(slug), "w") as f:
            json.dump(spec, f, indent=2)
            f.write("\n")

    def env_overrides(self) -> Dict[str, str]:
        out = {}
        for part in os.environ.get(self.env_var, "").split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip()] = v.strip()
        return out

    def active_variant(self, slug: str, state: Optional[Dict[str, dict]] = None) -> str:
        state = self.load_state() if state is None else state
        env = self.env_overrides()
        if slug in env:
            return env[slug]
        return state.get(slug, {}).get("variant", "baseline")

    def status_of(self, slug: str, state: Optional[Dict[str, dict]] = None) -> str:
        state = self.load_state() if state is None else state
        return state.get(slug, {}).get("status", "stub")

    def active_blocks(self) -> List[Tuple[str, str, dict]]:
        """(slug, variant_name, variant_dict) for every active variant, _shared first."""
        state = self.load_state()
        blocks = []
        slugs = ["_shared"] + [s["slug"] for s in self.registry.SLOTS]
        for slug in slugs:
            if slug == "_shared":
                spec = (
                    self.load_spec("_shared")
                    if os.path.exists(self.spec_path("_shared"))
                    else {"variants": {"baseline": {}}}
                )
            else:
                spec = self.load_spec(slug)
            var = self.active_variant(slug, state)
            if var not in spec["variants"]:
                raise KeyError(
                    f"{self.cls_key}/{slug}: variant '{var}' not found (have {list(spec['variants'])})"
                )
            blocks.append((slug, var, spec["variants"][var]))
        return blocks

    # ------------------------------------------------------------------ table patching
    def apply_table_patches(
        self, table: str, headers: List[str], rows: List[Dict[str, str]]
    ) -> int:
        """Apply every active variant's patches for `table` in place. Returns patched-row count."""
        key_col = TABLE_KEYS[table]
        by_key = {r[key_col]: r for r in rows if r.get(key_col)}
        id_col = _id_col(headers)
        count = 0
        deferred = []  # (row, col, template) for values using {id:<key>} placeholders
        shared_macros: Dict[str, str] = {}

        blocks = self.active_blocks()
        if blocks and blocks[0][0] == "_shared":
            shared_macros = dict(blocks[0][2].get("macros", {}))

        for slug, var, block in blocks:
            macros = dict(shared_macros)
            if slug != "_shared" and "macros" in block:
                macros.update(block["macros"])
            for key, patch in block.get("tables", {}).get(table, {}).items():
                patch = dict(patch)
                clone = patch.pop("_clone", None)
                if key in by_key:
                    row = by_key[key]
                else:
                    if clone == "__blank__":
                        row = {h: "" for h in headers}
                        if "*eol" in row:
                            row["*eol"] = "0"
                    elif clone and clone in by_key:
                        row = dict(by_key[clone])
                    else:
                        raise KeyError(
                            f"[{self.cls_key}/{slug}:{var}] {table}: '{key}' is new and needs a valid '_clone'"
                        )
                    row[key_col] = key
                    if id_col and id_col not in patch:
                        nums = [
                            int(r[id_col])
                            for r in rows
                            if r.get(id_col, "").lstrip("-").isdigit()
                        ]
                        row[id_col] = str(max(nums) + 1) if nums else "0"
                    rows.append(row)
                    by_key[key] = row
                for col, val in patch.items():
                    if col not in headers:
                        raise KeyError(
                            f"[{self.cls_key}/{slug}:{var}] {table}/{key}: unknown column '{col}'"
                        )
                    sval = _expand_macros(str(val), macros)
                    row[col] = sval
                    if "{id:" in sval:
                        deferred.append((row, col, sval))
                count += 1

        for row, col, tmpl in deferred:
            def _sub(m):
                return by_key[m.group(1)][id_col]

            row[col] = re.sub(r"\{id:([^}]+)\}", _sub, tmpl)
        return count

    # ------------------------------------------------------------------ layout + strings
    def _string_keys(self, slug: str) -> Tuple[str, str, str]:
        return (
            f"{self.string_prefix}{slug}_name",
            f"{self.string_prefix}{slug}_short",
            f"{self.string_prefix}{slug}_long",
        )

    def slot_texts(
        self, slot: dict, variant: str, status: str, override: dict, label: bool = True
    ) -> Tuple[str, str, str]:
        name = override.get("name", slot["name"])
        if status == "stub":
            short = override.get("short", f"[stub] {slot['role']} - acts as vanilla {slot['vname']}")
            long = override.get(
                "long",
                f"STUB: still behaves as vanilla {slot['vname']}.\n\n"
                f"Design intent ({slot['role']}):\n{slot['design']}",
            )
        else:
            short = override.get("short", slot["role"])
            long = override.get("long", slot["design"])
        if variant != "baseline" and label:
            long += f"\n\n[test variant: {variant}]"
        return name, short, long

    def apply_layout(self, by_name: Dict[str, dict], by_desc: Dict[str, dict]) -> None:
        reg = self.registry
        problems = reg.check_registry()
        if problems:
            raise RuntimeError(f"{self.cls_key} registry invalid: " + "; ".join(problems))
        for s in reg.SLOTS:
            row = by_name.get(s["vname"])
            if row is None or row.get("*Id") != str(s["vid"]) or row.get("charclass") != self.charclass:
                raise RuntimeError(
                    f"{self.cls_key} map: row '{s['vname']}' is not {self.charclass} id {s['vid']}"
                )
            row["reqlevel"] = str(reg.slot_level(s))
            prereqs = s.get("prereqs", [])
            for idx, c in enumerate(("reqskill1", "reqskill2", "reqskill3")):
                row[c] = reg.BY_SLUG[prereqs[idx]]["vname"] if idx < len(prereqs) else ""
            d = by_desc[row["skilldesc"]]
            d["SkillPage"] = str(reg.PAGE[s["tree"]])
            d["SkillRow"] = str(s["row"])
            d["SkillColumn"] = str(s["col"])
            if self.auto_strings:
                k_name, k_short, k_long = self._string_keys(s["slug"])
                d["str name"], d["str short"], d["str long"], d["str alt"] = (
                    k_name,
                    k_short,
                    k_long,
                    k_name,
                )

    def string_updates(self) -> List[Tuple[int, str, str]]:
        state = self.load_state()
        out: List[Tuple[int, str, str]] = []
        if self.auto_strings:
            for i, s in enumerate(self.registry.SLOTS):
                slug = s["slug"]
                var = self.active_variant(slug, state)
                spec = self.load_spec(slug)
                blk = spec["variants"].get(var, {})
                override = blk.get("strings", {})
                name, short, long = self.slot_texts(
                    s, var, self.status_of(slug, state), override, not blk.get("no_label", False)
                )
                k_name, k_short, k_long = self._string_keys(slug)
                base = self.string_id_base + i * 3
                out += [(base, k_name, name), (base + 1, k_short, short), (base + 2, k_long, long)]
            extra: Dict[str, str] = {}
            for _slug, _var, block in self.active_blocks():
                extra.update(block.get("strings_extra", {}))
            for i, key in enumerate(sorted(extra)):
                out.append((self.string_id_base + 200 + i, key, extra[key]))

        # Explicit string_entries: [[id, key, text], ...]
        for _slug, _var, block in self.active_blocks():
            for entry in block.get("string_entries", []):
                out.append((int(entry[0]), str(entry[1]), str(entry[2])))
        return out

    def manifest(self) -> List[dict]:
        state = self.load_state()
        return [
            {
                "slug": s["slug"],
                "name": s["name"],
                "variant": self.active_variant(s["slug"], state),
                "status": self.status_of(s["slug"], state),
            }
            for s in self.registry.SLOTS
        ]

    def hd_missile_pairs(self) -> List[Tuple[str, str]]:
        pairs: List[Tuple[str, str]] = []
        for _slug, _var, block in self.active_blocks():
            pairs += [(k, v) for k, v in block.get("hd_missiles", {}).items()]
        return pairs

    def animdata_speeds(self) -> Dict[str, object]:
        out: Dict[str, object] = {}
        for _slug, _var, block in self.active_blocks():
            for prefix, cfg in block.get("animdata", {}).items():
                out[prefix] = cfg
        return out

    def state_machine_defs(self) -> List[dict]:
        defs: List[dict] = []
        for _slug, _var, block in self.active_blocks():
            defs += block.get("state_machine", [])
        return defs

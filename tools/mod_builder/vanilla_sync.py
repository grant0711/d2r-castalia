#!/usr/bin/env python3
"""
vanilla_sync.py
Controlled, zero-leakage Blizzard patch upgrade pipeline for Castalia (D2R mod).

Phases:
  1. stage  - Extract pristine CASC files into gitignored runtime/vanilla-staging/<build>/
  2. audit  - Diff vanilla-reference/ vs staged <build>/ with schema, row, cell, string,
              and Castalia leakage classification; write docs/patches/patch_<old>_to_<new>.md
  3. apply  - Selectively promote changes via per-file policy (schema-only / accept / keep),
              migrate locked_tables/ headers if needed, and record vanilla-reference/SYNC_MANIFEST.json
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from mod_builder.common import GAME_DIR, MOD_EXCEL, REPO_ROOT, VANILLA_EXCEL, VANILLA_ROOT, VANILLA_STRINGS

EXTRACTOR = os.path.join(REPO_ROOT, "bin/setup/d2r-casc-extract")
STAGING_BASE = os.path.join(REPO_ROOT, "runtime/vanilla-staging")
LOCKED_TABLES_DIR = os.path.join(REPO_ROOT, "tools/mod_builder/locked_tables")
PATCH_DOCS_DIR = os.path.join(REPO_ROOT, "docs/patches")
SYNC_MANIFEST_PATH = os.path.join(VANILLA_ROOT, "SYNC_MANIFEST.json")

# Preferred primary-key column per table (fallback to first non-empty identifier column)
PREFERRED_KEYS: Dict[str, List[str]] = {
    "skills.txt": ["skill", "*Id"],
    "skilldesc.txt": ["skilldesc"],
    "missiles.txt": ["Missile", "*ID"],
    "states.txt": ["state", "*ID"],
    "itemstatcost.txt": ["Stat", "*ID"],
    "properties.txt": ["code", "*Id"],
    "uniqueitems.txt": ["index", "*ID"],
    "setitems.txt": ["index", "*ID"],
    "sets.txt": ["index"],
    "runes.txt": ["Name", "*Rune Name"],
    "weapons.txt": ["code", "name"],
    "armor.txt": ["code", "name"],
    "misc.txt": ["code", "name"],
    "itemtypes.txt": ["Code", "ItemType"],
    "magicprefix.txt": ["Name"],
    "magicsuffix.txt": ["Name"],
    "automagic.txt": ["Name"],
    "monstats.txt": ["Id", "hcIdx"],
    "monstats2.txt": ["Id"],
    "superuniques.txt": ["Superunique", "hcIdx"],
    "levels.txt": ["Name", "Id"],
    "treasureclassex.txt": ["Treasure Class"],
    "cubemain.txt": ["description"],
    "charstats.txt": ["class"],
    "pettype.txt": ["pet type"],
    "hireling.txt": ["Id", "Hireling"],
    "hirelingdesc.txt": ["id"],
    "objects.txt": ["Name", "*ID"],
    "shrines.txt": ["Code", "Name"],
    "gems.txt": ["code", "name"],
    "itemratio.txt": ["Function"],
    "difficultylevels.txt": ["Name"],
    "experience.txt": ["Level"],
}

ID_SENSITIVE_TABLES = {
    "skills.txt": "*Id",
    "states.txt": "*ID",
    "itemstatcost.txt": "*ID",
    "missiles.txt": "*ID",
    "monstats.txt": "hcIdx",
}


def _read_build_version(root_dir: str) -> str:
    for rel in ("data/global/dataversionbuild.txt", "data/global/DataVersionBuild.txt"):
        p = os.path.join(root_dir, rel)
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    s = line.strip()
                    if s and s.lower() != "build":
                        return s
    # Fallback to .build.info in GAME_DIR if reading staged build
    return "unknown"


def _read_game_build_info() -> Tuple[str, str]:
    """Return (version_str, build_num) from game/Diablo II Resurrected/.build.info."""
    p = os.path.join(GAME_DIR, ".build.info")
    if not os.path.isfile(p):
        return "unknown", "unknown"
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    if len(lines) < 2:
        return "unknown", "unknown"
    hdrs = [h.split("!")[0] for h in lines[0].split("|")]
    vals = lines[1].split("|")
    row = dict(zip(hdrs, vals))
    ver = row.get("Version", "unknown")
    bnum = ver.split(".")[-1] if "." in ver else ver
    return ver, bnum


def _read_tsv(path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        raw = f.read().splitlines()
    if not raw:
        return [], []
    headers = raw[0].split("\t")
    rows: List[Dict[str, str]] = []
    for line in raw[1:]:
        if not line:
            continue
        vals = line.split("\t")
        if len(vals) < len(headers):
            vals += [""] * (len(headers) - len(vals))
        elif len(vals) > len(headers):
            vals = vals[: len(headers)]
        rows.append(dict(zip(headers, vals)))
    return headers, rows


def _write_tsv(path: str, headers: List[str], rows: List[Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = ["\t".join(headers)]
    for r in rows:
        out.append("\t".join(str(r.get(h, "")) for h in headers))
    with open(path, "wb") as f:
        f.write(("\r\n".join(out) + "\r\n").encode("utf-8"))


def _pick_key_col(filename: str, headers: List[str]) -> Optional[str]:
    base = os.path.basename(filename).lower()
    for candidate in PREFERRED_KEYS.get(base, []):
        if candidate in headers:
            return candidate
    for h in headers:
        if h and not h.startswith("*") and h.lower() not in ("eol",):
            return h
    return headers[0] if headers else None


def _index_rows(rows: List[Dict[str, str]], key_col: Optional[str]) -> Dict[str, Dict[str, str]]:
    """Index rows uniquely by key_col, disambiguating duplicate keys with '#2', '#3', etc."""
    out: Dict[str, Dict[str, str]] = {}
    counts: Dict[str, int] = {}
    for idx, r in enumerate(rows):
        raw_k = (r.get(key_col, "").strip() if key_col else "") or f"<row:{idx+2}>"
        counts[raw_k] = counts.get(raw_k, 0) + 1
        k = raw_k if counts[raw_k] == 1 else f"{raw_k}#{counts[raw_k]}"
        out[k] = r
    return out


def _read_strings_map(path: str) -> Dict[str, Dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    out: Dict[str, Dict[str, str]] = {}
    if isinstance(data, list):
        for entry in data:
            k = entry.get("Key")
            if k is not None:
                out[str(k)] = entry
    return out


def stage_vanilla(build_override: Optional[str] = None) -> str:
    """Extract vanilla .txt and string .json files from CASC into runtime/vanilla-staging/<build>/."""
    if not os.path.isdir(os.path.join(GAME_DIR, "Data")):
        raise RuntimeError(f"D2R CASC Data folder not found at {GAME_DIR}/Data")
    if not os.path.isfile(EXTRACTOR):
        raise RuntimeError(f"CASC extractor not found at {EXTRACTOR}")

    ver, bnum = _read_game_build_info()
    tmp_dir = os.path.join(STAGING_BASE, "_tmp")
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir, exist_ok=True)

    patterns = [
        "*dataversionbuild.txt",
        "*global*excel*.txt",
        "*local*lng*strings*.json",
    ]
    for pat in patterns:
        subprocess.run([EXTRACTOR, GAME_DIR, tmp_dir, pat], check=True)

    staged_build = build_override or _read_build_version(tmp_dir)
    if staged_build == "unknown":
        staged_build = bnum

    dest_dir = os.path.join(STAGING_BASE, staged_build)
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    shutil.move(tmp_dir, dest_dir)
    print(f"[vanilla-sync] Staged D2R {ver} (dataversionbuild={staged_build}) -> {dest_dir}")
    print(f"[vanilla-sync] vanilla-reference/ was NOT modified.")
    return dest_dir


def _resolve_staging_dir(build: Optional[str]) -> Tuple[str, str]:
    if build:
        d = os.path.join(STAGING_BASE, str(build))
        if not os.path.isdir(d):
            raise RuntimeError(f"Staging directory not found: {d}. Run 'd2r-vanilla-sync stage' first.")
        return str(build), d
    if not os.path.isdir(STAGING_BASE):
        raise RuntimeError(f"No staged builds found under {STAGING_BASE}. Run 'd2r-vanilla-sync stage' first.")
    candidates = sorted(
        [n for n in os.listdir(STAGING_BASE) if os.path.isdir(os.path.join(STAGING_BASE, n)) and not n.startswith("_")]
    )
    if not candidates:
        raise RuntimeError(f"No staged builds found under {STAGING_BASE}. Run 'd2r-vanilla-sync stage' first.")
    chosen = candidates[-1]
    return chosen, os.path.join(STAGING_BASE, chosen)


def _list_relative_files(base_dir: str, ext: str) -> List[str]:
    found: List[str] = []
    if not os.path.isdir(base_dir):
        return found
    for root, _, files in os.walk(base_dir):
        for fn in files:
            if fn.lower().endswith(ext):
                rel = os.path.relpath(os.path.join(root, fn), base_dir)
                found.append(rel)
    return sorted(found)


def audit_vanilla(build: Optional[str] = None) -> str:
    """Generate a structured Markdown diff & Castalia leakage report comparing vanilla-reference/ vs staged build."""
    old_build = _read_build_version(VANILLA_ROOT)
    new_build, stage_dir = _resolve_staging_dir(build)
    game_ver, _ = _read_game_build_info()

    old_excel = VANILLA_EXCEL
    new_excel = os.path.join(stage_dir, "data/global/excel")
    old_strings = VANILLA_STRINGS
    new_strings = os.path.join(stage_dir, "data/local/lng/strings")

    locked_files = set(os.listdir(LOCKED_TABLES_DIR)) if os.path.isdir(LOCKED_TABLES_DIR) else set()
    mod_excel_files = set(_list_relative_files(MOD_EXCEL, ".txt"))

    old_txts = set(_list_relative_files(old_excel, ".txt"))
    new_txts = set(_list_relative_files(new_excel, ".txt"))
    all_txts = sorted(old_txts | new_txts)

    schema_changes: List[str] = []
    locked_schema_alerts: List[str] = []
    id_shifts: List[str] = []
    table_summaries: List[dict] = []
    new_tables: List[str] = sorted(new_txts - old_txts)
    removed_tables: List[str] = sorted(old_txts - new_txts)

    for rel in all_txts:
        if rel not in old_txts or rel not in new_txts:
            continue
        p_old = os.path.join(old_excel, rel)
        p_new = os.path.join(new_excel, rel)
        with open(p_old, "rb") as f1, open(p_new, "rb") as f2:
            if f1.read() == f2.read():
                continue

        h_old, r_old = _read_tsv(p_old)
        h_new, r_new = _read_tsv(p_new)
        added_cols = [c for c in h_new if c not in h_old]
        removed_cols = [c for c in h_old if c not in h_new]
        reordered = (not added_cols and not removed_cols and h_old != h_new)
        has_schema_change = bool(added_cols or removed_cols or reordered)
        if has_schema_change:
            parts = []
            if added_cols:
                parts.append(f"+cols: `{added_cols}`")
            if removed_cols:
                parts.append(f"-cols: `{removed_cols}`")
            if reordered:
                parts.append("reordered columns")
            schema_changes.append(f"- **`{rel}`**: " + "; ".join(parts))

        base_name = os.path.basename(rel)
        if rel == base_name and base_name in locked_files:
            h_lock, _ = _read_tsv(os.path.join(LOCKED_TABLES_DIR, base_name))
            if h_lock != h_new:
                locked_schema_alerts.append(
                    f"- **`locked_tables/{base_name}`** differs from new vanilla schema "
                    f"(+cols: `{[c for c in h_new if c not in h_lock]}`, -cols: `{[c for c in h_lock if c not in h_new]}`)"
                )

        key_col = _pick_key_col(rel, h_old)
        idx_old = _index_rows(r_old, key_col)
        idx_new = _index_rows(r_new, key_col)
        added_rows = [k for k in idx_new if k not in idx_old]
        removed_rows = [k for k in idx_old if k not in idx_new]

        # Check ID shifts on ID-sensitive tables
        id_col = ID_SENSITIVE_TABLES.get(rel.lower())
        if id_col and id_col in h_old and id_col in h_new:
            shifted = []
            for k in idx_old:
                if k in idx_new and idx_old[k].get(id_col) != idx_new[k].get(id_col):
                    shifted.append(f"`{k}` ({idx_old[k].get(id_col)} -> {idx_new[k].get(id_col)})")
            if shifted:
                id_shifts.append(f"- **`{rel}`** ({len(shifted)} ID shifts): " + ", ".join(shifted[:10]))

        # Load current mod table for leakage classification
        is_locked = (rel == base_name and base_name in locked_files)
        in_mod = rel in mod_excel_files
        idx_mod: Dict[str, Dict[str, str]] = {}
        if in_mod:
            _, r_mod = _read_tsv(os.path.join(MOD_EXCEL, rel))
            idx_mod = _index_rows(r_mod, key_col)

        common_cols = [c for c in h_old if c in h_new]
        leaks: List[Tuple[str, str, str, str]] = []
        overwritten: List[Tuple[str, str, str, str]] = []
        inherited_unmodded: List[Tuple[str, str, str, str]] = []
        locked_diffs: List[Tuple[str, str, str, str]] = []
        disabled_diffs: List[Tuple[str, str, str, str]] = []

        is_disabled_runes = (rel.lower() == "runes.txt" and in_mod)

        for k, row_old in idx_old.items():
            if k not in idx_new:
                continue
            row_new = idx_new[k]
            row_mod = idx_mod.get(k)
            row_disabled_in_mod = is_disabled_runes and (row_mod is not None and row_mod.get("complete", "").strip() != "1")
            for col in common_cols:
                v_old = row_old.get(col, "")
                v_new = row_new.get(col, "")
                if v_old == v_new:
                    continue
                item = (k, col, v_old, v_new)
                if is_locked:
                    locked_diffs.append(item)
                elif row_disabled_in_mod:
                    disabled_diffs.append(item)
                elif not in_mod:
                    inherited_unmodded.append(item)
                elif row_mod is None or row_mod.get(col, "") == v_old:
                    leaks.append(item)
                else:
                    overwritten.append(item)

        if is_locked:
            risk = "LOCKED TABLE"
            rec = "schema-only" if has_schema_change else "keep"
        elif disabled_diffs and not leaks:
            risk = "DISABLED IN MOD"
            rec = "schema-only" if has_schema_change else "keep"
        elif leaks or added_rows or removed_rows:
            risk = "LEAKS INTO CASTALIA" if in_mod else "GAME-INHERITED (NOT IN MOD)"
            rec = "schema-only" if has_schema_change else "review / keep"
        elif has_schema_change:
            risk = "ENGINE / SCHEMA"
            rec = "schema-only"
        elif inherited_unmodded:
            risk = "GAME-INHERITED (NOT IN MOD)"
            rec = "review / keep"
        else:
            risk = "OVERWRITTEN BY MOD"
            rec = "accept (safe)"

        table_summaries.append({
            "rel": rel,
            "risk": risk,
            "rec": rec,
            "has_schema_change": has_schema_change,
            "added_cols": added_cols,
            "removed_cols": removed_cols,
            "added_rows": added_rows,
            "removed_rows": removed_rows,
            "leaks": leaks,
            "overwritten": overwritten,
            "inherited_unmodded": inherited_unmodded,
            "locked_diffs": locked_diffs,
            "disabled_diffs": disabled_diffs,
        })

    # String JSON diffs
    old_jsons = set(_list_relative_files(old_strings, ".json"))
    new_jsons = set(_list_relative_files(new_strings, ".json"))
    string_diffs: List[dict] = []
    for rel in sorted(old_jsons | new_jsons):
        if rel not in old_jsons:
            string_diffs.append({"rel": rel, "status": "NEW FILE", "added": [], "removed": [], "changed": []})
            continue
        if rel not in new_jsons:
            string_diffs.append({"rel": rel, "status": "REMOVED FILE", "added": [], "removed": [], "changed": []})
            continue
        m_old = _read_strings_map(os.path.join(old_strings, rel))
        m_new = _read_strings_map(os.path.join(new_strings, rel))
        s_add = [k for k in m_new if k not in m_old]
        s_rem = [k for k in m_old if k not in m_new]
        s_chg = [
            (k, m_old[k].get("enUS", ""), m_new[k].get("enUS", ""))
            for k in m_old
            if k in m_new and m_old[k].get("enUS", "") != m_new[k].get("enUS", "")
        ]
        if s_add or s_rem or s_chg:
            string_diffs.append({"rel": rel, "status": "CHANGED", "added": s_add, "removed": s_rem, "changed": s_chg})

    # Build Markdown report
    os.makedirs(PATCH_DOCS_DIR, exist_ok=True)
    report_path = os.path.join(PATCH_DOCS_DIR, f"patch_{old_build}_to_{new_build}.md")
    md: List[str] = [
        f"# Blizzard Vanilla Patch Audit: `{old_build}` -> `{new_build}` (D2R {game_ver})",
        "",
        f"- **Generated:** {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- **Current `vanilla-reference/` build:** `{old_build}`",
        f"- **Staged CASC build:** `{new_build}` (`{stage_dir}`)",
        f"- **Changed `.txt` tables:** `{len(table_summaries)}` (new: `{len(new_tables)}`, removed: `{len(removed_tables)}`)",
        f"- **Changed string `.json` files:** `{len(string_diffs)}`",
        "",
        "## 1. Schema / Column Changes (Engine-Critical)",
    ]
    if schema_changes:
        md.extend(schema_changes)
    else:
        md.append("- None! Zero `.txt` columns were added, removed, or reordered.")

    if locked_schema_alerts:
        md.append("")
        md.append("### `locked_tables/` Schema Alerts")
        md.extend(locked_schema_alerts)

    md.append("")
    md.append("## 2. ID-Shift Alerts (`skills`, `states`, `itemstatcost`, `missiles`, `monstats`)")
    if id_shifts:
        md.extend(id_shifts)
    else:
        md.append("- None! Zero row ID shifts detected in ID-sensitive tables.")

    if new_tables or removed_tables:
        md.append("")
        md.append("## 3. Added / Removed `.txt` Tables")
        for t in new_tables:
            md.append(f"- **NEW:** `{t}`")
        for t in removed_tables:
            md.append(f"- **REMOVED:** `{t}`")

    md.append("")
    md.append("## 4. Changed `.txt` Tables — Castalia Leakage Matrix")
    if not table_summaries:
        md.append("- No `.txt` tables changed between these builds.")
    else:
        md.append("| Table | Leakage Classification | Schema? | +Rows / -Rows | Leaking Cells | Overwritten Cells | Recommended Policy |")
        md.append("| :--- | :--- | :---: | :---: | :---: | :---: | :--- |")
        for s in table_summaries:
            sc = "YES" if s["has_schema_change"] else "no"
            rr = f"+{len(s['added_rows'])} / -{len(s['removed_rows'])}"
            lk = len(s["leaks"]) + len(s["inherited_unmodded"])
            ow = len(s["overwritten"]) + len(s["locked_diffs"]) + len(s["disabled_diffs"])
            md.append(f"| `{s['rel']}` | **{s['risk']}** | {sc} | {rr} | {lk} | {ow} | `{s['rec']}` |")

        md.append("")
        md.append("### Detailed Table Changes")
        for s in table_summaries:
            md.append(f"#### `{s['rel']}` — `{s['risk']}`")
            if s["added_rows"]:
                md.append(f"- **Added rows ({len(s['added_rows'])}):** " + ", ".join(f"`{x}`" for x in s["added_rows"][:25]))
            if s["removed_rows"]:
                md.append(f"- **Removed rows ({len(s['removed_rows'])}):** " + ", ".join(f"`{x}`" for x in s["removed_rows"][:25]))
            for label, bucket in (
                ("Leaking into Castalia", s["leaks"]),
                ("Game-inherited (not overridden in mod)", s["inherited_unmodded"]),
                ("Overwritten by mod_builder (safe)", s["overwritten"]),
                ("Superseded by locked_tables/ (safe)", s["locked_diffs"]),
                ("Disabled in Castalia (safe)", s["disabled_diffs"]),
            ):
                if bucket:
                    md.append(f"- **{label} ({len(bucket)} cells):**")
                    for k, col, vo, vn in bucket[:30]:
                        md.append(f"  - `{k}`.`{col}`: `{vo}` -> `{vn}`")
                    if len(bucket) > 30:
                        md.append(f"  - *...and {len(bucket) - 30} more cells*")
            md.append("")

    md.append("## 5. String Table (`.json`) Changes")
    if not string_diffs:
        md.append("- No string `.json` changes detected.")
    else:
        for sd in string_diffs:
            md.append(
                f"- **`{sd['rel']}`** ({sd['status']}): "
                f"+{len(sd['added'])} keys, -{len(sd['removed'])} keys, {len(sd['changed'])} changed `enUS` strings"
            )
            for k in sd["added"][:15]:
                md.append(f"  - `+ {k}`")
            for k, vo, vn in sd["changed"][:15]:
                vo_s = vo.replace("\n", "\\n")[:80]
                vn_s = vn.replace("\n", "\\n")[:80]
                md.append(f"  - `~ {k}`: `{vo_s}` -> `{vn_s}`")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"[vanilla-sync] Wrote audit report -> {report_path}")
    print(f"  Build: {old_build} -> {new_build} (D2R {game_ver})")
    print(f"  Changed .txt tables: {len(table_summaries)} | Schema changes: {len(schema_changes)} | ID shifts: {len(id_shifts)}")
    print(f"  Changed string .json files: {len(string_diffs)}")
    for s in table_summaries:
        lk = len(s["leaks"]) + len(s["inherited_unmodded"])
        print(f"    - {s['rel']:32s} [{s['risk']}] +rows={len(s['added_rows'])} -rows={len(s['removed_rows'])} leaking_cells={lk}")
    return report_path


def _apply_schema_only_tsv(old_path: str, new_path: str) -> None:
    """Adopt new/reordered column schema from new_path while preserving all existing cell values from old_path."""
    h_old, r_old = _read_tsv(old_path)
    h_new, r_new = _read_tsv(new_path)
    key_col = _pick_key_col(old_path, h_old)
    idx_new = _index_rows(r_new, key_col)
    idx_old = _index_rows(r_old, key_col)

    merged_rows: List[Dict[str, str]] = []
    for k, old_row in idx_old.items():
        new_row = idx_new.get(k, {})
        out_row: Dict[str, str] = {}
        for col in h_new:
            if col in h_old:
                out_row[col] = old_row.get(col, "")
            else:
                out_row[col] = new_row.get(col, "")
        merged_rows.append(out_row)
    _write_tsv(old_path, h_new, merged_rows)


def apply_vanilla(
    build: Optional[str],
    accept: List[str],
    schema_only: List[str],
    keep: List[str],
    accept_strings: bool = False,
    accept_build_ver: bool = True,
) -> None:
    """Selectively promote staged vanilla files into vanilla-reference/ and update SYNC_MANIFEST.json."""
    old_build = _read_build_version(VANILLA_ROOT)
    new_build, stage_dir = _resolve_staging_dir(build)
    decisions: Dict[str, str] = {}

    if accept_build_ver:
        for rel in ("data/global/dataversionbuild.txt", "data/global/DataVersionBuild.txt"):
            src = os.path.join(stage_dir, "data/global/dataversionbuild.txt")
            if os.path.isfile(src):
                dst = os.path.join(VANILLA_ROOT, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        decisions["data/global/dataversionbuild.txt"] = "accepted"

    for rel in accept:
        src = os.path.join(stage_dir, "data/global/excel", rel)
        dst = os.path.join(VANILLA_EXCEL, rel)
        if not os.path.isfile(src):
            raise RuntimeError(f"Staged file not found for --accept: {src}")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        decisions[f"excel/{rel}"] = "accepted"
        print(f"[vanilla-sync] ACCEPTED: {rel}")

    for rel in schema_only:
        src = os.path.join(stage_dir, "data/global/excel", rel)
        dst = os.path.join(VANILLA_EXCEL, rel)
        if not os.path.isfile(src) or not os.path.isfile(dst):
            raise RuntimeError(f"Missing old or staged file for --schema-only: {rel}")
        _apply_schema_only_tsv(dst, src)
        decisions[f"excel/{rel}"] = "schema-only"
        print(f"[vanilla-sync] SCHEMA-ONLY: {rel}")
        # Also migrate locked_tables/ counterpart if present
        base_name = os.path.basename(rel)
        lock_p = os.path.join(LOCKED_TABLES_DIR, base_name)
        if rel == base_name and os.path.isfile(lock_p):
            _apply_schema_only_tsv(lock_p, src)
            decisions[f"locked_tables/{base_name}"] = "schema-only"
            print(f"[vanilla-sync] SCHEMA-ONLY (locked_tables): {base_name}")

    for rel in keep:
        decisions[f"excel/{rel}"] = "kept"
        print(f"[vanilla-sync] KEPT (frozen): {rel}")

    if accept_strings:
        new_strings_dir = os.path.join(stage_dir, "data/local/lng/strings")
        for rel in _list_relative_files(new_strings_dir, ".json"):
            src = os.path.join(new_strings_dir, rel)
            dst = os.path.join(VANILLA_STRINGS, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        decisions["strings/*.json"] = "accepted"
        print("[vanilla-sync] ACCEPTED: all string .json tables")

    manifest = {"history": []}
    if os.path.isfile(SYNC_MANIFEST_PATH):
        with open(SYNC_MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    manifest.setdefault("history", []).append({
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "from_build": old_build,
        "to_build": new_build,
        "decisions": decisions,
    })
    manifest["current_build"] = new_build if accept_build_ver else old_build
    with open(SYNC_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(f"[vanilla-sync] Updated {SYNC_MANIFEST_PATH}")


def _parse_csv_arg(val: Optional[str]) -> List[str]:
    if not val:
        return []
    return [x.strip() for x in val.split(",") if x.strip()]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="d2r-vanilla-sync", description="Controlled Blizzard vanilla-reference sync pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_stage = sub.add_parser("stage", help="Extract CASC vanilla files into gitignored runtime/vanilla-staging/<build>/")
    p_stage.add_argument("--build", default=None, help="Override staged build directory name")

    p_audit = sub.add_parser("audit", help="Generate structured diff & Castalia leakage report")
    p_audit.add_argument("--build", default=None, help="Staged build number (defaults to latest)")

    p_apply = sub.add_parser("apply", help="Selectively promote staged files into vanilla-reference/")
    p_apply.add_argument("--build", default=None, help="Staged build number (defaults to latest)")
    p_apply.add_argument("--accept", default="", help="Comma-separated excel/*.txt paths to accept in full")
    p_apply.add_argument("--schema-only", default="", help="Comma-separated excel/*.txt paths to update schema/columns only")
    p_apply.add_argument("--keep", default="", help="Comma-separated excel/*.txt paths explicitly pinned/kept")
    p_apply.add_argument("--accept-strings", action="store_true", help="Accept updated vanilla string .json files")
    p_apply.add_argument("--no-build-ver", action="store_true", help="Do not update dataversionbuild.txt")

    args = parser.parse_args(argv)
    if args.cmd == "stage":
        stage_vanilla(args.build)
    elif args.cmd == "audit":
        audit_vanilla(args.build)
    elif args.cmd == "apply":
        apply_vanilla(
            build=args.build,
            accept=_parse_csv_arg(args.accept),
            schema_only=_parse_csv_arg(args.schema_only),
            keep=_parse_csv_arg(args.keep),
            accept_strings=args.accept_strings,
            accept_build_ver=not args.no_build_ver,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

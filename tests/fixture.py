"""
fixture.py
Process-cached table & string loader for the Castalia TDD test suite.
Guarantees that compiled TSV and JSON files in my-mod/data/ are parsed and
checked for CRLF + column-count integrity once per test run.
"""
import functools
import json
import os
import sys
from typing import Dict, List, Set, Tuple

TOOLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools"))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from mod_builder.common import (
    MOD_EXCEL,
    MOD_ROOT,
    MOD_STRINGS,
    VANILLA_STRINGS,
    load_config,
    read_excel_tsv,
    read_strings_json,
)


@functools.lru_cache(maxsize=None)
def read_mod_tsv(filename: str, max_rows: int = 0) -> Tuple[List[str], List[Dict[str, str]]]:
    """Read a compiled TSV file from my-mod/data/global/excel, asserting CRLF and column counts."""
    path = os.path.join(MOD_EXCEL, filename)
    with open(path, "rb") as f:
        if max_rows > 0:
            lines: List[str] = []
            for _ in range(max_rows + 1):
                bline = f.readline()
                if not bline:
                    break
                if not bline.endswith(b"\r\n"):
                    raise AssertionError(f"{filename}: missing CRLF (\\r\\n) line endings")
                lines.append(bline[:-2].decode("utf-8"))
        else:
            raw_bytes = f.read()
            if b"\r\n" not in raw_bytes:
                raise AssertionError(f"{filename}: missing CRLF (\\r\\n) line endings")
            raw = raw_bytes.decode("utf-8")
            lines = raw.split("\r\n")
            if lines and lines[-1] == "":
                lines.pop()
    headers = lines[0].split("\t")
    rows: List[Dict[str, str]] = []
    for idx, line in enumerate(lines[1:], start=2):
        cols = line.split("\t")
        if len(cols) != len(headers):
            raise AssertionError(
                f"{filename} line {idx}: expected {len(headers)} columns, got {len(cols)}"
            )
        rows.append(dict(zip(headers, cols)))
    return headers, rows


@functools.lru_cache(maxsize=None)
def read_vanilla_tsv(filename: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Cached wrapper around read_excel_tsv for vanilla reference tables."""
    return read_excel_tsv(filename)


@functools.lru_cache(maxsize=1)
def load_all_string_keys() -> Set[str]:
    """Return the union of all string Keys across vanilla and mod JSON string tables."""
    keys: Set[str] = set()
    for root in (VANILLA_STRINGS, MOD_STRINGS):
        if not os.path.isdir(root):
            continue
        for fname in os.listdir(root):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            for entry in data:
                if isinstance(entry, dict) and "Key" in entry:
                    keys.add(entry["Key"])
    return keys


@functools.lru_cache(maxsize=1)
def get_indexed_tables() -> Dict[str, dict]:
    """Return pre-indexed dictionaries for fast O(1) lookups across test modules."""
    _, skill_rows = read_mod_tsv("skills.txt")
    _, desc_rows = read_mod_tsv("skilldesc.txt")
    _, missile_rows = read_mod_tsv("missiles.txt")
    _, state_rows = read_mod_tsv("states.txt")
    _, isc_rows = read_mod_tsv("itemstatcost.txt")
    _, van_isc_rows = read_vanilla_tsv("itemstatcost.txt")

    skills_by_name = {r["skill"]: r for r in skill_rows if r.get("skill")}
    skills_by_lower = {r["skill"].lower(): r for r in skill_rows if r.get("skill")}
    skills_by_id = {r["*Id"]: r for r in skill_rows if r.get("*Id")}
    desc_by_name = {r["skilldesc"]: r for r in desc_rows if r.get("skilldesc")}
    desc_by_lower = {r["skilldesc"].lower(): r for r in desc_rows if r.get("skilldesc")}
    missiles_by_name = {r["Missile"]: r for r in missile_rows if r.get("Missile")}
    states_by_name = {r["state"]: r for r in state_rows if r.get("state")}
    valid_stats = {r["Stat"] for r in van_isc_rows if r.get("Stat")} | {
        r["Stat"] for r in isc_rows if r.get("Stat")
    }

    return {
        "skills_by_name": skills_by_name,
        "skills_by_lower": skills_by_lower,
        "skills_by_id": skills_by_id,
        "desc_by_name": desc_by_name,
        "desc_by_lower": desc_by_lower,
        "missiles_by_name": missiles_by_name,
        "states_by_name": states_by_name,
        "valid_stats": valid_stats,
    }


def clear_fixture_caches() -> None:
    """Clear all cached tables so post-build verification always reads fresh disk state."""
    read_mod_tsv.cache_clear()
    read_vanilla_tsv.cache_clear()
    load_all_string_keys.cache_clear()
    get_indexed_tables.cache_clear()

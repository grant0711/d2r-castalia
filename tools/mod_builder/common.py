#!/usr/bin/env python3
"""
common.py
Shared utilities for reading pristine vanilla D2R .txt/JSON tables from
/home/grant/games/d2r/vanilla-reference/ and writing deterministic, validated
CRLF .txt/JSON tables to /home/grant/games/d2r/my-mod/.
"""
import json
import os
from typing import Dict, List, Tuple

VANILLA_ROOT = "/home/grant/games/d2r/vanilla-reference"
MOD_ROOT = "/home/grant/games/d2r/my-mod"
VANILLA_EXCEL = os.path.join(VANILLA_ROOT, "data/global/excel")
MOD_EXCEL = os.path.join(MOD_ROOT, "data/global/excel")
VANILLA_STRINGS = os.path.join(VANILLA_ROOT, "data/local/lng/strings")
MOD_STRINGS = os.path.join(MOD_ROOT, "data/local/lng/strings")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mod_config.json")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def read_excel_tsv(filename: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Read a pristine vanilla .txt table from VANILLA_EXCEL.
    Preserves exact column order and handles duplicate column names if any exist
    by returning (headers, rows_as_list_of_dicts_or_indexed).
    Note: All standard D2R excel tables have unique header names except a few legacy
    columns; we verify uniqueness and raise if duplicate headers exist so those can
    use read_excel_raw().
    """
    path = os.path.join(VANILLA_EXCEL, filename)
    with open(path, "r", encoding="utf-8", newline="") as f:
        raw = f.read()
    lines = raw.split("\r\n")
    if lines and lines[-1] == "":
        lines.pop()
    headers = lines[0].split("\t")
    if len(set(headers)) != len(headers):
        raise ValueError(f"{filename} has duplicate column headers; use read_excel_raw() instead")
    rows: List[Dict[str, str]] = []
    for idx, line in enumerate(lines[1:], start=2):
        cols = line.split("\t")
        if len(cols) != len(headers):
            raise ValueError(
                f"{filename} line {idx}: expected {len(headers)} columns, got {len(cols)}"
            )
        rows.append(dict(zip(headers, cols)))
    return headers, rows


def write_excel_tsv(filename: str, headers: List[str], rows: List[Dict[str, str]]) -> str:
    """
    Write a modified .txt table to MOD_EXCEL with strict CRLF (\\r\\n) endings
    and exact column count validation.
    """
    out_path = os.path.join(MOD_EXCEL, filename)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out_lines = ["\t".join(headers)]
    for idx, row in enumerate(rows, start=2):
        vals = [str(row.get(h, "")) for h in headers]
        if len(vals) != len(headers):
            raise ValueError(f"{filename} row {idx}: column count mismatch")
        for v in vals:
            if "\t" in v or "\n" in v or "\r" in v:
                raise ValueError(f"{filename} row {idx}: illegal tab/newline in cell {v!r}")
        out_lines.append("\t".join(vals))
    content = "\r\n".join(out_lines) + "\r\n"
    with open(out_path, "wb") as f:
        f.write(content.encode("utf-8"))
    return out_path


def read_excel_raw(filename: str) -> Tuple[List[str], List[List[str]]]:
    """Read a pristine vanilla .txt table as raw (headers, list_of_col_lists)."""
    path = os.path.join(VANILLA_EXCEL, filename)
    with open(path, "r", encoding="utf-8", newline="") as f:
        raw = f.read()
    lines = raw.split("\r\n")
    if lines and lines[-1] == "":
        lines.pop()
    headers = lines[0].split("\t")
    rows: List[List[str]] = []
    for idx, line in enumerate(lines[1:], start=2):
        cols = line.split("\t")
        if len(cols) != len(headers):
            raise ValueError(
                f"{filename} line {idx}: expected {len(headers)} columns, got {len(cols)}"
            )
        rows.append(cols)
    return headers, rows


def write_excel_raw(filename: str, headers: List[str], rows: List[List[str]]) -> str:
    """Write raw (headers, list_of_col_lists) to MOD_EXCEL with strict CRLF endings."""
    out_path = os.path.join(MOD_EXCEL, filename)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out_lines = ["\t".join(headers)]
    for idx, cols in enumerate(rows, start=2):
        if len(cols) != len(headers):
            raise ValueError(
                f"{filename} row {idx}: expected {len(headers)} columns, got {len(cols)}"
            )
        out_lines.append("\t".join(str(c) for c in cols))
    content = "\r\n".join(out_lines) + "\r\n"
    with open(out_path, "wb") as f:
        f.write(content.encode("utf-8"))
    return out_path


LANG_KEYS = [
    "enUS", "zhTW", "deDE", "esES", "frFR", "itIT",
    "koKR", "plPL", "esMX", "jaJP", "ptBR", "ruRU", "zhCN",
]


def read_strings_json(filename: str) -> List[dict]:
    """Read a pristine vanilla string JSON file from VANILLA_STRINGS."""
    path = os.path.join(VANILLA_STRINGS, filename)
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def write_strings_json(filename: str, entries: List[dict]) -> str:
    """Write a modified string JSON file to MOD_STRINGS with UTF-8 BOM and CRLF endings."""
    out_path = os.path.join(MOD_STRINGS, filename)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    text = json.dumps(entries, ensure_ascii=False, indent=2)
    text = text.replace("\r\n", "\n").replace("\n", "\r\n") + "\r\n"
    with open(out_path, "wb") as f:
        f.write(b"\xef\xbb\xbf" + text.encode("utf-8"))
    return out_path


def make_string_entry(entry_id: int, key: str, en_us: str) -> dict:
    """Create a 13-locale string entry dictionary."""
    d = {"id": entry_id, "Key": key}
    for lang in LANG_KEYS:
        d[lang] = en_us
    return d


def upsert_string_entries(entries: List[dict], updates: List[Tuple[int, str, str]]) -> List[dict]:
    """
    Update existing entries by Key (preserving their vanilla id) or append new entries
    with the specified id.
    """
    out = [dict(e) for e in entries]
    out_by_key = {e.get("Key"): e for e in out if isinstance(e, dict) and "Key" in e}
    for new_id, key, text in updates:
        if key in out_by_key:
            target = out_by_key[key]
            for lang in LANG_KEYS:
                target[lang] = text
        else:
            entry = make_string_entry(new_id, key, text)
            out.append(entry)
            out_by_key[key] = entry
    return out


def update_mod_strings_json(filename: str, updates: List[Tuple[int, str, str]]) -> str:
    """
    Read from MOD_STRINGS (if already initialized earlier in the build run) or VANILLA_STRINGS,
    upsert the given string entries, and write back to MOD_STRINGS.
    """
    mod_path = os.path.join(MOD_STRINGS, filename)
    src_path = mod_path if os.path.exists(mod_path) else os.path.join(VANILLA_STRINGS, filename)
    with open(src_path, "r", encoding="utf-8-sig") as f:
        entries = json.load(f)
    entries = upsert_string_entries(entries, updates)
    return write_strings_json(filename, entries)


def update_mod_hd_items_json(additions: List[Tuple[str, str]]) -> str:
    """
    Read data/hd/items/items.json from MOD_ROOT (if already initialized earlier in the build run)
    or VANILLA_ROOT, append any missing (code, asset) pairs, and write back to MOD_ROOT.
    """
    mod_path = os.path.join(MOD_ROOT, "data/hd/items/items.json")
    src_path = mod_path if os.path.exists(mod_path) else os.path.join(VANILLA_ROOT, "data/hd/items/items.json")
    with open(src_path, "r", encoding="utf-8") as f:
        items_list = json.load(f)

    existing_keys = set()
    for entry in items_list:
        if isinstance(entry, dict):
            existing_keys.update(entry.keys())

    for code, asset in additions:
        if code not in existing_keys:
            items_list.append({code: {"asset": asset}})
            existing_keys.add(code)

    os.makedirs(os.path.dirname(mod_path), exist_ok=True)
    text = json.dumps(items_list, indent=2)
    text = text.replace("\r\n", "\n").replace("\n", "\r\n") + "\r\n"
    with open(mod_path, "wb") as f:
        f.write(text.encode("utf-8"))
    return mod_path



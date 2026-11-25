"""
doc_gen.py
Auto-generates the live 30-skill spec & mechanics reference section inside
`docs/classes/<class>.md` directly from each class's declarative registry,
JSON specs, and compiled mod tables (`skills.txt`, `skilldesc.txt`, `skills.json`).

Eliminates documentation drift: every time `d2r-build-mod.py skills` runs,
the `<!-- AUTO-GENERATED-SPECS:START --> ... <!-- AUTO-GENERATED-SPECS:END -->`
block in each class doc is regenerated deterministically.
"""
import csv
import importlib
import json
import os
import re
from typing import Dict, List, Tuple

from mod_builder.common import MOD_EXCEL, MOD_STRINGS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

START_MARKER = "<!-- AUTO-GENERATED-SPECS:START -->"
END_MARKER = "<!-- AUTO-GENERATED-SPECS:END -->"

CLASSES = ("paladin", "barbarian", "assassin", "sorceress")


def _read_tsv(path: str, key_col: str) -> Dict[str, Dict[str, str]]:
    with open(path, encoding="latin-1") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    return {r[key_col]: r for r in rows if r.get(key_col)}


def _read_strings(path: str) -> Dict[str, str]:
    with open(path, encoding="utf-8-sig") as f:
        entries = json.load(f)
    return {e["Key"]: e.get("enUS", "") for e in entries if e.get("Key")}


def _clean_desc(text: str) -> str:
    if not text:
        return ""
    # Strip D2R color codes (ÿc0..ÿc;) and collapse newlines/pipes for markdown table cells
    s = re.sub(r"ÿc.", "", text)
    s = " / ".join(line.strip() for line in s.splitlines() if line.strip())
    s = s.replace("|", "\\|")
    if len(s) > 180:
        s = s[:177].rstrip() + "..."
    return s


def _mechanics_summary(srow: Dict[str, str], sspec: dict) -> str:
    parts: List[str] = []
    srvst = srow.get("srvstfunc", "")
    srvdo = srow.get("srvdofunc", "")
    if srvst or srvdo:
        parts.append(f"`func {srvst or '-'}/{srvdo or '-'}`")
    delay = srow.get("localdelay", "")
    if delay and delay.isdigit() and int(delay) > 0:
        sec = int(delay) / 25.0
        parts.append(f"`CD {sec:g}s`")
    if srow.get("aura") == "1":
        parts.append("`aura`")
    if srow.get("passive") == "1":
        parts.append("`passive`")
    if srow.get("finishing") == "1":
        parts.append("`finisher`")
    if srow.get("restrict") == "2" and srow.get("State1"):
        parts.append(f"`req:{srow['State1']}`")
    astate = srow.get("aurastate") or srow.get("auratargetstate")
    if astate:
        parts.append(f"`state:{astate}`")
    etype = srow.get("EType", "")
    if etype:
        parts.append(f"`{etype}`")
    rflags = srow.get("ResultFlags", "")
    if "ResultFlags" in sspec.get("tables", {}).get("skills.txt", {}).get(srow.get("skill", ""), {}):
        parts.append(f"`RF:{rflags or 'none'}`")
    # Flag Stun Fatigue / Conduction integration automatically from formulas
    all_calcs = " ".join(
        srow.get(c, "")
        for c in ("calc1", "calc2", "calc3", "calc4", "calc5", "calc6", "auralencalc", "aurarangecalc")
    )
    if "shortparam1" in all_calcs:
        parts.append("`StunFatigue`")
    if "target0" in all_calcs or "target1" in all_calcs or "goldlost" in all_calcs:
        parts.append("`Conduction`")
    return " ".join(parts) if parts else "—"


def render_auto_section(
    cls_key: str,
    skills_by_name: Dict[str, Dict[str, str]],
    desc_by_name: Dict[str, Dict[str, str]],
    strings_by_key: Dict[str, str],
) -> str:
    eng = importlib.import_module(f"mod_builder.classes.{cls_key}.engine")
    reg = importlib.import_module(f"mod_builder.classes.{cls_key}.registry")
    state = eng.load_state()

    done_count = sum(1 for s in reg.SLOTS if eng.status_of(s["slug"], state) == "done")
    lines: List[str] = [
        START_MARKER,
        f"## Live Skill Matrix (`{done_count} / {len(reg.SLOTS)} done` — Auto-Generated from JSON Specs & Compiled Tables)",
        "",
        f"> **Do not hand-edit this section.** Generated automatically by `tools/mod_builder/classes/doc_gen.py` during `d2r-build-mod.py skills` from `tools/mod_builder/classes/{cls_key}/` and compiled `skills.txt`/`skills.json`.",
        "",
    ]

    for tree, page in reg.PAGE.items():
        lines.append(f"### {tree.title()} (Page {page})")
        lines.append("")
        lines.append("| r.c | Lvl | Skill (`slug`) | Status / Variant | Engine Hooks | In-Game Description |")
        lines.append("| :---: | :---: | :--- | :--- | :--- | :--- |")
        tree_slots = sorted(
            (s for s in reg.SLOTS if s["tree"] == tree),
            key=lambda x: (x["row"], x["col"]),
        )
        for s in tree_slots:
            slug = s["slug"]
            var = eng.active_variant(slug, state)
            st = eng.status_of(slug, state)
            spec_blk = eng.load_spec(slug)["variants"].get(var, {})
            srow = skills_by_name.get(s["vname"], {})
            drow = desc_by_name.get(srow.get("skilldesc", ""), {})
            disp_name = strings_by_key.get(drow.get("str name", ""), s["name"])
            desc_txt = _clean_desc(
                strings_by_key.get(drow.get("str long", ""))
                or strings_by_key.get(drow.get("str short", ""))
                or s.get("design", "")
            )
            hooks = _mechanics_summary(srow, spec_blk)
            lines.append(
                f"| {s['row']}.{s['col']} | {reg.slot_level(s)} | **{disp_name}** (`{slug}`) | `{st}` / `{var}` | {hooks} | {desc_txt} |"
            )
        lines.append("")

    # Shared helper skills, missiles & HD entries from _shared.json
    shared_path = eng.spec_path("_shared")
    if os.path.exists(shared_path):
        shared_var = eng.active_variant("_shared", state)
        shared_blk = eng.load_spec("_shared")["variants"].get(shared_var, {})
        tables = shared_blk.get("tables", {})
        helper_skills = sorted(tables.get("skills.txt", {}).keys())
        shared_missiles = sorted(tables.get("missiles.txt", {}).keys())
        shared_states = sorted(tables.get("states.txt", {}).keys())
        hd_missiles = sorted(shared_blk.get("hd_missiles", {}).keys())
        if helper_skills or shared_missiles or shared_states or hd_missiles:
            lines.append(f"### Shared Helpers (`specs/_shared.json` — variant `{shared_var}`)")
            lines.append("")
            if helper_skills:
                lines.append(f"- **Helper Skills (`skills.txt`):** {', '.join(f'`{k}`' for k in helper_skills)}")
            if shared_states:
                lines.append(f"- **Shared States (`states.txt`):** {', '.join(f'`{k}`' for k in shared_states)}")
            if shared_missiles:
                lines.append(f"- **Shared/Custom Missiles (`missiles.txt`):** {', '.join(f'`{k}`' for k in shared_missiles)}")
            if hd_missiles:
                lines.append(f"- **HD Missile Bindings (`missiles.json`):** {', '.join(f'`{k}`' for k in hd_missiles)}")
            lines.append("")

    lines.append(END_MARKER)
    return "\n".join(lines)


def sync_class_docs() -> List[str]:
    """Regenerate the auto-generated spec section in every declarative class doc."""
    skills_by_name = _read_tsv(os.path.join(MOD_EXCEL, "skills.txt"), "skill")
    desc_by_name = _read_tsv(os.path.join(MOD_EXCEL, "skilldesc.txt"), "skilldesc")
    strings_by_key = _read_strings(os.path.join(MOD_STRINGS, "skills.json"))

    updated: List[str] = []
    for cls_key in CLASSES:
        doc_path = os.path.join(ROOT, "docs", "classes", f"{cls_key}.md")
        if not os.path.exists(doc_path):
            continue
        auto_block = render_auto_section(cls_key, skills_by_name, desc_by_name, strings_by_key)
        with open(doc_path, encoding="utf-8") as f:
            content = f.read()
        if START_MARKER in content and END_MARKER in content:
            pattern = re.compile(
                re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
                re.DOTALL,
            )
            new_content = pattern.sub(auto_block, content, count=1)
        else:
            new_content = content.rstrip() + "\n\n---\n\n" + auto_block + "\n"
        if new_content != content:
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(new_content)
        updated.append(doc_path)
    return updated

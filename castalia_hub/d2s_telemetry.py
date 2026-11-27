"""
.d2s telemetry parser and Drop-In Starter-Kit generator for Castalia Campaign Hub.
Reuses tools/mod_builder/char_manager.py so binary D2R v105 parsing/writing stays 100% in sync.
"""
import base64
import json
import os
import struct
import sys
from typing import Dict, List, Optional, Tuple

REPO_ROOT = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from mod_builder.char_manager import (  # noqa: E402
    ID_TO_CLASS_NAME,
    ID_TO_SHORT_CODE,
    create_character_from_template,
    default_gold_for_level,
    extract_host_progress_snapshot,
    inspect_character_d2s,
    locate_sections,
    tier_template_for_level,
)

# Standard D2R class skill-id base offsets for the 30-byte `if` block
CLASS_SKILL_OFFSET: Dict[int, int] = {
    0: 6,    # Amazon (6..35)
    1: 36,   # Sorceress (36..65)
    2: 66,   # Necromancer (66..95)
    3: 96,   # Paladin (96..125)
    4: 126,  # Barbarian (126..155)
    5: 221,  # Druid (221..250)
    6: 251,  # Assassin (251..280)
}

_SKILL_NAME_CACHE: Optional[Dict[int, str]] = None
_PASSIVE_SKILL_IDS: set = set()


def _load_castalia_skill_names(d2r_game_dir: Optional[str] = None) -> Dict[int, str]:
    """Load Castalia's live skill display names (and passive flags) keyed by skills.txt *Id."""
    global _SKILL_NAME_CACHE, _PASSIVE_SKILL_IDS
    if _SKILL_NAME_CACHE:
        return _SKILL_NAME_CACHE

    candidates: List[str] = []
    if d2r_game_dir:
        candidates.append(os.path.join(d2r_game_dir, "mods", "castalia", "castalia.mpq", "data"))
    candidates.append(os.path.realpath(os.path.join(REPO_ROOT, "castalia", "data")))

    mod_data = next(
        (c for c in candidates if os.path.isfile(os.path.join(c, "global", "excel", "skills.txt"))),
        "",
    )
    if not mod_data:
        return {}

    names: Dict[int, str] = {}
    skills_txt = os.path.join(mod_data, "global", "excel", "skills.txt")
    skilldesc_txt = os.path.join(mod_data, "global", "excel", "skilldesc.txt")
    skills_json = os.path.join(mod_data, "local", "lng", "strings", "skills.json")

    str_map: Dict[str, str] = {}
    if os.path.isfile(skills_json):
        try:
            with open(skills_json, "r", encoding="utf-8-sig") as f:
                for entry in json.load(f):
                    if isinstance(entry, dict) and "Key" in entry and "enUS" in entry:
                        str_map[entry["Key"]] = entry["enUS"]
        except Exception:
            pass

    desc_to_strkey: Dict[str, str] = {}
    if os.path.isfile(skilldesc_txt):
        try:
            with open(skilldesc_txt, "r", encoding="utf-8", newline="") as f:
                lines = f.read().splitlines()
            if lines:
                hdr = lines[0].split("\t")
                i_sd = hdr.index("skilldesc")
                i_sn = hdr.index("str name")
                for line in lines[1:]:
                    cols = line.split("\t")
                    if len(cols) > max(i_sd, i_sn) and cols[i_sd]:
                        desc_to_strkey[cols[i_sd].lower()] = cols[i_sn]
        except Exception:
            pass

    passives: set = set()
    if os.path.isfile(skills_txt):
        try:
            with open(skills_txt, "r", encoding="utf-8", newline="") as f:
                lines = f.read().splitlines()
            if lines:
                hdr = lines[0].split("\t")
                i_id = hdr.index("*Id")
                i_sk = hdr.index("skill")
                i_sd = hdr.index("skilldesc")
                i_pas = hdr.index("passive") if "passive" in hdr else -1
                for line in lines[1:]:
                    cols = line.split("\t")
                    if len(cols) <= max(i_id, i_sk, i_sd) or not cols[i_id].isdigit():
                        continue
                    sid = int(cols[i_id])
                    sd = cols[i_sd].lower()
                    skey = desc_to_strkey.get(sd, "")
                    display = str_map.get(skey) or cols[i_sk]
                    names[sid] = display
                    if i_pas >= 0 and len(cols) > i_pas and cols[i_pas].strip() == "1":
                        passives.add(sid)
        except Exception:
            pass

    if names:
        _SKILL_NAME_CACHE = names
        _PASSIVE_SKILL_IDS.clear()
        _PASSIVE_SKILL_IDS.update(passives)
    return names


def _detect_hell_baal_cleared(raw: bytearray) -> bool:
    """Check Woo! Hell Act 5 Quest 6 (Eve of Destruction / Baal) completion bit."""
    woo_idx = raw.find(b"Woo!")
    if woo_idx < 0:
        return False
    # Each difficulty block is 96 bytes starting at woo_idx + 10 (Normal=0, NM=1, Hell=2).
    # Act 5 Quest 6 (Baal) is word index 40 (offset 80 bytes into the 96-byte difficulty block).
    hell_baal_off = woo_idx + 10 + (2 * 96) + (40 * 2)
    if hell_baal_off + 2 > len(raw):
        return False
    word = struct.unpack_from("<H", raw, hell_baal_off)[0]
    return bool(word & 0x0001)


def _detect_horadric_cube(raw: bytearray, wp_code: str) -> bool:
    """
    Return True if the character has obtained the Horadric Cube:
      - Past Act 2 Normal (a3n+, NM, Hell), OR
      - Normal Act 2 Quest 2 (The Horadric Staff, word 10) has Bit 0 (complete), Bit 3 (Cube found), or Bit 4 set.
    """
    wp = str(wp_code or "a1n").strip().lower()
    if wp not in ("start", "a1n", "a2n"):
        return True
    woo_idx = raw.find(b"Woo!")
    if woo_idx < 0:
        return False
    q2_off = woo_idx + 10 + (10 * 2)  # Normal difficulty, quest word 10 (Horadric Staff)
    if q2_off + 2 > len(raw):
        return False
    word = struct.unpack_from("<H", raw, q2_off)[0]
    return bool(word & 0x0019)


def parse_d2s_telemetry(d2s_path: str, d2r_game_dir: Optional[str] = None) -> Dict[str, object]:
    """
    Parse a D2R v105 .d2s save and return campaign telemetry:
    char_name, char_class, class_name, char_level, char_wp, active_difficulty,
    active_act, build_summary, top_skills, hell_baal_cleared, mtime.
    """
    info = inspect_character_d2s(d2s_path)
    with open(d2s_path, "rb") as f:
        raw = bytearray(f.read())
    _, if_, jm = locate_sections(raw)
    skill_bytes = bytes(raw[if_ + 2 : jm])

    cls_id = int(info["class_id"])
    cls_short = ID_TO_SHORT_CODE.get(cls_id, "pal")
    skill_names = _load_castalia_skill_names(d2r_game_dir=d2r_game_dir)
    base_id = CLASS_SKILL_OFFSET.get(cls_id, 0)

    invested_castable: List[Tuple[int, str]] = []
    invested_all: List[Tuple[int, str]] = []
    for idx, pts in enumerate(skill_bytes[:30]):
        if pts > 0:
            sid = base_id + idx
            sname = skill_names.get(sid, f"Skill#{idx + 1}")
            invested_all.append((pts, sname))
            if sid not in _PASSIVE_SKILL_IDS:
                invested_castable.append((pts, sname))
    invested_castable.sort(key=lambda x: (-x[0], x[1]))
    invested_all.sort(key=lambda x: (-x[0], x[1]))

    chosen = invested_castable if invested_castable else invested_all
    top_skills = [{"name": n, "points": p} for p, n in chosen[:4]]
    if chosen:
        build_summary = " / ".join(n for _, n in chosen[:3])
    else:
        build_summary = "Unallocated"

    snap = extract_host_progress_snapshot(raw)
    return {
        "path": d2s_path,
        "char_name": str(info["name"]),
        "char_class": cls_short,
        "class_name": ID_TO_CLASS_NAME.get(cls_id, str(info["class_name"])),
        "char_level": int(info["level"]),
        "char_wp": str(info["wp_code"]),
        "active_difficulty": str(info["active_difficulty"]),
        "active_act": int(info["active_act"]),
        "waypoints": str(info["waypoints"]),
        "allocated_skills": int(info["allocated_skills"]),
        "skill_pts": int(info["skill_pts"]),
        "stat_pts": int(info["stat_pts"]),
        "build_summary": build_summary,
        "top_skills": top_skills,
        "hell_baal_cleared": _detect_hell_baal_cleared(raw),
        "has_cube": _detect_horadric_cube(raw, str(info["wp_code"])),
        "host_progress_b64": base64.b64encode(snap).decode("ascii") if snap else None,
        "mtime": os.path.getmtime(d2s_path),
    }


def generate_dropin_character(
    profile_dir: str,
    char_name: str,
    class_code: str,
    level: int,
    wp_code: str,
    has_cube: Optional[bool] = None,
    host_progress_b64: Optional[str] = None,
) -> Dict[str, object]:
    """Generate a Drop-In Starter-Kit .d2s character directly into a campaign profile folder."""
    clean = "".join(c for c in char_name.strip() if c.isalnum() or c in "_-")[:15]
    if not clean:
        raise ValueError("Character name must contain at least one letter or number.")
    os.makedirs(profile_dir, exist_ok=True)
    target_d2s = os.path.join(profile_dir, f"{clean}.d2s")
    if os.path.exists(target_d2s):
        raise FileExistsError(f"Character '{clean}' already exists in {profile_dir}")

    eff_level = max(1, min(99, int(level)))
    wp_norm = str(wp_code or "a1n").strip().lower()
    is_act1_normal = wp_norm in ("start", "a1n")
    # Only grant a Cube-bearing starter template if the host actually has the Horadric Cube
    # (automatically True past a2n; strictly False in a1n; gated on host telemetry in a2n).
    allow_cube = False if is_act1_normal else (
        bool(has_cube) if has_cube is not None else (wp_norm != "a2n")
    )

    if eff_level == 1:
        template_name = "default"
        inv_gold = 2000
        stash_gold = 0
    elif is_act1_normal:
        # Party is still in Act 1 Normal (no Horadric Cube yet): use default.d2s (no Cube)
        # and anchor Act 1 drop-in gold to 10,000 at Level 15 (matching real playtest economy).
        template_name = "default"
        inv_gold = 0
        stash_gold = min(10000, 2000 + (eff_level - 1) * 572)
    elif not allow_cube:
        # Party reached Act 2 Normal but host has not found the Horadric Cube yet: no Cube!
        template_name = "default"
        inv_gold = 0
        stash_gold = min(15000, 2000 + (eff_level - 1) * 650)
    else:
        template_name = None  # auto-pick tier template matching level (includes Horadric Cube)
        inv_gold = 0
        stash_gold = None

    host_progress_bytes = None
    if host_progress_b64 and eff_level > 1:
        try:
            decoded = base64.b64decode(host_progress_b64)
            if len(decoded) == 383:
                host_progress_bytes = decoded
        except Exception:
            host_progress_bytes = None

    create_character_from_template(
        clean,
        class_code,
        level=eff_level,
        wp_target=wp_code,
        host_progress_bytes=host_progress_bytes,
        stash_gold=stash_gold,
        inv_gold=inv_gold,
        template_name=template_name,
        save_dir=profile_dir,
    )
    telem = parse_d2s_telemetry(target_d2s)
    telem["starter_tier"] = template_name or tier_template_for_level(eff_level)
    telem["starter_gold"] = inv_gold if eff_level == 1 else (stash_gold if stash_gold is not None else default_gold_for_level(eff_level))
    return telem

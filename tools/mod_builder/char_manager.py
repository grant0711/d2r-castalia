#!/usr/bin/env python3
"""
char_manager.py
Multi-Class Character Save (.d2s) Generator, Respec Utility, Waypoint Unlocker,
and Starter Gold Provisioner for Castalia (D2R Overhaul Mod).

Operates on template .d2s files (in tools/char_templates/) or existing character
saves (in Saved Games/Diablo II Resurrected/mods/custom/), preserving 100% of
the character's JM item section bit-for-bit untouched while deterministically computing:
  - Class ID (0..6) & 16-byte Character Name (offset 0x12B)
  - Level (1..99) & exact Experience floor from experience.txt
  - Base Attributes (Str, Dex, Vit, Enr), Unspent Stat Points, Unspent Skill Points,
    and Life/Mana/Stamina pools from my-mod/data/global/excel/charstats.txt
  - Granular Act & Difficulty Waypoint + Quest progression (e.g. 'a1n', 'a2nm', 'a5h', 'all')
  - Completed quest reward bonuses (+1 A1, +1 A2, +2 A4 Skill Points; +20 Life & +5 Stat Points per completed A3)
  - Calibrated level-bracket Personal Stash Gold (or custom override)
  - Permanent Den of Evil respec lock & fresh 32-bit Map Seed
"""
import csv
import os
import secrets
import shutil
import struct
import zipfile
from typing import Dict, List, Optional, Tuple

from mod_builder.common import D2R_PLATFORM_ROOT, MOD_EXCEL, MOD_NAME, MOD_ROOT, REPO_ROOT, VANILLA_EXCEL

D2R_ROOT = D2R_PLATFORM_ROOT
DEFAULT_SAVE_DIR = os.path.join(
    D2R_PLATFORM_ROOT,
    f"prefixes/acct1/pfx/drive_c/users/steamuser/Saved Games/Diablo II Resurrected/mods/{MOD_NAME}",
)
TEMPLATE_DIR = os.path.join(REPO_ROOT, "tools/char_templates")


def save_dir_for_mod(mod_name: str = MOD_NAME) -> str:
    return os.path.join(
        D2R_PLATFORM_ROOT,
        f"prefixes/acct1/pfx/drive_c/users/steamuser/Saved Games/Diablo II Resurrected/mods/{mod_name}",
    )

# D2R Class IDs (byte 24 in .d2s) and charstats.txt / experience.txt row names
CLASS_INFO: Dict[str, Tuple[int, str]] = {
    "ama": (0, "Amazon"),
    "amazon": (0, "Amazon"),
    "sor": (1, "Sorceress"),
    "sorc": (1, "Sorceress"),
    "sorceress": (1, "Sorceress"),
    "nec": (2, "Necromancer"),
    "necro": (2, "Necromancer"),
    "necromancer": (2, "Necromancer"),
    "pal": (3, "Paladin"),
    "pally": (3, "Paladin"),
    "paladin": (3, "Paladin"),
    "bar": (4, "Barbarian"),
    "barb": (4, "Barbarian"),
    "barbarian": (4, "Barbarian"),
    "dru": (5, "Druid"),
    "druid": (5, "Druid"),
    "ass": (6, "Assassin"),
    "asn": (6, "Assassin"),
    "sin": (6, "Assassin"),
    "assassin": (6, "Assassin"),
}

ID_TO_CLASS_NAME: Dict[int, str] = {
    0: "Amazon",
    1: "Sorceress",
    2: "Necromancer",
    3: "Paladin",
    4: "Barbarian",
    5: "Druid",
    6: "Assassin",
    7: "Warlock",
}

ID_TO_SHORT_CODE: Dict[int, str] = {
    0: "ama",
    1: "sor",
    2: "nec",
    3: "pal",
    4: "bar",
    5: "dru",
    6: "ass",
}

# (stat id -> bit width) in the 'gf' stat section
STAT_BITS: Dict[int, int] = {
    0: 10,   # strength
    1: 10,   # energy
    2: 10,   # dexterity
    3: 10,   # vitality
    4: 10,   # statpts (unspent stat points)
    5: 8,    # newskills (unspent skill points)
    6: 21,   # hitpoints (256ths)
    7: 21,   # maxhp (256ths)
    8: 21,   # mana (256ths)
    9: 21,   # maxmana (256ths)
    10: 21,  # stamina (256ths)
    11: 21,  # maxstamina (256ths)
    12: 7,   # level
    13: 32,  # experience
    14: 25,  # gold (inventory)
    15: 25,  # goldbank (personal stash)
}

GOLD_STASH_MAX = 2_500_000


def default_gold_for_level(level: int) -> int:
    """
    Return the calibrated starter Personal Stash Gold for a character at `level`:
      - Lvl 1..9:   0 (omitted; fresh characters start with nothing)
      - Lvl 10..19: 60,000
      - Lvl 20..29: 240,000
      - Lvl 30..39: 315,000
      - Lvl 40..49: 535,000
      - Lvl 50..59: 825,000
      - Lvl 60..69: 1,240,000
      - Lvl 70+:    1,450,000
    Covers 7 player Magic vendor slots + Mercenary hire & 3 Mercenary Magic vendor slots
    + 4 extra potions + 1x Blacksmith's Malus (bml) from the Crafting (Gambling) UI.
    """
    if level < 10:
        return 0
    if level < 20:
        return 60_000
    if level < 30:
        return 240_000
    if level < 40:
        return 315_000
    if level < 50:
        return 535_000
    if level < 60:
        return 825_000
    if level < 70:
        return 1_240_000
    return 1_450_000


TIER_TEMPLATE_SLOTS: List[Tuple[str, str]] = [
    ("default", "Lvl 1-9 (4x Belt Minor Healing Potions, no Cube/Gems/Runes)"),
    ("tier1_chipped", "Lvl 10-14 (Chipped Gems/Skulls + Lvl 4-12 Runes)"),
    ("tier2_flawed", "Lvl 15-29 (Flawed Gems/Skulls + Lvl 12-26 Runes)"),
    ("tier3_normal", "Lvl 30-44 (Normal Gems/Skulls + Lvl 28-38 Runes)"),
    ("tier4_flawless", "Lvl 45-59 (Flawless Gems/Skulls + Lvl 38-52 Runes)"),
    ("tier5_perfect", "Lvl 60+ (Perfect Gems/Skulls + Lvl 48-68 Runes)"),
]


def tier_template_for_level(level: int) -> str:
    """
    Resolve which of the 5 Gem/Skull tier templates in tools/char_templates/
    corresponds to `level`:
      - Lvl 1..9:   default
      - Lvl 10..14: tier1_chipped
      - Lvl 15..29: tier2_flawed
      - Lvl 30..44: tier3_normal
      - Lvl 45..59: tier4_flawless
      - Lvl 60+:    tier5_perfect
    """
    if level < 10:
        return "default"
    if level < 15:
        return "tier1_chipped"
    if level < 30:
        return "tier2_flawed"
    if level < 45:
        return "tier3_normal"
    if level < 60:
        return "tier4_flawless"
    return "tier5_perfect"



# Cumulative waypoint counts per Act within a single difficulty (total 39 WPs):
# Act 1: 9 WPs (bits 0..8), Act 2: 9 WPs (bits 9..17), Act 3: 9 WPs (bits 18..26),
# Act 4: 3 WPs (bits 27..29), Act 5: 9 WPs (bits 30..38)
ACT_CUMULATIVE_WPS: Dict[int, int] = {
    1: 9,
    2: 18,
    3: 27,
    4: 30,
    5: 39,
}
ACT_TOWN_WP_BIT: Dict[int, int] = {
    1: 0,   # Rogue Encampment
    2: 9,   # Lut Gholein
    3: 18,  # Kurast Docks
    4: 27,  # The Pandemonium Fortress
    5: 30,  # Harrogath
}

# Authentic D2R v105 'Woo!' 16-bit quest word values for fully completed Acts 1..5
ACT_COMPLETED_QUEST_WORDS: Dict[int, Dict[int, int]] = {
    1: {
        0: 0x0001,   # Warriv Act 1 Intro
        1: 0x9001,   # Q1 Den of Evil (+1 Skill Point)
        2: 0x901D,   # Q2 Sisters' Burial Grounds (Blood Raven)
        3: 0x104D,   # Q5 Tools of the Trade (Charsi Malus)
        4: 0x9019,   # Q3 The Search for Cain (Deckard Cain rescued)
        5: 0x1015,   # Q4 The Forgotten Tower (Countess)
        6: 0x101D,   # Q6 Sisters to the Slaughter (Andariel)
        7: 0x0001,   # Traveled East to Act 2
        8: 0x0001,   # Jerhyn Act 2 Intro
    },
    2: {
        8: 0x0001,   # Jerhyn Act 2 Intro
        9: 0x1011,   # Q1 Radament's Lair (+1 Skill Point Book of Skill)
        10: 0x1C79,  # Q2 The Horadric Staff
        11: 0x9005,  # Q3 Tainted Sun
        12: 0x1181,  # Q4 Arcane Sanctuary
        13: 0x1005,  # Q5 The Summoner
        14: 0x1C25,  # Q6 The Seven Tombs (Duriel)
        15: 0x0001,  # Traveled East to Act 3
        16: 0x0001,  # Hratli Act 3 Intro
    },
    3: {
        16: 0x0001,  # Hratli Act 3 Intro
        17: 0x1001,  # Q4 Lam Esen's Tome (+5 Stat Points)
        18: 0x10FD,  # Q3 Khalim's Will
        19: 0x13F9,  # Q2 Blade of the Old Religion (Gidbinn)
        20: 0x1001,  # Q1 The Golden Bird (+20 Life Potion of Life)
        21: 0x100D,  # Q5 The Blackened Temple (Travincal Council)
        22: 0x1381,  # Q6 The Guardian (Mephisto)
        23: 0x0001,  # Stepped through Red Portal to Act 4
        24: 0x0001,  # Act 4 Intro
    },
    4: {
        24: 0x0001,  # Act 4 Intro
        25: 0x1001,  # Q1 The Fallen Angel (Izual, +2 Skill Points)
        26: 0x1201,  # Q3 Terror's End (Diablo)
        27: 0x1001,  # Q2 Hell's Forge
        28: 0x0001,  # Traveled to Harrogath (Act 5)
        32: 0x0001,  # Harrogath Act 5 Intro
    },
    5: {
        32: 0x0001,  # Harrogath Act 5 Intro
        35: 0x9021,  # Q1 Siege on Harrogath (Shenk)
        36: 0x1001,  # Q2 Rescue on Mount Arreat (Qual-Kehk)
        37: 0x178D,  # Q3 Prison of Ice (Anya + Malah's Scroll of Resistance bit 0x0080)
        38: 0x801E,  # Q4 Betrayal of Harrogath (Nihlathak)
        39: 0x1029,  # Q5 Rite of Passage (Ancients)
        40: 0x148D,  # Q6 Eve of Destruction (Baal)
    },
}


def resolve_class(cls_arg: str) -> Tuple[int, str]:
    key = cls_arg.strip().lower()
    if key not in CLASS_INFO:
        valid = sorted({k for k in CLASS_INFO if len(k) == 3})
        raise ValueError(f"Unknown class {cls_arg!r}. Valid classes: {', '.join(valid)}")
    return CLASS_INFO[key]


def parse_wp_target(wp_str: str) -> Tuple[int, int, bool]:
    """
    Parse a human-readable waypoint/progression target into (diff_idx, act_num, all_wps_in_final_act).
      - 'a1n' .. 'a5n'     -> Start at the beginning of Normal Act 1..5 (all prior Acts completed)
      - 'a1nm' .. 'a5nm'   -> Start at the beginning of Nightmare Act 1..5 (all prior Difficulties & Acts completed)
      - 'a1h' .. 'a5h'     -> Start at the beginning of Hell Act 1..5 (all prior Difficulties & Acts completed)
      - '<act><diff>-done' -> Also complete all quests & WPs inside that target Act (e.g. 'a3nm-done', 'a5n-done')
      - 'all'              -> Hell Act 5 completed (all 39 WPs across Normal, Nightmare, Hell)
      - 'start' / 'none'   -> Normal Act 1 (Rogue Encampment town WP only)
    """
    s = wp_str.strip().lower().replace(":", "").replace("-", "").replace("_", "")
    if s in ("all", "max", "hell"):
        return 2, 5, True
    if s in ("start", "none", "fresh"):
        return 0, 1, False
    if s in ("a2halls", "a2nhalls"):
        return 0, 2, False
    if s.startswith("a") and len(s) >= 3 and s[1].isdigit():
        act = int(s[1])
        if not (1 <= act <= 5):
            raise ValueError(f"Invalid Act number in waypoint target {wp_str!r} (must be 1..5)")
        diff_part = s[2:]
        complete_final = False
        for sfx, val in (("done", True), ("full", True), ("start", False)):
            if diff_part.endswith(sfx):
                complete_final = val
                diff_part = diff_part[: -len(sfx)] or "n"
                break
        if diff_part in ("n", "norm", "normal"):
            return 0, act, complete_final
        if diff_part in ("nm", "nightmare"):
            return 1, act, complete_final
        if diff_part in ("h", "hell"):
            return 2, act, complete_final
    raise ValueError(
        f"Invalid --wp target {wp_str!r}. Examples: 'start', 'a1n'..'a5n', 'a1nm'..'a5nm', 'a1h'..'a5h', 'a3nm-done', 'all'"
    )


def calc_d2s_checksum(buf: bytearray) -> int:
    b = bytearray(buf)
    b[12:16] = b"\x00\x00\x00\x00"
    csum = 0
    for byte in b:
        csum = (((csum << 1) & 0xFFFFFFFF) | (csum >> 31))
        csum = (csum + byte) & 0xFFFFFFFF
    return csum


def encode_gf(stats: Dict[int, int]) -> bytes:
    bits: List[str] = []
    for sid in sorted(stats):
        bits.append(f"{sid:09b}"[::-1])
        bits.append(f"{stats[sid]:0{STAT_BITS[sid]}b}"[::-1])
    bits.append("1" * 9)
    s = "".join(bits)
    s += "0" * ((8 - len(s) % 8) % 8)
    return bytes(int(s[i : i + 8][::-1], 2) for i in range(0, len(s), 8))


def decode_gf(data: bytes) -> Dict[int, int]:
    bits = "".join(f"{byte:08b}"[::-1] for byte in data)
    pos = 0
    stats: Dict[int, int] = {}
    while pos + 9 <= len(bits):
        sid = int(bits[pos : pos + 9][::-1], 2)
        pos += 9
        if sid == 0x1FF:
            break
        if sid not in STAT_BITS:
            raise RuntimeError(f"Unexpected stat id {sid} in gf section")
        n = STAT_BITS[sid]
        stats[sid] = int(bits[pos : pos + n][::-1], 2)
        pos += n
    return stats


def locate_sections(raw: bytearray) -> Tuple[int, int, int]:
    gf = raw.find(b"gf")
    if_ = raw.find(b"if", gf)
    jm = raw.find(b"JM", if_)
    if gf == -1 or if_ == -1 or jm == -1 or (jm - if_) != 32:
        raise RuntimeError(f"Unexpected gf/if/JM layout ({gf}, {if_}, {jm})")
    return gf, if_, jm


def load_charstats_row(class_row_name: str) -> Dict[str, str]:
    for root in (MOD_EXCEL, VANILLA_EXCEL):
        path = os.path.join(root, "charstats.txt")
        if os.path.exists(path):
            break
    with open(path, encoding="latin-1") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    head = rows[0]
    for r in rows[1:]:
        if r and r[0] == class_row_name:
            return {k: r[head.index(k)] for k in head if k and head.index(k) < len(r)}
    raise RuntimeError(f"{class_row_name!r} not found in {path}")


def exp_for_level(class_row_name: str, level: int) -> int:
    if level <= 1:
        return 0
    for root in (MOD_EXCEL, VANILLA_EXCEL):
        path = os.path.join(root, "experience.txt")
        if os.path.exists(path):
            break
    with open(path, encoding="latin-1") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    head = rows[0]
    col = head.index(class_row_name)
    for r in rows[1:]:
        if r and r[0] == str(level - 1):
            return int(r[col])
    return 0


def set_name_and_class(raw: bytearray, char_name: str, class_id: Optional[int] = None) -> None:
    clean_name = char_name.strip()[:15]
    name_bytes = clean_name.encode("ascii", errors="ignore").ljust(16, b"\x00")
    raw[0x12B : 0x12B + 16] = name_bytes
    if class_id is not None and raw[24] != class_id:
        raw[24] = class_id


def apply_waypoints_and_quests(raw: bytearray, wp_target: str) -> None:
    """
    Configure Woo! quest progression and WS waypoint bitfields up to `wp_target`
    ('start', 'a1n'..'a5n', 'a1nm'..'a5nm', 'a1h'..'a5h', 'all'), and permanently
    lock Akara's Den of Evil respec across all 3 difficulties.
    """
    target_diff, target_act, full_final_act = parse_wp_target(wp_target)

    # 1. Set D2R v105 progression byte at offset 21 (0x15) so the Character Select
    #    screen immediately prompts for Normal / Nightmare / Hell difficulty on the first click:
    #    0..4 = Normal only, 5..9 = Nightmare unlocked, 10..15 = Hell unlocked
    prog_val = min(15, target_diff * 5 + (target_act if full_final_act else max(0, target_act - 1)))
    if target_diff == 2 and target_act == 5 and full_final_act:
        prog_val = 15
    raw[21] = prog_val
    raw[26] = 0x1E

    # 2. Set active difficulty & arrival town Act at offsets 152..154 (0x98..0x9A: [Normal, Nightmare, Hell])
    #    Bit 7 (0x80) = active difficulty; bits 0..2 = current town Act (0=Act 1 .. 4=Act 5)
    arrival_act_idx = min(4, target_act if full_final_act else max(0, target_act - 1))
    raw[152:155] = b"\x00\x00\x00"
    raw[152 + target_diff] = 0x80 | arrival_act_idx

    woo = raw.find(b"Woo!")
    if woo != -1:
        for diff in range(3):
            base = woo + 10 + diff * 96
            for idx in range(48):
                struct.pack_into("<H", raw, base + idx * 2, 0)

            if diff <= target_diff:
                max_act = 5 if diff < target_diff else target_act
                complete_final = True if diff < target_diff else full_final_act
                completed_upto = max_act if complete_final else (max_act - 1)
                words_to_set: Dict[int, int] = {0: 0x0001}
                for act_i in range(1, completed_upto + 1):
                    words_to_set.update(ACT_COMPLETED_QUEST_WORDS[act_i])
                for idx, val in words_to_set.items():
                    cur = struct.unpack_from("<H", raw, base + idx * 2)[0]
                    struct.pack_into("<H", raw, base + idx * 2, cur | val)

            q41 = struct.unpack_from("<H", raw, base + 41 * 2)[0]
            struct.pack_into("<H", raw, base + 41 * 2, (q41 | 0x8001) & ~0x0002)

    ws = raw.find(b"WS", woo if woo != -1 else 0)
    if ws != -1:
        for diff in range(3):
            off = ws + 8 + diff * 24
            if diff > target_diff:
                mask = 1
            elif diff < target_diff:
                mask = (1 << 39) - 1
            else:
                if not full_final_act and target_act == 1:
                    mask = 1
                elif full_final_act:
                    num_wps = ACT_CUMULATIVE_WPS[target_act]
                    mask = (1 << num_wps) - 1
                    # Also unlock the arrival town waypoint of the next Act (e.g. Kurast Docks bit 18 after completing Act 2)
                    if target_act < 5:
                        mask |= 1 << ACT_TOWN_WP_BIT[target_act + 1]
                else:
                    prev_wps = ACT_CUMULATIVE_WPS.get(target_act - 1, 0)
                    town_bit = ACT_TOWN_WP_BIT[target_act]
                    mask = ((1 << prev_wps) - 1) | (1 << town_bit)
                    if "halls" in wp_target.lower() and target_act == 2:
                        mask |= (1 << 11) | (1 << 12)  # Dry Hills (11) & Halls of the Dead Level 2 (12)
            mask_bytes = mask.to_bytes(5, byteorder="little")
            raw[off : off + 7] = b"\x02\x01" + mask_bytes


def compute_completed_quest_bonuses(raw: bytes) -> Tuple[int, int, int]:
    """
    Inspect the 'Woo!' quest section across Normal, Nightmare, and Hell and return
    (quest_skill_pts, quest_stat_pts, quest_life_bonus):
      - Act 1 Q1 Den of Evil (word 1 & 1):       +1 Skill Point
      - Act 2 Q1 Radament's Lair (word 9 & 1):   +1 Skill Point
      - Act 3 Q4 Lam Esen's Tome (word 17 & 1):  +5 Stat Points
      - Act 3 Q1 The Golden Bird (word 20 & 1):  +20 Life
      - Act 4 Q1 The Fallen Angel (word 25 & 1): +2 Skill Points
    """
    woo = raw.find(b"Woo!")
    if woo == -1:
        return 0, 0, 0
    sk_pts = 0
    st_pts = 0
    life_bonus = 0
    for diff in range(3):
        base = woo + 10 + diff * 96
        w1 = struct.unpack_from("<H", raw, base + 1 * 2)[0]
        w9 = struct.unpack_from("<H", raw, base + 9 * 2)[0]
        w17 = struct.unpack_from("<H", raw, base + 17 * 2)[0]
        w20 = struct.unpack_from("<H", raw, base + 20 * 2)[0]
        w25 = struct.unpack_from("<H", raw, base + 25 * 2)[0]
        if w1 & 0x0001:
            sk_pts += 1
        if w9 & 0x0001:
            sk_pts += 1
        if w17 & 0x0001:
            st_pts += 5
        if w20 & 0x0001:
            life_bonus += 20
        if w25 & 0x0001:
            sk_pts += 2
    return sk_pts, st_pts, life_bonus


def describe_wp_progress(raw: bytes) -> str:
    woo = raw.find(b"Woo!")
    ws = raw.find(b"WS", woo if woo != -1 else 0)
    if ws == -1:
        return "?"
    diff_labels = ("N", "NM", "H")
    parts = []
    for diff in range(3):
        off = ws + 8 + diff * 24
        mask = int.from_bytes(raw[off + 2 : off + 7], byteorder="little") & ((1 << 39) - 1)
        count = bin(mask).count("1")
        if count > 1 or diff == 0:
            parts.append(f"{diff_labels[diff]}:{count}/39")
    return " ".join(parts)


def extract_host_progress_snapshot(raw: bytes) -> Optional[bytes]:
    """
    Extract a compact 383-byte snapshot of a host character's exact quest & waypoint state:
      - byte 0:        raw[0x15] (D2R v105 difficulty progression byte)
      - bytes 1..4:    raw[0x98:0x9B] (Normal/NM/Hell active act & difficulty flags, offsets 152..154)
      - bytes 4..302:  Woo! quest section (298 bytes)
      - bytes 302..383: WS waypoint section (81 bytes)
    """
    woo = raw.find(b"Woo!")
    ws = raw.find(b"WS", woo if woo >= 0 else 0)
    if woo < 0 or ws < 0 or ws - woo != 298 or ws + 81 > len(raw):
        return None
    return bytes([raw[0x15]]) + bytes(raw[0x98:0x9B]) + bytes(raw[woo : woo + 298]) + bytes(raw[ws : ws + 81])


def apply_host_progress_snapshot(raw: bytearray, snapshot: bytes) -> None:
    """Overlay a 383-byte host quest & waypoint snapshot onto a freshly created Drop-In .d2s."""
    if not snapshot or len(snapshot) != 383:
        raise ValueError(f"Invalid host_progress_bytes length: {len(snapshot) if snapshot else 0} (expected 383)")
    woo_blob = snapshot[4:302]
    ws_blob = snapshot[302:383]
    if not woo_blob.startswith(b"Woo!") or not ws_blob.startswith(b"WS"):
        raise ValueError("Invalid host_progress_bytes headers (missing Woo! or WS)")
    woo = raw.find(b"Woo!")
    ws = raw.find(b"WS", woo if woo >= 0 else 0)
    if woo < 0 or ws < 0 or ws - woo != 298 or ws + 81 > len(raw):
        raise ValueError("Target .d2s missing standard 298-byte Woo! / 81-byte WS layout")
    raw[0x15] = snapshot[0]
    raw[0x98:0x9B] = snapshot[1:4]
    raw[woo : woo + 298] = woo_blob
    raw[ws : ws + 81] = ws_blob


def configure_character_d2s(
    d2s_path: str,
    *,
    char_name: Optional[str] = None,
    class_id: Optional[int] = None,
    level: Optional[int] = None,
    wp_target: Optional[str] = None,
    host_progress_bytes: Optional[bytes] = None,
    reset_skills: bool = True,
    reset_stats: bool = True,
    stash_gold: Optional[int] = None,
    inv_gold: Optional[int] = None,
    reroll_seed: bool = True,
) -> Dict[str, object]:
    """
    Modify a .d2s character save in-place while preserving its JM item section 100% bit-for-bit untouched.
    """
    with open(d2s_path, "rb") as f:
        raw = bytearray(f.read())

    gf, if_, jm = locate_sections(raw)
    stats = decode_gf(bytes(raw[gf + 2 : if_]))

    if char_name is not None or class_id is not None:
        eff_name = char_name if char_name is not None else os.path.splitext(os.path.basename(d2s_path))[0]
        set_name_and_class(raw, eff_name, class_id)

    eff_class_id = raw[24]
    class_row_name = ID_TO_CLASS_NAME.get(eff_class_id, "Sorceress")
    cs = load_charstats_row(class_row_name)

    eff_level = max(1, min(99, level if level is not None else stats.get(12, raw[27])))
    if level is not None:
        raw[27] = eff_level
        if raw[43] != 0:
            raw[43] = eff_level
        stats[12] = eff_level
        stats[13] = exp_for_level(class_row_name, eff_level)

    if host_progress_bytes is not None:
        apply_host_progress_snapshot(raw, host_progress_bytes)
    elif wp_target is not None:
        apply_waypoints_and_quests(raw, wp_target)

    q_skill_pts, q_stat_pts, q_life_bonus = compute_completed_quest_bonuses(raw)

    per_lvl = lambda key: int(cs[key]) / 4.0
    fixed = lambda v: int(round(v * 256))

    if reset_stats or level is not None or wp_target is not None:
        stats[0] = int(cs["str"])
        stats[1] = int(cs["int"])
        stats[2] = int(cs["dex"])
        stats[3] = int(cs["vit"])
        stat_pts = (eff_level - 1) * int(cs["StatPerLevel"]) + q_stat_pts
        if stat_pts > 0:
            stats[4] = stat_pts
        else:
            stats.pop(4, None)
        life = int(cs["hpadd"]) + int(cs["vit"]) + (eff_level - 1) * per_lvl("LifePerLevel") + q_life_bonus
        mana = int(cs["int"]) + (eff_level - 1) * per_lvl("ManaPerLevel")
        stam = int(cs["stamina"]) + (eff_level - 1) * per_lvl("StaminaPerLevel")
        stats.update(
            {
                6: fixed(life),
                7: fixed(life),
                8: fixed(mana),
                9: fixed(mana),
                10: fixed(stam),
                11: fixed(stam),
            }
        )

    skill_Alloc = bytearray(raw[if_ + 2 : jm])
    if reset_skills:
        skill_Alloc = bytearray(30)
        sk_pts = min(255, (eff_level - 1) * int(cs["SkillsPerLevel"]) + q_skill_pts)
        if sk_pts > 0:
            stats[5] = sk_pts
        else:
            stats.pop(5, None)

    if stash_gold is not None:
        sg = max(0, min(GOLD_STASH_MAX, int(stash_gold)))
        if sg > 0:
            stats[15] = sg
        else:
            stats.pop(15, None)

    if inv_gold is not None:
        ig = max(0, min(eff_level * 10_000, int(inv_gold)))
        if ig > 0:
            stats[14] = ig
        else:
            stats.pop(14, None)

    if reroll_seed:
        woo = raw.find(b"Woo!")
        if woo >= 248:
            seed_off = 155 if woo == 403 else (woo - 162)
            struct.pack_into("<I", raw, seed_off, secrets.randbelow(0x7FFFFFFE) + 1)

    rebuilt = raw[:gf] + b"gf" + encode_gf(stats) + b"if" + bytes(skill_Alloc) + raw[jm:]
    struct.pack_into("<I", rebuilt, 8, len(rebuilt))
    csum = calc_d2s_checksum(rebuilt)
    struct.pack_into("<I", rebuilt, 12, csum)

    with open(d2s_path, "wb") as f:
        f.write(rebuilt)

    base_no_ext = os.path.splitext(d2s_path)[0]
    for ext in (".d2rl", ".map", ".ma0", ".ma1", ".ma2", ".ma3"):
        p = base_no_ext + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass

    jm_items = struct.unpack_from("<H", rebuilt, rebuilt.find(b"JM", rebuilt.find(b"if")) + 2)[0]
    return {
        "path": d2s_path,
        "name": rebuilt[0x12B : 0x12B + 16].split(b"\x00")[0].decode("ascii", "ignore"),
        "class_id": eff_class_id,
        "class_name": class_row_name,
        "level": stats.get(12, eff_level),
        "stat_pts": stats.get(4, 0),
        "skill_pts": stats.get(5, 0),
        "life": stats.get(7, 0) / 256.0,
        "mana": stats.get(9, 0) / 256.0,
        "stamina": stats.get(11, 0) / 256.0,
        "inv_gold": stats.get(14, 0),
        "stash_gold": stats.get(15, 0),
        "waypoints": describe_wp_progress(rebuilt),
        "items": jm_items,
        "checksum": f"0x{csum:08X}",
    }


def inspect_character_d2s(d2s_path: str) -> Dict[str, object]:
    with open(d2s_path, "rb") as f:
        raw = bytearray(f.read())
    gf, if_, jm = locate_sections(raw)
    stats = decode_gf(bytes(raw[gf + 2 : if_]))
    cls_id = raw[24]
    cls_name = ID_TO_CLASS_NAME.get(cls_id, f"Class{cls_id}")
    name = raw[0x12B : 0x12B + 16].split(b"\x00")[0].decode("ascii", "ignore") or os.path.splitext(os.path.basename(d2s_path))[0]
    allocated_skills = sum(raw[if_ + 2 : jm])
    jm_items = struct.unpack_from("<H", raw, jm + 2)[0]

    active_diff_idx = 0
    active_act_num = 1
    for d_idx in range(3):
        b = raw[152 + d_idx]
        if b & 0x80:
            active_diff_idx = d_idx
            active_act_num = min(5, (b & 0x07) + 1)
            break
    diff_names = ("Normal", "Nightmare", "Hell")
    diff_codes = ("n", "nm", "h")
    return {
        "path": d2s_path,
        "name": name,
        "class_id": cls_id,
        "class_name": cls_name,
        "level": stats.get(12, raw[27]),
        "stat_pts": stats.get(4, 0),
        "skill_pts": stats.get(5, 0),
        "allocated_skills": allocated_skills,
        "life": stats.get(7, 0) / 256.0,
        "mana": stats.get(9, 0) / 256.0,
        "stamina": stats.get(11, 0) / 256.0,
        "inv_gold": stats.get(14, 0),
        "stash_gold": stats.get(15, 0),
        "waypoints": describe_wp_progress(raw),
        "active_difficulty": diff_names[active_diff_idx],
        "active_act": active_act_num,
        "wp_code": f"a{active_act_num}{diff_codes[active_diff_idx]}",
        "items": jm_items,
    }


def create_character_from_template(
    char_name: str,
    class_arg: str,
    *,
    level: int = 1,
    wp_target: str = "start",
    host_progress_bytes: Optional[bytes] = None,
    stash_gold: Optional[int] = None,
    inv_gold: int = 0,
    template_name: Optional[str] = None,
    save_dir: str = DEFAULT_SAVE_DIR,
    export_path: Optional[str] = None,
) -> Dict[str, object]:
    """
    Create a new character save <CHAR_NAME>.d2s in `save_dir` from a template .d2s in
    `tools/char_templates/` (preferring tier template matching `level`, or `default.d2s`),
    then configure its class, level, pools, points, level-bracket gold, quests, and waypoints
    while leaving its JM item section 100% untouched.
    """
    cls_id, _ = resolve_class(class_arg)
    short_code = ID_TO_SHORT_CODE[cls_id]
    os.makedirs(save_dir, exist_ok=True)

    candidates = []
    if template_name:
        candidates.append(os.path.join(TEMPLATE_DIR, f"{template_name}.d2s"))
    tier_tmpl = tier_template_for_level(level)
    if tier_tmpl != "default":
        candidates.append(os.path.join(TEMPLATE_DIR, f"{tier_tmpl}.d2s"))
    candidates.append(os.path.join(TEMPLATE_DIR, f"{short_code}.d2s"))
    candidates.append(os.path.join(TEMPLATE_DIR, "default.d2s"))

    src_d2s = next((p for p in candidates if os.path.exists(p)), None)
    if not src_d2s:
        raise FileNotFoundError(f"No character template found in {TEMPLATE_DIR} (checked {candidates})")

    clean_name = char_name.strip()[:15]
    dst_d2s = os.path.join(save_dir, f"{clean_name}.d2s")
    shutil.copy2(src_d2s, dst_d2s)

    for ext in (".key", ".ctl"):
        src_side = os.path.splitext(src_d2s)[0] + ext
        dst_side = os.path.join(save_dir, f"{clean_name}{ext}")
        if os.path.exists(src_side) and not os.path.exists(dst_side):
            shutil.copy2(src_side, dst_side)

    eff_stash_gold = stash_gold if stash_gold is not None else default_gold_for_level(level)

    summary = configure_character_d2s(
        dst_d2s,
        char_name=clean_name,
        class_id=cls_id,
        level=level,
        wp_target=wp_target,
        host_progress_bytes=host_progress_bytes,
        reset_skills=True,
        reset_stats=True,
        stash_gold=eff_stash_gold,
        inv_gold=inv_gold,
        reroll_seed=True,
    )
    summary["template_used"] = os.path.basename(src_d2s)

    if export_path:
        exp_abs = os.path.abspath(export_path)
        if exp_abs.endswith(".zip"):
            os.makedirs(os.path.dirname(exp_abs), exist_ok=True)
            with zipfile.ZipFile(exp_abs, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(dst_d2s, arcname=os.path.basename(dst_d2s))
                for ext in (".key", ".ctl"):
                    sp = os.path.join(save_dir, f"{clean_name}{ext}")
                    if os.path.exists(sp):
                        zf.write(sp, arcname=os.path.basename(sp))
        else:
            os.makedirs(exp_abs, exist_ok=True)
            shutil.copy2(dst_d2s, os.path.join(exp_abs, os.path.basename(dst_d2s)))
            for ext in (".key", ".ctl"):
                sp = os.path.join(save_dir, f"{clean_name}{ext}")
                if os.path.exists(sp):
                    shutil.copy2(sp, os.path.join(exp_abs, os.path.basename(sp)))
        summary["exported_to"] = exp_abs

    return summary

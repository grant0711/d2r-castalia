#!/usr/bin/env python3
"""
lockboxes.py
Shared deterministic registry and HD .sprite builder for the 3-Tier Lockbox & Key system:
- Tier 1 (Normal, lvl 1-36):
    Box: "Crude Wooden Lockbox"     (2x2, asset: herb/herb)
    Key: "Crude Lockbox Key" (key)  (1x1, cost: 1,000g, asset: key/skeleton_key)
- Tier 2 (Nightmare, lvl 37-64):
    Box: "Reinforced Iron Lockbox"  (2x2, asset: torch/torch)
    Key: "Iron Lockbox Key" (ky2)   (1x1, cost: 5,000g, asset: body_part/jawbone)
- Tier 3 (Hell, lvl 65+):
    Box: "Ornate Gilded Lockbox"    (2x2, asset: quest/scroll_of_self_resurrect)
    Key: "Ornate Lockbox Key" (ky3) (1x1, cost: 10,000g, asset: body_part/horn)

Every spawnable Unique (401) and Set (135) item in the mod gets its own deterministic
3-character item code in misc.txt (536 total Lockbox codes). All codes in Tier 1 display
as "Crude Wooden Lockbox", Tier 2 as "Reinforced Iron Lockbox", and Tier 3 as "Ornate Gilded Lockbox".
"""
import csv
import os
import struct
import subprocess
from collections import deque
from typing import Dict, List, Set, Tuple

from mod_builder.common import MOD_EXCEL, MOD_ROOT, VANILLA_EXCEL, read_excel_tsv

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

LOCKBOX_TIER_INFO = {
    1: {
        "box_name": "Crude Wooden Lockbox",
        "box_display_name": "ÿc4Crude Wooden Lockbox",
        "box_asset": "herb/herb",
        "box_img": "lockbox_normal.jpg",
        "box_sound": "item_metalshield",
        "key_code": "key",
        "key_name": "Crude Lockbox Key",
        "key_cost": "5000",
        "key_asset": "key/skeleton_key",
        "key_img": "key_normal.jpg",
    },
    2: {
        "box_name": "Reinforced Iron Lockbox",
        "box_display_name": "ÿc4Reinforced Iron Lockbox",
        "box_asset": "torch/torch",
        "box_img": "lockbox_nightmare.jpg",
        "box_sound": "item_metalshield",
        "key_code": "ky2",
        "key_name": "Iron Lockbox Key",
        "key_cost": "25000",
        "key_asset": "body_part/jawbone",
        "key_img": "key_nightmare.jpg",
    },
    3: {
        "box_name": "Ornate Gilded Lockbox",
        "box_display_name": "ÿc4Ornate Gilded Lockbox",
        "box_asset": "quest/scroll_of_self_resurrect",
        "box_img": "lockbox_hell.jpg",
        "box_sound": "item_metalshield",
        "key_code": "ky3",
        "key_name": "Ornate Lockbox Key",
        "key_cost": "50000",
        "key_asset": "body_part/horn",
        "key_img": "key_hell.jpg",
    },
}

ACT_LEVEL_BANDS: List[Tuple[str, int, int, int]] = [
    # (act_prefix, tier, min_lvl, max_lvl)
    ("Act 1", 1, 1, 11),
    ("Act 2", 1, 12, 18),
    ("Act 3", 1, 19, 24),
    ("Act 4", 1, 25, 30),
    ("Act 5", 1, 31, 36),
    ("Act 1 (N)", 2, 37, 42),
    ("Act 2 (N)", 2, 43, 48),
    ("Act 3 (N)", 2, 49, 53),
    ("Act 4 (N)", 2, 54, 58),
    ("Act 5 (N)", 2, 59, 64),
    ("Act 1 (H)", 3, 65, 69),
    ("Act 2 (H)", 3, 70, 73),
    ("Act 3 (H)", 3, 74, 77),
    ("Act 4 (H)", 3, 78, 81),
    ("Act 5 (H)", 3, 82, 999),
]


def _read_mod_or_vanilla_tsv(filename: str) -> List[Dict[str, str]]:
    mod_path = os.path.join(MOD_EXCEL, filename)
    path = mod_path if os.path.exists(mod_path) else os.path.join(VANILLA_EXCEL, filename)
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _get_reserved_codes() -> Set[str]:
    reserved: Set[str] = {
        "wm2", "wm3", "yp2", "yp3", "vp2", "vp3",
        "bml", "bm2", "bm3", "ky0", "ky1", "ky2", "ky3",
        "vk1", "vk2", "vk3", "vk4",
        "sw1", "sw2", "sw3", "sw4",
        "va1", "va2", "va3", "va4",
        "xxx", "any", "all",
    }
    for fn, col in (
        ("weapons.txt", "code"),
        ("armor.txt", "code"),
        ("misc.txt", "code"),
        ("itemtypes.txt", "Code"),
    ):
        _, rows = read_excel_tsv(fn)
        for r in rows:
            c = r.get(col, "").strip()
            if c:
                reserved.add(c)
    return reserved


def _generate_box_codes(count: int, reserved: Set[str]) -> List[str]:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    codes: List[str] = []
    for p in ("z", "y", "q"):
        for c1 in chars:
            for c2 in chars:
                cand = f"{p}{c1}{c2}"
                if cand not in reserved:
                    codes.append(cand)
                    if len(codes) == count:
                        return codes
    raise RuntimeError(f"Could not generate {count} unique lockbox codes")


def _act_for_level(eff_lvl: int) -> Tuple[str, int]:
    for act_prefix, tier, lo, hi in ACT_LEVEL_BANDS:
        if lo <= eff_lvl <= hi:
            return act_prefix, tier
    return "Act 5 (H)", 3


def get_lockbox_registry() -> List[Dict[str, object]]:
    """
    Return the deterministic list of Lockbox definitions across all spawnable Uniques & Sets.
    Each dict contains:
      - code: 3-char item code in misc.txt (e.g. 'z00')
      - index: exact UniqueItems.txt or SetItems.txt 'index' string
      - base_code: underlying weapon/armor/misc item code (e.g. 'hax', 'rin')
      - is_unique: True for Unique, False for Set
      - eff_lvl: effective quality level (1..99)
      - tier: 1 (Normal 1-36), 2 (Nightmare 37-64), or 3 (Hell 65+)
      - act_prefix: 'Act 1' .. 'Act 5 (H)'
      - weight: integer drop weight inside its Act Lockbox Pool
      - box_name: UI string ('Crude Wooden Lockbox' / 'Reinforced Iron Lockbox' / 'Ornate Gilded Lockbox')
      - box_asset: HD asset path for items.json
      - key_code: paired key code ('key', 'ky2', or 'ky3')
    """
    base_lvl: Dict[str, int] = {}
    for fn in ("weapons.txt", "armor.txt", "misc.txt"):
        for r in _read_mod_or_vanilla_tsv(fn):
            c = r.get("code", "").strip()
            if c:
                base_lvl[c] = int(r.get("level") or "1")

    skip_base_codes = {
        "cm1", "cm2", "cm3", "cs2",
        "vip", "hst", "msf", "bks", "bkd", "hfh", "qf1", "qf2",
    }

    u_rows = _read_mod_or_vanilla_tsv("uniqueitems.txt")
    s_rows = _read_mod_or_vanilla_tsv("setitems.txt")

    raw_items: List[Tuple[str, str, bool, int, int]] = []
    for r in u_rows:
        idx = r.get("index", "").strip()
        bcode = r.get("code", "").strip()
        if not idx or not bcode or bcode in skip_base_codes:
            continue
        if r.get("disabled") == "1" or r.get("spawnable") != "1":
            continue
        lvl = int(r.get("lvl") or "1")
        lreq = int(r.get("lvl req") or "1")
        eff_lvl = max(lvl, lreq, base_lvl.get(bcode, 1))
        rarity = max(1, min(10, int(r.get("rarity") or "1")))
        # Uniques get 2x base weight multiplier relative to Sets so Uniques are the primary prize
        raw_items.append((idx, bcode, True, eff_lvl, rarity * 2))

    for r in s_rows:
        idx = r.get("index", "").strip()
        bcode = r.get("item", "").strip()
        if not idx or not bcode or bcode in skip_base_codes:
            continue
        lvl = int(r.get("lvl") or "1")
        if lvl >= 100:
            # Skip disabled/unused Warlord's rows (lvl=100)
            continue
        lreq = int(r.get("lvl req") or "1")
        eff_lvl = max(lvl, lreq, base_lvl.get(bcode, 1))
        rarity = max(1, min(10, int(r.get("rarity") or "1")))
        raw_items.append((idx, bcode, False, eff_lvl, rarity))

    reserved = _get_reserved_codes()
    codes = _generate_box_codes(len(raw_items), reserved)

    registry: List[Dict[str, object]] = []
    for box_code, (idx, bcode, is_uni, eff_lvl, weight) in zip(codes, raw_items):
        act_prefix, tier = _act_for_level(eff_lvl)
        tinfo = LOCKBOX_TIER_INFO[tier]
        registry.append(
            {
                "code": box_code,
                "index": idx,
                "base_code": bcode,
                "is_unique": is_uni,
                "eff_lvl": eff_lvl,
                "tier": tier,
                "act_prefix": act_prefix,
                "weight": weight,
                "box_name": tinfo["box_name"],
                "box_display_name": tinfo["box_display_name"],
                "box_asset": tinfo["box_asset"],
                "box_sound": tinfo["box_sound"],
                "key_code": tinfo["key_code"],
            }
        )
    return registry


def _decode_and_remove_black_bg(src_path: str, width: int, height: int, solid_interior: bool = True) -> bytes:
    """
    Decode src_path scaled to (width, height) using ffmpeg (lanczos) into RGBA8888.
    When solid_interior=True (used for Lockboxes), only pixels outside the outer
    row/column silhouette boundary of the box are made transparent—guaranteeing 100%
    opacity (alpha=255) for every pixel inside the box's edges.
    """
    raw = bytearray(
        subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                src_path,
                "-vf",
                f"scale={width}:{height}:flags=lanczos",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgba",
                "-",
            ]
        )
    )
    w, h = width, height

    def _px_brightness(x: int, y: int) -> int:
        idx = (y * w + x) * 4
        return max(raw[idx], raw[idx + 1], raw[idx + 2])

    bg = [[False] * w for _ in range(h)]

    if solid_interior:
        # Raycast from left, right, top, and bottom edges to find the exact outer silhouette
        # of the box. Nothing inside [row_left..row_right] x [col_top..col_bot] can ever be transparent.
        thresh = 14
        row_left = [w] * h
        row_right = [-1] * h
        for y in range(h):
            for x in range(w):
                if _px_brightness(x, y) > thresh:
                    row_left[y] = x
                    break
            for x in range(w - 1, -1, -1):
                if _px_brightness(x, y) > thresh:
                    row_right[y] = x
                    break

        col_top = [h] * w
        col_bot = [-1] * w
        for x in range(w):
            for y in range(h):
                if _px_brightness(x, y) > thresh:
                    col_top[x] = y
                    break
            for y in range(h - 1, -1, -1):
                if _px_brightness(x, y) > thresh:
                    col_bot[x] = y
                    break

        for y in range(h):
            for x in range(w):
                if x < row_left[y] or x > row_right[y] or y < col_top[x] or y > col_bot[x]:
                    bg[y][x] = True
    else:
        visited = [[False] * w for _ in range(h)]
        q: deque = deque()
        for x in range(w):
            for y in (0, h - 1):
                if _px_brightness(x, y) <= 16:
                    visited[y][x] = True
                    bg[y][x] = True
                    q.append((x, y))
        for y in range(h):
            for x in (0, w - 1):
                if not visited[y][x] and _px_brightness(x, y) <= 16:
                    visited[y][x] = True
                    bg[y][x] = True
                    q.append((x, y))

        while q:
            cx, cy = q.popleft()
            for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                    visited[ny][nx] = True
                    if _px_brightness(nx, ny) <= 14:
                        bg[ny][nx] = True
                        q.append((nx, ny))

    for y in range(h):
        for x in range(w):
            idx = (y * w + x) * 4
            if bg[y][x]:
                raw[idx] = 0
                raw[idx + 1] = 0
                raw[idx + 2] = 0
                raw[idx + 3] = 0
            else:
                raw[idx + 3] = 255
                adj_bg = 0
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if 0 <= nx < w and 0 <= ny < h and bg[ny][nx]:
                        adj_bg += 1
                if adj_bg >= 2:
                    br = max(raw[idx], raw[idx + 1], raw[idx + 2])
                    if br < 40:
                        raw[idx + 3] = max(140, min(255, int(br * 6)))
    return bytes(raw)


def _write_d2r_sprite(src_path: str, out_path: str, width: int, height: int, solid_interior: bool = True) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    raw_bytes = _decode_and_remove_black_bg(src_path, width, height, solid_interior=solid_interior)
    stream_size = width * height * 4
    header = struct.pack(
        "<4sHHIIIIIIII",
        b"SpA1",
        31,
        width,
        width,
        height,
        0,
        1,
        0,
        0,
        stream_size,
        4,
    )
    with open(out_path, "wb") as f:
        f.write(header)
        f.write(raw_bytes)


def build_lockbox_sprites() -> List[str]:
    """
    Compile the 3 Lockbox icons (2x2: 196x196 .sprite and 98x98 .lowend.sprite)
    and 3 Key icons (1x1: 98x98 .sprite and 49x49 .lowend.sprite) into
    my-mod/data/hd/global/ui/items/misc/.
    """
    ui_misc_root = os.path.join(MOD_ROOT, "data/hd/global/ui/items/misc")
    written: List[str] = []

    for tier, info in LOCKBOX_TIER_INFO.items():
        # 1. 2x2 Lockbox sprite (196x196 HD, 98x98 lowend) with strict solid interior
        box_src = os.path.join(ASSETS_DIR, info["box_img"])
        box_base = os.path.join(ui_misc_root, info["box_asset"])
        _write_d2r_sprite(box_src, f"{box_base}.sprite", 196, 196, solid_interior=True)
        _write_d2r_sprite(box_src, f"{box_base}.lowend.sprite", 98, 98, solid_interior=True)
        written.append(f"{box_base}.sprite")

        # 2. 1x1 Key sprite (98x98 HD, 49x49 lowend)
        key_src = os.path.join(ASSETS_DIR, info["key_img"])
        key_base = os.path.join(ui_misc_root, info["key_asset"])
        _write_d2r_sprite(key_src, f"{key_base}.sprite", 98, 98, solid_interior=False)
        _write_d2r_sprite(key_src, f"{key_base}.lowend.sprite", 49, 49, solid_interior=False)
        written.append(f"{key_base}.sprite")

    return written

#!/usr/bin/env python3
"""
build_site.py
Generates the late-90s / Arreat Summit ('classic.battle.net/diablo2exp/') static website
for Castalia in /home/grant/games/d2r/docs/site/:
- Extracts all 120 HD Skill Icons (Paladin, Barbarian, Assassin, Sorceress) into img/skills/
- Extracts all 12 Stone Skill Tree Background Plates (3 per class) into img/trees/
- Extracts custom Lockbox, Key, and Preparation Elixir sprites into img/items/
- Generates index.html with authentic 1999/2000 Battle.net Compendium / Arreat Summit tables,
  sidebar navigation, interactive visual skill trees with hover tooltips, and full class guides.
"""
import base64
import html
import json
import os
import re
import struct
import zlib
from typing import Dict, List, Tuple

from mod_builder.char_manager import TEMPLATE_DIR, TIER_TEMPLATE_SLOTS
from mod_builder.common import MOD_ROOT, MOD_STRINGS, VANILLA_ROOT
from mod_builder.verify import _read_mod_tsv

SITE_DIR = "/home/grant/games/d2r/docs/site"
IMG_SKILLS_DIR = os.path.join(SITE_DIR, "img/skills")
IMG_TREES_DIR = os.path.join(SITE_DIR, "img/trees")
IMG_ITEMS_DIR = os.path.join(SITE_DIR, "img/items")


def _write_png_rgba(path: str, w: int, h: int, rgba_bytes: bytes) -> None:
    """Minimal pure-Python RGBA PNG writer (zero external dependencies)."""
    raw_scanlines = bytearray()
    stride = w * 4
    for y in range(h):
        raw_scanlines.append(0)  # Filter type 0 (None)
        raw_scanlines.extend(rgba_bytes[y * stride : (y + 1) * stride])

    def _chunk(ctype: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(ctype + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    compressed = zlib.compress(bytes(raw_scanlines), 9)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(_chunk(b"IHDR", ihdr))
        f.write(_chunk(b"IDAT", compressed))
        f.write(_chunk(b"IEND", b""))


def _downscale_2x_rgba(w: int, h: int, rgba: bytes) -> Tuple[int, int, bytes]:
    nw, nh = w // 2, h // 2
    out = bytearray(nw * nh * 4)
    for y in range(nh):
        sy0 = (y * 2) * w * 4
        sy1 = (y * 2 + 1) * w * 4
        for x in range(nw):
            sx = (x * 2) * 4
            for c in range(4):
                v = (
                    rgba[sy0 + sx + c]
                    + rgba[sy0 + sx + 4 + c]
                    + rgba[sy1 + sx + c]
                    + rgba[sy1 + sx + 4 + c]
                ) // 4
                out[(y * nw + x) * 4 + c] = v
    return nw, nh, bytes(out)


def _extract_skill_icons_and_trees() -> Dict[Tuple[str, int], str]:
    """
    Extract cropped 94x92 skill icons for pal, bar, ass, sor and downscaled 448x584
    stone skill tree background plates (frames 0, 1, 2).
    """
    os.makedirs(IMG_SKILLS_DIR, exist_ok=True)
    os.makedirs(IMG_TREES_DIR, exist_ok=True)

    class_sprite_paths = {
        "pal": (
            os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/paladin/paskillicon.sprite"),
            os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/skill_trees/paskilltree.sprite"),
        ),
        "bar": (
            os.path.join(MOD_ROOT, "data/hd/global/ui/spells/barbarian/baskillicon.sprite"),
            os.path.join(MOD_ROOT, "data/hd/global/ui/spells/skill_trees/baskilltree.sprite"),
        ),
        "ass": (
            os.path.join(MOD_ROOT, "data/hd/global/ui/spells/assassin/asskillicon.sprite"),
            os.path.join(MOD_ROOT, "data/hd/global/ui/spells/skill_trees/asskilltree.sprite"),
        ),
        "sor": (
            os.path.join(MOD_ROOT, "data/hd/global/ui/spells/sorceress/soskillicon.sprite"),
            os.path.join(MOD_ROOT, "data/hd/global/ui/spells/skill_trees/soskilltree.sprite"),
        ),
    }

    # Load panel_skilltreebg.sprite (1023x1298) so we can composite the authentic carved stone background
    # underneath each 897x1169 frame of *skilltree.sprite (at offset bg_x0=63, bg_y0=15), and then
    # alpha-blend each skill's 132x130 icon directly into its stone socket!
    bg_path = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/skill_trees/panel_skilltreebg.sprite")
    with open(bg_path, "rb") as f:
        raw_bg = f.read()[40:]
    W_BG, H_BG = 1023, 1298
    BG_X0, BG_Y0 = 63, 15

    # Extract individual skill icons (cropped to the 94x92 stone icon plate interior: x=19..113, y=19..111)
    icon_Buffers = {}
    for cls, (icon_path, _) in class_sprite_paths.items():
        with open(icon_path, "rb") as f:
            raw_ic = f.read()
        w_ic, h_ic = struct.unpack("<II", raw_ic[8:16])
        icon_Buffers[cls] = (w_ic, h_ic, raw_ic[40:])

    _, sk_rows = _read_mod_tsv("skills.txt")
    _, sd_rows = _read_mod_tsv("skilldesc.txt")
    sd_by_id = {r["skilldesc"].lower(): r for r in sd_rows if r.get("skilldesc")}

    icon_rel_by_cls_cel: Dict[Tuple[str, int], str] = {}
    FW_IC, FH_IC = 132, 130
    PX0, PX1, PY0, PY1 = 19, 113, 19, 111
    CW, CH = PX1 - PX0, PY1 - PY0

    # Group skills by (cls, frame_idx) -> list of (row, col, cel) so we can stamp them onto the stone tree plate
    tree_stamps: Dict[Tuple[str, int], List[Tuple[int, int, int]]] = {}

    for r in sk_rows:
        cls = r.get("charclass", "")
        if cls not in class_sprite_paths:
            continue
        sd = sd_by_id.get(r.get("skilldesc", "").lower(), {})
        pg = sd.get("SkillPage", "")
        if pg not in ("1", "2", "3"):
            continue
        rw = int(sd.get("SkillRow") or "1")
        cl = int(sd.get("SkillColumn") or "1")
        cel = int(sd.get("IconCel") or "0")
        f_idx = 3 - int(pg)
        tree_stamps.setdefault((cls, f_idx), []).append((rw, cl, cel))

        if (cls, cel) in icon_rel_by_cls_cel:
            continue
        w_sheet, _, buf = icon_Buffers[cls]
        cropped = bytearray(CW * CH * 4)
        for dy in range(CH):
            sy = PY0 + dy
            s_off = (sy * w_sheet + cel * FW_IC + PX0) * 4
            d_off = dy * CW * 4
            cropped[d_off : d_off + CW * 4] = buf[s_off : s_off + CW * 4]
        rel_p = f"img/skills/{cls}_{cel}.png"
        _write_png_rgba(os.path.join(SITE_DIR, rel_p), CW, CH, bytes(cropped))
        icon_rel_by_cls_cel[(cls, cel)] = rel_p

    # Extract 3 stone tree frames per class, compositing:
    #   1) panel_skilltreebg.sprite (carved stone slab background)
    #   2) *skilltree.sprite (recessed stone slot boxes, connecting arrows & active top tab)
    #   3) *skillicon.sprite 132x130 icons inside each slot box
    W_T, H_T, FW_T = 2691, 1169, 897
    ROW_Y_HD = {1: 125, 2: 305, 3: 481, 4: 662, 5: 841, 6: 1017}
    COL_X_HD = {1: 109, 2: 371, 3: 631}

    for cls, (_, tree_path) in class_sprite_paths.items():
        with open(tree_path, "rb") as f:
            raw_t = f.read()[40:]
        w_sheet, _, ic_buf = icon_Buffers[cls]
        for f_idx in range(3):
            frame_rgba = bytearray(FW_T * H_T * 4)
            # Layer 1: Stone background from panel_skilltreebg.sprite
            for y in range(H_T):
                by = min(H_BG - 1, BG_Y0 + y)
                bg_off = (by * W_BG + BG_X0) * 4
                d_off = y * FW_T * 4
                frame_rgba[d_off : d_off + FW_T * 4] = raw_bg[bg_off : bg_off + FW_T * 4]
                # Ensure full opacity on background slab
                for x_i in range(3, FW_T * 4, 4):
                    frame_rgba[d_off + x_i] = 255

            # Layer 2: Alpha-blend *skilltree.sprite slot boxes & arrows over stone slab
            for y in range(H_T):
                s_off = (y * W_T + f_idx * FW_T) * 4
                d_off = y * FW_T * 4
                for x in range(FW_T):
                    si = s_off + x * 4
                    sa = raw_t[si + 3]
                    if sa > 0:
                        di = d_off + x * 4
                        inv_a = 255 - sa
                        frame_rgba[di] = (raw_t[si] * sa + frame_rgba[di] * inv_a) // 255
                        frame_rgba[di + 1] = (raw_t[si + 1] * sa + frame_rgba[di + 1] * inv_a) // 255
                        frame_rgba[di + 2] = (raw_t[si + 2] * sa + frame_rgba[di + 2] * inv_a) // 255
                        frame_rgba[di + 3] = 255

            # Layer 3: Alpha-blend each skill's 132x130 icon into its stone socket (COL_X + 10, ROW_Y + 13)
            for rw, cl, cel in tree_stamps.get((cls, f_idx), []):
                dst_x0 = COL_X_HD[cl] + 10
                dst_y0 = ROW_Y_HD[rw] + 13
                for dy in range(FH_IC):
                    ty = dst_y0 + dy
                    if not (0 <= ty < H_T):
                        continue
                    s_row_off = (dy * w_sheet + cel * FW_IC) * 4
                    d_row_off = (ty * FW_T + dst_x0) * 4
                    for dx in range(FW_IC):
                        si = s_row_off + dx * 4
                        sa = ic_buf[si + 3]
                        if sa > 0:
                            di = d_row_off + dx * 4
                            inv_a = 255 - sa
                            frame_rgba[di] = (ic_buf[si] * sa + frame_rgba[di] * inv_a) // 255
                            frame_rgba[di + 1] = (ic_buf[si + 1] * sa + frame_rgba[di + 1] * inv_a) // 255
                            frame_rgba[di + 2] = (ic_buf[si + 2] * sa + frame_rgba[di + 2] * inv_a) // 255
                            frame_rgba[di + 3] = 255

            nw, nh, small_bytes = _downscale_2x_rgba(FW_T, H_T, bytes(frame_rgba))
            _write_png_rgba(os.path.join(IMG_TREES_DIR, f"{cls}_frame_{f_idx}.png"), nw, nh, small_bytes)

    # Also extract custom misc item sprites (Lockbox, Key, Elixir)
    os.makedirs(IMG_ITEMS_DIR, exist_ok=True)
    misc_sprites = [
        ("lockbox_wood.png", "herb/herb.sprite"),
        ("lockbox_iron.png", "torch/torch.sprite"),
        ("lockbox_gold.png", "body_part/tail.sprite"),
        ("key_crude.png", "key/skeleton_key.sprite"),
        ("key_iron.png", "body_part/jawbone.sprite"),
        ("key_ornate.png", "body_part/horn.sprite"),
        ("elixir.png", "potion/elixir.sprite"),
    ]
    for out_name, sp_rel in misc_sprites:
        sp_path = os.path.join(MOD_ROOT, "data/hd/global/ui/items/misc", sp_rel)
        if os.path.exists(sp_path):
            with open(sp_path, "rb") as f:
                raw_sp = f.read()
            sw, sh = struct.unpack("<II", raw_sp[8:16])
            _write_png_rgba(os.path.join(IMG_ITEMS_DIR, out_name), sw, sh, raw_sp[40 : 40 + sw * sh * 4])

    return icon_rel_by_cls_cel


def _replace_ternary(s: str) -> str:
    while "?" in s:
        q = s.find("?")
        depth = 0
        start = 0
        for i in range(q - 1, -1, -1):
            if s[i] == ")":
                depth += 1
            elif s[i] == "(":
                if depth == 0:
                    start = i + 1
                    break
                depth -= 1
        depth = 0
        colon = -1
        for i in range(q + 1, len(s)):
            if s[i] == "(":
                depth += 1
            elif s[i] == ")":
                depth -= 1
            elif s[i] == ":" and depth == 0:
                colon = i
                break
        depth = 0
        end = len(s)
        for i in range(colon + 1, len(s)):
            if s[i] == "(":
                depth += 1
            elif s[i] == ")":
                if depth == 0:
                    end = i
                    break
                depth -= 1
        cond = s[start:q].strip()
        t_br = s[q + 1 : colon].strip()
        f_br = s[colon + 1 : end].strip()
        s = s[:start] + f"(({t_br}) if ({cond}) else ({f_br}))" + s[end:]
    return s


def _tiered_val(row: dict, base_col: str, lev_prefix: str, lvl: int) -> int:
    b = int(row.get(base_col, 0) or 0)
    d1 = int(row.get(f"{lev_prefix}1", 0) or 0)
    d2 = int(row.get(f"{lev_prefix}2", 0) or 0)
    d3 = int(row.get(f"{lev_prefix}3", 0) or 0)
    d4 = int(row.get(f"{lev_prefix}4", 0) or 0)
    d5 = int(row.get(f"{lev_prefix}5", 0) or 0)
    return (
        b
        + max(0, min(lvl, 8) - 1) * d1
        + max(0, min(lvl, 16) - 8) * d2
        + max(0, min(lvl, 22) - 16) * d3
        + max(0, min(lvl, 28) - 22) * d4
        + max(0, lvl - 28) * d5
    )


def _eval_skill_expr(sk: dict, sd: dict, miss_map: dict, expr: str, lvl: int, depth: int = 0) -> int:
    if not expr or depth > 8:
        return 0
    e = expr.strip().strip('"').strip()
    if not e:
        return 0

    def repl_sk(m):
        nm = m.group(1)
        return str(lvl) if nm.lower() == sk["skill"].lower() else "0"

    e = re.sub(r"skill\('([^']+)'\.[A-Za-z0-9_]+\)", repl_sk, e)

    def repl_ms(m):
        mn = m.group(1).lower()
        mr = miss_map.get(mn, {})
        r_expr = mr.get("Range", "0") or "0"
        base_r = _eval_skill_expr(sk, sd, miss_map, r_expr, lvl, depth + 1)
        lev_r = int(mr.get("LevRange", 0) or 0)
        return str(base_r + (lvl - 1) * lev_r)

    e = re.sub(r"miss\('([^']+)'\.[A-Za-z0-9_]+\)", repl_ms, e)

    def repl_st(m):
        st = m.group(1).lower()
        if st in ("stamina", "maxstamina"):
            return "256"
        return "0"

    e = re.sub(r"stat\('([^']+)'\.[A-Za-z0-9_]+\)", repl_st, e)
    e = _replace_ternary(e)

    pars = {f"par{i}": int(sk.get(f"Param{i}", 0) or 0) for i in range(1, 13)}

    def ln(a: int, b: int) -> int:
        return pars[f"par{a}"] + (lvl - 1) * pars[f"par{b}"]

    def dm(a: int, b: int) -> int:
        pa, pb = pars[f"par{a}"], pars[f"par{b}"]
        return int((110 * lvl) * (pb - pa) / (100 * (lvl + 6))) + pa

    hs = int(sk.get("HitShift", 8) or 8)
    raw_emin = _tiered_val(sk, "EMin", "EMinLev", lvl)
    raw_emax = _tiered_val(sk, "EMax", "EMaxLev", lvl)
    raw_pmin = _tiered_val(sk, "MinDam", "MinLevDam", lvl)
    raw_pmax = _tiered_val(sk, "MaxDam", "MaxLevDam", lvl)
    esym = _eval_skill_expr(sk, sd, miss_map, sk.get("EDmgSymPerCalc", ""), lvl, depth + 1) if sk.get("EDmgSymPerCalc") and depth < 4 else 0
    psym = _eval_skill_expr(sk, sd, miss_map, sk.get("DmgSymPerCalc", ""), lvl, depth + 1) if sk.get("DmgSymPerCalc") and depth < 4 else 0
    enms = int((raw_emin << hs) * (100 + esym) / 100)
    exms = int((raw_emax << hs) * (100 + esym) / 100)
    enma = enms >> 8
    exma = exms >> 8
    pnma = int((raw_pmin << hs >> 8) * (100 + psym) / 100)
    pxma = int((raw_pmax << hs >> 8) * (100 + psym) / 100)

    d1 = int(sk.get("ELevLen1", 0) or 0)
    d2 = int(sk.get("ELevLen2", 0) or 0)
    d3 = int(sk.get("ELevLen3", 0) or 0)
    elen = int(sk.get("ELen", 0) or 0) + max(0, min(lvl, 8) - 1) * d1 + max(0, min(lvl, 16) - 8) * d2 + max(0, lvl - 16) * d3
    lsym = _eval_skill_expr(sk, sd, miss_map, sk.get("ELenSymPerCalc", ""), lvl, depth + 1) if sk.get("ELenSymPerCalc") and depth < 4 else 0
    edln = int(elen * (100 + lsym) / 100)

    m_shift = int(sk.get("manashift", 8) or 8)
    usmc = max(int(sk.get("minmana", 0) or 0) << 8, (int(sk.get("mana", 0) or 0) + (lvl - 1) * int(sk.get("lvlmana", 0) or 0)) << m_shift)

    if sk.get("ToHitCalc"):
        toht = _eval_skill_expr(sk, sd, miss_map, sk["ToHitCalc"], lvl, depth + 1) if depth < 4 else 0
    else:
        toht = int(sk.get("ToHit", 0) or 0) + (lvl - 1) * int(sk.get("LevToHit", 0) or 0)

    env = {
        "lvl": lvl,
        "blvl": lvl,
        "min": min,
        "max": max,
        "ln12": ln(1, 2),
        "ln34": ln(3, 4),
        "ln56": ln(5, 6),
        "ln78": ln(7, 8),
        "dm12": dm(1, 2),
        "dm34": dm(3, 4),
        "dm56": dm(5, 6),
        "dm78": dm(7, 8),
        "dm91": dm(9, 10),
        "usmc": usmc,
        "toht": toht,
        "enma": enma,
        "exma": exma,
        "enms": enms,
        "exms": exms,
        "edns": raw_emin << hs,
        "edxs": raw_emax << hs,
        "pnma": pnma,
        "pxma": pxma,
        "elen": elen,
        "edln": edln,
        "len": _eval_skill_expr(sk, sd, miss_map, sk.get("auralencalc", ""), lvl, depth + 1) if "len" in e and depth < 4 else 0,
        "madm": ln(3, 4),
        "math": ln(1, 2),
        "mapi": dm(7, 8),
        "manc": dm(9, 10),
    }
    env.update(pars)
    for mi in (1, 2, 3):
        mname = (sd.get(f"descmissile{mi}", "") or sk.get("srvmissilea", "")).lower()
        mr = miss_map.get(mname, {})
        mhs = int(mr.get("HitShift", 8) or 8)
        memin = _tiered_val(mr, "EMin", "MinELev", lvl) or _tiered_val(mr, "EMin", "EMinLev", lvl)
        memax = _tiered_val(mr, "EMax", "MaxELev", lvl) or _tiered_val(mr, "EMax", "EMaxLev", lvl)
        mpmin = _tiered_val(mr, "MinDamage", "MinLevDam", lvl)
        mpmax = _tiered_val(mr, "MaxDamage", "MaxLevDam", lvl)
        env[f"m{mi}en"] = int((memin << mhs >> 8) * (100 + esym) / 100)
        env[f"m{mi}ex"] = int((memax << mhs >> 8) * (100 + esym) / 100)
        env[f"m{mi}na"] = int(((memin or mpmin) << mhs) * (100 + (esym or psym)) / 100)
        env[f"m{mi}xa"] = int(((memax or mpmax) << mhs) * (100 + (esym or psym)) / 100)

    for ci in range(1, 7):
        ck = f"clc{ci}"
        if ck in e and depth < 5:
            env[ck] = _eval_skill_expr(sk, sd, miss_map, sk.get(f"calc{ci}", ""), lvl, depth + 1)

    e_py = e.replace("/", "//")
    return int(eval(e_py, {"__builtins__": {}}, env))


def _fmt_num(v: float) -> str:
    if abs(v - round(v)) < 0.05:
        return str(int(round(v)))
    return f"{v:.1f}"


def _sub_signed_placeholder(tmpl: str, v1_str: str, v20_str: str) -> str:
    m = re.search(r"([+-]?)(%\+?d)(%?)", tmpl)
    if not m:
        return f"{tmpl} {v1_str}" if v1_str == v20_str else f"{tmpl} {v1_str} -> {v20_str}"
    lead_sign, ph, pct = m.group(1), m.group(2), m.group(3)
    sign = lead_sign or ("+" if ph == "%+d" else "")

    def add_s(s: str) -> str:
        if sign == "+" and not s.startswith(("+", "-")):
            return f"+{s}{pct}"
        if sign == "-" and not s.startswith("-"):
            return f"-{s}{pct}"
        return f"{s}{pct}"

    s1 = add_s(v1_str)
    s20 = add_s(v20_str)
    rep = s1 if s1 == s20 else f"{s1} -> {s20}"
    return tmpl[: m.start()] + rep + tmpl[m.end() :]


def _render_skilldesc_line(sk: dict, sd: dict, miss_map: dict, s_map: dict, fn: str, ta: str, tb: str, ca: str, cb: str) -> str:
    def get_s(k: str) -> str:
        return s_map.get(k, s_map.get(k.capitalize(), k)) if k else ""

    s_a = get_s(ta)
    s_b = get_s(tb)
    if fn == "18":
        return s_a
    if fn == "40":
        return ""
    if fn == "76":
        v1 = _eval_skill_expr(sk, sd, miss_map, ca, 1)
        v20 = _eval_skill_expr(sk, sd, miss_map, ca, 20)
        body = s_a.replace("%%", "%").replace("%s", s_b)
        return _sub_signed_placeholder(body, str(v1), str(v20))
    if fn == "77":
        va = _eval_skill_expr(sk, sd, miss_map, ca, 1)
        vb = _eval_skill_expr(sk, sd, miss_map, cb, 1)
        body = s_a.replace("%%", "%").replace("%s", s_b)
        body = re.sub(r"%\+?d", f"+{va}" if "%+d" in body and va >= 0 else str(va), body, count=1)
        body = re.sub(r"%\+?d", str(vb), body, count=1)
        return body
    if fn == "13":
        v1 = 100 + _eval_skill_expr(sk, sd, miss_map, ca, 1)
        v20 = 100 + _eval_skill_expr(sk, sd, miss_map, ca, 20)
        return _sub_signed_placeholder(s_a.replace("%%", "%"), str(v1), str(v20))
    if fn == "36":
        n1 = _eval_skill_expr(sk, sd, miss_map, ca, 1)
        d1 = _eval_skill_expr(sk, sd, miss_map, cb, 1) or 1
        n20 = _eval_skill_expr(sk, sd, miss_map, ca, 20)
        d20 = _eval_skill_expr(sk, sd, miss_map, cb, 20) or 1
        f1 = _fmt_num(n1 / d1)
        f20 = _fmt_num(n20 / d20)
        tmpl = (s_b or s_a).replace("%%", "%")
        return _sub_signed_placeholder(tmpl, f1, f20)
    if fn == "74":
        v1 = _eval_skill_expr(sk, sd, miss_map, ca, 1)
        v20 = _eval_skill_expr(sk, sd, miss_map, ca, 20)
        if v1 == 0 and v20 == 0:
            return ""
        tmpl = s_a.replace("%%", "%")
        return _sub_signed_placeholder(tmpl, str(v1), str(v20))
    if fn == "75":
        a1 = _eval_skill_expr(sk, sd, miss_map, ca, 1)
        b1 = _eval_skill_expr(sk, sd, miss_map, cb, 1)
        a20 = _eval_skill_expr(sk, sd, miss_map, ca, 20)
        b20 = _eval_skill_expr(sk, sd, miss_map, cb, 20)
        tmpl = s_a.replace("%%", "%")
        m_range = re.search(r"([+-]?)(%\+?d)-(%\+?d)(%?)", tmpl)
        if m_range:
            lead, ph1, ph2, pct = m_range.group(1), m_range.group(2), m_range.group(3), m_range.group(4)
            sign = lead or ("+" if "%+d" in (ph1, ph2) else "")
            r1 = f"{sign}{a1}-{b1}{pct}" if a1 != b1 else f"{sign}{a1}{pct}"
            r20 = f"{sign}{a20}-{b20}{pct}" if a20 != b20 else f"{sign}{a20}{pct}"
            rep = r1 if r1 == r20 else f"{r1} -> {r20}"
            return tmpl[: m_range.start()] + rep + tmpl[m_range.end() :]
        out = _sub_signed_placeholder(tmpl, str(a1), str(a20))
        out = _sub_signed_placeholder(out, str(b1), str(b20))
        return out
    return ""


def _build_skill_data_summary(sk: dict, sd: dict, miss_map: dict, s_map: dict) -> Tuple[str, str]:
    """
    Build (plain_tooltip_text, rich_html_cell) for a skill strictly from skills.txt, skilldesc.txt,
    missiles.txt, and skills.json / item-modifiers.json (zero hardcoded skill descriptions).
    """
    raw_long = s_map.get(sd.get("str long", ""), "") or s_map.get(sd.get("str short", ""), "")
    desc_lines = [ln.strip() for ln in raw_long.splitlines() if ln.strip()]
    lore_str = " — ".join(desc_lines)

    stat_lines: List[str] = []
    for prefix, mx in [("desc", 6), ("dsc2", 5)]:
        for i in range(1, mx + 1):
            fn = sd.get(f"{prefix}line{i}", "").strip()
            if not fn:
                continue
            rendered = _render_skilldesc_line(
                sk,
                sd,
                miss_map,
                s_map,
                fn,
                sd.get(f"{prefix}texta{i}", ""),
                sd.get(f"{prefix}textb{i}", ""),
                sd.get(f"{prefix}calca{i}", ""),
                sd.get(f"{prefix}calcb{i}", ""),
            )
            if rendered and rendered not in stat_lines:
                stat_lines.append(rendered)

    # Fallback if descdam=5 skill has EMin/EMax or mana in skills.txt without explicit descline rows
    if not stat_lines:
        if sk.get("EMin") and sk.get("EMax"):
            etype_names = {"fire": "Fire", "ltng": "Lightning", "cold": "Cold", "mag": "Magic", "pois": "Poison"}
            elbl = etype_names.get(sk.get("EType", ""), "Elemental")
            e1_min = _eval_skill_expr(sk, sd, miss_map, "enma", 1)
            e1_max = _eval_skill_expr(sk, sd, miss_map, "exma", 1)
            e20_min = _eval_skill_expr(sk, sd, miss_map, "enma", 20)
            e20_max = _eval_skill_expr(sk, sd, miss_map, "exma", 20)
            stat_lines.append(f"{elbl} Damage: {e1_min}-{e1_max} -> {e20_min}-{e20_max}")
        if sk.get("mana"):
            u1 = _eval_skill_expr(sk, sd, miss_map, "usmc", 1) / 256.0
            u20 = _eval_skill_expr(sk, sd, miss_map, "usmc", 20) / 256.0
            f1, f20 = _fmt_num(u1), _fmt_num(u20)
            stat_lines.append(f"Mana Cost: {f1}" if f1 == f20 else f"Mana Cost: {f1} -> {f20}")

    syn_lines: List[str] = []
    for i in range(1, 8):
        fn = sd.get(f"dsc3line{i}", "").strip()
        if not fn:
            continue
        rendered = _render_skilldesc_line(
            sk,
            sd,
            miss_map,
            s_map,
            fn,
            sd.get(f"dsc3texta{i}", ""),
            sd.get(f"dsc3textb{i}", ""),
            sd.get(f"dsc3calca{i}", ""),
            sd.get(f"dsc3calcb{i}", ""),
        )
        if rendered and rendered not in syn_lines:
            syn_lines.append(rendered)

    # Plain summary for hover tooltip attribute
    plain_parts = []
    if lore_str:
        plain_parts.append(lore_str)
    if stat_lines:
        plain_parts.append("Lvl 1 -> 20: " + " | ".join(stat_lines))
    if syn_lines:
        plain_parts.append("Synergies: " + " | ".join(syn_lines))
    plain_text = " — ".join(plain_parts)

    # Structured HTML for table cell
    html_parts = []
    if lore_str:
        html_parts.append(f'<div>{html.escape(lore_str)}</div>')
    if stat_lines:
        items = " &nbsp;&bull;&nbsp; ".join(f'<span class="d2-blue">{html.escape(s)}</span>' for s in stat_lines)
        html_parts.append(f'<div style="margin-top:3px;"><b class="d2-gold">Lvl 1 &rarr; 20:</b> {items}</div>')
    if syn_lines:
        sitems = " &nbsp;&bull;&nbsp; ".join(f'<span class="d2-green">{html.escape(s)}</span>' for s in syn_lines)
        html_parts.append(f'<div style="margin-top:2px;"><b class="d2-dim">Synergies:</b> {sitems}</div>')
    return plain_text, "".join(html_parts)


def _format_gem_or_rune_mod(code: str, param: str, mn_s: str, mx_s: str, prop_map: dict, isc_map: dict, s_map: dict) -> str:
    mn = int(mn_s or 0)
    mx = int(mx_s or 0)
    if code == "dmg-fire":
        return f"Adds {mn}–{mx} Fire Damage"
    if code == "dmg-cold":
        return f"Adds {mn}–{mx} Cold Damage"
    if code == "dmg-ltng":
        return f"Adds {mn}–{mx} Lightning Damage"
    if code == "dmg-mag":
        return f"Adds {mn}–{mx} Magic Damage"
    if code == "dmg-pois":
        frames = int(param or 75)
        tot = int(round(mn * frames / 256.0))
        secs = int(round(frames / 25.0))
        return f"+{tot} Poison Damage over {secs}s"
    if code == "dmg%":
        return f"+{mn}% Enhanced Damage"
    if code == "dmg-min":
        return f"+{mn} to Minimum Damage"
    if code == "dmg-max":
        return f"+{mn} to Maximum Damage"
    if code == "indestruct":
        return s_map.get("ModStre9s", "Indestructible")
    if code == "res-all":
        tmpl = s_map.get("strModAllResistances", "All Resistances +%d")
        return tmpl.replace("%+d", f"+{mn}").replace("%d", str(mn))

    pr = prop_map.get(code, {})
    st = pr.get("stat1", "")
    isc = isc_map.get(st, {})
    dfunc = int(isc.get("descfunc", 0) or 0)
    dval = int(isc.get("descval", 1) or 0)
    key = isc.get("descstrpos" if mn >= 0 else "descstrneg", "") or isc.get("descstrpos", "")
    txt = s_map.get(key, key).replace("%%", "%")
    if "%d" in txt or "%+d" in txt:
        v_s = f"+{mn}" if ("%+d" in txt and mn >= 0) else str(mn)
        return re.sub(r"%\+?d", v_s, txt, count=1)
    if dval == 0:
        return txt
    if dfunc in (1, 6, 12, 19):
        val_s = f"+{mn}" if mn >= 0 else str(mn)
    elif dfunc in (2, 7):
        val_s = f"{mn}%"
    elif dfunc in (3, 9):
        val_s = str(mn)
    elif dfunc in (4, 8):
        val_s = f"+{mn}%" if mn >= 0 else f"{mn}%"
    else:
        val_s = str(mn)
    if dval == 1:
        return f"{val_s} {txt}"
    return f"{txt} {val_s}"


def build_site() -> str:
    icon_map = _extract_skill_icons_and_trees()

    _, sk_rows = _read_mod_tsv("skills.txt")
    _, sd_rows = _read_mod_tsv("skilldesc.txt")
    _, miss_rows = _read_mod_tsv("missiles.txt")
    _, gem_rows = _read_mod_tsv("gems.txt")
    _, misc_rows = _read_mod_tsv("misc.txt")
    _, prop_rows = _read_mod_tsv("properties.txt")
    _, isc_rows = _read_mod_tsv("itemstatcost.txt")

    sd_by_id = {r["skilldesc"].lower(): r for r in sd_rows if r.get("skilldesc")}
    miss_map = {r["Missile"].lower(): r for r in miss_rows if r.get("Missile")}
    gems_by_code = {r["code"]: r for r in gem_rows if r.get("code")}
    misc_by_code = {r["code"]: r for r in misc_rows if r.get("code")}
    prop_map = {r["code"]: r for r in prop_rows if r.get("code")}
    isc_map = {r["Stat"]: r for r in isc_rows if r.get("Stat")}

    s_map: Dict[str, str] = {}
    for jf in ("skills.json", "item-modifiers.json", "item-runes.json", "item-names.json", "item-gems.json"):
        jpath = os.path.join(MOD_STRINGS, jf)
        if os.path.exists(jpath):
            with open(jpath, "r", encoding="utf-8-sig") as f:
                for e in json.load(f):
                    if isinstance(e, dict) and "Key" in e and e["Key"] not in s_map:
                        s_map[e["Key"]] = e["enUS"]

    sk_name_by_raw = {}
    for r in sk_rows:
        sd = sd_by_id.get(r.get("skilldesc", "").lower(), {})
        nm = s_map.get(sd.get("str name", ""), r.get("skill", ""))
        sk_name_by_raw[r.get("skill", "")] = nm

    class_meta = [
        (
            "pal",
            "Paladin",
            "Aura Mana Upkeep, Resistance-Synergized Elemental Cleave & Chain Hammer",
            {3: "Defensive Auras", 2: "Offensive Auras", 1: "Combat Skills"},
        ),
        (
            "bar",
            "Barbarian",
            "The Stamina Pendulum (0-Mana Melee) & In-Combat Warcry Stances",
            {3: "Warcries", 2: "Combat Masteries", 1: "Combat Skills"},
        ),
        (
            "ass",
            "Assassin",
            "All-Weapon Martial Arts, 15-Minute Held Combo Orbs & Orb-Fed Sentries",
            {3: "Martial Arts", 2: "Shadow Disciplines", 1: "Traps & Blades"},
        ),
        (
            "sor",
            "Sorceress",
            "Elemental Stance-Dancer, Directional Blinks & Co-Op Conduction",
            {3: "Cold Spells", 2: "Lightning Spells", 1: "Fire Spells"},
        ),
    ]

    class_lore_html: Dict[str, str] = {
        "pal": (
            '<div style="border:1px solid #4a3c28;background:#14100b;padding:12px 16px;margin:10px 0 12px 0;line-height:1.55;font-size:13px;color:#d8cbb8;">'
            '<div style="color:#d4af37;font-weight:bold;letter-spacing:0.5px;margin-bottom:6px;">THE PALADIN &mdash; TEMPLAR OF LIVING AURAS &amp; TACTICAL STEEL</div>'
            '<p style="margin:0 0 8px 0;">In Castalia, a Paladin\'s auras are no longer effortless background stat sticks &mdash; they are <b>living prayers that demand discipline</b>. '
            'Sustaining an active aura now draws steady mana upkeep, turning Energy, mana regeneration, and <b>Meditation</b> or <b>Redemption</b> into real tactical decisions, '
            'while investing hard points into key auras permanently embeds a subtle passive blessing into the Paladin himself. <b>Conviction</b> no longer erases enemy resistances for free; '
            'instead, it empowers the party\'s elemental strikes based on his Resistance Auras while shattering monster defenses in battle.</p>'
            '<p style="margin:0;">His martial arts have been reshaped around deliberate, physical combat. <b>Vengeance</b> now sweeps through enemies in a wide <b>elemental frontal cleave</b>, '
            '<b>Blessed Hammer</b> has been reborn as a <b>bouncing Chain Hammer</b> that knocks back and stuns entire packs, and <b>Sanctuary</b> stands alongside <b>Holy Fire</b>, '
            '<b>Holy Freeze</b>, and <b>Holy Shock</b> as a true magic pulse-and-weapon aura. Whether leading the front line as an elemental cleaver, anchoring a party with defensive prayers, '
            'or channeling the Light through <b>Holy Bolt</b> and <b>Fist of the Heavens</b>, the Paladin rewards active aura-weaving and smart positioning over mindless hammering.</p>'
            '</div>'
        ),
        "bar": (
            '<div style="border:1px solid #4a3c28;background:#14100b;padding:12px 16px;margin:10px 0 12px 0;line-height:1.55;font-size:13px;color:#d8cbb8;">'
            '<div style="color:#d4af37;font-weight:bold;letter-spacing:0.5px;margin-bottom:6px;">THE BARBARIAN &mdash; MASTER OF THE STAMINA PENDULUM</div>'
            '<p style="margin:0 0 8px 0;">The Barbarian of Castalia fights on <b>grit and breath</b>, not mana. His melee attacks cost <b>zero mana</b> and instead ride the rhythm of the '
            '<b>Stamina Pendulum</b> &mdash; turning his Stamina bar into an active combat resource. When fresh, <b>Well-Rested</b> strikes like <b>Strike</b>, <b>Shield Slam</b>, and '
            '<b>Concentrate</b> hit with measured force; <b>Stamina Spenders</b> like <b>Leap</b>, <b>Leap Attack</b>, and <b>Whirlwind</b> burn breath for explosive engagements and sweeping momentum; '
            'and as fatigue sets in, <b>Exhaustion</b> skills like <b>Flurry</b>, <b>Barrage</b>, <b>Frenzy</b>, and <b>Berserk</b> surge in ferocity, rewarding warriors who fight on the edge.</p>'
            '<p style="margin:0;">His Warcries are no longer passive chores shouted once at a waypoint. Transformed into active combat stances and battlefield roars &mdash; like <b>Second Wind</b>, '
            '<b>Enduring Cry</b>, and <b>Bloodlust</b> &mdash; they manage his stamina, fuel his Last Stand fury, and keep him pushing forward in the thick of the brawl.</p>'
            '</div>'
        ),
        "ass": (
            '<div style="border:1px solid #4a3c28;background:#14100b;padding:12px 16px;margin:10px 0 12px 0;line-height:1.55;font-size:13px;color:#d8cbb8;">'
            '<div style="color:#d4af37;font-weight:bold;letter-spacing:0.5px;margin-bottom:6px;">THE ASSASSIN &mdash; ALL-WEAPON MARTIAL ARTIST &amp; ORB-FED TACTICIAN</div>'
            '<p style="margin:0 0 8px 0;">Freed from claw-only restrictions, the Assassin of Castalia brings <b>Martial Arts</b> to any melee weapon in her hands. Her five Charge-Up disciplines &mdash; '
            '<b>Tiger Strike</b>, <b>Flamestrike</b>, <b>Blades of Ice</b>, <b>Electrocute</b>, and <b>Cobra Strike</b> &mdash; no longer expire in seconds: held orbs persist for <b>15 minutes</b>, '
            'continuously infusing her weapon attacks until she chooses to unleash their devastating 1-, 2-, or 3-charge finishers, or spin straight through enemy packs with <b>Omnislash</b>, '
            'carrying every held orb bonus without consuming a single charge.</p>'
            '<p style="margin:0;">Her Traps and Martial Arts are woven into a single seamless loop. Deploying a <b>Shrapnel</b>, <b>Fire</b>, <b>Ice</b>, <b>Lightning</b>, or <b>Soul Siphon Sentry</b> '
            'feeds her held orbs directly into the trap, supercharging its range, duration, and special payloads &mdash; from micro-stuns and solid freeze to Flash Blind and Life Tap. '
            'Backed by Shadow techniques like <b>Flow</b>, <b>Shadow Bind</b>, and <b>Caltrops</b>, she rewards fluid rhythm between close-quarters combos and tactical battlefield traps.</p>'
            '</div>'
        ),
        "sor": (
            '<div style="border:1px solid #4a3c28;background:#14100b;padding:12px 16px;margin:10px 0 12px 0;line-height:1.55;font-size:13px;color:#d8cbb8;">'
            '<div style="color:#d4af37;font-weight:bold;letter-spacing:0.5px;margin-bottom:6px;">THE SORCERESS &mdash; ELEMENTAL STANCE-DANCER &amp; CONDUIT</div>'
            '<p style="margin:0 0 8px 0;">The Sorceress of Castalia no longer stands in place spamming a single spell &mdash; she <b>becomes</b> the element she commands. '
            'By weaving between three mutually exclusive <b>Elemental Stances</b> &mdash; the glass-cannon fury of <b>Conflagration</b>, the lightning-fast storm of <b>Overcharge</b>, '
            'and the armored bastion of <b>Cryostasis</b> &mdash; she reshapes her spells mid-fight while accepting steep defensive trade-offs and locking out opposing elements until she shifts her attunement. '
            'With unrestricted Teleport removed, survival comes from sharp positioning and elemental blinks (<b>Flashfire</b>, <b>Phase Step</b>, <b>Glacier Step</b>).</p>'
            '<p style="margin:0;">Her true breakthrough, however, is <b>Conduction</b> &mdash; a brand-new cooperative art. By projecting her active stance onto a teammate or hireling, '
            'she does more than share elemental power: she <b>transforms how her allies\' own skills behave</b>, turning a Paladin\'s <i>Fist of the Heavens</i> into a lightning storm, '
            'widening his <i>Vengeance</i> and elemental auras, and letting an Assassin deploy fully charged sentries and amplified finishers without pause. '
            'Solo, she is a high-wire elemental duelist; in co-op, she is the catalyst that elevates every elemental fighter beside her.</p>'
            '</div>'
        ),
    }

    # Pixel coordinates on the 448x584 (half-size of 897x1169) stone tree image
    col_x_half = {1: (109 + 29) // 2, 2: (371 + 29) // 2, 3: (631 + 29) // 2}
    row_y_half = {
        1: (125 + 32) // 2,
        2: (305 + 32) // 2,
        3: (481 + 32) // 2,
        4: (662 + 32) // 2,
        5: (841 + 32) // 2,
        6: (1017 + 32) // 2,
    }

    def get_s(k: str) -> str:
        return s_map.get(k, s_map.get(k.capitalize(), k)) if k else ""

    calc_skills_data: Dict[str, dict] = {}
    referenced_missiles: set = set()

    class_sections_html = []
    for cls_code, cls_title, cls_subtitle, page_titles in class_meta:
        by_page: Dict[int, List[dict]] = {3: [], 2: [], 1: []}
        for r in sk_rows:
            if r.get("charclass") != cls_code:
                continue
            sd = sd_by_id.get(r.get("skilldesc", "").lower(), {})
            pg_s = sd.get("SkillPage", "")
            if pg_s not in ("1", "2", "3"):
                continue
            pg = int(pg_s)
            rw = int(sd.get("SkillRow") or "1")
            cl = int(sd.get("SkillColumn") or "1")
            cel = int(sd.get("IconCel") or "0")
            nm = s_map.get(sd.get("str name", ""), r["skill"])
            req_lvl = int(r.get("reqlevel") or "1")
            max_lvl = int(r.get("maxlvl") or "20")
            raw_prereqs = [
                r.get(f"reqskill{k}", "").strip()
                for k in (1, 2, 3)
                if r.get(f"reqskill{k}", "").strip()
            ]
            prereqs = [sk_name_by_raw.get(p, p) for p in raw_prereqs]
            icon_rel = icon_map.get((cls_code, cel), "")
            plain_tip, rich_html = _build_skill_data_summary(r, sd, miss_map, s_map)
            anchor_id = f"sk-{cls_code}-{r['*Id']}"

            # Collect raw skilldesc lines and missile references for the live JS D2R calculator
            raw_long = get_s(sd.get("str long", "")) or get_s(sd.get("str short", ""))
            lore_str = " — ".join(ln.strip() for ln in raw_long.splitlines() if ln.strip())
            desc_lines_js = []
            for prefix, mx in [("desc", 6), ("dsc2", 5)]:
                for i in range(1, mx + 1):
                    fn = sd.get(f"{prefix}line{i}", "").strip()
                    if fn:
                        ca_s = sd.get(f"{prefix}calca{i}", "").strip().strip('"').strip()
                        cb_s = sd.get(f"{prefix}calcb{i}", "").strip().strip('"').strip()
                        for m_match in re.findall(r"miss\('([^']+)'\.", ca_s + " " + cb_s):
                            referenced_missiles.add(m_match.lower())
                        desc_lines_js.append({
                            "fn": fn,
                            "ta": get_s(sd.get(f"{prefix}texta{i}", "")),
                            "tb": get_s(sd.get(f"{prefix}textb{i}", "")),
                            "ca": ca_s,
                            "cb": cb_s,
                        })
            syn_lines_js = []
            for i in range(1, 8):
                fn = sd.get(f"dsc3line{i}", "").strip()
                if fn:
                    ca_s = sd.get(f"dsc3calca{i}", "").strip().strip('"').strip()
                    cb_s = sd.get(f"dsc3calcb{i}", "").strip().strip('"').strip()
                    syn_lines_js.append({
                        "fn": fn,
                        "ta": get_s(sd.get(f"dsc3texta{i}", "")),
                        "tb": get_s(sd.get(f"dsc3textb{i}", "")),
                        "ca": ca_s,
                        "cb": cb_s,
                    })

            dm_list = []
            for mi in (1, 2, 3):
                mname = (sd.get(f"descmissile{mi}", "") or r.get("srvmissilea", "")).lower().strip()
                if mname:
                    referenced_missiles.add(mname)
                dm_list.append(mname)

            calc_skills_data[r["skill"]] = {
                "id": r["*Id"],
                "anchor": anchor_id,
                "rawName": r["skill"],
                "name": nm,
                "cls": cls_code,
                "page": pg,
                "row": rw,
                "col": cl,
                "reqlevel": req_lvl,
                "maxlvl": max_lvl,
                "reqskills": raw_prereqs,
                "prereqNames": prereqs,
                "lore": lore_str,
                "HitShift": int(r.get("HitShift") or 8),
                "manashift": int(r.get("manashift") or 8),
                "mana": int(r.get("mana") or 0),
                "lvlmana": int(r.get("lvlmana") or 0),
                "minmana": int(r.get("minmana") or 0),
                "ToHit": int(r.get("ToHit") or 0),
                "LevToHit": int(r.get("LevToHit") or 0),
                "ToHitCalc": r.get("ToHitCalc", "").strip().strip('"').strip(),
                "auralencalc": r.get("auralencalc", "").strip().strip('"').strip(),
                "EType": r.get("EType", ""),
                "EMin": [int(r.get("EMin") or 0)] + [int(r.get(f"EMinLev{k}") or 0) for k in range(1, 6)],
                "EMax": [int(r.get("EMax") or 0)] + [int(r.get(f"EMaxLev{k}") or 0) for k in range(1, 6)],
                "EDmgSymPerCalc": r.get("EDmgSymPerCalc", "").strip().strip('"').strip(),
                "MinDam": [int(r.get("MinDam") or 0)] + [int(r.get(f"MinLevDam{k}") or 0) for k in range(1, 6)],
                "MaxDam": [int(r.get("MaxDam") or 0)] + [int(r.get(f"MaxLevDam{k}") or 0) for k in range(1, 6)],
                "DmgSymPerCalc": r.get("DmgSymPerCalc", "").strip().strip('"').strip(),
                "ELen": [int(r.get("ELen") or 0)] + [int(r.get(f"ELevLen{k}") or 0) for k in range(1, 4)],
                "ELenSymPerCalc": r.get("ELenSymPerCalc", "").strip().strip('"').strip(),
                "Params": [int(r.get(f"Param{k}") or 0) for k in range(1, 13)],
                "Calcs": [r.get(f"calc{k}", "").strip().strip('"').strip() for k in range(1, 7)],
                "descmissiles": dm_list,
                "descLines": desc_lines_js,
                "synLines": syn_lines_js,
            }

            by_page[pg].append({
                "id": r["*Id"],
                "raw_name": r["skill"],
                "anchor": anchor_id,
                "name": nm,
                "row": rw,
                "col": cl,
                "reqlevel": req_lvl,
                "prereqs": prereqs,
                "icon": icon_rel,
                "plain_tip": plain_tip,
                "rich_html": rich_html,
            })

        trees_row_html = []
        tables_html = []
        for pg in (3, 2, 1):
            frame_idx = 3 - pg
            t_title = page_titles[pg]
            sk_list = sorted(by_page[pg], key=lambda x: (x["row"], x["col"]))

            overlay_nodes = []
            table_rows = []
            for sk in sk_list:
                px = col_x_half[sk["col"]]
                py = row_y_half[sk["row"]]
                prereq_str = ", ".join(sk["prereqs"]) if sk["prereqs"] else "None"
                tip_title = html.escape(sk["name"])
                tip_meta = f"Required Level: {sk['reqlevel']} | Prerequisites: {html.escape(prereq_str)}"
                tip_body = html.escape(sk["plain_tip"])
                raw_attr = html.escape(sk["raw_name"])
                overlay_nodes.append(
                    f'<a href="#{sk["anchor"]}" class="tree-icon-slot state-locked" '
                    f'id="slot-{sk["anchor"]}" data-skill="{raw_attr}" data-cls="{cls_code}" '
                    f'style="left:{px}px; top:{py}px;" '
                    f'data-name="{tip_title}" data-meta="{tip_meta}" data-desc="{tip_body}">'
                    f'<img src="{sk["icon"]}" width="47" height="46" class="tree-slot-art" alt="{tip_title}">'
                    f'<span class="tree-lvl-badge" id="badge-{sk["anchor"]}">0</span>'
                    f'<span class="tree-live-stat" id="livestat-{sk["anchor"]}"></span>'
                    f'</a>'
                )
                table_rows.append(
                    f'<tr id="{sk["anchor"]}">'
                    f'<td align="center" width="64" bgcolor="#0c0a08">'
                    f'<img src="{sk["icon"]}" width="48" height="47" class="sk-table-icon" alt="{tip_title}">'
                    f'</td>'
                    f'<td width="190" bgcolor="#120f0c">'
                    f'<b class="d2-gold">{tip_title}</b> '
                    f'<span class="sk-alloc-pill" id="tbl-pill-{sk["anchor"]}"></span><br>'
                    f'<span class="d2-dim">Req Level: <b>{sk["reqlevel"]}</b></span><br>'
                    f'<span class="d2-dim">Prereqs: {html.escape(prereq_str)}</span>'
                    f'</td>'
                    f'<td bgcolor="#0c0a08" class="sk-desc-cell">'
                    f'<div class="sk-live-row" id="tbl-live-{sk["anchor"]}"></div>'
                    f'{sk["rich_html"]}'
                    f'</td>'
                    f'</tr>'
                )

            tab_labels_html = []
            for tab_i, tab_pg in enumerate((3, 2, 1)):
                tab_cls = "tree-tab-label active" if tab_pg == pg else "tree-tab-label"
                tab_left = 2 + tab_i * 149
                tab_text = html.escape(page_titles[tab_pg]).replace(" &amp; ", "<br>&amp; ").replace(" ", "<br>", 1)
                tab_labels_html.append(
                    f'<div class="{tab_cls}" style="left:{tab_left}px;"><span>{tab_text}</span></div>'
                )

            trees_row_html.append(
                f'<td align="center" valign="top" bgcolor="#080705">'
                f'<div class="tree-plate-header">{html.escape(t_title)} '
                f'<span class="d2-dim" id="tree-pts-{cls_code}-{pg}">(0 pts)</span></div>'
                f'<div class="tree-canvas">'
                f'<img src="img/trees/{cls_code}_frame_{frame_idx}.png" width="448" height="584" class="tree-bg-img" alt="{html.escape(t_title)}">'
                f'{"".join(tab_labels_html)}'
                f'{"".join(overlay_nodes)}'
                f'</div>'
                f'</td>'
            )

            tables_html.append(
                f'<table width="100%" border="1" cellpadding="6" cellspacing="0" bordercolor="#4a3c28" class="arreat-table" style="margin-top:10px;">'
                f'<tr bgcolor="#261e14">'
                f'<th colspan="3" align="left" class="table-banner">{html.escape(cls_title)} — {html.escape(t_title)}</th>'
                f'</tr>'
                f'<tr bgcolor="#1a140e" class="table-subhdr">'
                f'<th width="64">Icon</th><th width="190" align="left">Skill &amp; Tier</th><th align="left">Effect &amp; Tactical Role</th>'
                f'</tr>'
                f'{"".join(table_rows)}'
                f'</table>'
            )

        class_sections_html.append(
            f'<div class="tab-panel" id="tab-class-{cls_code}">'
            f'<a name="class-{cls_code}"></a>'
            f'<div class="section-block">'
            f'<div class="section-title-bar">'
            f'<h2>{html.escape(cls_title.upper())} SKILL TREES &amp; INTERACTIVE BUILD CALCULATOR</h2>'
            f'<div class="section-sub">{html.escape(cls_subtitle)} — Hover any icon for live stats; Left-Click to allocate (+1 pt), Right-Click to remove (-1 pt), Shift+Click for 5 pts</div>'
            f'</div>'
            f'{class_lore_html.get(cls_code, "")}'
            f'<div class="calc-hud-bar" id="calc-hud-{cls_code}">'
            f'  <div class="calc-hud-left">'
            f'    <span class="calc-stat-box">Required Character Level: <b class="d2-bright-gold" id="calc-clvl-{cls_code}">1</b></span>'
            f'    <span class="calc-stat-box">Points Spent: <b class="d2-gold" id="calc-pts-{cls_code}">0</b> <span class="d2-dim">(+2 pts / level)</span></span>'
            f'    <span class="calc-gates" id="calc-gates-{cls_code}">'
            f'      <span class="gate-pill unlocked" data-gate="1">Lvl 1</span>'
            f'      <span class="gate-pill" data-gate="8">Lvl 8</span>'
            f'      <span class="gate-pill" data-gate="16">Lvl 16</span>'
            f'      <span class="gate-pill" data-gate="24">Lvl 24</span>'
            f'      <span class="gate-pill" data-gate="32">Lvl 32</span>'
            f'      <span class="gate-pill" data-gate="40">Lvl 40</span>'
            f'    </span>'
            f'  </div>'
            f'  <div class="calc-hud-right">'
            f'    <span class="calc-msg" id="calc-msg-{cls_code}">Click any unlocked Lvl 1 skill to begin</span>'
            f'    <button type="button" class="calc-reset-btn" data-reset-cls="{cls_code}">&#8634; Reset Skills</button>'
            f'  </div>'
            f'</div>'
            f'<table width="100%" border="1" cellpadding="6" cellspacing="0" bordercolor="#5c4b32" class="arreat-table">'
            f'<tr>{"".join(trees_row_html)}</tr>'
            f'</table>'
            f'<details class="compendium-drawer">'
            f'<summary>&#128214; Show Detailed 30-Skill Reference Compendium for {html.escape(cls_title)} (Level 1 / 8 / 16 / 20 Progression Tables)</summary>'
            f'{"".join(tables_html)}'
            f'</details>'
            f'</div>'
            f'</div>'
        )

    calc_missiles_data: Dict[str, dict] = {}
    for mname in sorted(referenced_missiles):
        mr = miss_map.get(mname, {})
        if not mr:
            continue
        emin_arr = [int(mr.get("EMin") or 0)] + [int(mr.get(f"MinELev{k}") or mr.get(f"EMinLev{k}") or 0) for k in range(1, 6)]
        emax_arr = [int(mr.get("EMax") or 0)] + [int(mr.get(f"MaxELev{k}") or mr.get(f"EMaxLev{k}") or 0) for k in range(1, 6)]
        pmin_arr = [int(mr.get("MinDamage") or 0)] + [int(mr.get(f"MinLevDam{k}") or 0) for k in range(1, 6)]
        pmax_arr = [int(mr.get("MaxDamage") or 0)] + [int(mr.get(f"MaxLevDam{k}") or 0) for k in range(1, 6)]
        calc_missiles_data[mname] = {
            "HitShift": int(mr.get("HitShift") or 8),
            "Range": (mr.get("Range") or "0").strip().strip('"').strip(),
            "LevRange": int(mr.get("LevRange") or 0),
            "EMin": emin_arr,
            "EMax": emax_arr,
            "MinDam": pmin_arr,
            "MaxDam": pmax_arr,
        }

    calc_payload_json = json.dumps({"skills": calc_skills_data, "missiles": calc_missiles_data}, separators=(",", ":"))

    # Build character generator payload (6 base64 .d2s templates, charstats.txt pools, and experience.txt curve)
    _, cstat_rows = _read_mod_tsv("charstats.txt")
    _, exp_rows = _read_mod_tsv("experience.txt")
    exp_by_lvl: Dict[int, int] = {1: 0}
    for er in exp_rows:
        lv_s = (er.get("Level") or "").strip()
        if lv_s.isdigit():
            exp_by_lvl[int(lv_s) + 1] = int(er.get("Amazon") or 0)
    exp_table_arr = [exp_by_lvl.get(lv, 0) for lv in range(100)]

    char_classes_data: Dict[str, dict] = {}
    class_order = [
        ("pal", 3, "Paladin"),
        ("bar", 4, "Barbarian"),
        ("ass", 6, "Assassin"),
        ("sor", 1, "Sorceress"),
        ("ama", 0, "Amazon"),
        ("nec", 2, "Necromancer"),
        ("dru", 5, "Druid"),
    ]
    cs_by_name = {r["class"]: r for r in cstat_rows if r.get("class")}
    for c_short, c_id, c_name in class_order:
        cr = cs_by_name.get(c_name, {})
        if cr:
            char_classes_data[c_short] = {
                "id": c_id,
                "name": c_name,
                "str": int(cr.get("str") or 0),
                "dex": int(cr.get("dex") or 0),
                "int": int(cr.get("int") or 0),
                "vit": int(cr.get("vit") or 0),
                "stamina": int(cr.get("stamina") or 0),
                "hpadd": int(cr.get("hpadd") or 0),
                "LifePerLevel": int(cr.get("LifePerLevel") or 0),
                "ManaPerLevel": int(cr.get("ManaPerLevel") or 0),
                "StaminaPerLevel": int(cr.get("StaminaPerLevel") or 0),
                "StatPerLevel": int(cr.get("StatPerLevel") or 5),
                "SkillsPerLevel": int(cr.get("SkillsPerLevel") or 2),
            }

    tmpl_b64_map: Dict[str, str] = {}
    for slot_name, _slot_desc in TIER_TEMPLATE_SLOTS:
        tp = os.path.join(TEMPLATE_DIR, f"{slot_name}.d2s")
        if os.path.exists(tp):
            with open(tp, "rb") as tf:
                tmpl_b64_map[slot_name] = base64.b64encode(tf.read()).decode("ascii")

    char_gen_payload_json = json.dumps(
        {
            "classes": char_classes_data,
            "exp": exp_table_arr,
            "templates": tmpl_b64_map,
        },
        separators=(",", ":"),
    )

    # Build 7 Gem & Skull Families table dynamically from gems.txt and misc.txt
    gem_families = [
        ("Ruby", "Fire", 'class="d2-red"', ["gcr", "gfr", "gsr", "glr", "gpr"]),
        ("Sapphire", "Cold", 'class="d2-blue"', ["gcb", "gfb", "gsb", "glb", "gpb"]),
        ("Topaz", "Lightning", 'class="d2-yellow"', ["gcy", "gfy", "gsy", "gly", "gpy"]),
        ("Emerald", "Poison", 'class="d2-green"', ["gcg", "gfg", "gsg", "glg", "gpg"]),
        ("Diamond", "Arcane", 'style="color:#ffffff;"', ["gcw", "gfw", "gsw", "glw", "gpw"]),
        ("Amethyst", "Physical", 'style="color:#c878ff;"', ["gcv", "gfv", "gsv", "gzv", "gpv"]),
        ("Skull", "Attrition", 'class="d2-gold"', ["skc", "skf", "sku", "skl", "skz"]),
    ]
    gem_tier_reqs = [misc_by_code.get(c, {}).get("levelreq", "1") or "1" for c in ["gcr", "gfr", "gsr", "glr", "gpr"]]
    gem_rows_html: List[str] = []
    for f_idx, (fam_name, fam_sub, fam_style, f_codes) in enumerate(gem_families):
        bg_attr = ' bgcolor="#120e0a"' if f_idx % 2 == 1 else ""
        slot_defs = [
            ("weapon", "Martial Weapon / Gloves (0.6x) / Ring (0.5x)"),
            ("helm", "Armor & Staff (1.0x) / Helm, Orb & Wand (0.75x) / Boots-Belt (0.6x) / Amulet (0.5x)"),
            ("shield", "Shield / Off-Hand (1.0x)"),
        ]
        for s_idx, (s_prefix, s_label) in enumerate(slot_defs):
            cells = []
            for t_idx, gc in enumerate(f_codes):
                gr = gems_by_code[gc]
                mod_txt = html.escape(
                    _format_gem_or_rune_mod(
                        gr[f"{s_prefix}Mod1Code"],
                        gr[f"{s_prefix}Mod1Param"],
                        gr[f"{s_prefix}Mod1Min"],
                        gr[f"{s_prefix}Mod1Max"],
                        prop_map,
                        isc_map,
                        s_map,
                    )
                )
                if t_idx == 4:
                    mod_txt = f"<b>{mod_txt}</b>"
                cells.append(f'<td align="center">{mod_txt}</td>')
            first_col = (
                f'<td rowspan="3"><b {fam_style}>{html.escape(fam_name)}</b><br>'
                f'<span class="d2-dim">({html.escape(fam_sub)})</span></td>'
                if s_idx == 0
                else ""
            )
            gem_rows_html.append(f"<tr{bg_attr}>{first_col}<td>{s_label}</td>{''.join(cells)}</tr>")

    # Build 33 Semantic Runes table dynamically from gems.txt, misc.txt, and item-runes.json
    rune_rows_html: List[str] = []
    for r_num in range(1, 34):
        rc = f"r{r_num:02d}"
        gr = gems_by_code[rc]
        mr = misc_by_code.get(rc, {})
        r_name = s_map.get(rc, gr.get("name", rc))
        r_lvl = mr.get("levelreq", "1") or "1"
        bg_attr = ' bgcolor="#120e0a"' if r_num % 2 == 0 else ""
        w_txt = html.escape(_format_gem_or_rune_mod(gr["weaponMod1Code"], gr["weaponMod1Param"], gr["weaponMod1Min"], gr["weaponMod1Max"], prop_map, isc_map, s_map))
        h_txt = html.escape(_format_gem_or_rune_mod(gr["helmMod1Code"], gr["helmMod1Param"], gr["helmMod1Min"], gr["helmMod1Max"], prop_map, isc_map, s_map))
        s_txt = html.escape(_format_gem_or_rune_mod(gr["shieldMod1Code"], gr["shieldMod1Param"], gr["shieldMod1Min"], gr["shieldMod1Max"], prop_map, isc_map, s_map))
        rune_rows_html.append(
            f"<tr{bg_attr}>"
            f'<td align="center">{rc}</td>'
            f'<td><span class="d2-orange">{html.escape(r_name)}</span> (Lvl {html.escape(r_lvl)})</td>'
            f"<td>{w_txt}</td><td>{h_txt}</td><td>{s_txt}</td>"
            f"</tr>"
        )

    html_doc = f"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>The Castalia Compendium - Diablo II: Resurrected Tactical Overhaul</title>
<style type="text/css">
  body {{
    background-color: #000000;
    background-image: radial-gradient(circle at 50% 0%, #1a120b 0%, #050403 45%, #000000 100%);
    color: #d4c8b0;
    font-family: Verdana, Tahoma, Arial, Helvetica, sans-serif;
    font-size: 12px;
    line-height: 1.5;
    margin: 0;
    padding: 0;
  }}
  a:link, a:visited {{
    color: #c7b377;
    text-decoration: underline;
  }}
  a:hover {{
    color: #ffffff;
    background-color: #2b2114;
    text-decoration: none;
  }}
  h1, h2, h3, .gothic-hdr, .table-banner, .tree-plate-header {{
    font-family: "Exocet", "Cinzel", "Palatino Linotype", "Book Antiqua", Georgia, serif;
    letter-spacing: 1px;
  }}
  .d2-gold {{ color: #c7b377; }}
  .d2-bright-gold {{ color: #f0d890; font-weight: bold; }}
  .d2-blue {{ color: #6969ff; font-weight: bold; }}
  .d2-yellow {{ color: #ffff00; font-weight: bold; }}
  .d2-orange {{ color: #ff9900; font-weight: bold; }}
  .d2-green {{ color: #00e600; font-weight: bold; }}
  .d2-unique {{ color: #b8a472; font-weight: bold; }}
  .d2-red {{ color: #ff4d4d; font-weight: bold; }}
  .d2-dim {{ color: #8c8270; font-size: 11px; }}

  /* Arreat Summit Frame Layout */
  .top-banner {{
    background: linear-gradient(180deg, #24190e 0%, #0d0906 60%, #000000 100%);
    border-bottom: 2px ridge #7a633e;
    padding: 14px 20px 10px 20px;
    text-align: center;
  }}
  .top-banner h1 {{
    color: #c7b377;
    font-size: 28px;
    margin: 0;
    text-shadow: 2px 2px 0px #000000, 0 0 12px #804000;
    letter-spacing: 3px;
  }}
  .top-banner .subtitle {{
    color: #9e8f74;
    font-size: 11px;
    margin-top: 4px;
  }}
  .sidebar-cell {{
    background-color: #0b0907;
    border-right: 2px ridge #5c4b32;
    width: 215px;
    padding: 10px;
  }}
  .nav-box {{
    border: 1px solid #4a3c28;
    background-color: #120e0a;
    margin-bottom: 12px;
  }}
  .nav-box-hdr {{
    background: linear-gradient(180deg, #332617 0%, #1c140c 100%);
    border-bottom: 1px solid #5c4b32;
    color: #f0d890;
    font-family: "Palatino Linotype", Georgia, serif;
    font-size: 12px;
    font-weight: bold;
    padding: 5px 8px;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .nav-list {{
    list-style-type: square;
    color: #7a633e;
    margin: 6px 8px 8px 22px;
    padding: 0;
    font-size: 11px;
  }}
  .nav-list li {{
    margin-bottom: 4px;
  }}
  .content-cell {{
    padding: 16px 22px 40px 22px;
    max-width: 1440px;
  }}
  .section-block {{
    margin-bottom: 32px;
  }}
  .section-title-bar {{
    background: linear-gradient(90deg, #2b1f12 0%, #140f09 65%, #000000 100%);
    border: 1px ridge #6e5838;
    padding: 7px 12px;
    margin-bottom: 10px;
  }}
  .section-title-bar h2 {{
    color: #f0d890;
    font-size: 16px;
    margin: 0;
  }}
  .section-title-bar .section-sub {{
    color: #a3957b;
    font-size: 11px;
    margin-top: 2px;
  }}
  .arreat-table {{
    border-collapse: collapse;
    border: 2px ridge #5c4b32;
    background-color: #0b0907;
    font-size: 12px;
  }}
  .arreat-table th, .arreat-table td {{
    border: 1px solid #382d1e;
  }}
  .table-banner {{
    color: #f0d890;
    font-size: 14px;
    padding: 6px 10px;
    background: linear-gradient(90deg, #302314 0%, #17110a 100%);
  }}
  .table-subhdr th {{
    color: #c7b377;
    font-size: 11px;
    text-transform: uppercase;
    padding: 5px 8px;
  }}
  .quote-box {{
    background-color: #110d09;
    border: 1px inset #4a3c28;
    padding: 10px 14px;
    margin-bottom: 12px;
    color: #cbbd9f;
  }}

  /* Interactive Stone Skill Tree Canvas (448x584) */
  .tree-plate-header {{
    background-color: #1f170e;
    border: 1px solid #5c4b32;
    color: #f0d890;
    font-size: 13px;
    font-weight: bold;
    padding: 4px 6px;
    margin-bottom: 4px;
    width: 436px;
  }}
  .tree-canvas {{
    position: relative;
    width: 448px;
    height: 584px;
    border: 2px inset #6e5838;
    margin: 0 auto;
    overflow: hidden;
  }}
  .tree-bg-img {{
    position: absolute;
    left: 0;
    top: 0;
    width: 448px;
    height: 584px;
    display: block;
    z-index: 1;
  }}
  .tree-tab-label {{
    position: absolute;
    top: 4px;
    width: 146px;
    height: 40px;
    z-index: 3;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    font-family: "Exocet", "Cinzel", "Palatino Linotype", Georgia, serif;
    font-size: 11px;
    font-weight: bold;
    line-height: 1.15;
    color: #857760;
    text-shadow: 1px 1px 2px #000000;
    text-transform: uppercase;
    pointer-events: none;
  }}
  .tree-tab-label.active {{
    color: #f0d890;
    text-shadow: 1px 1px 2px #000000, 0 0 8px #805500;
  }}
  .tree-icon-slot {{
    position: absolute;
    width: 47px;
    height: 46px;
    display: block;
    border: 1px solid transparent;
    text-decoration: none;
    z-index: 5;
    cursor: pointer;
    user-select: none;
  }}
  .tree-slot-art {{
    position: absolute;
    left: 0;
    top: 0;
    width: 47px;
    height: 46px;
    display: block;
    pointer-events: none;
    transition: filter 0.12s ease;
  }}
  .tree-icon-slot.state-locked .tree-slot-art {{
    filter: grayscale(100%) brightness(0.32) contrast(1.1);
  }}
  .tree-icon-slot.state-avail .tree-slot-art {{
    filter: grayscale(88%) brightness(0.58);
  }}
  .tree-icon-slot.state-avail:hover .tree-slot-art {{
    filter: grayscale(30%) brightness(0.88);
  }}
  .tree-icon-slot.state-alloc .tree-slot-art {{
    filter: none;
  }}
  .tree-icon-slot.state-alloc {{
    border: 1px solid rgba(240, 216, 144, 0.55);
    box-shadow: 0 0 6px rgba(255, 170, 0, 0.35);
  }}
  .tree-icon-slot:hover {{
    border: 1px solid #f0d890;
    box-shadow: 0 0 10px #ffaa00;
    background-color: rgba(255, 200, 80, 0.12);
    z-index: 10;
  }}
  .tree-lvl-badge {{
    position: absolute;
    left: 65px;
    top: 29px;
    width: 24px;
    height: 22px;
    line-height: 22px;
    text-align: center;
    color: #6b5e4c;
    font-size: 10px;
    font-weight: bold;
    font-family: Tahoma, sans-serif;
    text-shadow: 1px 1px 1px #000000;
    pointer-events: none;
  }}
  .tree-icon-slot.state-avail .tree-lvl-badge {{
    color: #a8987e;
  }}
  .tree-icon-slot.state-alloc .tree-lvl-badge {{
    color: #f0d890;
    font-size: 11px;
    text-shadow: 1px 1px 2px #000000, 0 0 5px #805500;
  }}
  .tree-live-stat {{
    position: absolute;
    left: -10px;
    top: 47px;
    width: 92px;
    text-align: center;
    font-size: 9px;
    font-family: Tahoma, Verdana, sans-serif;
    font-weight: bold;
    color: #78a8ff;
    background-color: rgba(8, 6, 4, 0.90);
    border: 1px solid #5c4b32;
    padding: 1px 2px;
    line-height: 1.15;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: none;
    pointer-events: none;
    z-index: 9;
    text-shadow: 1px 1px 1px #000000;
  }}
  .tree-icon-slot.state-alloc .tree-live-stat {{
    display: block;
  }}

  /* Character Build Calculator HUD Bar */
  .calc-hud-bar {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(180deg, #1f170f 0%, #100c08 100%);
    border: 2px ridge #6e5838;
    padding: 7px 12px;
    margin-bottom: 8px;
    gap: 8px;
  }}
  .calc-hud-left, .calc-hud-right {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
  }}
  .calc-stat-box {{
    background-color: #0b0907;
    border: 1px inset #4a3c28;
    padding: 3px 9px;
    font-size: 12px;
    color: #d4c8b0;
  }}
  .calc-gates {{
    display: inline-flex;
    gap: 4px;
    align-items: center;
  }}
  .gate-pill {{
    background-color: #14100b;
    border: 1px solid #3a2e1e;
    color: #665a48;
    font-size: 10px;
    font-weight: bold;
    padding: 2px 6px;
  }}
  .gate-pill.unlocked {{
    background-color: #291e10;
    border-color: #8c734b;
    color: #f0d890;
    box-shadow: 0 0 4px rgba(240, 216, 144, 0.25);
  }}
  .calc-msg {{
    color: #a8987e;
    font-size: 11px;
    font-style: italic;
  }}
  .calc-msg.warn {{
    color: #ff6b6b;
    font-style: normal;
    font-weight: bold;
  }}
  .calc-reset-btn {{
    background: linear-gradient(180deg, #3b2816 0%, #1e140b 100%);
    border: 1px outset #8c734b;
    color: #f0d890;
    font-family: "Exocet", "Cinzel", "Palatino Linotype", Georgia, serif;
    font-size: 11px;
    font-weight: bold;
    padding: 4px 10px;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .calc-reset-btn:hover {{
    background: linear-gradient(180deg, #52381f 0%, #2b1d10 100%);
    color: #ffffff;
  }}
  .sk-alloc-pill {{
    display: inline-block;
    background-color: #291e10;
    border: 1px solid #8c734b;
    color: #f0d890;
    font-size: 10px;
    font-weight: bold;
    padding: 0 5px;
    margin-left: 4px;
  }}
  .sk-alloc-pill:empty {{
    display: none;
  }}
  .sk-live-row {{
    background-color: #16110b;
    border-left: 3px solid #f0d890;
    padding: 4px 8px;
    margin-bottom: 5px;
    font-size: 11px;
  }}
  .sk-live-row:empty {{
    display: none;
  }}
  .sk-table-icon {{
    border: 1px ridge #6e5838;
  }}
  .sk-desc-cell {{
    color: #d8ccb8;
    line-height: 1.45;
  }}

  /* Floating In-Game D2 Tooltip */
  #d2-tooltip {{
    position: fixed;
    display: none;
    pointer-events: none;
    background-color: rgba(0, 0, 0, 0.95);
    border: 2px ridge #8c734b;
    padding: 9px 13px;
    max-width: 370px;
    z-index: 9999;
    text-align: center;
    box-shadow: 4px 4px 0px #000000;
  }}
  #d2-tooltip .tt-name {{
    color: #c7b377;
    font-family: "Palatino Linotype", Georgia, serif;
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 3px;
  }}
  #d2-tooltip .tt-meta {{
    color: #6969ff;
    font-size: 11px;
    margin-bottom: 5px;
  }}
  #d2-tooltip .tt-desc {{
    color: #ffffff;
    font-size: 11px;
    line-height: 1.42;
  }}
  .retro-footer {{
    border-top: 2px ridge #4a3c28;
    margin-top: 30px;
    padding-top: 12px;
    text-align: center;
    font-size: 10px;
    color: #786d5c;
  }}

  /* Top Web 1.0 Arreat Summit Tab Bar & Single-View Panels */
  .top-tab-bar {{
    background: linear-gradient(180deg, #1b140c 0%, #0d0906 100%);
    border-bottom: 2px ridge #7a633e;
    padding: 8px 12px 0 12px;
    text-align: center;
    white-space: nowrap;
    overflow-x: auto;
  }}
  .top-tab-btn {{
    display: inline-block;
    background: linear-gradient(180deg, #281d11 0%, #140e08 100%);
    border: 2px outset #6e5838;
    border-bottom: none;
    color: #b8a472;
    font-family: "Exocet", "Cinzel", "Palatino Linotype", Georgia, serif;
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 0.5px;
    padding: 7px 14px 6px 14px;
    margin: 0 2px;
    cursor: pointer;
    text-decoration: none;
    user-select: none;
  }}
  .top-tab-btn:hover {{
    background: linear-gradient(180deg, #382817 0%, #1d150c 100%);
    color: #ffffff;
  }}
  .top-tab-btn.active {{
    background: linear-gradient(180deg, #4b361e 0%, #24190d 100%);
    border-color: #c7b377;
    color: #f0d890;
    text-shadow: 0 0 8px #805500;
    position: relative;
    top: 1px;
    padding-bottom: 7px;
  }}
  .tab-panel {{
    display: none;
  }}
  .tab-panel.active {{
    display: block;
  }}
  .compendium-drawer {{
    margin-top: 14px;
    background-color: #110d09;
    border: 1px ridge #5c4b32;
    padding: 8px 12px;
  }}
  .compendium-drawer summary {{
    color: #f0d890;
    font-family: "Palatino Linotype", Georgia, serif;
    font-size: 13px;
    font-weight: bold;
    cursor: pointer;
    user-select: none;
  }}
  .compendium-drawer summary:hover {{
    color: #ffffff;
  }}
</style>
</head>
<body>

<div id="d2-tooltip">
  <div class="tt-name" id="tt-name"></div>
  <div class="tt-meta" id="tt-meta"></div>
  <div class="tt-desc" id="tt-desc"></div>
</div>

<!-- TOP ARREAT SUMMIT BANNER -->
<div class="top-banner">
  <h1>&#9876; THE CASTALIA COMPENDIUM &#9876;</h1>
  <div class="subtitle">Official Strategy Guide &amp; Horadric Grimoire for <b>Diablo II: Resurrected — Castalia</b></div>
</div>

<!-- TOP ARREAT SUMMIT NAVIGATION TABS -->
<div class="top-tab-bar" id="top-tab-bar">
  <a href="#overview" class="top-tab-btn active" data-tab="tab-overview">&#9876; Overview &amp; Cube</a>
  <a href="#char-generator" class="top-tab-btn" data-tab="tab-chargen">&#11015; Character Generator (.d2s)</a>
  <a href="#class-pal" class="top-tab-btn" data-tab="tab-class-pal">Paladin</a>
  <a href="#class-bar" class="top-tab-btn" data-tab="tab-class-bar">Barbarian</a>
  <a href="#class-ass" class="top-tab-btn" data-tab="tab-class-ass">Assassin</a>
  <a href="#class-sor" class="top-tab-btn" data-tab="tab-class-sor">Sorceress</a>
  <a href="#gems-skulls" class="top-tab-btn" data-tab="tab-items">&#9874; Gems &amp; 33 Runes</a>
  <a href="#monsters" class="top-tab-btn" data-tab="tab-world">Monsters &amp; Mercs</a>
</div>

<table width="100%" border="0" cellpadding="0" cellspacing="0">
<tr>
  <!-- LEFT NAVIGATION SIDEBAR -->
  <td valign="top" class="sidebar-cell">
    <div class="nav-box">
      <div class="nav-box-hdr">Getting Started</div>
      <ul class="nav-list">
        <li><a href="#overview" data-tab-link="tab-overview">Overview &amp; 7 Cube Recipes</a></li>
        <li><a href="#char-generator" data-tab-link="tab-chargen"><b class="d2-bright-gold">Join Campaign (.d2s)</b></a></li>
        <li><a href="#philosophy" data-tab-link="tab-overview">Design Philosophy</a></li>
      </ul>
    </div>

    <div class="nav-box">
      <div class="nav-box-hdr">Class Calculators</div>
      <ul class="nav-list">
        <li><a href="#class-pal" data-tab-link="tab-class-pal"><b class="d2-gold">Paladin</b> (30 Skills)</a></li>
        <li><a href="#class-bar" data-tab-link="tab-class-bar"><b class="d2-gold">Barbarian</b> (30 Skills)</a></li>
        <li><a href="#class-ass" data-tab-link="tab-class-ass"><b class="d2-gold">Assassin</b> (30 Skills)</a></li>
        <li><a href="#class-sor" data-tab-link="tab-class-sor"><b class="d2-gold">Sorceress</b> (30 Skills)</a></li>
      </ul>
    </div>

    <div class="nav-box">
      <div class="nav-box-hdr">Items &amp; World</div>
      <ul class="nav-list">
        <li><a href="#gems-skulls" data-tab-link="tab-items">7 Gem &amp; Skull Families</a></li>
        <li><a href="#runes-33" data-tab-link="tab-items">The 33 Semantic Runes</a></li>
        <li><a href="#monsters" data-tab-link="tab-world">4 Monster Archetypes</a></li>
        <li><a href="#mercenaries" data-tab-link="tab-world">10-Slot Mercenaries</a></li>
      </ul>
    </div>

    <div class="nav-box" style="padding:8px; text-align:center;">
      <img src="img/items/lockbox_gold.png" width="52" height="52" alt="Lockbox"><br>
      <span class="d2-dim"><i>"A few honest rules, pieced together carefully, yield near-infinite room for creativity."</i></span>
    </div>
  </td>

  <!-- MAIN CONTENT AREA -->
  <td valign="top" class="content-cell">

    <!-- TAB 1: OVERVIEW, 7 CUBE RECIPES & DESIGN PHILOSOPHY -->
    <div class="tab-panel active" id="tab-overview">
    <a name="overview"></a>
    <a name="quickstart"></a>
    <div class="section-block">
      <div class="section-title-bar">
        <h2>QUICK START: WHAT TO EXPECT IN SANCTUARY</h2>
        <div class="section-sub">A grounded, tactical overhaul built for solo purists and co-op expeditions</div>
      </div>

      <div class="quote-box">
        <p style="margin-top:0;"><b>Castalia</b> is built for <b>veteran Diablo II players</b> who want to experiment with a reimagined skill and resource economy—experiencing a more grounded, tactical version of <i>Diablo II</i> rather than an overpowered power-fantasy.</p>
        <ul style="margin-bottom:0;">
          <li><b>Playthrough-Focused (Solo or Co-op):</b> Designed to be played alone or with friends as a complete expedition from Act 1 Normal through Act 5 Hell. Need a starter character to join a friend's game? Open the <a href="#char-generator" data-tab-link="tab-chargen"><b class="d2-bright-gold">Character Generator (.d2s)</b></a> tab above.</li>
          <li><b>What You See Is How It Works:</b> Every monster prints its <span class="d2-gold">elemental vulnerability, resistance, and combat trait</span> directly beneath its health bar. Physical silhouettes tell the truth: if a monster is <b>small</b>, it is fast, numerous, and fragile; if it is <b>huge</b>, it is slow, solitary, and hits like a truck.</li>
          <li><b>Diegetic Item Archetypes:</b> Every piece of gear behaves like what it actually is—and rolls affixes to match. Light armor and bucklers lean into agility, stamina, and casting speed; heavy plate and tower shields anchor raw defense, strength, and damage reduction at the cost of weight; blunt weapons crush with raw force while daggers and bows favor speed and precision; and caster plates, masks, and bone gear naturally attract magical properties. You can read an item's role at a glance and find meaningful upgrades directly out in the world.</li>
        </ul>
      </div>

      <a name="cube-recipes"></a>
      <table width="100%" border="1" cellpadding="6" cellspacing="0" bordercolor="#5c4b32" class="arreat-table">
        <tr bgcolor="#261e14">
          <th colspan="3" align="left" class="table-banner">&#9874; THE 7 HORADRIC CUBE RECIPES (ALL YOU NEED TO PLAY)</th>
        </tr>
        <tr bgcolor="#1a140e" class="table-subhdr">
          <th width="22%" align="left">Recipe Purpose</th>
          <th width="38%" align="left">Horadric Cube Inputs</th>
          <th width="40%" align="left">Resulting Output</th>
        </tr>
        <tr>
          <td><span class="d2-orange">1. Craft Any Item</span></td>
          <td><span class="d2-blue">Any Magic Item</span> + <b>1 Gem / Skull</b> + <span class="d2-orange">2 Runes</span></td>
          <td><span class="d2-orange">Crafted Item</span> stamped with the Gem's stat + both Runes' stats <i>(scaled by Gem tier)</i> + <code>1–4</code> random affixes</td>
        </tr>
        <tr bgcolor="#120e0a">
          <td><span class="d2-orange">2. Distill a Unique / Set</span></td>
          <td><span class="d2-unique">Any Unique</span> or <span class="d2-green">Set Item</span> + <span class="d2-blue">Blacksmith's Malus</span> + <span class="d2-blue">Magic Jewel</span></td>
          <td><span class="d2-orange">Crafted Jewel</span> containing that Unique or Set item's <b>Top 4 signature stats</b></td>
        </tr>
        <tr>
          <td><span class="d2-bright-gold">3. Punch Sockets</span></td>
          <td><b>Unsocketed Weapon / Armor</b> + <span class="d2-blue">Blacksmith's Malus</span> + <b>Perfect Skull</b></td>
          <td>Punches sockets by quality: <span class="d2-blue">Magic</span> <b>2&ndash;3</b>, <span class="d2-yellow">Rare</span> / <span class="d2-orange">Crafted</span> <b>1&ndash;2</b>, <span class="d2-unique">Unique</span> / <span class="d2-green">Set</span> <b>1</b> <i>(capped by base item max)</i></td>
        </tr>
        <tr bgcolor="#120e0a">
          <td><span class="d2-bright-gold">4. Clear Sockets</span></td>
          <td><b>Socketed Weapon / Armor</b> + <span class="d2-blue">Blacksmith's Malus</span> + <b>Perfect Skull</b></td>
          <td><b>Clears all sockets</b> on the item <i>(destroying socketed contents so you can re-socket)</i></td>
        </tr>
        <tr>
          <td><span class="d2-yellow">5. Upgrade Base Tier</span></td>
          <td><b>Normal or Exceptional Item</b> + <span class="d2-yellow">Tempered Malus</span> <i>(Charsi Quest)</i></td>
          <td>Upgrades base tier (<b>Normal &rarr; Exceptional</b> or <b>Exceptional &rarr; Elite</b>; strictly 3 per playthrough)</td>
        </tr>
        <tr bgcolor="#120e0a">
          <td><span class="d2-gold">6. Combine / Split Runes &amp; Gems</span></td>
          <td><b>2x Identical Gems/Runes</b> <i>—or—</i> <span class="d2-orange">1x Rune</span> + <b>1x Gem</b></td>
          <td><b>Upgrades 2-to-1</b> into next tier <i>—or—</i> <b>Splits</b> a Rune into lower runes (<code>50%</code> to <code>100%</code> recovery by Gem tier)</td>
        </tr>
        <tr>
          <td><span class="d2-unique">7. Unlock a Lockbox</span></td>
          <td><img src="img/items/lockbox_wood.png" width="22" height="22" align="absmiddle"> <b>Crude / Iron / Ornate Lockbox</b> + <img src="img/items/key_crude.png" width="22" height="22" align="absmiddle"> <b>Matching Key</b></td>
          <td>Unlocks the <span class="d2-unique">Unique</span> or <span class="d2-green">Set</span> item sealed inside <i>(Keys sold by town vendors for 5k / 25k / 50k Gold)</i></td>
        </tr>
      </table>
    </div>

    <!-- CORE DESIGN PHILOSOPHY -->
    <a name="philosophy"></a>
    <div class="section-block">
      <div class="section-title-bar">
        <h2>CORE DESIGN PRINCIPLES &amp; WORLD RULES</h2>
        <div class="section-sub">First-principles itemization, an unbroken dungeon frame, and a real Gold standard</div>
      </div>

      <table width="100%" border="1" cellpadding="8" cellspacing="0" bordercolor="#4a3c28" class="arreat-table">
        <tr>
          <td width="50%" valign="top" bgcolor="#0e0b08">
            <h3 class="d2-bright-gold" style="margin-top:0;">1. First Principles Over Flashcards <sup>(1)</sup></h3>
            <p>Traditional Runewords reward flashcard memorization—looking up arbitrary rune sequences whose individual pieces have little connection to the final result. By stripping away Runewords and giving every Gem, Skull, and Rune a single, consistent rule, Castalia lets you engineer over <b>385,000 crafting combinations</b> from first principles.</p>

            <h3 class="d2-bright-gold">2. Keeping the World Intact <sup>(2)</sup></h3>
            <p>Town Portals, Rejuvenation Potions, and universal <code>Teleport</code> do not exist. Health and Mana potions restore over <b>3.0 seconds</b> on a <b>3.0-second cooldown</b>, and <img src="img/items/elixir.png" width="18" height="18" align="absmiddle"> <b>Preparation Elixirs</b> (<i>Thawing, Antidote, Stamina</i>) last <b>5 minutes</b>. In the dungeon, you fight to control <b>Wells</b> (100% refill every 10s) and <b>Recovery Shrines</b> (60s recharge).</p>
          </td>
          <td width="50%" valign="top" bgcolor="#0e0b08">
            <h3 class="d2-bright-gold" style="margin-top:0;">3. Every Item Color Has Its Own Crown &amp; No Free Immunity Breakers <sup>(3)</sup></h3>
            <ul>
              <li><span class="d2-blue">Magic (Blue):</span> 2 affixes max, but rolls <b>1.33x higher single-stat ceilings</b> and exclusive binary traits (<i>Ignore Target's Defense, Knockback, Jeweler's</i>).</li>
              <li><span class="d2-yellow">Rare (Yellow):</span> Up to 6 affixes with low-level junk tiers pruned out at higher levels.</li>
              <li><span class="d2-orange">Crafted (Orange):</span> Stamps 1 Gem/Skull + 2 Runes onto any slot alongside 1–4 random rolls.</li>
              <li><span class="d2-unique">Uniques</span> &amp; <span class="d2-green">Sets:</span> Distinct cross-class skills, auras, and procs—or distillable into Crafted Jewels.</li>
              <li><b>No Free Immunity Breakers:</b> Sunder Charms and player <code>-Enemy Elemental Resistance %</code> pierce do not exist; overcoming <code>95%–99%</code> resistant monsters requires a multi-element, physical, or mercenary toolkit.</li>
            </ul>

            <h3 class="d2-bright-gold" id="gold-economy">4. The Combat Gold Standard <sup>(4)(5)(6)(7)</sup></h3>
            <p>Vendors cap sell-back prices at <code>500g / 1,500g / 3,500g</code> so you never haul scrap metal back to town. Gold comes from killing monsters, popping Super Chests, and stacking <b>Gold Find</b>—and is spent on <b>75%-cost Equipment Repairs</b>, <b>Blacksmith's Maluses</b> (scaling with character level at the Gamble screen), <b>Lockbox Keys</b> (<code>5k / 25k / 50k</code>), <b>Charsi's Untempered Malus</b> (<code>100k</code>), and <b>Act-Partitioned Magic Vendors</b>.</p>
          </td>
        </tr>
      </table>

      <details class="compendium-drawer">
        <summary>&#128218; Theoretical Influences &amp; Design Notes (1–7)</summary>
        <div class="quote-box" style="font-size:11px; margin-top:8px; margin-bottom:0;">
          <ol style="margin:4px 0 4px 18px; padding:0;">
            <li><b>Combinatorial Grammar:</b> Inspired by Hermann Hesse's <i>Das Glasperlenspiel</i> (<i>The Glass Bead Game</i>, 1943), where a small, transparent alphabet of symbols yields near-infinite combinations without arbitrary exceptions.</li>
            <li><b>The Magic Circle &amp; Diegetic Space:</b> Draws on Johan Huizinga's <i>Homo Ludens</i> (1938) and the concept of the <i>Magic Circle</i>—the fragile boundary that gives play-worlds their emotional gravity so long as instant escape hatches do not break the frame.</li>
            <li><b>Pareto Frontiers &amp; Non-Dominated Strategies:</b> Rooted in multi-objective game theory and Pareto optimality, ensuring that Magic, Rare, Crafted, and Unique/Set items occupy distinct strengths rather than collapsing into a single dominant meta.</li>
            <li><b>Bounded Rationality &amp; Signal-to-Noise:</b> Informed by Herbert Simon's <i>Bounded Rationality</i>, Daniel Kahneman's <i>System 1 / System 2</i> attention model, and Barry Schwartz's <i>The Paradox of Choice</i>.</li>
            <li><b>Loss Aversion &amp; Asymmetric Tradeoffs:</b> Draws on Daniel Kahneman and Amos Tversky's <i>Prospect Theory</i> (1979), using voluntary vulnerabilities (Kiss-Curse items and Elemental Stances) to make build-defining power feel earned.</li>
            <li><b>Homeostatic Flow:</b> Based on Mihaly Csikszentmihalyi's <i>Flow</i> (1990), coupling skill effectiveness to oscillating resource pendulums (Stamina, Aura Mana Upkeep, Held Combo Orbs, and Stance Dials).</li>
            <li><b>Sound Money, Marginal Utility &amp; Reinforcement Schedules:</b> Draws on Carl Menger's theory of marginal utility (1871), intertemporal opportunity cost, and B.F. Skinner's reinforcement schedules—preventing extinction of reinforcement during dry loot streaks by anchoring Gold to combat.</li>
          </ol>
        </div>
      </details>
    </div>
    </div>

    <!-- TAB 2: CO-OP CAMPAIGN & CHARACTER SAVE (.D2S) GENERATOR -->
    <div class="tab-panel" id="tab-chargen">
    <a name="char-generator"></a>
    <div class="section-block">
      <div class="section-title-bar">
        <h2>CO-OP CAMPAIGN &amp; STARTER CHARACTER SAVE (<code>.d2s</code>) GENERATOR</h2>
        <div class="section-sub">Generate a ready-to-play character with a unique party name, tier starter kit, and unlocked waypoints</div>
      </div>

      <table width="100%" border="1" cellpadding="8" cellspacing="0" bordercolor="#7a633e" class="arreat-table" style="margin-bottom:14px;">
        <tr bgcolor="#2b1f12">
          <th colspan="2" align="left" class="table-banner">&#9876; JOIN A CO-OP CAMPAIGN OR GENERATE A STARTER CHARACTER SAVE (<code>.d2s</code>)</th>
        </tr>
        <tr>
          <td width="56%" valign="top" bgcolor="#0e0b08">
            <div style="margin-bottom:8px; color:#d8ccb8;">
              Generate a ready-to-play <b>Castalia</b> character save (<code>.d2s</code>) seeded with your unique character name (required so two players never collide in TCP/IP multiplayer), authentic <code>charstats.txt</code> Life/Mana/Stamina pools, unspent Skill &amp; Stat points, completed quest rewards, Personal Stash Gold, and the tier-matched <b>Horadric Cube + Gems/Skulls + Runes</b> starter kit.
            </div>

            <table width="100%" border="0" cellpadding="4" cellspacing="0" style="font-size:12px;">
              <tr>
                <td width="34%"><b class="d2-bright-gold">1. Your Character Name:</b></td>
                <td>
                  <input type="text" id="cg-name" maxlength="15" placeholder="Enter unique name (e.g. Alex)"
                         style="background:#1a130b; border:1px solid #8c734b; color:#f0d890; font-weight:bold; padding:4px 8px; width:210px; font-size:12px;">
                  <span class="d2-dim">(2–15 letters, unique in party)</span>
                </td>
              </tr>
              <tr>
                <td><b class="d2-bright-gold">2. Character Class:</b></td>
                <td>
                  <select id="cg-class" style="background:#1a130b; border:1px solid #8c734b; color:#f0d890; font-weight:bold; padding:4px 8px; width:210px; font-size:12px;">
                    <option value="pal">Paladin (Overhauled — 30 Skills)</option>
                    <option value="bar">Barbarian (Overhauled — 30 Skills)</option>
                    <option value="ass">Assassin (Overhauled — 30 Skills)</option>
                    <option value="sor">Sorceress (Overhauled — 30 Skills)</option>
                    <option value="ama">Amazon</option>
                    <option value="nec">Necromancer</option>
                    <option value="dru">Druid</option>
                  </select>
                </td>
              </tr>
              <tr>
                <td><b class="d2-bright-gold">3. Character Level:</b></td>
                <td>
                  <input type="number" id="cg-level" min="1" max="99" value="30"
                         style="background:#1a130b; border:1px solid #8c734b; color:#f0d890; font-weight:bold; padding:4px 8px; width:80px; font-size:12px;">
                  <span class="d2-dim" id="cg-tier-preview">Tier 3 (Normal): Cube, Tome of ID, Normal Gems/Skulls, Lvl 28-38 Runes + 315,000g</span>
                </td>
              </tr>
              <tr>
                <td><b class="d2-bright-gold">4. Starting Act &amp; Difficulty:</b></td>
                <td>
                  <select id="cg-wp" style="background:#1a130b; border:1px solid #8c734b; color:#f0d890; font-weight:bold; padding:4px 8px; width:260px; font-size:12px;">
                    <optgroup label="Normal Difficulty">
                      <option value="a1n">Normal — Act 1 (Rogue Encampment)</option>
                      <option value="a2n">Normal — Act 2 (Lut Gholein)</option>
                      <option value="a3n">Normal — Act 3 (Kurast Docks)</option>
                      <option value="a4n">Normal — Act 4 (Pandemonium Fortress)</option>
                      <option value="a5n" selected>Normal — Act 5 (Harrogath)</option>
                    </optgroup>
                    <optgroup label="Nightmare Difficulty">
                      <option value="a1nm">Nightmare — Act 1 (Rogue Encampment)</option>
                      <option value="a2nm">Nightmare — Act 2 (Lut Gholein)</option>
                      <option value="a3nm">Nightmare — Act 3 (Kurast Docks)</option>
                      <option value="a4nm">Nightmare — Act 4 (Pandemonium Fortress)</option>
                      <option value="a5nm">Nightmare — Act 5 (Harrogath)</option>
                    </optgroup>
                    <optgroup label="Hell Difficulty">
                      <option value="a1h">Hell — Act 1 (Rogue Encampment)</option>
                      <option value="a2h">Hell — Act 2 (Lut Gholein)</option>
                      <option value="a3h">Hell — Act 3 (Kurast Docks)</option>
                      <option value="a4h">Hell — Act 4 (Pandemonium Fortress)</option>
                      <option value="a5h">Hell — Act 5 (Harrogath)</option>
                      <option value="all">Hell — All 39 Waypoints &amp; Quests Completed</option>
                    </optgroup>
                  </select>
                </td>
              </tr>
            </table>

            <div style="margin-top:10px; display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
              <button type="button" id="cg-download-btn"
                      style="background:linear-gradient(180deg, #4b3419 0%, #261a0c 100%); border:2px ridge #c7b377; color:#f0d890; font-weight:bold; font-size:13px; padding:6px 14px; cursor:pointer;">
                &#11015; Generate &amp; Save .d2s Character File
              </button>
              <button type="button" id="cg-copy-link-btn" class="calc-reset-btn" style="padding:6px 10px;">
                &#128279; Copy Pre-Filled Invite Link
              </button>
              <span id="cg-status-msg" class="d2-gold" style="font-size:11px;"></span>
            </div>
            <div style="margin-top:6px;" class="d2-dim">
              Shareable Pre-Filled URL: <code id="cg-share-url" style="color:#a3957b;">?name=Alex&amp;class=pal&amp;level=30&amp;wp=a5n#char-generator</code>
            </div>
          </td>

          <td width="44%" valign="top" bgcolor="#120e0a">
            <div style="color:#f0d890; font-weight:bold; margin-bottom:6px;">&#128193; WHERE TO SAVE YOUR <code>.d2s</code> FILE (2-SECOND SHORTCUT)</div>
            <p style="margin-top:0; margin-bottom:6px; font-size:11px; color:#d8ccb8;">
              Click <b>Copy Windows Save Path</b> below, then when the <b>Save As</b> window opens (or in File Explorer), press <code>Ctrl+L</code>, paste (<code>Ctrl+V</code>), and hit <code>Enter</code> to jump directly into your Castalia save folder:
            </p>
            <div style="background:#080604; border:1px solid #5c4b32; padding:6px 8px; margin-bottom:8px; display:flex; align-items:center; justify-content:space-between; gap:8px;">
              <code id="cg-win-path" style="color:#00e600; font-size:11px; word-break:break-all;">%USERPROFILE%\\Saved Games\\Diablo II Resurrected\\mods\\castalia</code>
              <button type="button" id="cg-copy-win-btn" class="calc-reset-btn" style="white-space:nowrap;">&#128203; Copy Windows Save Path</button>
            </div>
            <div style="font-size:11px; color:#a8987e; line-height:1.45;">
              <b>Automatic Level-Tier Starter Loadout Included:</b>
              <ul style="margin:4px 0 0 18px; padding:0;">
                <li><b>Lvl 1–9:</b> 4x Belt Minor Healing Potions (bare fresh start)</li>
                <li><b>Lvl 10–14 (Chipped):</b> Cube, Tome of ID, 8 Chipped Gems/Skulls, 6 Runes + <code>60,000g</code></li>
                <li><b>Lvl 15–29 (Flawed):</b> Cube, Tome of ID, 8 Flawed Gems/Skulls, 6 Runes + <code>240,000g</code></li>
                <li><b>Lvl 30–44 (Normal):</b> Cube, Tome of ID, 8 Normal Gems/Skulls, 6 Runes + <code>315k–535kg</code></li>
                <li><b>Lvl 45–59 (Flawless):</b> Cube, Tome of ID, 8 Flawless Gems/Skulls, 6 Runes + <code>535k–825kg</code></li>
                <li><b>Lvl 60+ (Perfect):</b> Cube, Tome of ID, 8 Perfect Gems/Skulls, 6 Runes + <code>1.24M–1.45Mg</code></li>
              </ul>
            </div>
          </td>
        </tr>
      </table>
    </div>
    </div>

    <!-- TAB 3: GEMS, SKULLS & 33 RUNES -->
    <div class="tab-panel" id="tab-items">
    <a name="gems-skulls"></a>
    <div class="section-block">
      <div class="section-title-bar">
        <h2>GEMS, SKULLS &amp; THE 33 SEMANTIC RUNES</h2>
        <div class="section-sub">Strictly 1 property per slot, zero overlap, used for both Socketing and Horadric Cube Crafting</div>
      </div>

      <table width="100%" border="1" cellpadding="5" cellspacing="0" bordercolor="#5c4b32" class="arreat-table" style="margin-bottom:16px;">
        <tr bgcolor="#261e14">
          <th colspan="7" align="left" class="table-banner">7 GEM &amp; SKULL FAMILIES (Level Req: {" / ".join(gem_tier_reqs)} &nbsp;|&nbsp; Crafting Output ilvl: 14 / 29 / 44 / 59 / 100% clvl)</th>
        </tr>
        <tr bgcolor="#1a140e" class="table-subhdr">
          <th align="left">Family</th>
          <th align="left">Slot Group</th>
          <th>Chipped (Req {gem_tier_reqs[0]})<br><span class="d2-dim">Rune Mult: 0.20-0.30x</span></th>
          <th>Flawed (Req {gem_tier_reqs[1]})<br><span class="d2-dim">Rune Mult: 0.35-0.45x</span></th>
          <th>Standard (Req {gem_tier_reqs[2]})<br><span class="d2-dim">Rune Mult: 0.55-0.65x</span></th>
          <th>Flawless (Req {gem_tier_reqs[3]})<br><span class="d2-dim">Rune Mult: 0.75-0.85x</span></th>
          <th>Perfect (Req {gem_tier_reqs[4]})<br><span class="d2-dim">Rune Mult: 0.90-1.00x</span></th>
        </tr>
        {"".join(gem_rows_html)}
      </table>

      <a name="runes-33"></a>
      <table width="100%" border="1" cellpadding="4" cellspacing="0" bordercolor="#5c4b32" class="arreat-table">
        <tr bgcolor="#261e14">
          <th colspan="5" align="left" class="table-banner">THE 33 SEMANTIC RUNES (r01 – r33 &nbsp;|&nbsp; Built Automatically from gems.txt &amp; misc.txt)</th>
        </tr>
        <tr bgcolor="#1a140e" class="table-subhdr">
          <th width="8%">Rune</th>
          <th width="20%" align="left">Semantic Name (Lvl Req)</th>
          <th width="24%" align="left">Weapon / Gloves (0.6x) / Ring (0.5x)</th>
          <th width="24%" align="left">Armor / Helm (0.75x) / Boots-Belt (0.6x) / Amul (0.5x)</th>
          <th width="24%" align="left">Shield / Off-Hand (1.0x)</th>
        </tr>
        {"".join(rune_rows_html)}
      </table>
    </div>
    </div>

    <!-- TAB 4: MONSTER ARCHETYPES & 10-SLOT MERCENARIES -->
    <div class="tab-panel" id="tab-world">
    <a name="monsters"></a>
    <a name="dungeons"></a>
    <a name="mercenaries"></a>
    <div class="section-block">
      <div class="section-title-bar">
        <h2>MONSTER ARCHETYPES, OPTIONAL DUNGEONS &amp; 10-SLOT MERCENARIES</h2>
        <div class="section-sub">Readable enemy roles, +20% difficulty / +30% reward side dungeons, and fully geared companions</div>
      </div>

      <table width="100%" border="1" cellpadding="6" cellspacing="0" bordercolor="#5c4b32" class="arreat-table" style="margin-bottom:14px;">
        <tr bgcolor="#261e14">
          <th colspan="5" align="left" class="table-banner">THE 4 MONSTER COMBAT ARCHETYPES (Strictly 1 Unique Pack Per Zone, 99% Max Resist Cap)</th>
        </tr>
        <tr bgcolor="#1a140e" class="table-subhdr">
          <th align="left">Archetype &amp; Silhouette</th>
          <th>Pack Size</th>
          <th>HP Scaling (N &rarr; H)</th>
          <th>Damage Scaling</th>
          <th align="left">Tactical Behavior</th>
        </tr>
        <tr>
          <td><b class="d2-gold">1. Heavy Brutes &amp; Dread Hulks</b><br><span class="d2-dim">Zombies, Yetis, Blunderbores, Thorned Hulks, Siege Beasts, Blood Lords</span></td>
          <td align="center"><b>1 – 2</b></td>
          <td align="center"><code>3.40x &rarr; 4.08x</code></td>
          <td align="center"><code>1.70x &rarr; 2.00x</code></td>
          <td>Slow, lumbering juggernauts with <code>15%</code> Critical Strike and <code>+4</code> skill levels. Punish face-tanking; reward kiting and Crushing Blow.</td>
        </tr>
        <tr bgcolor="#120e0a">
          <td><b class="d2-gold">2. Swarmers</b><br><span class="d2-dim">Fallen, Flayers, Quill Rats, Scarabs, Spiders, Imps, Stygian Dolls</span></td>
          <td align="center"><b>Full Packs</b></td>
          <td align="center"><code>1.30x &rarr; 1.56x</code></td>
          <td align="center"><code>1.20x &rarr; 1.42x</code></td>
          <td>Fast (`+2` Walk/Run), low-HP packs that overwhelm positioning; countered by AoE control and Flat Physical Damage Reduced.</td>
        </tr>
        <tr>
          <td><b class="d2-gold">3. Arcane Casters</b><br><span class="d2-dim">Shamans, Wraiths, Unravelers, Gloams, Vampires, Succubi, Oblivion Knights</span></td>
          <td align="center"><b>2 – 3</b></td>
          <td align="center"><code>2.15x &rarr; 2.58x</code></td>
          <td align="center"><code>1.50x &rarr; 1.77x</code></td>
          <td>High-priority spellcasters with <code>+6</code> skill levels; demand line-of-sight discipline, elemental absorb/max resist, and gap-closers.</td>
        </tr>
        <tr bgcolor="#120e0a">
          <td><b class="d2-gold">4. Elite Infantry</b><br><span class="d2-dim">Corrupt Rogues, Skeletons, Goatmen, Claw Vipers, Zealots, Doom Knights</span></td>
          <td align="center"><b>2 – 4</b></td>
          <td align="center"><code>2.50x &rarr; 3.00x</code></td>
          <td align="center"><code>1.45x &rarr; 1.71x</code></td>
          <td>Balanced frontline formations with <code>12%</code> Critical Strike and <code>+4</code> skill levels.</td>
        </tr>
      </table>

      <table width="100%" border="1" cellpadding="6" cellspacing="0" bordercolor="#5c4b32" class="arreat-table">
        <tr bgcolor="#261e14">
          <th colspan="2" align="left" class="table-banner">10-SLOT MERCENARY LOADOUTS &amp; SKILL KITS (All Mercs Equip Helm, Armor, Weap, Off-Hand, Gloves, Boots, Belt, Amulet &amp; 2 Rings)</th>
        </tr>
        <tr>
          <td width="25%" bgcolor="#120e0a"><b class="d2-gold">Act 1 Rogue Scouts</b><br><span class="d2-dim">(Bows + Magic/Rare Quivers)</span></td>
          <td><b>Fire Rogue:</b> <i>Weaken / Life Tap / Lower Resist</i> + <i>Fire &amp; Exploding Arrow</i> &nbsp;|&nbsp; <b>Ice Rogue:</b> <i>Dim Vision / Slow Missiles / Decrepify</i> + <i>Cold &amp; Freezing Arrow</i> &nbsp;|&nbsp; <b>Physical Rogue:</b> <i>Inner Sight / Cloak of Shadows / Amplify Damage</i> + <i>Multiple Shot, Strafe &amp; Critical Strike</i>.</td>
        </tr>
        <tr bgcolor="#120e0a">
          <td><b class="d2-gold">Act 2 Desert Guards</b><br><span class="d2-dim">(9-Aura Progression Matrix)</span></td>
          <td><b>Normal:</b> <i>Thorns, Defiance, Blessed Aim</i> &nbsp;|&nbsp; <b>Nightmare:</b> <i>Cleansing, Holy Freeze, Vigor</i> &nbsp;|&nbsp; <b>Hell:</b> <i>Meditation, Salvation, Sanctuary</i>.</td>
        </tr>
        <tr>
          <td bgcolor="#120e0a"><b class="d2-gold">Act 3 Iron Wolves</b><br><span class="d2-dim">(Sword + Shield Casters)</span></td>
          <td>Dedicated <b>Fire</b>, <b>Cold</b>, and <b>Lightning</b> spellcasters scaling with Elemental Masteries and Faster Cast Rate.</td>
        </tr>
        <tr bgcolor="#120e0a">
          <td><b class="d2-gold">Act 5 Barbarians</b><br><span class="d2-dim">(2H Vanguard or 1H Dual-Wield)</span></td>
          <td><b>2H Vanguard:</b> <i>Stun + Battle Orders + Might / Concentration</i> &nbsp;|&nbsp; <b>1H Dual-Wield:</b> <i>Frenzy + Double Swing + Might / Fanaticism + Iron Skin</i>.</td>
        </tr>
      </table>
    </div>
    </div>

    <!-- TABS 5-8: INTERACTIVE CLASS SKILL TREES & COMPENDIUM -->
    {"".join(class_sections_html)}

    <div class="retro-footer">
      &#9876; <b>THE CASTALIA COMPENDIUM</b> &#9876; &nbsp;|&nbsp; Built for <i>Diablo II: Resurrected</i>
    </div>

  </td>
</tr>
</table>

<script type="text/javascript">
var D2_CALC_DATA = {calc_payload_json};
(function() {{
  var DATA = D2_CALC_DATA;
  var SKILLS = DATA.skills;
  var MISSILES = DATA.missiles;

  // Allocated points per raw skill name: {{ "Sacrifice": 0, ... }}
  var alloc = {{}};
  var skillsByCls = {{ pal: [], bar: [], ass: [], sor: [] }};
  for (var k in SKILLS) {{
    if (Object.prototype.hasOwnProperty.call(SKILLS, k)) {{
      alloc[k] = 0;
      var c = SKILLS[k].cls;
      if (skillsByCls[c]) skillsByCls[c].push(SKILLS[k]);
    }}
  }}

  function tieredVal(arr, lvl) {{
    if (!arr || !arr.length) return 0;
    var b = arr[0] || 0;
    var d1 = arr[1] || 0, d2 = arr[2] || 0, d3 = arr[3] || 0, d4 = arr[4] || 0, d5 = arr[5] || 0;
    return b
      + Math.max(0, Math.min(lvl, 8) - 1) * d1
      + Math.max(0, Math.min(lvl, 16) - 8) * d2
      + Math.max(0, Math.min(lvl, 22) - 16) * d3
      + Math.max(0, Math.min(lvl, 28) - 22) * d4
      + Math.max(0, lvl - 28) * d5;
  }}

  function tieredLen(arr, lvl) {{
    if (!arr || !arr.length) return 0;
    var b = arr[0] || 0, d1 = arr[1] || 0, d2 = arr[2] || 0, d3 = arr[3] || 0;
    return b
      + Math.max(0, Math.min(lvl, 8) - 1) * d1
      + Math.max(0, Math.min(lvl, 16) - 8) * d2
      + Math.max(0, lvl - 16) * d3;
  }}

  // Recursive-descent D2R integer expression parser (with Math.trunc on '/')
  function evalArith(str, env) {{
    var pos = 0;
    var n = str.length;
    function skipWS() {{ while (pos < n && str.charCodeAt(pos) <= 32) pos++; }}

    function parseTernary() {{
      var cond = parseCmp();
      skipWS();
      if (pos < n && str.charAt(pos) === '?') {{
        pos++;
        var tVal = parseTernary();
        skipWS();
        if (pos < n && str.charAt(pos) === ':') pos++;
        var fVal = parseTernary();
        return cond ? tVal : fVal;
      }}
      return cond;
    }}

    function parseCmp() {{
      var left = parseAdd();
      while (true) {{
        skipWS();
        if (str.substr(pos, 2) === '>=') {{ pos += 2; left = (left >= parseAdd()) ? 1 : 0; }}
        else if (str.substr(pos, 2) === '<=') {{ pos += 2; left = (left <= parseAdd()) ? 1 : 0; }}
        else if (str.substr(pos, 2) === '==') {{ pos += 2; left = (left === parseAdd()) ? 1 : 0; }}
        else if (str.substr(pos, 2) === '!=') {{ pos += 2; left = (left !== parseAdd()) ? 1 : 0; }}
        else if (pos < n && str.charAt(pos) === '>') {{ pos++; left = (left > parseAdd()) ? 1 : 0; }}
        else if (pos < n && str.charAt(pos) === '<') {{ pos++; left = (left < parseAdd()) ? 1 : 0; }}
        else break;
      }}
      return left;
    }}

    function parseAdd() {{
      var left = parseMul();
      while (true) {{
        skipWS();
        var ch = str.charAt(pos);
        if (ch === '+') {{ pos++; left = left + parseMul(); }}
        else if (ch === '-') {{ pos++; left = left - parseMul(); }}
        else break;
      }}
      return left;
    }}

    function parseMul() {{
      var left = parseUnary();
      while (true) {{
        skipWS();
        var ch = str.charAt(pos);
        if (ch === '*') {{ pos++; left = left * parseUnary(); }}
        else if (ch === '/') {{
          pos++;
          var r = parseUnary();
          left = r !== 0 ? Math.trunc(left / r) : 0;
        }}
        else break;
      }}
      return left;
    }}

    function parseUnary() {{
      skipWS();
      if (pos < n && str.charAt(pos) === '+') {{ pos++; return parseUnary(); }}
      if (pos < n && str.charAt(pos) === '-') {{ pos++; return -parseUnary(); }}
      return parsePrimary();
    }}

    function parsePrimary() {{
      skipWS();
      if (pos < n && str.charAt(pos) === '(') {{
        pos++;
        var v = parseTernary();
        skipWS();
        if (pos < n && str.charAt(pos) === ')') pos++;
        return v;
      }}
      var start = pos;
      if (pos < n && str.charCodeAt(pos) >= 48 && str.charCodeAt(pos) <= 57) {{
        while (pos < n && str.charCodeAt(pos) >= 48 && str.charCodeAt(pos) <= 57) pos++;
        return parseInt(str.slice(start, pos), 10) || 0;
      }}
      while (pos < n && /[A-Za-z0-9_]/.test(str.charAt(pos))) pos++;
      var ident = str.slice(start, pos);
      skipWS();
      if (pos < n && str.charAt(pos) === '(') {{
        pos++;
        var args = [];
        skipWS();
        if (pos < n && str.charAt(pos) !== ')') {{
          args.push(parseTernary());
          skipWS();
          while (pos < n && str.charAt(pos) === ',') {{
            pos++;
            args.push(parseTernary());
            skipWS();
          }}
        }}
        if (pos < n && str.charAt(pos) === ')') pos++;
        if (ident === 'min') return Math.min(args[0] || 0, args[1] || 0);
        if (ident === 'max') return Math.max(args[0] || 0, args[1] || 0);
        return 0;
      }}
      return Object.prototype.hasOwnProperty.call(env, ident) ? env[ident] : 0;
    }}

    return parseTernary() | 0;
  }}

  function evalSkillExpr(sk, expr, lvl, depth) {{
    if (!expr || (depth || 0) > 8) return 0;
    var d = depth || 0;
    var e = String(expr).trim();
    if (!e) return 0;

    e = e.replace(/skill\\('([^']+)'\\.[A-Za-z0-9_]+\\)/g, function(_, nm) {{
      if (nm.toLowerCase() === sk.rawName.toLowerCase()) return String(lvl);
      for (var rk in alloc) {{
        if (rk.toLowerCase() === nm.toLowerCase()) return String(alloc[rk] || 0);
      }}
      return "0";
    }});

    e = e.replace(/miss\\('([^']+)'\\.[A-Za-z0-9_]+\\)/g, function(_, mn) {{
      var mr = MISSILES[mn.toLowerCase()];
      if (!mr) return "0";
      var baseR = evalSkillExpr(sk, mr.Range || "0", lvl, d + 1);
      return String(baseR + (lvl - 1) * (mr.LevRange || 0));
    }});

    e = e.replace(/stat\\('([^']+)'\\.[A-Za-z0-9_]+\\)/g, function(_, st) {{
      var s = st.toLowerCase();
      return (s === "stamina" || s === "maxstamina") ? "256" : "0";
    }});

    var P = sk.Params;
    function ln(a, b) {{ return (P[a - 1] || 0) + (lvl - 1) * (P[b - 1] || 0); }}
    function dm(a, b) {{
      var pa = P[a - 1] || 0, pb = P[b - 1] || 0;
      return Math.trunc((110 * lvl) * (pb - pa) / (100 * (lvl + 6))) + pa;
    }}

    var hs = sk.HitShift || 8;
    var rawEmin = tieredVal(sk.EMin, lvl);
    var rawEmax = tieredVal(sk.EMax, lvl);
    var rawPmin = tieredVal(sk.MinDam, lvl);
    var rawPmax = tieredVal(sk.MaxDam, lvl);
    var esym = (sk.EDmgSymPerCalc && d < 4) ? evalSkillExpr(sk, sk.EDmgSymPerCalc, lvl, d + 1) : 0;
    var psym = (sk.DmgSymPerCalc && d < 4) ? evalSkillExpr(sk, sk.DmgSymPerCalc, lvl, d + 1) : 0;
    var enms = Math.trunc((rawEmin << hs) * (100 + esym) / 100);
    var exms = Math.trunc((rawEmax << hs) * (100 + esym) / 100);
    var enma = enms >> 8;
    var exma = exms >> 8;
    var pnma = Math.trunc(((rawPmin << hs) >> 8) * (100 + psym) / 100);
    var pxma = Math.trunc(((rawPmax << hs) >> 8) * (100 + psym) / 100);

    var elen = tieredLen(sk.ELen, lvl);
    var lsym = (sk.ELenSymPerCalc && d < 4) ? evalSkillExpr(sk, sk.ELenSymPerCalc, lvl, d + 1) : 0;
    var edln = Math.trunc(elen * (100 + lsym) / 100);

    var mShift = sk.manashift || 8;
    var usmc = Math.max((sk.minmana || 0) << 8, ((sk.mana || 0) + (lvl - 1) * (sk.lvlmana || 0)) << mShift);
    var toht = (sk.ToHitCalc && d < 4)
      ? evalSkillExpr(sk, sk.ToHitCalc, lvl, d + 1)
      : ((sk.ToHit || 0) + (lvl - 1) * (sk.LevToHit || 0));

    var env = {{
      lvl: lvl, blvl: lvl,
      ln12: ln(1, 2), ln34: ln(3, 4), ln56: ln(5, 6), ln78: ln(7, 8),
      dm12: dm(1, 2), dm34: dm(3, 4), dm56: dm(5, 6), dm78: dm(7, 8), dm91: dm(9, 10),
      usmc: usmc, toht: toht,
      enma: enma, exma: exma, enms: enms, exms: exms,
      edns: rawEmin << hs, edxs: rawEmax << hs,
      pnma: pnma, pxma: pxma,
      elen: elen, edln: edln,
      len: (e.indexOf("len") !== -1 && d < 4) ? evalSkillExpr(sk, sk.auralencalc, lvl, d + 1) : 0,
      madm: ln(3, 4), math: ln(1, 2), mapi: dm(7, 8), manc: dm(9, 10)
    }};
    for (var pi = 1; pi <= 12; pi++) env["par" + pi] = P[pi - 1] || 0;

    for (var mi = 1; mi <= 3; mi++) {{
      var mname = (sk.descmissiles && sk.descmissiles[mi - 1]) || "";
      var mr = MISSILES[mname] || {{}};
      var mhs = mr.HitShift || 8;
      var memin = tieredVal(mr.EMin, lvl);
      var memax = tieredVal(mr.EMax, lvl);
      var mpmin = tieredVal(mr.MinDam, lvl);
      var mpmax = tieredVal(mr.MaxDam, lvl);
      env["m" + mi + "en"] = Math.trunc(((memin << mhs) >> 8) * (100 + esym) / 100);
      env["m" + mi + "ex"] = Math.trunc(((memax << mhs) >> 8) * (100 + esym) / 100);
      env["m" + mi + "na"] = Math.trunc(((memin || mpmin) << mhs) * (100 + (esym || psym)) / 100);
      env["m" + mi + "xa"] = Math.trunc(((memax || mpmax) << mhs) * (100 + (esym || psym)) / 100);
    }}

    for (var ci = 1; ci <= 6; ci++) {{
      var ck = "clc" + ci;
      if (e.indexOf(ck) !== -1 && d < 5) {{
        env[ck] = evalSkillExpr(sk, sk.Calcs[ci - 1] || "", lvl, d + 1);
      }}
    }}

    return evalArith(e, env);
  }}

  function fmtNum(v) {{
    if (Math.abs(v - Math.round(v)) < 0.05) return String(Math.round(v));
    return v.toFixed(1);
  }}

  function subSignedSingle(tmpl, valStr) {{
    var m = tmpl.match(/([+-]?)(%\\+?d)(%?)/);
    if (!m) return tmpl + " " + valStr;
    var lead = m[1], ph = m[2], pct = m[3];
    var sign = lead || (ph === "%+d" ? "+" : "");
    var s = String(valStr);
    if (sign === "+" && s.charAt(0) !== "+" && s.charAt(0) !== "-") s = "+" + s + pct;
    else if (sign === "-" && s.charAt(0) !== "-") s = "-" + s + pct;
    else s = s + pct;
    return tmpl.slice(0, m.index) + s + tmpl.slice(m.index + m[0].length);
  }}

  function renderSingleLevelLine(sk, lnObj, lvl) {{
    var fn = lnObj.fn, ta = lnObj.ta || "", tb = lnObj.tb || "", ca = lnObj.ca || "", cb = lnObj.cb || "";
    if (fn === "18") return ta;
    if (fn === "40") return "";
    if (fn === "76") {{
      var v = evalSkillExpr(sk, ca, lvl);
      var body = ta.replace(/%%/g, "%").replace("%s", tb);
      return subSignedSingle(body, String(v));
    }}
    if (fn === "77") {{
      var va = evalSkillExpr(sk, ca, lvl);
      var vb = evalSkillExpr(sk, cb, lvl);
      var b77 = ta.replace(/%%/g, "%").replace("%s", tb);
      b77 = b77.replace(/%\\+?d/, (b77.indexOf("%+d") !== -1 && va >= 0 ? "+" : "") + va);
      b77 = b77.replace(/%\\+?d/, String(vb));
      return b77;
    }}
    if (fn === "13") {{
      var v13 = 100 + evalSkillExpr(sk, ca, lvl);
      return subSignedSingle(ta.replace(/%%/g, "%"), String(v13));
    }}
    if (fn === "36") {{
      var n = evalSkillExpr(sk, ca, lvl);
      var d = evalSkillExpr(sk, cb, lvl) || 1;
      var f = fmtNum(n / d);
      var tmpl36 = (tb || ta).replace(/%%/g, "%");
      return subSignedSingle(tmpl36, f);
    }}
    if (fn === "74") {{
      var v74 = evalSkillExpr(sk, ca, lvl);
      if (v74 === 0) return "";
      return subSignedSingle(ta.replace(/%%/g, "%"), String(v74));
    }}
    if (fn === "75") {{
      var a = evalSkillExpr(sk, ca, lvl);
      var b = evalSkillExpr(sk, cb, lvl);
      var tmpl75 = ta.replace(/%%/g, "%");
      var mr = tmpl75.match(/([+-]?)(%\\+?d)-(%\\+?d)(%?)/);
      if (mr) {{
        var lead = mr[1], ph1 = mr[2], ph2 = mr[3], pct = mr[4];
        var sign = lead || ((ph1 === "%+d" || ph2 === "%+d") ? "+" : "");
        var r = (a !== b) ? (sign + a + "-" + b + pct) : (sign + a + pct);
        return tmpl75.slice(0, mr.index) + r + tmpl75.slice(mr.index + mr[0].length);
      }}
      var out = subSignedSingle(tmpl75, String(a));
      out = subSignedSingle(out, String(b));
      return out;
    }}
    return "";
  }}

  function getSkillLevelLines(sk, lvl) {{
    var lines = [];
    for (var i = 0; i < sk.descLines.length; i++) {{
      var s = renderSingleLevelLine(sk, sk.descLines[i], lvl);
      if (s && lines.indexOf(s) === -1) lines.push(s);
    }}
    if (!lines.length) {{
      if (sk.EMin && (sk.EMin[0] || sk.EMax[0])) {{
        var etMap = {{ fire: "Fire", ltng: "Lightning", cold: "Cold", mag: "Magic", pois: "Poison" }};
        var elbl = etMap[sk.EType] || "Elemental";
        var emin = evalSkillExpr(sk, "enma", lvl);
        var emax = evalSkillExpr(sk, "exma", lvl);
        lines.push(elbl + " Damage: " + emin + "-" + emax);
      }}
      if (sk.mana) {{
        var u = fmtNum(evalSkillExpr(sk, "usmc", lvl) / 256);
        lines.push("Mana Cost: " + u);
      }}
    }}
    return lines;
  }}

  function getPrimaryShortStat(sk, lvl) {{
    var lines = getSkillLevelLines(sk, lvl);
    if (!lines.length) return "";
    // Prefer a damage / main effect line over Mana Cost / Duration / Radius / Delay
    var chosen = lines[0];
    for (var i = 0; i < lines.length; i++) {{
      var ln = lines[i];
      if (!/^(Mana Cost|Duration|Blaze Duration|Radius|Range|Casting Delay|Minimum Mana)/i.test(ln)) {{
        chosen = ln;
        break;
      }}
    }}
    return chosen
      .replace(/Physical Damage Received Reduced by /i, "DR ")
      .replace(/Physical Damage Reduced by /i, "DR ")
      .replace(/to Monster Defense Per Hit/i, "Mon Def")
      .replace(/Lightning Damage:/i, "Ltng:")
      .replace(/Magic Damage:/i, "Magic:")
      .replace(/Cold Damage:/i, "Cold:")
      .replace(/Fire Damage:/i, "Fire:")
      .replace(/Poison Damage:/i, "Pois:")
      .replace(/Attack Rating:/i, "AR:")
      .replace(/Enhanced Damage/i, "ED")
      .replace(/Damage:/i, "Dmg:")
      .replace(/Defense:/i, "Def:");
  }}

  function getClassTotals(cls) {{
    var list = skillsByCls[cls] || [];
    var total = 0;
    var byPage = {{ 1: 0, 2: 0, 3: 0 }};
    for (var i = 0; i < list.length; i++) {{
      var pts = alloc[list[i].rawName] || 0;
      total += pts;
      byPage[list[i].page] = (byPage[list[i].page] || 0) + pts;
    }}
    var clvl = 1 + Math.floor(total / 2);
    return {{ total: total, clvl: clvl, byPage: byPage }};
  }}

  function checkCanAdd(sk) {{
    var pts = alloc[sk.rawName] || 0;
    if (pts >= sk.maxlvl) {{
      return {{ ok: false, reason: sk.name + " is already at Maximum Level (" + sk.maxlvl + ")." }};
    }}
    var tots = getClassTotals(sk.cls);
    var missingReqs = [];
    for (var i = 0; i < sk.reqskills.length; i++) {{
      var rq = sk.reqskills[i];
      if ((alloc[rq] || 0) < 1) {{
        missingReqs.push(SKILLS[rq] ? SKILLS[rq].name : rq);
      }}
    }}
    if (missingReqs.length > 0) {{
      return {{ ok: false, reason: "Requires Prerequisite: " + missingReqs.join(", ") }};
    }}
    if (tots.clvl < sk.reqlevel) {{
      var neededPts = (sk.reqlevel - 1) * 2 - tots.total;
      return {{
        ok: false,
        reason: "Requires Character Level " + sk.reqlevel + " (spend " + neededPts + " more skill point" + (neededPts === 1 ? "" : "s") + " first)."
      }};
    }}
    return {{ ok: true, reason: "" }};
  }}

  function checkCanRemove(sk) {{
    var pts = alloc[sk.rawName] || 0;
    if (pts <= 0) return {{ ok: false, reason: "" }};
    var list = skillsByCls[sk.cls] || [];
    if (pts === 1) {{
      for (var i = 0; i < list.length; i++) {{
        var other = list[i];
        if ((alloc[other.rawName] || 0) > 0 && other.reqskills.indexOf(sk.rawName) !== -1) {{
          return {{ ok: false, reason: "Cannot remove last point: required by " + other.name + "." }};
        }}
      }}
    }}
    // Check that reducing total points by 1 does not drop clvl below any remaining allocated skill's reqlevel
    var tots = getClassTotals(sk.cls);
    var newTotal = tots.total - 1;
    var newClvl = 1 + Math.floor(newTotal / 2);
    for (var j = 0; j < list.length; j++) {{
      var o = list[j];
      var remPts = (o.rawName === sk.rawName) ? (pts - 1) : (alloc[o.rawName] || 0);
      if (remPts > 0 && newClvl < o.reqlevel) {{
        return {{
          ok: false,
          reason: "Cannot lower Character Level below Level " + o.reqlevel + " while " + o.name + " is allocated."
        }};
      }}
    }}
    return {{ ok: true, reason: "" }};
  }}

  function setClassMessage(cls, text, isWarn) {{
    var el = document.getElementById("calc-msg-" + cls);
    if (!el) return;
    el.textContent = text;
    el.className = isWarn ? "calc-msg warn" : "calc-msg";
  }}

  function updateClassUI(cls) {{
    var tots = getClassTotals(cls);
    var clvlEl = document.getElementById("calc-clvl-" + cls);
    var ptsEl = document.getElementById("calc-pts-" + cls);
    if (clvlEl) clvlEl.textContent = String(tots.clvl);
    if (ptsEl) ptsEl.textContent = String(tots.total);

    for (var pg = 1; pg <= 3; pg++) {{
      var tpEl = document.getElementById("tree-pts-" + cls + "-" + pg);
      if (tpEl) tpEl.textContent = "(" + (tots.byPage[pg] || 0) + " pts)";
    }}

    var gatesWrap = document.getElementById("calc-gates-" + cls);
    if (gatesWrap) {{
      var pills = gatesWrap.querySelectorAll(".gate-pill");
      for (var g = 0; g < pills.length; g++) {{
        var gateLvl = parseInt(pills[g].getAttribute("data-gate") || "1", 10);
        if (tots.clvl >= gateLvl) pills[g].classList.add("unlocked");
        else pills[g].classList.remove("unlocked");
      }}
    }}

    var list = skillsByCls[cls] || [];
    for (var i = 0; i < list.length; i++) {{
      var sk = list[i];
      var pts = alloc[sk.rawName] || 0;
      var slotEl = document.getElementById("slot-" + sk.anchor);
      var badgeEl = document.getElementById("badge-" + sk.anchor);
      var liveEl = document.getElementById("livestat-" + sk.anchor);
      var tblPill = document.getElementById("tbl-pill-" + sk.anchor);
      var tblLive = document.getElementById("tbl-live-" + sk.anchor);

      if (badgeEl) badgeEl.textContent = String(pts);

      var canAdd = checkCanAdd(sk).ok;
      if (slotEl) {{
        slotEl.classList.remove("state-locked", "state-avail", "state-alloc");
        if (pts > 0) slotEl.classList.add("state-alloc");
        else if (canAdd) slotEl.classList.add("state-avail");
        else slotEl.classList.add("state-locked");
      }}

      if (pts > 0) {{
        var shortStat = getPrimaryShortStat(sk, pts);
        if (liveEl) liveEl.textContent = shortStat;
        if (tblPill) tblPill.textContent = "Allocated: Lvl " + pts + "/" + sk.maxlvl;
        if (tblLive) {{
          var curLines = getSkillLevelLines(sk, pts);
          tblLive.innerHTML = '<b class="d2-bright-gold">Current Allocated Level ' + pts + ':</b> <span class="d2-blue">' + curLines.join(" &nbsp;&bull;&nbsp; ") + '</span>';
        }}
      }} else {{
        if (liveEl) liveEl.textContent = "";
        if (tblPill) tblPill.textContent = "";
        if (tblLive) tblLive.innerHTML = "";
      }}
    }}
  }}

  var activeSlot = null;

  function renderTooltipForSlot(slotEl) {{
    if (!slotEl) return;
    var rawName = slotEl.getAttribute("data-skill") || "";
    var sk = SKILLS[rawName];
    if (!sk) return;

    var pts = alloc[rawName] || 0;
    var tots = getClassTotals(sk.cls);

    ttName.innerHTML = sk.name + (pts > 0
      ? ' <span class="d2-bright-gold">(Level ' + pts + '/' + sk.maxlvl + ')</span>'
      : ' <span class="d2-dim">(Unallocated)</span>');

    var lvlOk = tots.clvl >= sk.reqlevel;
    var lvlHtml = '<span class="' + (lvlOk ? 'd2-green' : 'd2-red') + '">Required Level: ' + sk.reqlevel + '</span>';
    var prereqParts = [];
    for (var i = 0; i < sk.reqskills.length; i++) {{
      var rq = sk.reqskills[i];
      var rqName = SKILLS[rq] ? SKILLS[rq].name : rq;
      var rqOk = (alloc[rq] || 0) >= 1;
      prereqParts.push('<span class="' + (rqOk ? 'd2-green' : 'd2-red') + '">' + rqName + '</span>');
    }}
    var prereqHtml = prereqParts.length ? (" | Prereqs: " + prereqParts.join(", ")) : "";
    ttMeta.innerHTML = lvlHtml + prereqHtml;

    var htmlBlocks = [];
    if (sk.lore) {{
      htmlBlocks.push('<div style="color:#d8ccb8; margin-bottom:5px;">' + sk.lore + '</div>');
    }}

    if (pts === 0) {{
      var firstLines = getSkillLevelLines(sk, 1);
      if (firstLines.length) {{
        htmlBlocks.push('<div style="color:#f0d890; font-weight:bold; margin-top:4px;">First Level (Level 1):</div>');
        htmlBlocks.push('<div style="color:#78a8ff;">' + firstLines.join("<br>") + '</div>');
      }}
    }} else {{
      var curLines = getSkillLevelLines(sk, pts);
      if (curLines.length) {{
        htmlBlocks.push('<div style="color:#f0d890; font-weight:bold; margin-top:4px;">Current Skill Level (' + pts + '):</div>');
        htmlBlocks.push('<div style="color:#78a8ff;">' + curLines.join("<br>") + '</div>');
      }}
      if (pts < sk.maxlvl) {{
        var nextLines = getSkillLevelLines(sk, pts + 1);
        if (nextLines.length) {{
          htmlBlocks.push('<div style="color:#a8987e; font-weight:bold; margin-top:5px;">Next Level (' + (pts + 1) + '):</div>');
          htmlBlocks.push('<div style="color:#8ca8d8;">' + nextLines.join("<br>") + '</div>');
        }}
      }}
    }}

    var synOut = [];
    for (var s = 0; s < sk.synLines.length; s++) {{
      var sl = renderSingleLevelLine(sk, sk.synLines[s], Math.max(1, pts));
      if (sl) synOut.push(sl);
    }}
    if (synOut.length) {{
      htmlBlocks.push('<div style="color:#00e600; margin-top:6px; font-size:10px;"><b>Synergies:</b><br>' + synOut.join("<br>") + '</div>');
    }}

    var check = checkCanAdd(sk);
    if (!check.ok && pts < sk.maxlvl) {{
      htmlBlocks.push('<div style="color:#ff6b6b; margin-top:5px; font-size:10px;">' + check.reason + '</div>');
    }} else if (pts < sk.maxlvl) {{
      htmlBlocks.push('<div style="color:#8c8270; margin-top:5px; font-size:10px;">Left-Click: +1 pt (Shift: +5) &nbsp;|&nbsp; Right-Click: -1 pt</div>');
    }}

    ttDesc.innerHTML = htmlBlocks.join("");
  }}

  var tt = document.getElementById('d2-tooltip');
  var ttName = document.getElementById('tt-name');
  var ttMeta = document.getElementById('tt-meta');
  var ttDesc = document.getElementById('tt-desc');
  var slots = document.querySelectorAll('.tree-icon-slot');

  for (var i = 0; i < slots.length; i++) {{
    slots[i].addEventListener('mouseenter', function(e) {{
      activeSlot = this;
      renderTooltipForSlot(this);
      tt.style.display = 'block';
    }});
    slots[i].addEventListener('mousemove', function(e) {{
      var x = e.clientX + 16;
      var y = e.clientY + 16;
      if (x + 380 > window.innerWidth) x = e.clientX - 386;
      if (y + tt.offsetHeight + 20 > window.innerHeight) y = Math.max(8, e.clientY - tt.offsetHeight - 12);
      tt.style.left = x + 'px';
      tt.style.top = y + 'px';
    }});
    slots[i].addEventListener('mouseleave', function() {{
      activeSlot = null;
      tt.style.display = 'none';
    }});
    slots[i].addEventListener('click', function(e) {{
      e.preventDefault();
      var rawName = this.getAttribute('data-skill') || '';
      var sk = SKILLS[rawName];
      if (!sk) return;
      var count = e.shiftKey ? 5 : 1;
      var added = 0;
      var lastCheck = {{ ok: true, reason: "" }};
      for (var c = 0; c < count; c++) {{
        lastCheck = checkCanAdd(sk);
        if (!lastCheck.ok) break;
        alloc[rawName] = (alloc[rawName] || 0) + 1;
        added++;
      }}
      if (added > 0) {{
        var tots = getClassTotals(sk.cls);
        setClassMessage(sk.cls, sk.name + " -> Level " + alloc[rawName] + " (Required Character Level: " + tots.clvl + ")", false);
        updateClassUI(sk.cls);
        renderTooltipForSlot(this);
      }} else if (lastCheck.reason) {{
        setClassMessage(sk.cls, lastCheck.reason, true);
        renderTooltipForSlot(this);
      }}
    }});
    slots[i].addEventListener('contextmenu', function(e) {{
      e.preventDefault();
      var rawName = this.getAttribute('data-skill') || '';
      var sk = SKILLS[rawName];
      if (!sk) return;
      var count = e.shiftKey ? 5 : 1;
      var removed = 0;
      var lastCheck = {{ ok: true, reason: "" }};
      for (var c = 0; c < count; c++) {{
        lastCheck = checkCanRemove(sk);
        if (!lastCheck.ok) break;
        alloc[rawName] = (alloc[rawName] || 0) - 1;
        removed++;
      }}
      if (removed > 0) {{
        var tots = getClassTotals(sk.cls);
        setClassMessage(sk.cls, "Removed point from " + sk.name + " (Required Character Level: " + tots.clvl + ")", false);
        updateClassUI(sk.cls);
        renderTooltipForSlot(this);
      }} else if (lastCheck.reason) {{
        setClassMessage(sk.cls, lastCheck.reason, true);
        renderTooltipForSlot(this);
      }}
    }});
  }}

  var resetBtns = document.querySelectorAll('.calc-reset-btn');
  for (var r = 0; r < resetBtns.length; r++) {{
    resetBtns[r].addEventListener('click', function() {{
      var cls = this.getAttribute('data-reset-cls') || '';
      var list = skillsByCls[cls] || [];
      for (var k = 0; k < list.length; k++) {{
        alloc[list[k].rawName] = 0;
      }}
      updateClassUI(cls);
      setClassMessage(cls, "All skills reset — Required Character Level reverted to 1.", false);
    }});
  }}

  // Initialize all 4 classes
  updateClassUI("pal");
  updateClassUI("bar");
  updateClassUI("ass");
  updateClassUI("sor");

  // =========================================================================
  // CO-OP CAMPAIGN & CHARACTER SAVE (.D2S) GENERATOR (100% STATIC GITHUB PAGES)
  // =========================================================================
  var CHAR_GEN_DATA = {char_gen_payload_json};

  var cgNameEl = document.getElementById("cg-name");
  var cgClassEl = document.getElementById("cg-class");
  var cgLevelEl = document.getElementById("cg-level");
  var cgWpEl = document.getElementById("cg-wp");
  var cgTierPrev = document.getElementById("cg-tier-preview");
  var cgShareUrlEl = document.getElementById("cg-share-url");
  var cgStatusEl = document.getElementById("cg-status-msg");
  var cgDownloadBtn = document.getElementById("cg-download-btn");
  var cgCopyLinkBtn = document.getElementById("cg-copy-link-btn");
  var cgCopyWinBtn = document.getElementById("cg-copy-win-btn");

  function defaultGoldForLevel(lvl) {{
    if (lvl < 10) return 0;
    if (lvl < 20) return 60000;
    if (lvl < 30) return 240000;
    if (lvl < 40) return 315000;
    if (lvl < 50) return 535000;
    if (lvl < 60) return 825000;
    if (lvl < 70) return 1240000;
    return 1450000;
  }}

  function tierKeyForLevel(lvl) {{
    if (lvl < 10) return "default";
    if (lvl < 15) return "tier1_chipped";
    if (lvl < 30) return "tier2_flawed";
    if (lvl < 45) return "tier3_normal";
    if (lvl < 60) return "tier4_flawless";
    return "tier5_perfect";
  }}

  function tierLabelForLevel(lvl) {{
    var g = defaultGoldForLevel(lvl).toLocaleString();
    if (lvl < 10) return "Bare Lvl 1-9: 4x Belt Minor Healing Potions (0g)";
    if (lvl < 15) return "Tier 1 (Chipped): Cube, Tome of ID, Chipped Gems/Skulls, Lvl 4-12 Runes + " + g + "g";
    if (lvl < 30) return "Tier 2 (Flawed): Cube, Tome of ID, Flawed Gems/Skulls, Lvl 12-26 Runes + " + g + "g";
    if (lvl < 45) return "Tier 3 (Normal): Cube, Tome of ID, Normal Gems/Skulls, Lvl 28-38 Runes + " + g + "g";
    if (lvl < 60) return "Tier 4 (Flawless): Cube, Tome of ID, Flawless Gems/Skulls, Lvl 38-52 Runes + " + g + "g";
    return "Tier 5 (Perfect): Cube, Tome of ID, Perfect Gems/Skulls, Lvl 48-68 Runes + " + g + "g";
  }}

  function sanitizeCharName(raw) {{
    return (raw || "").replace(/[^A-Za-z_-]/g, "").slice(0, 15);
  }}

  function buildShareableInviteUrl(fullAbsolute) {{
    var nm = sanitizeCharName(cgNameEl ? cgNameEl.value : "") || "Alex";
    var cls = cgClassEl ? cgClassEl.value : "pal";
    var lvl = Math.max(1, Math.min(99, parseInt(cgLevelEl ? cgLevelEl.value : "30", 10) || 30));
    var wp = cgWpEl ? cgWpEl.value : "a5n";
    var qs = "?name=" + encodeURIComponent(nm) + "&class=" + encodeURIComponent(cls) + "&level=" + lvl + "&wp=" + encodeURIComponent(wp) + "#char-generator";
    if (fullAbsolute && window.location) {{
      var base = window.location.origin + window.location.pathname;
      return base + qs;
    }}
    return qs;
  }}

  function updateCharGenUI() {{
    var lvl = Math.max(1, Math.min(99, parseInt(cgLevelEl ? cgLevelEl.value : "30", 10) || 30));
    if (cgTierPrev) cgTierPrev.textContent = tierLabelForLevel(lvl);
    if (cgShareUrlEl) cgShareUrlEl.textContent = buildShareableInviteUrl(false);
  }}

  // Pre-fill form fields from URL query parameters (e.g. ?name=Alex&class=bar&level=55&wp=a3nm#char-generator)
  (function applyUrlParams() {{
    if (!window.location.search) return;
    var sp = new URLSearchParams(window.location.search);
    var hasParam = false;
    if (sp.get("name") && cgNameEl) {{ cgNameEl.value = sanitizeCharName(sp.get("name")); hasParam = true; }}
    if (sp.get("class") && cgClassEl) {{ cgClassEl.value = sp.get("class").toLowerCase(); hasParam = true; }}
    if (sp.get("level") && cgLevelEl) {{ cgLevelEl.value = sp.get("level"); hasParam = true; }}
    if (sp.get("wp") && cgWpEl) {{ cgWpEl.value = sp.get("wp").toLowerCase(); hasParam = true; }}
    if (hasParam && cgStatusEl) {{
      cgStatusEl.className = "d2-bright-gold";
      cgStatusEl.textContent = "Pre-filled from invite link! Click 'Generate & Save .d2s Character File' to download.";
    }}
  }})();

  // Client-side D2R v105 .d2s binary generator (static fallback when /api/char.d2s is offline)
  var ACT_COMPLETED_QUEST_WORDS = {{
    1: [[0,0x0001],[1,0x9001],[2,0x901D],[3,0x104D],[4,0x9019],[5,0x1015],[6,0x101D],[7,0x0001],[8,0x0001]],
    2: [[8,0x0001],[9,0x1011],[10,0x1C79],[11,0x9005],[12,0x1181],[13,0x1005],[14,0x1C25],[15,0x0001],[16,0x0001]],
    3: [[16,0x0001],[17,0x1001],[18,0x10FD],[19,0x13F9],[20,0x1001],[21,0x100D],[22,0x1381],[23,0x0001],[24,0x0001]],
    4: [[24,0x0001],[25,0x1001],[26,0x1201],[27,0x1001],[28,0x0001],[32,0x0001]],
    5: [[32,0x0001],[35,0x9021],[36,0x1001],[37,0x178D],[38,0x801E],[39,0x1029],[40,0x148D]]
  }};
  var ACT_CUMULATIVE_WPS = {{ 0: 0, 1: 9, 2: 18, 3: 27, 4: 30, 5: 39 }};
  var ACT_TOWN_WP_BIT = {{ 1: 0, 2: 9, 3: 18, 4: 27, 5: 30 }};
  var STAT_BITS = {{ 0:10, 1:10, 2:10, 3:10, 4:10, 5:8, 6:21, 7:21, 8:21, 9:21, 10:21, 11:21, 12:7, 13:32, 14:25, 15:25 }};

  function b64ToUint8Array(b64) {{
    var bin = window.atob(b64);
    var out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }}

  function findMarker(buf, str, start) {{
    var s = start || 0;
    for (var i = s; i <= buf.length - str.length; i++) {{
      var ok = true;
      for (var j = 0; j < str.length; j++) {{
        if (buf[i + j] !== str.charCodeAt(j)) {{ ok = false; break; }}
      }}
      if (ok) return i;
    }}
    return -1;
  }}

  function parseWpCode(wpStr) {{
    var s = (wpStr || "a1n").toLowerCase().replace(/[:-_]/g, "");
    if (s === "all") return {{ diff: 2, act: 5, full: true }};
    if (s === "start") return {{ diff: 0, act: 1, full: false }};
    var act = parseInt(s.charAt(1), 10) || 1;
    var dp = s.slice(2);
    var full = false;
    if (dp.slice(-4) === "done") {{ full = true; dp = dp.slice(0, -4) || "n"; }}
    var diff = (dp === "h" || dp === "hell") ? 2 : ((dp === "nm" || dp === "nightmare") ? 1 : 0);
    return {{ diff: diff, act: act, full: full }};
  }}

  function encodeGfSection(statsObj) {{
    var bits = "";
    function revBits(val, width) {{
      var b = "";
      var v = val >>> 0;
      for (var i = 0; i < width; i++) {{
        b += (v & 1) ? "1" : "0";
        v = v >>> 1;
      }}
      return b;
    }}
    for (var sid = 0; sid <= 15; sid++) {{
      if (statsObj[sid] !== undefined && statsObj[sid] !== null) {{
        bits += revBits(sid, 9);
        bits += revBits(statsObj[sid], STAT_BITS[sid]);
      }}
    }}
    bits += "111111111";
    while (bits.length % 8 !== 0) bits += "0";
    var out = new Uint8Array(bits.length / 8);
    for (var i = 0; i < out.length; i++) {{
      var byteVal = 0;
      for (var b = 0; b < 8; b++) {{
        if (bits.charAt(i * 8 + b) === "1") byteVal |= (1 << b);
      }}
      out[i] = byteVal;
    }}
    return out;
  }}

  function generateD2sClientSide(cleanName, clsCode, level, wpCode) {{
    var tKey = tierKeyForLevel(level);
    var b64 = CHAR_GEN_DATA.templates[tKey] || CHAR_GEN_DATA.templates["default"];
    var raw = b64ToUint8Array(b64);
    var dv = new DataView(raw.buffer, raw.byteOffset, raw.byteLength);
    var cs = CHAR_GEN_DATA.classes[clsCode] || CHAR_GEN_DATA.classes["pal"];

    // 1. Set 16-byte Character Name (0x12B) & Class ID (24) & Level (27, 43)
    for (var i = 0; i < 16; i++) raw[0x12B + i] = (i < cleanName.length) ? cleanName.charCodeAt(i) : 0;
    raw[24] = cs.id;
    raw[27] = level;
    if (raw[43] !== 0) raw[43] = level;

    // 2. Progression byte (21) & Active difficulty/town bytes (152..154)
    var wp = parseWpCode(wpCode);
    var progVal = Math.min(15, wp.diff * 5 + (wp.full ? wp.act : Math.max(0, wp.act - 1)));
    if (wp.diff === 2 && wp.act === 5 && wp.full) progVal = 15;
    raw[21] = progVal;
    raw[26] = 0x1E;
    var arrivalIdx = Math.min(4, wp.full ? wp.act : Math.max(0, wp.act - 1));
    raw[152] = 0; raw[153] = 0; raw[154] = 0;
    raw[152 + wp.diff] = 0x80 | arrivalIdx;

    // 3. Woo! Quests & Quest Bonuses
    var woo = findMarker(raw, "Woo!", 0);
    var qSk = 0, qSt = 0, qLife = 0;
    if (woo !== -1) {{
      for (var d = 0; d < 3; d++) {{
        var base = woo + 10 + d * 96;
        for (var w = 0; w < 48; w++) dv.setUint16(base + w * 2, 0, true);
        if (d <= wp.diff) {{
          var maxAct = (d < wp.diff) ? 5 : wp.act;
          var compFinal = (d < wp.diff) ? true : wp.full;
          var compUpto = compFinal ? maxAct : (maxAct - 1);
          dv.setUint16(base, 0x0001, true);
          for (var a = 1; a <= compUpto; a++) {{
            var pairs = ACT_COMPLETED_QUEST_WORDS[a] || [];
            for (var p = 0; p < pairs.length; p++) {{
              var wIdx = pairs[p][0], wVal = pairs[p][1];
              dv.setUint16(base + wIdx * 2, dv.getUint16(base + wIdx * 2, true) | wVal, true);
            }}
          }}
        }}
        var q41 = dv.getUint16(base + 41 * 2, true);
        dv.setUint16(base + 41 * 2, (q41 | 0x8001) & ~0x0002, true);
        if (dv.getUint16(base + 1 * 2, true) & 1) qSk += 1;
        if (dv.getUint16(base + 9 * 2, true) & 1) qSk += 1;
        if (dv.getUint16(base + 17 * 2, true) & 1) qSt += 5;
        if (dv.getUint16(base + 20 * 2, true) & 1) qLife += 20;
        if (dv.getUint16(base + 25 * 2, true) & 1) qSk += 2;
      }}
    }}

    // 4. WS Waypoints (using BigInt for 39-bit masks)
    var ws = findMarker(raw, "WS", woo !== -1 ? woo : 0);
    if (ws !== -1) {{
      for (var d2 = 0; d2 < 3; d2++) {{
        var off = ws + 8 + d2 * 24;
        var mask = 1n;
        if (d2 < wp.diff) {{
          mask = (1n << 39n) - 1n;
        }} else if (d2 === wp.diff) {{
          if (!wp.full && wp.act === 1) {{
            mask = 1n;
          }} else if (wp.full) {{
            var nWps = BigInt(ACT_CUMULATIVE_WPS[wp.act]);
            mask = (1n << nWps) - 1n;
            if (wp.act < 5) mask |= (1n << BigInt(ACT_TOWN_WP_BIT[wp.act + 1]));
          }} else {{
            var pWps = BigInt(ACT_CUMULATIVE_WPS[wp.act - 1] || 0);
            var tBit = BigInt(ACT_TOWN_WP_BIT[wp.act]);
            mask = ((1n << pWps) - 1n) | (1n << tBit);
          }}
        }}
        raw[off] = 2; raw[off + 1] = 1;
        for (var mb = 0; mb < 5; mb++) {{
          raw[off + 2 + mb] = Number((mask >> BigInt(mb * 8)) & 0xFFn);
        }}
      }}
    }}

    // 5. Reroll Map Seed
    if (woo >= 248) {{
      var seedOff = (woo === 403) ? 155 : (woo - 162);
      dv.setUint32(seedOff, Math.floor(Math.random() * 0x7FFFFFFD) + 1, true);
    }}

    // 6. Build gf stats & 30 zeroed skill points, preserving raw[jm:] bit-for-bit
    var gf = findMarker(raw, "gf", ws !== -1 ? ws : 0);
    var ifPos = findMarker(raw, "if", gf);
    var jm = findMarker(raw, "JM", ifPos);
    var life = cs.hpadd + cs.vit + (level - 1) * (cs.LifePerLevel / 4.0) + qLife;
    var mana = cs.int + (level - 1) * (cs.ManaPerLevel / 4.0);
    var stam = cs.stamina + (level - 1) * (cs.StaminaPerLevel / 4.0);
    var statPts = (level - 1) * cs.StatPerLevel + qSt;
    var skPts = Math.min(255, (level - 1) * cs.SkillsPerLevel + qSk);
    var sGold = defaultGoldForLevel(level);
    var statsObj = {{
      0: cs.str,
      1: cs.int,
      2: cs.dex,
      3: cs.vit,
      6: Math.round(life * 256),
      7: Math.round(life * 256),
      8: Math.round(mana * 256),
      9: Math.round(mana * 256),
      10: Math.round(stam * 256),
      11: Math.round(stam * 256),
      12: level,
      13: CHAR_GEN_DATA.exp[level] || 0
    }};
    if (statPts > 0) statsObj[4] = statPts;
    if (skPts > 0) statsObj[5] = skPts;
    if (sGold > 0) statsObj[15] = sGold;

    var gfBytes = encodeGfSection(statsObj);
    var tailLen = raw.length - jm;
    var totalLen = gf + 2 + gfBytes.length + 2 + 30 + tailLen;
    var rebuilt = new Uint8Array(totalLen);
    rebuilt.set(raw.subarray(0, gf), 0);
    rebuilt[gf] = 0x67; rebuilt[gf + 1] = 0x66; // 'gf'
    rebuilt.set(gfBytes, gf + 2);
    var newIf = gf + 2 + gfBytes.length;
    rebuilt[newIf] = 0x69; rebuilt[newIf + 1] = 0x66; // 'if'
    // 30 zero bytes for unallocated skills follow automatically
    rebuilt.set(raw.subarray(jm), newIf + 2 + 30);

    // 7. Recompute file length (offset 8) and 32-bit rotate-left checksum (offset 12)
    var rdv = new DataView(rebuilt.buffer, rebuilt.byteOffset, rebuilt.byteLength);
    rdv.setUint32(8, rebuilt.length, true);
    rdv.setUint32(12, 0, true);
    var csum = 0;
    for (var ci = 0; ci < rebuilt.length; ci++) {{
      csum = (((csum << 1) | (csum >>> 31)) >>> 0);
      csum = ((csum + rebuilt[ci]) >>> 0);
    }}
    rdv.setUint32(12, csum, true);
    return rebuilt;
  }}

  async function saveD2sBytes(bytes, filename) {{
    if (window.showSaveFilePicker) {{
      try {{
        var handle = await window.showSaveFilePicker({{
          suggestedName: filename,
          types: [{{ description: "Diablo II Character Save (.d2s)", accept: {{ "application/octet-stream": [".d2s"] }} }}]
        }});
        var writable = await handle.createWritable();
        await writable.write(bytes);
        await writable.close();
        return true;
      }} catch (err) {{
        if (err && err.name === "AbortError") return false;
      }}
    }}
    var blob = new Blob([bytes], {{ type: "application/octet-stream" }});
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(function() {{ document.body.removeChild(a); URL.revokeObjectURL(url); }}, 500);
    return true;
  }}

  if (cgNameEl) cgNameEl.addEventListener("input", updateCharGenUI);
  if (cgClassEl) cgClassEl.addEventListener("change", updateCharGenUI);
  if (cgLevelEl) cgLevelEl.addEventListener("input", updateCharGenUI);
  if (cgWpEl) cgWpEl.addEventListener("change", updateCharGenUI);

  if (cgCopyLinkBtn) {{
    cgCopyLinkBtn.addEventListener("click", function() {{
      var fullUrl = buildShareableInviteUrl(true);
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(fullUrl);
      }}
      cgCopyLinkBtn.textContent = "✓ Copied Invite Link!";
      setTimeout(function() {{ cgCopyLinkBtn.innerHTML = "&#128279; Copy Pre-Filled Invite Link"; }}, 3000);
    }});
  }}

  if (cgCopyWinBtn) {{
    cgCopyWinBtn.addEventListener("click", function() {{
      var winPath = "%USERPROFILE%\\\\Saved Games\\\\Diablo II Resurrected\\\\mods\\\\castalia";
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(winPath);
      }}
      cgCopyWinBtn.textContent = "✓ Copied! Paste (Ctrl+L, Ctrl+V) in Save As";
      setTimeout(function() {{ cgCopyWinBtn.innerHTML = "&#128203; Copy Windows Save Path"; }}, 3500);
    }});
  }}

  if (cgDownloadBtn) {{
    cgDownloadBtn.addEventListener("click", async function() {{
      var cleanName = sanitizeCharName(cgNameEl ? cgNameEl.value : "");
      if (cleanName.length < 2) {{
        if (cgStatusEl) {{
          cgStatusEl.className = "d2-red";
          cgStatusEl.textContent = "Please enter a unique character name (2–15 letters) first!";
        }}
        if (cgNameEl) cgNameEl.focus();
        return;
      }}
      var clsCode = cgClassEl ? cgClassEl.value : "pal";
      var lvl = Math.max(1, Math.min(99, parseInt(cgLevelEl ? cgLevelEl.value : "30", 10) || 30));
      var wpCode = cgWpEl ? cgWpEl.value : "a5n";

      try {{
        var bytes = generateD2sClientSide(cleanName, clsCode, lvl, wpCode);
        var saved = await saveD2sBytes(bytes, cleanName + ".d2s");
        if (saved && cgStatusEl) {{
          cgStatusEl.className = "d2-green";
          cgStatusEl.textContent = "✓ Saved " + cleanName + ".d2s (" + bytes.length + " bytes)! Place in Saved Games\\\\Diablo II Resurrected\\\\mods\\\\castalia";
        }}
      }} catch (err) {{
        if (cgStatusEl) {{
          cgStatusEl.className = "d2-red";
          cgStatusEl.textContent = "Error: " + (err.message || String(err));
        }}
      }}
    }});
  }}

  updateCharGenUI();

  // =========================================================================
  // TOP ARREAT SUMMIT TAB ROUTER (REDUCES PAGE DENSITY TO 1 FOCUSED PANEL)
  // =========================================================================
  var tabBtns = document.querySelectorAll(".top-tab-btn");
  var tabPanels = document.querySelectorAll(".tab-panel");
  var tabLinks = document.querySelectorAll("[data-tab-link]");

  var HASH_TO_TAB = {{
    "#overview": "tab-overview",
    "#quickstart": "tab-overview",
    "#cube-recipes": "tab-overview",
    "#philosophy": "tab-overview",
    "#gold-economy": "tab-overview",
    "#notes": "tab-overview",
    "#char-generator": "tab-chargen",
    "#class-pal": "tab-class-pal",
    "#class-bar": "tab-class-bar",
    "#class-ass": "tab-class-ass",
    "#class-sor": "tab-class-sor",
    "#gems-skulls": "tab-items",
    "#runes-33": "tab-items",
    "#monsters": "tab-world",
    "#dungeons": "tab-world",
    "#mercenaries": "tab-world"
  }};

  function activateTab(tabId, skipScroll) {{
    if (!tabId) return;
    for (var i = 0; i < tabPanels.length; i++) {{
      if (tabPanels[i].id === tabId) tabPanels[i].classList.add("active");
      else tabPanels[i].classList.remove("active");
    }}
    for (var j = 0; j < tabBtns.length; j++) {{
      if (tabBtns[j].getAttribute("data-tab") === tabId) tabBtns[j].classList.add("active");
      else tabBtns[j].classList.remove("active");
    }}
    if (!skipScroll) window.scrollTo(0, 0);
  }}

  for (var tb = 0; tb < tabBtns.length; tb++) {{
    tabBtns[tb].addEventListener("click", function(e) {{
      var tid = this.getAttribute("data-tab");
      if (tid) activateTab(tid, false);
    }});
  }}

  for (var tl = 0; tl < tabLinks.length; tl++) {{
    tabLinks[tl].addEventListener("click", function() {{
      var tid = this.getAttribute("data-tab-link");
      if (tid) activateTab(tid, true);
    }});
  }}

  function syncTabFromLocation() {{
    var h = (window.location.hash || "").toLowerCase();
    var sp = new URLSearchParams(window.location.search || "");
    if (HASH_TO_TAB[h]) {{
      activateTab(HASH_TO_TAB[h], true);
      return;
    }}
    if (h.indexOf("#sk-pal-") === 0) {{ activateTab("tab-class-pal", true); return; }}
    if (h.indexOf("#sk-bar-") === 0) {{ activateTab("tab-class-bar", true); return; }}
    if (h.indexOf("#sk-ass-") === 0) {{ activateTab("tab-class-ass", true); return; }}
    if (h.indexOf("#sk-sor-") === 0) {{ activateTab("tab-class-sor", true); return; }}
    if (sp.get("name") || sp.get("class") || sp.get("level") || sp.get("wp")) {{
      activateTab("tab-chargen", true);
      return;
    }}
  }}

  window.addEventListener("hashchange", syncTabFromLocation);
  syncTabFromLocation();
}})();
</script>
</body>
</html>
"""
    out_html = os.path.join(SITE_DIR, "index.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return out_html


if __name__ == "__main__":
    p = build_site()
    print(f"Built site at: {p}")

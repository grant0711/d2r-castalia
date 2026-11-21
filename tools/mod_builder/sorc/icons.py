"""
Sorceress skill icons (soskillicon.sprite / .lowend.sprite).

Fire tree icon changes (cel = normal frame, cel+1 = pressed frame; each cel is 132x130 HD / 67x65 lowend):
  - Ignition      (row 'fire mastery',      cel 50) <- vanilla Warmth icon (cel 2)
  - Conflagration (row 'enchant',           cel 32) <- vanilla Fire Mastery icon (cel 50)
  - Brimstone     (row 'inferno',           cel 10) <- vanilla Fire Ball icon (cel 22)
  - Kindling      (row 'warmth',            cel  2) <- NEW: simplified flaming sword & horned demon silhouette (assets/skill_icons/kindling.jpg)
  - Pyroclasm     (row 'fire ball',         cel 22) <- NEW: four radial fire bolts (assets/skill_icons/pyroclasm.jpg)

Lightning tree icon changes:
  - Overcharge     (row 'energy shield',     cel 44) <- vanilla Lightning Mastery icon (cel 54)
  - Echo           (row 'lightning mastery', cel 54) <- NEW: concentric echo wave arcs (assets/skill_icons/echo.jpg)
  - Conduction     (row 'telekinesis',       cel 14) <- NEW: lightning bolt & horned demon silhouette (assets/skill_icons/conduction.jpg)
  - Sunderbolt     (row 'static field',      cel 12) <- NEW: downward bolt splitting shock wedges (assets/skill_icons/sunderbolt.jpg)
  - Heaven's Wrath (row 'charged bolt',      cel  4) <- NEW: celestial starburst halo pierced by thunderbolt (assets/skill_icons/heavens_wrath.jpg)
New icons are stamped as silver-plate silhouettes on the same brown stone tile as the vanilla icons.
"""
import math
import os
import subprocess

from mod_builder.common import MOD_ROOT, REPO_ROOT, VANILLA_ROOT

FW, FH, NF = 132, 130, 60
FW_LOW, FH_LOW = 67, 65
PX0, PX1, PY0, PY1 = 19, 112, 19, 111  # plate interior (93x92)
CX, CY = 65.5, 65.0

# dst cel <- src cel (verbatim copies of vanilla art)
COPY_CELS = {50: 2, 32: 50, 10: 22, 44: 54}


def _cel(buf: bytes, cel: int, w: int, h: int) -> bytearray:
    rb = NF * w * 4
    out = bytearray(w * h * 4)
    for y in range(h):
        out[y * w * 4:(y + 1) * w * 4] = buf[y * rb + cel * w * 4: y * rb + (cel + 1) * w * 4]
    return out


def _put(dst: bytearray, cel: int, frame: bytes, w: int, h: int) -> None:
    rb = NF * w * 4
    for y in range(h):
        dst[y * rb + cel * w * 4: y * rb + (cel + 1) * w * 4] = frame[y * w * 4:(y + 1) * w * 4]


def _is_silver(r: int, g: int, b: int, pressed: int) -> bool:
    return (r - b) <= 13 and g >= (56 if pressed else 68)


def _mask_from_cel(cel_buf: bytearray, pressed: int) -> list:
    m = [[0.0] * FW for _ in range(FH)]
    for y in range(PY0 + 3, PY1 - 3):
        for x in range(PX0 + 3, PX1 - 3):
            o = (y * FW + x) * 4
            if _is_silver(cel_buf[o], cel_buf[o + 1], cel_buf[o + 2], pressed):
                m[y][x] = 1.0
    return m


def _dilate(m: list, r: int) -> list:
    out = [[0.0] * FW for _ in range(FH)]
    for y in range(PY0, PY1):
        for x in range(PX0, PX1):
            best = 0.0
            for oy in range(-r, r + 1):
                for ox in range(-r, r + 1):
                    if ox * ox + oy * oy <= r * r:
                        yy, xx = y + oy, x + ox
                        if 0 <= yy < FH and 0 <= xx < FW and m[yy][xx] > best:
                            best = m[yy][xx]
            out[y][x] = best
    return out


def _brown_templates(sor_raw: bytes) -> list:
    """Reconstruct clean, blotch-free Sorceress brown stone plates from complementary vanilla cels."""
    m12 = _dilate(_mask_from_cel(_cel(sor_raw, 12, FW, FH), 0), 6)
    m54 = _dilate(_mask_from_cel(_cel(sor_raw, 54, FW, FH), 0), 6)
    tmpls = []
    for pressed in (0, 1):
        c12 = bytearray(_cel(sor_raw, 12 + pressed, FW, FH))  # Static Field (clean center & axes)
        c44 = _cel(sor_raw, 44 + pressed, FW, FH)            # Energy Shield (clean mid annulus)
        c54 = _cel(sor_raw, 54 + pressed, FW, FH)            # Lightning Mastery (clean outer quadrants)
        for y in range(20, 110):
            for x in range(20, 110):
                if m12[y][x] > 0 and abs(x - CX) > 12.5 and abs(y - CY) > 12.5:
                    o = (y * FW + x) * 4
                    c12[o:o + 4] = c54[o:o + 4] if m54[y][x] == 0 else c44[o:o + 4]
                elif m12[y][x] > 0 and 15.0 <= math.hypot(x - CX, y - CY) <= 26.0:
                    o = (y * FW + x) * 4
                    c12[o:o + 4] = c44[o:o + 4]
        tmpls.append(c12)
    return tmpls


def _silver_templates(bar_raw: bytes) -> list:
    """Reconstruct 100% defect-free brushed silver-plate templates from Barbarian cels."""
    donor_cels = tuple(range(0, 60, 2))
    tmpls = []
    rb = NF * FW * 4
    for pressed in (0, 1):
        g_min, g_max = (112, 175) if pressed else (136, 202)
        t = bytearray(FW * FH * 4)
        for y in range(FH):
            for x in range(FW):
                vals = []
                for dc in donor_cels:
                    o = y * rb + ((dc + pressed) * FW + x) * 4
                    r, g, b, a = bar_raw[o:o + 4]
                    if (r - b) <= 4 and g_min <= g <= g_max:
                        vals.append((r + g + b, r, g, b, a))
                if vals:
                    vals.sort(key=lambda v: v[0])
                    _, r, g, b, a = vals[len(vals) // 2]
                else:
                    v = 138 if pressed else 166
                    r, g, b, a = v - 2, v, v + 2, 255
                t[(y * FW + x) * 4:(y * FW + x) * 4 + 4] = bytes((r, g, b, a))
        tmpls.append(t)
    return tmpls


def _stamp(base: bytearray, mask: list, silver: bytearray, pressed: int) -> bytearray:
    out = bytearray(base)
    bright = 0.84 if pressed else 1.0
    for y in range(PY0 + 1, PY1 - 1):
        for x in range(PX0 + 1, PX1 - 1):
            m = mask[y][x]
            m_max = max(m, mask[y - 1][x], mask[y + 1][x], mask[y][x - 1], mask[y][x + 1])
            if m_max <= 0.05:
                continue
            o = (y * FW + x) * 4
            br_r, br_g, br_b = out[o], out[o + 1], out[o + 2]
            if m <= 0.12:
                t = min(1.0, (m_max - 0.05) / 0.5)
                out[o:o + 4] = bytes((int(br_r * (1 - 0.88 * t)), int(br_g * (1 - 0.88 * t)),
                                      int(br_b * (1 - 0.88 * t)), 255))
                continue
            sr, sg, sb = silver[o], silver[o + 1], silver[o + 2]
            if mask[y - 1][x - 1] < 0.35:
                sr, sg, sb = (min(255, v + int(48 * bright)) for v in (sr, sg, sb))
            elif mask[y + 1][x + 1] < 0.35:
                sr, sg, sb = (max(0, v - int(42 * bright)) for v in (sr, sg, sb))
            a = min(1.0, (m - 0.12) / 0.45)
            out[o:o + 4] = bytes((int(br_r * (1 - a) + sr * a), int(br_g * (1 - a) + sg * a),
                                  int(br_b * (1 - a) + sb * a), 255))
    return out


def _shift(mask: list, d: int) -> list:
    out = [[0.0] * FW for _ in range(FH)]
    for y in range(FH - d):
        out[y + d][d:] = mask[y][:FW - d]
    return out


def _downscale(frame: bytes) -> bytes:
    return subprocess.check_output(
        ["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{FW}x{FH}", "-i", "-",
         "-vf", "scale=66:65:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
        input=bytes(frame))


def _mask_from_icon_jpg(filename: str, inset: int = 5) -> list:
    """Load a white-on-black silhouette JPEG from assets/skill_icons/ into the plate interior."""
    img_path = os.path.join(REPO_ROOT, "assets", "skill_icons", filename)
    pw = (PX1 - PX0) - 2 * inset
    ph = (PY1 - PY0) - 2 * inset
    art_px = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", img_path,
        "-vf", f"scale={pw}:{ph}:flags=lanczos",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"
    ])
    m = [[0.0] * FW for _ in range(FH)]
    for py in range(ph):
        for px_i in range(pw):
            aoff = (py * pw + px_i) * 3
            lum = (art_px[aoff] + art_px[aoff + 1] + art_px[aoff + 2]) / (3.0 * 255.0)
            tx = PX0 + inset + px_i
            ty = PY0 + inset + py
            if PX0 + 2 <= tx < PX1 - 2 and PY0 + 2 <= ty < PY1 - 2:
                m[ty][tx] = max(0.0, min(1.0, (lum - 0.35) / 0.35))
    return m


def kindling_mask(src_cels: dict, pressed: int) -> list:
    return _mask_from_icon_jpg("kindling.jpg", inset=4)


def pyroclasm_mask(src_cels: dict, pressed: int) -> list:
    return _mask_from_icon_jpg("pyroclasm.jpg", inset=6)


def echo_mask(src_cels: dict, pressed: int) -> list:
    return _mask_from_icon_jpg("echo.jpg", inset=3)


def conduction_mask(src_cels: dict, pressed: int) -> list:
    return _mask_from_icon_jpg("conduction.jpg", inset=3)


def sunderbolt_mask(src_cels: dict, pressed: int) -> list:
    return _mask_from_icon_jpg("sunderbolt.jpg", inset=3)


def heavens_wrath_mask(src_cels: dict, pressed: int) -> list:
    return _mask_from_icon_jpg("heavens_wrath.jpg", inset=3)


def build_soskillicon_pair() -> str:
    rel = "data/hd/global/ui/spells/sorceress/"
    src_hd = os.path.join(VANILLA_ROOT, rel, "soskillicon.sprite")
    src_low = os.path.join(VANILLA_ROOT, rel, "soskillicon.lowend.sprite")
    bar_src = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/barbarian/baskillicon.sprite")
    with open(src_hd, "rb") as f:
        raw_hd = f.read()
    with open(src_low, "rb") as f:
        raw_low = f.read()
    with open(bar_src, "rb") as f:
        bar_raw = f.read()[40:]
    hdr_hd, hdr_low = raw_hd[:40], raw_low[:40]
    sor_raw = raw_hd[40:]
    low_raw = raw_low[40:]
    if len(sor_raw) != NF * FW * FH * 4 or len(low_raw) != NF * FW_LOW * FH_LOW * 4:
        raise RuntimeError("soskillicon sprite has unexpected dimensions")
    out_hd, out_low = bytearray(sor_raw), bytearray(low_raw)

    # 1. verbatim vanilla art moves
    for dst, src in COPY_CELS.items():
        for p in (0, 1):
            _put(out_hd, dst + p, _cel(sor_raw, src + p, FW, FH), FW, FH)
            _put(out_low, dst + p, _cel(low_raw, src + p, FW_LOW, FH_LOW), FW_LOW, FH_LOW)

    # 2. new art
    src_cels = {c: _cel(sor_raw, c, FW, FH) for c in (0, 1, 32, 33)}
    brown = _brown_templates(sor_raw)
    silver = _silver_templates(bar_raw)
    for dst, maker in (
        (2, kindling_mask),
        (22, pyroclasm_mask),
        (54, echo_mask),
        (14, conduction_mask),
        (12, sunderbolt_mask),
        (4, heavens_wrath_mask),
    ):
        for p in (0, 1):
            mask = maker(src_cels, p)
            if p:
                mask = _shift(mask, 2)
            frame = _stamp(brown[p], mask, silver[p], p)
            _put(out_hd, dst + p, bytes(frame), FW, FH)
            low = _downscale(frame)
            padded = bytearray(FW_LOW * FH_LOW * 4)
            for y in range(FH_LOW):
                padded[y * FW_LOW * 4: y * FW_LOW * 4 + 66 * 4] = low[y * 66 * 4:(y + 1) * 66 * 4]
            _put(out_low, dst + p, bytes(padded), FW_LOW, FH_LOW)

    dst_hd = os.path.join(MOD_ROOT, rel, "soskillicon.sprite")
    dst_low = os.path.join(MOD_ROOT, rel, "soskillicon.lowend.sprite")
    os.makedirs(os.path.dirname(dst_hd), exist_ok=True)
    with open(dst_hd, "wb") as f:
        f.write(hdr_hd + out_hd)
    with open(dst_low, "wb") as f:
        f.write(hdr_low + out_low)
    return f"{dst_hd}, {dst_low}"


def render_preview(path: str, cels=(50, 32, 10, 2, 22), sprite=None) -> None:
    """Dev helper: PNG strip of the given cels (normal frames) from the built HD sprite."""
    sprite = sprite or os.path.join(MOD_ROOT, "data/hd/global/ui/spells/sorceress/soskillicon.sprite")
    raw = open(sprite, "rb").read()[40:]
    rb = NF * FW * 4
    strip = bytearray()
    for y in range(FH):
        for c in cels:
            strip += raw[y * rb + c * FW * 4: y * rb + (c + 1) * FW * 4]
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s",
                    f"{FW * len(cels)}x{FH}", "-i", "-", path], input=bytes(strip), check=True)

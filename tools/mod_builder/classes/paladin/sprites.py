#!/usr/bin/env python3
"""
paladin/sprites.py
Paladin UI sprite builders (Dismiss Aura submenu icon frames).
"""
def _build_submenu_skillicon_pair(suffix: str, frame_w: int, frame_h: int) -> str:
    """
    Append frames 40 (normal) and 41 (pressed) to data/hd/global/ui/spells/submenu/skillicon{suffix}
    for "Dismiss Aura" (IconCel=40): a hollow circular aura ring with a carved diagonal X across it.
    """
    import math
    import os
    import struct
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    sub_src = os.path.join(VANILLA_ROOT, f"data/hd/global/ui/spells/submenu/skillicon{suffix}")
    pal_src = os.path.join(VANILLA_ROOT, f"data/hd/global/ui/spells/paladin/paskillicon{suffix}")
    with open(sub_src, "rb") as f:
        sub_data = f.read()
    with open(pal_src, "rb") as f:
        pal_px = f.read()[40:]

    sub_hdr = bytearray(sub_data[:40])
    sub_px = sub_data[40:]
    base_frames = 40
    base_row_bytes = base_frames * frame_w * 4
    pal_row_bytes = 60 * frame_w * 4

    total_frames = 42  # frames 0..39 vanilla + 40 (Dismiss Aura normal) + 41 (Dismiss Aura pressed)
    total_w = total_frames * frame_w
    out_px = bytearray(total_w * frame_h * 4)
    out_row_bytes = total_w * 4

    cx = (frame_w - 1) / 2.0
    cy = frame_h / 2.0
    scale = frame_h / 130.0
    r_inner = 22.0 * scale
    r_ring_in = 33.0 * scale
    r_ring_out = 45.0 * scale
    x_reach = 36.0 * scale
    x_half_w = 5.5 * scale

    for y in range(frame_h):
        dst_row_off = y * out_row_bytes
        src_sub_off = y * base_row_bytes
        out_px[dst_row_off : dst_row_off + base_row_bytes] = sub_px[src_sub_off : src_sub_off + base_row_bytes]

        for idx_offset, pal_cel in ((0, 16), (1, 17)):  # Defiance normal (16) and pressed (17)
            frame_idx = 40 + idx_offset
            p_off_row = y * pal_row_bytes + pal_cel * frame_w * 4
            u_off_row = y * base_row_bytes + (0 + idx_offset) * frame_w * 4  # Kick frame 0/1 for dark stone background
            f_off_row = dst_row_off + frame_idx * frame_w * 4
            press_shift = 2.0 * scale if idx_offset == 1 else 0.0
            dy = y - (cy + press_shift)

            for x in range(frame_w - 1):
                dx = x - cx
                dist = math.hypot(dx, dy)
                px_p = pal_px[p_off_row + x * 4 : p_off_row + (x + 1) * 4]
                r, g, b, a = px_p[0], px_p[1], px_p[2], px_p[3]

                # 1. Replace the inner shield emblem inside the aura circle with the warm brownish plate color of the bounding box
                if dist < r_ring_in:
                    t = max(0.0, min(1.0, (dist - r_inner) / max(1.0, r_ring_in - r_inner)))
                    # Use subtle texture variation from the original pixel mapped onto the warm brownish plate palette (~RGB 72, 48, 32)
                    tex = ((r + g + b) / 765.0 - 0.5) * 18.0
                    pr = max(35, min(110, int(72 + tex)))
                    pg = max(24, min(80, int(48 + tex * 0.75)))
                    pb = max(16, min(58, int(33 + tex * 0.55)))
                    r = int(pr * (1.0 - t) + r * t * 0.90)
                    g = int(pg * (1.0 - t) + g * t * 0.90)
                    b = int(pb * (1.0 - t) + b * t * 0.90)
                elif dist <= r_ring_out + 6.0 * scale:
                    # Subtle silver-gold tone on the circular aura ring itself
                    lum = int(r * 0.35 + g * 0.45 + b * 0.20)
                    r = min(255, int(lum * 1.05 + 15))
                    g = min(255, int(lum * 0.98 + 10))
                    b = min(255, int(lum * 0.88 + 5))

                # 2. Composite a crisp diagonal "X" slash across the aura circle matching the warm gold/ivory of the aura ring
                if abs(dx) <= x_reach and abs(dy) <= x_reach and dist <= r_ring_out + 2.0 * scale:
                    d1 = abs(dx - dy) / 1.41421356
                    d2 = abs(dx + dy) / 1.41421356
                    d_x = min(d1, d2)
                    if d_x <= x_half_w + 1.5 * scale:
                        if d_x <= x_half_w - 1.2 * scale:
                            # Bevelled warm gold / ivory X core matching the Paladin aura ring
                            ridge = max(0.0, 1.0 - (d_x / max(0.5, x_half_w - 1.2 * scale)))
                            xr = min(255, int(175 + 70 * ridge))
                            xg = min(255, int(155 + 75 * ridge))
                            xb = min(255, int(115 + 75 * ridge))
                            r, g, b = xr, xg, xb
                        else:
                            # Dark outline around the X bars for contrast against the aura ring
                            r = int(r * 0.25)
                            g = int(g * 0.22)
                            b = int(b * 0.18)

                out_px[f_off_row + x * 4 : f_off_row + (x + 1) * 4] = bytes((r, g, b, a))

            # Clamp rightmost separator column (frame_w - 1) to match column (frame_w - 2)
            out_px[f_off_row + (frame_w - 1) * 4 : f_off_row + frame_w * 4] = out_px[
                f_off_row + (frame_w - 2) * 4 : f_off_row + (frame_w - 1) * 4
            ]

    struct.pack_into("<I", sub_hdr, 8, total_w)
    struct.pack_into("<I", sub_hdr, 12, frame_h)
    struct.pack_into("<I", sub_hdr, 20, total_frames)
    struct.pack_into("<I", sub_hdr, 32, len(out_px))

    dst_path = os.path.join(MOD_ROOT, f"data/hd/global/ui/spells/submenu/skillicon{suffix}")
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "wb") as f:
        f.write(sub_hdr + out_px)
    return dst_path



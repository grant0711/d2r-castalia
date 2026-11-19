#!/usr/bin/env python3
"""
barbarian/sprites.py
Barbarian skill icons (baskillicon), skill tree background plates (baskilltree),
and Shield Slam sequence animation state machine (barbarian_state_machine.json).
"""
def _build_baskillicon_pair(suffix: str, frame_w: int, frame_h: int) -> str:
    """
    Build data/hd/global/ui/spells/barbarian/baskillicon{suffix} with:
      1. Passive Combat Masteries (stamped as recessed brown cutouts on the brushed-silver plate):
         - IconCel  2 (frames  2,  3): One-Handed Mastery (Id 127)
         - IconCel  4 (frames  4,  5): Two-Handed Mastery (Id 128)
         - IconCel  6 (frames  6,  7): Battle Fervor (Id 129)
         - IconCel 16 (frames 16, 17): Critical Strike (Id 134)
         - IconCel 20 (frames 20, 21): Venom Ward (Id 136)
         - IconCel 30 (frames 30, 31): Unflinching (Id 141)
      2. Active Warcries & Combat Skills (stamped in brushed silver on the dark-brown active plate):
         - IconCel 10 (frames 10, 11): Second Wind (Id 131) - Howling Barbarian + 1 '+' sign
         - IconCel 32 (frames 32, 33): Enduring Cry (Id 142) - Howling Barbarian + 3 '+' signs
         - IconCel 48 (frames 48, 49): Bloodlust (Id 150) - Howling Barbarian + shrunk Grim Ward skull & crossbones
         - IconCel 26 (frames 26, 27): Shield Slam (Id 139) - AI-generated minimalist Shield Slam silhouette
    """
    import os
    import subprocess
    from mod_builder.common import MOD_ROOT, REPO_ROOT, VANILLA_ROOT

    d2r_root = REPO_ROOT
    src_path = os.path.join(VANILLA_ROOT, f"data/hd/global/ui/spells/barbarian/baskillicon{suffix}")
    with open(src_path, "rb") as f:
        raw = f.read()

    hdr = raw[:40]
    out_px = bytearray(raw[40:])
    total_frames = 60
    row_bytes = total_frames * frame_w * 4

    is_hd = frame_h >= 100
    scale_f = 1.0 if is_hd else 0.5
    # Inner brushed-silver plate bounds inside the 4-rivet bronze border
    plate_x0, plate_x1 = (19, 112) if is_hd else (10, 56)
    plate_y0, plate_y1 = (19, 111) if is_hd else (10, 55)
    plate_w = plate_x1 - plate_x0
    plate_h = plate_y1 - plate_y0
    press_shift = 2 if is_hd else 1

    # 1. Reconstruct clean blank normal & pressed silver-plate button templates across vanilla
    #    passive frames (2, 4, 6, 16, 18, 20, 30, 38, 44).
    donor_cels = (2, 4, 6, 16, 18, 20, 30, 38, 44)
    blank_templates = [bytearray(frame_w * frame_h * 4), bytearray(frame_w * frame_h * 4)]
    for pressed in (0, 1):
        tmpl = blank_templates[pressed]
        g_min = 112 if pressed else 136
        g_max = 172 if pressed else 198
        for y in range(frame_h):
            in_plate_y = plate_y0 <= y < plate_y1
            for x in range(frame_w):
                in_plate = in_plate_y and (plate_x0 <= x < plate_x1)
                samples = []
                clean_silver = []
                for dc in donor_cels:
                    soff = y * row_bytes + ((dc + pressed) * frame_w + x) * 4
                    r, g, b, a = raw[40 + soff : 40 + soff + 4]
                    samples.append((r + g + b, r, g, b, a))
                    if in_plate and (r - b) <= 0 and g_min <= g <= g_max:
                        clean_silver.append((r + g + b, r, g, b, a))
                if clean_silver:
                    clean_silver.sort(key=lambda t: t[0])
                    _, r, g, b, a = clean_silver[len(clean_silver) // 2]
                elif in_plate:
                    found = False
                    for mx, my in (
                        (plate_x0 + plate_x1 - 1 - x, y),
                        (x, plate_y0 + plate_y1 - 1 - y),
                        (plate_x0 + 6, plate_y0 + 6),
                    ):
                        msamples = []
                        for dc in donor_cels:
                            soff = my * row_bytes + ((dc + pressed) * frame_w + mx) * 4
                            r, g, b, a = raw[40 + soff : 40 + soff + 4]
                            if (r - b) <= 0 and g_min <= g <= g_max:
                                msamples.append((r + g + b, r, g, b, a))
                        if msamples:
                            msamples.sort(key=lambda t: t[0])
                            _, r, g, b, a = msamples[len(msamples) // 2]
                            found = True
                            break
                    if not found:
                        samples.sort(key=lambda t: t[0])
                        _, r, g, b, a = samples[-3]
                else:
                    samples.sort(key=lambda t: t[0])
                    _, r, g, b, a = samples[-3]
                doff = (y * frame_w + x) * 4
                tmpl[doff : doff + 4] = bytes((r, g, b, a))

    # 2. Stamp the 6 v2 AI-generated passive Combat Mastery icons
    icon_specs = (
        (2, "one_handed_mastery.jpg", 0.10),
        (4, "two_handed_mastery.jpg", 0.08),
        (6, "battle_fervor.jpg", 0.10),
        (16, "critical_strike.jpg", 0.12),
        (20, "venom_ward.jpg", 0.14),
        (30, "unflinching.jpg", 0.10),
    )

    for base_cel, filename, crop_margin in icon_specs:
        img_path = os.path.join(d2r_root, "assets", "skill_icons", filename)
        keep_frac = 1.0 - 2.0 * crop_margin
        art_px = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                img_path,
                "-vf",
                f"crop=iw*{keep_frac:.2f}:ih*{keep_frac:.2f}:iw*{crop_margin:.2f}:ih*{crop_margin:.2f},scale={plate_w}:{plate_h}:flags=lanczos",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ]
        )

        mask = [[0.0] * plate_w for _ in range(plate_h)]
        for py in range(plate_h):
            for px_i in range(plate_w):
                aoff = (py * plate_w + px_i) * 3
                lum = (art_px[aoff] + art_px[aoff + 1] + art_px[aoff + 2]) / (3.0 * 255.0)
                m = max(0.0, min(1.0, (0.72 - lum) / 0.37))
                edge_d = min(px_i, plate_w - 1 - px_i, py, plate_h - 1 - py)
                if edge_d < 2:
                    m = 0.0
                elif edge_d == 2:
                    m *= 0.5
                mask[py][px_i] = m

        for pressed in (0, 1):
            fidx = base_cel + pressed
            tmpl = blank_templates[pressed]
            shift = press_shift if pressed else 0
            bright = 0.84 if pressed else 1.0

            for y in range(frame_h):
                row_off = y * row_bytes + fidx * frame_w * 4
                t_off = y * frame_w * 4
                out_px[row_off : row_off + frame_w * 4] = tmpl[t_off : t_off + frame_w * 4]

            for py in range(plate_h):
                sy = py - shift
                if not (0 <= sy < plate_h):
                    continue
                y = plate_y0 + py
                row_off = y * row_bytes + fidx * frame_w * 4
                for px_i in range(plate_w):
                    sx = px_i - shift
                    if not (0 <= sx < plate_w):
                        continue
                    x = plate_x0 + px_i
                    m = mask[sy][sx]
                    m_tl = mask[max(0, sy - 1)][max(0, sx - 1)]
                    m_br = mask[min(plate_h - 1, sy + 1)][min(plate_w - 1, sx + 1)]

                    px_off = row_off + x * 4
                    sr, sg, sb, sa = out_px[px_off : px_off + 4]

                    if m <= 0.05:
                        if m_tl > 0.55:
                            hl = int(55 * (m_tl - 0.55) / 0.45 * bright)
                            out_px[px_off : px_off + 4] = bytes(
                                (min(255, sr + hl), min(255, sg + hl), min(255, sb + hl), sa)
                            )
                        continue

                    grain = ((sr + sg + sb) / 3.0 - 182.0) * 0.35
                    cr = max(20, min(140, int((68 + grain) * bright)))
                    cg = max(14, min(105, int((48 + grain * 0.75) * bright)))
                    cb = max(10, min(85, int((36 + grain * 0.55) * bright)))

                    if m < 0.65:
                        rim_t = 1.0 - abs(m - 0.40) / 0.40
                        cr = int(cr * (1.0 - 0.72 * rim_t))
                        cg = int(cg * (1.0 - 0.75 * rim_t))
                        cb = int(cb * (1.0 - 0.78 * rim_t))
                    elif m_tl < 0.35:
                        cr = min(255, int(cr + 52 * bright))
                        cg = min(255, int(cg + 34 * bright))
                        cb = min(255, int(cb + 22 * bright))
                    elif m_br < 0.35:
                        cr = int(cr * 0.45)
                        cg = int(cg * 0.42)
                        cb = int(cb * 0.38)

                    r = int(sr * (1.0 - m) + cr * m)
                    g = int(sg * (1.0 - m) + cg * m)
                    b = int(sb * (1.0 - m) + cb * m)
                    out_px[px_off : px_off + 4] = bytes((r, g, b, sa))

    # 3. Reconstruct a spotless dark-brown active skill button template (normal & pressed)
    active_donors = (0, 8, 10, 12, 14, 22, 24, 26, 28, 32, 34, 36, 40, 42, 46, 48, 50, 52, 56, 58)
    brown_templates = [bytearray(frame_w * frame_h * 4), bytearray(frame_w * frame_h * 4)]
    for pressed in (0, 1):
        bt = brown_templates[pressed]
        for y in range(frame_h):
            in_plate_y = plate_y0 <= y < plate_y1
            for x in range(frame_w):
                in_plate = in_plate_y and (plate_x0 <= x < plate_x1)
                samples = []
                brown = []
                for dc in active_donors:
                    off = y * row_bytes + ((dc + pressed) * frame_w + x) * 4
                    r, g, b, a = raw[40 + off : 40 + off + 4]
                    samples.append((r + g + b, r, g, b, a))
                    if (r - b) >= 14 and 20 <= g <= 68:
                        brown.append((r + g + b, r, g, b, a))
                if brown:
                    brown.sort(key=lambda t: t[0])
                    _, r, g, b, a = brown[len(brown) // 2]
                elif in_plate:
                    found = False
                    for mx, my in (
                        (frame_w - 1 - x, y),
                        (x, frame_h - 1 - y),
                        (plate_x0 + 5, plate_y0 + 5),
                    ):
                        mb = []
                        for dc in active_donors:
                            off = my * row_bytes + ((dc + pressed) * frame_w + mx) * 4
                            r, g, b, a = raw[40 + off : 40 + off + 4]
                            if (r - b) >= 14 and 20 <= g <= 68:
                                mb.append((r + g + b, r, g, b, a))
                        if mb:
                            mb.sort(key=lambda t: t[0])
                            _, r, g, b, a = mb[len(mb) // 2]
                            found = True
                            break
                    if not found:
                        samples.sort(key=lambda t: t[0])
                        _, r, g, b, a = samples[len(samples) // 4]
                else:
                    samples.sort(key=lambda t: t[0])
                    _, r, g, b, a = samples[len(samples) // 2]
                bt[(y * frame_w + x) * 4 : (y * frame_w + x) * 4 + 4] = bytes((r, g, b, a))

    # Build clean Howling Barbarian base frame (from Cel 8 Howl, with top-right exclamation marks cleared)
    howl_base = [bytearray(frame_w * frame_h * 4), bytearray(frame_w * frame_h * 4)]
    clear_y0 = int(round(18 * scale_f))
    clear_y1 = int(round(56 * scale_f))
    clear_x0 = int(round(50 * scale_f))
    clear_x1 = int(round(112 * scale_f))
    for pressed in (0, 1):
        hb = howl_base[pressed]
        bt = brown_templates[pressed]
        for y in range(frame_h):
            off = y * row_bytes + ((8 + pressed) * frame_w) * 4
            hb[y * frame_w * 4 : (y + 1) * frame_w * 4] = raw[40 + off : 40 + off + frame_w * 4]
            if clear_y0 <= y <= clear_y1:
                for x in range(clear_x0, clear_x1):
                    p_off = (y * frame_w + x) * 4
                    hb[p_off : p_off + 4] = bt[p_off : p_off + 4]

    def _stamp_silver_fg(base_buf: bytearray, fg_mask, pressed: int) -> bytearray:
        out = bytearray(base_buf)
        st = blank_templates[pressed]
        bright = 0.84 if pressed else 1.0
        for y in range(plate_y0 - 1, plate_y1 + 1):
            for x in range(plate_x0 - 1, plate_x1 + 1):
                m = fg_mask[y][x]
                m_tl = fg_mask[y - 1][x - 1]
                m_br = fg_mask[y + 1][x + 1]
                m_max = max(m, fg_mask[y - 1][x], fg_mask[y + 1][x], fg_mask[y][x - 1], fg_mask[y][x + 1])
                if m_max <= 0.05:
                    continue
                p_off = (y * frame_w + x) * 4
                br_r, br_g, br_b, br_a = out[p_off : p_off + 4]
                if m <= 0.12:
                    t = min(1.0, (m_max - 0.05) / 0.5)
                    out[p_off : p_off + 4] = bytes(
                        (
                            int(br_r * (1.0 - 0.88 * t)),
                            int(br_g * (1.0 - 0.88 * t)),
                            int(br_b * (1.0 - 0.88 * t)),
                            br_a,
                        )
                    )
                    continue
                sr, sg, sb, _ = st[p_off : p_off + 4]
                if m_tl < 0.35:
                    sr = min(255, sr + int(48 * bright))
                    sg = min(255, sg + int(48 * bright))
                    sb = min(255, sb + int(48 * bright))
                elif m_br < 0.35:
                    sr = max(0, sr - int(42 * bright))
                    sg = max(0, sg - int(42 * bright))
                    sb = max(0, sb - int(42 * bright))
                alpha_t = min(1.0, (m - 0.12) / 0.45)
                r = int(br_r * (1.0 - alpha_t) + sr * alpha_t)
                g = int(br_g * (1.0 - alpha_t) + sg * alpha_t)
                b = int(br_b * (1.0 - alpha_t) + sb * alpha_t)
                out[p_off : p_off + 4] = bytes((r, g, b, br_a))
        return out

    def _write_frame_buf(fidx: int, buf: bytearray) -> None:
        for y in range(frame_h):
            row_off = y * row_bytes + fidx * frame_w * 4
            out_px[row_off : row_off + frame_w * 4] = buf[y * frame_w * 4 : (y + 1) * frame_w * 4]

    def _add_plus(mask, cx_hd: float, cy_hd: float, arm_l_hd: float, arm_w_hd: float, shift_px: int) -> None:
        cx = cx_hd * scale_f + shift_px
        cy = cy_hd * scale_f + shift_px
        arm_l = arm_l_hd * scale_f
        arm_w = arm_w_hd * scale_f
        for y in range(plate_y0, plate_y1):
            for x in range(plate_x0, plate_x1):
                dx, dy = abs(x - cx), abs(y - cy)
                d = min(max(dx - arm_l, dy - arm_w), max(dx - arm_w, dy - arm_l))
                val = max(0.0, min(1.0, 0.5 - d * (0.85 / scale_f)))
                if val > mask[y][x]:
                    mask[y][x] = val

    # 3a. Second Wind (IconCel 10, frames 10 & 11): Howling Barbarian + 1 '+' sign
    for pressed in (0, 1):
        shift = press_shift if pressed else 0
        m_sw = [[0.0] * frame_w for _ in range(frame_h)]
        _add_plus(m_sw, cx_hd=80.0, cy_hd=38.0, arm_l_hd=11.0, arm_w_hd=3.6, shift_px=shift)
        _write_frame_buf(10 + pressed, _stamp_silver_fg(howl_base[pressed], m_sw, pressed))

    # 3b. Enduring Cry (IconCel 32, frames 32 & 33): Howling Barbarian + 3 '+' signs
    for pressed in (0, 1):
        shift = press_shift if pressed else 0
        m_ec = [[0.0] * frame_w for _ in range(frame_h)]
        _add_plus(m_ec, cx_hd=71.0, cy_hd=29.0, arm_l_hd=7.5, arm_w_hd=2.6, shift_px=shift)
        _add_plus(m_ec, cx_hd=92.0, cy_hd=33.0, arm_l_hd=7.5, arm_w_hd=2.6, shift_px=shift)
        _add_plus(m_ec, cx_hd=78.0, cy_hd=47.0, arm_l_hd=7.5, arm_w_hd=2.6, shift_px=shift)
        _write_frame_buf(32 + pressed, _stamp_silver_fg(howl_base[pressed], m_ec, pressed))

    # 3c. Bloodlust (IconCel 48, frames 48 & 49): Howling Barbarian + shrunk Grim Ward skull & crossbones
    gw_x0, gw_x1 = int(round(30 * scale_f)), int(round(102 * scale_f))
    gw_y0, gw_y1 = int(round(20 * scale_f)), int(round(108 * scale_f))
    gw_w, gw_h = gw_x1 - gw_x0, gw_y1 - gw_y0
    dst_w, dst_h = max(1, int(round(35 * scale_f))), max(1, int(round(42 * scale_f)))
    for pressed in (0, 1):
        shift = press_shift if pressed else 0
        f_bl = bytearray(howl_base[pressed])
        dst_x0 = int(round(64 * scale_f)) + shift
        dst_y0 = int(round(18 * scale_f)) + shift
        src_cel = 48 + pressed
        for dy in range(dst_h):
            for dx in range(dst_w):
                sx = gw_x0 + shift + (dx + 0.5) * gw_w / dst_w
                sy = gw_y0 + shift + (dy + 0.5) * gw_h / dst_h
                ix, iy = int(sx), int(sy)
                fx, fy = sx - ix, sy - iy
                rgba = [0.0, 0.0, 0.0, 0.0]
                for oy in (0, 1):
                    for ox in (0, 1):
                        wt = ((1.0 - fx) if ox == 0 else fx) * ((1.0 - fy) if oy == 0 else fy)
                        soff = (min(frame_h - 1, iy + oy) * row_bytes) + (src_cel * frame_w + min(frame_w - 1, ix + ox)) * 4
                        for c in range(4):
                            rgba[c] += raw[40 + soff + c] * wt
                sr, sg, sb, _ = [int(round(v)) for v in rgba]
                if ((sr - sb) <= 12 and sg >= (70 if pressed else 85)) or (sg < 32 and (sr + sg + sb) < 95):
                    doff = ((dst_y0 + dy) * frame_w + (dst_x0 + dx)) * 4
                    f_bl[doff : doff + 4] = bytes((sr, sg, sb, 255))
        _write_frame_buf(48 + pressed, f_bl)

    # 3d. Shield Slam (IconCel 26, frames 26 & 27): Minimalist AI-generated Shield Slam silhouette
    ss_path = os.path.join(d2r_root, "assets", "skill_icons", "shield_slam.jpg")
    art_ss = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            ss_path,
            "-vf",
            f"crop=iw*0.80:ih*0.80:iw*0.10:ih*0.10,scale={plate_w}:{plate_h}:flags=lanczos",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ]
    )
    for pressed in (0, 1):
        shift = press_shift if pressed else 0
        m_ss = [[0.0] * frame_w for _ in range(frame_h)]
        for py in range(plate_h):
            sy = py - shift
            if not (0 <= sy < plate_h):
                continue
            for px_i in range(plate_w):
                sx = px_i - shift
                if not (0 <= sx < plate_w):
                    continue
                if min(px_i, plate_w - 1 - px_i, py, plate_h - 1 - py) < 2:
                    continue
                aoff = (sy * plate_w + sx) * 3
                lum = (art_ss[aoff] + art_ss[aoff + 1] + art_ss[aoff + 2]) / (3.0 * 255.0)
                m_ss[plate_y0 + py][plate_x0 + px_i] = max(0.0, min(1.0, (lum - 0.35) / 0.35))
        _write_frame_buf(26 + pressed, _stamp_silver_fg(brown_templates[pressed], m_ss, pressed))

    # 3e. Battle Command (IconCel 58, frames 58 & 59): Left-facing Howling Barbarian + Heart sub-icon
    import math
    for pressed in (0, 1):
        shift = press_shift if pressed else 0
        bcmd_base = bytearray(frame_w * frame_h * 4)
        bt = brown_templates[pressed]
        max_x_clear = int(round((67 + (2 if pressed else 0)) * scale_f))
        max_y_clear = int(round((61 + (2 if pressed else 0)) * scale_f))
        max_xy_clear = int(round((125 + (3 if pressed else 0)) * scale_f))
        for y in range(frame_h):
            off = y * row_bytes + ((58 + pressed) * frame_w) * 4
            bcmd_base[y * frame_w * 4 : (y + 1) * frame_w * 4] = raw[40 + off : 40 + off + frame_w * 4]
            if (plate_y0 - 1) <= y <= max_y_clear:
                for x in range(plate_x0 - 1, min(frame_w, max_x_clear + 1)):
                    if (x + y) <= max_xy_clear:
                        p_off = (y * frame_w + x) * 4
                        bcmd_base[p_off : p_off + 4] = bt[p_off : p_off + 4]

        m_bc = [[0.0] * frame_w for _ in range(frame_h)]
        cx = 50.0 * scale_f + shift
        cy = 38.0 * scale_f + shift
        hr = 7.4 * scale_f
        inv_sqrt2 = 0.7071067811865475

        for y in range(plate_y0, plate_y1):
            for x in range(plate_x0, plate_x1):
                dx = abs(x - cx)
                dy = y - cy
                u = (dx - dy) * inv_sqrt2
                v = (dx + dy) * inv_sqrt2
                if u >= hr or v <= 0.0:
                    d = math.hypot(u - hr, v) - hr
                elif u >= 0.0:
                    d = v - hr
                else:
                    d = math.hypot(u, max(0.0, v - hr)) if v > hr else (v - hr)
                val = max(0.0, min(1.0, 0.5 - d * (0.85 / scale_f)))
                if val > m_bc[y][x]:
                    m_bc[y][x] = val
        _write_frame_buf(58 + pressed, _stamp_silver_fg(bcmd_base, m_bc, pressed))

    dst_path = os.path.join(MOD_ROOT, f"data/hd/global/ui/spells/barbarian/baskillicon{suffix}")
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "wb") as f:
        f.write(hdr + out_px)
    return dst_path


def _build_baskilltree_pair() -> str:
    """
    Build data/hd/global/ui/spells/skill_trees/baskilltree.sprite and .lowend.sprite
    with the reorganized Frame 1 (Barbarian Combat Masteries):
      - Row 1 (y=125): Col 1 (One-Handed Mastery), Col 2 (Two-Handed Mastery), Col 3 (Throwing Mastery)
      - Row 2 (y=304): Col 2 only (Critical Strike, standalone)
      - Left Chain (Col 1, x=109): Row 3 (Unflinching) -> Row 4 (Increased Speed) -> Row 5 (Battle Fervor)
      - Right Chain (Col 3, x=631): Row 4 (Iron Skin) -> Row 5 (Venom Ward) -> Row 6 (Natural Resistance)
    """
    import os
    import subprocess
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    src_hd = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/skill_trees/baskilltree.sprite")
    src_low = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/skill_trees/baskilltree.lowend.sprite")
    with open(src_hd, "rb") as f:
        raw_hd = bytearray(f.read())
    with open(src_low, "rb") as f:
        raw_low = bytearray(f.read())

    hdr_hd = raw_hd[:40]
    px_hd = bytearray(raw_hd[40:])
    W, H, fw = 2691, 1169, 897

    def copy_rect(src_f: int, src_x: int, src_y: int, dst_f: int, dst_x: int, dst_y: int, w: int, h: int) -> None:
        for dy in range(h):
            sy = src_y + dy
            ty = dst_y + dy
            if not (0 <= sy < H and 0 <= ty < H):
                continue
            s_off = (sy * W + src_f * fw + src_x) * 4
            d_off = (ty * W + dst_f * fw + dst_x) * 4
            px_hd[d_off : d_off + w * 4] = raw_hd[40 + s_off : 40 + s_off + w * 4]

    def copy_rect_hflip(
        src_f: int,
        src_x: int,
        src_y: int,
        dst_f: int,
        dst_x: int,
        dst_y: int,
        w: int,
        h: int,
    ) -> None:
        for dy in range(h):
            sy = src_y + dy
            ty = dst_y + dy
            if not (0 <= sy < H and 0 <= ty < H):
                continue
            s_off = (sy * W + src_f * fw + src_x) * 4
            d_off = (ty * W + dst_f * fw + dst_x) * 4
            for dx in range(w):
                sx_rev = w - 1 - dx
                if raw_hd[40 + s_off + sx_rev * 4 + 3] > 0:
                    px_hd[d_off + dx * 4 : d_off + (dx + 1) * 4] = raw_hd[
                        40 + s_off + sx_rev * 4 : 40 + s_off + (sx_rev + 1) * 4
                    ]

    def clear_rect(dst_f: int, dst_x: int, dst_y: int, w: int, h: int) -> None:
        zero = b"\x00" * (w * 4)
        for dy in range(h):
            ty = dst_y + dy
            if 0 <= ty < H:
                d_off = (ty * W + dst_f * fw + dst_x) * 4
                px_hd[d_off : d_off + w * 4] = zero

    # Clear Frame 1 below the top tab header (y = 120..1168)
    clear_rect(1, 0, 120, fw, H - 120)

    # 1. Row 1 (y=125): Col 1 (x=109), Col 2 (x=371), Col 3 (x=631)
    for cx in (109, 371, 631):
        copy_rect(1, 371, 304, 1, cx, 125, 217, 157)

    # 2. Row 2 (y=304): Col 2 (x=371, Critical Strike, standalone)
    copy_rect(1, 371, 304, 1, 371, 304, 217, 157)

    # 3. Left Chain on Col 1 (x=109):
    #    Row 2 (Unflinching, y=304) -> 1-row arrow -> Row 3 (Increased Speed, y=480) -> 2-row arrow -> Row 5 (Battle Fervor, y=840)
    copy_rect(1, 371, 304, 1, 109, 304, 217, 157)
    copy_rect(2, 371, 635, 1, 109, 456, 155, 25)
    # Copy vanilla Frame 1 Col 1 Row 3 -> 2-row arrow -> Row 5 block (y=480..996)
    copy_rect(1, 109, 480, 1, 109, 480, 217, 517)

    # 4. Right Chain on Col 3 (x=631):
    #    Row 3 (Iron Skin, y=480) -> 1-row arrow -> Row 4 (Venom Ward, y=661) -> 2-row arrow -> Row 6 (Natural Resistance, y=1016)
    copy_rect(1, 371, 304, 1, 631, 480, 217, 157)
    copy_rect(2, 371, 635, 1, 631, 635, 155, 26)
    # Copy vanilla Frame 1 Col 3 Row 4 -> 2-row arrow -> Row 6 block (y=661..1168)
    copy_rect(1, 631, 661, 1, 631, 661, 217, 508)

    # -------------------------------------------------------------------------
    # Reorganize Frame 2 (Barbarian Combat Skills, SkillPage=1):
    #   - Col 1 (x=109, Tactical Defensive): Row 1 (Bash) -> Row 3 (Concentrate) -> Row 5 (Shield Slam)
    #   - Col 2 (x=371, Stamina Spenders):   Row 2 (Leap) -> Row 4 (Leap Attack) -> Row 6 (Whirlwind)
    #   - Col 3 (x=631, Exhaustion/Berserk): Row 1 (Double Swing) -> Row 3 (Double Throw) -> Row 5 (Berserk) -> Row 6 (Frenzy)
    #   - Diagonal Arrow: Col 3 Row 5 (Berserk) -> Col 2 Row 6 (Whirlwind)
    # -------------------------------------------------------------------------
    clear_rect(2, 0, 120, fw, H - 120)

    # 1. Col 1 (x=109): Row 1 (y=125) -> 2-row arrow -> Row 3 (y=480) -> 2-row arrow -> Row 5 (y=840)
    #    (Copied from vanilla Frame 0 Col 3, which has the exact Row 1 -> Row 3 -> Row 5 chain!)
    copy_rect(0, 631, 125, 2, 109, 125, 217, 875)

    # 2. Col 2 (x=371): Row 2 (y=304) -> 2-row arrow -> Row 4 (y=661) -> 2-row arrow -> Row 6 (y=1016)
    #    (Copied from vanilla Frame 2 Col 1, which has the exact Row 2 -> Row 4 -> Row 6 chain!)
    copy_rect(2, 109, 304, 2, 371, 304, 217, 865)

    # 3. Col 3 (x=631): Row 1 -> 2-row arrow -> Row 3 -> 2-row arrow -> Row 5 -> 1-row arrow -> Row 6
    copy_rect(0, 631, 125, 2, 631, 125, 217, 715)
    copy_rect(0, 371, 840, 2, 631, 840, 217, 329)

    # 4. Diagonal Arrow from Col 3 Row 5 (Berserk) down-left to Col 2 Row 6 (Whirlwind)
    #    (Copied from vanilla Frame 0's Col 2 Row 5 -> Col 1 Row 6 diagonal arrow at x=262..371, y=890..1016)
    copy_rect(0, 262, 890, 2, 522, 890, 109, 126)

    # -------------------------------------------------------------------------
    # Reorganize Frame 0 (Barbarian Warcries, SkillPage=3):
    #   - Col 1 (x=109): Row 1 (Bulwark) -> Row 4 (Battle Command) -> Row 5 (Battle Orders)
    #   - Col 2 (x=371): Row 2 (Taunt) -> Row 3 (Howl) -> Row 4 (Battle Cry) -> Row 6 (War Cry)
    #   - Col 3 (x=631): Row 1 (Enduring Cry) -> Row 3 (Second Wind) -> Row 5 (Bloodlust)
    #   - Diagonal Arrows into War Cry (Col 2 Row 6):
    #       * Down-right from Battle Orders (Col 1 Row 5)
    #       * Down-left from Bloodlust (Col 3 Row 5)
    # -------------------------------------------------------------------------
    clear_rect(0, 0, 120, fw, H - 120)

    # 1. Col 1 (x=109): Row 1 (y=125) -> 3-row arrow -> Row 4 (y=661) -> 1-row arrow -> Row 5 (y=840)
    #    (Vanilla Frame 0 Col 2 at y=304..839 is Row 2 + 3-row arrow; shifting by -179px aligns Row 1 -> Row 4!)
    copy_rect(0, 371, 304, 0, 109, 125, 217, 536)
    copy_rect(1, 371, 304, 0, 109, 661, 217, 157)
    copy_rect(2, 371, 635, 0, 109, 816, 155, 26)
    copy_rect(1, 109, 840, 0, 109, 840, 217, 157)

    # 2. Col 2 (x=371): Row 2 (y=304) -> 1-row arrow -> Row 3 (y=480) -> 1-row arrow -> Row 4 (y=661) -> 2-row arrow -> Row 6 (y=1016)
    copy_rect(1, 371, 304, 0, 371, 304, 217, 157)
    copy_rect(2, 371, 635, 0, 371, 456, 155, 25)
    copy_rect(1, 371, 304, 0, 371, 480, 217, 157)
    copy_rect(2, 371, 635, 0, 371, 635, 155, 26)
    copy_rect(1, 631, 661, 0, 371, 661, 217, 508)

    # 3. Col 3 (x=631): Row 1 (y=125) -> 2-row arrow -> Row 3 (y=480) -> 2-row arrow -> Row 5 (y=840)
    copy_rect(0, 631, 125, 0, 631, 125, 217, 875)

    # 4. Diagonal Arrows into War Cry (Col 2 Row 6):
    #    - Down-right from Battle Orders (Col 1 Row 5): copied from vanilla Frame 0's Col 1 Row 1 -> Col 2 Row 2 arrow (+715px y-offset)
    copy_rect(0, 262, 170, 0, 262, 885, 118, 132)
    #    - Down-left from Bloodlust (Col 3 Row 5): copied from vanilla Frame 0's Col 2 Row 5 -> Col 1 Row 6 arrow (+260px x-offset)
    copy_rect(0, 262, 890, 0, 522, 890, 109, 126)

    dst_hd = os.path.join(MOD_ROOT, "data/hd/global/ui/spells/skill_trees/baskilltree.sprite")
    os.makedirs(os.path.dirname(dst_hd), exist_ok=True)
    with open(dst_hd, "wb") as f:
        f.write(hdr_hd + px_hd)

    # Downscale all 3 frames (2691x1169 -> 1347x584) into baskilltree.lowend.sprite
    hdr_low = raw_low[:40]
    W_low, H_low = 1347, 584
    px_low = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s",
            f"{W}x{H}",
            "-i",
            "-",
            "-vf",
            f"scale={W_low}:{H_low}:flags=lanczos",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-",
        ],
        input=bytes(px_hd),
    )

    dst_low = os.path.join(MOD_ROOT, "data/hd/global/ui/spells/skill_trees/baskilltree.lowend.sprite")
    with open(dst_low, "wb") as f:
        f.write(hdr_low + px_low)

    return f"{dst_hd}, {dst_low}"



def _build_barbarian_state_machine() -> str:
    """Add 3D HD PLRMODE_SEQUENCE (modeId=18) states for Barbarian Shield Charge (skillIndex 139 & 107).

    In vanilla barbarian_state_machine.json, there is no modeId=18 entry for skillIndex 139 (Stun/Shield Charge)
    or 107 (Charge), which caused the 3D HD renderer to remain in PMODE_RUN / PMODE_NEUTRAL / Run_Turn_180
    during Shield Charge without raising the shield or swinging the weapon on impact.
    - stepIndex 0 (Charge_Run): binds 1hs_run / 1ht_run / hth_run (loopCount=0) in modeId=18 so the Barbarian
      immediately cancels any 180-turn pivot and sprints directly at the target.
    - stepIndex 1 (Charge_Attack): binds 1hs_block / 1ht_block / hth_block (loopCount=1) so the Barbarian
      raises and slams his shield into the monster on impact without swinging his weapon.
    """
    import json
    import os
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    src_path = os.path.join(
        VANILLA_ROOT, "data/hd/character/player/barbarian/barbarian_state_machine.json"
    )
    with open(src_path, "r", encoding="utf-8") as f:
        sm = json.load(f)

    charge_run_bindings = {
        "hth": ["hth_run"],
        "bow": ["bow_run"],
        "1hs": ["1hs_run"],
        "1ht": ["1ht_run"],
        "stf": ["stf_run"],
        "2hs": ["2hs_run"],
        "2ht": ["2ht_run"],
        "xbw": ["xbw_run"],
        "1js": ["1js_run"],
        "1jt": ["1jt_run"],
        "1ss": ["1ss_run"],
        "1st": ["1st_run"],
    }
    charge_attack_bindings = {
        "hth": ["hth_block"],
        "1hs": ["1hs_block"],
        "1ht": ["1ht_block"],
        "stf": ["stf_attack1"],
        "2hs": ["2hs_attack1"],
        "2ht": ["2ht_attack1"],
        "1js": ["1js_attack1"],
        "1jt": ["1jt_attack1"],
        "1ss": ["1ss_attack1"],
        "1st": ["1st_attack1"],
    }

    new_states = [
        (66, "AnimationState046", "Charge_Run", 139, 0, 0, charge_run_bindings),
        (67, "AnimationState047", "Charge_Attack", 139, 1, 1, charge_attack_bindings),
        (68, "AnimationState048", "Charge_Run_107", 107, 0, 0, charge_run_bindings),
        (69, "AnimationState049", "Charge_Attack_107", 107, 1, 1, charge_attack_bindings),
    ]
    new_state_ids = [s[0] for s in new_states]

    for state_id, name, internal_name, skill_idx, step_idx, loop_cnt, bindings in new_states:
        sm["states"].append(
            {
                "type": "AnimationState",
                "name": name,
                "_name": internal_name,
                "audioId": "",
                "loopCount": loop_cnt,
                "stateId": state_id,
                "enableVfxAttributes": False,
                "modeId": 18,
                "skillIndex": skill_idx,
                "stepIndex": step_idx,
                "animationBindings": bindings,
                "enterEvents": [],
                "exitEvents": [],
                "exitBlendType": 0,
            }
        )

    all_state_ids = [s["stateId"] for s in sm["states"]]

    # 1. Add fast (0.05s) transitions from every existing state into the new Shield Charge states
    for tg in sm["transitions"]:
        base_name = tg["name"]
        for target_id in new_state_ids:
            tg["settings"].append(
                {
                    "type": "AnimationTransitionItem",
                    "name": f"{base_name}_transition{target_id:03d}",
                    "crossfadeSeconds": 0.05,
                    "to": target_id,
                }
            )

    # 2. Add transition groups from each new Shield Charge state to all states
    fast_return_targets = {1, 2, 3, 7, 8, 9, 64, 65, 66, 67, 68, 69}
    for state_id, name, _, _, _, _, _ in new_states:
        group_name = f"{name}_transitiongroup"
        settings = []
        for idx, to_id in enumerate(all_state_ids):
            t_name = (
                f"{group_name}_transition"
                if idx == 0
                else f"{group_name}_transition{to_id:03d}"
            )
            settings.append(
                {
                    "type": "AnimationTransitionItem",
                    "name": t_name,
                    "crossfadeSeconds": 0.05 if to_id in fast_return_targets else 0.2,
                    "to": to_id,
                }
            )
        sm["transitions"].append(
            {
                "type": "AnimationTransitionGroup",
                "name": group_name,
                "from": state_id,
                "settings": settings,
            }
        )

    dst_path = os.path.join(
        MOD_ROOT, "data/hd/character/player/barbarian/barbarian_state_machine.json"
    )
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(sm, f, indent=2)
        f.write("\n")
    return dst_path



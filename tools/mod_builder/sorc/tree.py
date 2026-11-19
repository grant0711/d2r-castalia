"""
Sorceress skill tab background (soskilltree.sprite / .lowend.sprite).

Rebuilds each tree frame (0 = Cold, 1 = Lightning, 2 = Fire) from the positions and `prereqs`
declared in `registry.SLOTS`, stamping standalone slot boxes and prerequisite arrows cleanly.
"""
import os
import subprocess

from mod_builder.common import MOD_ROOT, VANILLA_ROOT
from mod_builder.sorc.registry import BY_SLUG, FRAME, SLOTS

W, H, FW = 2691, 1169, 897
ROW_Y = [125, 304, 480, 661, 840, 1016]
COL_X = [109, 371, 631]
TILE_W, TILE_H = 217, 153
# Arrow-free standalone slot (Fire Mastery cell: Fire frame 2, col 2, row 6)
TILE_SRC = (2, 371, 1016)


def build_soskilltree_pair() -> str:
    rel = "data/hd/global/ui/spells/skill_trees/"
    src_hd = os.path.join(VANILLA_ROOT, rel, "soskilltree.sprite")
    src_low = os.path.join(VANILLA_ROOT, rel, "soskilltree.lowend.sprite")
    with open(src_hd, "rb") as f:
        raw_hd = bytearray(f.read())
    with open(src_low, "rb") as f:
        raw_low = bytearray(f.read())
    if len(raw_hd) != 40 + W * H * 4:
        raise RuntimeError("soskilltree.sprite has unexpected dimensions")

    hdr_hd, px = raw_hd[:40], bytearray(raw_hd[40:])
    src_px = bytes(raw_hd[40:])

    def off(frame: int, x: int, y: int) -> int:
        return (y * W + frame * FW + x) * 4

    def src_alpha(frame: int, x: int, y: int) -> int:
        return src_px[off(frame, x, y) + 3]

    def in_standalone_box(x: int, y: int, box_x: int, box_y: int) -> bool:
        rx, ry = x - box_x, y - box_y
        if 0 <= rx < TILE_W and 0 <= ry < TILE_H:
            return src_alpha(TILE_SRC[0], TILE_SRC[1] + rx, TILE_SRC[2] + ry) > 0
        return False

    def copy_rect(
        src_f: int, src_x: int, src_y: int,
        dst_f: int, dst_x: int, dst_y: int,
        w: int, h: int, transparent_skip: bool = True,
    ) -> None:
        for dy in range(h):
            sy, ty = src_y + dy, dst_y + dy
            if not (0 <= sy < H and 0 <= ty < H):
                continue
            s_o = off(src_f, src_x, sy)
            d_o = off(dst_f, dst_x, ty)
            if not transparent_skip:
                px[d_o:d_o + w * 4] = src_px[s_o:s_o + w * 4]
            else:
                for dx in range(w):
                    if src_px[s_o + dx * 4 + 3] > 0:
                        px[d_o + dx * 4:d_o + (dx + 1) * 4] = src_px[s_o + dx * 4:s_o + (dx + 1) * 4]

    def draw_v_arrow(dst_f: int, col: int, r_start: int, r_end: int) -> None:
        x = COL_X[col - 1] + 40
        y_start = ROW_Y[r_start - 1] + 152
        y_end = ROW_Y[r_end - 1] + 4
        gap = y_end - y_start
        span = r_end - r_start
        if span == 1:
            copy_rect(2, 149, 484 - gap, dst_f, x, y_start, 75, gap, transparent_skip=True)
        elif span == 2:
            copy_rect(2, 411, 484 - gap, dst_f, x, y_start, 75, gap, transparent_skip=True)
        elif span == 3:
            copy_rect(2, 671, 665 - gap, dst_f, x, y_start, 75, gap, transparent_skip=True)
        else:
            copy_rect(2, 671, 277, dst_f, x, y_start, 75, 20, transparent_skip=True)
            body_h = (y_end - 25) - (y_start + 20)
            for dy in range(body_h):
                sy = 297 + int(dy * 340 / max(1, body_h - 1))
                copy_rect(2, 671, sy, dst_f, x, y_start + 20 + dy, 75, 1, transparent_skip=True)
            copy_rect(2, 671, 640, dst_f, x, y_end - 25, 75, 25, transparent_skip=True)

    def draw_diag_down_right(dst_f: int, p_col: int, p_row: int, s_col: int, s_row: int) -> None:
        if p_col == 1 and s_col == 2:
            # Template: Frame 2 Fire Wall (c1,r4 at 109,661) -> Meteor (c2,r5 at 371,840)
            dy_shift = ROW_Y[s_row - 1] - 840
            for sy in range(700, 845):
                ty = sy + dy_shift
                if not (0 <= ty < H):
                    continue
                for sx in range(258, 407):
                    if src_alpha(2, sx, sy) > 0 and not in_standalone_box(sx, sy, 109, 661) and not in_standalone_box(sx, sy, 371, 840):
                        s_o = off(2, sx, sy)
                        d_o = off(dst_f, sx, ty)
                        px[d_o:d_o + 4] = src_px[s_o:s_o + 4]
        elif p_col == 2 and s_col == 3:
            # Template: Frame 2 Fire Ball (c2,r3 at 371,480) -> Enchant (c3,r4 at 631,661)
            dy_shift = ROW_Y[s_row - 1] - 661
            for sy in range(520, 665):
                ty = sy + dy_shift
                if not (0 <= ty < H):
                    continue
                for sx in range(520, 669):
                    if src_alpha(2, sx, sy) > 0 and not in_standalone_box(sx, sy, 371, 480) and not in_standalone_box(sx, sy, 631, 661):
                        s_o = off(2, sx, sy)
                        d_o = off(dst_f, sx, ty)
                        px[d_o:d_o + 4] = src_px[s_o:s_o + 4]

    def draw_diag_down_left(dst_f: int, p_col: int, p_row: int, s_col: int, s_row: int) -> None:
        # Template: Frame 0 Glacial Spike (c2,r4 at 371,661) -> Blizzard (c1,r5 at 109,840)
        dx_shift = COL_X[s_col - 1] - 109
        dy_shift = ROW_Y[s_row - 1] - 840
        for sy in range(700, 845):
            ty = sy + dy_shift
            if not (0 <= ty < H):
                continue
            for sx in range(245, 375):
                tx = sx + dx_shift
                if src_alpha(0, sx, sy) > 0 and not in_standalone_box(sx, sy, 371, 661) and not in_standalone_box(sx, sy, 109, 840):
                    s_o = off(0, sx, sy)
                    d_o = off(dst_f, tx, ty)
                    px[d_o:d_o + 4] = src_px[s_o:s_o + 4]

    for frame in FRAME.values():
        zero = b"\x00" * (FW * 4)
        for y in range(120, H):
            o = off(frame, 0, y)
            px[o:o + FW * 4] = zero

    for s in SLOTS:
        frame = FRAME[s["tree"]]
        x, y = COL_X[s["col"] - 1], ROW_Y[s["row"] - 1]
        copy_rect(TILE_SRC[0], TILE_SRC[1], TILE_SRC[2], frame, x, y, TILE_W, TILE_H, transparent_skip=True)

    for s in SLOTS:
        frame = FRAME[s["tree"]]
        for p_slug in s.get("prereqs", []):
            p = BY_SLUG[p_slug]
            if p["col"] == s["col"] and s["row"] > p["row"]:
                draw_v_arrow(frame, s["col"], p["row"], s["row"])
            elif s["col"] == p["col"] + 1 and s["row"] == p["row"] + 1:
                draw_diag_down_right(frame, p["col"], p["row"], s["col"], s["row"])
            elif s["col"] == p["col"] - 1 and s["row"] == p["row"] + 1:
                draw_diag_down_left(frame, p["col"], p["row"], s["col"], s["row"])

    dst_hd = os.path.join(MOD_ROOT, rel, "soskilltree.sprite")
    os.makedirs(os.path.dirname(dst_hd), exist_ok=True)
    with open(dst_hd, "wb") as f:
        f.write(hdr_hd + px)

    w_low, h_low = 1347, 584
    px_low = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-i", "-",
         "-vf", f"scale={w_low}:{h_low}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
        input=bytes(px))
    if len(raw_low) != 40 + len(px_low):
        raise RuntimeError("soskilltree.lowend.sprite has unexpected dimensions")
    dst_low = os.path.join(MOD_ROOT, rel, "soskilltree.lowend.sprite")
    with open(dst_low, "wb") as f:
        f.write(raw_low[:40] + px_low)
    return f"{dst_hd}, {dst_low}"

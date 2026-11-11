"""
Sorceress skill tab background (soskilltree.sprite / .lowend.sprite).

The vanilla background bakes the slot boxes AND the prerequisite arrows into 3 frames
(0 = Fire, 1 = Lightning, 2 = Cold). For the iteration phase we clear everything under the tab
header and stamp one plain, arrow-free slot box at every (row, col) used by registry.SLOTS, so the
grid always matches the 1:1 map and no stale arrows mislead. Real dependency arrows come later,
once a whole tree is built.
"""
import os
import subprocess

from mod_builder.common import MOD_ROOT, VANILLA_ROOT
from mod_builder.sorc.registry import FRAME, SLOTS

W, H, FW = 2691, 1169, 897
ROW_Y = [125, 304, 480, 661, 840, 1016]
COL_X = [109, 371, 631]
TILE_W, TILE_H = 217, 153
# Arrow-free standalone slot (Fire Mastery cell: Fire frame, col 2, row 6)
TILE_SRC = (0, 371, 1016)


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

    tile = [src_px[off(TILE_SRC[0], TILE_SRC[1], TILE_SRC[2] + dy):
                   off(TILE_SRC[0], TILE_SRC[1], TILE_SRC[2] + dy) + TILE_W * 4] for dy in range(TILE_H)]

    for frame in FRAME.values():
        zero = b"\x00" * (FW * 4)
        for y in range(120, H):
            o = off(frame, 0, y)
            px[o:o + FW * 4] = zero

    for s in SLOTS:
        frame = FRAME[s["tree"]]
        x, y = COL_X[s["col"] - 1], ROW_Y[s["row"] - 1]
        for dy in range(TILE_H):
            o = off(frame, x, y + dy)
            px[o:o + TILE_W * 4] = tile[dy]

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

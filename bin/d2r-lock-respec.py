#!/usr/bin/env python3
"""
d2r-lock-respec.py
Sets Quest 3 (w[3] |= 0x0001, "Tools of the Trade / Charsi's Imbue Already Used") and
Quest 41 (w[41] |= 0x0001, "Den of Evil Respec Already Used") across all 3 difficulties
(Normal, Nightmare, Hell) in every .d2s character save in SAVED_MOD, and recomputes the .d2s
32-bit checksum at offset 0x0C.
This permanently prevents Charsi from offering the Imbue quest/reward and Akara from offering
the "Reset Stat/Skill Points" menu option.
"""
import glob
import os
import struct
import sys


def calc_d2s_checksum(buf: bytearray) -> int:
    b = bytearray(buf)
    b[12:16] = b"\x00\x00\x00\x00"
    csum = 0
    for byte in b:
        csum = (((csum << 1) & 0xFFFFFFFF) | (csum >> 31))
        csum = (csum + byte) & 0xFFFFFFFF
    return csum


def lock_respec_in_d2s(path: str) -> bool:
    with open(path, "rb") as f:
        raw = bytearray(f.read())
    woo_idx = raw.find(b"Woo!")
    if woo_idx == -1 or len(raw) < woo_idx + 10 + 3 * 96:
        return False

    changed = False
    # Quest 3 = Act 1 Tools of the Trade (Charsi's Imbue)
    # Quest 41 = Act 1 Den of Evil Respec Reward
    for diff_idx in range(3):
        for q_idx in (3, 41):
            q_off = woo_idx + 10 + diff_idx * 96 + q_idx * 2
            val = struct.unpack_from("<H", raw, q_off)[0]
            new_val = (val | 0x0001) & ~0x0002
            if val != new_val:
                struct.pack_into("<H", raw, q_off, new_val)
                changed = True

    if changed:
        new_csum = calc_d2s_checksum(raw)
        struct.pack_into("<I", raw, 12, new_csum)
        with open(path, "wb") as f:
            f.write(raw)
    return changed


def main() -> None:
    save_dirs = sys.argv[1:] or [
        "/home/grant/games/d2r/prefixes/acct1/pfx/drive_c/users/steamuser/Saved Games/Diablo II Resurrected/mods/custom"
    ]
    for sdir in save_dirs:
        if not os.path.isdir(sdir):
            continue
        for path in sorted(glob.glob(os.path.join(sdir, "*.d2s"))):
            if lock_respec_in_d2s(path):
                print(f"[d2r-lock-respec] Locked Quests 3 (Imbue) & 41 (Respec) in {os.path.basename(path)}")


if __name__ == "__main__":
    main()

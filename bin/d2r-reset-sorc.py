#!/usr/bin/env python3
"""
d2r-reset-sorc.py - manage the SORC Sorceress test character.

Usage:
  d2r-reset-sorc.py            Reset skills: zero all 30 skill points and refund
                               (level - 1) * SkillsPerLevel unspent skill points.
                               Everything else on the character is left untouched.
  d2r-reset-sorc.py --init     Build the test character from scratch at level 60:
                               stats, unspent stat/skill points, life/mana/stamina
                               from charstats.txt, all waypoints/act flags in
                               Normal/Nightmare/Hell, and a full personal stash gold.
  d2r-reset-sorc.py --stats    Also reset attributes to base and refund stat points
                               (can be combined with the default action).
  d2r-reset-sorc.py --level N  Level for --init (default 60).

Close the game (or sit at the character select screen) before running; the game
only reads the .d2s when the character is loaded. A one-time backup is written to
SORC.d2s.bak_original on the first run.
"""
import argparse
import csv
import os
import shutil
import struct
import sys

SAVE_DIRS = [
    "/home/grant/games/d2r/prefixes/acct1/pfx/drive_c/users/steamuser/Saved Games/Diablo II Resurrected/mods/custom",
]
CHAR_NAME = "SORC"
CLASS_ROW = "Sorceress"
MOD_ROOT = "/home/grant/games/d2r/my-mod/data/global/excel"
VANILLA_ROOT = "/home/grant/games/d2r/vanilla-reference/data/global/excel"

# (stat id -> bit width) for the base stats stored in the character 'gf' section
STAT_BITS = {0: 10, 1: 10, 2: 10, 3: 10, 4: 10, 5: 8, 6: 21, 7: 21, 8: 21, 9: 21,
             10: 21, 11: 21, 12: 7, 13: 32, 14: 25, 15: 25}
GOLD_STASH_MAX = 2_500_000


def calc_d2s_checksum(buf: bytearray) -> int:
    b = bytearray(buf)
    b[12:16] = b"\x00\x00\x00\x00"
    csum = 0
    for byte in b:
        csum = (((csum << 1) & 0xFFFFFFFF) | (csum >> 31))
        csum = (csum + byte) & 0xFFFFFFFF
    return csum


def encode_gf(stats: dict[int, int]) -> bytes:
    bits: list[str] = []
    for sid in sorted(stats):
        bits.append(f"{sid:09b}"[::-1])
        bits.append(f"{stats[sid]:0{STAT_BITS[sid]}b}"[::-1])
    bits.append("1" * 9)
    s = "".join(bits)
    s += "0" * ((8 - len(s) % 8) % 8)
    return bytes(int(s[i:i + 8][::-1], 2) for i in range(0, len(s), 8))


def decode_gf(data: bytes) -> dict[int, int]:
    """Decode the stat bitstream (data starts right after the 'gf' marker)."""
    bits = "".join(f"{byte:08b}"[::-1] for byte in data)
    pos = 0
    stats: dict[int, int] = {}
    while True:
        sid = int(bits[pos:pos + 9][::-1], 2)
        pos += 9
        if sid == 0x1FF:
            break
        if sid not in STAT_BITS:
            raise RuntimeError(f"unexpected stat id {sid} in gf section")
        n = STAT_BITS[sid]
        stats[sid] = int(bits[pos:pos + n][::-1], 2)
        pos += n
    return stats


def load_charstats() -> dict:
    for root in (MOD_ROOT, VANILLA_ROOT):
        path = os.path.join(root, "charstats.txt")
        if os.path.exists(path):
            break
    with open(path, encoding="latin-1") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    head = rows[0]
    for r in rows[1:]:
        if r[0] == CLASS_ROW:
            return {k: r[head.index(k)] for k in head if k and head.index(k) < len(r)}
    raise RuntimeError(f"{CLASS_ROW} not found in {path}")


def exp_for_level(level: int) -> int:
    """Experience needed to reach `level` (experience.txt row N is the cost to reach N+1)."""
    for root in (MOD_ROOT, VANILLA_ROOT):
        path = os.path.join(root, "experience.txt")
        if os.path.exists(path):
            break
    with open(path, encoding="latin-1") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    head = rows[0]
    col = head.index(CLASS_ROW)
    for r in rows[1:]:
        if r[0] == str(level - 1):
            return int(r[col])
    return 0


def locate(raw: bytearray):
    gf = raw.find(b"gf")
    if_ = raw.find(b"if", gf)
    jm = raw.find(b"JM", if_)
    if gf == -1 or if_ == -1 or jm == -1 or jm - if_ != 32:
        raise RuntimeError(f"unexpected gf/if/JM layout ({gf}, {if_}, {jm})")
    return gf, if_, jm


def unlock_world(raw: bytearray) -> None:
    """Act transition/quest flags and every waypoint, Normal + Nightmare + Hell."""
    act_unlock_words = {
        0: 0x0001, 6: 0x101D, 7: 0x0001, 8: 0x0001, 14: 0x1C25, 15: 0x0001,
        16: 0x0001, 22: 0x1001, 23: 0x0001, 24: 0x0001, 26: 0x1001, 28: 0x0001,
        32: 0x0001, 40: 0x1001, 41: 0x8001,
    }
    woo = raw.find(b"Woo!")
    if woo != -1:
        for diff in range(3):
            base = woo + 10 + diff * 96
            for idx, val in act_unlock_words.items():
                cur = struct.unpack_from("<H", raw, base + idx * 2)[0]
                struct.pack_into("<H", raw, base + idx * 2, cur | val)
    ws = raw.find(b"WS", woo if woo != -1 else 0)
    if ws != -1:
        for diff in range(3):
            off = ws + 8 + diff * 24
            raw[off:off + 7] = b"\x02\x01\xff\xff\xff\xff\x7f"


def process(path: str, init: bool, reset_stats: bool, level: int) -> None:
    if not os.path.exists(path):
        print(f"[skip] {path} not found")
        return
    backup = path + ".bak_original"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)

    with open(path, "rb") as f:
        raw = bytearray(f.read())
    gf, if_, jm = locate(raw)
    cs = load_charstats()
    stats = decode_gf(bytes(raw[gf + 2:if_]))

    if init:
        raw[27] = level
        if raw[43] != 0:
            raw[43] = level
        unlock_world(raw)

    lvl = level if init else stats.get(12, raw[27])
    per_lvl = lambda key: int(cs[key]) / 4.0
    fixed = lambda v: int(round(v * 256))

    if init or reset_stats:
        stats[0] = int(cs["str"])
        stats[2] = int(cs["dex"])
        stats[1] = int(cs["int"])
        stats[3] = int(cs["vit"])
        stats[4] = (lvl - 1) * int(cs["StatPerLevel"])
        life = int(cs["hpadd"]) + int(cs["vit"]) + (lvl - 1) * per_lvl("LifePerLevel")
        mana = int(cs["int"]) + (lvl - 1) * per_lvl("ManaPerLevel")
        stam = int(cs["stamina"]) + (lvl - 1) * per_lvl("StaminaPerLevel")
        stats.update({6: fixed(life), 7: fixed(life), 8: fixed(mana), 9: fixed(mana),
                      10: fixed(stam), 11: fixed(stam)})
    if init:
        stats[12] = lvl
        stats[13] = exp_for_level(lvl)
        stats[15] = GOLD_STASH_MAX

    stats[5] = (lvl - 1) * int(cs["SkillsPerLevel"])

    rebuilt = raw[:gf] + b"gf" + encode_gf(stats) + b"if" + (b"\x00" * 30) + raw[jm:]
    struct.pack_into("<I", rebuilt, 8, len(rebuilt))
    struct.pack_into("<I", rebuilt, 12, calc_d2s_checksum(rebuilt))
    with open(path, "wb") as f:
        f.write(rebuilt)

    side = os.path.splitext(path)[0] + ".d2rl"
    if os.path.exists(side):
        os.remove(side)
    print(f"[d2r-reset-sorc] {path}")
    print(f"  level={stats.get(12)} skill pts={stats[5]} stat pts={stats.get(4)} "
          f"life={stats.get(7, 0) / 256:.1f} mana={stats.get(9, 0) / 256:.1f} "
          f"stamina={stats.get(11, 0) / 256:.1f} stash gold={stats.get(15)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init", action="store_true", help="build the level-N test character")
    ap.add_argument("--stats", action="store_true", help="also reset attributes and stat points")
    ap.add_argument("--level", type=int, default=60)
    args = ap.parse_args()
    for d in SAVE_DIRS:
        process(os.path.join(d, f"{CHAR_NAME}.d2s"), args.init, args.stats, args.level)


if __name__ == "__main__":
    sys.exit(main())

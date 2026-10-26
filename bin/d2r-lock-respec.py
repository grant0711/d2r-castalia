#!/usr/bin/env python3
"""
d2r-lock-respec.py
1. Sets Quest 41 (w[41] |= 0x0001, "Den of Evil Respec Already Used") across all 3 difficulties
   (Normal, Nightmare, Hell) in every .d2s character save in SAVED_MOD, permanently preventing
   Akara from offering the "Reset Stat/Skill Points" menu option.
2. Randomizes the 32-bit Map Seed (offset 0x9B in D2R v105 .d2s) and removes cached automap
   files (.ma0/.ma1/.ma2/.ma3/.map) on launch, exit, and every in-game "Save and Exit" (--watch)
   so Single Player maps regenerate every single game just like online play.
"""
import glob
import os
import secrets
import struct
import sys
import time


def calc_d2s_checksum(buf: bytearray) -> int:
    b = bytearray(buf)
    b[12:16] = b"\x00\x00\x00\x00"
    csum = 0
    for byte in b:
        csum = (((csum << 1) & 0xFFFFFFFF) | (csum >> 31))
        csum = (csum + byte) & 0xFFFFFFFF
    return csum


def _clear_automap_files(d2s_path: str) -> int:
    base, _ = os.path.splitext(d2s_path)
    removed = 0
    for ext in (".map", ".ma0", ".ma1", ".ma2", ".ma3"):
        p = base + ext
        if os.path.exists(p):
            try:
                os.remove(p)
                removed += 1
            except OSError:
                pass
    return removed


def _wipe_unclaimed_corpse(raw: bytearray) -> bool:
    """
    Detect an unclaimed player corpse in a D2R .d2s buffer and wipe it (setting wCorpseCount = 0).
    In D2R .d2s format:
      - The Mercenary section starts with b'jf' (followed by Mercenary items if a Mercenary is hired,
        then b'kf' for the Iron Golem section).
      - Immediately preceding b'jf' is the Player Corpse header:
          * When alive / no corpse: b'JM\\x00\\x00' right before b'jf'
          * When dead with an unclaimed corpse: b'JM\\x01\\x00' + <12-byte corpse info> + b'JM' + <2-byte item count> + <corpse items> right before b'jf'
    By locating b'JM\\x01\\x00' whose inner corpse item header is b'JM' at offset +16 (and precedes b'jf'),
    we replace the entire corpse block [corpse_off : jf_off] with b'JM\\x00\\x00' (0 corpses).
    """
    # Find the Mercenary section marker b'jf' directly preceding the Golem marker b'kf'
    kf_off = raw.rfind(b"kf")
    if kf_off == -1:
        return False
    jf_off = raw.rfind(b"jf", 0, kf_off)
    if jf_off == -1 or jf_off < 20:
        return False

    # Case 1: Already 0 corpses (b'JM\x00\x00' immediately before b'jf')
    if raw[jf_off - 4 : jf_off] == b"JM\x00\x00":
        return False

    # Case 2: Search backward from jf_off for the Corpse Header b'JM\x01\x00' (or b'JM\x02\x00' etc.)
    # where offset +16 also starts with the corpse item list's b'JM' tag
    if_off = raw.find(b"if", 780)
    search_start = (if_off + 34) if if_off != -1 else 900
    pos = search_start
    while pos <= jf_off - 20:
        idx = raw.find(b"JM", pos, jf_off - 16)
        if idx == -1:
            break
        corpse_cnt = struct.unpack_from("<H", raw, idx + 2)[0]
        if 1 <= corpse_cnt <= 16 and raw[idx + 16 : idx + 18] == b"JM":
            # Found the unclaimed Corpse Header at idx!
            # Replace [idx : jf_off] with b'JM\x00\x00' (0 corpses)
            raw[idx:jf_off] = b"JM\x00\x00"
            return True
        pos = idx + 1

    return False


def process_d2s(path: str, reroll_map_seed: bool = True) -> tuple[bool, bool, bool]:
    with open(path, "rb") as f:
        raw = bytearray(f.read())
    woo_idx = raw.find(b"Woo!")
    if woo_idx == -1 or len(raw) < woo_idx + 10 + 3 * 96:
        return False, False, False

    respec_changed = False
    for diff_idx in range(3):
        q41_off = woo_idx + 10 + diff_idx * 96 + 41 * 2
        val = struct.unpack_from("<H", raw, q41_off)[0]
        if (val & 0x0001) == 0:
            struct.pack_into("<H", raw, q41_off, (val | 0x0001) & ~0x0002)
            respec_changed = True

    corpse_wiped = _wipe_unclaimed_corpse(raw)

    seed_changed = False
    if reroll_map_seed and woo_idx >= 248:
        # In D2R .d2s (v98..v105, Woo! at 403), dwMapSeed is at offset 155 (0x9B = woo_idx - 248)
        seed_off = 155 if woo_idx == 403 else (woo_idx - 162)
        old_seed = struct.unpack_from("<I", raw, seed_off)[0]
        new_seed = secrets.randbelow(0x7FFFFFFE) + 1
        if new_seed == old_seed:
            new_seed = (new_seed % 0x7FFFFFFE) + 1
        struct.pack_into("<I", raw, seed_off, new_seed)
        seed_changed = True

    if respec_changed or seed_changed or corpse_wiped:
        # Always update the total file size in the .d2s header (offset 8, uint32 LE) before checksumming!
        struct.pack_into("<I", raw, 8, len(raw))
        new_csum = calc_d2s_checksum(raw)
        struct.pack_into("<I", raw, 12, new_csum)
        tmp_path = path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(raw)
        os.replace(tmp_path, path)

    if seed_changed:
        _clear_automap_files(path)

    return respec_changed, seed_changed, corpse_wiped


def run_once(save_dirs: list[str]) -> None:
    for sdir in save_dirs:
        if not os.path.isdir(sdir):
            continue
        for path in sorted(glob.glob(os.path.join(sdir, "*.d2s"))):
            respec_ch, seed_ch, corpse_ch = process_d2s(path, reroll_map_seed=True)
            if respec_ch or seed_ch or corpse_ch:
                print(
                    f"[d2r-save-guard] Updated {os.path.basename(path)} "
                    f"(respec_locked={respec_ch}, map_seed_rerolled={seed_ch}, corpse_wiped={corpse_ch})",
                    flush=True,
                )


def watch_loop(save_dirs: list[str]) -> None:
    """
    Poll SAVED_MOD for .d2s / .ma* / .map writes (which D2R writes whenever the player clicks
    'Save and Exit' to return to the Character Select screen) and immediately reroll that
    character's .d2s Map Seed and wipe .map/.ma* so the next game entered from Character Select
    generates a fresh map. Automatically exits when the parent launcher (d2r-mod/proton) exits.
    """
    parent_pid = os.getppid()
    seen_d2s: dict[str, int] = {}
    for sdir in save_dirs:
        if not os.path.isdir(sdir):
            continue
        for d2s_path in glob.glob(os.path.join(sdir, "*.d2s")):
            try:
                seen_d2s[d2s_path] = os.stat(d2s_path).st_mtime_ns
            except OSError:
                pass

    while True:
        time.sleep(0.05)
        if os.getppid() != parent_pid:
            # Parent d2r-mod / proton process exited; do one final cleanup and terminate
            run_once(save_dirs)
            break
        for sdir in save_dirs:
            if not os.path.isdir(sdir):
                continue
            for d2s_path in glob.glob(os.path.join(sdir, "*.d2s")):
                try:
                    mtime_ns = os.stat(d2s_path).st_mtime_ns
                except OSError:
                    continue
                base, _ = os.path.splitext(d2s_path)
                has_automap = any(
                    os.path.exists(base + ext) for ext in (".map", ".ma0", ".ma1", ".ma2", ".ma3")
                )
                if seen_d2s.get(d2s_path) != mtime_ns or has_automap:
                    # Wait 40ms for D2R.exe to finish flushing .d2s and .ma* on Save & Exit
                    time.sleep(0.04)
                    if os.path.isfile(d2s_path):
                        respec_ch, seed_ch, corpse_ch = process_d2s(d2s_path, reroll_map_seed=True)
                        if corpse_ch:
                            print(
                                f"[d2r-save-guard] Wiped unclaimed corpse on Save & Exit for {os.path.basename(d2s_path)}",
                                flush=True,
                            )
                    try:
                        seen_d2s[d2s_path] = os.stat(d2s_path).st_mtime_ns
                    except OSError:
                        pass


def main() -> None:
    args = sys.argv[1:]
    watch = False
    if "--watch" in args:
        watch = True
        args.remove("--watch")
    save_dirs = args or [
        "/home/grant/games/d2r/prefixes/acct1/pfx/drive_c/users/steamuser/Saved Games/Diablo II Resurrected/mods/custom"
    ]
    run_once(save_dirs)
    if watch:
        watch_loop(save_dirs)


if __name__ == "__main__":
    main()

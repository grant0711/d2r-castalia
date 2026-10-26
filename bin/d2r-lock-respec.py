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


def process_d2s(path: str, reroll_map_seed: bool = True) -> tuple[bool, bool]:
    with open(path, "rb") as f:
        raw = bytearray(f.read())
    woo_idx = raw.find(b"Woo!")
    if woo_idx == -1 or len(raw) < woo_idx + 10 + 3 * 96:
        return False, False

    respec_changed = False
    for diff_idx in range(3):
        q41_off = woo_idx + 10 + diff_idx * 96 + 41 * 2
        val = struct.unpack_from("<H", raw, q41_off)[0]
        if (val & 0x0001) == 0:
            struct.pack_into("<H", raw, q41_off, (val | 0x0001) & ~0x0002)
            respec_changed = True

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

    if respec_changed or seed_changed:
        new_csum = calc_d2s_checksum(raw)
        struct.pack_into("<I", raw, 12, new_csum)
        tmp_path = path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(raw)
        os.replace(tmp_path, path)

    if seed_changed:
        _clear_automap_files(path)

    return respec_changed, seed_changed


def run_once(save_dirs: list[str]) -> None:
    for sdir in save_dirs:
        if not os.path.isdir(sdir):
            continue
        for path in sorted(glob.glob(os.path.join(sdir, "*.d2s"))):
            respec_ch, seed_ch = process_d2s(path, reroll_map_seed=True)
            if respec_ch or seed_ch:
                print(
                    f"[d2r-save-guard] Updated {os.path.basename(path)} "
                    f"(respec_locked={respec_ch}, map_seed_rerolled={seed_ch})",
                    flush=True,
                )


def watch_loop(save_dirs: list[str]) -> None:
    """
    Poll SAVED_MOD for .ctl writes (which D2R writes ~4ms after .d2s whenever the player clicks
    'Save and Exit' to leave a game) and immediately reroll that character's .d2s Map Seed
    and wipe .map/.ma* so the next game entered from Character Select generates a fresh map.
    """
    seen_ctl: dict[str, int] = {}
    for sdir in save_dirs:
        if not os.path.isdir(sdir):
            continue
        for ctl_path in glob.glob(os.path.join(sdir, "*.ctl")):
            try:
                seen_ctl[ctl_path] = os.stat(ctl_path).st_mtime_ns
            except OSError:
                pass

    while True:
        time.sleep(0.2)
        for sdir in save_dirs:
            if not os.path.isdir(sdir):
                continue
            for ctl_path in glob.glob(os.path.join(sdir, "*.ctl")):
                try:
                    mtime_ns = os.stat(ctl_path).st_mtime_ns
                except OSError:
                    continue
                if seen_ctl.get(ctl_path) != mtime_ns:
                    seen_ctl[ctl_path] = mtime_ns
                    # Wait briefly for D2R.exe to finish flushing .d2s/.ma* on Save & Exit
                    time.sleep(0.15)
                    base, _ = os.path.splitext(ctl_path)
                    d2s_path = base + ".d2s"
                    if os.path.isfile(d2s_path):
                        process_d2s(d2s_path, reroll_map_seed=True)
                    try:
                        seen_ctl[ctl_path] = os.stat(ctl_path).st_mtime_ns
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

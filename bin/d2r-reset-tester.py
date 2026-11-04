#!/usr/bin/env python3
"""
d2r-reset-tester.py
Sets the TESTER Paladin character save to Level 99 with:
- 0 hard points in all 30 skills
- 200 unspent skill points (newskills)
- 400 unspent stat points (statpts)
- Generous Strength/Dexterity/Vitality/Energy and 2,000 HP / 1,000 Mana / 1,000 Stamina
So we can iteratively test individual Paladin skills from a clean slate.
"""
import os
import struct


def calc_d2s_checksum(buf: bytearray) -> int:
    b = bytearray(buf)
    b[12:16] = b"\x00\x00\x00\x00"
    csum = 0
    for byte in b:
        csum = (((csum << 1) & 0xFFFFFFFF) | (csum >> 31))
        csum = (csum + byte) & 0xFFFFFFFF
    return csum


def encode_gf_bitstream(stats: list[tuple[int, int, int]]) -> bytes:
    """
    Encode list of (stat_id, num_bits, value) + 9-bit 0x1ff terminator into LSB-first bytes.
    """
    bit_chunks: list[str] = []
    for sid, nbits, val in stats:
        # 9-bit stat ID, LSB first
        bit_chunks.append(f"{sid:09b}"[::-1])
        # nbits value, LSB first
        bit_chunks.append(f"{val:0{nbits}b}"[::-1])
    # 9-bit terminator 0x1ff
    bit_chunks.append("1" * 9)
    bit_str = "".join(bit_chunks)
    pad = (8 - (len(bit_str) % 8)) % 8
    bit_str += "0" * pad
    out = bytearray()
    for i in range(0, len(bit_str), 8):
        byte_bits = bit_str[i : i + 8][::-1]
        out.append(int(byte_bits, 2))
    return bytes(out)


def upgrade_tester_d2s(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, "rb") as f:
        raw = bytearray(f.read())

    gf_idx = raw.find(b"gf")
    if_idx = raw.find(b"if", gf_idx)
    jm_idx = raw.find(b"JM", if_idx)
    if gf_idx == -1 or if_idx == -1 or jm_idx == -1 or (jm_idx - if_idx) != 32:
        raise RuntimeError(f"{path}: unexpected gf/if/JM layout ({gf_idx}, {if_idx}, {jm_idx})")

    # 1. Set header level at offset 27 (and offset 43 if used) to 99, and Progression (offset 26) to 30 (Normal/NM/Hell unlocked)
    raw[26] = 30
    raw[27] = 99
    if raw[43] != 0:
        raw[43] = 99

    # 1b. Unlock all Act Transitions in Woo! and all 39 Waypoints across Normal, Nightmare, and Hell in WS
    woo_idx = raw.find(b"Woo!")
    if woo_idx != -1:
        act_unlock_words = {
            0: 0x0001,   # Act 1 Intro
            6: 0x101D,   # Sisters to the Slaughter
            7: 0x0001,   # Act 1 -> Act 2 Travel
            8: 0x0001,   # Act 2 Intro
            14: 0x1C25,  # The Seven Tombs
            15: 0x0001,  # Act 2 -> Act 3 Travel
            16: 0x0001,  # Act 3 Intro
            22: 0x1001,  # The Guardian
            23: 0x0001,  # Act 3 -> Act 4 Travel
            24: 0x0001,  # Act 4 Intro
            26: 0x1001,  # Terror's End
            28: 0x0001,  # Act 4 -> Act 5 Travel
            32: 0x0001,  # Act 5 Intro
            40: 0x1001,  # Eve of Destruction
            41: 0x8001,  # Respec locked
        }
        for diff_idx in range(3):
            base_off = woo_idx + 10 + diff_idx * 96
            for w_idx, w_val in act_unlock_words.items():
                cur_val = struct.unpack_from("<H", raw, base_off + w_idx * 2)[0]
                struct.pack_into("<H", raw, base_off + w_idx * 2, cur_val | w_val)

    ws_idx = raw.find(b"WS")
    if ws_idx != -1:
        for diff_idx in range(3):
            wp_off = ws_idx + 8 + diff_idx * 24
            raw[wp_off : wp_off + 7] = b"\x02\x01\xff\xff\xff\xff\x7f"

    # 2. Build new 'gf' stats payload for Level 99 Paladin with authentic base stats
    # (25 Str, 20 Dex, 25 Vit, 15 Enr -> 251 Life, 162 Mana, 187 Stamina) + 490 free statpts + 200 free newskills
    new_stats = [
        (0, 10, 25),                  # strength = 25 (base)
        (1, 10, 15),                  # energy = 15 (base)
        (2, 10, 20),                  # dexterity = 20 (base)
        (3, 10, 25),                  # vitality = 25 (base)
        (4, 10, 490),                 # statpts = 490 (98 levels * 5)
        (5, 8, 200),                  # newskills = 200
        (6, 21, 251 * 256),           # hitpoints = 251
        (7, 21, 251 * 256),           # maxhp = 251
        (8, 21, 162 * 256),           # mana = 162
        (9, 21, 162 * 256),           # maxmana = 162
        (10, 21, 187 * 256),          # stamina = 187
        (11, 21, 187 * 256),          # maxstamina = 187
        (12, 7, 99),                  # level = 99
        (13, 32, 3520485254),         # experience = 3,520,485,254 (Lvl 99)
        (14, 25, 990000),             # gold = 990,000
        (15, 25, 2500000),            # goldbank = 2,500,000
    ]
    gf_payload = encode_gf_bitstream(new_stats)

    # 3. Reset all 30 Paladin skills in 'if' section to 0
    if_section = b"if" + (b"\x00" * 30)

    rebuilt = raw[:gf_idx] + b"gf" + gf_payload + if_section + raw[jm_idx:]
    struct.pack_into("<I", rebuilt, 8, len(rebuilt))
    csum = calc_d2s_checksum(rebuilt)
    struct.pack_into("<I", rebuilt, 12, csum)

    with open(path, "wb") as f:
        f.write(rebuilt)

    # Remove stale .d2rl sidecar so D2RLoader refreshes it from the updated .d2s
    d2rl_path = os.path.splitext(path)[0] + ".d2rl"
    if os.path.exists(d2rl_path):
        os.remove(d2rl_path)

    print(f"[d2r-reset-tester] Updated {path} (len={len(rebuilt)}, checksum=0x{csum:08X})")


def main() -> None:
    targets = [
        "/home/grant/games/d2r/prefixes/acct1/pfx/drive_c/users/steamuser/Saved Games/Diablo II Resurrected/mods/custom/TESTER.d2s",
        "/home/grant/games/d2r/prefixes/acct1/pfx/drive_c/users/steamuser/Saved Games/Diablo II Resurrected/TESTER.d2s",
        "/home/grant/games/d2r/prefixes/mod/pfx/drive_c/users/steamuser/Saved Games/Diablo II Resurrected/mods/custom/TESTER.d2s",
        "/home/grant/games/d2r/prefixes/mod/pfx/drive_c/users/steamuser/Saved Games/Diablo II Resurrected/TESTER.d2s",
    ]
    for t in targets:
        upgrade_tester_d2s(t)


if __name__ == "__main__":
    main()

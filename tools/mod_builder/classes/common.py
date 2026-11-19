#!/usr/bin/env python3
"""
common.py
Shared skill, state, missile, animation, and tooltip helpers across all classes.
"""
from typing import Dict, List, Tuple

from mod_builder.common import (
    read_excel_tsv,
    write_excel_tsv,
)

def parse_int(val: str, default: int = 0) -> int:
    if not val or not val.strip():
        return default
    try:
        return int(float(val.strip()))
    except ValueError:
        return default


def scale_int(val: str, mult: float, min_val: int = 1) -> str:
    v = parse_int(val, 0)
    if v <= 0:
        return val
    return str(max(min_val, int(round(v * mult))))


# 4-stage non-linear progression formulas replacing linear ln12 / ln34 / ln56:
#   - Levels 1..5:  0.50x step per level (10/20)
#   - Levels 6..10: 0.75x step per level (15/20)
#   - Levels 11..15: 1.15x step per level (23/20)
#   - Levels 16+:   1.50x step per level (30/20)
# At Level 20: (10*19 + 5*15 + 8*10 + 7*5)/20 = 380/20 = 19 -> parA + 19*parB (100% identical to lnAB at Level 20!)
RAMP12 = "(par1+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*par2/20)"
RAMP34 = "(par3+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*par4/20)"
RAMP56 = "(par5+(10*(lvl-1)+5*max(0,lvl-5)+8*max(0,lvl-10)+7*max(0,lvl-15))*par6/20)"


def _curve_lev_brackets(
    row: Dict[str, str],
    base_col: str,
    lev_cols: Tuple[str, str, str, str, str],
    mult: float = 1.0,
) -> None:
    """
    Redistribute Base + Lev1..5 across a non-linear curve (gentle Levels 1-8, medium 9-16, steep 17-22+)
    while preserving the EXACT same total value at Level 20 (Base + 7*L1 + 8*L2 + 4*L3) as linear scaling!
    """
    b0 = parse_int(row.get(base_col, "0"))
    l1 = parse_int(row.get(lev_cols[0], "0"))
    l2 = parse_int(row.get(lev_cols[1], "0"))
    l3 = parse_int(row.get(lev_cols[2], "0"))
    l4 = parse_int(row.get(lev_cols[3], "0"))
    l5 = parse_int(row.get(lev_cols[4], "0"))

    if b0 <= 0 and l1 <= 0:
        return

    # Target total at Level 20 under the linear multiplier
    target_20 = int(round((b0 + 7 * l1 + 8 * l2 + 4 * l3) * mult))

    # Gentle start at Level 1 (~0.70x) and Levels 2-8 (~0.50x), near-normal at Levels 9-16 (~0.90x),
    # and catch up in Levels 17-20 so Level 20 hits target_20!
    new_b0 = max(1, int(round(b0 * mult * 0.70))) if b0 > 0 else 0
    new_l1 = max(1, int(round(l1 * mult * 0.50))) if l1 > 0 else 0
    new_l2 = max(new_l1, int(round(l2 * mult * 0.90))) if l2 > 0 else 0
    rem_for_l3 = target_20 - new_b0 - 7 * new_l1 - 8 * new_l2
    new_l3 = max(new_l2, int(round(rem_for_l3 / 4.0))) if l3 > 0 else 0
    new_l4 = max(new_l3, int(round(l4 * mult * 1.15))) if l4 > 0 else 0
    new_l5 = max(new_l4, int(round(l5 * mult * 1.20))) if l5 > 0 else 0

    if b0 > 0:
        row[base_col] = str(new_b0)
    if l1 > 0:
        row[lev_cols[0]] = str(new_l1)
    if l2 > 0:
        row[lev_cols[1]] = str(new_l2)
    if l3 > 0:
        row[lev_cols[2]] = str(new_l3)
    if l4 > 0:
        row[lev_cols[3]] = str(new_l4)
    if l5 > 0:
        row[lev_cols[4]] = str(new_l5)


# Custom passive/potion states to append to states.txt (each gets a unique ID >= 232, all < 255)
PALADIN_PASSIVE_STATES = [
    "pal_might",
    "hp_cooldown",
]

BARBARIAN_STATES = [
    ("bar_second_wind", {"castoverlay": "shoutstart", "overlay1": "innersight"}),
    ("bar_battle_trance", {"group": "11", "aura": "1", "overlay1": "battlecommand", "castoverlay": "battlecommandcast"}),
    ("bar_totem_debuff", {"group": "10", "aura": "1", "overlay1": "bloodlust_state", "castoverlay": "battleorderscast"}),
    ("bar_stamina_reflex", {"curable": "1", "curse": "1"}),
    ("bar_warcry_debuff", {"overlay1": "battlecry", "onsound": "barbarian_battlecry_state"}),
]

ASSASSIN_STATES = [
    ("ass_trap_consume", {"group": "12", "aura": "1", "active": "1", "srvactivefunc": "18", "stat": "item_kickdamage", "overlay1": "innersight"}),
    ("ass_whirl_shred", {"curable": "1"}),
    ("ass_fof_passive", {}),
    ("ass_flow_passive", {}),
    (
        "ass_shadow_bind",
        {
            "curse": "1",
            "curable": "1",
            "overlay1": "cloaked",
            "castoverlay": "psychic_hammer_hit",
            "colorpri": "85",
            "colorshift": "73",
            "light-r": "140",
            "light-g": "110",
            "light-b": "180",
        },
    ),
    ("ass_cobra_debuff", {"curable": "1", "curse": "1"}),
    ("ass_boi_passive", {}),
    ("ass_cot_passive", {}),
]


def build_states(cfg: dict) -> str:
    headers, rows = read_excel_tsv("states.txt")
    existing_states = set()
    max_id = 0
    for r in rows:
        st = r.get("state", "")
        if st:
            existing_states.add(st)
        if st == "staminapot":
            # Keep stambarblue disabled so the HUD stamina bar visibly drains/refills,
            # and use monster-only Inner Sight (white/silver sparkles) while active.
            r["stambarblue"] = ""
            r["overlay1"] = "innersight"
        elif st == "thawing":
            # Monster-only Korlic cold pierce aura overlay while active.
            r["overlay1"] = "korliccoldpierce"
        elif st == "antidote":
            # Monster-only Terror overlay (green swirl in D2R HD) while active.
            r["overlay1"] = "curseterror"
        elif st == "shout":
            # Group 11: Mutually exclusive with Enduring Cry (bar_battle_trance) so the player must choose either Bulwark Shout OR Enduring Cry!
            r["group"] = "11"
            r["armblue"] = ""
            r["stat"] = ""
        elif st == "battleorders":
            # Group 10: Mutually exclusive with Bloodlust (bar_totem_debuff) so the player must choose either Battle Orders OR Bloodlust!
            r["group"] = "10"
        elif st in (
            "progressive_damage",
            "progressive_steal",
            "progressive_other",
            "progressive_fire",
            "progressive_cold",
            "progressive_lightning",
        ):
            # Group 12: Single Active Charge-Up Rule (1 -> 2 -> 3 charges per state)
            r["group"] = "12"
        sid = parse_int(r.get("*ID", ""), -1)
        if sid > max_id:
            max_id = sid

    all_new_states = (
        [(st_name, {}) for st_name in PALADIN_PASSIVE_STATES]
        + list(BARBARIAN_STATES)
        + list(ASSASSIN_STATES)
    )
    next_id = max_id + 1
    for st_name, extra_cols in all_new_states:
        if st_name in existing_states:
            continue
        new_row = {h: "" for h in headers}
        new_row["state"] = st_name
        new_row["*ID"] = str(next_id)
        for col_k, col_v in extra_cols.items():
            if col_k in new_row:
                new_row[col_k] = col_v
        new_row["*eol"] = "0"
        rows.append(new_row)
        existing_states.add(st_name)
        next_id += 1

    from mod_builder.sorc import engine as sorc_engine

    sorc_engine.apply_table_patches("states.txt", headers, rows)
    return write_excel_tsv("states.txt", headers, rows)



def _set_dsc_line(row: Dict[str, str], prefix: str, idx: int, ltype: str, ta: str = "", tb: str = "", ca: str = "", cb: str = "") -> None:
    row[f"{prefix}line{idx}"] = ltype
    row[f"{prefix}texta{idx}"] = ta
    row[f"{prefix}textb{idx}"] = tb
    row[f"{prefix}calca{idx}"] = ca
    row[f"{prefix}calcb{idx}"] = cb


def _clear_dsc3_synergies(row: Dict[str, str], skill_title_key: str) -> None:
    _set_dsc_line(row, "dsc3", 1, "40", "Sksyn", skill_title_key, "2", "")
    for i in range(2, 8):
        _set_dsc_line(row, "dsc3", i, "", "", "", "", "")



# Appended frames 29..54 in data/hd/global/ui/spells/hireables/hrskillicon.sprite (and .lowend.sprite)
# sliced directly from each class's native skillicon.sprite sheet at IconCel.
CUSTOM_MERC_SKILL_ICONS = (
    (29, "weaken",            "necromancer", "neskillicon", 12),
    (30, "life tap",          "necromancer", "neskillicon", 32),
    (31, "lower resist",      "necromancer", "neskillicon", 50),
    (32, "dim vision",        "necromancer", "neskillicon", 10),
    (33, "slow missiles",     "amazon",      "amskillicon", 22),
    (34, "decrepify",         "necromancer", "neskillicon", 42),
    (35, "cloak of shadows",  "assassin",    "asskillicon", 24),
    (36, "amplify damage",    "necromancer", "neskillicon", 0),
    (37, "multiple shot",     "amazon",      "amskillicon", 12),
    (38, "strafe",            "amazon",      "amskillicon", 40),
    (39, "critical strike",   "amazon",      "amskillicon", 6),
    (40, "cleansing",         "paladin",     "paskillicon", 38),
    (41, "meditation",        "paladin",     "paskillicon", 48),
    (42, "salvation",         "paladin",     "paskillicon", 58),
    (43, "vigor",             "paladin",     "paskillicon", 26),
    (44, "sanctuary",         "paladin",     "paskillicon", 46),
    (45, "redemption",        "paladin",     "paskillicon", 56),
    (46, "concentration",     "paladin",     "paskillicon", 34),
    (47, "fanaticism",        "paladin",     "paskillicon", 52),
    (48, "holy fire",         "paladin",     "paskillicon", 20),
    (49, "holy shock",        "paladin",     "paskillicon", 44),
    (50, "fire mastery",      "sorceress",   "soskillicon", 50),
    (51, "cold mastery",      "sorceress",   "soskillicon", 58),
    (52, "lightning mastery", "sorceress",   "soskillicon", 54),
    (53, "battle orders",     "barbarian",   "baskillicon", 46),
    (54, "double swing",      "barbarian",   "baskillicon", 14),
)



def apply_env_and_boss_missiles(rows_by_name: Dict[str, Dict[str, str]]) -> None:
    """Scale Chest/Environmental Trap Missiles and Act Boss Poison Missiles."""
    # 3. Chest & Environmental Trap Missiles:
    #    Scale raw pre-resistance trap damage to ~100% of expected character Life across Normal,
    #    Nightmare, and Hell (so a character with ~50% resistance loses ~50% of their Life total,
    #    while wide min-max roll variance makes opening chests with low resistances genuinely dangerous).
    #    Note: For trap entities (trap-firebolt, trap-nova, trap-poisoncloud), D2Game.dll spawns the
    #    missile via MONAI_TrapMissile / Skill1 at sLvl = max(1, mLvl / 6) (sLvl=3 in Normal at mLvl=18,
    #    sLvl=8 in Nightmare at mLvl=48, sLvl=13 in Hell at mLvl=78).
    if "trapnova" in rows_by_name:
        tn = rows_by_name["trapnova"]
        tn["HitShift"] = "8"
        tn["EType"] = "ltng"
        tn["EMin"] = "60"
        tn["MinELev1"] = "60"
        tn["MinELev2"] = "110"
        tn["MinELev3"] = "160"
        tn["MinELev4"] = "180"
        tn["MinELev5"] = "200"
        tn["EMax"] = "200"
        tn["MaxELev1"] = "180"
        tn["MaxELev2"] = "330"
        tn["MaxELev3"] = "480"
        tn["MaxELev4"] = "540"
        tn["MaxELev5"] = "600"

    if "trapfirebolt" in rows_by_name:
        tfb = rows_by_name["trapfirebolt"]
        tfb["HitShift"] = "8"
        tfb["EType"] = "fire"
        # Ensure a SINGLE Fire Bolt hit deals full chest trap damage (~150-500 raw in Normal,
        # ~500-1,600 raw in Nightmare, ~950-3,000 raw in Hell) since the player only gets hit by 1 bolt
        tfb["EMin"] = "70"
        tfb["MinELev1"] = "55"
        tfb["MinELev2"] = "105"
        tfb["MinELev3"] = "155"
        tfb["MinELev4"] = "175"
        tfb["MinELev5"] = "195"
        tfb["EMax"] = "200"
        tfb["MaxELev1"] = "170"
        tfb["MaxELev2"] = "320"
        tfb["MaxELev3"] = "470"
        tfb["MaxELev4"] = "530"
        tfb["MaxELev5"] = "590"

    if "fireexplosion" in rows_by_name:
        fe = rows_by_name["fireexplosion"]
        fe["HitShift"] = "8"
        fe["EType"] = "fire"
        fe["EMin"] = "70"
        fe["MinELev1"] = "55"
        fe["MinELev2"] = "105"
        fe["MinELev3"] = "155"
        fe["MinELev4"] = "175"
        fe["MinELev5"] = "195"
        fe["EMax"] = "200"
        fe["MaxELev1"] = "170"
        fe["MaxELev2"] = "320"
        fe["MaxELev3"] = "470"
        fe["MaxELev4"] = "530"
        fe["MaxELev5"] = "590"

    if "trappoisonjavcloud" in rows_by_name:
        tpj = rows_by_name["trappoisonjavcloud"]
        tpj["EType"] = "pois"
        tpj["ELen"] = "150"  # 6 seconds (fast, urgent poison drain)
        tpj["EMin"] = "75"
        tpj["MinELev1"] = "55"
        tpj["MinELev2"] = "105"
        tpj["MinELev3"] = "155"
        tpj["MinELev4"] = "175"
        tpj["MinELev5"] = "195"
        tpj["EMax"] = "160"
        tpj["MaxELev1"] = "115"
        tpj["MaxELev2"] = "215"
        tpj["MaxELev3"] = "315"
        tpj["MaxELev4"] = "355"
        tpj["MaxELev5"] = "395"

    if "primepoisoncloud" in rows_by_name:
        ppc = rows_by_name["primepoisoncloud"]
        ppc["EType"] = "pois"
        ppc["ELen"] = "150"  # 6 seconds
        ppc["EMin"] = "75"
        ppc["MinELev1"] = "55"
        ppc["MinELev2"] = "105"
        ppc["MinELev3"] = "155"
        ppc["MinELev4"] = "175"
        ppc["MinELev5"] = "195"
        ppc["EMax"] = "160"
        ppc["MaxELev1"] = "115"
        ppc["MaxELev2"] = "215"
        ppc["MaxELev3"] = "315"
        ppc["MaxELev4"] = "355"
        ppc["MaxELev5"] = "395"

    for gas_name, gmin, gmax in (
        ("rancidgascloud", "240", "480"),
        ("chokinggascloud", "540", "1080"),
        ("stranglinggascloud", "960", "1920"),
    ):
        if gas_name in rows_by_name:
            gc = rows_by_name[gas_name]
            gc["EType"] = "pois"
            gc["ELen"] = "100"  # 4 seconds
            gc["EMin"] = gmin
            gc["EMax"] = gmax
            gc["MinELev1"] = "50"
            gc["MinELev2"] = "95"
            gc["MinELev3"] = "140"
            gc["MinELev4"] = "160"
            gc["MinELev5"] = "180"
            gc["MaxELev1"] = "100"
            gc["MaxELev2"] = "190"
            gc["MaxELev3"] = "280"
            gc["MaxELev4"] = "320"
            gc["MaxELev5"] = "360"

    # 4. Act Boss Missiles (Andariel Poison Spray & Poison Bolt — 1.45x base + progressive per-level scaling)
    for boss_ms in ("andarielspray", "andypoisonbolt"):
        if boss_ms in rows_by_name:
            bm = rows_by_name[boss_ms]
            for dcol in (
                "MinDamage", "MaxDamage", "MinLevDam1", "MinLevDam2", "MinLevDam3", "MinLevDam4", "MinLevDam5",
                "MaxLevDam1", "MaxLevDam2", "MaxLevDam3", "MaxLevDam4", "MaxLevDam5",
                "EMin", "EMax", "MinELev1", "MinELev2", "MinELev3", "MinELev4", "MinELev5",
                "MaxELev1", "MaxELev2", "MaxELev3", "MaxELev4", "MaxELev5",
            ):
                if bm.get(dcol):
                    bm[dcol] = scale_int(bm[dcol], 1.45)
            if bm.get("Vel"):
                bm["Vel"] = str(min(28, int(bm["Vel"]) + 3))
            if bm.get("MaxVel"):
                bm["MaxVel"] = str(min(28, int(bm["MaxVel"]) + 3))



def _build_animdata() -> str:
    """Update animdata.d2 and eanimdata.d2 so:
    1. AIA1HT2 has fpc=16, spd=227, and two melee hit triggers (frames 5 and 11, matching the two
       claw slices of ht2_sequence) for Dual-Claw Normal Attack & Charge-Up skills.
    2. AIA2* (AIA2HT2, AIA2HT1, AIA21HS, AIA21HT, AIA22HS, AIA22HT, AIA2STF, AIA2HTH) has fpc=16,
       spd=256, and four rapid melee hit triggers (frames 4, 7, 10, 13) for Omnislash (anim/seqtrans='A2'),
       allowing srvdofunc=1 to execute 4 rapid weapon strikes and release all 3 pending Martial Arts
       charge tiers (Charge 3 -> Charge 2 -> Charge 1) in a single sequence.
    """
    import os
    import struct
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    out_paths = []
    for fname in ("animdata.d2", "eanimdata.d2"):
        src_path = os.path.join(VANILLA_ROOT, f"data/global/{fname}")
        if not os.path.exists(src_path):
            continue
        with open(src_path, "rb") as f:
            data = f.read()

        buckets = []
        pos = 0
        for _ in range(256):
            cnt = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            recs = []
            for _ in range(cnt):
                recs.append(data[pos : pos + 160])
                pos += 160
            buckets.append(recs)

        # 1. Modify AIA1HT2 in-place to fire two melee hit events (frames 5 and 11) for Dual-Claw Normal Attack & Charge-Up skills.
        for target_name in ("AIA1HT2",):
            b_idx = sum(ord(c) for c in target_name) & 0xFF
            name_bytes = target_name.encode("ascii").ljust(8, b"\x00")
            new_recs = []
            for r in buckets[b_idx]:
                if r[:8] == name_bytes:
                    ev_bytes = bytearray(144)
                    ev_bytes[5] = 1
                    ev_bytes[11] = 1
                    r = struct.pack("<8sII", name_bytes, 16, 227) + bytes(ev_bytes)
                new_recs.append(r)
            buckets[b_idx] = new_recs

        # 2. Modify AIS1* (State_Skill1 / S1, used exclusively by Shuriken) to 8 frames at speed=292 (~6.7-7 frames per throw,
        #    ~90% as fast as Blade Fury's 6-frame throw rate) with event=1 at frame 3.
        for wcls in ("1HS", "1HT", "2HS", "2HT", "BOW", "HT1", "HT2", "HTH", "STF", "XBW"):
            target_name = f"AIS1{wcls}"
            b_idx = sum(ord(c) for c in target_name) & 0xFF
            name_bytes = target_name.encode("ascii").ljust(8, b"\x00")
            new_recs = []
            for r in buckets[b_idx]:
                if r[:8] == name_bytes:
                    ev_bytes = bytearray(144)
                    ev_bytes[3] = 1
                    r = struct.pack("<8sII", name_bytes, 8, 292) + bytes(ev_bytes)
                new_recs.append(r)
            buckets[b_idx] = new_recs

        # Sorceress experiments: per-prefix playback speed overrides (e.g. a slower stance cast animation)
        from mod_builder.sorc import engine as _sorc_engine

        for _prefix, _cfg in _sorc_engine.animdata_speeds().items():
            _pb = _prefix.encode("ascii")
            for _bi, _recs in enumerate(buckets):
                _new = []
                for _r in _recs:
                    if _r[:8].split(b"\x00")[0].startswith(_pb):
                        _r = bytearray(_r)
                        if isinstance(_cfg, dict):
                            _old_fpc = struct.unpack_from("<I", _r, 8)[0]
                            _fpc = int(_cfg.get("fpc", _old_fpc))
                            struct.pack_into("<I", _r, 8, _fpc)
                            struct.pack_into("<I", _r, 12, int(_cfg.get("spd", 256)))
                            if _cfg.get("events") == "scale" and _old_fpc:
                                _ev = bytes(_r[16:])
                                _nev = bytearray(len(_ev))
                                for _i, _b in enumerate(_ev):
                                    if _b:
                                        _j = min(len(_nev) - 1, round(_i * _fpc / _old_fpc))
                                        _nev[_j] = _b
                                _r[16:] = _nev
                        else:
                            struct.pack_into("<I", _r, 12, int(_cfg))
                        _r = bytes(_r)
                    _new.append(_r)
                buckets[_bi] = _new

        out = bytearray()
        for recs in buckets:
            out += struct.pack("<I", len(recs))
            for r in recs:
                out += r

        dst_path = os.path.join(MOD_ROOT, f"data/global/{fname}")
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        with open(dst_path, "wb") as f:
            f.write(out)
        out_paths.append(dst_path)
    return ", ".join(out_paths)


def build_pettype(cfg: dict) -> str:
    headers, rows = read_excel_tsv("pettype.txt")
    base_trap = None
    existing = set()
    for r in rows:
        pt = r.get("pet type", "")
        existing.add(pt)
        if pt == "assassintrap":
            r["partysend"] = "1"
            base_trap = dict(r)
    if base_trap:
        for new_pt in ("phystrap", "firetrap", "ltngtrap", "miasmatrap", "deathtrap", "bladesentinel"):
            if new_pt not in existing:
                nr = dict(base_trap)
                nr["pet type"] = new_pt
                nr["partysend"] = "1"
                rows.append(nr)
    return write_excel_tsv("pettype.txt", headers, rows)



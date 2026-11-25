#!/usr/bin/env python3
"""
skills.py
Step 11: Unified Class Skill, Synergy, Passive & Sprite Orchestrator.

Delegates class-specific skill, missile, string, sprite, and animation builders to:
  - mod_builder.classes.common     (shared formulas, states.txt, animdata.d2, pettype.txt, env/boss missiles)
  - mod_builder.classes.paladin    (Paladin 30-skill overhaul & Dismiss Aura submenu icon)
  - mod_builder.classes.barbarian  (Barbarian 30-skill Stamina Pendulum overhaul, icons, tree & state machine)
  - mod_builder.classes.assassin   (Assassin 30-skill Charge-Up/Sentry/Blade overhaul, icons, tree & state machine)
  - mod_builder.classes.sorceress  (Sorceress 30-skill Elemental Stance overhaul, icons, tree & state machine)
"""
from typing import Dict, Tuple

from mod_builder.classes.assassin import (
    ASSASSIN_HD_MISSILE_PAIRS,
    ASSASSIN_STRING_UPDATES,
    _build_assassin_state_machine,
    _build_asskillicon_pair,
    _build_asskilltree_pair,
    _build_chargeboltsentry_hd,
    apply_assassin_missiles,
    apply_assassin_skills_and_desc,
)
from mod_builder.classes.barbarian import (
    BARBARIAN_STRING_UPDATES,
    _apply_barbarian_skilldesc,
    _apply_barbarian_skills,
    _build_barbarian_state_machine,
    _build_baskillicon_pair,
    _build_baskilltree_pair,
    append_barbarian_helper_skills,
    apply_barbarian_missiles,
)
from mod_builder.classes.common import (
    CUSTOM_MERC_SKILL_ICONS,
    RAMP12,
    RAMP34,
    RAMP56,
    _build_animdata,
    _clear_dsc3_synergies,
    _curve_lev_brackets,
    _set_dsc_line,
    apply_env_and_boss_missiles,
    build_pettype,
    build_states,
    parse_int,
    scale_int,
)
from mod_builder.classes.paladin import (
    PALADIN_STRING_UPDATES,
    _apply_paladin_skilldesc,
    _apply_paladin_skills,
    _build_submenu_skillicon_pair,
    apply_paladin_missiles,
)
from mod_builder.classes.sorceress import (
    engine as sorc_engine,
    icons as sorc_icons,
    statemachine as sorc_sm,
    tree as sorc_tree,
)
from mod_builder.common import (
    read_excel_tsv,
    read_strings_json,
    update_mod_hd_missiles_json,
    upsert_string_entries,
    write_excel_tsv,
    write_strings_json,
)


def apply_skill_missile_updates(rows_by_name: Dict[str, Dict[str, str]], rows: list = None) -> None:
    """Apply all class and environmental skill-related missile updates (called by weapons_armor.build_missiles)."""
    apply_paladin_missiles(rows_by_name, rows)
    apply_env_and_boss_missiles(rows_by_name)
    apply_barbarian_missiles(rows_by_name)
    apply_assassin_missiles(rows_by_name, rows)


def build_skills_and_desc(cfg: dict) -> Tuple[str, str]:
    s_headers, s_rows = read_excel_tsv("skills.txt")
    by_name = {r["skill"]: r for r in s_rows if r.get("skill")}

    # Stretch the 6 skill tier unlock requirements across the 1-40 Normal difficulty curve:
    # Vanilla: 1 / 6 / 12 / 18 / 24 / 30  ->  Mod: 1 / 8 / 16 / 24 / 32 / 40
    tier_reqlevel_map = {"1": "1", "6": "8", "12": "16", "18": "24", "24": "32", "30": "40"}
    for r in s_rows:
        if r.get("charclass"):
            rl = r.get("reqlevel", "")
            if rl in tier_reqlevel_map:
                r["reqlevel"] = tier_reqlevel_map[rl]
            # Linear charge-repair cost progression by skill reqlevel (with Castalia's rep_mult=768):
            # skReq 1 (~63g/chg, ~3.2k full) -> skReq 40 (~335g/chg, ~40k full at 120 charges).
            req_i = int(r.get("reqlevel") or "1")
            if r.get("cost mult"):
                r["cost mult"] = str(max(1, 4 + int(round(req_i * 0.35))))
            if r.get("cost add"):
                r["cost add"] = str(max(1, 75 + int(round(req_i * 7.5))))
        else:
            if r.get("cost mult"):
                r["cost mult"] = scale_int(r["cost mult"], 0.06, min_val=1)
            if r.get("cost add"):
                r["cost add"] = scale_int(r["cost add"], 0.06, min_val=1)

    d_headers, d_rows = read_excel_tsv("skilldesc.txt")
    by_desc = {r["skilldesc"]: r for r in d_rows if r.get("skilldesc")}

    # 1. Paladin & Barbarian skill/skilldesc updates
    _apply_paladin_skills(by_name)
    _apply_paladin_skilldesc(by_desc)
    _apply_barbarian_skills(by_name)
    _apply_barbarian_skilldesc(by_desc)

    # 2. Environmental Trap Skills & Act Boss Signature Spells
    for t_skill in ("PoisonBallTrap", "CursedBallTrapRight", "CursedBallTrapLeft"):
        if t_skill in by_name:
            ts = by_name[t_skill]
            ts["HitShift"] = "8"
            ts["MinDam"], ts["MaxDam"] = "70", "200"
            for idx, (mn, mx) in enumerate(zip(("55", "105", "155", "175", "195"), ("170", "320", "470", "530", "590")), 1):
                ts[f"MinLevDam{idx}"], ts[f"MaxLevDam{idx}"] = mn, mx

    for boss_skill in (
        "PrimeLightning", "PrimeBolt", "MephistoMissile", "MephFrostNova",
        "DiabLight", "DiabCold", "DiabFire",
        "Baal Nova", "Baal Inferno", "Baal Cold Missiles",
    ):
        if boss_skill in by_name:
            bs = by_name[boss_skill]
            for dcol in (
                "MinDam", "MaxDam", "MinLevDam1", "MinLevDam2", "MinLevDam3", "MinLevDam4", "MinLevDam5",
                "MaxLevDam1", "MaxLevDam2", "MaxLevDam3", "MaxLevDam4", "MaxLevDam5",
                "EMin", "EMax", "EMinLev1", "EMinLev2", "EMinLev3", "EMinLev4", "EMinLev5",
                "EMaxLev1", "EMaxLev2", "EMaxLev3", "EMaxLev4", "EMaxLev5",
            ):
                if bs.get(dcol):
                    bs[dcol] = scale_int(bs[dcol], 1.40)

    for frame_idx, sdesc_key, _cls_dir, _spr_prefix, _icon_cel in CUSTOM_MERC_SKILL_ICONS:
        if sdesc_key in by_desc:
            by_desc[sdesc_key]["HireableIconCel"] = str(frame_idx)

    # 3. Barbarian Stamina helper rows & Assassin overhaul
    append_barbarian_helper_skills(s_headers, s_rows, by_name)
    apply_assassin_skills_and_desc(s_headers, s_rows, by_name, d_headers, d_rows, by_desc)

    # 4. Sorceress 1:1 map layout + active experiment variants
    sorc_engine.apply_layout(by_name, by_desc)
    sorc_engine.apply_table_patches("skills.txt", s_headers, s_rows)
    sorc_engine.apply_table_patches("skilldesc.txt", d_headers, d_rows)

    # 4b. Append hidden QA Conduction self-aura skill (always present to keep skill IDs stable;
    #     lvl 1 = Fire, lvl 2 = Lightning, lvl 3 = Cold; crafted via qa_conduction_test Cube recipes).
    if "QA Conduction" not in by_name and "Might" in by_name:
        qa_id = max(int(r.get("*Id") or 0) for r in s_rows) + 1
        qa_row = {h: "" for h in s_headers}
        qa_row["skill"] = "QA Conduction"
        qa_row["*Id"] = str(qa_id)
        qa_row["skilldesc"] = "lightning mastery"
        qa_row["srvdofunc"] = "65"
        qa_row["cltdofunc"] = ""
        qa_row["range"] = "none"
        qa_row["aura"] = "1"
        qa_row["InGame"] = "1"
        qa_row["InTown"] = "1"
        qa_row["immediate"] = "1"
        qa_row["HitShift"] = "8"
        qa_row["aurafilter"] = "73731"
        qa_row["aurastate"] = "sorc_conduction"
        qa_row["auratargetstate"] = "sorc_conduction"
        qa_row["aurarangecalc"] = "2"
        qa_row["perdelay"] = "10"
        qa_row["aurastat1"] = "target0"
        qa_row["aurastatcalc1"] = "lvl * 1000 + 50"
        qa_row["aurastat2"] = "passive_fire_mastery"
        qa_row["aurastatcalc2"] = "(lvl == 1) ? 30 : 0"
        qa_row["aurastat3"] = "passive_ltng_mastery"
        qa_row["aurastatcalc3"] = "(lvl == 2) ? 30 : 0"
        qa_row["aurastat4"] = "passive_cold_mastery"
        qa_row["aurastatcalc4"] = "(lvl == 3) ? 30 : 0"
        qa_row["aurastat5"] = "target1"
        qa_row["aurastatcalc5"] = "101"
        qa_row["aurastat6"] = "goldlost"
        qa_row["aurastatcalc6"] = "76"
        qa_row["*eol"] = "0"
        s_rows.append(qa_row)
        by_name["QA Conduction"] = qa_row

    # 5. Globally scrub all player-side elemental resistance pierce (passive_*_pierce)
    #    and Sunder Charm immunity pierce (item_pierce_*_immunity) stats/calcs across skills.txt
    if "Apocalypse" in by_name:
        by_name["Apocalypse"]["aurastat1"] = ""
        by_name["Apocalypse"]["aurastatcalc1"] = ""
    _forbidden_pierce_tokens = (
        "passive_fire_pierce", "passive_ltng_pierce", "passive_cold_pierce",
        "passive_pois_pierce", "passive_mag_pierce", "passive_dmg_pierce",
        "item_pierce_fire_immunity", "item_pierce_light_immunity", "item_pierce_ltng_immunity",
        "item_pierce_cold_immunity", "item_pierce_poison_immunity",
        "item_pierce_damage_immunity", "item_pierce_magic_immunity",
    )
    for _r in s_rows:
        for _pi in range(1, 15):
            _scol, _ccol = f"passivestat{_pi}", f"passivecalc{_pi}"
            if _scol in _r or _ccol in _r:
                _sval = _r.get(_scol, "")
                _cval = _r.get(_ccol, "")
                if any(tok in _sval or tok in _cval for tok in _forbidden_pierce_tokens):
                    if _scol in _r:
                        _r[_scol] = ""
                    if _ccol in _r:
                        _r[_ccol] = ""
        for _ai in range(1, 7):
            _scol, _ccol = f"aurastat{_ai}", f"aurastatcalc{_ai}"
            _sval = _r.get(_scol, "")
            _cval = _r.get(_ccol, "")
            if any(tok in _sval or tok in _cval for tok in _forbidden_pierce_tokens):
                _r[_scol] = ""
                _r[_ccol] = ""

    # Append hidden global Stamina Fatigue proc skill (cast via combat events on Boots/Armor/Gloves/Belts):
    # Inverse severity-vs-duration curve for Stamina % (clc1):
    #   >=65%: 0% (1 frame -> clears prior fatigue)
    #   50%:  -5% for 29.7s | 25%: -16% for 8.9s | 10%: -33% for 3.1s | 0-5%: -45% for 2.0-2.3s
    # Exempt: Barbarian Bloodlust (stat('skill_chillingarmor'.accr) > 0) and Mercenaries/Monsters (maxstamina < 256).
    if not any(r.get("skill") == "Stamina Fatigue" for r in s_rows):
        max_sid = max((int(r["*Id"]) for r in s_rows if (r.get("*Id") or "").isdigit()), default=428)
        sf = {h: "" for h in s_headers}
        sf["skill"] = "Stamina Fatigue"
        sf["*Id"] = str(max_sid + 1)
        sf["srvdofunc"] = "18"
        sf["aurastate"] = "stamina_fatigue"
        sf["auralencalc"] = "(stat('skill_chillingarmor'.accr)>0)?1:((clc1<65)?min(750,50+(clc1*clc1*5)/18):1)"
        sf["calc1"] = "(stat('stamina'.accr)*100)/max(256,stat('maxstamina'.accr))"
        sf["*calc1 desc"] = "Current Stamina %"
        sf["calc2"] = "((clc1<65)?min(45,max(0,1000/(clc1+13)-10)):0)*((stat('skill_chillingarmor'.accr)>0)?0:1)*((stat('maxstamina'.accr)<256)?0:1)"
        sf["*calc2 desc"] = "Base stamina exhaustion scalar P (0..45, Bloodlust & Merc exempt)"
        # Normalized per-stat D2R frame weights so FRW/IAS/FCR/FHR/FBR suffer uniform real-frame slowdown:
        # FRW 0.89x (-40% max, avoids moonwalk), IAS 0.75x (-33% max), FCR 0.80x (-36% max), FHR/FBR 0.40x (-18% max, base speed 50)
        sf["aurastat1"] = "item_fastermovevelocity"
        sf["aurastatcalc1"] = "0-(clc2*8)/9"
        sf["aurastat2"] = "item_fasterattackrate"
        sf["aurastatcalc2"] = "0-(clc2*3)/4"
        sf["aurastat3"] = "item_fastercastrate"
        sf["aurastatcalc3"] = "0-(clc2*4)/5"
        sf["aurastat4"] = "item_fastergethitrate"
        sf["aurastatcalc4"] = "0-(clc2*2)/5"
        sf["aurastat5"] = "item_fasterblockrate"
        sf["aurastatcalc5"] = "0-(clc2*2)/5"
        # Non-zero inert marker stat ensures srvdofunc=18 always overwrites & wipes any prior fatigue state
        # in 1 frame (0.04s) when Bloodlust is active or Stamina recovers >= 65%
        sf["aurastat6"] = "create_season"
        sf["aurastatcalc6"] = "1"
        sf["enhanceable"] = "1"
        sf["attackrank"] = "0"
        sf["range"] = "none"
        sf["anim"] = "SC"
        sf["seqtrans"] = "SC"
        sf["monanim"] = "SC"
        sf["ItemEffect"] = "1"
        sf["maxlvl"] = "20"
        sf["minmana"] = "0"
        sf["manashift"] = "8"
        sf["mana"] = "0"
        sf["lvlmana"] = "0"
        sf["InTown"] = "1"
        sf["InGame"] = "1"
        sf["HitShift"] = "8"
        sf["*eol"] = "0"
        s_rows.append(sf)

    # Append hidden Stun Fatigue (domeleeattack) & Stun Reset (attackedinmelee / kill) helper skills:
    # Consecutive uninterrupted melee swings increment shortparam1 (1 -> 2 -> 3 -> 4, 5.0s window),
    # scaling Smite stun 100% -> 75% -> 50% -> 25% -> 0% on Hit 5+. Getting attacked in melee or scoring
    # a kill immediately fires Stun Reset (1-frame wipe via create_season=1), restoring 100% stun in brawls/hallways.
    if not any(r.get("skill") == "Stun Fatigue" for r in s_rows):
        max_sid = max((int(r["*Id"]) for r in s_rows if (r.get("*Id") or "").isdigit()), default=428)
        stf = {h: "" for h in s_headers}
        stf["skill"] = "Stun Fatigue"
        stf["*Id"] = str(max_sid + 1)
        stf["srvdofunc"] = "18"
        stf["aurastate"] = "stun_fatigue"
        stf["auralencalc"] = "125"
        stf["aurastat1"] = "shortparam1"
        stf["aurastatcalc1"] = "min(4,stat('shortparam1'.accr)+1)"
        stf["enhanceable"] = "1"
        stf["attackrank"] = "0"
        stf["range"] = "none"
        stf["anim"] = "SC"
        stf["seqtrans"] = "SC"
        stf["monanim"] = "SC"
        stf["ItemEffect"] = "1"
        stf["maxlvl"] = "20"
        stf["minmana"] = "0"
        stf["manashift"] = "8"
        stf["mana"] = "0"
        stf["lvlmana"] = "0"
        stf["InTown"] = "1"
        stf["InGame"] = "1"
        stf["HitShift"] = "8"
        stf["*eol"] = "0"
        s_rows.append(stf)

    if not any(r.get("skill") == "Stun Reset" for r in s_rows):
        max_sid = max((int(r["*Id"]) for r in s_rows if (r.get("*Id") or "").isdigit()), default=428)
        strst = {h: "" for h in s_headers}
        strst["skill"] = "Stun Reset"
        strst["*Id"] = str(max_sid + 1)
        strst["srvdofunc"] = "18"
        strst["aurastate"] = "stun_fatigue"
        strst["auralencalc"] = "1"
        strst["aurastat1"] = "create_season"
        strst["aurastatcalc1"] = "1"
        strst["enhanceable"] = "1"
        strst["attackrank"] = "0"
        strst["range"] = "none"
        strst["anim"] = "SC"
        strst["seqtrans"] = "SC"
        strst["monanim"] = "SC"
        strst["ItemEffect"] = "1"
        strst["maxlvl"] = "20"
        strst["minmana"] = "0"
        strst["manashift"] = "8"
        strst["mana"] = "0"
        strst["lvlmana"] = "0"
        strst["InTown"] = "1"
        strst["InGame"] = "1"
        strst["HitShift"] = "8"
        strst["*eol"] = "0"
        s_rows.append(strst)

    p_skills = write_excel_tsv("skills.txt", s_headers, s_rows)
    p_desc = write_excel_tsv("skilldesc.txt", d_headers, d_rows)
    return p_skills, p_desc


def build_skill_strings(cfg: dict) -> str:
    entries = read_strings_json("skills.json")
    updates = (
        list(PALADIN_STRING_UPDATES)
        + list(BARBARIAN_STRING_UPDATES)
        + list(ASSASSIN_STRING_UPDATES)
        + sorc_engine.string_updates()
    )
    entries = upsert_string_entries(entries, updates)
    return write_strings_json("skills.json", entries)


def build_skills_all(cfg: dict) -> str:
    import time

    from mod_builder import skill_order
    from mod_builder.affixes import build_itemstatcost
    from mod_builder.weapons_armor import build_missiles

    run_started_at = time.time() - 1.0
    p0 = build_itemstatcost(cfg)
    p1 = build_states(cfg)
    p2, p3 = build_skills_and_desc(cfg)
    p4 = build_skill_strings(cfg)
    p5 = build_missiles(cfg)
    p6 = _build_submenu_skillicon_pair(".sprite", 132, 130)
    p7 = _build_submenu_skillicon_pair(".lowend.sprite", 67, 65)
    p8 = _build_baskillicon_pair(".sprite", 132, 130)
    p9 = _build_baskillicon_pair(".lowend.sprite", 67, 65)
    p10 = _build_baskilltree_pair()
    p11 = _build_barbarian_state_machine()
    p12 = build_pettype(cfg)
    p13 = _build_assassin_state_machine()
    p14 = _build_animdata()
    p15 = update_mod_hd_missiles_json(
        list(ASSASSIN_HD_MISSILE_PAIRS)
        + [("foh_conduction_nova", "electric_nova")]
        + sorc_engine.hd_missile_pairs()
    )
    p16 = _build_chargeboltsentry_hd()
    p17 = _build_asskilltree_pair()
    p18 = _build_asskillicon_pair()
    p19 = f"{sorc_tree.build_soskilltree_pair()}, {sorc_icons.build_soskillicon_pair()}"
    p20 = sorc_sm.build_sorceress_state_machine()
    # Must run LAST: every state machine above was generated from vanilla in the source skill-id space.
    p21 = f"{len(skill_order.remap_state_machines(run_started_at))} state machines skill-id remapped"
    return f"{p0}, {p1}, {p2}, {p3}, {p4}, {p5}, {p6}, {p7}, {p8}, {p9}, {p10}, {p11}, {p12}, {p13}, {p14}, {p15}, {p16}, {p17}, {p18}, {p19}, {p20}, {p21}"

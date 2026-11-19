#!/usr/bin/env python3
"""
assassin/sprites.py
Assassin skill icons (asskillicon), skill tree background plates (asskilltree),
all-weapon animation state machine (assassin_state_machine.json), and 3D sentry turret entity swap.
"""
def _build_asskilltree_pair() -> str:
    """
    Build data/hd/global/ui/spells/skill_trees/asskilltree.sprite and .lowend.sprite
    with reorganized Frame 0 (Martial Arts, SkillPage=3) and Frame 2 (Traps & Blades, SkillPage=1),
    leaving Frame 1 (Shadow Disciplines, SkillPage=2) untouched:
      - Frame 0 (Martial Arts, SkillPage=3):
          * Col 1 (x=109): Row 2 (Fists of Fire) -> Row 3 (Blades of Ice) -> Row 4 (Claws of Thunder) -> Row 6 (Omnislash)
          * Col 2 (x=371): Row 1 (Tiger Strike) -> Row 3 (Dragon Claw) -> Row 5 (Cobra Strike) -> diagonal to Row 6 Col 1 (Omnislash)
          * Col 3 (x=631): Row 1 (Dragon Talon) -> Row 4 (Dragon Tail) -> Row 5 (Dragon Flight)
      - Frame 2 (Traps & Blades, SkillPage=1):
          * Col 1 (x=109): Row 3 (Fire Sentry) -> Row 4 (Ice Sentry) -> Row 5 (Lightning Sentry)
          * Col 2 (x=371): Row 1 (Caltrops) -> Row 2 (Shrapnel Sentry) -> Row 6 (Soul Siphon Sentry)
          * Col 3 (x=631): Row 1 (Blade Sentinel) -> Row 3 (Blade Fury) -> Row 5 (Blade Shield) -> Row 6 (Shuriken)
                           plus diagonal from Row 5 Col 3 (Blade Shield) to Row 6 Col 2 (Soul Siphon Sentry)
    """
    import os
    import subprocess
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    src_hd = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/skill_trees/asskilltree.sprite")
    src_low = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/skill_trees/asskilltree.lowend.sprite")
    with open(src_hd, "rb") as f:
        raw_hd = bytearray(f.read())
    with open(src_low, "rb") as f:
        raw_low = bytearray(f.read())

    hdr_hd = raw_hd[:40]
    px_hd = bytearray(raw_hd[40:])
    W, H, fw = 2691, 1169, 897

    ROW_Y = {1: 125, 2: 305, 3: 481, 4: 662, 5: 841, 6: 1017}
    COL_X = {1: 109, 2: 371, 3: 631}

    def copy_rect(
        src_f: int,
        src_x: int,
        src_y: int,
        dst_f: int,
        dst_x: int,
        dst_y: int,
        w: int,
        h: int,
        transparent_skip: bool = False,
    ) -> None:
        for dy in range(h):
            sy = src_y + dy
            ty = dst_y + dy
            if not (0 <= sy < H and 0 <= ty < H):
                continue
            s_off = (sy * W + src_f * fw + src_x) * 4
            d_off = (ty * W + dst_f * fw + dst_x) * 4
            if not transparent_skip:
                px_hd[d_off : d_off + w * 4] = raw_hd[40 + s_off : 40 + s_off + w * 4]
            else:
                for dx in range(w):
                    if raw_hd[40 + s_off + dx * 4 + 3] > 0:
                        px_hd[d_off + dx * 4 : d_off + (dx + 1) * 4] = raw_hd[
                            40 + s_off + dx * 4 : 40 + s_off + (dx + 1) * 4
                        ]

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

    def draw_box(dst_f: int, col: int, row: int) -> None:
        x = COL_X[col]
        y = ROW_Y[row]
        top_h = min(135, H - y)
        copy_rect(0, 371, 125, dst_f, x, y, 217, top_h, transparent_skip=True)
        rem_h = min(21, max(0, H - (y + 135)))
        if rem_h > 0:
            copy_rect(0, 631, 976, dst_f, x, y + 135, 217, rem_h, transparent_skip=True)

    def draw_v_arrow(dst_f: int, col: int, r_start: int, r_end: int) -> None:
        x = COL_X[col] + 40
        y_start = ROW_Y[r_start] + 152
        y_end = ROW_Y[r_end] + 4
        gap = y_end - y_start
        if r_end == r_start + 1:
            copy_rect(0, 149, 845 - gap, dst_f, x, y_start, 75, gap, transparent_skip=True)
        else:
            copy_rect(0, 411, 633, dst_f, x, y_start, 75, 20, transparent_skip=True)
            body_h = (y_end - 25) - (y_start + 20)
            for dy in range(body_h):
                sy = 653 + int(dy * 342 / max(1, body_h - 1))
                copy_rect(0, 411, sy, dst_f, x, y_start + 20 + dy, 75, 1, transparent_skip=True)
            copy_rect(0, 411, 996, dst_f, x, y_end - 25, 75, 25, transparent_skip=True)

    # 1. Rebuild Frame 0 (Martial Arts, SkillPage=3)
    clear_rect(0, 0, 120, fw, H - 120)
    for col, row in [(2, 1), (3, 1), (1, 2), (1, 3), (2, 3), (1, 4), (3, 4), (2, 5), (3, 5), (1, 6)]:
        draw_box(0, col, row)

    draw_v_arrow(0, 1, 2, 3)
    draw_v_arrow(0, 1, 3, 4)
    draw_v_arrow(0, 2, 1, 3)
    draw_v_arrow(0, 2, 3, 5)
    draw_v_arrow(0, 1, 4, 6)
    # Cobra Strike (Col 2, Row 5) -> Omnislash (Col 1, Row 6): down-left diagonal (same art as Frame 2's Blade Shield -> Soul Siphon)
    copy_rect(1, 260, 180, 0, 260, 892, 109, 134, transparent_skip=True)
    draw_v_arrow(0, 3, 1, 4)
    draw_v_arrow(0, 3, 4, 5)

    # 2. Rebuild Frame 1 (Shadow Disciplines, SkillPage=2)
    clear_rect(1, 0, 120, fw, H - 120)
    for col, row in [(3, 1), (1, 2), (2, 2), (1, 3), (3, 3), (1, 4), (2, 5), (3, 5), (1, 6), (3, 6)]:
        draw_box(1, col, row)

    draw_v_arrow(1, 1, 2, 3)  # Cloak of Shadows (c1,r2) -> Shadow Bind (c1,r3)
    draw_v_arrow(1, 1, 3, 4)  # Shadow Bind (c1,r3) -> Mind Blast (c1,r4)
    draw_v_arrow(1, 1, 4, 6)  # Mind Blast (c1,r4) -> Shadow Master (c1,r6)
    draw_v_arrow(1, 2, 2, 5)  # Weapon Block (c2,r2) -> Fade (c2,r5)
    draw_v_arrow(1, 3, 1, 3)  # Lethality (c3,r1) -> Burst of Speed (c3,r3)
    draw_v_arrow(1, 3, 3, 5)  # Burst of Speed (c3,r3) -> Venom (c3,r5)
    draw_v_arrow(1, 3, 5, 6)  # Venom (c3,r5) -> Flow (c3,r6)
    # Lethality (Col 3, Row 1) -> Weapon Block (Col 2, Row 2): down-left diagonal
    copy_rect(1, 260, 180, 1, 522, 180, 109, 134, transparent_skip=True)
    # Fade (Col 2, Row 5) -> Shadow Master (Col 1, Row 6): down-left diagonal
    copy_rect(1, 260, 180, 1, 260, 892, 109, 134, transparent_skip=True)

    # 3. Rebuild Frame 2 (Traps & Blades, SkillPage=1)
    clear_rect(2, 0, 120, fw, H - 120)
    for col, row in [(2, 1), (3, 1), (2, 2), (1, 3), (3, 3), (1, 4), (1, 5), (3, 5), (2, 6), (3, 6)]:
        draw_box(2, col, row)

    draw_v_arrow(2, 1, 3, 4)
    draw_v_arrow(2, 1, 4, 5)
    draw_v_arrow(2, 2, 1, 2)
    draw_v_arrow(2, 2, 2, 6)
    draw_v_arrow(2, 3, 1, 3)
    draw_v_arrow(2, 3, 3, 5)
    draw_v_arrow(2, 3, 5, 6)
    copy_rect(1, 260, 180, 2, 522, 892, 109, 134, transparent_skip=True)
    # Shrapnel Sentry (Col 2, Row 2) -> Fire Sentry (Col 1, Row 3): down-left diagonal
    copy_rect(1, 260, 180, 2, 260, 356, 109, 134, transparent_skip=True)

    dst_hd = os.path.join(MOD_ROOT, "data/hd/global/ui/spells/skill_trees/asskilltree.sprite")
    os.makedirs(os.path.dirname(dst_hd), exist_ok=True)
    with open(dst_hd, "wb") as f:
        f.write(hdr_hd + px_hd)

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

    dst_low = os.path.join(MOD_ROOT, "data/hd/global/ui/spells/skill_trees/asskilltree.lowend.sprite")
    with open(dst_low, "wb") as f:
        f.write(hdr_low + px_low)

    return f"{dst_hd}, {dst_low}"



def _build_assassin_state_machine() -> str:
    """Update data/hd/character/player/assassin/assassin_state_machine.json so:
    1. Attack1 (modeId=7) and all 5 Charge-Up skills (plus Dragon Claw) bind 'ht2_sequence' for Dual Claws (ht2)
       while preserving standard 1H/2H melee attack bindings (hth, ht1, 1hs, 1ht, 2hs, 2ht, stf).
    2. Omnislash (skillIndex=280, Zeal/Fend multi-strike finisher) has both stepIndex=0 (FirstAttack, stateId=32)
       and stepIndex=1 (FollowUpAttack, stateId=67) states supporting all weapon types (1H, 2H, and Dual Claws
       alternating between right-hand ht2_attack1/5 and left-hand ht2_attack2/3 slashes).
    """
    import json
    import os
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    src_path = os.path.join(
        VANILLA_ROOT, "data/hd/character/player/assassin/assassin_state_machine.json"
    )
    with open(src_path, "r", encoding="utf-8") as f:
        sm = json.load(f)

    target_skills = {254, 259, 260, 265, 269, 274}
    fallback_bindings = {
        "hth": ["hth_attack1", "hth_attack2"],
        "ht1": ["ht1_attack1", "ht1_attack2"],
        "1hs": ["1hs_attack1", "1hs_attack2"],
        "1ht": ["1ht_attack1", "1ht_attack2"],
        "2hs": ["2hs_attack1", "2hs_attack2"],
        "2ht": ["2ht_attack1", "2ht_attack2"],
        "stf": ["stf_attack1", "stf_attack2"],
    }
    omnislash_first_bindings = {
        "hth": ["hth_attack1", "hth_attack2", "hth_attack3"],
        "ht1": ["ht1_attack1", "ht1_attack2", "ht1_attack3"],
        "ht2": ["ht2_sequence"],
        "1hs": ["1hs_attack1", "1hs_attack2"],
        "1ht": ["1ht_attack1", "1ht_attack2"],
        "2hs": ["2hs_attack1", "2hs_attack2"],
        "2ht": ["2ht_attack1", "2ht_attack2"],
        "stf": ["stf_attack1", "stf_attack2"],
        "bow": ["bow_attack1", "bow_attack2"],
        "xbw": ["xbw_attack1", "xbw_attack2"],
    }
    omnislash_followup_bindings = {
        "hth": ["hth_attack2", "hth_attack3", "hth_attack1"],
        "ht1": ["ht1_attack2", "ht1_attack3", "ht1_attack1"],
        "ht2": ["ht2_attack2", "ht2_attack1", "ht2_attack3", "ht2_attack5"],
        "1hs": ["1hs_attack2", "1hs_attack1"],
        "1ht": ["1ht_attack2", "1ht_attack1"],
        "2hs": ["2hs_attack2", "2hs_attack1"],
        "2ht": ["2ht_attack2", "2ht_attack1"],
        "stf": ["stf_attack2", "stf_attack1"],
        "bow": ["bow_attack2", "bow_attack1"],
        "xbw": ["xbw_attack2", "xbw_attack1"],
    }

    for st in sm["states"]:
        if st.get("modeId") == 13 and st.get("skillIndex") == -1:
            # Bind State_Skill1 (S1, used exclusively by Shuriken) to the Blade Fury throwing clip (<wclass>_bladefury)
            b = st.setdefault("animationBindings", {})
            bladefury_wclasses = {"hth", "bow", "1hs", "1ht", "stf", "2hs", "2ht", "xbw", "ht1", "ht2"}
            for wk in list(b.keys()):
                if wk in bladefury_wclasses:
                    b[wk] = [f"{wk}_bladefury"]
                else:
                    b[wk] = ["1hs_bladefury"]
        elif st.get("modeId") == 7 and st.get("skillIndex") == -1:
            b = st.setdefault("animationBindings", {})
            b["ht2"] = ["ht2_sequence"]
        elif st.get("modeId") == 18 and st.get("skillIndex") in target_skills:
            b = st.setdefault("animationBindings", {})
            b["ht2"] = ["ht2_sequence"]
            for wk, wv in fallback_bindings.items():
                if wk not in b:
                    b[wk] = wv
        elif st.get("modeId") == 18 and st.get("skillIndex") == 280 and st.get("stepIndex") == 0:
            # Whirlwind-engine Omnislash: looping spin (loopCount=0) using the Assassin's claw whirlwind clips;
            # other weapon classes loop their normal attack clips.
            st["loopCount"] = 0
            # The claw whirlwind clips are the only spin clips the Assassin skeleton has; every other weapon
            # class reuses the single-claw spin (weapon is simply held in the posed hand).
            st["animationBindings"] = {
                "hth": ["ht1_whirlwind"],
                "ht1": ["ht1_whirlwind"],
                "ht2": ["ht2_whirlwind"],
                "1hs": ["ht1_whirlwind"],
                "1ht": ["ht1_whirlwind"],
                "2hs": ["ht1_whirlwind"],
                "2ht": ["ht1_whirlwind"],
                "stf": ["ht1_whirlwind"],
            }

    followup_state_id = 67
    followup_state_name = "AnimationState048"
    sm["states"].append(
        {
            "type": "AnimationState",
            "name": followup_state_name,
            "_name": "Omnislash_FollowUpAttack",
            "audioId": "",
            "loopCount": 1,
            "stateId": followup_state_id,
            "enableVfxAttributes": False,
            "modeId": 18,
            "skillIndex": 280,
            "stepIndex": 1,
            "animationBindings": omnislash_followup_bindings,
            "enterEvents": [],
            "exitEvents": [],
            "exitBlendType": 0,
        }
    )

    all_state_ids = [s["stateId"] for s in sm["states"]]
    fast_omnislash_targets = {1, 32, followup_state_id}

    for tg in sm["transitions"]:
        base_name = tg["name"]
        from_id = tg.get("from")
        if from_id == 32:
            for s_item in tg["settings"]:
                if s_item.get("to") in fast_omnislash_targets:
                    s_item["crossfadeSeconds"] = 0.05
        tg["settings"].append(
            {
                "type": "AnimationTransitionItem",
                "name": f"{base_name}_transition{followup_state_id:03d}",
                "crossfadeSeconds": 0.05 if from_id == 32 else 0.2,
                "to": followup_state_id,
            }
        )

    group_name = f"{followup_state_name}_transitiongroup"
    followup_settings = []
    for idx, to_id in enumerate(all_state_ids):
        t_name = (
            f"{group_name}_transition"
            if idx == 0
            else f"{group_name}_transition{to_id:03d}"
        )
        followup_settings.append(
            {
                "type": "AnimationTransitionItem",
                "name": t_name,
                "crossfadeSeconds": 0.05 if to_id in fast_omnislash_targets else 0.2,
                "to": to_id,
            }
        )
    sm["transitions"].append(
        {
            "type": "AnimationTransitionGroup",
            "name": group_name,
            "from": followup_state_id,
            "settings": followup_settings,
        }
    )

    dst_path = os.path.join(
        MOD_ROOT, "data/hd/character/player/assassin/assassin_state_machine.json"
    )
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(sm, f, indent=2)
        f.write("\n")
    return dst_path


def _build_chargeboltsentry_hd() -> str:
    """Replace chargeboltsentry's and deathsentry's 3D lightning-rod turret assets in D2R HD with the
    non-lightning mechanical rotary turret (wakeofdestruction/torso.model + skeleton + animations)
    and preload their respective missile VFX.
    """
    import json
    import os
    from mod_builder.common import MOD_ROOT, VANILLA_ROOT

    wod_def_path = os.path.join(VANILLA_ROOT, "data/hd/character/enemy/wakeofdestruction.json")
    wod_sm_path = os.path.join(
        VANILLA_ROOT, "data/hd/character/enemy/wakeofdestruction/wakeofdestruction_state_machine.json"
    )
    if not (os.path.exists(wod_def_path) and os.path.exists(wod_sm_path)):
        return ""

    out_files = []
    turret_specs = [
        (
            "chargeboltsentry",
            [("BoltSentry_Seq", 306), ("SentryLightning_Seq", 313)],
            [
                "data/hd/missiles/unholy_bolt.json",
                "data/hd/missiles/bone_spirit_explode.json",
                "data/hd/missiles/sentrylightningbolt.json",
                "data/hd/missiles/lightning_strike.json",
            ],
        ),
        (
            "deathsentry",
            [("DeathSentry_Seq", 312)],
            [
                "data/hd/missiles/expansion_arctic_blast_ice.json",
                "data/hd/missiles/expansion_arctic_blast_ice_2.json",
            ],
        ),
    ]
    for unit_name, seq_specs, preload_missiles in turret_specs:
        with open(wod_def_path, "r", encoding="utf-8") as f:
            u_def = json.load(f)
        u_def["name"] = unit_name
        sm_rel = f"data/hd/character/enemy/{unit_name}/{unit_name}_state_machine.json"
        u_def["dependencies"]["json"] = [{"path": sm_rel}] + [
            {"path": mp} for mp in preload_missiles
        ]
        for ent in u_def.get("entities", []):
            if ent.get("name") == "entity_root":
                for comp in ent.get("components", []):
                    if comp.get("type") == "UnitRootComponent":
                        comp["state_machine_filename"] = sm_rel
                    elif comp.get("type") == "DefinitionPreloadComponent":
                        comp["missiles"] = [
                            {
                                "type": "UnitDefinitionListEntry",
                                "name": f"Root_UnitDefinitionList_Entry{idx + 1}",
                                "filename": mp,
                            }
                            for idx, mp in enumerate(preload_missiles)
                        ]

        with open(wod_sm_path, "r", encoding="utf-8") as f:
            u_sm = json.load(f)
        u_sm["name"] = f"{unit_name}_statemachine"
        new_states = []
        for st in u_sm.get("states", []):
            if st.get("modeId") == 14 and st.get("skillIndex") == 281:
                for seq_name, skill_idx in seq_specs:
                    st_copy = dict(st)
                    st_copy["_name"] = seq_name
                    st_copy["skillIndex"] = skill_idx
                    new_states.append(st_copy)
            else:
                new_states.append(st)
        u_sm["states"] = new_states

        dst_def = os.path.join(MOD_ROOT, f"data/hd/character/enemy/{unit_name}.json")
        dst_sm = os.path.join(MOD_ROOT, sm_rel)
        os.makedirs(os.path.dirname(dst_def), exist_ok=True)
        os.makedirs(os.path.dirname(dst_sm), exist_ok=True)
        with open(dst_def, "w", encoding="utf-8") as f:
            json.dump(u_def, f, indent=2)
            f.write("\n")
        with open(dst_sm, "w", encoding="utf-8") as f:
            json.dump(u_sm, f, indent=2)
            f.write("\n")
        out_files.extend([dst_def, dst_sm])
    return ", ".join(out_files)



def _build_asskillicon_pair() -> str:
    """
    Build data/hd/global/ui/spells/assassin/asskillicon.sprite and .lowend.sprite
    with custom normal & pressed frames for the 8 updated Assassin skill icons:
      - IconCel  0 (frames  0,  1): Shrapnel Sentry (Sentry triangle with eye + Blade Fury shuriken on top)
      - IconCel  2 (frames  2,  3): Caltrops (AI-generated spiked caltrops silhouette stamped in silver plate)
      - IconCel  6 (frames  6,  7): Soul Siphon Sentry (Sentry triangle with eye + curled Cobra hood on top)
      - IconCel 12 (frames 12, 13): Lightning Sentry (Vanilla Charged Bolt Sentry icon from Cel 6)
      - IconCel 14 (frames 14, 15): Shuriken (Single large symmetric 8-pointed shuriken + motion arcs)
      - IconCel 16 (frames 16, 17): Ice Sentry (Sentry triangle with eye + radiating frozen bolt on top)
      - IconCel 56 (frames 56, 57): Omnislash (AI-generated rapid multi-sword slash silhouette stamped in silver plate)
      - IconCel 58 (frames 58, 59): Electrocute (Simple white-plate thunderbolt stamped on Assassin dark stone tile)
    """
    import math
    import os
    import subprocess
    from mod_builder.common import MOD_ROOT, REPO_ROOT, VANILLA_ROOT

    assets_dir = os.path.join(REPO_ROOT, "assets", "skill_icons")
    ass_src = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/assassin/asskillicon.sprite")
    ass_low_src = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/assassin/asskillicon.lowend.sprite")
    bar_src = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/barbarian/baskillicon.sprite")
    sor_src = os.path.join(VANILLA_ROOT, "data/hd/global/ui/spells/sorceress/soskillicon.sprite")

    with open(ass_src, "rb") as f:
        raw_hd = f.read()
    with open(ass_low_src, "rb") as f:
        raw_low = f.read()
    with open(bar_src, "rb") as f:
        bar_raw = f.read()[40:]
    with open(sor_src, "rb") as f:
        sor_raw = f.read()[40:]

    hdr_hd = raw_hd[:40]
    ass_raw = raw_hd[40:]
    out_hd = bytearray(ass_raw)

    hdr_low = raw_low[:40]
    out_low = bytearray(raw_low[40:])

    fw, fh, nframes = 132, 130, 60
    row_bytes = nframes * fw * 4
    plate_x0, plate_x1 = 19, 112
    plate_y0, plate_y1 = 19, 111
    plate_w = plate_x1 - plate_x0
    plate_h = plate_y1 - plate_y0

    # 1. Reconstruct clean silver-plate templates (normal & pressed) from Barbarian passive cels
    donor_cels = (2, 4, 6, 16, 18, 20, 30, 38, 44)
    silver_tmpls = [bytearray(fw * fh * 4), bytearray(fw * fh * 4)]
    for pressed in (0, 1):
        st = silver_tmpls[pressed]
        g_min = 112 if pressed else 136
        g_max = 172 if pressed else 198
        for y in range(fh):
            in_plate_y = plate_y0 <= y < plate_y1
            for x in range(fw):
                in_plate = in_plate_y and (plate_x0 <= x < plate_x1)
                clean_silver = []
                samples = []
                for dc in donor_cels:
                    soff = y * row_bytes + ((dc + pressed) * fw + x) * 4
                    r, g, b, a = bar_raw[soff : soff + 4]
                    samples.append((r + g + b, r, g, b, a))
                    if in_plate and (r - b) <= 0 and g_min <= g <= g_max:
                        clean_silver.append((r + g + b, r, g, b, a))
                if clean_silver:
                    clean_silver.sort(key=lambda t: t[0])
                    _, r, g, b, a = clean_silver[len(clean_silver) // 2]
                else:
                    samples.sort(key=lambda t: t[0])
                    _, r, g, b, a = samples[-2]
                st[(y * fw + x) * 4 : (y * fw + x) * 4 + 4] = bytes((r, g, b, a))

    # 2. Reconstruct clean dark-brown stone button templates (normal & pressed) from Assassin cels
    brown_tmpls = [bytearray(fw * fh * 4), bytearray(fw * fh * 4)]
    ass_donors = tuple(range(0, 60, 2))
    for pressed in (0, 1):
        bt = brown_tmpls[pressed]
        for y in range(fh):
            for x in range(fw):
                brown = []
                samples = []
                for dc in ass_donors:
                    soff = y * row_bytes + ((dc + pressed) * fw + x) * 4
                    r, g, b, a = ass_raw[soff : soff + 4]
                    samples.append((r + g + b, r, g, b, a))
                    if (r - b) >= 14 and 20 <= g <= 68:
                        brown.append((r + g + b, r, g, b, a))
                if brown:
                    brown.sort(key=lambda t: t[0])
                    _, r, g, b, a = brown[len(brown) // 2]
                else:
                    samples.sort(key=lambda t: t[0])
                    _, r, g, b, a = samples[len(samples) // 3]
                bt[(y * fw + x) * 4 : (y * fw + x) * 4 + 4] = bytes((r, g, b, a))

    def is_fg_pixel(r: int, g: int, b: int, pressed: int) -> bool:
        g_thr = 56 if pressed else 68
        if (r - b) <= 13 and g >= g_thr:
            return True
        if (r + g + b) < 92 and (r - b) <= 18:
            return True
        return False

    def sample_bilinear(raw_buf: bytes, cel: int, sx: float, sy: float):
        ix, iy = int(math.floor(sx)), int(math.floor(sy))
        fx, fy = sx - ix, sy - iy
        rgba = [0.0, 0.0, 0.0, 0.0]
        for oy in (0, 1):
            for ox in (0, 1):
                cx = max(0, min(fw - 1, ix + ox))
                cy = max(0, min(fh - 1, iy + oy))
                wt = ((1.0 - fx) if ox == 0 else fx) * ((1.0 - fy) if oy == 0 else fy)
                soff = (cy * row_bytes) + (cel * fw + cx) * 4
                for c in range(4):
                    rgba[c] += raw_buf[soff + c] * wt
        return [int(round(v)) for v in rgba]

    def stamp_sentry_triangle(buf: bytearray, pressed: int) -> None:
        sh = 2 if pressed else 0
        for y in range(62 + sh, 108 + sh):
            half_w = (y - (60 + sh)) * 0.72 + 4.0
            for x in range(plate_x0, plate_x1):
                if abs(x - (65.5 + sh)) <= half_w:
                    soff = (y * row_bytes) + ((6 + pressed) * fw + x) * 4
                    r, g, b, _ = ass_raw[soff : soff + 4]
                    if is_fg_pixel(r, g, b, pressed):
                        doff = (y * fw + x) * 4
                        buf[doff : doff + 4] = bytes((r, g, b, 255))

    def stamp_silver_mask(base_buf: bytearray, mask, pressed: int) -> bytearray:
        out = bytearray(base_buf)
        st = silver_tmpls[pressed]
        bright = 0.84 if pressed else 1.0
        for y in range(plate_y0, plate_y1):
            for x in range(plate_x0, plate_x1):
                m = mask[y][x]
                m_tl = mask[y - 1][x - 1]
                m_br = mask[y + 1][x + 1]
                m_max = max(m, mask[y - 1][x], mask[y + 1][x], mask[y][x - 1], mask[y][x + 1])
                if m_max <= 0.05:
                    continue
                p_off = (y * fw + x) * 4
                br_r, br_g, br_b, _ = out[p_off : p_off + 4]
                if m <= 0.12:
                    t = min(1.0, (m_max - 0.05) / 0.5)
                    out[p_off : p_off + 4] = bytes(
                        (
                            int(br_r * (1.0 - 0.88 * t)),
                            int(br_g * (1.0 - 0.88 * t)),
                            int(br_b * (1.0 - 0.88 * t)),
                            255,
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
                out[p_off : p_off + 4] = bytes((r, g, b, 255))
        return out

    def stamp_ai_jpg(filename: str, pressed: int, crop_margin: float = 0.06) -> bytearray:
        img_path = os.path.join(assets_dir, filename)
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
        sh = 2 if pressed else 0
        mask = [[0.0] * fw for _ in range(fh)]
        for py in range(plate_h):
            sy = py - sh
            if not (0 <= sy < plate_h):
                continue
            for px_i in range(plate_w):
                sx = px_i - sh
                if not (0 <= sx < plate_w):
                    continue
                if min(px_i, plate_w - 1 - px_i, py, plate_h - 1 - py) < 2:
                    continue
                aoff = (sy * plate_w + sx) * 3
                lum = (art_px[aoff] + art_px[aoff + 1] + art_px[aoff + 2]) / (3.0 * 255.0)
                mask[plate_y0 + py][plate_x0 + px_i] = max(0.0, min(1.0, (lum - 0.35) / 0.35))
        return stamp_silver_mask(brown_tmpls[pressed], mask, pressed)

    fw_low, fh_low = 67, 65
    row_bytes_low = nframes * fw_low * 4

    def write_frame_pair(fidx: int, buf_hd: bytearray) -> None:
        for y in range(fh):
            row_off = y * row_bytes + fidx * fw * 4
            out_hd[row_off : row_off + fw * 4] = buf_hd[y * fw * 4 : (y + 1) * fw * 4]
        buf_low = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgba",
                "-s",
                f"{fw}x{fh}",
                "-i",
                "-",
                "-vf",
                "scale=66:65:flags=lanczos",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgba",
                "-",
            ],
            input=bytes(buf_hd),
        )
        for y in range(fh_low):
            row_off_low = y * row_bytes_low + fidx * fw_low * 4
            out_low[row_off_low : row_off_low + 66 * 4] = buf_low[y * 66 * 4 : (y + 1) * 66 * 4]

    for pressed in (0, 1):
        sh = 2 if pressed else 0

        # 1. Shrapnel Sentry (IconCel 0): Sentry triangle + Blade Fury shuriken over top
        f_shrapnel = bytearray(brown_tmpls[pressed])
        for y in range(19 + sh, 68 + sh):
            for x in range(38 + sh, 94 + sh):
                dx = (x - (65.5 + sh)) * 1.22
                dy = (y - (41.0 + sh)) * 1.22
                if dx > 3.0 and dy > 3.0:
                    dx = -dx
                sx = 46.5 + sh + dx
                sy = 48.0 + sh + dy
                if 18 <= sx <= 76 and 18 <= sy <= 78 and math.hypot(dx, dy) <= 28.5:
                    r, g, b, _ = sample_bilinear(ass_raw, 10 + pressed, sx, sy)
                    if is_fg_pixel(r, g, b, pressed):
                        doff = (y * fw + x) * 4
                        f_shrapnel[doff : doff + 4] = bytes((r, g, b, 255))
        stamp_sentry_triangle(f_shrapnel, pressed)
        write_frame_pair(0 + pressed, f_shrapnel)

        # 2. Caltrops (IconCel 2): AI-generated spiked caltrops silhouette
        write_frame_pair(2 + pressed, stamp_ai_jpg("caltrops.jpg", pressed, crop_margin=0.06))

        # 3. Lightning Sentry (IconCel 12): Copy vanilla Charged Bolt Sentry icon from Cel 6
        f_light = bytearray(fw * fh * 4)
        for y in range(fh):
            soff = (y * row_bytes) + (6 + pressed) * fw * 4
            f_light[y * fw * 4 : (y + 1) * fw * 4] = ass_raw[soff : soff + fw * 4]
        write_frame_pair(12 + pressed, f_light)

        # 4. Soul Siphon Sentry (IconCel 6): Sentry triangle + curled Cobra Strike hood over top
        f_siphon = bytearray(brown_tmpls[pressed])
        for y in range(19 + sh, 80 + sh):
            for x in range(32 + sh, 98 + sh):
                if (y - sh) > 58 and abs((x - sh) - 65.5) > ((y - sh) - 50) * 0.85 + 11.0:
                    continue
                sx = 64.0 + sh + (x - (65.5 + sh)) * 1.18
                sy = 50.0 + sh + (y - (46.0 + sh)) * 1.18
                if 20 <= sx - sh <= 104 and 19 <= sy - sh <= 83:
                    if 28 <= (sy - sh) <= 36 and ((sx - sh) < 51 or (sx - sh) > 75):
                        continue
                    if ((sx - sh) < 34 and (sy - sh) < 61) or ((sx - sh) > 94):
                        continue
                    r, g, b, _ = sample_bilinear(ass_raw, 50 + pressed, sx, sy)
                    if is_fg_pixel(r, g, b, pressed):
                        doff = (y * fw + x) * 4
                        f_siphon[doff : doff + 4] = bytes((r, g, b, 255))
        stamp_sentry_triangle(f_siphon, pressed)
        write_frame_pair(6 + pressed, f_siphon)

        # 5. Shuriken (IconCel 14): Single large symmetric 8-pointed shuriken + motion arcs
        f_shuriken = bytearray(brown_tmpls[pressed])
        for y in range(plate_y0, plate_y1):
            for x in range(plate_x0, plate_x1):
                if ((x - sh) > 76 and (y - sh) < 55) or ((x - sh) < 52 and (y - sh) > 78):
                    soff = (y * row_bytes) + ((10 + pressed) * fw + x) * 4
                    r, g, b, _ = ass_raw[soff : soff + 4]
                    if is_fg_pixel(r, g, b, pressed):
                        doff = (y * fw + x) * 4
                        f_shuriken[doff : doff + 4] = bytes((r, g, b, 255))
        for y in range(plate_y0, plate_y1):
            for x in range(plate_x0, plate_x1):
                dx = (x - (65.5 + sh)) / 1.40
                dy = (y - (65.0 + sh)) / 1.40
                if dx > 3.0 and dy > 3.0:
                    dx = -dx
                sx = 46.5 + sh + dx
                sy = 48.5 + sh + dy
                if 18 <= sx - sh <= 76 and 18 <= sy - sh <= 79 and math.hypot(dx, dy) <= 29.0:
                    r, g, b, _ = sample_bilinear(ass_raw, 10 + pressed, sx, sy)
                    if is_fg_pixel(r, g, b, pressed):
                        doff = (y * fw + x) * 4
                        f_shuriken[doff : doff + 4] = bytes((r, g, b, 255))
        write_frame_pair(14 + pressed, f_shuriken)

        # 6. Ice Sentry (IconCel 16): Sentry triangle + radiating frozen bolt on top
        f_ice = bytearray(brown_tmpls[pressed])
        for y in range(19 + sh, 68 + sh):
            for x in range(34 + sh, 98 + sh):
                sx = 65.5 + sh + (x - (65.5 + sh)) * 1.55
                sy = 65.0 + sh + (y - (41.0 + sh)) * 1.55
                if 20 <= sx - sh <= 110 and 20 <= sy - sh <= 110 and math.hypot(sx - (65.5 + sh), sy - (65.0 + sh)) <= 44.0:
                    r, g, b, _ = sample_bilinear(ass_raw, 52 + pressed, sx, sy)
                    if is_fg_pixel(r, g, b, pressed):
                        doff = (y * fw + x) * 4
                        f_ice[doff : doff + 4] = bytes((r, g, b, 255))
        stamp_sentry_triangle(f_ice, pressed)
        write_frame_pair(16 + pressed, f_ice)

        # 7. Omnislash (IconCel 56): AI-generated multi-sword flurry silhouette
        write_frame_pair(56 + pressed, stamp_ai_jpg("omnislash.jpg", pressed, crop_margin=0.06))

        # 8. Electrocute (IconCel 58): Simple white-plate thunderbolt on Assassin dark brown tile
        f_electro = bytearray(brown_tmpls[pressed])
        for y in range(plate_y0, plate_y1):
            for x in range(plate_x0, plate_x1):
                soff = (y * row_bytes) + ((26 + pressed) * fw + x) * 4
                r, g, b, _ = sor_raw[soff : soff + 4]
                if is_fg_pixel(r, g, b, pressed):
                    doff = (y * fw + x) * 4
                    f_electro[doff : doff + 4] = bytes((r, g, b, 255))
        write_frame_pair(58 + pressed, f_electro)

        # 9. Lethality (IconCel 20): Crossed broadsword and Assassin claw plate
        write_frame_pair(20 + pressed, stamp_ai_jpg("lethality.jpg", pressed, crop_margin=0.06))

        # 10. Flow (IconCel 22): Hooded Assassin silhouette with swirling speed/flow arcs
        write_frame_pair(22 + pressed, stamp_ai_jpg("flow.jpg", pressed, crop_margin=0.06))

        # 11. Shadow Bind (IconCel 38): Monster bound by swirling shadow tendrils around its limbs/feet
        write_frame_pair(38 + pressed, stamp_ai_jpg("shadow_bind.jpg", pressed, crop_margin=0.06))

    dst_hd = os.path.join(MOD_ROOT, "data/hd/global/ui/spells/assassin/asskillicon.sprite")
    dst_low = os.path.join(MOD_ROOT, "data/hd/global/ui/spells/assassin/asskillicon.lowend.sprite")
    os.makedirs(os.path.dirname(dst_hd), exist_ok=True)
    with open(dst_hd, "wb") as f:
        f.write(hdr_hd + out_hd)
    with open(dst_low, "wb") as f:
        f.write(hdr_low + out_low)
    return f"{dst_hd}, {dst_low}"



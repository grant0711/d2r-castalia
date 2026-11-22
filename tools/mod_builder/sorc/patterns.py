"""
patterns.py
Indexed D2R Server/Client Function Reference, Missile Function Reference, Stance Marker
Formula Builders, and 7 Reusable Skill Archetype Blueprints for the Sorceress Overhaul
(and future class skill overhauls).

Use via CLI:
  d2r-sorc funcs [filter]          # query skills.txt & missiles.txt server/client functions
  d2r-sorc patterns [slug|role]    # view proven pattern & parallel template for a skill or role
"""
from typing import Dict, List

# ---------------------------------------------------------------------------
# 1. Canonical Stance Marker Stats & Cross-Stance Fizzle Formula Helpers
# ---------------------------------------------------------------------------
STANCE_MARKERS: Dict[str, Dict[str, str]] = {
    "fire": {
        "stance_slug": "conflagration",
        "state": "sorc_stance_fire",
        "stat": "skill_handofathena",
        "expr": "((stat('skill_handofathena'.accr) + ((stat('modifierlist_level'.accr) == 1) ? 1 : 0)) > 0)",
        "opposing_expr": "((stat('skill_frenzy'.accr) + stat('skill_decrepify'.accr)) > 0)",
    },
    "cold": {
        "stance_slug": "cryostasis",
        "state": "sorc_stance_cold",
        "stat": "skill_frenzy",
        "expr": "((stat('skill_frenzy'.accr) + ((stat('modifierlist_level'.accr) == 3) ? 1 : 0)) > 0)",
        "opposing_expr": "((stat('skill_handofathena'.accr) + stat('skill_decrepify'.accr)) > 0)",
    },
    "lightning": {
        "stance_slug": "overcharge",
        "state": "sorc_stance_light",
        "stat": "skill_decrepify",
        "expr": "((stat('skill_decrepify'.accr) + ((stat('modifierlist_level'.accr) == 2) ? 1 : 0)) > 0)",
        "opposing_expr": "((stat('skill_handofathena'.accr) + stat('skill_frenzy'.accr)) > 0)",
    },
}


def stance_bonus_expr(tree: str, base_expr: str, bonus_expr: str) -> str:
    """Return `<base_expr> + (<stance_on> ? <bonus_expr> : 0)`."""
    m = STANCE_MARKERS[tree]["expr"]
    return f"({base_expr} + ({m} ? ({bonus_expr}) : 0))"


def cross_stance_fizzle_expr(tree: str, normal_expr: str, fizzle_val: str = "1") -> str:
    """
    Wrap an offensive skill's Range/Radius/Duration expression so that casting it while an
    OPPOSING elemental stance is active immediately fizzles (`fizzle_val`, typically '0' or '1').
    """
    opp = STANCE_MARKERS[tree]["opposing_expr"]
    return f"({opp} ? {fizzle_val} : ({normal_expr}))"


# ---------------------------------------------------------------------------
# 2. Proven skills.txt Server / Client Function Catalog
# ---------------------------------------------------------------------------
SKILL_FUNCS: List[Dict[str, str]] = [
    {
        "id": "1 / 1",
        "srvstfunc": "",
        "srvdofunc": "1",
        "cltstfunc": "",
        "cltdofunc": "1",
        "name": "Direct Linear Projectile Launcher",
        "missile_cols": "srvmissile, cltmissile (NOT srvmissilea!)",
        "calcs": "calc1 = optional explosion radius on impact (if missile uses pSrvHitFunc=1); calc2 = optional submissile spawn rate",
        "proven_in": "cinder_lance (Fire Bolt), brimstone_lance (Inferno), frost_dart (Ice Bolt), icicle_spear (Glacial Spike), static_lance (Lightning)",
        "pitfalls": (
            "1) Uses srvmissile/cltmissile, NOT srvmissilea. "
            "2) Do NOT put pSrvHitFunc=38 on firebolt (breaks collision completely). "
            "3) For conditional stance AoE impact visuals, set CltHitSubMissile1 to an 'erruption center' clone (pCltDoFunc=48) gated by cltcalc1."
        ),
    },
    {
        "id": "154 / 99",
        "srvstfunc": "",
        "srvdofunc": "154",
        "cltstfunc": "",
        "cltdofunc": "99",
        "name": "Dynamic-Count 360° Radial Ring Spawner (Ring of Fire)",
        "missile_cols": "srvmissilea, srvmissileb, srvmissilec, cltmissilea (all set to ring missile)",
        "calcs": "calc1 = impact explosion radius; calc2 = radial bolt count (e.g. 5..16)",
        "proven_in": "pyroclasm (Fire Ball)",
        "pitfalls": (
            "1) Ignores calc3 / cltcalc1 Missile Velocity Adder (vanilla comment is false). "
            "2) Scale ring radius via Vel + VelLev + MaxVel + Range on the missile row itself, and clear Accel='' so bolts do not brake early. "
            "3) Cap radial bolt count (calc2) at ~16 directions."
        ),
    },
    {
        "id": "22 / 25",
        "srvstfunc": "",
        "srvdofunc": "22",
        "cltstfunc": "",
        "cltdofunc": "25",
        "name": "Dense 64-Bolt Expanding Nova Ring (Frost Nova / Nova)",
        "missile_cols": "srvmissilea, cltmissilea",
        "calcs": "calc3 = Server Missile Velocity Adder; cltcalc1 = Client Missile Velocity Adder",
        "proven_in": "hoarfrost_burst (Frost Nova), pulse_ring (Nova)",
        "pitfalls": (
            "Unlike 154/99, srvdofunc=22 / cltdofunc=25 DOES honor calc3 and cltcalc1 as a live Velocity Adder! "
            "Keep calc3 == cltcalc1 so server hit ring and client visual ring travel at identical speeds."
        ),
    },
    {
        "id": "17 / 23",
        "srvstfunc": "",
        "srvdofunc": "17",
        "cltstfunc": "",
        "cltdofunc": "23",
        "name": "Multi-Bolt Fan / Cone Emitter (Charged Bolt)",
        "missile_cols": "srvmissilea, cltmissilea",
        "calcs": "calc1 = bolt count",
        "proven_in": "Vanilla Charged Bolt / Electrocute Charge 1",
        "pitfalls": "Fires a forward fan of calc1 missiles using srvmissilea/cltmissilea.",
    },
    {
        "id": "14+28 / 17+28",
        "srvstfunc": "14",
        "srvdofunc": "28",
        "cltstfunc": "17",
        "cltdofunc": "28",
        "name": "Cursor Ground Vortex / Field + Target Debuff State",
        "missile_cols": "srvmissilea = maker/delay missile (pSrvHitFunc=11 -> HitSubMissile1 = center); cltmissilea = center missile (pCltDoFunc=48)",
        "calcs": (
            "aurafilter=3, auratargetstate=<debuff_state>, aurarangecalc=<radius>, auralencalc=<frames>, aurastat1..6=<debuffs>; "
            "calc1 / cltcalc1 = ground patch & pull/explosion radius; calc2 / cltcalc2 = ground submissile spawn interval (frames)"
        ),
        "proven_in": "backdraft (Fire Wall), permafrost (Ice Blast), tesla_field (Static Field)",
        "pitfalls": (
            "1) Clear HitClass=221 on Warlock-cloned missiles (use HitClass=32 for Fire, 48 for Cold, 64 for Lightning) to avoid purple shadow hit overlays. "
            "2) Ensure CltSubMissile1/2 on the pCltDoFunc=48 center missile has CollideType=0 and pSrvDmgFunc='' so client ground visuals don't desync."
        ),
    },
    {
        "id": "-+28 / -+28",
        "srvstfunc": "",
        "srvdofunc": "28",
        "cltstfunc": "",
        "cltdofunc": "28",
        "name": "Cursor Delayed Impact / Bombardment Zone (Skyfall / Blizzard)",
        "missile_cols": "srvmissilea..c = center controller, cltmissilea = center controller",
        "calcs": "aurarangecalc = impact radius; calc1 / cltcalc1 = impact & crater radius; calc2 / cltcalc2 = crater/shard spawn rate",
        "proven_in": "skyfall (Meteor), whiteout (Blizzard), stormcall (Thunder Storm), heavens_wrath (Charged Bolt)",
        "pitfalls": (
            "1) Server HitSubMissile1 from pSrvHitFunc=14 never spawns client visuals automatically; attach a client crater controller "
            "(cloned from 'erruption center', pCltDoFunc=48) to CltHitSubMissile2 on the center missile so the lingering crater renders cleanly. "
            "2) Do not use skill('Meteor'.len) inside missile Range (evaluates to 0 on client); write an explicit formula like '75 + lvl*5'."
        ),
    },
    {
        "id": "166 / 104",
        "srvstfunc": "",
        "srvdofunc": "166",
        "cltstfunc": "",
        "cltdofunc": "104",
        "name": "Directional Blink with Path Wake & Landing AoE (Blade Warp Engine)",
        "missile_cols": "srvmissilea = warp missile, cltmissilea = warp missile (cloned from bladewarp)",
        "calcs": (
            "lob=1, warp=1, range=rng, restrict=2, State1=<stance_state>, localdelay=75; "
            "calc1 / cltcalc1 = landing AoE radius; calc2 / cltcalc2 = landing nova spawn rate (1); "
            "calc5 = 1 (required attack count for srvdofunc=166!); calc6 = 100"
        ),
        "proven_in": "glacier_step (Chilling Armor), phase_step (Teleport)",
        "pitfalls": (
            "1) calc5 MUST be >= 1 (e.g. '1') or srvdofunc=166 will not execute the warp! "
            "2) Clear MissileWeaponVFX='' on the bladewarp clone so a floating dagger doesn't render on the Sorceress. "
            "3) Warp missile uses pSrvDoFunc=2, pCltDoFunc=3, pSrvHitFunc=42, Vel=96, Range=15, CollideType=6. "
            "4) (Proven in-game, phase_step p6/p7) The warp's ExplosionMissile is CLIENT-ONLY: it never spawns on the server, "
            "so nothing chained from it deals damage or applies states. Landing damage comes from srvdofunc=166 ITSELF "
            "(skill EType/EMin/EMax over aurarangecalc). For server-side effects use the warp's trail-dropper "
            "(pSrvDoFunc=2 -> SubMissile1, dropped every frame along the path; e.g. a sigil pulse pSrvDoFunc=14 with "
            "Param1=1 + missile Radius applying the skill's auratargetstate). Blink distance is NOT limited by the warp Range."
        ),
    },
    {
        "id": "23 / -",
        "srvstfunc": "",
        "srvdofunc": "23",
        "cltstfunc": "",
        "cltdofunc": "",
        "name": "Self-State Sprint with Ground Trail (Blaze Engine)",
        "missile_cols": "srvmissilea = blaze",
        "calcs": "aurastate='blaze', auralencalc=<frames>, passivecalc1=<FRW%>, restrict=2, State1=<stance_state>, localdelay=250",
        "proven_in": "flashfire (Blaze)",
        "pitfalls": "srvdofunc=23 applies the hardcoded blaze state/trail; use passivecalc1 on the skill row to scale velocitypercent dynamically with stance marker.",
    },
    {
        "id": "18 / -",
        "srvstfunc": "",
        "srvdofunc": "18",
        "cltstfunc": "",
        "cltdofunc": "",
        "name": "Timed Self-Stance / Armor Buff with Melee Retaliation",
        "missile_cols": "(none — srvdofunc=18 does not spawn srvmissilea)",
        "calcs": (
            "aurastate=<stance_state> (states.txt group=13 for mutual exclusivity, restrict=1 so shapeshift/restricted skills can cast), "
            "auralencalc=<duration_frames>, aurastat1..5=<boons_and_busts>, aurastat6=<stance_marker_stat>=1, "
            "auraevent1='damagedinmelee', auraeventfunc1=2 (freeze) or 3 (elemental damage)"
        ),
        "proven_in": "conflagration (Enchant), cryostasis (Frozen Armor), overcharge (Energy Shield)",
        "pitfalls": (
            "1) srvdofunc=18 applies only ONE state and never fires offensive events (doactive, domissileattack, domissiledamage). "
            "2) Use auraevent1='damagedinmelee' (landed hits only) rather than 'attackedinmelee' (which fires on whiffs)."
        ),
    },
    {
        "id": "14+144 / 17+-",
        "srvstfunc": "14",
        "srvdofunc": "144",
        "cltstfunc": "17",
        "cltdofunc": "",
        "name": "Multi-Head Turret Cluster Summon with Stance Snapshot (Hydra Engine)",
        "missile_cols": "(summon='hydra', pettype='hydra', sumskill1='HydraMissile')",
        "calcs": (
            "sumsk1calc = (stance_on) ? (lvl + 30) : lvl (snapshots active stance into HydraMissile level!); "
            "sumsk2calc = lvl (passes true Hydra level into HydraMissile); "
            "calc1 = duration in frames; calc2 = petmax (max active 3-head clusters)"
        ),
        "proven_in": "pyre_hydra (Hydra)",
        "pitfalls": (
            "Hydra turrets do not inherit the player's state stats directly; encode the stance flag by adding +30 to sumsk1calc "
            "and testing (lvl > 30) inside HydraMissile's calc1/calc4 and missile Range!"
        ),
    },
    {
        "id": "26 / 27",
        "srvstfunc": "",
        "srvdofunc": "26",
        "cltstfunc": "",
        "cltdofunc": "27",
        "name": "Bouncing Chain Projectile (Chain Lightning / Shuriken / Chain Hammer)",
        "missile_cols": "srvmissilea..c = chain_missile, cltmissilea..c = chain_missile",
        "calcs": "aurarangecalc = bounce search radius (sub-tiles, e.g. 20); calc1 = max bounce hits (e.g. ln34/par5)",
        "proven_in": "spearbolt (Chain Lightning), Paladin Blessed Hammer, Assassin Shuriken",
        "pitfalls": "Requires srvmissilea, srvmissileb, srvmissilec and cltmissilea, cltmissileb, cltmissilec all populated with the chain missile name.",
    },
    {
        "id": "1 / 29",
        "srvstfunc": "",
        "srvdofunc": "1",
        "cltstfunc": "",
        "cltdofunc": "29",
        "name": "Moving Rotating Bolt-Ring Emitter (Frozen Orb Engine)",
        "missile_cols": "srvmissile = orb_main, cltmissile = orb_main, srvmissilea = bolt, cltmissilea = bolt",
        "calcs": "Orb missile uses pSrvDoFunc=16, pCltDoFunc=18, pSrvHitFunc=20, pCltHitFunc=20, SubMissile1=bolt, CltSubMissile1=bolt, HitSubMissile1=bolt, CltHitSubMissile1=bolt",
        "proven_in": "frozen_orb (Frozen Orb)",
        "pitfalls": "Damage lives on the emitted bolt missile (and/or skills.txt with MissileSkill=1 on the bolt), not the carrier orb.",
    },
]


# ---------------------------------------------------------------------------
# 3. Proven missiles.txt Server / Client Function Catalog
# ---------------------------------------------------------------------------
MISSILE_FUNCS: List[Dict[str, str]] = [
    {
        "id": "do 1 / 1",
        "pSrvDoFunc": "1",
        "pCltDoFunc": "1",
        "name": "Standard Linear Mover",
        "notes": "Moves at Vel (+ VelLev per skill level, up to MaxVel) for Range frames. Distance = Vel * Range.",
    },
    {
        "id": "do 2 / 3",
        "pSrvDoFunc": "2",
        "pCltDoFunc": "3",
        "name": "Wake / Trail Dropper Along Flight Path",
        "notes": "Continuously drops SubMissile1 (server) and CltSubMissile1 (client) along its trajectory (used by Brimstone Lance wake & Glacier Step blink path). Set SrvCalc1=0, CltCalc1=0.",
    },
    {
        "id": "do 5 / 5",
        "pSrvDoFunc": "5",
        "pCltDoFunc": "5",
        "name": "Stationary Burning / Damaging Ground Patch (Firewall Cell)",
        "notes": "Used on wake/crater submissiles (brimstone_wake, skyfall_fire) to tick damage every frame/NextDelay for Range frames.",
    },
    {
        "id": "do 16 / 18",
        "pSrvDoFunc": "16",
        "pCltDoFunc": "18",
        "name": "Rotating Bolt-Ring Carrier (Frozen Orb)",
        "notes": "Fires SubMissile1 / CltSubMissile1 in a sweeping spiral while moving, then detonates in a final ring via pSrvHitFunc=20 / pCltHitFunc=20.",
    },
    {
        "id": "do 25 / 48",
        "pSrvDoFunc": "25",
        "pCltDoFunc": "48",
        "name": "Circular Area Server + Client Submissile Scatter (Eruption Center)",
        "notes": (
            "Scatters SubMissile1 (server damage pulses) across skill.calc1 radius every skill.calc2 frames, "
            "and CltSubMissile1/2 (client visuals) across skill.cltcalc1 radius every skill.cltcalc2 frames."
        ),
    },
    {
        "id": "do - / 48",
        "pSrvDoFunc": "",
        "pCltDoFunc": "48",
        "name": "Client-Only Circular Ground Visual Scatter",
        "notes": "Used on cinder_lance_crater, backdraft_center, skyfall_crater_clt to scatter flames/ice cracks across cltcalc1 radius without extra server submissiles.",
    },
    {
        "id": "hit 1 / 1",
        "pSrvHitFunc": "1",
        "pCltHitFunc": "1",
        "name": "Radial AoE Explosion on Impact (Fireball / Cinder Lance / Freezing Arrow)",
        "notes": "Deals AoE damage within skill.calc1 sub-tiles on impact and spawns ExplosionMissile.",
    },
    {
        "id": "hit 1 / 46",
        "pSrvHitFunc": "1",
        "pCltHitFunc": "46",
        "name": "Radial AoE Impact + Client Submissile Ring Burst",
        "notes": "Deals AoE damage within skill.calc1 sub-tiles and spawns skill.calc4 radial CltHitSubMissile1 bolts on impact (proven on Pyre Hydra).",
    },
    {
        "id": "hit 11 / -",
        "pSrvHitFunc": "11",
        "pCltHitFunc": "",
        "name": "Spawn HitSubMissile1 on Expiration / Impact (Maker -> Center Hand-off)",
        "notes": "Used on backdraft_maker and backdraft_explode to chain into the next stage missile when Range expires.",
    },
    {
        "id": "hit 42 / -",
        "pSrvHitFunc": "42",
        "pCltHitFunc": "",
        "name": "Blade Warp Destination Trigger",
        "notes": "Teleports the caster to the missile destination. Its ExplosionMissile (e.g. glacier_step_nova) spawns on the CLIENT ONLY (visuals); server landing damage is srvdofunc 166's own hit.",
    },
]


# ---------------------------------------------------------------------------
# 4. The 7 Reusable Skill Archetype Blueprints (Fire -> Cold & Lightning Map)
# ---------------------------------------------------------------------------
SKILL_ARCHETYPES: Dict[str, Dict[str, str]] = {
    "line 1 (levelling)": {
        "template_slug": "cinder_lance",
        "skills_funcs": "srvdofunc=1, cltdofunc=1 (srvmissile / cltmissile)",
        "missile_pattern": (
            "Fast projectile with Vel + VelLev scaling; pSrvHitFunc=1, pCltHitFunc=1 with calc1=1 base explosion radius "
            "and calc1=4 in matching stance + CltHitSubMissile1 cloned from 'erruption center' (pCltDoFunc=48) for stance AoE burst. "
            "Range wrapped in cross_stance_fizzle_expr(tree, ..., '1')."
        ),
        "tree_slots": "Fire: cinder_lance (done) | Cold: frost_dart (stub -> next) | Lightning: static_lance (stub -> next)",
    },
    "AoE 1 (levelling)": {
        "template_slug": "pyroclasm",
        "skills_funcs": "srvdofunc=154, cltdofunc=99 (radial bolt ring) OR srvdofunc=22, cltdofunc=25 (expanding 64-bolt nova ring)",
        "missile_pattern": (
            "Caster-centered 360° ring. Radius grows with skill level (via VelLev on 154/99 or calc3/cltcalc1 Velocity Adder on 22/25) "
            "and expands further while matching stance is active. Range wrapped in cross_stance_fizzle_expr(tree, ..., '1')."
        ),
        "tree_slots": "Fire: pyroclasm (done) | Cold: hoarfrost_burst (stub -> next) | Lightning: pulse_ring (stub -> next)",
    },
    "combo (CC/AoE)": {
        "template_slug": "backdraft",
        "skills_funcs": "srvstfunc=14, srvdofunc=28, cltstfunc=17, cltdofunc=28",
        "missile_pattern": (
            "Cursor ground controller (maker -> center with pCltDoFunc=48 ground patch visuals) + auratargetstate debuff "
            "or periodic interrupt/shatter pulse across calc1 radius (+bonus radius/duration in matching stance). "
            "Range/aurarangecalc wrapped in cross_stance_fizzle_expr(tree, ..., '0')."
        ),
        "tree_slots": "Fire: backdraft (done) | Cold: permafrost (stub -> next) | Lightning: tesla_field (stub -> next)",
    },
    "utility (mobility)": {
        "template_slug": "glacier_step",
        "skills_funcs": "srvdofunc=166, cltdofunc=104 (Blade Warp blink) OR srvdofunc=23 (Blaze sprint)",
        "missile_pattern": (
            "Strictly stance-gated via restrict=2, State1=sorc_stance_<tree>, with cooldown localdelay=75..250. "
            "Leaves a damaging/chilling wake along the path and/or detonates an arrival nova at destination."
        ),
        "tree_slots": "Fire: flashfire (done) | Cold: glacier_step (wip) | Lightning: phase_step (stub -> next)",
    },
    "AoE 2 (power spike)": {
        "template_slug": "skyfall",
        "skills_funcs": "srvdofunc=28, cltdofunc=28",
        "missile_pattern": (
            "Cursor delayed bombardment / storm zone (skyfall_center / blizzardcenter) with level-scaling radius (calc1 / cltcalc1) "
            "and lingering ground crater/storm (pCltDoFunc=48), expanded in matching stance and fizzled in opposing stances."
        ),
        "tree_slots": "Fire: skyfall (done) | Cold: whiteout (stub -> next) | Lightning: stormcall (stub -> next)",
    },
    "line 2 (boss killer)": {
        "template_slug": "brimstone_lance",
        "skills_funcs": "srvdofunc=1, cltdofunc=1 (all-piercing wake lance) OR srvdofunc=26, cltdofunc=27 (chain bounce)",
        "missile_pattern": (
            "Heavy all-piercing projectile (CollideKill=0, Pierce=1, LastCollide=1, NextDelay=4) with pSrvDoFunc=2, pCltDoFunc=3 "
            "dropping a damaging wake trail (SubMissile1/CltSubMissile1) that persists 10x longer in matching stance."
        ),
        "tree_slots": "Fire: brimstone_lance (done) | Cold: icicle_spear (stub -> next) | Lightning: spearbolt (stub -> next)",
    },
    "capstone": {
        "template_slug": "pyre_hydra",
        "skills_funcs": "srvstfunc=14, srvdofunc=144 (Hydra summon) OR srvdofunc=1, cltdofunc=29 (Frozen Orb) OR srvdofunc=28, cltdofunc=28 (Pillar + radial storm)",
        "missile_pattern": (
            "Level 40 signature skill with no cooldown, non-linear tier scaling, 2 tree synergies, stance empowerment, "
            "and cross-stance fizzle in opposing stances."
        ),
        "tree_slots": "Fire: pyre_hydra (done) | Cold: frozen_orb (stub -> next) | Lightning: heavens_wrath (stub -> next)",
    },
}

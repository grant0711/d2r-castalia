"""
Sorceress 1:1 skill map (single source of truth for layout, names and design intent).

Every one of the 30 vanilla Sorceress skill rows is reused (same row name, charclass="sor", icon
frame). `vid` is the SOURCE id builders/specs author against; at write time mod_builder/skill_order.py
re-sorts the rows so each tier is a contiguous final id block (and remaps numeric skill refs + HD
skillIndex). What changes is what that row *does*, what it is *called* and its final id:

    vanilla row (id, name)  --1:1-->  new skill (name, tree, row, col, level, design)

NOTE: items that grant "+1 Fire Ball" etc. will now boost whichever new skill replaced that
row. That is intended; it is the cost of keeping the save format stable.

Pages: 1 = Fire, 2 = Lightning, 3 = Cold (matches soskilltree.sprite frames 0, 1, 2).
Rows are the mod's 6 unlock tiers: 1 / 8 / 16 / 24 / 32 / 40.
"""

TIER_LEVELS = [1, 8, 16, 24, 32, 40]
PAGE = {"fire": 1, "lightning": 2, "cold": 3}
# soskilltree.sprite frame per tree (Frame 0 = Left Tab = Cold/Page 3, Frame 1 = Middle Tab = Lightning/Page 2, Frame 2 = Right Tab = Fire/Page 1)
FRAME = {"cold": 0, "lightning": 1, "fire": 2}

# Each entry:
#   slug    stable file/key name (never rename)
#   tree    fire | cold | lightning
#   vid     vanilla *Id that is replaced
#   vname   vanilla skills.txt `skill` row name (the row we reuse)
#   name    new in-game name
#   row/col skill tab grid position (row 1..6, col 1..3)
#   role    slot role from the blueprint
#   design  one-paragraph intent (what the finished skill should do)
#   level   optional reqlevel override (defaults to the tier level of `row`)
#   prereqs optional list of prerequisite slugs
SLOTS = [
    # ------------------------------------------------------------------ FIRE
    dict(slug="cinder_lance", tree="fire", vid=36, vname="Fire Bolt", name="Cinder Lance",
         row=1, col=1, prereqs=[], role="line 1 (levelling)",
         design="Fast bolt of flame whose velocity scales with level (Vel=14, VelLev=4, MaxVel=40). In Conflagration: range doubles (15 -> 30) and bolts detonate in a radius-4 AoE explosion on impact. Fizzles in Cryostasis or Overcharge."),
    dict(slug="pyroclasm", tree="fire", vid=47, vname="Fire Ball", name="Pyroclasm",
         row=2, col=1, prereqs=["cinder_lance"], role="AoE 1 (levelling)",
         design="Caster-centered 360-degree ring of fiery bolts with knockback; ring radius scales with level (Vel=8, VelLev=3, MaxVel=16) and bolt count grows 5 -> 8 (+5 bolts in Conflagration, up to 16). Fizzles in Cryostasis or Overcharge."),
    dict(slug="flashfire", tree="fire", vid=46, vname="Blaze", name="Flashfire",
         row=3, col=3, prereqs=["conflagration"], role="utility (mobility)",
         design="Strictly requires Conflagration to cast (restrict=2, State1=sorc_stance_fire). 3s tactical sprint (+100% FRW in Conflagration, 10s cooldown) leaving a 3s burning trail whose damage scales non-linearly with level."),
    dict(slug="conflagration", tree="fire", vid=52, vname="Enchant", name="Conflagration",
         row=3, col=2, prereqs=[], role="STANCE",
         design="Castable timed Fire stance (60s + 10s/lvl, srvdofunc=18, states.txt group=13, marker stat skill_handofathena=1). Boons: +5% -> +75% Fire Skill Damage, +5% -> +40% FCR, +30% -> +258% Mana Recovery Rate. Busts: +5% -> +50% Physical Damage Taken (cap 75%) and 1 -> 10 Life/sec drain. Melee attackers that hit you take Fire damage scaled by stance level and Kindling."),
    dict(slug="backdraft", tree="fire", vid=51, vname="Fire Wall", name="Backdraft",
         row=2, col=3, prereqs=[], role="combo (CC/AoE)",
         design="Cursor fiery vortex (2s cooldown) that pulls enemies inward and slows movement speed (45%+lvl%, +15% in Conflagration, duration extended by Kindling) while burning the ground before detonating in a blast (radius 3..5, +2 in Conflagration). Fizzles in Cryostasis or Overcharge."),
    dict(slug="kindling", tree="fire", vid=37, vname="Warmth", name="Kindling",
         row=4, col=2, prereqs=["conflagration"], role="support passive",
         design="Passive: increases Conflagration's melee fire retaliation damage by +10% per level and extends Backdraft's slow duration by +5 frames per base level."),
    dict(slug="skyfall", tree="fire", vid=56, vname="Meteor", name="Skyfall",
         row=4, col=3, prereqs=["flashfire"], role="AoE 2 (power spike)",
         design="Calls down a meteor on the cursor (1.2s delay, 1.2s cooldown), dealing heavy AoE impact damage and leaving a burning crater (radius 4..7, +3 in Conflagration; duration 3s + 0.2s/lvl). Fizzles in Cryostasis or Overcharge."),
    dict(slug="brimstone_lance", tree="fire", vid=41, vname="Inferno", name="Brimstone Lance",
         row=5, col=1, prereqs=["pyroclasm"], role="line 2 (boss killer)",
         design="Heavy blazing lance that pierces all enemies (Vel=18, VelLev=6, MaxVel=36, Range=38) and drops a burning wake along its flight path (0.4s base duration, 4.0s molten wake in Conflagration). Fizzles in Cryostasis or Overcharge."),
    dict(slug="ignition", tree="fire", vid=61, vname="Fire Mastery", name="Ignition",
         row=5, col=3, prereqs=["kindling", "skyfall"], role="dial (potency)",
         design="Always-on passive: continually regenerates Life each second (1 Life/sec at lvl 1 -> 10 Life/sec at lvl 26), offsetting Conflagration's life drain."),
    dict(slug="pyre_hydra", tree="fire", vid=62, vname="Hydra", name="Pyre Hydra",
         row=6, col=2, prereqs=["brimstone_lance", "kindling"], role="capstone",
         design="Zero-cooldown Level 40 capstone: summons 3-headed Hydra cluster(s) at the cursor (max 1 cluster at lvl 1-12, 2 at 13-25, 3 at 26+). In Conflagration (snapshotted via sumsk1calc=lvl+30): duration +4s, bolt range increases, and every bolt impact erupts into 6 radial sub-bolts with radius-6 AoE. Fizzles in Cryostasis or Overcharge."),
    # ------------------------------------------------------------------ COLD
    dict(slug="frost_dart", tree="cold", vid=39, vname="Ice Bolt", name="Frost Dart",
         row=1, col=2, role="line 1 (levelling)",
         design="Fast long-range ice bolt that chills enemies and scales velocity/reach with level. In Cryostasis: chill duration and impact AoE radius expand. Fizzles in Conflagration or Overcharge."),
    dict(slug="hoarfrost_burst", tree="cold", vid=44, vname="Frost Nova", name="Hoarfrost Burst",
         row=2, col=2, role="AoE 1 (levelling)",
         design="Instant expanding frost ring around the caster that chills/freezes nearby enemies; ring radius and duration grow with level and expand further in Cryostasis. Fizzles in Conflagration or Overcharge."),
    dict(slug="glacier_step", tree="cold", vid=60, vname="Chilling Armor", name="Glacier Step",
         row=3, col=1, role="utility (mobility)",
         design="Strictly requires Cryostasis to cast (restrict=2, State1=sorc_stance_cold). Directional ice blink (srvdofunc=166 / cltdofunc=104, 3s cooldown) that freezes and damages enemies along your wake and in a burst of ice spikes where you arrive."),
    dict(slug="permafrost", tree="cold", vid=45, vname="Ice Blast", name="Permafrost",
         row=3, col=3, role="combo (CC/AoE)",
         design="Cursor ground freeze field that chills/slows and damages enemies inside it, with expanded radius and duration in Cryostasis. Fizzles in Conflagration or Overcharge."),
    dict(slug="cryostasis", tree="cold", vid=40, vname="Frozen Armor", name="Cryostasis",
         row=4, col=1, role="STANCE",
         design="Castable timed Cold stance (60s + 10s/lvl, srvdofunc=18, states.txt group=13, marker stat skill_frenzy=1): the slow juggernaut. Boons: +5% -> +75% Cold Skill Damage, +3% -> +25% Physical Damage Reduction, +10% -> +200% Defense. Busts: -5% -> -50% Run/Walk Speed and -5% -> -30% FCR. Melee attackers that hit you are frozen (duration scaled by stance level and Brittle Touch)."),
    dict(slug="equilibrium", tree="cold", vid=65, vname="Cold Mastery", name="Equilibrium",
         row=4, col=2, role="dial (penalty reduction)",
         design="Always-on passive: restores Mana after each enemy you kill (+2 at lvl 1 -> +30 at lvl 20)."),
    dict(slug="brittle_touch", tree="cold", vid=50, vname="Shiver Armor", name="Brittle Touch",
         row=4, col=3, role="support passive",
         design="Passive: increases Cryostasis's melee freeze retaliation duration by +5% per level."),
    dict(slug="whiteout", tree="cold", vid=59, vname="Blizzard", name="Whiteout",
         row=5, col=1, role="AoE 2 (power spike)",
         design="Cursor snowstorm bombardment that chills and damages enemies in a growing radius, with expanded radius/intensity in Cryostasis. Fizzles in Conflagration or Overcharge."),
    dict(slug="icicle_spear", tree="cold", vid=55, vname="Glacial Spike", name="Icicle Spear",
         row=5, col=3, role="line 2 (boss killer)",
         design="Heavy all-piercing ice lance that deep-chills targets and leaves a freezing wake (persisting longer in Cryostasis). Fizzles in Conflagration or Overcharge."),
    dict(slug="frozen_orb", tree="cold", vid=64, vname="Frozen Orb", name="Frozen Orb",
         row=6, col=2, role="capstone",
         design="Zero-cooldown Level 40 capstone: spinning orb travels forward firing a sweeping spiral of ice bolts before detonating in a final ring, empowered in Cryostasis. Fizzles in Conflagration or Overcharge."),
    # ------------------------------------------------------------- LIGHTNING
    dict(slug="static_lance", tree="lightning", vid=49, vname="Lightning", name="Static Lance",
         row=1, col=2, role="line 1 (levelling)",
         design="Fast long-range lightning bolt/beam that scales velocity/reach with level and gains bonus AoE/discharge in Overcharge. Fizzles in Conflagration or Cryostasis."),
    dict(slug="pulse_ring", tree="lightning", vid=48, vname="Nova", name="Pulse Ring",
         row=2, col=1, role="AoE 1 (levelling)",
         design="Instant expanding lightning ring around the caster whose radius scales with level and expands further in Overcharge. Fizzles in Conflagration or Cryostasis."),
    dict(slug="phase_step", tree="lightning", vid=54, vname="Teleport", name="Phase Step",
         row=2, col=3, role="utility (mobility)",
         design="Strictly requires Overcharge to cast (restrict=2, State1=sorc_stance_light). High-speed lightning blink with short cooldown and static discharge along the path/arrival."),
    dict(slug="afterglow", tree="lightning", vid=63, vname="Lightning Mastery", name="Echo",
         row=3, col=1, role="dial (cross-stance synergy)",
         design="Always-on passive (slug 'afterglow', in-game name 'Echo'): converts 5% -> 75% of damage taken into Mana (capped at 100%)."),
    dict(slug="tesla_field", tree="lightning", vid=42, vname="Static Field", name="Sunderbolt",
         row=3, col=2, role="combo (CC/AoE)",
         design="Fist of the Heavens engine (80/36): calls down a sky-bolt onto a target, knocking back and briefly scattering surrounding minions (terror w/ hidden overlay, 0.72->1.12s neutral / 1.44->1.84s Overcharge) while leaving a crackling ground shock field (2.0->3.6s neutral / 3.0->4.6s Overcharge) under the isolated target. Fizzles in Conflagration or Cryostasis."),
    dict(slug="conduction", tree="lightning", vid=43, vname="Telekinesis", name="Conduction",
         row=3, col=3, role="support passive",
         design="Passive: increases Overcharge's melee lightning retaliation damage by +10% per level."),
    dict(slug="overcharge", tree="lightning", vid=58, vname="Energy Shield", name="Overcharge",
         row=4, col=2, role="STANCE",
         design="Castable timed Lightning stance (60s + 10s/lvl, srvdofunc=18, states.txt group=13, marker stat skill_decrepify=1). Boons: +5% -> +75% Lightning Skill Damage, +5% -> +40% FRW, +5% -> +40% FHR. Busts: -5% -> -75% Fire Resist and -5% -> -75% Cold Resist. Melee attackers that hit you take Lightning damage scaled by stance level and Conduction."),
    dict(slug="stormcall", tree="lightning", vid=57, vname="Thunder Storm", name="Stormcall",
         row=4, col=3, role="AoE 2 (power spike)",
         design="Cursor lightning storm bombardment that calls down strikes across a target area, with expanded radius/intensity in Overcharge. Fizzles in Conflagration or Cryostasis."),
    dict(slug="spearbolt", tree="lightning", vid=53, vname="Chain Lightning", name="Spearbolt",
         row=5, col=2, role="line 2 (boss killer)",
         design="Heavy high-voltage boss killer (piercing wake lance or multi-bounce chain lightning) empowered in Overcharge. Fizzles in Conflagration or Cryostasis."),
    dict(slug="heavens_wrath", tree="lightning", vid=38, vname="Charged Bolt", name="Heaven's Wrath",
         row=6, col=2, role="capstone",
         design="Zero-cooldown Level 40 capstone: pillar of lightning strikes the cursor and unleashes radial follow-up strikes/bolts, empowered in Overcharge. Fizzles in Conflagration or Cryostasis."),
]

BY_SLUG = {s["slug"]: s for s in SLOTS}
BY_VID = {s["vid"]: s for s in SLOTS}


def slot_level(slot: dict) -> int:
    return int(slot.get("level", TIER_LEVELS[slot["row"] - 1]))


def check_registry() -> list:
    """Static sanity checks on the map. Returns a list of problems (empty = ok)."""
    problems = []
    if len(SLOTS) != 30:
        problems.append(f"expected 30 slots, found {len(SLOTS)}")
    for key in ("slug", "vid", "vname", "name"):
        vals = [s[key] for s in SLOTS]
        if len(set(vals)) != len(vals):
            problems.append(f"duplicate {key}")
    cells = {}
    for s in SLOTS:
        cell = (s["tree"], s["row"], s["col"])
        if cell in cells:
            problems.append(f"cell {cell} used by {cells[cell]} and {s['slug']}")
        cells[cell] = s["slug"]
        if not (1 <= s["row"] <= 6 and 1 <= s["col"] <= 3):
            problems.append(f"{s['slug']}: row/col out of range")
    for tree in PAGE:
        n = sum(1 for s in SLOTS if s["tree"] == tree)
        if n != 10:
            problems.append(f"tree {tree} has {n} skills (need 10)")
    return problems

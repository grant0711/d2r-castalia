"""
Sorceress 1:1 skill map (single source of truth for layout, names and design intent).

Every one of the 30 vanilla Sorceress skill rows is KEPT (same row name, same *Id, same
charclass="sor", same icon frame) so saves, items (`oskill`, staves, charms) and tables that
reference them keep working. What changes is what that row *does* and what it is *called*:

    vanilla row (id, name)  --1:1-->  new skill (name, tree, row, col, level, design)

NOTE: items that grant "+1 Fire Ball" etc. will now boost whichever new skill replaced that
row. That is intended; it is the cost of keeping the save format stable.

Pages: 1 = Fire, 2 = Lightning, 3 = Cold (matches soskilltree.sprite frames 0, 1, 2).
Rows are the mod's 6 unlock tiers: 1 / 8 / 16 / 24 / 32 / 40.
"""

TIER_LEVELS = [1, 8, 16, 24, 32, 40]
PAGE = {"fire": 1, "lightning": 2, "cold": 3}
# soskilltree.sprite frame per tree (Fire, Lightning, Cold)
FRAME = {"fire": 0, "lightning": 1, "cold": 2}

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
SLOTS = [
    # ------------------------------------------------------------------ FIRE
    dict(slug="cinder_lance", tree="fire", vid=36, vname="Fire Bolt", name="Cinder Lance",
         row=1, col=2, role="line 1 (levelling)",
         design="Fast, thin, long-range fire bolt that pierces 3 enemies. In Conflagration the whole path ignites."),
    dict(slug="pyroclasm", tree="fire", vid=47, vname="Fire Ball", name="Pyroclasm",
         row=2, col=1, role="AoE 1 (levelling)",
         design="Instant ring blast centred on the caster, radius 6, with knockback. In Conflagration: radius +50% and a 3s fire ring."),
    dict(slug="flashfire", tree="fire", vid=46, vname="Blaze", name="Flashfire",
         row=2, col=3, role="utility (mobility)",
         design="8-yd dash in a line leaving a burning corridor (3s). In Conflagration the corridor lasts 6s and is twice as wide."),
    dict(slug="backdraft", tree="fire", vid=51, vname="Fire Wall", name="Backdraft",
         row=3, col=1, role="combo (CC/AoE)",
         design="Ground fire (r4, 6s) that slows enemies 30%. A later fire spell hitting it detonates it (r6). Strong on arrival, only +3%/lvl; slow and detonation stay useful. Conflagration: detonations chain to adjacent patches."),
    dict(slug="conflagration", tree="fire", vid=52, vname="Enchant", name="Conflagration",
         row=3, col=2, role="STANCE",
         design="Castable timed state (60s+10s/lvl). Benefits: +105% FCR and a 3s fire trail on every cast. Penalties: rapid mana decay (hidden mana-burn missile per cast), outgoing damage rolls 25-175%, damage taken re-rolls each cast (+0..60%). Benefit/penalty halves are separate states so Afterglow can keep the benefits. One red orb shows while the benefits are on."),
    dict(slug="ignition", tree="fire", vid=61, vname="Fire Mastery", name="Ignition",
         row=3, col=3, role="dial (potency)",
         design="Passive: all active stance benefit numbers +2% per level (up to +40%). Penalties do not grow."),
    dict(slug="kindling", tree="fire", vid=37, vname="Warmth", name="Kindling",
         row=4, col=1, role="support passive",
         design="Fire hits apply a stacking Burn (3 dmg/stack/s, max 5, 4s). In Conflagration a burning enemy that dies leaves a 2-yd fire patch for 2s."),
    dict(slug="skyfall", tree="fire", vid=56, vname="Meteor", name="Skyfall",
         row=4, col=3, role="AoE 2 (power spike)",
         design="Meteor lands on the cursor after a 1.2s delay, r7. First big AoE jump (Blizzard-like). In Conflagration the delay drops to 0.6s."),
    dict(slug="brimstone_lance", tree="fire", vid=41, vname="Inferno", name="Brimstone Lance",
         row=5, col=2, role="line 2 (boss killer)",
         design="Slow heavy spear that pierces ALL enemies, -25% fire resistance for 6s, +40% damage to unique bosses. In Conflagration leaves a molten line (4s)."),
    dict(slug="pyre_hydra", tree="fire", vid=62, vname="Hydra", name="Pyre Hydra",
         row=6, col=2, role="capstone",
         design="Summons 3 fire-spewing heads at the cursor for 12s; each fires at enemies in range and leaves fire pools. No cooldown, no self-risk. In Conflagration the heads leave trails and their fire detonates nearby Backdraft patches."),
    # ------------------------------------------------------------------ COLD
    dict(slug="frost_dart", tree="cold", vid=39, vname="Ice Bolt", name="Frost Dart",
         row=1, col=2, role="line 1 (levelling)",
         design="Fast long-range bolt that chills. In Cryostasis the cold pierce applies."),
    dict(slug="hoarfrost_burst", tree="cold", vid=44, vname="Frost Nova", name="Hoarfrost Burst",
         row=2, col=2, role="AoE 1 (levelling)",
         design="Instant ring around the caster (r5) that freezes 1.5s. In Cryostasis radius +30% and freeze +1s."),
    dict(slug="glacier_step", tree="cold", vid=60, vname="Chilling Armor", name="Glacier Step",
         row=3, col=1, role="utility (mobility)",
         design="8-yd slide along an ice lane that chills enemies on it. In Cryostasis you ignore the -30% slow while sliding and freeze enemies at the start point for 1s."),
    dict(slug="permafrost", tree="cold", vid=45, vname="Ice Blast", name="Permafrost",
         row=3, col=3, role="combo (CC/AoE)",
         design="Ground freeze field (r5, 8s) that slows 40%; fire hits or melee strikes shatter enemies inside it. Strong on arrival, low per-level scaling. In Cryostasis the field is placed under you and you are chill-immune inside it."),
    dict(slug="cryostasis", tree="cold", vid=40, vname="Frozen Armor", name="Cryostasis",
         row=4, col=1, role="STANCE",
         design="Castable timed state (60s+10s/lvl). Benefits: +250% Defense, +25% cold pierce, melee attackers frozen 1s. Penalties: move speed -30%, physical damage taken +25%. Separate benefit/penalty states; one blue orb while the benefits are on."),
    dict(slug="equilibrium", tree="cold", vid=65, vname="Cold Mastery", name="Equilibrium",
         row=4, col=2, role="dial (penalty reduction)",
         design="Passive: every active stance penalty -1.5% per level, capped at -30% (Fire's mana burn, Cold's slow/physical damage, Lightning's scatter cone)."),
    dict(slug="brittle_touch", tree="cold", vid=50, vname="Shiver Armor", name="Brittle Touch",
         row=4, col=3, role="support passive",
         design="Chilled enemies take +20% physical damage. In Cryostasis melee hits on frozen enemies shatter them (150% weapon damage, r3)."),
    dict(slug="whiteout", tree="cold", vid=59, vname="Blizzard", name="Whiteout",
         row=5, col=1, role="AoE 2 (power spike)",
         design="Delayed (1s) snowstorm on the cursor, 4s, r8, slows and chills. First big cold AoE jump. In Cryostasis enemies caught 2s+ freeze solid."),
    dict(slug="icicle_spear", tree="cold", vid=55, vname="Glacial Spike", name="Icicle Spear",
         row=5, col=3, role="line 2 (boss killer)",
         design="Slow heavy lance that pierces ALL enemies, -25% cold resistance for 6s, +40% damage to unique bosses. In Cryostasis freeze duration x1.5."),
    dict(slug="frozen_orb", tree="cold", vid=64, vname="Frozen Orb", name="Frozen Orb",
         row=6, col=2, role="capstone",
         design="Spinning orb travels to the cursor firing a ring of ice bolts, then returns. No cooldown, no self-risk. In Cryostasis frozen enemies hit by its bolts take +100% shatter damage."),
    # ------------------------------------------------------------- LIGHTNING
    dict(slug="static_lance", tree="lightning", vid=49, vname="Lightning", name="Static Lance",
         row=1, col=2, role="line 1 (levelling)",
         design="Instant long-range beam that pierces every enemy. In Overcharge it splits into three scattered beams."),
    dict(slug="pulse_ring", tree="lightning", vid=48, vname="Nova", name="Pulse Ring",
         row=2, col=1, role="AoE 1 (levelling)",
         design="Instant expanding ring (r7) that shocks and triggers hit recovery. In Overcharge it discharges the crawling bolts early."),
    dict(slug="phase_step", tree="lightning", vid=54, vname="Teleport", name="Phase Step",
         row=2, col=3, role="utility (mobility)",
         design="12-yd teleport, 2s cooldown. In Overcharge you land within 3 yd of the target point (random) and leave a bolt ring at the origin."),
    dict(slug="afterglow", tree="lightning", vid=63, vname="Lightning Mastery", name="Afterglow",
         row=3, col=1, role="dial (benefit persistence)",
         design="Passive (unlock lvl 24): when you swap stances the previous stance's BENEFITS persist for 2s + 0.5s per level (11.5s at 20; gear levels count up to 27 = 15.5s). Penalties end immediately."),
    dict(slug="tesla_field", tree="lightning", vid=42, vname="Static Field", name="Tesla Field",
         row=3, col=2, role="combo (CC/AoE)",
         design="Static orb on the ground (8s) zapping enemies within r6 every 0.5s and interrupting them. Strong on arrival, low per-level scaling. In Overcharge it absorbs your bolt ring and doubles its zap rate."),
    dict(slug="conduction", tree="lightning", vid=43, vname="Telekinesis", name="Conduction",
         row=3, col=3, role="support passive",
         design="Lightning hits lower the target's lightning resistance 5% per hit (max -30%, 5s). In Overcharge the Charged Bolt ring also applies it."),
    dict(slug="overcharge", tree="lightning", vid=58, vname="Energy Shield", name="Overcharge",
         row=4, col=2, role="STANCE",
         design="Castable timed state (60s+10s/lvl). Benefits: a ring of 6 Charged Bolts on every cast, Faraday Shield (40% of enemy projectiles pass through). Penalty: single-target projectiles spray in a 30-degree cone. Separate benefit/penalty states; one white orb while the benefits are on."),
    dict(slug="stormcall", tree="lightning", vid=57, vname="Thunder Storm", name="Stormcall",
         row=4, col=3, role="AoE 2 (power spike)",
         design="Delayed (1s) strikes at 4 random spots near the cursor (r5 each). First big lightning AoE jump. In Overcharge the strike count doubles."),
    dict(slug="spearbolt", tree="lightning", vid=53, vname="Chain Lightning", name="Spearbolt",
         row=5, col=2, role="line 2 (boss killer)",
         design="Slow heavy bolt that pierces ALL enemies, -25% lightning resistance for 6s, +40% damage to unique bosses. In Overcharge it splits into two scattered bolts."),
    dict(slug="heavens_wrath", tree="lightning", vid=38, vname="Charged Bolt", name="Heaven's Wrath",
         row=6, col=2, role="capstone",
         design="Pillar of lightning strikes the cursor, then 8 follow-up strikes rain in a ring around it over 3s. No cooldown, no self-risk. In Overcharge strikes chain through Charged Bolts."),
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

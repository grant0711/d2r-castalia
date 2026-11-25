"""
Assassin 1:1 skill map (single source of truth for layout, names, prereqs & design).
"""

TIER_LEVELS = [1, 8, 16, 24, 32, 40]
PAGE = {'traps': 1, 'shadow': 2, 'martial': 3}

SLOTS = [
    # ------------------------------------------------------------------ TRAPS
    dict(slug='shock_field', tree='traps', vid=256, vname='Shock Field', name='Caltrops', row=1, col=2, prereqs=[], role='traps', design='Caltrops'),
    dict(slug='blade_sentinel', tree='traps', vid=257, vname='Blade Sentinel', name='Blade Sentinel', row=1, col=3, prereqs=[], role='traps', design='Blade Sentinel'),
    dict(slug='fire_trauma', tree='traps', vid=251, vname='Fire Trauma', name='Shrapnel Sentry', row=2, col=2, prereqs=['shock_field'], role='traps', design='Shrapnel Sentry'),
    dict(slug='wake_of_fire_sentry', tree='traps', vid=262, vname='Wake of Fire Sentry', name='Fire Sentry', row=3, col=1, prereqs=['fire_trauma'], role='traps', design='Fire Sentry'),
    dict(slug='blade_fury', tree='traps', vid=266, vname='Blade Fury', name='Blade Fury', row=3, col=3, prereqs=['blade_sentinel'], role='traps', design='Blade Fury'),
    dict(slug='death_sentry', tree='traps', vid=276, vname='Death Sentry', name='Ice Sentry', row=4, col=1, prereqs=['wake_of_fire_sentry'], role='traps', design='Ice Sentry'),
    dict(slug='lightning_sentry', tree='traps', vid=271, vname='Lightning Sentry', name='Lightning Sentry', row=5, col=1, prereqs=['death_sentry'], role='traps', design='Lightning Sentry'),
    dict(slug='blade_shield', tree='traps', vid=277, vname='Blade Shield', name='Blade Shield', row=5, col=3, prereqs=['blade_fury'], role='traps', design='Blade Shield'),
    dict(slug='charged_bolt_sentry', tree='traps', vid=261, vname='Charged Bolt Sentry', name='Soul Siphon Sentry', row=6, col=2, prereqs=['fire_trauma', 'blade_shield'], role='traps', design='Soul Siphon Sentry'),
    dict(slug='inferno_sentry', tree='traps', vid=272, vname='Inferno Sentry', name='Shuriken', row=6, col=3, prereqs=['blade_shield'], role='traps', design='Shuriken'),
    # ------------------------------------------------------------------ SHADOW
    dict(slug='claw_mastery', tree='shadow', vid=252, vname='Claw Mastery', name='Lethality', row=1, col=3, prereqs=[], role='shadow', design='Lethality'),
    dict(slug='cloak_of_shadows', tree='shadow', vid=264, vname='Cloak of Shadows', name='Cloak of Shadows', row=2, col=1, prereqs=[], role='shadow', design='Cloak of Shadows'),
    dict(slug='weapon_block', tree='shadow', vid=263, vname='Weapon Block', name='Weapon Block', row=2, col=2, prereqs=['claw_mastery'], role='shadow', design='Weapon Block'),
    dict(slug='shadow_warrior', tree='shadow', vid=268, vname='Shadow Warrior', name='Shadow Bind', row=3, col=1, prereqs=['cloak_of_shadows'], role='shadow', design='Shadow Bind'),
    dict(slug='quickness', tree='shadow', vid=258, vname='Quickness', name='Burst of Speed', row=3, col=3, prereqs=['claw_mastery'], role='shadow', design='Burst of Speed'),
    dict(slug='mind_blast', tree='shadow', vid=273, vname='Mind Blast', name='Mind Blast', row=4, col=1, prereqs=['shadow_warrior'], role='shadow', design='Mind Blast'),
    dict(slug='fade', tree='shadow', vid=267, vname='Fade', name='Fade', row=5, col=2, prereqs=['weapon_block'], role='shadow', design='Fade'),
    dict(slug='venom', tree='shadow', vid=278, vname='Venom', name='Venom', row=5, col=3, prereqs=['quickness'], role='shadow', design='Venom'),
    dict(slug='shadow_master', tree='shadow', vid=279, vname='Shadow Master', name='Shadow Master', row=6, col=1, prereqs=['fade', 'mind_blast'], role='shadow', design='Shadow Master'),
    dict(slug='psychic_hammer', tree='shadow', vid=253, vname='Psychic Hammer', name='Flow', row=6, col=3, prereqs=['venom'], role='shadow', design='Flow'),
    # ------------------------------------------------------------------ MARTIAL
    dict(slug='tiger_strike', tree='martial', vid=254, vname='Tiger Strike', name='Tiger Strike', row=1, col=2, prereqs=[], role='martial', design='Tiger Strike'),
    dict(slug='dragon_talon', tree='martial', vid=255, vname='Dragon Talon', name='Dragon Talon', row=1, col=3, prereqs=[], role='martial', design='Dragon Talon'),
    dict(slug='fists_of_fire', tree='martial', vid=259, vname='Fists of Fire', name='Flamestrike', row=2, col=1, prereqs=[], role='martial', design='Flamestrike'),
    dict(slug='blades_of_ice', tree='martial', vid=274, vname='Blades of Ice', name='Blades of Ice', row=3, col=1, prereqs=['fists_of_fire'], role='martial', design='Blades of Ice'),
    dict(slug='dragon_claw', tree='martial', vid=260, vname='Dragon Claw', name='Dragon Claw', row=3, col=2, prereqs=['tiger_strike'], role='martial', design='Dragon Claw'),
    dict(slug='claws_of_thunder', tree='martial', vid=269, vname='Claws of Thunder', name='Electrocute', row=4, col=1, prereqs=['blades_of_ice'], role='martial', design='Electrocute'),
    dict(slug='dragon_tail', tree='martial', vid=270, vname='Dragon Tail', name='Dragon Tail', row=4, col=3, prereqs=['dragon_talon'], role='martial', design='Dragon Tail'),
    dict(slug='cobra_strike', tree='martial', vid=265, vname='Cobra Strike', name='Cobra Strike', row=5, col=2, prereqs=['dragon_claw'], role='martial', design='Cobra Strike'),
    dict(slug='dragon_flight', tree='martial', vid=275, vname='Dragon Flight', name='Dragon Flight', row=5, col=3, prereqs=['dragon_tail'], role='martial', design='Dragon Flight'),
    dict(slug='royal_strike', tree='martial', vid=280, vname='Royal Strike', name='Omnislash', row=6, col=1, prereqs=['claws_of_thunder', 'cobra_strike'], role='martial', design='Omnislash'),
]

BY_SLUG = {s["slug"]: s for s in SLOTS}
BY_VID = {s["vid"]: s for s in SLOTS}


def slot_level(slot: dict) -> int:
    return slot.get("level", TIER_LEVELS[slot["row"] - 1])


def check_registry() -> list:
    errors = []
    if len(SLOTS) != 30:
        errors.append(f"expected 30 slots, got {len(SLOTS)}")
    for field in ('slug', 'vid', 'vname'):
        vals = [s[field] for s in SLOTS]
        if len(vals) != len(set(vals)):
            errors.append(f"duplicate {field}")
    seen_cells = set()
    for s in SLOTS:
        cell = (s['tree'], s['row'], s['col'])
        if cell in seen_cells:
            errors.append(f"cell collision at {cell}")
        seen_cells.add(cell)
        for p in s.get('prereqs', []):
            if p not in BY_SLUG:
                errors.append(f"{s['slug']}: unknown prereq {p}")
    return errors

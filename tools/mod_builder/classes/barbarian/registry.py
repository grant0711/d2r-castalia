"""
Barbarian 1:1 skill map (single source of truth for layout, names, prereqs & design).
"""

TIER_LEVELS = [1, 8, 16, 24, 32, 40]
PAGE = {'combat': 1, 'masteries': 2, 'warcries': 3}

SLOTS = [
    # ------------------------------------------------------------------ COMBAT
    dict(slug='bash', tree='combat', vid=126, vname='Bash', name='Strike', row=1, col=1, prereqs=[], role='combat', design='Strike'),
    dict(slug='double_swing', tree='combat', vid=133, vname='Double Swing', name='Flurry', row=1, col=3, prereqs=[], role='combat', design='Flurry'),
    dict(slug='leap', tree='combat', vid=132, vname='Leap', name='Leap', row=2, col=2, prereqs=[], role='combat', design='Leap'),
    dict(slug='concentrate', tree='combat', vid=144, vname='Concentrate', name='Concentrate', row=3, col=1, prereqs=['bash'], role='combat', design='Concentrate'),
    dict(slug='double_throw', tree='combat', vid=140, vname='Double Throw', name='Barrage', row=3, col=3, prereqs=['double_swing'], role='combat', design='Barrage'),
    dict(slug='leap_attack', tree='combat', vid=143, vname='Leap Attack', name='Leap Attack', row=4, col=2, prereqs=['leap'], role='combat', design='Leap Attack'),
    dict(slug='stun', tree='combat', vid=139, vname='Stun', name='Shield Slam', row=5, col=1, prereqs=['concentrate'], role='combat', design='Shield Slam'),
    dict(slug='berserk', tree='combat', vid=152, vname='Berserk', name='Berserk', row=5, col=3, prereqs=['double_throw'], role='combat', design='Berserk'),
    dict(slug='whirlwind', tree='combat', vid=151, vname='Whirlwind', name='Whirlwind', row=6, col=2, prereqs=['leap_attack', 'berserk'], role='combat', design='Whirlwind'),
    dict(slug='frenzy', tree='combat', vid=147, vname='Frenzy', name='Frenzy', row=6, col=3, prereqs=['berserk'], role='combat', design='Frenzy'),
    # ------------------------------------------------------------------ MASTERIES
    dict(slug='blade_mastery', tree='masteries', vid=127, vname='Blade Mastery', name='One-Handed Mastery', row=1, col=1, prereqs=[], role='masteries', design='One-Handed Mastery'),
    dict(slug='axe_mastery', tree='masteries', vid=128, vname='Axe Mastery', name='Two-Handed Mastery', row=1, col=2, prereqs=[], role='masteries', design='Two-Handed Mastery'),
    dict(slug='throwing_mastery', tree='masteries', vid=135, vname='Throwing Mastery', name='Throwing Mastery', row=1, col=3, prereqs=[], role='masteries', design='Throwing Mastery'),
    dict(slug='increased_stamina', tree='masteries', vid=141, vname='Increased Stamina', name='Unflinching', row=2, col=1, prereqs=[], role='masteries', design='Unflinching'),
    dict(slug='pole_arm_mastery', tree='masteries', vid=134, vname='Pole Arm Mastery', name='Critical Strike', row=2, col=2, prereqs=[], role='masteries', design='Critical Strike'),
    dict(slug='increased_speed', tree='masteries', vid=148, vname='Increased Speed', name='Increased Speed', row=3, col=1, prereqs=['increased_stamina'], role='masteries', design='Increased Speed'),
    dict(slug='iron_skin', tree='masteries', vid=145, vname='Iron Skin', name='Iron Skin', row=3, col=3, prereqs=[], role='masteries', design='Iron Skin'),
    dict(slug='spear_mastery', tree='masteries', vid=136, vname='Spear Mastery', name='Venom Ward', row=4, col=3, prereqs=['iron_skin'], role='masteries', design='Venom Ward'),
    dict(slug='mace_mastery', tree='masteries', vid=129, vname='Mace Mastery', name='Battle Fervor', row=5, col=1, prereqs=['increased_speed'], role='masteries', design='Battle Fervor'),
    dict(slug='natural_resistance', tree='masteries', vid=153, vname='Natural Resistance', name='Natural Resistance', row=6, col=3, prereqs=['spear_mastery'], role='masteries', design='Natural Resistance'),
    # ------------------------------------------------------------------ WARCRIES
    dict(slug='shout', tree='warcries', vid=138, vname='Shout', name='Shout', row=1, col=1, prereqs=[], role='warcries', design='Shout'),
    dict(slug='find_item', tree='warcries', vid=142, vname='Find Item', name='Enduring Cry', row=1, col=3, prereqs=[], role='warcries', design='Enduring Cry'),
    dict(slug='taunt', tree='warcries', vid=137, vname='Taunt', name='Taunt', row=2, col=2, prereqs=[], role='warcries', design='Taunt'),
    dict(slug='howl', tree='warcries', vid=130, vname='Howl', name='Howl', row=3, col=2, prereqs=['taunt'], role='warcries', design='Howl'),
    dict(slug='find_potion', tree='warcries', vid=131, vname='Find Potion', name='Second Wind', row=3, col=3, prereqs=['find_item'], role='warcries', design='Second Wind'),
    dict(slug='battle_command', tree='warcries', vid=155, vname='Battle Command', name='Battle Command', row=4, col=1, prereqs=['shout'], role='warcries', design='Battle Command'),
    dict(slug='battle_cry', tree='warcries', vid=146, vname='Battle Cry', name='Battle Cry', row=4, col=2, prereqs=['howl'], role='warcries', design='Battle Cry'),
    dict(slug='battle_orders', tree='warcries', vid=149, vname='Battle Orders', name='Battle Orders', row=5, col=1, prereqs=['battle_command'], role='warcries', design='Battle Orders'),
    dict(slug='grim_ward', tree='warcries', vid=150, vname='Grim Ward', name='Bloodlust', row=5, col=3, prereqs=['find_potion'], role='warcries', design='Bloodlust'),
    dict(slug='war_cry', tree='warcries', vid=154, vname='War Cry', name='War Cry', row=6, col=2, prereqs=['battle_orders', 'battle_cry', 'grim_ward'], role='warcries', design='War Cry'),
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

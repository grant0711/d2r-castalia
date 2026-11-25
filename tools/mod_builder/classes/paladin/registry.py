"""
Paladin 1:1 skill map (single source of truth for layout, names, prereqs & design).
"""

TIER_LEVELS = [1, 8, 16, 24, 32, 40]
PAGE = {'combat': 1, 'offensive': 2, 'defensive': 3}

SLOTS = [
    # ------------------------------------------------------------------ COMBAT
    dict(slug='sacrifice', tree='combat', vid=96, vname='Sacrifice', name='Sacrifice', row=1, col=1, prereqs=[], role='combat', design='Sacrifice'),
    dict(slug='smite', tree='combat', vid=97, vname='Smite', name='Smite', row=1, col=3, prereqs=[], role='combat', design='Smite'),
    dict(slug='holy_bolt', tree='combat', vid=101, vname='Holy Bolt', name='Holy Bolt', row=2, col=2, prereqs=[], role='combat', design='Holy Bolt'),
    dict(slug='zeal', tree='combat', vid=106, vname='Zeal', name='Zeal', row=3, col=1, prereqs=['sacrifice'], role='combat', design='Zeal'),
    dict(slug='charge', tree='combat', vid=107, vname='Charge', name='Charge', row=3, col=3, prereqs=['smite'], role='combat', design='Charge'),
    dict(slug='vengeance', tree='combat', vid=111, vname='Vengeance', name='Vengeance', row=4, col=1, prereqs=['zeal'], role='combat', design='Vengeance'),
    dict(slug='blessed_hammer', tree='combat', vid=112, vname='Blessed Hammer', name='Blessed Hammer', row=4, col=2, prereqs=['holy_bolt'], role='combat', design='Blessed Hammer'),
    dict(slug='conversion', tree='combat', vid=116, vname='Conversion', name='Conversion', row=5, col=1, prereqs=['vengeance'], role='combat', design='Conversion'),
    dict(slug='holy_shield', tree='combat', vid=117, vname='Holy Shield', name='Holy Shield', row=5, col=3, prereqs=['charge', 'blessed_hammer'], role='combat', design='Holy Shield'),
    dict(slug='fist_of_the_heavens', tree='combat', vid=121, vname='Fist of the Heavens', name='Fist of the Heavens', row=6, col=2, prereqs=['blessed_hammer', 'conversion'], role='combat', design='Fist of the Heavens'),
    # ------------------------------------------------------------------ OFFENSIVE
    dict(slug='might', tree='offensive', vid=98, vname='Might', name='Might', row=1, col=1, prereqs=[], role='offensive', design='Might'),
    dict(slug='holy_fire', tree='offensive', vid=102, vname='Holy Fire', name='Holy Fire', row=2, col=2, prereqs=['might'], role='offensive', design='Holy Fire'),
    dict(slug='thorns', tree='offensive', vid=103, vname='Thorns', name='Thorns', row=2, col=3, prereqs=[], role='offensive', design='Thorns'),
    dict(slug='blessed_aim', tree='offensive', vid=108, vname='Blessed Aim', name='Blessed Aim', row=3, col=1, prereqs=['might'], role='offensive', design='Blessed Aim'),
    dict(slug='concentration', tree='offensive', vid=113, vname='Concentration', name='Concentration', row=4, col=1, prereqs=['blessed_aim'], role='offensive', design='Concentration'),
    dict(slug='holy_freeze', tree='offensive', vid=114, vname='Holy Freeze', name='Holy Freeze', row=4, col=2, prereqs=['holy_fire'], role='offensive', design='Holy Freeze'),
    dict(slug='holy_shock', tree='offensive', vid=118, vname='Holy Shock', name='Holy Shock', row=5, col=2, prereqs=['holy_freeze'], role='offensive', design='Holy Shock'),
    dict(slug='sanctuary', tree='offensive', vid=119, vname='Sanctuary', name='Sanctuary', row=5, col=3, prereqs=['thorns', 'holy_freeze'], role='offensive', design='Sanctuary'),
    dict(slug='fanaticism', tree='offensive', vid=122, vname='Fanaticism', name='Fanaticism', row=6, col=1, prereqs=['concentration'], role='offensive', design='Fanaticism'),
    dict(slug='conviction', tree='offensive', vid=123, vname='Conviction', name='Conviction', row=6, col=3, prereqs=['sanctuary'], role='offensive', design='Conviction'),
    # ------------------------------------------------------------------ DEFENSIVE
    dict(slug='prayer', tree='defensive', vid=99, vname='Prayer', name='Prayer', row=1, col=1, prereqs=[], role='defensive', design='Prayer'),
    dict(slug='resist_fire', tree='defensive', vid=100, vname='Resist Fire', name='Resist Fire', row=1, col=3, prereqs=[], role='defensive', design='Resist Fire'),
    dict(slug='defiance', tree='defensive', vid=104, vname='Defiance', name='Defiance', row=2, col=2, prereqs=[], role='defensive', design='Defiance'),
    dict(slug='resist_cold', tree='defensive', vid=105, vname='Resist Cold', name='Resist Cold', row=2, col=3, prereqs=[], role='defensive', design='Resist Cold'),
    dict(slug='cleansing', tree='defensive', vid=109, vname='Cleansing', name='Cleansing', row=3, col=1, prereqs=['prayer'], role='defensive', design='Cleansing'),
    dict(slug='resist_lightning', tree='defensive', vid=110, vname='Resist Lightning', name='Resist Lightning', row=3, col=3, prereqs=[], role='defensive', design='Resist Lightning'),
    dict(slug='vigor', tree='defensive', vid=115, vname='Vigor', name='Vigor', row=4, col=2, prereqs=['cleansing', 'defiance'], role='defensive', design='Vigor'),
    dict(slug='meditation', tree='defensive', vid=120, vname='Meditation', name='Meditation', row=5, col=1, prereqs=['cleansing'], role='defensive', design='Meditation'),
    dict(slug='redemption', tree='defensive', vid=124, vname='Redemption', name='Redemption', row=6, col=2, prereqs=['vigor'], role='defensive', design='Redemption'),
    dict(slug='salvation', tree='defensive', vid=125, vname='Salvation', name='Salvation', row=6, col=3, prereqs=[], role='defensive', design='Salvation'),
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

# Castalia — Developer Architecture & Pipeline Handbook

This document provides a technical orientation for developers working on **Castalia** (`/home/grant/games/d2r`). Everything in the mod is generated deterministically from pristine vanilla tables (`vanilla-reference/`) into `my-mod/data/`, verified by an automated invariant suite (`tools/mod_builder/verify.py`), and published to the strategy guide website (`docs/site/index.html`).

---

## 1. Repository Layout

```text
/home/grant/games/d2r/
├── README.md                           # High-level overview, 7 Horadric Cube recipes & build command
├── bin/                                # Executable CLI entrypoints
│   ├── d2r-build-mod.py                # Master pure-function build & verification pipeline
│   ├── d2r-sorc                        # Interactive one-skill-at-a-time experiment CLI
│   └── d2r-reset-sorc.py               # Offline test character (.d2s) respec & level utility
├── assets/                             # Custom source artwork (white-on-black silhouettes & item icons)
│   ├── skill_icons/                    # Custom skill icon silhouettes stamped onto class icon sprites
│   └── items/                          # Custom Lockbox, Key, and Preparation Elixir artwork
├── tools/
│   ├── build_site.py                   # Data-driven Arreat Summit website & JS skill calculator generator
│   └── mod_builder/                    # Pure-function data transformation modules
│       ├── common.py                   # TSV/JSON readers/writers, config loader, HD missile JSON helper
│       ├── mod_config.json             # Tunable global parameters
│       ├── verify.py                   # 8-suite invariant verification harness
│       ├── skills.py                   # Thin orchestrator delegating to classes/*
│       ├── classes/                    # Unified per-class skill, missile, sprite & animation packages
│       │   ├── common.py               # Shared formulas (RAMP12/34/56), states.txt, animdata.d2, pettype.txt
│       │   ├── paladin/                # Paladin 30-skill overhaul (skills.py, sprites.py)
│       │   ├── barbarian/              # Barbarian 30-skill Stamina Pendulum overhaul (skills.py, sprites.py)
│       │   ├── assassin/               # Assassin 30-skill Charge-Up/Sentry/Blade overhaul (skills.py, sprites.py)
│       │   └── sorceress/              # Bridges mod_builder.sorc (registry, engine, patterns, tree, icons, specs/)
│       ├── sorc/                       # Sorceress declarative experiment engine & compacted specs/*.json
│       ├── affixes.py                  # Magic/Rare/Crafted affix pruning, levelreq calibration, itemstatcost.txt
│       ├── cubemain.py                 # 7 Horadric Cube recipe families (~271,000 rows)
│       ├── gamble_npc.py               # Act-partitioned vendor inventory & gamble tables
│       ├── gems_runes.py               # 7 Gem/Skull families & 33 Semantic Runes (gems.txt, item-runes.json)
│       ├── itemratio.py                # Drop quality ratios (100% Magic+ equipment floor)
│       ├── itemtypes_automagic.py      # Automagic pools, 10-slot mercenary equ=1, quiver magic/rare support
│       ├── lockboxes.py                # 536 Unique/Set Lockbox item codes & key sprite generators
│       ├── misc_items.py               # Potions, Preparation Elixirs, Keys, Maluses, Gem levelreqs (misc.txt)
│       ├── monsters.py                 # 4 Monster Archetypes, resistance cap (99%), 10-slot merc AI & kits
│       ├── treasureclass.py            # Treasure class hierarchy, Gem tier progression, Skeleton skull bias
│       ├── unique_sets.py              # Locked Unique/Set/Boss Charm tables (tools/mod_builder/locked_tables/)
│       └── weapons_armor.py            # Weapon/Armor base balance, repair costs, Circlet reqs, missiles.txt
├── docs/
│   ├── ARCHITECTURE.md                 # This developer handbook
│   ├── engine_reference/               # Technical reference for D2R server/client functions & class mechanics
│   │   ├── README.md                   # Master lookup tables for skills.txt & missiles.txt functions
│   │   ├── paladin_auras_and_combat.md # Paladin Aura Mana Upkeep, Frontal Cleave Vengeance & Chain Hammer
│   │   ├── barbarian_stamina_mechanics.md # Barbarian Stamina Pendulum & Ancients escalation hooks
│   │   ├── assassin_charges_and_traps.md  # Assassin 15m Combo Orbs & srvstfunc=39 selective trap release
│   │   └── sorceress_stances_and_spells.md # Sorceress group=13 Stances, Stance Markers, Fizzle & 7 Archetypes
│   ├── sorc/                           # Sorceress status dashboard (STATUS.md) & per-skill experiment logs
│   └── site/                           # Auto-generated strategy guide & interactive skill calculator (index.html)
├── vanilla-reference/                  # Read-only pristine D2R extracted tables and sprites
└── my-mod/                             # Compiled mod output symlinked into D2R's mods/custom/custom.mpq
```

---

## 2. The Pure-Function Build & Verification Pipeline

Never hand-edit files inside `my-mod/data/`. Every file in `my-mod/data/` is deterministically generated from `vanilla-reference/` by running:

```bash
python3 /home/grant/games/d2r/bin/d2r-build-mod.py
```

You can also rebuild individual steps (which always run the full `verify.py` invariant suite and regenerate `docs/site/index.html` afterward):

```bash
python3 /home/grant/games/d2r/bin/d2r-build-mod.py skills
python3 /home/grant/games/d2r/bin/d2r-build-mod.py gems cubemain
```

### How `tools/build_site.py` Eliminates Documentation Drift
- `tools/build_site.py` contains **zero hardcoded skill descriptions, rune stats, or gem stats**.
- Instead, it reads the compiled `.txt` and `.json` files in `my-mod/data/` (`skills.txt`, `skilldesc.txt`, `missiles.txt`, `gems.txt`, `misc.txt`, `properties.txt`, `itemstatcost.txt`, `skills.json`, `item-modifiers.json`, `item-runes.json`), composites the in-game stone skill tree plates (`img/trees/<cls>_frame_0..2.png`), and embeds a real-time JavaScript D2R integer formula evaluator into `docs/site/index.html`.
- Whenever a skill formula, synergy, gem, or rune is changed in Python or JSON specs, running `d2r-build-mod.py` or `d2r-sorc build` automatically updates the website and interactive skill calculator.

---

## 3. Iterating on Class Skills (`bin/d2r-sorc` & `tools/mod_builder/classes/`)

### Reference Commands (No Codebase Grepping Required)
Before implementing or modifying a skill, query the indexed server/client function catalog directly from the CLI:

```bash
# 1. View all 30 Sorceress skill slots, their vanilla row mappings, status, and active variant:
./bin/d2r-sorc map

# 2. Look up proven skills.txt (srvstfunc/srvdofunc/cltstfunc/cltdofunc) & missiles.txt functions:
./bin/d2r-sorc funcs
./bin/d2r-sorc funcs "166"

# 3. Look up the exact archetype pattern, stance marker, and cross-stance fizzle guard for a skill:
./bin/d2r-sorc patterns frost_dart

# 4. Inspect a single skill's design intent, active patch, and diff against vanilla:
./bin/d2r-sorc show frost_dart
```

### Controlled Experiment Loop
1. **Create or update a variant** in `tools/mod_builder/sorc/specs/<slug>.json` (or via `d2r-sorc variant` / `d2r-sorc set`).
2. **Activate & build**:
   ```bash
   ./bin/d2r-sorc use <slug> <variant>
   ./bin/d2r-sorc build
   ```
3. **Log observations & compact**:
   ```bash
   ./bin/d2r-sorc log <slug> "Verified in game: ..."
   ./bin/d2r-sorc status <slug> done
   ./bin/d2r-sorc compact <slug>
   ```
   Running `d2r-sorc compact` prunes obsolete inactive variants from `specs/<slug>.json` (keeping `"baseline"` and the active variant) so spec files stay under `~4 KB` and never saturate context windows.

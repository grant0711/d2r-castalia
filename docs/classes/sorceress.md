# Sorceress — Elemental Stances, Cross-Tree Passives & Spell Archetypes

- **Status:** **30 / 30 Done** (Fire 10/10, Lightning 10/10, Cold 10/10 — all 30 skills complete & verified!)
- **Declarative Specs:** [`tools/mod_builder/classes/sorceress/`](file:///home/grant/games/d2r/tools/mod_builder/classes/sorceress) (`registry.py`, `engine.py`, `patterns.py`, `tree.py`, `icons.py`, `statemachine.py`, `state.json`, `specs/*.json`)
- **CLI:** `./bin/d2r-class sor <map|show|patterns|funcs|variant|set|use|build|test|compact>`

---

## 1. Fast CLI Loop (`bin/d2r-sorc`)

```bash
# View live 30-slot map, status (30 / 30 done), and active variants:
./bin/d2r-sorc map [fire|cold|lightning]

# Inspect engine functions, parallel patterns, or skill diffs:
./bin/d2r-sorc patterns <slug>
./bin/d2r-sorc funcs [query]
./bin/d2r-sorc show <slug>

# Iterate, test formulas/stances, build, and prune obsolete variants:
./bin/d2r-sorc use <slug> <variant>
./bin/d2r-sorc test [slug]
./bin/d2r-sorc build
./bin/d2r-sorc compact <slug>
```

---

## 2. Hard Engine & Design Contracts

1. **1:1 Vanilla Row Reuse + Tier-Contiguous Final IDs:** Reuse the 30 vanilla `charclass="sor"` rows (`vid` `36..65`) 1:1; never add a 31st `charclass="sor"` row. Helper skills in `specs/_shared.json` must clear `"charclass": ""`. [`skill_order.py`](file:///home/grant/games/d2r/tools/mod_builder/skill_order.py) tier-sorts final IDs at write time so `automagic.txt` stays `< 2048` rows; always author against source `vid`/`vname`.
2. **Skill Tab Progression Order:** Tabs run left-to-right **Fire (Page 3, Frame 0) $\rightarrow$ Cold (Page 2, Frame 1) $\rightarrow$ Lightning (Page 1, Frame 2)**, mirroring Stance unlock levels (`Conflagration` Lvl 16 $\rightarrow$ `Cryostasis` Lvl 24 $\rightarrow$ `Overcharge` Lvl 32).
3. **Stance Detection Markers (`group = 13`, `srvdofunc = 18`):**
   - **Conflagration** (Fire, `sorc_stance_fire`): `stat('skill_handofathena'.accr) > 0`
   - **Cryostasis** (Cold, `sorc_stance_cold`): `stat('skill_frenzy'.accr) > 0`
   - **Overcharge** (Lightning, `sorc_stance_light`): `stat('skill_decrepify'.accr) > 0`
4. **Cross-Stance Fizzle Contract:** Casting any offensive spell while an **opposing** stance is active must fizzle immediately (`Range = 1` or `0`, `Radius = 0`).
5. **Hard Stance Gating on Mobility Skills:** `Blaze` (`flashfire`), `Avalanche` (`glacier_step`), and `Blink` (`phase_step`) set `"restrict": "2"` + `State1 = sorc_stance_<tree>`.
6. **Engine Pitfall (`srvdofunc = 166` Blink):** The warp's `ExplosionMissile` (hitfunc 42) spawns on the **client only**. Server-side path effects must use the trail-dropper (`pSrvDoFunc = 2` -> `SubMissile1`). See [`docs/engine/STATS_AND_PITFALLS.md`](file:///home/grant/games/d2r/docs/engine/STATS_AND_PITFALLS.md).
7. **Zero Elemental Pierce:** No player skill or passive may grant `passive_*_pierce`.
8. **Tooltip Next-Level Rule:** Use `lvl` (or `clc1..6` referencing `lvl`) in `skilldesc.txt` so the "Next Level" panel shifts to `lvl + 1`.

---

## 3. Core Mechanics: Stances, Cross-Tree Passives, `sorc_tempo` & Conduction

### Mutually Exclusive Elemental Stances (`srvdofunc = 18`, `group = 13`)

| Tree | Stance (`slug` $\rightarrow$ Row) | State | Marker (`aurastat6 = 1`) | Boons (`Lvl 1 -> 20`) | Busts (`Lvl 1 -> 20`) | Melee Retaliation (`damagedinmelee`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fire** | **Conflagration** (`conflagration` $\rightarrow$ `Enchant` 52, Lvl 16) | `sorc_stance_fire` | `skill_handofathena` | `+5% -> +30%` Fire Dmg, `+5% -> +40%` FCR, `+15% -> +110%` Mana Regen | `+3% -> +25%` Phys Dmg Taken | `auraeventfunc1 = 3` (Fire retaliation) |
| **Cold** | **Cryostasis** (`cryostasis` $\rightarrow$ `Frozen Armor` 40, Lvl 24) | `sorc_stance_cold` | `skill_frenzy` | `+5% -> +30%` Cold Dmg, `+3% -> +25%` Phys DR, `+10% -> +200%` Defense | `-5% -> -30%` FRW, `-5% -> -20%` FCR | `auraeventfunc1 = 2` (Freezes melee attacker) |
| **Ltng** | **Overcharge** (`overcharge` $\rightarrow$ `Energy Shield` 58, Lvl 32) | `sorc_stance_light` | `skill_decrepify` | `+5% -> +30%` Ltng Dmg, `+5% -> +40%` FRW, `+5% -> +40%` FHR, `+5% -> +40%` FBR | `-10% -> -100%` Defense | `auraeventfunc1 = 3` (Lightning retaliation) |

- All three stances use `anim = "SQ"`, `seqtrans = "SC"`, bound via `statemachine.py` to `PLRMODE_SEQUENCE` (`modeId = 18`).

### Unified Tri-Elemental Monster State (`sorc_tempo`, `curse = ""`)
All three trees share a single invisible monster state (`sorc_tempo`, applied via `pSrvHitFunc = 4` $\rightarrow$ `pSrvDoFunc = 14 / Param2 = 30`) so cross-element hits cleanly overwrite each other without colliding with Necromancer curses or Assassin `Shadow Bind`:
- **Fire (`1.00×` DPS baseline — Melee Support):** `-5% -> -20%` Physical Resist (`damageresist`, cap `-25%`) for `4.0s` (`100` frames).
- **Cold (`0.85×` DPS — Premier CC):** `-5% -> -15%` FRW/IAS (cap `-20%`), `-10% -> -20%` FCR (cap `-25%`), `-10% -> -30%` FHR (cap `-35%`) for a fixed `9.0s` (`225` frames) gradual thaw.
- **Lightning (`1.15×` DPS — Peak Damage):** `+20% -> +40%` FRW/IAS, `+40% -> +80%` FHR supercharge for `3.0s` (`75` frames).

### Cross-Tree Passives & Radiating Co-op Conduction
- **Expansion** (`kindling` $\rightarrow$ `Warmth` 37, Fire R4C2, Lvl 24): Logistic S-curve AoE/explosion radius bonus (up to `+50%`, stored in `ironmaiden_level`).
- **Stasis** (`brittle_touch` $\rightarrow$ `Shiver Armor` 50, Cold R4C1, Lvl 24): Logistic S-curve lingering duration bonus (up to `+100%`, stored in `conversion_maxhp`).
- **Arc** (`conduction` $\rightarrow$ `Telekinesis` 43, Lightning R2C2, Lvl 8): Logistic S-curve projectile range bonus (up to `+75%`, stored in `lifetap_level`) + `+1` bonus chain/bolt every 6 levels (cap `+3`, stored in `conversion_level`).
- **Sustain Passives:** **Warmth** (`ignition` $\rightarrow$ `Fire Mastery` 61, `+20% -> +172%` Mana Recovery Rate) and **Equilibrium** (`Cold Mastery` 65, `+2 -> +30` MAEK).
- **Conduction** (`afterglow` $\rightarrow$ `Lightning Mastery` 63, Lightning R6C1, Lvl 40): Radiating party stance transfer (`srvdofunc = 22` Nova ring $\rightarrow$ `conduction_wave` cloned from `battleorders` with `CollideFriend = 1`, `pSrvHitFunc = 18`, `InTown = ""`). Transfers active stance elemental damage (capped at `+30%`) plus **Expansion / Stasis / Arc** onto all nearby allies and hirelings via `sorc_conduction` (`target0`, `target1`, `goldlost`) while **never self-applying to the caster** (zero solo double-dipping; 2-Sorceress co-op conduction supported).

---

## 4. The 7 Reusable Spell Archetypes & 60-pt / 100-pt Build Split

Each tree supports a **60-pt Hybrid** combo (`~0.80×` of same-tree Capstone) and a **100-pt Specialist** build culminating in the Level 40 Capstone:

| Slot Role | Fire (`1.00×`, `10/10`) | Cold (`0.85×`, `10/10`) | Lightning (`1.15×`, `10/10`) | `skills.txt` Functions |
| :--- | :--- | :--- | :--- | :---: |
| **1. Line 1 (Lvl 1)** | **Fire Bolt** (`Fire Bolt` 36) | **Ice Bolt** (`Ice Bolt` 39) | **Static Lance** (`Lightning` 49) | `1 / 1` |
| **2. AoE 1 (Lvl 8)** | **Pyroclasm** (`Fire Ball` 47) | **Frost Nova** (`Frost Nova` 44) | **Nova** (`Nova` 48) | `154 / 99` or `22 / 25` |
| **3. Combo CC/AoE (60-pt)** | **Backdraft** (`Fire Wall` 51) | **Permafrost** (`Ice Blast` 45) | **Sunderbolt** (`Static Field` 42) | `14+28 / 17+28` or `80 / 36` |
| **4. Mobility Utility** | **Blaze** (`Blaze` 46) | **Avalanche** (`Chilling Armor` 60) | **Blink** (`Teleport` 54) | `23 / -` or `166 / 104` |
| **5. AoE 2 (60-pt)** | **Meteor** (`Meteor` 56) | **Blizzard** (`Blizzard` 59) | **Stormcall** (`Thunder Storm` 57) | `28 / 28` |
| **6. Line 2 (100-pt)** | **Brimstone Lance** (`Inferno` 41) | **Icicle Spear** (`Glacial Spike` 55) | **Spearbolt** (`Chain Lightning` 53) | `1 / 1` (wake / chain) |
| **7. Capstone (100-pt, Lvl 40)** | **Hydra** (`Hydra` 62) | **Frozen Orb** (`Frozen Orb` 64) | **Thunder Storm** (`Charged Bolt` 38) | `14+144 / 17`, `1 / 29`, `13+29` |

---

<!-- AUTO-GENERATED-SPECS:START -->
## Live Skill Matrix (`30 / 30 done` — Auto-Generated from JSON Specs & Compiled Tables)

> **Do not hand-edit this section.** Generated automatically by `tools/mod_builder/classes/doc_gen.py` during `d2r-build-mod.py skills` from `tools/mod_builder/classes/sorceress/` and compiled `skills.txt`/`skills.json`.

### Fire (Page 3)

| r.c | Lvl | Skill (`slug`) | Status / Variant | Engine Hooks | In-Game Description |
| :---: | :---: | :--- | :--- | :--- | :--- |
| 1.1 | 1 | **Fire Bolt** (`cinder_lance`) | `done` / `test_fizzle` | `fire` `Conduction` | Hurls a bolt of flame against a single target / Bolts explode on impact while Conflagration is active |
| 2.1 | 8 | **Pyroclasm** (`pyroclasm`) | `done` / `test_fizzle` | `func -/154` `fire` `Conduction` | Unleashes a ring of fiery bolts / that knock enemies back |
| 2.3 | 8 | **Backdraft** (`backdraft`) | `done` / `test_fizzle` | `func 14/28` `CD 2s` `state:backdraft_slow` `fire` `Conduction` | Ignites a fiery vortex that draws enemies inward / before detonating in a blast |
| 3.2 | 16 | **Conflagration** (`conflagration`) | `done` / `final5` | `func -/18` `CD 3s` `state:sorc_stance_fire` `fire` | Stance / Wreathe yourself in flame, empowering fire spells, cast speed, / and mana recovery at the cost of physical vulnerability / Only one stance may be active at a time |
| 3.3 | 16 | **Blaze** (`flashfire`) | `done` / `final1` | `func -/23` `CD 8s` `req:sorc_stance_fire` `state:blaze` `fire` | Requires Conflagration to cast / Sprint forward, leaving a trail of flame |
| 4.2 | 24 | **Expansion** (`kindling`) | `done` / `final2` | `passive` `fire` | Passive / Increases the area of effect radius of all Sorceress spells |
| 4.3 | 24 | **Meteor** (`skyfall`) | `done` / `test_fizzle` | `func -/28` `CD 1.2s` `state:sorc_tempo` `fire` `Conduction` | Calls down a meteor on your target, / leaving a crater of flame |
| 5.1 | 32 | **Brimstone Lance** (`brimstone_lance`) | `done` / `test_fizzle` | `func -/1` `state:sorc_tempo` `fire` `Conduction` | Hurls a heavy lance that pierces enemies / and leaves a fiery wake |
| 5.3 | 32 | **Warmth** (`ignition`) | `done` / `final2` | `passive` `fire` | Passive / Increases the rate at which you recover mana |
| 6.2 | 40 | **Hydra** (`pyre_hydra`) | `done` / `test_fizzle` | `func 14/144` `state:sorc_tempo` `fire` `Conduction` | Summons fire-spewing hydra heads / that bombard nearby enemies |

### Cold (Page 2)

| r.c | Lvl | Skill (`slug`) | Status / Variant | Engine Hooks | In-Game Description |
| :---: | :---: | :--- | :--- | :--- | :--- |
| 1.2 | 1 | **Ice Bolt** (`frost_dart`) | `done` / `final1` | `cold` `Conduction` | Hurls a bolt of ice that chills its target / Bolts explode on impact while Cryostasis is active |
| 2.2 | 8 | **Frost Nova** (`hoarfrost_burst`) | `done` / `final1` | `func -/22` `state:sorc_tempo` `cold` `Conduction` | Unleashes an expanding ring of frost / that chills nearby enemies |
| 3.1 | 16 | **Permafrost** (`permafrost`) | `done` / `final1` | `func 14/28` `CD 2s` `state:sorc_tempo` `cold` `Conduction` | Freezes the ground at the target location, / slowing enemies before shattering in a blast |
| 3.3 | 16 | **Equilibrium** (`equilibrium`) | `done` / `final1` | `passive` | Passive / Restores mana after each enemy you kill |
| 4.1 | 24 | **Stasis** (`brittle_touch`) | `done` / `final2` | `passive` | Passive / Extends the duration of lingering Sorceress spells and stances |
| 4.2 | 24 | **Cryostasis** (`cryostasis`) | `done` / `final5` | `func -/18` `CD 3s` `state:sorc_stance_cold` | Stance / Encase yourself in frost, boosting cold damage, defense, / and physical resistance at the cost of speed / Only one stance may be active at a time |
| 4.3 | 24 | **Avalanche** (`glacier_step`) | `done` / `avalanche1` | `func -/23` `CD 8s` `req:sorc_stance_cold` `state:blaze` `frze` `RF:8` | Requires Cryostasis to cast / Surge forward, knocking back and freezing nearby foes |
| 5.1 | 32 | **Blizzard** (`whiteout`) | `done` / `final1` | `func -/28` `CD 1.6s` `state:sorc_tempo` `cold` `Conduction` | Calls down a raging snowstorm / that chills and bombards enemies |
| 5.3 | 32 | **Icicle Spear** (`icicle_spear`) | `done` / `final1` | `func -/1` `state:sorc_tempo` `frze` `Conduction` | Hurls a heavy ice lance that pierces enemies / and leaves a freezing wake |
| 6.2 | 40 | **Frozen Orb** (`frozen_orb`) | `done` / `singularity1` | `CD 1.48s` `state:sorc_tempo` `cold` | Launches a spinning orb that hovers in place, / spraying piercing shards before detonating in a frost ring |

### Lightning (Page 1)

| r.c | Lvl | Skill (`slug`) | Status / Variant | Engine Hooks | In-Game Description |
| :---: | :---: | :--- | :--- | :--- | :--- |
| 1.3 | 1 | **Static Lance** (`static_lance`) | `done` / `p1_static_lance` | `func -/1` `state:sorc_tempo` `ltng` `Conduction` | Hurls a fast bolt of lightning / Bolts explode on impact while Overcharge is active |
| 2.1 | 8 | **Nova** (`pulse_ring`) | `done` / `final1` | `func -/22` `state:sorc_tempo` `ltng` `Conduction` | Unleashes an expanding ring of lightning / around you |
| 2.2 | 8 | **Arc** (`conduction`) | `done` / `final2` | `passive` | Passive / Increases the range of Sorceress projectiles / and adds bonus chains or bolts |
| 3.3 | 16 | **Sunderbolt** (`tesla_field`) | `done` / `final1` | `func -/80` `CD 2s` `state:terror` `ltng` `Conduction` | Calls down a bolt of lightning on a target, / scattering nearby foes and leaving a shock field |
| 4.1 | 24 | **Stormcall** (`stormcall`) | `done` / `p9_consistent_nova_damage` | `func -/28` `CD 1.6s` `state:sorc_tempo` `ltng` `Conduction` | Calls down a violent lightning storm / across the target area |
| 4.3 | 24 | **Spearbolt** (`spearbolt`) | `done` / `p13_snappy_shock_wake` | `func -/1` `state:sorc_tempo` `ltng` `Conduction` | Hurls a lightning spear that leaves a shock wake / and erupts into chaining arcs on impact |
| 5.2 | 32 | **Overcharge** (`overcharge`) | `done` / `final5` | `func -/18` `CD 3s` `state:sorc_stance_light` `ltng` | Stance / Become supercharged, boosting lightning damage and speed / at the cost of reduced defense / Only one stance may be active at a time |
| 5.3 | 32 | **Blink** (`phase_step`) | `done` / `p10_scaling_frenzy` | `func -/166` `CD 1.52s` `req:sorc_stance_light` `state:sorc_tempo` `ltng` | Requires Overcharge to cast / Blink to a location, shocking foes in your path |
| 6.1 | 40 | **Conduction** (`afterglow`) | `done` / `final1` | `func -/22` `CD 1s` `req:sorc_stance_fire` `state:sorc_conduction` | Requires an active stance / Radiates your active stance element onto nearby allies and hirelings |
| 6.3 | 40 | **Thunder Storm** (`heavens_wrath`) | `done` / `p6_stance_cancel` | `func 13/29` `CD 11s` `state:thunderstorm` `ltng` `Conduction` | Summons a storm around you that calls down / chaining lightning bolts on nearby enemies |

### Shared Helpers (`specs/_shared.json` — variant `anim_v3`)

- **Helper Skills (`skills.txt`):** `Blaze`, `Blizzard`, `Chain Lightning`, `Charged Bolt`, `Chilling Armor`, `Cold Mastery`, `Enchant`, `Energy Shield`, `Fire Ball`, `Fire Bolt`, `Fire Mastery`, `Fire Wall`, `Frost Nova`, `Frozen Armor`, `Frozen Orb`, `Glacial Spike`, `Hydra`, `Ice Blast`, `Ice Bolt`, `Inferno`, `Lightning`, `Lightning Mastery`, `Meteor`, `Nova`, `Shiver Armor`, `Static Field`, `Telekinesis`, `Teleport`, `Thunder Storm`, `Warmth`
- **Shared States (`states.txt`):** `sorc_stance_cold`, `sorc_stance_fire`, `sorc_stance_light`, `sorc_tempo`
- **Shared/Custom Missiles (`missiles.txt`):** `cold_tempo_pulse`
- **HD Missile Bindings (`missiles.json`):** `cold_tempo_pulse`

<!-- AUTO-GENERATED-SPECS:END -->

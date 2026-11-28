# Sorceress — Elemental Stances, Cross-Tree Passives & Spell Archetypes

- **Status:** **30 / 30 Done** (Fire 10/10, Lightning 10/10, Cold 10/10 — all 30 skills complete & verified!)
- **Declarative Specs:** [`tools/mod_builder/classes/sorceress/`](file:///home/grant/games/d2r/tools/mod_builder/classes/sorceress) (`registry.py`, `engine.py`, `patterns.py`, `tree.py`, `icons.py`, `statemachine.py`, `state.json`, `specs/*.json`)
- **CLI:** `./bin/d2r-class sor <map|show|patterns|funcs|variant|set|use|build|test|compact>`

---

## 1. Fast CLI Loop (`bin/d2r-sorc`)

```bash
# View live 30-slot map, status (24 done, 6 stub), and active variants:
./bin/d2r-sorc map [fire|lightning|cold]

# Look up proven engine functions & parallel Fire archetype for the next Cold skill:
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
2. **Stance Detection Markers (`group = 13`, `srvdofunc = 18`):**
   - **Conflagration** (Fire, `sorc_stance_fire`): `stat('skill_handofathena'.accr) > 0`
   - **Cryostasis** (Cold, `sorc_stance_cold`): `stat('skill_frenzy'.accr) > 0`
   - **Overcharge** (Lightning, `sorc_stance_light`): `stat('skill_decrepify'.accr) > 0`
3. **Cross-Stance Fizzle Contract:** Casting any offensive spell while an **opposing** stance is active must fizzle immediately (`Range = 1` or `0`, `Radius = 0`).
4. **Hard Stance Gating on Mobility Skills:** `flashfire`, `glacier_step`, and `phase_step` set `"restrict": "2"` + `State1 = sorc_stance_<tree>`.
5. **Engine Pitfall (`srvdofunc = 166` Blink):** The warp's `ExplosionMissile` (hitfunc 42) spawns on the **client only**. Server-side path effects must use the trail-dropper (`pSrvDoFunc = 2` -> `SubMissile1`). See [`docs/engine/STATS_AND_PITFALLS.md`](file:///home/grant/games/d2r/docs/engine/STATS_AND_PITFALLS.md).
6. **Zero Elemental Pierce:** No player skill or passive may grant `passive_*_pierce`.
7. **Tooltip Next-Level Rule:** Use `lvl` (or `clc1..6` referencing `lvl`) in `skilldesc.txt` so the "Next Level" panel shifts to `lvl + 1`.

---

## 3. Core Mechanics: Stances, Cross-Tree Passives & Conduction

### Mutually Exclusive Elemental Stances (`srvdofunc = 18`, `group = 13`)

| Tree | Stance (`slug` $\rightarrow$ Row) | State | Marker (`aurastat6 = 1`) | Boons (`Lvl 1 -> 20`) | Busts (`Lvl 1 -> 20`) | Melee Retaliation (`damagedinmelee`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fire** | **Conflagration** (`conflagration` $\rightarrow$ `Enchant` 52) | `sorc_stance_fire` | `skill_handofathena` | `+5% -> +30%` Fire Dmg, `+5% -> +40%` FCR, `+15% -> +110%` Mana Regen | `+5% -> +50%` Phys Dmg Taken | `auraeventfunc1 = 3` (Fire retaliation) |
| **Cold** | **Cryostasis** (`cryostasis` $\rightarrow$ `Frozen Armor` 40) | `sorc_stance_cold` | `skill_frenzy` | `+5% -> +30%` Cold Dmg, `+3% -> +25%` Phys DR, `+10% -> +200%` Defense | `-5% -> -30%` FRW, `-5% -> -20%` FCR | `auraeventfunc1 = 2` (Freezes melee attacker) |
| **Ltng** | **Overcharge** (`overcharge` $\rightarrow$ `Energy Shield` 58) | `sorc_stance_light` | `skill_decrepify` | `+5% -> +30%` Ltng Dmg, `+5% -> +40%` FRW, `+5% -> +40%` FHR, `+5% -> +40%` FBR | `-10% -> -100%` Defense | `auraeventfunc1 = 3` (Lightning retaliation) |

- All three stances use `anim = "SQ"`, `seqtrans = "SC"`, bound via `statemachine.py` to `PLRMODE_SEQUENCE` (`modeId = 18`).

### Cross-Tree Passives & Co-op Conduction
- **Expansion** (`kindling` $\rightarrow$ `Warmth` 37, Fire R4C2, Lvl 24): Logistic S-curve AoE/explosion radius bonus (up to `+100%`, stored in `ironmaiden_level`).
- **Stasis** (`brittle_touch` $\rightarrow$ `Shiver Armor` 50, Cold R4C3, Lvl 24): Logistic S-curve lingering duration bonus (up to `+100%`, stored in `conversion_maxhp`).
- **Arc** (`conduction` $\rightarrow$ `Telekinesis` 43, Lightning R2C2, Lvl 8): Logistic S-curve projectile range bonus (up to `+75%`, stored in `lifetap_level`) + `+1` bonus chain/bolt every 6 levels (cap `+3`, stored in `conversion_level`).
- **Sustain Passives:** **Ignition** (`Fire Mastery` 61, `+30% -> +258%` Mana Recovery Rate) and **Equilibrium** (`Cold Mastery` 65, `+2 -> +30` MAEK).
- **Conduction** (`afterglow` $\rightarrow$ `Lightning Mastery` 63, Lightning R6C1, Lvl 40): Ally/hireling stance transfer (`srvdofunc = 25`, `TargetAlly = 1`, `TargetPet = 1`, `restrict = 2`). Transfers active stance elemental damage (capped at `+30%`, zero defensive boons/busts) plus **Expansion / Stasis / Arc** via `sorc_conduction` (`aurastat4 = target0 = stance*1000 + Expansion`, `aurastat5 = target1 = 1 + Stasis`, `aurastat6 = goldlost = 1 + Arc`; all 6 slots non-zero so stance swaps overwrite cleanly).

### Lightning Tree Supercharge Theme
Lightning offensive spells supercharge struck monsters (`velocitypercent` & `attackrate` = `min(40, 18 + 2*lvl)`, `item_fastergethitrate` = `min(80, 36 + 4*lvl)` for 3s). Use **`pSrvHitFunc = 4`** + `HitSubMissile1 = <sigil_pulse>` on piercing/impact missiles so damage is preserved (`pSrvHitFunc = 11` suppresses direct damage).

---

## 4. The 7 Reusable Spell Archetypes

| Slot Role | Fire (`10/10 done`) | Lightning (`10/10 done`) | Cold (`4/10 done`) | `skills.txt` Functions |
| :--- | :--- | :--- | :--- | :---: |
| **1. Line 1 (Lvl 1)** | **Cinder Lance** (`Fire Bolt` 36) | **Static Lance** (`Lightning` 49) | *Frost Dart* (`Ice Bolt` 39) — **stub** | `1 / 1` |
| **2. AoE 1 (Lvl 8)** | **Pyroclasm** (`Fire Ball` 47) | **Pulse Ring** (`Nova` 48) | *Hoarfrost Burst* (`Frost Nova` 44) — **stub** | `154 / 99` or `22 / 25` |
| **3. Combo CC/AoE** | **Backdraft** (`Fire Wall` 51) | **Sunderbolt** (`Static Field` 42) | *Permafrost* (`Ice Blast` 45) — **stub** | `14+28 / 17+28` or `80 / 36` |
| **4. Mobility Utility** | **Flashfire** (`Blaze` 46) | **Phase Step** (`Teleport` 54) | **Glacier Step** (`Chilling Armor` 60) — **done** | `23 / -` or `166 / 104` |
| **5. AoE 2 (Power Spike)** | **Skyfall** (`Meteor` 56) | **Stormcall** (`Thunder Storm` 57) | *Whiteout* (`Blizzard` 59) — **stub** | `28 / 28` |
| **6. Line 2 (Boss Killer)** | **Brimstone Lance** (`Inferno` 41) | **Spearbolt** (`Chain Lightning` 53) | *Icicle Spear* (`Glacial Spike` 55) — **stub** | `1 / 1` (wake / chain) |
| **7. Capstone (Lvl 40)** | **Pyre Hydra** (`Hydra` 62) | **Heaven's Wrath** (`Charged Bolt` 38) | *Frozen Orb* (`Frozen Orb` 64) — **stub** | `14+144 / 17`, `13+29`, `1 / 29` |

---

## 5. Remaining Work: 6 Cold Tree Stubs

Run `./bin/d2r-sorc patterns <slug>` before implementing any skill below:

| Unlock | Grid | Skill (`slug`) | Vanilla Row (`*Id`) | Role | Parallel Template |
| :---: | :---: | :--- | :--- | :--- | :--- |
| **Lvl 1** | R1C2 | **Frost Dart** (`frost_dart`) | `Ice Bolt` (`39`) | Line 1 | Copy `cinder_lance.json` (`1/1`), scale velocity/chill + Cryostasis AoE frost burst. |
| **Lvl 8** | R2C2 | **Hoarfrost Burst** (`hoarfrost_burst`) | `Frost Nova` (`44`) | AoE 1 | Parallel to `pulse_ring.json` (`22/25`, `calc3`/`cltcalc1` velocity adder) or `pyroclasm.json` (`154/99`). |
| **Lvl 16** | R3C3 | **Permafrost** (`permafrost`) | `Ice Blast` (`45`) | Combo CC/AoE | Copy `backdraft.json` (`14+28 / 17+28`), cursor freeze/chill field scaled by **Expansion** & **Stasis**. |
| **Lvl 32** | R5C1 | **Whiteout** (`whiteout`) | `Blizzard` (`59`) | AoE 2 | Parallel to `skyfall.json` (`28/28`, `blizzardcenter`), cursor snowstorm expanded in Cryostasis. |
| **Lvl 32** | R5C3 | **Icicle Spear** (`icicle_spear`) | `Glacial Spike` (`55`) | Line 2 | Copy `brimstone_lance.json` (`1/1`, piercing + `pSrvDoFunc=2` freezing wake 10x longer in Cryostasis). |
| **Lvl 40** | R6C2 | **Frozen Orb** (`frozen_orb`) | `Frozen Orb` (`64`) | Capstone | Zero-CD Lvl 40 capstone (`1/29`, `pSrvDoFunc=16/pCltDoFunc=18`), Cryostasis empowerment + cross-stance fizzle. |

### Final Cold Tree Polish Checklist (Once All 30 Skills Are `done`)
1. Populate Cold `prereqs` in [`registry.py`](file:///home/grant/games/d2r/tools/mod_builder/classes/sorceress/registry.py) (`tree.py` auto-draws `soskilltree.sprite` arrows).
2. Audit Cold skill icons in [`icons.py`](file:///home/grant/games/d2r/tools/mod_builder/classes/sorceress/icons.py).
3. Run `./bin/d2r-sorc compact --all`, `python3 ./bin/d2r-build-mod.py`, and `python3 -m unittest -v`.

---

<!-- AUTO-GENERATED-SPECS:START -->
## Live Skill Matrix (`24 / 30 done` — Auto-Generated from JSON Specs & Compiled Tables)

> **Do not hand-edit this section.** Generated automatically by `tools/mod_builder/classes/doc_gen.py` during `d2r-build-mod.py skills` from `tools/mod_builder/classes/sorceress/` and compiled `skills.txt`/`skills.json`.

### Fire (Page 1)

| r.c | Lvl | Skill (`slug`) | Status / Variant | Engine Hooks | In-Game Description |
| :---: | :---: | :--- | :--- | :--- | :--- |
| 1.1 | 1 | **Cinder Lance** (`cinder_lance`) | `done` / `test_fizzle` | `fire` `Conduction` | Hurls a bolt of flame against a single target / Bolts explode on impact while Conflagration is active |
| 2.1 | 8 | **Pyroclasm** (`pyroclasm`) | `done` / `test_fizzle` | `func -/154` `fire` `Conduction` | unleashes a ring of fiery bolts that knock enemies back |
| 2.3 | 8 | **Backdraft** (`backdraft`) | `done` / `test_fizzle` | `func 14/28` `CD 2s` `state:backdraft_slow` `fire` `Conduction` | Ignites a fiery vortex that draws enemies inward / before detonating in a blast |
| 3.2 | 16 | **Conflagration** (`conflagration`) | `done` / `final5` | `func -/18` `CD 3s` `state:sorc_stance_fire` `fire` | Stance / Wreathe yourself in flame, empowering fire spells, cast speed, / and mana recovery at the cost of physical vulnerability / Only one stance may be active at a time |
| 3.3 | 16 | **Flashfire** (`flashfire`) | `done` / `final1` | `func -/23` `CD 8s` `req:sorc_stance_fire` `state:blaze` `fire` | Requires Conflagration to cast / Sprint forward, leaving a trail of flame |
| 4.2 | 24 | **Expansion** (`kindling`) | `done` / `final2` | `passive` `fire` | Passive / increases the area of effect radius of all Sorceress spells |
| 4.3 | 24 | **Skyfall** (`skyfall`) | `done` / `test_fizzle` | `func -/28` `CD 1.2s` `fire` `Conduction` | Calls down a meteor on your target, / leaving a crater of flame |
| 5.1 | 32 | **Brimstone Lance** (`brimstone_lance`) | `done` / `test_fizzle` | `func -/1` `fire` `Conduction` | Hurls a heavy lance that pierces enemies / and leaves a fiery wake |
| 5.3 | 32 | **Ignition** (`ignition`) | `done` / `final2` | `passive` `fire` | Passive / increases the rate at which you recover mana |
| 6.2 | 40 | **Pyre Hydra** (`pyre_hydra`) | `done` / `test_fizzle` | `func 14/144` `fire` `Conduction` | Summons fire-spewing hydra heads / that bombard nearby enemies |

### Lightning (Page 2)

| r.c | Lvl | Skill (`slug`) | Status / Variant | Engine Hooks | In-Game Description |
| :---: | :---: | :--- | :--- | :--- | :--- |
| 1.3 | 1 | **Static Lance** (`static_lance`) | `done` / `p1_static_lance` | `func -/1` `state:static_lance_frenzy` `ltng` `Conduction` | hurls a fast bolt of lightning whose velocity increases with level / overcharge: doubles range and erupts in a shock burst on impact |
| 2.1 | 8 | **Pulse Ring** (`pulse_ring`) | `done` / `final1` | `func -/22` `state:pulse_ring_frenzy` `ltng` `Conduction` | unleashes an expanding ring of lightning around you / overcharge: greatly increased ring radius |
| 2.2 | 8 | **Arc** (`conduction`) | `done` / `final2` | `passive` | Passive / increases the range of all Sorceress projectiles / and adds bonus chains or bolts |
| 3.3 | 16 | **Sunderbolt** (`tesla_field`) | `done` / `final1` | `func -/80` `CD 2s` `state:terror` `ltng` `Conduction` | calls down a bolt of lightning onto an enemy, scattering surrounding foes while leaving a crackling field that shocks the target / overcharge: wider scatter reach and longer sho... |
| 4.1 | 24 | **Stormcall** (`stormcall`) | `done` / `p9_consistent_nova_damage` | `func -/28` `CD 1.6s` `state:stormcall_frenzy` `ltng` `Conduction` | calls down a violent storm of lightning strikes across the target area / overcharge: wider storm area, longer duration, and faster strike rate |
| 4.3 | 24 | **Spearbolt** (`spearbolt`) | `done` / `p13_snappy_shock_wake` | `func -/1` `state:spearbolt_frenzy` `ltng` `Conduction` | hurls a high-voltage spear of lightning that leaves a crackling wake and erupts into chaining lightning arcs on impact / overcharge: longer-lasting crackling wake and extra chai... |
| 5.2 | 32 | **Overcharge** (`overcharge`) | `done` / `final5` | `func -/18` `CD 3s` `state:sorc_stance_light` `ltng` | Stance / become supercharged, boosting lightning damage, movement, hit recovery, / and block speed at the cost of reduced defense / melee attackers that hit you are shocked / on... |
| 5.3 | 32 | **Phase Step** (`phase_step`) | `done` / `p10_scaling_frenzy` | `func -/166` `CD 1.52s` `req:sorc_stance_light` `state:phase_step_frenzy` `ltng` | requires Overcharge to cast / blink to a location, shocking monsters in your path |
| 6.1 | 40 | **Conduction** (`afterglow`) | `done` / `final1` | `func -/25` `CD 1s` `req:sorc_stance_fire` `state:sorc_conduction` | conducts your active elemental stance onto a targeted ally or hireling / transfers matching elemental skill damage (up to +30%) / empowers matching elemental skills of allies wi... |
| 6.3 | 40 | **Heaven's Wrath** (`heavens_wrath`) | `done` / `p6_stance_cancel` | `func 13/29` `CD 11s` `state:thunderstorm` `ltng` `Conduction` | summons a close-range storm that calls down chaining bolts of lightning on nearby enemies / overcharge: faster strikes, wider reach, longer burst, and extra chain jumps |

### Cold (Page 3)

| r.c | Lvl | Skill (`slug`) | Status / Variant | Engine Hooks | In-Game Description |
| :---: | :---: | :--- | :--- | :--- | :--- |
| 1.2 | 1 | **Frost Dart** (`frost_dart`) | `wip` / `final1` | `cold` `Conduction` | Hurls a fast bolt of ice that chills its target / Cryostasis: doubles range and erupts in a frost burst on impact |
| 2.2 | 8 | **Hoarfrost Burst** (`hoarfrost_burst`) | `wip` / `final1` | `func -/22` `cold` `Conduction` | Unleashes an expanding ring of frost around you that chills nearby enemies / Cryostasis: greatly increased ring radius |
| 3.1 | 16 | **Glacier Step** (`glacier_step`) | `done` / `p3_freeze_curve` | `func -/166` `CD 3s` `req:sorc_stance_cold` `frze` | requires Cryostasis to cast / blink across an icy path, freezing and damaging enemies along your wake and in a burst of ice spikes where you arrive |
| 3.3 | 16 | **Permafrost** (`permafrost`) | `wip` / `final1` | `func 14/28` `CD 2s` `state:permafrost_chill` `cold` `Conduction` | Freezes the ground at the target location, heavily chilling and slowing enemies / before shattering in a blast of frost / Cryostasis: instantly freezes enemies solid on cast, wi... |
| 4.1 | 24 | **Cryostasis** (`cryostasis`) | `done` / `final5` | `func -/18` `CD 3s` `state:sorc_stance_cold` | Stance / encase yourself in frost, boosting cold damage and reducing physical damage taken and raising defense / at the cost of movement and cast speed / melee attackers that hi... |
| 4.2 | 24 | **Equilibrium** (`equilibrium`) | `done` / `final1` | `passive` | Passive / restores mana after each enemy you kill |
| 4.3 | 24 | **Stasis** (`brittle_touch`) | `done` / `final2` | `passive` | Passive / extends the duration of all lingering Sorceress / spell effects, wakes, storms, summons, and stances |
| 5.1 | 32 | **Whiteout** (`whiteout`) | `wip` / `final1` | `func -/28` `CD 1.6s` `cold` `Conduction` | Calls down a violent snowstorm that chills and bombards enemies / Cryostasis: wider storm radius, longer duration, and faster shard cadence |
| 5.3 | 32 | **Icicle Spear** (`icicle_spear`) | `wip` / `final1` | `func -/1` `frze` `Conduction` | Hurls a heavy ice lance that pierces and freezes enemies / and leaves a freezing wake / Cryostasis: wake persists 10x longer |
| 6.2 | 40 | **Frozen Orb** (`frozen_orb`) | `wip` / `final1` | `cold` | Releases a spinning orb of ice that unleashes a sweeping spiral of chilling bolts / before detonating in a final burst / Cryostasis: extended orb travel and wider bolt reach |

### Shared Helpers (`specs/_shared.json` — variant `anim_v3`)

- **Helper Skills (`skills.txt`):** `Blaze`, `Blizzard`, `Chain Lightning`, `Charged Bolt`, `Chilling Armor`, `Cold Mastery`, `Enchant`, `Energy Shield`, `Fire Ball`, `Fire Bolt`, `Fire Mastery`, `Fire Wall`, `Frost Nova`, `Frozen Armor`, `Frozen Orb`, `Glacial Spike`, `Hydra`, `Ice Blast`, `Ice Bolt`, `Inferno`, `Lightning`, `Lightning Mastery`, `Meteor`, `Nova`, `Shiver Armor`, `Static Field`, `Telekinesis`, `Teleport`, `Thunder Storm`, `Warmth`
- **Shared States (`states.txt`):** `sorc_stance_cold`, `sorc_stance_fire`, `sorc_stance_light`

<!-- AUTO-GENERATED-SPECS:END -->

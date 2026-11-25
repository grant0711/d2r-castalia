# Sorceress — Elemental Stances, Cross-Tree Passives & Spell Archetypes

- **Status:** **24 / 30 Done** (Fire 10/10, Lightning 10/10, Cold 4/10; 6 Cold stubs remaining)
- **Source Implementation:** [`tools/mod_builder/classes/sorceress/`](file:///home/grant/games/d2r/tools/mod_builder/classes/sorceress) (`registry.py`, `engine.py`, `patterns.py`, `tree.py`, `icons.py`, `statemachine.py`, `state.json`, `specs/*.json`)
- **CLI Workflow:** [`bin/d2r-sorc`](file:///home/grant/games/d2r/bin/d2r-sorc) (`map`, `show`, `patterns`, `funcs`, `variant`, `set`, `use`, `build`, `test`, `compact`)

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

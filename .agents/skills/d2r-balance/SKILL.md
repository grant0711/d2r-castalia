---
name: d2r-balance
description: >-
  Balance, benchmark, and tune Castalia (D2R mod) skill trees across Normal, Nightmare, and Hell
  using /home/grant/games/d2r/bin/d2r-balance and real Hell hybrid playtest targets. Activate this
  skill whenever tuning skill damage curves, synergies, mana costs, or adding Lightning/Cold/other
  class evaluators to tools/mod_builder/balance.py.
---

# Castalia Skill Tree Balancing Playbook (`bin/d2r-balance`)

Use this process when balancing any reworked skill tree (Fire, Lightning, Cold, or other classes) so Normal progression feels crisp, Hell hybrid builds compete with Vanilla D2R against Castalia's scaled monsters, and mana economy stays meaningful.

## 1. Quick Commands

```bash
# Run the progression simulator across 28 Normal / NM / Hell checkpoints:
/home/grant/games/d2r/bin/d2r-balance sorc fire

# Rebuild Sorceress skills & run all 30 invariant tests after tuning JSON specs:
/home/grant/games/d2r/bin/d2r-sorc build && python3 -m unittest -v

# Set up a realistic lvl 70 Hell hybrid test character (preserving items):
/home/grant/games/d2r/bin/d2r-char set SORC --level 70
/home/grant/games/d2r/bin/d2r-char reset SORC
```

When starting a new tree (e.g., **Cold** or **Lightning**), add an `eval_<tree>_skill()` evaluator and CLI target in [`tools/mod_builder/balance.py`](file:///home/grant/games/d2r/tools/mod_builder/balance.py) modeled on `eval_fire_skill()`.

---

## 2. Core Castalia Balance Realities

Always account for these three structural differences between Castalia and Vanilla D2R:

1. **Castalia Hell Monsters are Much Tougher:**
   - Hell monster HP is **~3.0×–4.1× Vanilla** (e.g., Stony Field Hell `alvl 68`: Skeleton `10,779`, Goatman `14,583` / `20,833` eHP at `30%` res, Zombie `21,980` — vs Vanilla's `3,593–5,389`).
   - Hell monster physical damage is **~1.7×–2.0× Vanilla** (`93–156` avg per hit in Stony Field vs `55–80` in Vanilla).
   - Neutral Hell monster elemental resistance is **30%**; affinity-resistant monsters sit at **75%+** (and player skills have **zero** elemental/sunder pierce).
2. **Players Must Hybridize:**
   - Because of 75%+ affinity resistances and zero pierce, players must reserve **~40–50% of skill points** (~50–60 pts at lvl 70) for a second element. Never balance Hell solely around a mono-tree 40/40 synergy dump.
3. **Stances Are Not Vanilla Masteries:**
   - Sorceress stances grant **`+5% → +30%`** elemental skill damage at lvl 20 (vs Vanilla Fire/Lightning Mastery's `+163% → +198%`). Skill base scaling (`EMinLev3..5`) and cohesive synergies must carry the Hell damage curve — **do not** weaken stance identity or inflate stance bonuses to compensate.

---

## 3. Five-Step Balancing Process

### Step 1: Normal & Unlock Step-Change (`EMin/EMax/Lev1/Lev2`, lvls 1–16)
- Tune `EMin`, `EMax`, `EMinLev1..2`, `EMaxLev1..2` against Normal Act 1–5 checkpoints (`bin/d2r-balance`).
- **Step-change rule:** When a higher-tier skill unlocks (lvl 8, 16, 24, 32, 40), lvl 1 of the new skill should feel like a clear power step-change over an already-leveled lower-tier skill (check realistic mid-game spreads, e.g., lvl 32 character).

### Step 2: Design Two Cohesive Endgame Pathways per Tree
Avoid dead lvl-1 synergy dumps. Structure synergies so active skills feed each other and support two viable endgame specs:
- **Heavy Spec (~80 pts, 100% DPS benchmark):** 3 mutually-synergizing active skills (`~10%/lvl` each) + Stance.
  - *Fire reference:* `Pyroclasm (20) + Brimstone Lance (20) + Pyre Hydra (20) + Conflagration (20)` (`~44k` combined ST DPS at lvl 70).
- **Compact Combo Spec (~60 pts, ~70–75% of Heavy Spec DPS):** 2 mutually-synergizing cooldown/combo skills (`~18%/lvl` each way, plus optional `6%/lvl` bonus from a 3rd skill) + Stance — freeing 20+ extra points for the off-tree.
  - *Fire reference:* `Backdraft (20) + Skyfall (20) + Conflagration (20)` (`~32k` combined rotation DPS = `71.5%` of Heavy Fire).

### Step 3: Ramp Hell Scaling via `Lev3 / Lev4 / Lev5` (lvls 17+)
- Keep `EMin/EMax/Lev1/Lev2` stable so Normal A1–A5 playtesting stays intact.
- Ramp **`EMinLev3` (lvls 17–22), `EMinLev4` (lvls 23–28), and `EMinLev5` (lvls 29+)** so a lvl 70 hybrid character (`+5` to `+7` skills, ~50–60 pts unallocated/off-tree) clears neutral Hell trash (**Stony Field Hell**, `10k–21k` eHP) in:
  - **Primary direct/line spam spell:** ~`1.5–4.0` casts per trash mob (comparable to Vanilla Fire Ball's `1.0–1.5` shots).
  - **360° AoE / defensive ring spell:** ~`5–10` casts per single Goatman (melting packs around you).
  - **2-skill cooldown combo (pull + nuke):** 1 clean combo (~`25k–30k` burst + ground burn) clears a Stony Field pack.
  - **Capstone summon/barrage:** ~`2–3s` to shred a Hell pack with stance enhancement active.

### Step 4: Audit Every Sub-Missile, Pet Formula, and Tooltip
Before playtesting in Hell, inspect all child rows in `missiles.txt` and `skills.txt`:
- **No flat Hell sub-missiles:** Every wake, crater, explosion, or stance splash sub-missile (`brimstone_wake`, `skyfall_fire`, `backdraft_center`, `backdraft_explode`, `pyre_hydra_blast`, etc.) must have matching `EDmgSymPerCalc` and `MinELev1..5`/`MaxELev1..5` (or pet piecewise multiplier).
- **Pet `+skills` check:** If a pet casts a separate missile skill (like `Hydra` → `HydraMissile`), verify `sumsk2calc = lvl` passes effective skill level and that the pet's multiplier formula matches the parent skill's `EMin/EMax/Lev1..5` curve 1:1.
- **Tooltip parity:** Verify `descdam`, `descline*`, and `dsc3calca*` display actual damage/DPS and updated synergy percentages.

### Step 5: Mana Economy Audit
Check effective mana cost `max(minmana, (mana + (lvl - 1) * lvlmana) * (2 ** manashift) / 256)` at **L1, L10, L20, L26**:
- Watch out for inherited **`manashift=7`** (half-cost!) making endgame spells trivially cheap.
- Keep **L1** costs gentle for Act 1 Normal, and ramp `lvlmana` so **L26** casts meaningfully tax a 450–600 mana pool even with ~15 points in the tree's sustain passive:
  - **Starter spam (T1):** `~3` (L1) → `~15.5` (L26)
  - **Core AoE / Line (T2–T5):** `~6–12` (L1) → `~31–37` (L26)
  - **Cooldown Nuke / Capstone (T2–T6):** `~18–24` (L1) → `~55–62` (L26)
- Verify the tree's sustain passive (`Ignition` `20% → 172%`, `Echo`, `Equilibrium`) makes investment feel valuable without making mana infinite on bare gear.

---

## 4. Reference Verification Checklist
- [ ] `bin/d2r-sorc build` succeeds cleanly (all 6 mod invariant suites pass).
- [ ] `python3 -m unittest -v` passes (**30/30** tests).
- [ ] Side-by-side Hell Stony Field math checked for both **Heavy (80 pt)** and **Compact Combo (60 pt)** hybrid specs vs Vanilla Fire Ball.
- [ ] In-game playtest on a lvl 70 hybrid character (`~50–60` pts left for off-tree) confirms survivability, TTK, and mana pressure feel right.
- [ ] Remove any temporary QA/testing recipes (e.g., temporary `cubemain.py` reroll rows) before committing.

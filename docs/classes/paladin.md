# Paladin Technical Reference: Aura Mana Upkeep, Resistance-Synergized Cleave & Chain Hammer

Source implementation:
- [tools/mod_builder/classes/paladin/skills.py](file:///home/grant/games/d2r/tools/mod_builder/classes/paladin/skills.py)
- [tools/mod_builder/classes/paladin/sprites.py](file:///home/grant/games/d2r/tools/mod_builder/classes/paladin/sprites.py)

---

## 1. Active Aura Mana Upkeep vs. Zero-Mana Recovery Stances

### Periodic Aura Mana Drain (`srvdofunc = 65`, `perdelay = 50`)
In vanilla D2R, Paladin auras (`srvdofunc = 65`) have `mana = 0, lvlmana = 0`, making them passive "set and forget" buffs. In Castalia, active combat and defensive auras drain Mana every `perdelay` tick (`50` frames = `2.0` seconds, or `10` frames = `0.4` seconds on `Thorns`) by populating `mana`, `lvlmana`, and `manashift`:

- In `skilldesc.txt`, `descline1 = 36` with `desctexta1 = "StrSkill34"` (`"Mana Cost: %d per second"`), `desccalca1 = "usmc/2"` (for `50`-frame `2.0s` tick auras, or `"usmc*5"` for `10`-frame `0.4s` tick `Thorns`), and `desccalcb1 = "256"` displays the exact **Mana/second** upkeep rate (`0.5–1.2` Mana/sec at Level 1 $\rightarrow$ `5.2–7.1` Mana/sec at Level 20).

### Zero-Mana Recovery Stances (`Prayer`, `Meditation`, `Redemption`)
To create an active stance-switching rhythm, three Defensive Auras cost **`0` Mana/sec**:
1. **Prayer (`Id 99`)**: `InTown = 1`, `mana = 0`, heals party Life every 2 seconds without draining Mana (synergized by hard points in `Cleansing`).
2. **Meditation (`Id 120`)**: `mana = 0`, grants `+85%` $\rightarrow$ `+506%` Mana recovery, but sets `aurastat2 = "damagepercent"`, `aurastatcalc2 = "-50"` (**`-50%` Base Weapon Damage** while active) so the Paladin switches to Meditation to recover Mana and switches back to an offensive aura to fight.
3. **Redemption (`Id 124`)**: `mana = 0`, periodically redeems nearby corpses while granting active `item_healafterkill` (`+21` $\rightarrow$ `+96` LAEK) and `item_manaafterkill` (`+14` $\rightarrow$ `+64` MAEK).

---

## 2. Reworked Paladin Combat & Aura Mechanics

### 1. Vengeance (`Id 111`) — 156° Frontal Cleave + Single-Element Resistance Synergies
- **Frontal Arc Cleave**: Uses `srvstfunc = 1`, `srvdofunc = 153` (Sweep/Cleave attack), `cltdofunc = 100`, `Param9 = 13` (`156°` frontal arc), striking all enemies in front of the Paladin in a single swing.
- **Single-Element Resistance Synergies**:
  - `calc1` (Fire Damage `%`): `RAMP12 + skill('Resist Fire'.blvl) * par7` (`+23%/lvl` from `Resist Fire`)
  - `calc2` (Cold Damage `%`): `RAMP34 + skill('Resist Cold'.blvl) * par7` (`+23%/lvl` from `Resist Cold`)
  - `calc3` (Lightning Damage `%`): `RAMP56 + skill('Resist Lightning'.blvl) * par7` (`+23%/lvl` from `Resist Lightning`)
  - Investing in a single Resistance Aura lets the Paladin specialize Vengeance into a specific element (up to `+619%` in that element at Level 20/20).

### 2. Blessed Hammer (`Id 112`) — Bouncing Chain Hammer (`srvdofunc = 26`, `cltdofunc = 27`)
- Converted from the vanilla spiraling turret into a `1.0s` cooldown (`localdelay = 25`) tactical **Chain Hammer**:
  - `srvdofunc = 26`, `cltdofunc = 27` (`Chain Lightning` bounce handler) with `srvmissilea..c = "blessedhammer"`, `cltmissilea..c = "blessedhammer"`.
  - `aurarangecalc = "par1"` (`16` subtiles = `10.6` yards bounce search radius).
  - `calc1 = "ln34/par5"` (`4` bounces at Level 1 $\rightarrow$ `8` bounces at Level 20).
  - `calc4 = "min(250, par2 * (100 + skill('Smite'.blvl) * par6) / 100)"` (`15` frames = `0.6s` base Stun on every bounce, synergized `+10%/lvl` by `Smite`).
  - In `missiles.txt`, `blessedhammer` uses `pSrvDoFunc = 1`, `pCltDoFunc = 1`, `pSrvHitFunc = 12`, `pCltHitFunc = 16`, `pSrvDmgFunc = 7` (applies `calc4` stun), `ResultFlags = 5` (GetHit + Knockback), and `Vel = 16, VelLev = 6, MaxVel = 40`.

### 3. Conviction (`Id 123`) — Friendly Party & Mercenary Aura on a Logistic S-Curve
- Because Castalia eliminates all `-Enemy Elemental Resistance %` pierce, `Conviction` is reworked into a **friendly party & mercenary buff aura** (`aurafilter = 65795`, applying `auratargetstate = "conviction"` to allies within `13.3` yards):
  - **S-Curve Factor (`calc1`, `1` at Lvl 1 $\rightarrow$ `39` at Lvl 20)**:
    ```text
    1 + max(0,lvl-1) + max(0,min(lvl,15)-5) + max(0,min(lvl,15)-7) + max(0,min(lvl,14)-8) + max(0,min(lvl,12)-9)
    ```
    Concentrates the steepest marginal gains across levels `6–15` to reward genuine hard-point commitment over 1-point `+skills` splashing.
  - **Party Buffs (`aurastat1..5`)**:
    - `aurastat1 = "item_damagetargetac"`: `-(60 + clc1 * 18)` (`-60` $\rightarrow$ `-762` Monster Defense Per Hit)
    - `aurastat2 = "item_slow"`: `min(35, 4 + (clc1 * 4) / 5)` (`4%` $\rightarrow$ `35%` Slows Target)
    - `aurastat3 = "passive_fire_mastery"`: `(skill('Resist Fire'.blvl) * (3 + clc1 * 3)) / 20` (`+%` Fire Skill Damage scaled by hard points in `Resist Fire`)
    - `aurastat4 = "passive_cold_mastery"`: `(skill('Resist Cold'.blvl) * (3 + clc1 * 3)) / 20` (`+%` Cold Skill Damage scaled by hard points in `Resist Cold`)
    - `aurastat5 = "passive_ltng_mastery"`: `(skill('Resist Lightning'.blvl) * (3 + clc1 * 3)) / 20` (`+%` Lightning Skill Damage scaled by hard points in `Resist Lightning`)

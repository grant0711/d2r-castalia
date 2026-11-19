# Barbarian Stamina Pendulum: Co-opted Functions, Stamina Drain & Stamina-Coupled Damage

Source implementation:
- [skills.py](file:///home/grant/games/d2r/tools/mod_builder/skills.py#L1193-L2143) (Barbarian Stamina Spenders, Well-Rested skills, Exhaustion skills, and Stamina Control Warcries)
- [skills.py](file:///home/grant/games/d2r/tools/mod_builder/skills.py#L2642-L2842) (Barbarian Leap/Warcry missiles)
- [skills.py](file:///home/grant/games/d2r/tools/mod_builder/skills.py#L4289-L4426) (`Bar Stamina Reflex` `Id 433` and helper pulse skills)

---

## 1. Co-opting Engine Functions to Drain Stamina on `Leap`, `Leap Attack`, and `Whirlwind`

### The Engine Limitation
`skills.txt` has no native "Stamina Cost" column (only Mana via `mana` / `lvlmana`), and vanilla `Leap` (`srvdofunc = 77`), `Leap Attack` (`srvdofunc = 78`), and `Whirlwind` (`srvdofunc = 62`) have no hook to cast a secondary skill or apply a self-stat on landing or during spin ticks.

### Part A — Co-opting the Ancients' Escalation Hooks (`srvdofunc = 170` & `srvdofunc = 168`)
We replaced the vanilla `srvdofunc` handlers on `Leap`, `Leap Attack`, and `Whirlwind` with the special escalation-capable functions built for the Act 5 Ancients (**Korlic** and **Talic**):

| Skill | Vanilla `srvdofunc` | Replacement `srvdofunc` | Escalation Hook Columns in `skills.txt` | When the Hook Fires |
| :--- | :---: | :---: | :--- | :--- |
| **Leap** (`Id 132`) | `77` | **`170`** (`Korlic's Leap Attack`, `cltdofunc = 43`) | `calc5` = Skill ID to cast (`433`)<br>`calc6` = Skill Level (`1`) | Automatically casts Skill `calc5` at level `calc6` at the moment the Barbarian lands (alongside `srvmissilea = leapknockback`). |
| **Leap Attack** (`Id 143`) | `78` | **`170`** (`Korlic's Leap Attack`, `cltdofunc = 44`) | `calc5` = Skill ID to cast (`433`)<br>`calc6` = Skill Level (`10`) | Automatically casts Skill `calc5` at level `calc6` on landing (alongside `srvmissilea = leapattack` and the melee strike). |
| **Whirlwind** (`Id 151`) | `62` | **`168`** (`Talic's Whirlwind`, `srvstfunc = 38`, `cltstfunc = 31`, `cltdofunc = 45`) | `calc6` = Escalation 1 Skill ID (`433`)<br>`calc2` = Escalation 1 Skill Level (`2`)<br>`calc3` = Cast Chance % (`100`) | Automatically casts Skill `calc6` at level `calc2` (`100%` chance) on every spin attack tick while whirling. |

### Part B — Draining Player Stamina via `Bar Stamina Reflex` (`Id 433`: `srvdofunc = 30` + `auraevent1 = "install"` + `auraeventfunc1 = "3"` + `EType = "stam"`)
How does casting hidden skill **`Bar Stamina Reflex` (`*Id = 433`)** subtract Stamina from the Barbarian when he leaps into or whirls through enemies?

```python
sk_reflex["skill"] = "Bar Stamina Reflex"
sk_reflex["*Id"] = "433"
sk_reflex["srvdofunc"] = "30"
sk_reflex["aurafilter"] = "3"
sk_reflex["auratargetstate"] = "bar_stamina_reflex"
sk_reflex["auralencalc"] = "2"
sk_reflex["aurarangecalc"] = "(lvl==10)?9:((lvl==1)?6:4)"
sk_reflex["auraevent1"] = "install"
sk_reflex["auraeventfunc1"] = "3"
sk_reflex["ItemEffect"] = "1"
sk_reflex["HitShift"] = "3"
sk_reflex["EType"] = "stam"
sk_reflex["EMin"] = "12"
sk_reflex["EMinLev1"] = "4"
sk_reflex["EMinLev2"] = "-6"
sk_reflex["EMax"] = "12"
sk_reflex["EMaxLev1"] = "4"
sk_reflex["EMaxLev2"] = "-6"
```

1. **Radial Curse Application (`srvdofunc = 30`)**:
   - When `Leap`, `Leap Attack`, or `Whirlwind` triggers `Bar Stamina Reflex` (`Id 433`), `srvdofunc = 30` applies `auratargetstate = "bar_stamina_reflex"` (`curable = 1, curse = 1` in `states.txt`) for `2` frames to units within `aurarangecalc` subtiles (`6` subtiles at `sLvl 1` for `Leap`, `4` subtiles at `sLvl 2` for `Whirlwind`, `9` subtiles at `sLvl 10` for `Leap Attack`).
2. **Instant State-Install Reflection (`auraevent1 = "install"`, `auraeventfunc1 = "3"`, `EType = "stam"`)**:
   - In D2R's engine, `auraeventfunc = 3` is `Shiver Armor`'s elemental reflection callback: whenever its paired `auraevent` triggers on a unit holding the state, that unit inflicts the skill's elemental damage (`EType`, `EMin`..`EMax`) back onto the source!
   - By binding `auraeventfunc1 = "3"` to **`auraevent1 = "install"`** (which fires **immediately on the exact frame the state is applied**) and setting **`EType = "stam"`** (the engine's native Stamina-drain damage type used by Act 2/3 swarm monsters), each monster within `aurarangecalc` immediately reflects `EType = "stam"` damage back onto the Barbarian on state install—draining his Stamina bar in proportion to enemy contact!
3. **3-Tier Scaling in One Skill Row (`sLvl 1`, `sLvl 2`, `sLvl 10`)**:
   - By setting `EMin = 12`, `EMinLev1 = 4` (levels 2–8), and `EMinLev2 = -6` (levels 9–16):
     - **`sLvl 1` (`Leap`)**: `aurarangecalc = 6` subtiles, gentle drain (`12` at `HitShift = 3`).
     - **`sLvl 2` (`Whirlwind`)**: `aurarangecalc = 4` subtiles, stronger per-tick spin drain (`16` at `HitShift = 3`).
     - **`sLvl 10` (`Leap Attack`)**: `aurarangecalc = 9` subtiles, heavy landing drain (`28` at `HitShift = 3`).

---

## 2. Instant Flat Stamina & Life Refills via Short-Duration Regen Pulses

Because `skills.txt` has no native "restore flat Stamina on cast" function, we implemented **`Second Wind`** (`Find Potion`, `Id 131`) as a 2-frame Warcry (`srvdofunc = 68`, `cltdofunc = 25`, `srvmissilea = battlecommand`, `auralencalc = 2`) that normalizes `staminarecoverybonus` against the caster's `maxstamina`:

```python
swind["auralencalc"] = "2"
swind["aurastat1"] = "staminarecoverybonus"
swind["aurastatcalc1"] = "(clc1*15000*256)/max(256,stat('maxstamina'.accr))-100"
swind["aurastat2"] = "item_staminadrainpct"
swind["aurastatcalc2"] = "100"
```

- Because engine Stamina regeneration scales with `maxstamina * (100 + staminarecoverybonus)`, dividing `clc1 * 15000 * 256` by `max(256, stat('maxstamina'.accr))` cancels `maxstamina` out of the equation—delivering an **exact flat `clc1` Stamina refill** over the 2-frame (`0.08s`) state duration regardless of how much Maximum Stamina the Barbarian has.
- Similarly, **`Battle Command`** (`Id 155`) was converted into an immediate flat Life heal over `5` frames (`0.2s`) using `aurastat1 = "hpregen"` and `aurastatcalc1 = "(clc1*256)/5"`.
- In `states.txt`, we also cleared `stambarblue = ""` on `staminapot` so Stamina shrines/potions do not hide the real-time Stamina bar level with a static blue bar.

---

## 3. Coupling Attack Damage, AR, Defense, Speed, Range & Stun to Stamina Levels

### Fixed-Point Stamina Percentage Formulas (`RESTED_PCT` & `EXHAUST_PCT`)
In `itemstatcost.txt`, both `stamina` (`*ID 10`) and `maxstamina` (`*ID 11`) use 8-bit fixed-point precision (`ValShift = 8`, meaning `1` displayed Stamina = `256` raw `.accr` units).

Because `stat('stamina'.accr)` and `stat('maxstamina'.accr)` both include the `256x` factor, their ratio yields an exact integer percentage (`0..100`) inside any `skills.txt` formula column:

- **`RESTED_PCT` (Current Stamina %, `0` at empty $\rightarrow$ `100` at full)**:
  ```text
  ((stat('stamina'.accr)*100)/max(256,stat('maxstamina'.accr)))
  ```
- **`EXHAUST_PCT` (Missing Stamina %, `0` at full $\rightarrow$ `100` at empty)**:
  ```text
  (100-(stat('stamina'.accr)*100)/max(256,stat('maxstamina'.accr)))
  ```

### How Each Barbarian Skill Family Couples to `RESTED_PCT` or `EXHAUST_PCT`

#### Family 1: Stamina Spenders (`Leap`, `Leap Attack`, `Whirlwind`) — Degrade as Stamina Drops (`RESTED_PCT`)
All three Stamina Spenders cost `0` Mana (`minmana = 0, mana = 0, lvlmana = 0`), drain Stamina on enemy contact via `Bar Stamina Reflex` (`Id 433`), and lose effectiveness as `RESTED_PCT` falls from `100%` to `0%`:

| Skill | Coupled Parameter | `skills.txt` Column | Stamina-Coupled Formula | Behavior (`100%` Stamina $\rightarrow$ `0%` Stamina) |
| :--- | :--- | :--- | :--- | :--- |
| **Leap** (`Id 132`) | Jump Distance | `aurarangecalc` (`= clc3`) | `6 + ((dm12 - 6) * RESTED_PCT) / 100` | Full `dm12` jump distance at 100% Stamina $\rightarrow$ short 6-subtile hop at 0% Stamina. |
| **Leap** (`Id 132`) | Leap Air Speed % | `calc2` | `90 + ((par7 - 90) * RESTED_PCT) / 100` | Full `par7` air speed at 100% Stamina $\rightarrow$ sluggish `90%` speed at 0% Stamina. |
| **Leap** (`Id 132`) | Knockback Radius | `calc1` | `2 + ((ln34 - 2) * RESTED_PCT) / 100` | Full `ln34` knockback radius at 100% Stamina $\rightarrow$ 2-subtile radius at 0% Stamina. |
| **Leap Attack** (`Id 143`) | Melee Weapon `%ED` | `calc1` | `((clc3 + 50) * RESTED_PCT) / 100 - 50` | Full `+clc3%` ED at 100% Stamina $\rightarrow$ **`-50%` ED penalty** at 0% Stamina. |
| **Leap Attack** (`Id 143`) | Landing Shockwave Damage % | `DmgSymPerCalc` | `((75 + skill('Leap'.blvl)*par8) * RESTED_PCT) / 100 - 75` | Full shockwave damage at 100% Stamina $\rightarrow$ `-75%` shockwave damage at 0% Stamina. |
| **Leap Attack** (`Id 143`) | Landing AoE Stun | `calc4` (read by `leapattack` `pSrvDmgFunc = 7`) | `(RESTED_PCT >= 50) ? par6 : 0` | Stuns landing pack for `35` frames (`1.4s`) when Stamina $\ge 50\%$; **0 stun** below 50% Stamina. |
| **Whirlwind** (`Id 151`) | Spin Weapon `%ED` | `calc1` | `((RAMP12 + syn*par8 + 50) * RESTED_PCT) / 100 - 50` | Full skill + synergy `%ED` at 100% Stamina $\rightarrow$ **`-50%` ED penalty** at 0% Stamina. |

#### Family 2: "Well-Rested" Disciplined Attacks (`Bash`, `Shield Slam`, `Concentrate`) — Scale UP with `RESTED_PCT`
These skills store their Zero-Stamina baseline `%ED` in `calc5` and their Maximum Well-Rested bonus `%ED` in `calc6`, then compute total `%ED` in `calc1`:
```text
calc1 = clc5 + ((RESTED_PCT) * clc6) / 100
```
- **Bash (`Id 126`)**: Scales from `clc5` (`RAMP12 + Concentrate_syn`) at 0% Stamina up to `clc5 + clc6` (`+40%..+135%` extra ED) at 100% Stamina.
- **Concentrate (`Id 144`)**: Both weapon `%ED` (`calc1`) and self-buff Defense `%` (`aurastatcalc1 = RAMP34 + (RESTED_PCT * RAMP34) / 100`) double at 100% Stamina.
- **Shield Slam (`Stun`, `Id 139`)**: Reworked into a Shield-requiring (`itypea1 = "shld"`) tactical Charge (`srvstfunc = 31`, `srvdofunc = 67`, `cltstfunc = 25`, `cltdofunc = 37`, `localdelay = 25`, `AttackNoMana = ""`). Both its weapon `%ED` (`calc1`, which also scales with `stat('toblock'.accr)`) and its Stun Duration (`ELenSymPerCalc = (RESTED_PCT * 50) / 100`) scale up with `RESTED_PCT`.

#### Family 3: "Exhaustion / Last Stand" Attacks (`Double Swing`, `Double Throw`, `Frenzy`, `Berserk`) + `Bloodlust` (`Id 150`) — Scale UP with `EXHAUST_PCT`
These four skills do the inverse—storing their Full-Stamina baseline `%ED` in `calc5` and their Maximum Exhaustion bonus `%ED` in `calc6`, then scaling up linearly as Stamina is depleted (`EXHAUST_PCT`: `0% -> 100%`):
```text
calc1 = clc5 + ((EXHAUST_PCT) * clc6) / 100
```
- **Coupling `Bloodlust` (`Grim Ward`, `Id 150`) Exclusively to Exhaustion Skills**:
  - `Bloodlust` is a self-buff Warcry (`srvdofunc = 18`, `aurastate = bar_totem_debuff` in `group = 10`, mutually exclusive with `Battle Orders`) that drains Life (`aurastat1 = "hpregen"`, `aurastatcalc1 = "-(clc5*256)/25"`) and sets a marker stat on the Barbarian: **`aurastat2 = "skill_chillingarmor"`, `aurastatcalc2 = "1"`**.
  - `Bloodlust` pre-computes its Max Exhaustion Damage `%` in `calc1` and its live Exhaustion Attack Rating `%` in `calc4 = (EXHAUST_PCT * clc2) / 100`.
  - Each of the four Exhaustion skills (`Double Swing`, `Double Throw`, `Frenzy`, `Berserk`) checks `stat('skill_chillingarmor'.accr) > 0` inside its `calc6` (`%ED`) and `ToHitCalc` (`%AR`) formulas:
    ```text
    BLOODLUST_MAX_DMG = ((stat('skill_chillingarmor'.accr)>0)?skill('Grim Ward'.clc1):0)
    BLOODLUST_CUR_AR  = ((stat('skill_chillingarmor'.accr)>0)?skill('Grim Ward'.clc4):0)
    ```
  - This allows an active Warcry buff (`Bloodlust`) to dynamically amplify **only** the four Exhaustion skills' damage and Attack Rating in direct proportion to missing Stamina (`EXHAUST_PCT`), without affecting Well-Rested or Stamina Spender skills.

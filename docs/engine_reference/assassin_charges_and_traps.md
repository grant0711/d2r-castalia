# Assassin Charge-Up, Finisher Release & Sentry Trap Reference

Source implementation:
- [skills.py](file:///home/grant/games/d2r/tools/mod_builder/skills.py#L2871-L4098) (Missile chains & submissiles)
- [skills.py](file:///home/grant/games/d2r/tools/mod_builder/skills.py#L4428-L5976) (Charge-Up skills, Sentry Traps, Finishing Moves, and `Omnislash`)
- [monsters.py](file:///home/grant/games/d2r/tools/mod_builder/monsters.py#L861-L968) (Sentry pet `monstats.txt` & `monprop.txt` definitions)

---

## 1. Progressive Charge-Up States & Per-Orb Holding Stats

Every Charge-Up skill uses `srvstfunc = 23` and `srvdofunc = 34`, which increment the skill's `aurastat1` (`progressive_*`) from `1 -> 2 -> 3` on each successful melee hit and apply `aurastate` for `auralencalc` frames (`22,500` frames = 15 minutes).

Crucially, `srvdofunc = 34` **multiplies `aurastat1..6` by the current orb count (`1x / 2x / 3x`)** whenever a charge is added. This allows `aurastat2` to grant a live unit stat that scales linearly with held orbs (`1 / 2 / 3`) on every melee attack (including non-finisher skills like `Omnislash`/Whirlwind), while showing `0` bonus at `0` orbs:

| Charge-Up Skill | `aurastate` / `aurastat1` | Per-Orb Holding Stat (`aurastat2`) | How Zero-Orb Character Screen Accuracy Is Preserved |
| :--- | :--- | :--- | :--- |
| **Tiger Strike** (`Id 254`) | `progressive_damage` | `damagepercent` (`+clc1%` ED per orb) | `damagepercent` is only active while `progressive_damage` is on the unit (`1x / 2x / 3x`). |
| **Fists of Fire / Flamestrike** (`Id 259`) | `progressive_fire` | `item_slash_damage` (`+clc3` per orb) | `EType/EMin/EMax` on the skill row are cleared (`""`). `passivestate = ass_fof_passive` sets `passivestat1 = item_absorb_slash = 1`, which our custom stat wiring uses alongside `item_slash_damage` to add `1x / 2x / 3x` Fire melee damage (`Max = 2 * Min`) only while holding orbs. |
| **Cobra Strike** (`Id 265`) | `progressive_steal` | `item_damagetargetac` (`-50` Monster Defense per hit per orb $\rightarrow$ `-50 / -100 / -150`) | `Send Bits` on `item_damagetargetac` (`*ID 120` in `itemstatcost.txt`) increased from `8` to `16` and `damagerelated` cleared (`""`) so dual-claw swings do not overwrite the state's stat block. |
| **Claws of Thunder / Electrocute** (`Id 269`) | `progressive_lightning` | `item_thrust_damage_percent` (`+clc3` Max Lightning damage per orb) | `passivestate = ass_cot_passive` sets `passivestat1 = item_absorb_thrust = 1` and `passivestat2 = lightmindam = 1`. |
| **Blades of Ice** (`Id 274`) | `progressive_cold` | `item_crush_damage` (`+clc3` Min Cold damage per orb, `Max = 2 * Min`) | `passivestate = ass_boi_passive` sets `passivestat1 = item_absorb_crush = 1` and `passivestat2 = coldlength = 75`. |

---

## 2. Selective Orb Consumption on Paired Sentry Traps (`srvstfunc = 39` + `srvdofunc = 45`)

### The Problem
`srvdofunc = 45` (Assassin Trap Summon) has no native mechanism to consume `progressive_*` charges. Furthermore, if the player is holding multiple orb types simultaneously (e.g., `3` Fire Orbs and `2` Lightning Orbs), casting **Fire Sentry** must:
1. Read the current `progressive_fire` orb count (`0..3`) and pass it to the newly spawned **Fire Sentry** pet, AND
2. Clear **only `progressive_fire`**, leaving `progressive_lightning` (and any other orb types) completely intact.

### The Mechanism (3-Step Frame Lifecycle)
Each Sentry Trap is paired 1:1 with a Charge-Up skill's `progressive_*` state by setting **`srvstfunc = 39`** + **`srvdofunc = 45`** on the Trap skill row:

```python
snap_fof = "max(stat('progressive_fire'.accr), stat('item_kickdamage'.accr))"
wof["srvstfunc"] = "39"
wof["srvdofunc"] = "45"
wof["aurastate"] = "progressive_fire"
wof["auralencalc"] = "12"
wof["aurastat1"] = "item_kickdamage"
wof["aurastatcalc1"] = snap_fof
wof["sumskill5"] = "Ass Trap Charge Consume"
wof["sumsk5calc"] = snap_fof
```

1. **Frame 0 — Cast Start (`srvstfunc = 39`)**:
   - `srvstfunc = 39` executes on Frame 0 when the trap-laying animation begins (before `srvdofunc = 45` fires on the animation's action frame).
   - Crucially, `srvstfunc = 39` evaluates `aurastatcalc1` **before** stripping the existing `progressive_fire` state's stats. Thus `max(stat('progressive_fire'.accr), stat('item_kickdamage'.accr))` reads the live Fire Orb count (`0, 1, 2, or 3`) and stores it into the scratchpad stat `item_kickdamage`.
   - `srvstfunc = 39` then overwrites **only `progressive_fire`** on the Assassin with a **12-frame duration (`auralencalc = 12`)** and a stat list containing only `item_kickdamage = 0..3` (zeroing `progressive_fire`). Other `progressive_*` states on the Assassin are untouched.
2. **Action Frame (<12 Frames Later) — Pet Summon (`srvdofunc = 45`)**:
   - On the cast animation's action flag frame, `srvdofunc = 45` spawns the sentry pet and evaluates `sumskill1..5` (`sumsk1calc..5calc`) and `passivestat1..5` (`passivecalc1..5`) while the 12-frame state is still active.
   - Because `stat('item_kickdamage'.accr)` still holds the snapshotted count (`0..3`), `sumskill5 = "Ass Trap Charge Consume"` sets the pet's base level (`blvl`) of `Ass Trap Charge Consume` to `0, 1, 2, or 3`.
   - In `monstats.txt`, each sentry (`wakeofdestruction`, `infernosentry`, `chargeboltsentry`, `lightningsentry`, `deathsentry`) sets `SendSkills = 31` (bitmask `0b11111` syncing `Skill1..Skill5` to the client) and lists `Ass Trap Charge Consume` in `Skill4` (with no `Sk4mode`, so the AI never casts it; it acts purely as an integer variable `0..3` readable on both server and client via `skill('Ass Trap Charge Consume'.blvl)`).
3. **Frame 12 — Clean State Expiration**:
   - Twelve frames (`0.48s`) after cast start, the overwritten `progressive_fire` state expires naturally, removing the Fire Orb visual overlay and clearing `item_kickdamage` back to `0`.

---

## 3. Variable Sentry Trap Behavior (`0, 1, 2, 3` Charges)

Once the sentry pet holds `skill('Ass Trap Charge Consume'.blvl)` = `0, 1, 2, or 3`, each sentry modifies its firing skill and missiles across three tiers:

| Sentry Trap (Summon Skill $\rightarrow$ Pet Firing Skill) | Paired Orb State | **1 Orb (`c >= 1`)** | **2 Orbs (`c >= 2`)** | **3 Orbs (`c == 3` Capstone)** |
| :--- | :--- | :--- | :--- | :--- |
| **Shrapnel Sentry** (`Fire Trauma` $\rightarrow$ `mon inferno sentry` firing `bladefragment3`) | `progressive_damage` (`Tiger Strike`) | **+Shots**: `calc4 = par8 + (6 + ts_blvl / 4)` (`11` $\rightarrow$ `17..22` shots). | **+Velocity & Range**: `sumsk1calc` boosts `mon inferno sentry` level to `9 + ts_blvl / 2` (raising `Vel = 16 -> 32` via `VelLev = 8`); `Range` increases from `18` to `32 + ts_blvl`. | **100% Open Wounds**: `Fire Trauma` sets `passivestat2 = item_openwounds`, `passivecalc2 = (snap >= 3) ? 101 : 0`. Combined with `monprop.txt` registering `openwounds = -1 / -1` on `infernosentry`, net Open Wounds is `0%` at 0–2 orbs and `100%` at 3 orbs. |
| **Fire Sentry** (`Wake of Fire Sentry` $\rightarrow$ `Wake Of Destruction Sentry` firing `vampirefireball`) | `progressive_fire` (`Fists of Fire`) | **+Shots**: `calc4 = par8 + (3 + fof_blvl / 10)` (`5` $\rightarrow$ `8..10` shots). | **+Velocity & Range**: `sumsk1calc` boosts `Wake Of Destruction Sentry` level to `9 + fof_blvl / 2` (`Vel = 10 -> 30` via `VelLev = 8`); `Range` increases from `16` to `28 + fof_blvl`. | **AoE Stun Detonation**: `vampirefireball` (`pSrvHitFunc = 38`, `sHitPar1 = 6`) bursts into 6 `sucfireball` submissiles (`pSrvDoFunc = 2`, `SrvCalc1 = (c >= 3) ? 1 : 0`), which spawn `sucfireballexplode` (`pSrvDmgFunc = 7`, `dParam1 = 10`, `Range = (c >= 3) ? 3 : 0`) to stun monsters for 10 frames. |
| **Soul Siphon Sentry** (`Charged Bolt Sentry` $\rightarrow$ `BoltSentry` firing `sentrychargedbolt`) | `progressive_steal` (`Cobra Strike`) | **+Shots**: `calc4 = par8 + (5 + cs_blvl / 4)` (`9` $\rightarrow$ `14..19` shots). | **+Velocity & Range**: `sumsk1calc` sets `BoltSentry` level to `2` (`10` at 3 orbs), increasing `Vel = 16 -> 24` (`VelLev = 8`) and `Range = 30 -> 46 + cs_blvl`. | **Life Tap Curse Pulse**: At 3 orbs (`lvl = 10`), `sentrychargedbolt` (`pSrvDoFunc = 2`, `SrvCalc1 = (lvl >= 3) ? 1 : 999`) spawns `sentryspikeinair` (`pSrvHitFunc = 38`, `sHitPar1 = -4, sHitPar2 = 1`), which spawns `-4 + 10 = 6` `sentryspikeonground` controllers (`pSrvDoFunc = 14`, `Param1 = 1`, `Param2 = 30`, `Skill = BoltSentry`) applying `lifetap` in a 5-subtile radius (`aurarangecalc = (lvl >= 3) ? 5 : 0`). |
| **Lightning Sentry** (`Lightning Sentry` $\rightarrow$ `sentry lightning` firing `sentrylightningbolt`) | `progressive_lightning` (`Claws of Thunder`) | **+Range**: `sentrylightningbolt` `Range` increases from `8` to `14 + cot_blvl / 3` frames. | **+Shots**: `calc4 = par8 + (4 + cot_blvl / 5)` (`7` $\rightarrow$ `11..15` shots). | **Dim Vision Blind**: `sentrylightningbolt` (`pSrvDoFunc = 2`, `SrvCalc1 = 1`) spawns `sentrylightningbolt2` (`pSrvHitFunc = 21`, `Skill = sentry lightning`, `Range = (c >= 3) ? 2 : 0`), applying `auratargetstate = dimvision` for `100 + 10 * cot_blvl` frames (`auralencalc = (c >= 3) ? ... : 0`). |
| **Ice Sentry** (`Death Sentry` $\rightarrow$ `mon death sentry` firing `frozenhorror arcticblast1`) | `progressive_cold` (`Blades of Ice`) | **+Range**: `frozenhorror arcticblast1` `Range` increases from `16` to `26 + boi_blvl / 2` frames. | **+Shots**: `calc4 = par8 + (15 + boi_blvl / 2)` (`25` $\rightarrow$ `40..50` bursts). | **Solid Freeze**: `frozenhorror arcticblast1` (`pSrvDoFunc = 2`, `SrvCalc1 = 1`) spawns `frozenhorror arcticblast2` (`EType = frze`, `pSrvDmgFunc = 2`, `dParam1 = 100`, `Range = (c >= 3) ? 2 : 0`), freezing hit monsters solid for `75 + 5 * lvl` frames. |

---

## 4. Melee Finishing Move Releases (`srvprgfunc1..3` / `cltprgfunc1..3`)

### Which Attack Functions Can Release Orbs
In D2R's engine, the `finishing = 1` column in `skills.txt` does **not** automatically make any `srvdofunc` release progressive charges. Only five melee `srvdofunc` handlers call the engine's progressive release routine:
- `srvdofunc = 1` (Normal Attack)
- `srvdofunc = 42` (`Dragon Talon` — note: hardcodes kick/boot physical damage)
- `srvdofunc = 47` (`Dragon Claw` — dual-claw weapon strike)
- `srvdofunc = 50` (`Dragon Tail` — AoE knockback kick)
- `srvdofunc = 53` (`Dragon Flight` — teleport kick)

When one of these functions hits with `prgchargesconsumed = 1` (and `Param8 = 1` for Guaranteed Hit when charges are active), it executes `srvprgfuncN` and `cltprgfuncN` (`N = 1, 2, or 3`, corresponding to the orb count) on each active `progressive_*` skill:

| Charge-Up Skill | Charge 1 Release (`srvprgfunc1` / `cltprgfunc1`) | Charge 2 Release (`srvprgfunc2` / `cltprgfunc2`) | Charge 3 Release (`srvprgfunc3` / `cltprgfunc3`) |
| :--- | :--- | :--- | :--- |
| **Tiger Strike** (`Id 254`) | `41` / `15` (`prgcalc1 = 36`, `srvmissilea = inferno sentry 1`): 36-missile 360° Physical Shockwave Ring (`Vel = 8, Range = 7` = 7.0 subtiles) with `1x` multiplier (`calc6`). | `41` / `15` (`prgcalc2 = 36`, `srvmissileb = inferno sentry 2`): 7.0-subtile Physical Shockwave Ring with `2x` damage multiplier (`calc6`). | `41` / `15` (`prgcalc3 = 36`, `srvmissilec = progressive radius damage`): 7.0-subtile Physical Shockwave Ring with `3x` damage multiplier + **100% Knockback** (`ResultFlags = 13`, `KnockBack = 100`). |
| **Fists of Fire** (`Id 259`) | `39` / `9` (`prgcalc1 = 6`, `srvmissilea = fistsoffireexplode`): 6-subtile disc of instant Fire Explosions. | `39` / `9` (`prgcalc2 = 9`, `srvmissileb = fistsoffirefirewall`): 9-subtile wide Burning Ground field (`Range = 85` frames). | `40` / `14` (`prgcalc3 = 9`, `srvmissilec = royalstrikemeteorcenter`): Calls down a crashing Meteor (`royalstrikemeteor` + `royalstrikemeteorfire`). |
| **Cobra Strike** (`Id 265`) | `prgdam = 2` (`1x` Life Steal) + `41` / `15` (`prgcalc1 = 36`, `srvmissilea = unholybolt2` $\rightarrow$ `undeadmissile2` with `pSrvHitFunc = 21`): 7.0-subtile Soul-Hex Wave applying `Ass Cobra Hex 1` (`-1x` flat & `%` Monster Defense). | `prgdam = 2` (`1x` Life & Mana Steal) + `41` / `15` (`unholybolt3` $\rightarrow$ `undeadmissile3`): 7.0-subtile Soul-Hex Wave applying `Ass Cobra Hex 2` (`-2x` flat & `%` Monster Defense). | `prgdam = 2` (`2x` Life & Mana Steal) + `41` / `15` (`unholybolt4` $\rightarrow$ `undeadmissile4`): 7.0-subtile Soul-Hex Wave applying `Ass Cobra Hex 3` (`-3x` flat & `%` Monster Defense). |
| **Claws of Thunder** (`Id 269`) | `37` / `11` (`prgcalc1 = max(4, 8 - lvl/5)`, `srvmissilea = clawsofthunderbolt`): Fan of `8..16` Charged Bolts (`64 / prgcalc1`). | `36` / `10` (`srvmissileb = clawsofthundernova`): Full-screen 360° Lightning Nova. | `143` / `83` (`srvmissilec = royalstrikechainlightning`, `pSrvHitFunc = 12`): Multi-target bouncing Chain Lightning (`aurarangecalc = 5 + lvl / 4`). |
| **Blades of Ice** (`Id 274`) | `39` / `9` (`prgcalc1 = 6`, `srvmissilea = bladesoficeexplode`): 6-subtile Ice Blast disc with Solid Freeze (`pSrvDmgFunc = 2, dParam1 = 100`). | `41` / `15` (`prgcalc2 = 12`, `srvmissileb = royalstrikechaosice`): 12-bolt radial Ice Ring (`EType = frze`) that bursts into `bladesoficeexplode` on hit (`pSrvHitFunc = 38, sHitPar1 = 4`). | `40` / `14` (`prgcalc3 = 9`, `srvmissilec = catapult cold ball on`): Launches a full **Frozen Orb** (`pSrvDoFunc = 15, pCltDoFunc = 19` $\rightarrow$ `catapult cold ball` + `catapult cold explosion`). |

---

## 5. Non-Consuming Whirlwind Capstone (`Omnislash`, `srvdofunc = 168`)

Because `srvdofunc = 168` (`Talic's Whirlwind`, paired with `srvstfunc = 38`, `cltstfunc = 31`, `cltdofunc = 45`, `srvstopfunc = 1`, `cltstopfunc = 1`) does **not** consume progressive charges, we used it on **`Omnislash`** (`Royal Strike` ID 280) as the Assassin's "keep your orbs" AoE melee capstone:
1. **Carries Held-Orb Stats on Every Hit**: Every spin hit automatically deals the Assassin's active `aurastat2` bonuses (`+%ED`, Fire, Cold, Lightning, or `-Monster Defense per Hit`) from her held orbs without consuming them.
2. **Automatic Resistance Shred via Escalation Hook (`calc6`)**:
   - `srvdofunc = 168` automatically casts the skill ID stored in `calc6` at skill level `calc2` (`10`) with probability `calc3` (`100%`) on every spin tick.
   - We wired `calc6` to a hidden classless Warcry skill **`Ass Whirl Shred`** (`srvdofunc = 68`, `srvmissilea = battlecry`, `aurafilter = 98304`, `auratargetstate = ass_whirl_shred`, `auralencalc = 75` frames) that shreds nearby enemies' `fireresist`, `coldresist`, and `lightresist` based on the Assassin's points in `Fists of Fire`, `Blades of Ice`, and `Claws of Thunder` (`-(skill('<ChargeSkill>'.blvl) + skill('Royal Strike'.blvl)/2)`).
   - *Design Note*: A curse-style `srvdofunc = 30` skill requires a cursor target and fails when triggered from `srvdofunc = 168`'s `calc6` hook, whereas a Warcry-style `srvdofunc = 68` + `battlecry` ring missile requires no target and reliably hits every monster around the spinning Assassin.

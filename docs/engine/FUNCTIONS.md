# D2R Engine Function Reference (`skills.txt` & `missiles.txt`)

This document is the cross-class master lookup for server/client skill functions, progressive finisher release functions, and missile controllers **verified through in-game experimentation** in Castalia.

> **Read First Before Authoring Any New Skill or Repurposing Any Stat:**
> - **[STATS_AND_PITFALLS.md](file:///home/grant/games/d2r/docs/engine/STATS_AND_PITFALLS.md)** — Canonical registry of all repurposed vanilla Stat IDs, reserved `states.txt` groups (`1..13`), reserved `automagic.txt` groups (`304..325`), and **explicitly verified FALSE / broken D2R C++ behaviors**.
> - **[DIAGNOSTIC_PROTOCOL.md](file:///home/grant/games/d2r/docs/DIAGNOSTIC_PROTOCOL.md)** — Mandatory 1-variable-at-a-time debugging protocol and temporary visible debug overlay technique.

## Per-Class Technical Docs
- **[docs/classes/paladin.md](file:///home/grant/games/d2r/docs/classes/paladin.md)** — Aura Mana Devotion, Frontal Cleave `Vengeance`, Bouncing Chain `Blessed Hammer`, S-Curve Party `Conviction`, `Smite` + `Stun Fatigue`.
- **[docs/classes/barbarian.md](file:///home/grant/games/d2r/docs/classes/barbarian.md)** — Stamina Pendulum, co-opted Ancients hooks (`srvdofunc = 168 / 170`), `Second Wind` flat Stamina heal, `Shield Slam`.
- **[docs/classes/assassin.md](file:///home/grant/games/d2r/docs/classes/assassin.md)** — 15m Charge-Up Orbs, `srvstfunc = 39` + `srvdofunc = 45` selective trap release, `Omnislash`.
- **[docs/classes/sorceress.md](file:///home/grant/games/d2r/docs/classes/sorceress.md)** — `group = 13` Elemental Stances, Stance Markers, Cross-Stance Fizzle, Cross-Tree Passives, `Conduction`, 7 Spell Archetypes.
- **[docs/classes/amazon.md](file:///home/grant/games/d2r/docs/classes/amazon.md)** — Amazon overhaul design blueprint.

---

## Quick Lookup: Verified Functions

### 1. Skill Functions (`skills.txt`)

| Column | ID | Engine Behavior | Verified Usage in Mod |
| :--- | :---: | :--- | :--- |
| `srvstfunc` | `23` | Starts a progressive Charge-Up melee attack. | All 5 Assassin Charge-Up skills (`Tiger Strike`, `Fists of Fire`, `Cobra Strike`, `Claws of Thunder`, `Blades of Ice`). |
| `srvdofunc` | `34` | Executes the Charge-Up melee hit and increments `aurastat1` (`progressive_*`) from `1 -> 2 -> 3`, applying `aurastate` for `auralencalc` frames. | All 5 Assassin Charge-Up skills. |
| `srvstfunc` | `39` | Self-buff start function executed at **Frame 0** of the cast animation (before the action frame). Evaluates `aurastatcalc1..6` while the old `aurastate` is still active, then overwrites `aurastate` on the caster with the skill's own `aurastat1..6` and `auralencalc`. | Paired Sentry Traps (`Fire Trauma`, `Wake of Fire Sentry`, `Charged Bolt Sentry`, `Lightning Sentry`, `Death Sentry`) to snapshot and expire **only** the paired `progressive_*` state over `12` frames. |
| `srvdofunc` | `45` | Summons a trap pet (`summon`, `pettype`, `petmax`) on the cast animation's action frame and evaluates `sumskill1..5` (`sumsk1calc..5calc`) and `passivestat1..5` onto the spawned pet. | All 5 Assassin Sentry Traps. |
| `srvdofunc` | `1, 42, 47, 50, 53` | The **only** melee `srvdofunc` handlers that call the engine's progressive charge release (`srvprgfunc1..3`, `cltprgfunc1..3`, `prgdam`). Note: `srvdofunc = 42` (`Dragon Talon`) hardcodes boot damage. | Normal Attack (`1`), `Dragon Talon` (`42`), `Dragon Claw` (`47`), `Dragon Tail` (`50`), `Dragon Flight` (`53`). |
| `srvdofunc` | `13` | Multi-strike weapon attack (`Zeal` / `Fend`). `calc1` = hit count, `Param2` = % animation frame rollback. **Ignores `finishing = 1`** (never consumes or releases progressive orbs, though held-orb `aurastat` unit stats apply to each swing). | Tested during `Omnislash` prototyping. |
| `srvstfunc` / `srvdofunc` | `31` / `67` | `Charge` sprint-strike (`cltstfunc = 25`, `cltdofunc = 37`). `calc1` = `%ED`, `calc2` = sprint velocity %. Setting `AttackNoMana = ""` prevents fallback to normal attack in melee range or during `localdelay`. | Barbarian `Shield Slam` (`Stun` ID 139, with `itypea1 = "shld"` and `EType = "stun"`). |
| `srvstfunc` / `srvdofunc` | `38` / `168` | `Talic's Whirlwind` (`cltstfunc = 31`, `cltdofunc = 45`, `srvstopfunc = 1`, `cltstopfunc = 1`). **Ignores `finishing = 1`** (keeps held orbs intact while applying their `aurastat` bonuses on every spin hit). Automatically casts the skill ID in `calc6` at level `calc2` (`calc3` = % chance) on spin ticks. | Barbarian `Whirlwind` (`calc6 = 433` `Bar Stamina Reflex` at `calc2 = 2`); Assassin `Omnislash` (`Royal Strike` ID 280, `calc6` = `Ass Whirl Shred`). |
| `srvdofunc` | `170` | `Korlic's Leap Attack` (`cltdofunc = 43` for Leap, `44` for Leap Attack). Performs a jump to target (`aurarangecalc` = max jump range, `calc2` = air speed %, `calc1` = knockback radius on Leap or `%ED` on Leap Attack) and **automatically casts the skill ID in `calc5` at skill level `calc6` upon landing**. | Barbarian `Leap` (`calc5 = 433, calc6 = 1`) and `Leap Attack` (`calc5 = 433, calc6 = 10`) to trigger `Bar Stamina Reflex` on landing. |
| `srvdofunc` | `18` | Self/party buff (`Chilling Armor` / `Battle Cry` style) applying `aurastate` and `aurastat1..6` for `auralencalc` frames. | Barbarian `Bloodlust` (`Grim Ward` ID 150, setting `aurastat2 = skill_chillingarmor = 1` marker and `hpregen` drain). |
| `srvdofunc` | `30` | Radial curse/state application within `aurarangecalc` subtiles (`aurafilter` = target filter), applying `auratargetstate` for `auralencalc` frames. When combined with **`auraevent1 = "install"`**, **`auraeventfunc1 = "3"`** (`Shiver Armor` reflection), and **`EType = "stam"`**, every affected monster immediately reflects flat Stamina drain back onto the caster on state install! | `Bar Stamina Reflex` (`Id 433`, cast by `Leap`, `Leap Attack`, and `Whirlwind`). |
| `srvdofunc` | `68` | Warcry radial pulse (`Battle Cry` / `Howl` / `Battle Command`). Spawns `srvmissilea` in a ring around the caster with no target required; applies `aurastate` (self) and `auratargetstate` (targets) with `aurastat1..6`. | `Second Wind` (`Id 131`, 2-frame normalized `staminarecoverybonus` flat Stamina heal), `Enduring Cry` (`Id 142`), `Ass Whirl Shred`. |

### 2. Progressive Finisher Release Functions (`skills.txt`)

| `srvprgfunc` | `cltprgfunc` | Missile Column (`1 / 2 / 3`) | Engine Behavior & Parameters |
| :---: | :---: | :---: | :--- |
| `36` | `10` | `srvmissilea / b / c` | Spawns a 360° radial Nova of the missile. **Caveat**: Hardcodes a full-screen (~20-subtile) Nova override in C++, ignoring shorter `Range` values in `missiles.txt`. Used on `Claws of Thunder` Charge 2 (`clawsofthundernova`). |
| `37` | `11` | `srvmissilea / b / c` | Spawns a fan of Charged Bolts. `prgcalc` sets the direction step divisor (`64 / prgcalc` = total bolts spawned). Used on `Claws of Thunder` Charge 1 (`clawsofthunderbolt`). |
| `39` | `9` | `srvmissilea / b / c` | Spawns a circular disc/patch of stationary or ground missiles around the target with radius = `prgcalc` (in subtiles). Used on `Fists of Fire` Charges 1 & 2 (`fistsoffireexplode`, `fistsoffirefirewall`) and `Blades of Ice` Charge 1 (`bladesoficeexplode`). |
| `40` | `14` | `srvmissilea / b / c` | Spawns a single target-point controller or directional orb missile (`royalstrikemeteorcenter` on `Fists of Fire` Charge 3; `catapult cold ball on` Frozen Orb on `Blades of Ice` Charge 3). |
| `41` | `15` | `srvmissilea / b / c` | Spawns a 360° ring of missiles with angular step `prgcalc` (`prgcalc = 36` $\rightarrow$ 10° step = 36 missiles; `prgcalc = 12` $\rightarrow$ 12 missiles). **Strictly obeys `Vel` and `Range` in `missiles.txt`**, making it ideal for custom-radius shockwaves (`Tiger Strike` 7-subtile shockwave, `Cobra Strike` 7-subtile Soul-Hex wave, `Blades of Ice` Charge 2 radial ice bolts). |
| `143` | `83` | `srvmissilea / b / c` | Fires a Chain Lightning missile (`royalstrikechainlightning`) on Finisher release. Used on `Claws of Thunder` Charge 3. |

### 3. Missile Functions (`missiles.txt`)

| Function Column | ID | Engine Behavior | Verified Usage in Mod |
| :--- | :---: | :--- | :--- |
| `pSrvDoFunc` / `pCltDoFunc` | `1` / `1` | Standard linear missile movement (`Vel`, `VelLev`, `MaxVel`, `Accel`, `Range`). | Base bolts, shockwave rings, shurikens (`bladefragment3`). |
| `pSrvDoFunc` | `2` | Linear movement that **spawns `SubMissile1` every frame while `SrvCalc1 > 0`**. Because `SubMissile1` inherits the parent's coordinates and direction, setting `SrvCalc1 = (cond) ? 1 : 0` (or gating `SubMissile1`'s `Range`) attaches a conditional payload to a piercing projectile. | `sucfireball` $\rightarrow$ `sucfireballexplode` (stun); `sentrychargedbolt` $\rightarrow$ `sentryspikeinair` (Life Tap); `frozenhorror arcticblast1` $\rightarrow$ `frozenhorror arcticblast2` (freeze); `sentrylightningbolt` $\rightarrow$ `sentrylightningbolt2` (blind); `unholybolt2..4` $\rightarrow$ `undeadmissile2..4` (defense shred). |
| `pSrvDoFunc` | `14` | Stationary ground controller (`grimwardsmall`). Every `Param1` frames, executes `skills.txt` `srvdofunc = Param2` (e.g. `30` = curse/state aura) using the skill named in `Skill`. | `sentryspikeonground` (`Param1 = 1`, `Param2 = 30`, `Skill = BoltSentry`) to apply `lifetap` in a 5-subtile radius on `Soul Siphon Sentry` Charge 3 impacts. |
| `pSrvDoFunc` / `pCltDoFunc` | `15` / `19` | `Frozen Orb` main carrier (`Param1` = spawn rate, `Param2` = direction index increment; spawns `SubMissile1` / `CltSubMissile1` while flying). | `catapult cold ball on` (`Blades of Ice` Charge 3 Finisher). |
| `pSrvDoFunc` / `pCltDoFunc` | `16` / `20` | `Frozen Orb` final radial nova bolt (`Param1` = activation frame, `Param2` = periodic path delay). | `catapult cold explosion` (spawned on expiration of `catapult cold ball on`). |
| `pSrvHitFunc` / `pCltHitFunc` | `1` / `1` | Fireball radial AoE splash damage (`sHitPar1` = radius, or `0` to read `Skill`'s `calc1`; requires `EType`, `ResultFlags = 5`, `HitFlags = 2`). Client spawns `CltHitSubMissile1` in disc `cHitPar1` with density `cHitPar2`. | `Cinder Lance` (`firebolt`), `Pyre Hydra` (`hydramissile`). |
| `pSrvHitFunc` / `pCltHitFunc` | `12` / `16` | Chain Lightning bounce (`sHitPar1` / `cHitPar1` = bounce search radius, or `0` to use `aurarangecalc`). | `royalstrikechainlightning`, `throwingstar` (`Shuriken`). |
| `pSrvHitFunc` | `21` | Applies the `auratargetstate` (and `aurastat1..6`) of the skill named in `Skill` to any unit hit. **Caveat**: Skips direct missile damage, so use on a secondary `SubMissile1` spawned by a `pSrvDoFunc = 2` parent missile. | `undeadmissile2..4` (`Ass Cobra Hex 1..3`), `sentrylightningbolt2` (`dimvision`). |
| `pSrvHitFunc` / `pCltHitFunc` | `29` / `30` | `Frozen Orb` expiration burst (spawns `HitSubMissile1` / `CltHitSubMissile1` in a 360° ring with density step `sHitPar1` / `cHitPar1`). | `catapult cold ball on` $\rightarrow$ `catapult cold explosion`. |
| `pSrvHitFunc` / `pCltHitFunc` | `38` / `46` | Radial burst of `HitSubMissile1` / `CltHitSubMissile1` on impact. Count = `sHitPar1 + lvl * sHitPar2` (or `Skill`'s `calc4` when both are `0`). **Negative baseline trick**: Setting `sHitPar1 = -4, sHitPar2 = 1` spawns `0` submissiles when `lvl <= 4` and `6` submissiles when `lvl = 10`! | `vampirefireball` $\rightarrow$ `sucfireball`; `royalstrikechaosice` $\rightarrow$ `bladesoficeexplode`; `sentryspikeinair` $\rightarrow$ `sentryspikeonground` (`sHitPar1 = -4, sHitPar2 = 1`). |
| `pCltDoFunc` | `48` | Client-side `erruption center` controller (`pSrvDoFunc = 25`). Spawns `CltSubMissile1` / `CltSubMissile2` randomly within radius `cltcalc1` every `cltcalc2` frames of the referenced `Skill`. Evaluates `stat('...'.accr)` in `cltcalc1`/`cltcalc2` on the client! | `Skyfall` (`skyfall_crater_clt`), `Cinder Lance` (`cinder_lance_crater`). |
| `pSrvDmgFunc` | `2` | Converts `dParam1`% (`100` = 100%) of Cold Length (`ELen`) into Solid Freeze duration. | `bladesoficeexplode`, `royalstrikechaosice`, `frozenhorror arcticblast2`. |
| `pSrvDmgFunc` | `7` | Applies Stun duration of `dParam1` frames on hit (requires `ResultFlags = 4` or `5`, `HitFlags = 2`). | `sucfireballexplode` (`Fire Sentry` 3-Orb Capstone). |

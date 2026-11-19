# Sorceress Technical Reference: Elemental Stances, Cross-Stance Fizzle & Spell Archetypes

Source implementation:
- [tools/mod_builder/sorc/registry.py](file:///home/grant/games/d2r/tools/mod_builder/sorc/registry.py) (30-slot 1:1 skill map)
- [tools/mod_builder/sorc/engine.py](file:///home/grant/games/d2r/tools/mod_builder/sorc/engine.py) (Declarative table-patch & variant engine)
- [tools/mod_builder/sorc/patterns.py](file:///home/grant/games/d2r/tools/mod_builder/sorc/patterns.py) (Indexed server/client functions, stance markers & 7 spell archetypes)
- [tools/mod_builder/sorc/specs/](file:///home/grant/games/d2r/tools/mod_builder/sorc/specs) (Per-skill JSON table patches)

---

## 1. The 1:1 Save-Compatible Row Rule

D2R's `.d2s` save format expects exactly 30 `charclass = "sor"` rows at vanilla `*Id` `36..65`. Adding a 31st `charclass = "sor"` row corrupts character saves. Therefore:
- Every Sorceress skill in Castalia reuses one of the 30 vanilla Sorceress rows 1:1 (defined in `registry.SLOTS`).
- Helper skills created via `_clone` in `specs/_shared.json` or individual specs must always clear `"charclass": ""`.

---

## 2. Mutually Exclusive Elemental Stances (`srvdofunc = 18`, `group = 13`)

Each tree features one castable timed **Elemental Stance** (`70s` at Lvl 1 $\rightarrow$ `260s` at Lvl 20) using `srvdofunc = 18` and sharing `group = 13` in `states.txt` so activating any stance automatically replaces the previous stance:

| Tree | Stance (`slug` $\rightarrow$ Row) | `states.txt` State | Marker Stat (`aurastat6 = 1`) | Boons (`Lvl 1 -> 20`) | Busts (`Lvl 1 -> 20`) | Melee Retaliation (`damagedinmelee`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fire** | **Conflagration** (`conflagration` $\rightarrow$ `Enchant` 52) | `sorc_stance_fire` | `skill_handofathena` | `+5% -> +75%` Fire Dmg<br>`+5% -> +40%` FCR<br>`+30% -> +258%` Mana Regen | `+5% -> +50%` Phys Dmg Taken<br>`-1 -> -10` Life/sec Drain | `auraeventfunc1 = 3` (Fire damage scaled by stance lvl & **Kindling**) |
| **Cold** | **Cryostasis** (`cryostasis` $\rightarrow$ `Frozen Armor` 40) | `sorc_stance_cold` | `skill_frenzy` | `+5% -> +75%` Cold Dmg<br>`+3% -> +25%` Phys DR<br>`+10% -> +200%` Defense | `-5% -> -50%` Walk/Run Speed<br>`-5% -> -30%` FCR | `auraeventfunc1 = 2` (Freezes attacker for `1.2s -> 3.5s`, scaled by **Brittle Touch**) |
| **Ltng** | **Overcharge** (`overcharge` $\rightarrow$ `Energy Shield` 58) | `sorc_stance_light` | `skill_decrepify` | `+5% -> +75%` Ltng Dmg<br>`+5% -> +40%` FRW<br>`+5% -> +40%` FHR | `-5% -> -75%` Fire Resist<br>`-5% -> -75%` Cold Resist | `auraeventfunc1 = 3` (Lightning damage scaled by stance lvl & **Conduction**) |

### Stance Cast Animation (`sorceress_state_machine.json`)
- All three stances use `anim = "SQ"`, `seqtrans = "SC"`, `seqnum = 4/6/13`, bound via `statemachine.py` to `PLRMODE_SEQUENCE` (`modeId = 18`) playing `<wclass>_skill2` with `loopCount = 6` (a deliberate focusing posture).
- All three stance states set `restrict = 1` in `states.txt` so stance-gated movement skills (`restrict = 2`, `State1 = sorc_stance_<tree>`) can be cast only while that tree's stance is active.

---

## 3. Stance Detection & Cross-Stance Fizzle Formulas

Because each stance sets a dedicated unit stat (`skill_handofathena`, `skill_frenzy`, or `skill_decrepify`) to `1` in `aurastat6`, any active spell or client missile controller (`pCltDoFunc = 48`) can inspect which stance is active in real time:

1. **Matching-Stance Empowerment**:
   - Fire spells test `(stat('skill_handofathena'.accr) > 0)` to unlock bonus projectiles, wider explosion radii, or 10x longer molten wakes.
   - Cold spells test `(stat('skill_frenzy'.accr) > 0)`.
   - Lightning spells test `(stat('skill_decrepify'.accr) > 0)`.
   - For turret summons (`Pyre Hydra`), the stance state is snapshotted at cast time via `sumsk1calc = (stat('skill_handofathena'.accr) > 0) ? (lvl + 30) : lvl`, and `HydraMissile` tests `(lvl > 30)`.
2. **Cross-Stance Fizzle Rule**:
   - Casting an offensive spell from Tree A while either of the two opposing stances (Tree B or Tree C) is active causes the spell to **fizzle out immediately** (`Range = 1` or `0`, `Radius = 0`):
     - **Fire Spells**: `((stat('skill_frenzy'.accr) + stat('skill_decrepify'.accr)) > 0) ? 1 : (<normal_range>)`
     - **Cold Spells**: `((stat('skill_handofathena'.accr) + stat('skill_decrepify'.accr)) > 0) ? 1 : (<normal_range>)`
     - **Lightning Spells**: `((stat('skill_handofathena'.accr) + stat('skill_frenzy'.accr)) > 0) ? 1 : (<normal_range>)`

---

## 4. The 7 Reusable Offensive & Utility Spell Archetypes

| Slot Role | Fire Implementation (`done`) | Cold & Lightning Counterparts | `skills.txt` Functions | `missiles.txt` Architecture |
| :--- | :--- | :--- | :---: | :--- |
| **1. Line 1 (Levelling)** | **Cinder Lance** (`Fire Bolt` 36) | **Frost Dart** (`Ice Bolt` 39)<br>**Static Lance** (`Lightning` 49) | `srvdofunc = 1`<br>`cltdofunc = 1` | Uses `srvmissile`/`cltmissile`; scales velocity & reach via `VelLev`; `pSrvHitFunc = 1` + `CltHitSubMissile1` (`erruption center`, `pCltDoFunc = 48`) triggers an AoE burst in matching stance. |
| **2. AoE 1 (Levelling)** | **Pyroclasm** (`Fire Ball` 47) | **Hoarfrost Burst** (`Frost Nova` 44)<br>**Pulse Ring** (`Nova` 48) | `154 / 99` *(Ring of Fire)* or `22 / 25` *(Nova)* | Caster-centered 360° ring. On `154/99`, `calc2` scales bolt count (`5..13`) and `VelLev` scales radius (`Accel = ""`). On `22/25`, `calc3`/`cltcalc1` Velocity Adder scales ring radius. |
| **3. Combo (CC / AoE)** | **Backdraft** (`Fire Wall` 51) | **Permafrost** (`Ice Blast` 45)<br>**Tesla Field** (`Static Field` 42) | `srvstfunc = 14`<br>`srvdofunc = 28`<br>`cltstfunc = 17`<br>`cltdofunc = 28` | Cursor maker missile (`pSrvHitFunc = 11`) chains into center controller (`pCltDoFunc = 48` ground patch) while applying `auratargetstate` slow/debuff and periodic pulses across `calc1` radius. |
| **4. Utility (Mobility)** | **Flashfire** (`Blaze` 46) | **Glacier Step** (`Chilling Armor` 60)<br>**Phase Step** (`Teleport` 54) | `23 / -` *(Sprint)* or `166 / 104` *(Blade Warp)* | Stance-gated (`restrict = 2`, `State1 = sorc_stance_<tree>`). `166/104` (`lob=1, warp=1, calc5=1`) blinks along a `pSrvDoFunc=2, pCltDoFunc=3, pSrvHitFunc=42` path and detonates an arrival nova (`pSrvDoFunc=25, pCltDoFunc=48`). |
| **5. AoE 2 (Power Spike)** | **Skyfall** (`Meteor` 56) | **Whiteout** (`Blizzard` 59)<br>**Stormcall** (`Thunder Storm` 57) | `srvdofunc = 28`<br>`cltdofunc = 28` | Cursor delayed impact / bombardment controller (`calc1` / `cltcalc1` radius) spawning lingering ground damage (`HitSubMissile1`) and client crater patch (`CltHitSubMissile2`, `pCltDoFunc = 48`). |
| **6. Line 2 (Boss Killer)** | **Brimstone Lance** (`Inferno` 41) | **Icicle Spear** (`Glacial Spike` 55)<br>**Spearbolt** (`Chain Lightning` 53) | `1 / 1` *(Piercing Wake)* or `26 / 27` *(Chain)* | All-piercing heavy projectile (`CollideKill = 0, Pierce = 1, LastCollide = 1, NextDelay = 4`) with `pSrvDoFunc = 2, pCltDoFunc = 3` dropping a damaging ground wake (`pSrvDoFunc = 5, pCltDoFunc = 5`) that lasts 10x longer in matching stance. |
| **7. Capstone (Lvl 40)** | **Pyre Hydra** (`Hydra` 62) | **Frozen Orb** (`Frozen Orb` 64)<br>**Heaven's Wrath** (`Charged Bolt` 38) | `14+144 / 17` *(Hydra)*, `1 / 29` *(Orb)*, or `28 / 28` | Zero-cooldown Level 40 capstone with non-linear tier scaling, two tree synergies, stance-empowered AoE geometry, and cross-stance fizzle. |

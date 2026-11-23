# Conduction Co-Op Iteration Log (Paladin & Assassin)

Tracks in-game QA verification, engine discoveries, and fixes for Sorceress **Conduction** (`skill_enchant` = `1` Fire / `2` Lightning / `3` Cold) co-op skill enhancements.

---

## Verified Engine Rules Discovered
1. **Conduction Marker Stat (`skill_enchant`, ID 165 — NOT `modifierlist_level`, ID 351):**
   - `modifierlist_level` (`Signed=""`) is an unsigned monster-affix internal stat; D2R ignores it in player skill calcs (`stat('modifierlist_level'.accr)` always returned `0`).
   - `skill_enchant` (`Signed=1, Send Bits=12`, unused across all skills) works 100% reliably across `skills.txt`, `missiles.txt`, and `skilldesc.txt`.
2. **QA Solo-Test Ring (`QA Conduction`, ID 435):**
   - `srvdofunc = 65` requires `auratargetstate = sorc_conduction`, `aurafilter = 73731`, `InGame = 1`, `InTown = 1`, `skilldesc = lightning mastery`, and `cubemain.txt` `mod 1 = aura` requires the numeric skill ID (`435`).
3. **Fist of the Heavens (`fistoftheheavensdelay`, `srvdofunc = 80` / `pSrvHitFunc = 22`) Sub-Missile Rules:**
   - `pSrvDoFunc = 15` (`frozenorb`) overwrites `dwParam` where `srvdofunc = 80` stores the target monster GUID — breaking `pSrvHitFunc = 22` (solo skybolt + Holy Bolts).
   - `pSrvHitFunc = 38` does NOT client-send `HitSubMissile1` even with `ClientSend = 1`; it requires the client mirror (`pCltHitFunc = 46`, `cHitPar1 = 16`, `CltHitSubMissile1 = foh_conduction_nova`).
   - HD `missiles.json` model name for Nova is `"electric_nova"`, NOT `"nova"`.
   - `foh_conduction_nova` must clear `Accel = ""` (inherited `-1000` from `nova` kills velocity on frame 1 when spawned via `pSrvHitFunc = 38`).
   - `pSrvDoFunc = 2` / `pCltDoFunc = 3` (trail emitter) preserves `dwParam` (keeping `pSrvHitFunc = 22` + Holy Bolts intact), but requires `Vel >= 1` to emit `SubMissile1`.

---

## In-Game Playtest Matrix

### Paladin
| Skill | Status | Notes |
| :--- | :--- | :--- |
| **Holy Fire** (Fire `== 1`) | **PASSED** | Verified +2.7 yd radius tooltip/aura + faster `perdelay` (tested at `10`, restored to balanced `35`). |
| **Holy Freeze** (Cold `== 3`) | **PASSED** | Verified +2.7 yd radius + `+15%` deeper slow on tooltip & in-game. |
| **Holy Shock** (Ltng `== 2`) | **PASSED** | Verified +2.7 yd radius + faster `perdelay = 35`. |
| **Vengeance** (Any `>= 1`) | **PASSED** | Verified `156° -> 240°` tooltip cleave arc, `+2` sub-tiles reach, and `2×` Cold chill under Cold ring. |
| **Fist of the Heavens** (Ltng `== 2`) | **PASSED (Iter 8)** | Pristine vanilla skybolt + radial Holy Bolts + crackling `electric_nova` arcs trailing every bolt under Lightning Conduction (0 effect solo). |

#### Fist of the Heavens Iteration History
- **Iter 1 (`pSrvDoFunc=17, Param1=10`):** No Nova — expired at `Range=10` before firing.
- **Iter 2 (`pSrvDoFunc=15, pCltDoFunc=19, pSrvHitFunc=38, missiles.json="nova"`):** Server Nova dealt AoE damage to non-demons, but client invisible (`"nova"` wrong HD asset) AND `pSrvDoFunc=15` clobbered `dwParam` (no Holy Bolts).
- **Iter 3 (`pSrvDoFunc=15, pCltDoFunc=1, ClientSend=1, missiles.json="electric_nova"`):** Server Nova dealt damage, but `pSrvHitFunc=38` does not client-send without `pCltHitFunc=46`.
- **Iter 4 (`pSrvDoFunc=15, pCltDoFunc=19, pCltHitFunc=46, missiles.json="electric_nova"`):** **Bright 360° Electric Nova visible & dealing damage**, but ring-off FoH dealt 0 damage because `pSrvDoFunc=15` clobbered `dwParam`.
- **Iter 5 (`pSrvDoFunc=2, pCltDoFunc=3, SrvCalc1=9, CltCalc1=9, Vel=0`):** Holy Bolts restored (`dwParam` preserved!), but `Vel=0` prevented trail emitter `pSrvDoFunc=2` from spawning `foh_conduction_trigger`.
- **Iter 6 (`pSrvDoFunc=2, pCltDoFunc=3, SrvCalc1=9, CltCalc1=9, Vel=1, MaxVel=1`):** Main strike + 3 Holy Bolts work cleanly, but no Nova — `srvdofunc=80` spawns `fistoftheheavensdelay` with `(dx,dy)=(0,0)` so trail emitter `pSrvDoFunc=2` never registers movement.
- **Iter 7 (`pSrvDoFunc=17, pCltDoFunc=24, Param1=8, Param2=0, Vel=""`):** Main strike + 3 Holy Bolts work cleanly, but `cairnstones` did not emit `SubMissile1` on `fistoftheheavensdelay`.
- **Iter 8 (CURRENT — Vanilla `fistoftheheavensdelay` + `fistoftheheavensbolt` trail emitter):** Restores `fistoftheheavensdelay` to 100% pristine vanilla (`pSrvDoFunc=1, pCltDoFunc=1, pSrvHitFunc=22`), and attaches proven `pSrvDoFunc=2 / pCltDoFunc=3` (`SrvCalc1=5, CltCalc1=5`) onto the moving `fistoftheheavensbolt` (`Vel=18`) to emit crackling `foh_conduction_nova` (`electric_nova`, `Size=3, NextDelay=12, Range=(skill_enchant==2)?10:0`) along every radiating bolt!

### Assassin
| Skill | Status | Notes |
| :--- | :--- | :--- |
| **Fire / Ice / Lightning Sentry** | **PASSED (0-Orb 3-Charge)** | Confirmed 0-orb full 3-charge deployment in-game! Engine limit confirmed (Iter 1 & 2): `srvstfunc=39` always clears `aurastate = progressive_*` even when `auralencalc=0`; restored clean `auralencalc=12`. |
| **Blades of Ice** (Cold `== 3`) | **PASSED** | Confirmed good in-game: Charge 3 Frozen Orb (`catapult cold ball on`) `+60%` flight (`30 -> 48`) + wider Charge 1/2 freeze & range. |
| **Electrocute** (Ltng `== 2`) | **PASSED** | Confirmed acceptable in-game: Charge 2 Nova widened (`13 -> 22`) + Charge 3 Chain Lightning (`royalstrikechainlightning`) trails real-damage `electric_nova` sparks (`cot_conduction_spark`). |
| **Flamestrike** (Fire `== 1`) | **PASSED (Iter 8 — Pyroclasm Burst)** | Replaced broken Charge 3 Meteor (`auralencalc=22500` incompatibility) with proven `srvprgfunc3=41 / cltprgfunc3=15` **Pyroclasm Burst** (`fof_pyroclasm_ball`, exploding `fireball`s with `fireexplosion2` splash): **8** Fireballs (`Range=12`) solo -> **16** Fireballs (`Range=18`, `2×` density!) under Fire Conduction! Charge 1 (`fistsoffireexplode`) reverted clean. |

### Follow-Up TODOs
- [ ] Audit all Assassin charge-up finisher release radii, bolt counts, and travel ranges (solo & conducted) to ensure consistent tier progression and avoid overpowered AoE coverage (also tracked in `docs/engine_reference/assassin_charges_and_traps.md`).

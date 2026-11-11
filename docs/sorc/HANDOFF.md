# Sorceress Overhaul — Session Handoff

## 1. Where We Are
- **Branch / Commit**: `main` at `445f8a5` (`final4: conservative capped scaling; Cold juggernaut; Fire life drain`).
- **Build & Verify**: `python3 /home/grant/games/d2r/bin/d2r-sorc build` (runs `skills` build + all 8 verification suites).
- **Test Character Reset**: `python3 /home/grant/games/d2r/bin/d2r-sorc char` (refunds all 118 skill points on `SORC.d2s`).
- **Status Dashboard**: See [STATUS.md](file:///home/grant/games/d2r/docs/sorc/STATUS.md) and [README.md](file:///home/grant/games/d2r/docs/sorc/README.md).

## 2. Completed & Locked-In Skills
1. **All 3 Stances (`done`, variant `final4`)**:
   - **Conflagration** (`conflagration`, replaces `Enchant` ID 52, Fire R3C2)
   - **Cryostasis** (`cryostasis`, replaces `Frozen Armor` ID 40, Cold R4C1)
   - **Overcharge** (`overcharge`, replaces `Energy Shield` ID 58, Lightning R4C2)
   - *Mechanics*: `srvdofunc=18`, mutually exclusive via `states.txt` `group=13`, 6-loop `skill2` cast animation (`_shared` variant `anim_v3`), linear Boon/Bust scaling with caps, `Echo` cross-stance boon carry, and `damagedinmelee` retaliation (`auraeventfunc1=2/3`).
2. **Retaliation Support Passives (`wip`, variant `final2`)**:
   - **Kindling** (`kindling`, ID 37 `Warmth`), **Brittle Touch** (`brittle_touch`, ID 50 `Shiver Armor`), **Conduction** (`conduction`, ID 43 `Telekinesis`).
   - Pure passives (`passive=1`) scaling stance melee retaliation damage (`+10%/lvl`) or freeze length (`+5%/lvl`), with working Current/Next Level tooltips.
3. **Dials (`r9_no_vanilla_passive`)**:
   - **Echo** (`afterglow`, ID 63 `Lightning Mastery`) is wired into all 3 stances; **Ignition** (`ignition`, ID 61) and **Equilibrium** (`equilibrium`, ID 65) have vanilla mastery stats stripped and await dial formula hookup.
4. **Fire Line 1: Cinder Lance (`wip`, variant `p3_scaling`)**:
   - Replaces `Fire Bolt` (ID 36, Fire R1C2, Req Lvl 1).
   - Pierces all enemies (`CollideKill=0`) and scales velocity and reach per level (`Vel=18`, `VelLev=6`, `MaxVel=40`, `Range=26`).

## 3. Hard Engine Rules Discovered
- **Never add a 31st `charclass="sor"` skill** (corrupts `.d2s` saves). All 30 Sorceress skills reuse the 30 vanilla rows 1:1 ([registry.py](file:///home/grant/games/d2r/tools/mod_builder/sorc/registry.py)).
- **Investment Must Change Feel**: Every active skill must scale a tangible geometry/feel parameter with skill points (velocity, range/radius, projectile count, or secondary duration), not just damage.
- **Stance Constraints**:
  - `srvdofunc=18` applies only ONE state and does NOT fire offensive aura events (`doactive`, `domissileattack`, `domissiledamage`), nor does it spawn `srvmissilea`.
  - Defensive events (`damagedinmelee`, `hitbymissile`) DO work on `srvdofunc=18`.
  - However, **active spells** CAN read whether a stance is active via `stat('skill_handofathena'.accr)` or similar marker stats if needed, or scale directly with skill level / calcs!
- **Tooltip Next-Level Rule**: In `skilldesc.txt`, `skill('X'.lvl)` evaluates only current level in both Current and Next tooltip sections. Always use `lvl` (or `clc1..6` referencing `lvl`) for the skill's own level so "Next Level" displays `lvl + 1`.
- **Skilldesc Line Limit**: `skilldesc.txt` only has `descline1..6`; overflow additional lines into `dsc2line1..5`.

## 4. Next Up: Remaining Fire Tree Skills (in Unlock Order)
1. **Lvl 8 AoE 1 — `Pyroclasm` (`pyroclasm`, replaces `Fire Ball` ID 47, R2C1)**:
   - Instant ring blast centered on caster with knockback and level-scaling radius/missile count.
2. **Lvl 8 Utility — `Flashfire` (`flashfire`, replaces `Blaze` ID 46, R2C3)**:
   - Mobility / burning trail utility.
3. **Lvl 16 Combo — `Backdraft` (`backdraft`, replaces `Fire Wall` ID 51, R3C1)**:
   - Ground fire patch + crowd control / combo.
4. **Lvl 16 Dial — `Ignition` (`ignition`, replaces `Fire Mastery` ID 61, R3C3)**:
   - Passive boosting active stance boons by `+2%/lvl`.
5. **Lvl 24 AoE 2 — `Skyfall` (`skyfall`, replaces `Meteor` ID 56, R4C3)**:
   - Delayed heavy AoE impact on cursor.
6. **Lvl 32 Line 2 — `Brimstone Lance` (`brimstone_lance`, replaces `Inferno` ID 41, R5C2)**:
   - Heavy piercing spear / multi-projectile boss killer.
7. **Lvl 40 Capstone — `Pyre Hydra` (`pyre_hydra`, replaces `Hydra` ID 62, R6C2)**:
   - Multi-head summon at cursor (no cooldown).

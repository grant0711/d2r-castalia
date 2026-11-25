# Paladin — Aura Mana Devotion, Stun Fatigue & Reworked Combat

- **Declarative Specs:** [`tools/mod_builder/classes/paladin/`](file:///home/grant/games/d2r/tools/mod_builder/classes/paladin) (`registry.py`, `engine.py`, `state.json`, `specs/_shared.json`, `specs/*.json`, `sprites.py`)
- **CLI:** `./bin/d2r-class pal <map|show|variant|set|use|build|check|test>`

---

## 1. Engine Architecture & Core Mechanics

### Aura Mana Devotion (`srvdofunc = 65`) vs. Zero-Mana Recovery Stances
- **Periodic Mana Upkeep:** Active combat and defensive auras drain Mana every `perdelay` tick (`50` frames = `2.0s`; `10` frames = `0.4s` on `Thorns`) and scale both power and radius down to `0` at `0%` Mana so aura strength tracks current Mana devotion.
- **Zero-Mana Recovery Stances (`Prayer`, `Meditation`, `Redemption`):** Cost `0` Mana/sec so the Paladin switches actively between recovery stances and combat auras (`Meditation` trades `-50%` weapon `%ED` for high Mana recovery; `Redemption` grants active LAEK/MAEK + corpse redemption).

### Reworked Combat & Aura Highlights (See Live Matrix Below for Exact Values)
- **Smite (`smite`) & Charge (`charge`):** Both integrate global **Stun Fatigue** (`shortparam1`, `100% -> 75% -> 50% -> 25% -> 0%` stun across consecutive uninterrupted melee attacks; reset on melee hit taken via `Stun Reset` or after 5s) and **Cold Conduction** duration scaling. `Smite` clears `ResultFlags` to remove knockback lock; `Charge` (`srvdofunc = 67`) hardcodes Knockback in D2R C++ (see [`STATS_AND_PITFALLS.md`](file:///home/grant/games/d2r/docs/engine/STATS_AND_PITFALLS.md)).
- **Vengeance (`vengeance`):** `srvstfunc = 35`, `srvdofunc = 164` frontal arc cleave with single-element synergies from `Resist Fire / Cold / Lightning`.
- **Blessed Hammer (`blessed_hammer`):** `1.0s` cooldown bouncing Chain Hammer (`srvdofunc = 26`, `cltdofunc = 27`, `pSrvDmgFunc = 7` stun synergized by `Smite`).
- **Conviction (`conviction`):** Friendly party & mercenary elemental damage aura (`+50%` self / `+33%` party Fire/Cold/Lightning damage, zero enemy resist pierce; `descfunc = 75`).
- **Fist of the Heavens (`fist_of_the_heavens`):** True Lightning damage variance + `foh_conduction_nova` shock burst when Conducted.

---

<!-- AUTO-GENERATED-SPECS:START -->
## Live Skill Matrix (`30 / 30 done` — Auto-Generated from JSON Specs & Compiled Tables)

> **Do not hand-edit this section.** Generated automatically by `tools/mod_builder/classes/doc_gen.py` during `d2r-build-mod.py skills` from `tools/mod_builder/classes/paladin/` and compiled `skills.txt`/`skills.json`.

### Combat (Page 1)

| r.c | Lvl | Skill (`slug`) | Status / Variant | Engine Hooks | In-Game Description |
| :---: | :---: | :--- | :--- | :--- | :--- |
| 1.1 | 1 | **Sacrifice** (`sacrifice`) | `done` / `final` | `func 29/64` | increased accuracy and damage / at the cost of life |
| 1.3 | 1 | **Smite** (`smite`) | `done` / `final` | `func -/150` `RF:none` `StunFatigue` `Conduction` | strikes an enemy with your shield, bypassing defense / to always hit and briefly stun the target |
| 2.2 | 8 | **Holy Bolt** (`holy_bolt`) | `done` / `final` | `mag` | a bolt of divine energy / that damages demons and undead / or heals allies |
| 3.1 | 16 | **Zeal** (`zeal`) | `done` / `final` | `func 37/13` `Conduction` | allows you to attack multiple adjacent enemies / with a single attack |
| 3.3 | 16 | **Charge** (`charge`) | `done` / `final` | `func 31/67` `stun` `StunFatigue` `Conduction` | charge into battle and attack an enemy |
| 4.1 | 24 | **Vengeance** (`vengeance`) | `done` / `final` | `func 35/164` `cold` `Conduction` | cleaves enemies in a frontal arc, adding fire, lightning, / and cold damage to each successful attack |
| 4.2 | 24 | **Blessed Hammer** (`blessed_hammer`) | `done` / `final` | `func -/26` `CD 1s` `mag` `Conduction` | hurls an ethereal hammer that bounces between nearby enemies, / dealing magic damage, knocking back, and stunning targets |
| 5.1 | 32 | **Conversion** (`conversion`) | `done` / `final` | `func 32/79` `state:conversion` `Conduction` | converts monsters to fight against / other foul demons and beasts |
| 5.3 | 32 | **Holy Shield** (`holy_shield`) | `done` / `final` | `func 36/18` `state:holyshield` `Conduction` | enhances your shield with divine power, increasing blocking / and reducing physical and magic damage taken |
| 6.2 | 40 | **Fist of the Heavens** (`fist_of_the_heavens`) | `done` / `final` | `func -/80` `CD 1.4s` `ltng` `Conduction` | lightning strikes your target as holy bolts / seek out nearby enemies |

### Offensive (Page 2)

| r.c | Lvl | Skill (`slug`) | Status / Variant | Engine Hooks | In-Game Description |
| :---: | :---: | :--- | :--- | :--- | :--- |
| 1.1 | 1 | **Might** (`might`) | `done` / `final` | `func -/65` `aura` `state:might` `Conduction` | when active, aura increases the damage / done by you and your party |
| 2.2 | 8 | **Holy Fire** (`holy_fire`) | `done` / `final` | `func -/66` `aura` `state:holyfire` `fire` `Conduction` | when active, aura damages nearby enemies / with heavenly flames / adds fire damage to your attack |
| 2.3 | 8 | **Thorns** (`thorns`) | `done` / `final` | `func -/65` `aura` `state:thorns` `Conduction` | when active, aura reflects melee damage taken by you / and your party back at your enemies |
| 3.1 | 16 | **Blessed Aim** (`blessed_aim`) | `done` / `final` | `func -/65` `aura` `state:blessedaim` `Conduction` | when active, aura increases the attack rating / for you and your party |
| 4.1 | 24 | **Concentration** (`concentration`) | `done` / `final` | `func -/65` `aura` `state:concentration` `Conduction` | when active, aura increases the damage and decreases the chance / that the attack will be interrupted for you and your party |
| 4.2 | 24 | **Holy Freeze** (`holy_freeze`) | `done` / `final` | `func -/81` `aura` `state:holywind` `cold` `Conduction` | when active, aura freezes nearby monsters / adds cold damage to your attack |
| 5.2 | 32 | **Holy Shock** (`holy_shock`) | `done` / `final` | `func -/66` `aura` `state:holyshock` `ltng` `Conduction` | when active, aura causes pulses of electricity / to damage nearby enemies / adds lightning damage to your attack |
| 5.3 | 32 | **Sanctuary** (`sanctuary`) | `done` / `final` | `func -/66` `aura` `state:sanctuary` `mag` `Conduction` | when active, aura damages the undead / and knocks them back |
| 6.1 | 40 | **Fanaticism** (`fanaticism`) | `done` / `final` | `func -/65` `aura` `state:fanaticism` `Conduction` | when active, aura increases damage, attack speed / and attack rating for you and your party |
| 6.3 | 40 | **Conviction** (`conviction`) | `done` / `final` | `func -/65` `aura` `state:conviction` `Conduction` | when active, aura empowers you and your party with / fire, cold, and lightning damage based on points in each Resistance Aura / while attacks slow enemies and shred monster defe... |

### Defensive (Page 3)

| r.c | Lvl | Skill (`slug`) | Status / Variant | Engine Hooks | In-Game Description |
| :---: | :---: | :--- | :--- | :--- | :--- |
| 1.1 | 1 | **Prayer** (`prayer`) | `done` / `final` | `func -/65` `aura` `state:prayer` `Conduction` | when active, aura slowly regenerates / the life of you and your party |
| 1.3 | 1 | **Resist Fire** (`resist_fire`) | `done` / `final` | `func -/65` `aura` `state:resistfire` `Conduction` | when active, aura decreases fire damage / done to you and your party |
| 2.2 | 8 | **Defiance** (`defiance`) | `done` / `final` | `func -/65` `aura` `state:defiance` `Conduction` | when active, aura bolsters the defense of you and your party / and reduces physical damage taken from attacks |
| 2.3 | 8 | **Resist Cold** (`resist_cold`) | `done` / `final` | `func -/65` `aura` `state:resistcold` `Conduction` | when active, aura decreases cold damage / done to you and your party |
| 3.1 | 16 | **Cleansing** (`cleansing`) | `done` / `final` | `func -/65` `aura` `state:cleansing` `Conduction` | when active, aura reduces the length / of time you and your party / will remain poisoned or cursed |
| 3.3 | 16 | **Resist Lightning** (`resist_lightning`) | `done` / `final` | `func -/65` `aura` `state:resistlight` `Conduction` | when active, aura decreases lightning damage / done to you and your party |
| 4.2 | 24 | **Vigor** (`vigor`) | `done` / `final` | `func -/65` `aura` `state:stamina` `Conduction` | when active, aura increases movement speed and hit recovery / for you and your party to swiftly reposition in battle |
| 5.1 | 32 | **Meditation** (`meditation`) | `done` / `final` | `func -/65` `aura` `state:meditation` `Conduction` | when active, aura increases mana recovery / for you and your party |
| 6.2 | 40 | **Redemption** (`redemption`) | `done` / `final` | `func -/82` `aura` `state:redemption` `Conduction` | when active, aura restores life and mana after each kill / while periodically redeeming nearby slain enemies |
| 6.3 | 40 | **Salvation** (`salvation`) | `done` / `final` | `func -/65` `aura` `state:resistall` `Conduction` | when active, aura decreases fire, cold and lightning damage / done to you and your party |

### Shared Helpers (`specs/_shared.json` — variant `final`)

- **Shared/Custom Missiles (`missiles.txt`):** `foh_conduction_nova`
- **HD Missile Bindings (`missiles.json`):** `foh_conduction_nova`

<!-- AUTO-GENERATED-SPECS:END -->

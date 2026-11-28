# Repurposed Vanilla Stat Registry & Verified D2R Engine Pitfalls

**Read this before adding any custom stat, state, `itemevent`, or complex calc formula.**
Every entry below is empirically verified in-game in D2R Castalia. Anything not verified is explicitly marked as unverified.

---

## 1. Repurposed Vanilla Stat ID Registry (`itemstatcost.txt`)

> **Hard Rule:** **NEVER append brand-new stat IDs past `*ID = 367` (`heraldtier`).** Appended stats fail `itemevent` dispatch and break `.d2s` item parsing if ever removed. Always repurpose an existing unused vanilla stat ID and register it here so two systems never collide.

| `*ID` | Stat Name | Owner in Castalia | Encoding / Events | Notes |
| :---: | :--- | :--- | :--- | :--- |
| `104` | `skill_bypass_demons` | Global **Stun Fatigue** (`automagic` Group `324`: Boots/Gloves) | `Encode=2`, `fCallback=1`, `itemevent1=domeleeattack (20)` | Casts `Stun Fatigue` (`*Id 437`). Zero tooltip. |
| `105` | `skill_bypass_undead` | Paladin **Sanctuary** (`passivestat3`) | Vanilla | **In use — do not repurpose.** |
| `106` | `skill_bypass_beasts` | Global **Stamina Fatigue** ranged trigger (`automagic` Groups `324`/`325`) | `Encode=2`, `fCallback=1`, `damagerelated=1`, `itemevent1=damagedbymissile (21)`, `itemevent2=domissileattack (20)` | Casts `Stamina Fatigue`. Zero tooltip. |
| `161` | `skill_handofathena` | Sorceress **Conflagration** (Fire Stance marker = `1`) | Vanilla (`Send Bits=12`) | **In use.** |
| `162` | `skill_staminapercent` | Stamina Potion / Elixir (`misc.txt` `vps`) | Vanilla | **In use.** |
| `163` | `skill_passive_staminapercent` | Global **Stun Reset** (`automagic` Group `325`: Armor/Belts) | `Encode=2`, `fCallback=1`, `op=""`, `itemevent1=attackedinmelee (21)` | Casts `Stun Reset` (`*Id 438`). Zero tooltip. *(Vanilla `op=1/maxstamina` cleared.)* |
| `164` | `skill_concentration` | Paladin **Concentration** / Druid **Werebear** | Vanilla | **In use.** |
| `166` | `skill_pierce` | Barbarian **Throwing Mastery** (`passivestat3`) | Vanilla | **In use.** |
| `167` | `skill_conviction` | Global **Stamina Fatigue** melee trigger (`automagic` Groups `324`/`325`) | `Encode=2`, `fCallback=1`, `itemevent1=attackedinmelee (21)`, `itemevent2=domeleeattack (20)` | Casts `Stamina Fatigue`. Zero tooltip. |
| `168` | `skill_chillingarmor` | Barbarian **Bloodlust** active marker (`= 1`) | Vanilla | Exempts Bloodlust from `Stamina Fatigue` and drives Exhaustion bonus. |
| `169` | `skill_frenzy` | Sorceress **Cryostasis** (Cold Stance marker = `1`) | Vanilla | **In use.** |
| `170` | `skill_decrepify` | Sorceress **Overcharge** (Lightning Stance marker = `1`) | Vanilla | **In use.** |
| `173` | `target0` | Sorceress **Conduction** (`stance*1000 + Expansion`, `1000..3050`) | Vanilla (`Send Bits=32`) | Decoded via `COND_STANCE = (stat('target0'.accr)/1000)` and `COND_EXP = (stat('target0'.accr) - COND_STANCE*1000)`. |
| `174` | `target1` | Sorceress **Conduction** (`1 + Stasis`, `1..101`) | Vanilla (`Send Bits=32`) | `+1` offset guarantees non-zero write for `srvdofunc=25` overwrite. |
| `175` | `goldlost` | Sorceress **Conduction** (`1 + Arc`, `1..76`) | Vanilla (`Send Bits=24`) | `+1` offset guarantees non-zero write for `srvdofunc=25` overwrite. |
| `176` | `conversion_level` | Sorceress **Arc** passive (`+1` chain/bolt per 6 lvls, cap `+3`) | Vanilla (`Send Bits=8`) | **In use.** |
| `177` | `conversion_maxhp` | Sorceress **Stasis** passive (duration S-curve, up to `+100%`) | Vanilla (`Send Bits=16`) | **In use.** |
| `184` | `create_season` | Inert non-zero `1`-frame state wipe marker (`= 1`) | Vanilla | Used by `Stamina Fatigue` and `Stun Reset` so `srvdofunc=18` always overwrites existing states. |
| `355` | `shortparam1` | Global **Stun Fatigue** stack counter (`0..4`) | Vanilla (`Send Bits=16`, `Save Bits=""`) | Incremented by `Stun Fatigue` (`domeleeattack`), read by `Smite` / `Charge` / `Shield Slam`, wiped by `Stun Reset`. |
| — | `ironmaiden_level` | Sorceress **Expansion** passive (radius S-curve, up to `+50%`) | Vanilla | **In use.** |
| — | `lifetap_level` | Sorceress **Arc** passive (range S-curve, up to `+75%`) | Vanilla | **In use.** |
| — | `item_slash_damage` / `item_absorb_slash` | Assassin **Fists of Fire** held-orb fire damage (`op=2`) | Custom `op=2` in `affixes.py` | **In use.** |
| — | `item_crush_damage` / `item_absorb_crush` | Assassin **Blades of Ice** held-orb cold damage (`op=2`) | Custom `op=2` in `affixes.py` | **In use.** |
| — | `item_thrust_damage_percent` / `item_absorb_thrust` | Assassin **Claws of Thunder** held-orb lightning damage (`op=2`) | Custom `op=2` in `affixes.py` | **In use.** |

### Reserved `states.txt` Groups & `automagic.txt` Groups
- **`states.txt` `group` in use:** `1..13` (`10` = Barb Battle Orders vs Bloodlust; `11` = Barb Shout vs Enduring Cry; `13` = Sorc 3 Elemental Stances). **Next free group: `14`.**
- **`automagic.txt` custom groups:** `304..323` (shields, helms, staves/orbs, class helms/pelts), `324` (Boots/Gloves: Stamina Fatigue + Stun Fatigue), `325` (Armor/Belts: Stamina Fatigue + Stun Reset). **Total rows must stay `< 2048`** (`.d2s` 11-bit auto-affix ID limit; enforced by `test_automagic_rows_fit_d2s_save_format`).

---

## 2. Explicitly Verified FALSE / Engine Pitfalls (Do NOT Re-Attempt)

1. **Formula Buffer & Nesting Overflow (`skills.txt`, `skilldesc.txt`, `missiles.txt`):**
   - **Fact:** D2R's TSV formula buffer is **255 bytes**, and deeply nested formulas near ~246+ chars silently compile to `0` (verified on `Smite` `calc2` at 246 chars and `Hydra` `EDmgSymPerCalc` at 284 chars).
   - **Mitigation:** Always factor sub-expressions into free `calc1..6` slots so every formula stays short and flat. Enforced automatically at `<= 248` chars by `test_calc_formula_character_length_limits`.
2. **Unspaced Ternary Unary Minus (`?-`):**
   - **Fact:** D2R's calc parser silently compiles `?-15:` (no space) to `0`. Always write `0-(...)`. Enforced by `test_calc_formula_character_length_limits`.
3. **Zero-Value Overwrites on `srvdofunc = 18` & `srvdofunc = 25`:**
   - **Fact:** D2R skips overwriting an existing `aurastate` if *all* `aurastatcalc1..6` values evaluate to `0`.
   - **Mitigation:** For 1-frame state wipes (`Stamina Fatigue`, `Stun Reset`), always include an inert non-zero stat (`aurastat = create_season`, `aurastatcalc = 1`). For stance-swap overwrites (`Conduction`), add `+1` offsets (`1 + Stasis`, `1 + Arc`).
4. **Self-Incrementing States Must NOT Have a `states.txt` `group`:**
   - **Fact:** `srvdofunc = 18` strips all states in `group` (including itself) *before* evaluating `aurastatcalc1..6`. Putting `stun_fatigue` in `group = 14` reset `shortparam1` to `0` before `+1` ran, locking stacks at `1` forever.
5. **`srvdofunc = 150` (`Smite`) Engine Hardcodes:**
   - **Fact:** `srvdofunc = 150` ignores `aurastate`/`auratargetstate`/`HitClass`, hardcodes `HITCLASS_STUN` impact audio (`impact_stun_1..3`) in C++, and treats `ResultFlags = 8` (Knockback) as a static boolean bit.
   - **Fact:** Pairing `srvstfunc = 32` (`Concentrate`) or `srvstfunc = 39` (`Berserk`) with `srvdofunc = 150` clobbers `Smite`'s stun execution (and `srvstfunc = 39` hardcodes `armor_override_percent = 100`, dropping Defense to 0!).
   - **Fact (`descdam = 10` LCS Quirk — Verified 2026-11-28):** `skilldesc.txt` `descdam = 10` (Smite Character Screen damage) ignores both `ddam calc1` and live `calc1` Stamina scaling — it hardcodes vanilla `ln34` (`Param3 + (lvl-1)*Param4`). Actual server-side Smite damage (`srvdofunc = 150`) and the Skill Tree tooltip (`desccalca2 = clc1`) **do** evaluate `calc1` dynamically with Stamina.
6. **`srvdofunc = 67` (`Charge`) Engine Hardcode:**
   - **Fact:** Knockback is hardcoded inside `srvdofunc = 67` in C++ even when `ResultFlags = ""`.
7. **Negative `staminarecoverybonus` Cannot Drain Stamina:**
   - **Fact:** Empirically tested with `staminarecoverybonus = -2500` — D2R clamps standing/walking Stamina regen at `>= 0`. It cannot actively drain Stamina (unlike `hpregen`, which supports negative Life Drain).
8. **`itemevent` & `properties.txt` Constraints:**
   - **Fact:** `doactive` is **NOT** emitted for item events in D2R.
   - **Fact:** `properties.txt` `func2 = 11` is ignored; only `func1 = 11` registers a proc (split into separate properties).
   - **Fact:** `hitbymissile` does NOT fire `func 21` (use `damagedbymissile` + `damagerelated = 1`).
   - **Fact:** Always clear vanilla `op` / `op stat1` columns when repurposing a stat for `Encode = 2` `itemevent` (leftover `op = 1` on `skill_passive_staminapercent` blocked `Stun Reset` until cleared).
   - **Unverified / Known Issue:** `itemevent2 = kill` (`func 20`) on `skill_passive_staminapercent` did NOT fire in Test 4 while `itemevent1 = attackedinmelee` (`func 21`) on the same stat *did* fire. Do not assume `itemevent2 = kill` works on repurposed stats without a controlled 1-variable test.
9. **`srvdofunc = 166` Blink (`Phase Step` / `Glacier Step`) Client-Only `ExplosionMissile`:**
   - **Fact:** `hitfunc = 42` (`ExplosionMissile`) spawns on the client only — never deals server damage or applies states. Use the warp's server trail-dropper (`pSrvDoFunc = 2` -> `SubMissile1`).
10. **Never Repurpose `lastexp` (`*ID = 29`) or `armor_override_percent` (`*ID = 182`):**
    - **Fact:** `lastexp` holds the character's actual previous XP value (millions at Lvl 60); `armor_override_percent` is overwritten to `100` by `srvstfunc = 39`.
11. **Dual Website Evaluators (`tools/build_site.py`):**
    - **Fact:** `build_site.py` has *two* expression evaluators — Python `_eval_skill_expr` (static tables) and browser JS `evalSkillExpr` (live tooltips). Both must default `mana`/`maxmana`/`stamina`/`maxstamina` to `256` and stay in sync.

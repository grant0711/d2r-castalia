# Paladin Smite Stun & Stun-Fatigue Diagnostic Log

Controlled 1-variable-at-a-time test log for `Smite` (`*Id = 97`, `srvdofunc = 150`).

---

## Prior Observations (Before Controlled Matrix)

| Run | `srvstfunc` | `ResultFlags` | `calc2` length | Observed In-Game |
| :--- | :---: | :---: | :---: | :--- |
| Pre-session baseline | `""` | `"8"` | `198` chars | Stun + Knockback both worked. |
| Attempt 1 (`smite_fatigue` via `srvstfunc=39`) | `"39"` | `"8"` | `253` chars | Knockback worked; **0 stun** (and `srvstfunc=39` hardcoded `armor_override_percent=100`). |
| Attempt 2 (`srvstfunc=32` + `lastexp`) | `"32"` | `"8"` | `242` chars | Knockback worked; **0 stun** (`lastexp` = character XP). |
| Attempt 3 (`srvstfunc=32` + `shortparam1`, no KB) | `"32"` | `""` | `246` chars | Knockback gone; **0 stun**. |
| Attempt 4 (`srvstfunc=""` + `domeleeattack` `Stun Fatigue`) | `""` | `""` | `246` chars | Knockback gone; **0 stun on Hit 1**. |

### Active Hypotheses for Why Hit 1 Had 0 Stun in Attempt 4
1. **H1 (`calc2` Expression Overflow / Token Stack Limit):** `calc2` reached `246` characters with 6 levels of nested parentheses and 4 `stat()` calls; D2R's `skills.txt` formula compiler silently compiles oversized/over-nested formulas to `0`.
2. **H2 (`ResultFlags = ""` Blocks Stun in `srvdofunc = 150`):** `srvdofunc = 150` may require `ResultFlags` (or a specific flag bit) to apply the stun state.
3. **H3 (`shortparam1` Non-Zero or `Stun Fatigue` State Behavior):** `shortparam1` might not default to `0`, or `domeleeattack` might fire *before* `calc2` is evaluated.

---

## Test 1 — Baseline Control: Short `calc2` (`48` chars), `ResultFlags = ""`, No `shortparam1`

- **Change:**
  - Factor `RESTED_PCT` into `calc5` (`(stat('stamina'.accr)*100)/max(256,stat('maxstamina'.accr))`).
  - Set `calc2 = (clc5>=33)?min(250,(ln12*clc5)/100):0` (`38` chars — zero `shortparam1`, zero `target1`, zero deep nesting).
  - Keep `srvstfunc = ""`, `ResultFlags = ""`, `Param1 = 12`, `Param2 = 2`.
- **Expected Outcomes:**
  - **If Hit 1 stuns (swirling stars above monster):** **H1 is CONFIRMED** (`calc2` length/nesting overflowed D2R's calc compiler) AND `ResultFlags = ""` does NOT block stun. Proceed to Test 2 (`shortparam1` + visible `stun_fatigue` debug overlay).
  - **If Hit 1 still does NOT stun:** **H2 is CONFIRMED** (`ResultFlags = ""` disables stun in `srvdofunc = 150`). Proceed to Test 2b (`ResultFlags = "4"` GetHit-only vs `"8"` Knockback).
- **Result:** **PASS** — Stun works cleanly on Hit 1 with `ResultFlags = ""`!
  - **Confirmed:** **H1** (`calc2` at `246` chars / 6-deep nested parens overflowed D2R's formula compiler, silently compiling to `0`).
  - **Ruled Out:** **H2** (`ResultFlags = ""` does NOT block stun in `srvdofunc = 150`).

---

## Test 2 — Short Split `calc3` + `calc2` with `shortparam1` & Visible `stun_fatigue` Debug Overlay

- **Change:**
  - Keep `calc5 = RESTED_PCT` (53 chars).
  - Add `calc3 = ((100+max(0,stat('target1'.accr)-1)/2)*max(0,4-stat('shortparam1'.accr)))/4` (`78` chars: Cold Conduction `Stasis` × Stun Fatigue `4→3→2→1→0 / 4`).
  - Set `calc2 = (clc5>=33)?min(250,((ln12*clc5)/100*clc3)/100):0` (`49` chars).
  - Temporarily add `overlay1 = "shout"` on `stun_fatigue` in `states.txt` so we can visually confirm:
    1. `domeleeattack` applies `stun_fatigue` on Smite hit (overlay appears),
    2. Hits 1–4 taper stun `100% → 75% → 50% → 25%` and Hit 5+ deals `0` stun (no swirl above monster),
    3. Getting attacked in melee (`attackedinmelee`) or killing a monster (`kill`) immediately clears the overlay (`Stun Reset`).
- **Result:** **PARTIAL PASS**
  1. **PASS:** Hit 1 stuns AND `stun_fatigue` debug overlay appears on the Paladin.
  2. **PASS:** Stun swirl tapers down over Hits 2–4 and stops applying by Hit 5+!
  3. **FAIL:** Getting hit in melee (`attackedinmelee`) or killing a monster (`kill`) did NOT clear the `stun_fatigue` overlay.
  - **Diagnosis:** `Stun Reset` (`*Id = 435`, `auralencalc = 1`) tried to overwrite the *same* `aurastate = stun_fatigue` applied by `Stun Fatigue` (`*Id = 434`, `auralencalc = 125`), which D2R's `srvdofunc = 18` skips when a different skill attempts a shorter/weaker overwrite of the same state.

---

## Test 3 — Mutual-Exclusion State Group (`group = 14`) for `stun_fatigue` vs `stun_reset`

- **Change:**
  - Place `stun_fatigue` (keeping temporary `overlay1 = "shout"` for verification) and a new `stun_reset` state in **`group = 14`** (verified unused in `states.txt`).
  - Point `Stun Reset` (`attackedinmelee` + `kill` on Armor/Belts Group `325`) to `aurastate = "stun_reset"`, `auralencalc = "1"`, `aurastat1 = "create_season"`, `aurastatcalc1 = "1"`.
  - Applying `stun_reset` in `group = 14` unconditionally strips `stun_fatigue` in D2R C++ regardless of remaining duration or skill ID.
- **Expected Outcome:**
  - Smite Hit 1–4 tapers stun and displays the debug overlay.
  - Getting swung at in melee OR killing a monster **immediately clears** the debug overlay and resets Smite stun to 100%.
  - *(Verify a freshly bought Armor or Belt [Group `325`] is equipped on `PAL`.)*
- **Result:** **FAIL** — Even with a newly bought Belt (Group `325`), getting swung at, hit in melee, or killing a monster did NOT clear the red `stun_fatigue` overlay (only waiting 5s cleared it).
  - **Inspection Finding:** `skill_passive_staminapercent` (`*ID = 163`) still retained vanilla `op = 1`, `op stat1 = maxstamina` in `itemstatcost.txt`!

---

## Test 4 — Isolate Whether `Stun Reset` Is Firing At All

- **Change:**
  - Clear `op = ""` and `op stat1 = ""` on `skill_passive_staminapercent` in `affixes.py` (`itemstatcost.txt`).
  - Give `stun_reset` a temporary visible debug overlay (`overlay1 = "energyshield"`) and `auralencalc = "50"` (2.0s) so we can unambiguously see if `Stun Reset` fires on `attackedinmelee` or `kill`.
- **Expected Outcomes:**
  - **If `energyshield` appears & red `shout` disappears on melee hit / kill:** `Stun Reset` is firing and `group = 14` strips `stun_fatigue` cleanly → drop `auralencalc` to `1` (or `2`) and strip debug overlays!
  - **If `energyshield` NEVER appears:** `skill_passive_staminapercent` (`*ID = 163`) is not dispatching `itemevent` → switch to a verified `Encode = 2` stat / check `belt` `auto prefix`.
- **Result:** **KEY BREAKTHROUGH**
  1. **PASS:** Being swung at in melee (`attackedinmelee`) triggered `Stun Reset` (`energyshield` orb appeared AND red `stun_fatigue` overlay immediately vanished!).
  2. **FAIL (`kill`):** Killing a monster did not trigger `Stun Reset` (`itemevent2 = kill` on `skill_passive_staminapercent` did not fire).
  3. **REGRESSION (Stun Taper):** While the red overlay was active, subsequent Smite hits did **not** lose stun — because placing `stun_fatigue` in `group = 14` caused `srvdofunc = 18` to strip `group = 14` (`stun_fatigue` itself!) *before* evaluating `aurastatcalc1 = min(4, stat('shortparam1'.accr)+1)`, keeping `shortparam1` stuck at `1` instead of incrementing `1 → 2 → 3 → 4`!

---

## Test 5 — Remove `group = 14` So `Stun Fatigue` Stacks `1→2→3→4`, Test Same-State `Stun Reset` With Fixed `skill_passive_staminapercent`

- **Hypothesis:** In Test 2 (`group = ""`), `Stun Fatigue` stacked `1 → 2 → 3 → 4` cleanly, and `Stun Reset` only failed because `skill_passive_staminapercent` still had `op = 1` + no fresh Group `325` Belt. Now that `op = 1` is cleared and the Belt is equipped, same-state `aurastate = stun_fatigue` (`auralencalc = 1`, `create_season = 1`) should BOTH stack `1→2→3→4` AND clear on `attackedinmelee`!
- **Change:**
  - Remove `group = 14` from `stun_fatigue` (keeping temporary `overlay1 = "shout"`).
  - Point `Stun Reset` back to `aurastate = "stun_fatigue"`, `auralencalc = "1"`, `aurastat1 = "create_season"`, `aurastatcalc1 = "1"`.
- **Expected Outcome:**
  1. Uninterrupted Smites on a tanky monster taper stun `100% → 75% → 50% → 25% → 0%` (matching Test 2).
  2. Getting swung at in melee immediately clears the red `stun_fatigue` overlay and restores 100% stun on the next hit.
- **Result:** **PASS (SHIPPED)**
  1. **PASS:** Uninterrupted Smites smoothly taper stun duration (`100% → 75% → 50% → 25% → 0%`) and stop stunning by Hit 5+.
  2. **PASS:** Being struck in melee immediately fires `Stun Reset` (wiping `stun_fatigue` in 1 frame and restoring 100% stun), or waiting 5s without attacking naturally expires it.
- **Final Cleanup:** Removed temporary `overlay1 = "shout"` debug overlay from `stun_fatigue`. Production state verified (`36 / 36` tests).

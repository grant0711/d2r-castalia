# Dynamic Co-Op Encounters & Monster Skill Scaling Plan

> **Goal:** Make 2–8 player co-op in Castalia *tactically different* — not just the same monsters with bigger HP bars. As player count increases, bosses and key monster families gain new tactical behaviors (higher speed/tempo, secondary sub-missiles, extended range/AoE, and multi-phase enrages) so party composition, positioning, and co-op tools (`Conduction`, `War Cry`, `Salvation`, `Second Wind`, `Meditation`) genuinely matter.

---

## 1. The Vanilla D2R Co-Op Scaling Problem

D2R's multiplayer `/players N` scaling is hardcoded in C++ and only touches four things:
- **Monster HP:** $\text{Base} \times \frac{N + 1}{2}$ (`+50%` per extra player → `1.5×` P2, `2.5×` P4, `4.5×` P8)
- **Monster XP:** $\text{Base} \times \frac{N + 1}{2}$ (+ proximity party bonus)
- **Monster Physical Damage & AR (NM/Hell only):** $\text{Base} \times (1 + 6.25\% \times (N - 1))$ (`+18.75%` at P4, `+43.75%` at P8)
- **Trash `NoDrop` Chance:** $\text{NoDrop}^{N_{\text{eff}}}$

Everything that makes combat *feel* different — **monster speed, elemental spell damage, projectile count, sub-missiles, AoE radius, and attack patterns** — is **100% static** from P1 to P8. As a result, 2–4 coordinated players easily out-scale P2–P4 monsters and fights feel identical to solo play, just slightly longer.

---

## 2. The Engine Pathway: Reading `stat('maxhp'.accr)` & `stat('hitpoints'.accr)`

While player skills cannot read a target monster's HP in `skills.txt`, **monster skills and monster auras can read their own `stat('maxhp'.accr)` and `stat('hitpoints'.accr)`** (stored in 1/256ths internally).

### A. Removing Invisible HP Roll Noise (`minHP = maxHP`)
- Currently in `monstats.txt`, spawnable monsters have a median `maxHP / minHP` spread of **`1.50×`** (90th percentile `2.02×`), which is barely noticeable in gameplay but blurs `maxhp` thresholds.
- Fixing `minHP = maxHP` (using the midpoint) makes base HP deterministic per monster ID and difficulty.

### B. Exact Player-Count Detection on Act Bosses & Super Uniques
- Act Bosses (`Andariel`, `Duriel`, `Mephisto`, `Diablo`, `Baal`, `Ancients`) and Super Uniques (`Countess`, `Summoner`, `Nihlathak`, `Izual`, `Hephasto`, `Smith`) have a **fixed `mlvl`** and **never roll Champion/Unique HP multipliers**.
- With `minHP = maxHP`, their `P1` `maxhp` is **100% deterministic**, so their skills can detect exact player-count tiers:
  - **Solo (`P1`):** `maxhp < P1_HP * 1.25`
  - **Duo (`P2–P3`):** `P1_HP * 1.25 <= maxhp < P1_HP * 2.25` (`1.5×` – `2.0×`)
  - **Full Party (`P4+`):** `maxhp >= P1_HP * 2.25` (`2.5×` – `4.5×`)

### C. Natural Dual-Scaling on Regular Monster Archetypes
- Regular monsters' `maxhp` scales with `mlvl`, Champion/Unique multipliers (`2×` in Hell), *and* player count (`1.5×` P2, `2.5×` P4, `4.5×` P8).
- Scaling monster skills off `maxhp` thresholds creates a clean **win-win**:
  - In **solo P1**, Champions and Uniques cross the threshold and cast upgraded elite patterns.
  - In **co-op P3–P8**, even regular packs cross the threshold and escalate their tactical threat alongside their HP.

### D. HP-Threshold Boss Phases (`hitpoints * 100 / maxhp`)
- Independent of player count, any boss skill or innate aura can evaluate current HP %:
  - `(stat('hitpoints'.accr) * 100) / max(256, stat('maxhp'.accr))`
- Below `50%` or `25%` HP, bosses can enter a **Phase 2 / Enrage state** (higher speed, extra projectiles, new sub-missiles), combining WoW-style encounter phases with co-op scaling.

---

## 3. Tactical Levers Available in D2R `.txt` Tables

All four levers below use proven D2R mechanics already verified elsewhere in Castalia:

| Tactical Lever | Engine Mechanism | Example Co-Op Escalation |
| :--- | :--- | :--- |
| **Conditional Secondary Sub-Missiles** | Sub-missile `Range` = `0` in P1, `> 0` at `P2+`/`P4+` *(proven via `foh_conduction_nova` & `cot_conduction_spark`)* | Mephisto's Charged Bolt / Skull Missile splits into radial frost/lightning sparks in P2+; Diablo's Firestorm leaves secondary ember bursts in P4+. |
| **Increased Range & Velocity** | `missiles.txt` `Range` formula & `skills.txt` `aurarangecalc` scaled by `maxhp` tier | Longer-reaching boss beams/novas, wider Shaman fireballs, deeper Viper charges that pressure ranged backliners (`Sorceress`, `Amazon`). |
| **Increased Speed & Attack Tempo** | Monster self-aura (`srvdofunc = 65` or `18`) granting `velocitypercent` + `attackrate` when `maxhp` tier or `<50%` HP phase is active | Bosses and elite packs move and strike noticeably faster in co-op, rewarding frontline CC (`War Cry`, `Holy Freeze`, `Shadow Bind`, `Decrepify`). |
| **Co-Op Elemental Spell Scaling** | `EDmgSymPerCalc` scaled by `maxhp` tier | Closes D2R's hardcoded gap where monster physical damage scales `+6.25%/player` in NM/Hell while elemental spells stay stuck at P1 damage. |

---

## 4. Phased Implementation Roadmap

### Phase 1 — Deterministic HP Foundation
- Set `minHP = maxHP` (midpoint) on all Act Bosses and Super Uniques in `tools/mod_builder/monsters.py` (and evaluate doing the same for regular monsters).
- Export or compute a reference table of exact `P1` `maxhp` values (Normal / Nightmare / Hell) for every Act Boss & Super Unique so `skills.txt` / `missiles.txt` formulas never hardcode drift-prone magic numbers.
- Add unit tests in `tests/test_monster_invariants.py` verifying `minHP == maxHP` and `P1 / P2 / P4 / P8` threshold separation.

### Phase 2 — Act Boss Co-Op & Phase Overhaul
Design signature P2+ / P4+ and `<50%` HP escalations for the 5 Act Bosses (plus `Ancients`):
- **Andariel:** Wider poison spray + secondary poison clouds on impact in co-op; faster melee frenzy below 50% HP.
- **Duriel:** Stronger chill/charge tempo in co-op; frost nova sub-bursts on hit in P2+/P4+.
- **Mephisto:** Additional lightning/cold sub-missiles on Skull Missile & Charged Bolt; faster cast cadence in co-op (rewards Paladin `Salvation`).
- **Diablo:** Wider Fire Nova & Lightning Hose reach + secondary Firestorm eruptions in P2+/P4+; `<50%` HP enrage aura.
- **Baal:** Hoarfrost Wedge / Mana Rift range & sub-missile escalation in co-op; faster clone/summon tempo.

### Phase 3 — Iconic Monster Family Co-Op Escalation
Extend `maxhp`-scaled tactical upgrades to key Hell monster skills (so packs feel genuinely more dangerous in co-op *and* Champions/Uniques stand out in solo):
- **Ranged Casters:** `Gloams` (Lightning), `Oblivion Knights` (Elemental Bolts), `Fallen Shamans` (Fireball), `Succubi` (Blood Star) — wider `Range` / conditional split sub-missiles.
- **Frontline Bruisers:** `Death Lords` / `Minotaurs` / `Claw Vipers` — faster charge/frenzy tempo or wider cleave/shockwave impact.

### Phase 4 — Simulation & Live Co-Op Verification
- Extend `tests/test_skill_simulation.py` to evaluate every reworked monster skill across simulated `P1`, `P2`, `P4`, `P8`, and `<50%` HP states.
- Playtest solo (`/players 1`) vs. `/players 2`, `/players 4`, and `/players 8` in-game to confirm P1 stays fair while P2–P8 feel tactically distinct and exciting.

---

## 5. The Castalia Co-Op Healer & Resource Support Trinity

To give co-op parties genuine role diversity (avoiding a single mandatory support class), Castalia targets **three distinct healer/resource-support archetypes**:

| Class | Support Identity | Health Restore | Stamina Restore | Mana Restore |
| :--- | :--- | :--- | :--- | :--- |
| **Paladin** | Sustained Aura & Targeted Cleric *(gated by Mana upkeep & Devotion)* | `Prayer` (steady aura) + `Holy Bolt` (targeted burst) | **`Vigor` (planned):** Tempered `+11% → +75%` Stamina Recovery Bonus (`staminarecoverybonus` in `aurastat3`, scaled by Mana Devotion; `+Max Stamina` stays removed so Barbarian keeps its niche) | `Meditation` (0-Mana active recovery stance) |
| **Barbarian** | Tactical Burst Warcry Medic *(3.0s shared Warcry CD)* | `Battle Command` (instant party HP burst heal) | `Second Wind` (instant party Stamina refill) + `Enduring Cry` (party `+Max Stamina`) | — |
| **Druid** *(planned rework)* | Stationary, Targetable Resource Totems *(long CD, high Mana cost, scaling HP/Res/Duration)* | **Life Totem** (party `item_healafterkill` aura) | — *(remains Paladin / Barbarian domain)* | **Mana Totem** (party `item_manaafterkill` aura) |

### Druid Co-Op Totem Design (Stationary, Targetable Party Anchors)
Rather than duplicating Paladin's passive self-auras or Barbarian's burst Warcries, the Druid's co-op support revolves around **stationary, targetable Totems** that the party plants and defends during fights:

1. **Life Totem (Party `item_healafterkill`):**
   - Stationary (`Velocity = 0`, `Run = 0`), targetable summon with scaling **Life, Resistances, Duration, and Aura Radius** so it can absorb hits rather than dying to a single stray arrow, while still demanding smart placement and protection.
   - High Mana cost and long cooldown — planting it is a deliberate tactical commitment for a pack or boss room.
   - Radiates **`item_healafterkill`** to all nearby allies, rewarding aggressive pack clearing.
2. **Mana Totem (Party `item_manaafterkill`):**
   - Same stationary, targetable totem architecture (scaling Life, Resistances, Duration, Radius; high Mana cost & long cooldown).
   - Radiates **`item_manaafterkill`** to all nearby allies — giving casters and Auradins an active, kill-driven Mana sustain engine completely distinct from Paladin's passive `Meditation` stance.
3. **Domain Boundaries & Conduction Hooks:**
   - **No Stamina restore** on Druid — Stamina recovery stays strictly in the Paladin (`Vigor`) and Barbarian (`Second Wind` / `Enduring Cry`) domains.
   - Under Sorceress `Conduction`, Totem duration scales with **`Stasis`** and Totem aura radius scales with **`Expansion`**.

---

## 6. Co-Op Reward Escalation (Dynamic Magic Find & Gold Find Bounties)

Making co-op harder without making it *more rewarding* discourages group play. Since D2R's `/players N` only lowers trash `NoDrop` (and gives **zero** drop bonus on Act Bosses / Super Uniques, which already have `NoDrop = 0`), we can use the exact same `stat('maxhp'.accr)` detection to reward parties directly:

### Mechanism: `maxhp`-Gated Co-Op Bounty State (`coop_bounty`)
- Broadly applied by **Act Bosses, Super Uniques, AND normal monsters** (via monster skills, auras, or event hooks wherever a monster cleanly supports it): applies a short-duration (5–10s) state **`coop_bounty`** (`aurastat1 = item_magicbonus`, `aurastat2 = item_goldbonus`) to nearby fighting players **only when `stat('maxhp'.accr)` crosses a co-op (`P2+` / `P4+`) threshold**.
- **Solo (`P1`):** `aurastatcalc1 = 0` → **`+0%` MF / GF** (zero solo inflation).
- **Duo (`P2–P3`):** e.g. **`+50%` MF / `+50%` GF** while actively engaged near the boss.
- **Full Party (`P4+`):** e.g. **`+100%` to `+150%` MF / `+100%` GF** (and optionally an extra bump during `<50%` HP boss enrage phases).

### Why This Works So Well in D2R
- **Directly rewards fighting together:** Whoever lands the killing blow has `coop_bounty` active when D2R rolls the drop table — and because it is proximity/combat-applied with a short duration, AFK town leechers don't receive it.
- **Frees co-op players from pure MF gear:** Players can wear real combat/co-op survival gear (`Clarity` runes, resistances, Stamina/Life gear) and still earn strong Unique/Set/Rare odds as their reward for conquering harder co-op bosses.
- **Naturally self-balancing:** D2R's built-in MF diminishing returns (`MF * 250 / (MF + 250)` for Uniques) prevent runaway drop inflation while making the co-op reward immediately noticeable (and visible on the Advanced Stats MF line).

### Co-Op Gem & Rune Scaling via `Picks` + `NoDrop` (Same Solo Average, ~2.7× Co-Op Drops!)
Because **Magic Find does not affect Gems or Runes**, and vanilla Champions/Uniques (`NoDrop = 0`) drop `1.00×` total (`0.25×` per player at P4), we can convert `NoDrop = 0` tables into **higher `Picks` + calibrated `NoDrop`** while preserving the **exact same solo P1 expected value**:

- **Example (`Picks = 4`, `NoDrop = 3 × sumW` → `25%` per pick at P1):**
  - **`P1` (Solo):** `4 × 25.0%` = **`1.00` expected drops** *(identical solo aggregate!)*
  - **`P2` (Duo):** `4 × 43.8%` = **`1.75` expected drops** (`0.88×` / player)
  - **`P4` (4-Player):** `4 × 68.4%` = **`2.73` expected drops** (`0.68×` / player — nearly **3×** more Champion/Unique Gems & Runes!)
  - **`P8`:** `4 × 90.0%` = **`3.60` expected drops**
- **Where it applies cleanly (respecting D2R's 6-item-per-monster hard cap):**
  - **Champions & Uniques:** Keep `1` guaranteed drop (so a Unique/Champion never drops empty in solo) + add a `Picks = 3..4` calibrated `NoDrop` bonus TC for Gems/Runes/Good (stays well under the 6-item cap).
  - **Chests / Containers:** Increase `Picks` (`1 → 2`) and `NoDrop` (`20 → 60`, keeping `0.50` expected items/chest at P1) so P4 chest drops jump from `1.90×` to **`2.73×`**.
  - **Act Bosses:** D2R's hard ceiling is **6 dropped items per kill** (not `Picks = -6` itself). Act Bosses can either keep 6 solo drops + `coop_bounty`, **or** be reshaped into e.g. `2–3` guaranteed drops + `3–4` calibrated `NoDrop` picks (e.g., `~3.5–4.0` avg drops in solo P1 scaling up to **`5.5–6.0` drops** in P4–P8 co-op) so Act Boss loot quantity *also* visibly grows with party size.

---

## 7. Design Guardrail: Player Skill Integrity & Co-Op Summon Scaling

- **Never downgrade player skills in co-op:** A player's own attacks, spells, and buffs should feel 100% consistent and honest whether playing solo or with friends. Difficulty escalation belongs on the **monsters and encounters**, never by silently nerfing the player.
- **Anti-Chain-Stun by Global Design (Not Co-Op Nerfs):** Chain-stun cheese (`Smite`, `War Cry`, `Mind Blast`, `Shockwave`, etc.) should be prevented *globally* across both solo and co-op via genuine skill tradeoffs — casting delays (`localdelay`), high Mana costs, Stamina Exhaustion cutoffs (`0` stun below `33%` Stamina), and short/capped stun windows — rather than hiding a co-op-only stun penalty.
- **Summon-specific co-op tuning (Druid & Necromancer):** Summons are the one clean exception where co-op state (`coop_bounty` / `coop_tier`) can help maintain feel and readability:
  - **Druid:** Keep total summon count very small (e.g., few beasts + stationary Totems) so co-op screens stay readable, and optionally grant **bonus summon survivability** (Life / Resistances / PDR) in co-op encounters so low-count summons and Totems survive escalated co-op boss spells.
  - **Necromancer:** Trim maximum army size slightly (cleaner co-op battlefield, less body-blocking of melee teammates) while using subtle co-op summon scaling (survivability / skill tuning) so the leaner army stays effective against P2–P8 encounters.

---

## 8. Co-Op Integrity & Save Isolation (TODO)

**Goal:** Protect weekly co-op campaigns and the Castalia community from casual vanilla save imports or third-party Hero-Edited characters (e.g., imported vanilla Runewords, Sunder Charms, or hacked stats/items) that would invalidate the mod's rules and ruin the shared experience.

### On the Docket: `gf` Bit-Width Isolation (`CSvBits`)
- **Mechanism:** Widen `CSvBits` on a universal character stat in `itemstatcost.txt` (e.g., `strength` `*ID = 0` from `10` → `11`).
  - Every vanilla `.d2s` and every stock third-party Hero Editor / web save editor hardcodes `CSvBits = 10` for `strength`.
  - Shifting `CSvBits` by 1 bit causes D2R running Castalia to reject **any** vanilla or Hero-Edited save (even a naked Level 1 character with no items) due to `gf` bitstream misalignment.
  - Characters created in-game in Castalia work seamlessly, and our own official tools (`bin/d2r-char` in `tools/mod_builder/char_manager.py` and the embedded website Calculator `.d2s` downloader in `tools/build_site.py`) simply update `STAT_BITS[0] = 11`.
- **Verification & Rollout Checklist:**
  1. Test in-game once to confirm D2R dynamically honors `CSvBits = 11` on `strength` (new Castalia char saves/reloads cleanly; vanilla `.d2s` is rejected).
  2. Update `STAT_BITS` in `tools/mod_builder/char_manager.py` and `tools/build_site.py`.
  3. Roll out cleanly before launching recurring community co-op campaigns (one-time migration/recreation of existing dev test saves).





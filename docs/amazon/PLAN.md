# Castalia — Amazon Rework Plan (Draft)

> **Status:** Core Identity Locked — Mapping 30 Skill Slots  
> **Hard Castalia Boundaries:** Zero Runewords, zero player elemental/sunder pierce (`passive_*_pierce` / `item_pierce_*_immunity`), 6-tier level grid (`1 / 8 / 16 / 24 / 32 / 40`), 0-Mana physical skills following Castalia's universal Martial Stamina rules.

---

## 1. Existing Amazon Foundation Already in Castalia
- **4-Tier Valkyrie Equipment (`monequip.txt` + `unique_sets.py`):** `Valkyrie Spear / Armor / Helm I–IV` already built (scaling damage, IAS, Crushing Blow, Life Steal, All Res, PDR, Might/Defiance auras, Amp/Decrepify procs).
- **Quivers & Auto-Replenishing Javelins (`affixes.py` / `weapons_armor.py`):** Quivers (`bowq`, `xboq`) roll resistance & elemental damage prefixes; throwing weapons auto-replenish.
- **Glove Charges (`affixes.py`):** Amazon Bow/Spear attack charges on Gloves aligned to Castalia tier gates.

---

## 2. Core Mechanical Identity: **Cadence & Counter-Attack**
Instead of adding a second resource bar on top of Stamina, the Amazon plays as Castalia's **rhythmic duelist, skirmisher, and siege marksman**, built around **two intuitive reactive counters**, **one proactive opener→payoff cadence**, and a **diegetic Bow vs. Crossbow split**:

### A. Two Reactive Counter Windows (`3s`, Engine-Native `events.txt`)
1. **`Riposte` (Melee Spear/Javelin Counter — `attackedinmelee`):**
   - Triggered automatically whenever an enemy swings at the Amazon in melee (**even if she `Dodge`s or blocks it!**).
   - Stamps a **3-second `ama_riposte` state** + visual flash.
   - Pressing **`Riposte`** during the window unleashes a devastating counter-thrust (massive `% ED`, high AR, Stun); outside the window it fizzles or does a light poke.
2. **`Countershot` (Ranged Bow/Crossbow Counter — `hitbymissile`):**
   - Triggered automatically whenever an enemy missile hits/clips the Amazon (`hitbymissile`).
   - Stamps a **3-second `ama_countershot` state** + visual flash.
   - Pressing **`Countershot`** during the window fires a blistering, precision high-velocity return shot (massive `% ED` / guaranteed Crit or Pierce).

### B. One Proactive Offensive Window (`Sighted` / `Cadence`, `4s`)
- Opened by **tactical setup skills** (`Inner Sight`, `Impale`, `Poison Javelin`, and Bow opener candidates like `Magic Arrow` / `Cold Arrow`).
- While glowing for **4 seconds**, **payoff volleys & flurries** (`Guided Arrow`, `Multiple Shot`, `Strafe`, `Fend`, `Charged Strike`, `Lightning Fury`, Crossbow skills) gain a clean bonus (extra damage / speed / impact).
- Reinforced visually on the skill tree by direct prerequisite arrows (`Setup → Payoff`) so the rhythm is obvious without memorization.

### C. Universal Martial Stamina + **Crossbow Exemption**
- **Bow & Spear Physical Skills (`0` Mana):** `Multiple Shot`, `Guided Arrow`, `Strafe`, `Jab`, `Impale`, `Fend` follow Castalia's **Half-Power Rule (`50% → 100%` with Stamina)**.
- **`Dodge`, `Avoid`, `Evade` (Live Passives):** Scale `50% → 100%` with current Stamina % (and `Dodge` pairs directly with `attackedinmelee` → `Riposte`!).
- **Stun Exhaustion Rule (`100% → 33%`, `0` below `33%`):** Applies to heavy spear stuns (`Impale`, `Riposte`).
- **Crossbow (`xbow`) Mechanical Exemption:** Dedicated Crossbow-only skills (`itypea1 = xbow`) **bypass Stamina degradation** because the mechanical winch/prod holds the draw — creating a **Heavy Arbalest / Siege Amazon** archetype that can wear Heavy Armor behind `Valkyrie` + `Decoy`!

---

## 3. Bow vs. Crossbow Split (1–2 Dedicated `xbow`-Only Skills + Affix Pool Split)
- **Bow (`bow`) — *Agile Skirmisher*:** Fast, fluid, Stamina-driven volleys (`Multiple Shot`, `Strafe`, `Guided Arrow`), Elemental Arrows (`Fire` / `Cold`), Light Armor & mobility.
- **Crossbow (`xbow`) — *Heavy Arbalest / Siege Sniper*:** Slower rate of fire, **exempt from Stamina penalty**, heavy armor-piercing bolts:
  1. **`Siege Bolt` (`itypea1 = xbow`, Mid-Tier, e.g. Lvl 16/24):** Heavy, high-damage mechanical bolt with built-in **Pierce + Knockback/Stagger** (reclaims a stepping-stone bow slot like `Ice Arrow` or `Fire Arrow`).
  2. **`Ballista` / `Heavy Quarrel` (`itypea1 = xbow`, High-Tier, e.g. Lvl 32/40):** Devastating siege capstone — massive single-bolt armor-shredding impact or heavy mechanical 3-bolt spread, **no Stamina penalty**, huge payoff during `Sighted`!
- **Itemization Differentiation (`magicprefix.txt` / `magicsuffix.txt` — NO `automagic.txt` clutter):**
  - Split/bias the magic prefix & suffix pools between `bow` and `xbow` (mirroring our Staff vs. Orb approach) so Bows and Crossbows spawn distinct identities directly on blue/rare drops without relying on noisy automagic.

---

## 4. 30-Skill Slot Map (Working Draft)

### Tree 1: Bow & Crossbow (`SkillPage = 1`)
| Id | Pos | Req | Vanilla Slot | Proposed Castalia Role |
|---:|:---:|---:|---|---|
| 6 | R1C2 | 1 | Magic Arrow | **Magic Arrow** — low-mana Magic damage answer to Physical Immunes |
| 7 | R1C3 | 1 | Fire Arrow | **Fire Arrow** — Fire opener (Mana) |
| 11 | R2C1 | 8 | Cold Arrow | **Cold Arrow** — Cold opener (Mana) |
| 12 | R2C2 | 8 | Multiple Shot | **Multiple Shot** — `0` Mana, Bow/Xbow cone clear (`Sighted` payoff, Stamina-scaled) |
| 16 | R3C3 | 16 | Exploding Arrow | **Exploding Arrow** — Fire AoE (Mana) |
| 21 | R4C1 | 24 | Ice Arrow | *Candidate slot for **`Siege Bolt` (`xbow`-only, no Stamina penalty)** or **`Countershot`**!* |
| 22 | R4C2 | 24 | Guided Arrow | **Guided Arrow** — `0` Mana, precision homing **Payoff** (`Sighted` bonus, Stamina-scaled) |
| 26 | R5C2 | 32 | Strafe | **Strafe** — `0` Mana, mobile multi-target (`Sighted` payoff, Stamina-scaled) |
| 27 | R5C3 | 32 | Immolation Arrow | **Immolation Arrow** — Fire ground burn / zone denial (Mana) |
| 31 | R6C1 | 40 | Freezing Arrow | **Freezing Arrow** — Cold AoE freeze capstone (Mana) |

*(Note: If we want **both** `Countershot` AND 2 Crossbow-only skills in Bow & Crossbow, we can either fold `Cold Arrow`/`Ice Arrow` into 2 Cold tiers (`Cold Arrow` + `Freezing Arrow`) and `Fire Arrow`/`Exploding Arrow`/`Immolation Arrow` into 2–3 Fire tiers, or place `Countershot` in Passive & Magic / reclaim `Ice Arrow` + `Fire Arrow`!)*

### Tree 2: Passive & Magic (`SkillPage = 2`)
| Id | Pos | Req | Vanilla Slot | Proposed Castalia Role |
|---:|:---:|---:|---|---|
| 8 | R1C1 | 1 | Inner Sight | **Inner Sight** — Defense shred + reveals + grants 4s **`Sighted`** opener! |
| 9 | R1C3 | 1 | Critical Strike | **Critical Strike** — Live passive |
| 13 | R2C2 | 8 | Dodge | **Dodge** — Live passive (`50% → 100%` Stamina; pairs with `attackedinmelee` → `Riposte`) |
| 17 | R3C1 | 16 | Slow Missiles | **Slow Missiles** — Signature ranged denial (pairs with `Countershot`) |
| 18 | R3C2 | 16 | Avoid | **Avoid** — Live passive (`50% → 100%` Stamina) |
| 23 | R4C3 | 24 | Penetrate | **Penetrate** — Live passive AR |
| 28 | R5C1 | 32 | Dopplezon | **Decoy** — Positional bait & frontline tank |
| 29 | R5C2 | 32 | Evade | **Evade** — Live passive (`50% → 100%` Stamina) |
| 32 | R6C1 | 40 | Valkyrie | **Valkyrie** — Frontline anchor (4-tier gear already built) |
| 33 | R6C3 | 40 | Pierce | **Pierce** — Live passive |

### Tree 3: Javelin & Spear (`SkillPage = 3`)
| Id | Pos | Req | Vanilla Slot | Proposed Castalia Role |
|---:|:---:|---:|---|---|
| 10 | R1C1 | 1 | Jab | **Jab** — `0` Mana, rapid spear/jav strikes (Stamina-scaled) |
| 14 | R2C2 | 8 | Power Strike | *Candidate slot for **`Riposte`** (Spear/Jav reactive counter, 3s `attackedinmelee` window)!* |
| 15 | R2C3 | 8 | Poison Javelin | **Poison Javelin** — Poison opener (grants 4s `Sighted` for melee follow-up!) |
| 19 | R3C1 | 16 | Impale | **Impale** — `0` Mana, heavy spear **Opener** (grants 4s `Sighted` + 33% Stun rule) |
| 20 | R3C3 | 16 | Lightning Bolt | **Lightning Bolt** — Single-target Lightning javelin (Mana) |
| 24 | R4C2 | 24 | Charged Strike | **Charged Strike** — Close-range Lightning payoff (`Sighted` bonus, tuned for Hell) |
| 25 | R4C3 | 24 | Plague Javelin | **Plague Javelin** — Poison cloud zone denial (Mana) |
| 30 | R5C1 | 32 | Fend | **Fend** — `0` Mana, multi-target spear **Payoff** (`Sighted` bonus, Stamina-scaled) |
| 34 | R6C2 | 40 | Lightning Strike | **Lightning Strike** — Chaining Lightning melee capstone (Mana) |
| 35 | R6C3 | 40 | Lightning Fury | **Lightning Fury** — Ranged Lightning split capstone (`Sighted` bonus, tuned for Hell) |

---

## 5. Next Decisions to Lock In
1. **Bow & Crossbow Slot Budget (10 slots):** To fit **`Countershot`** + **1–2 Crossbow-only skills** (`Siege Bolt`, `Ballista/Heavy Quarrel`), which vanilla Bow stepping stones should we consolidate? (e.g., `Cold Arrow` + `Ice Arrow` → single `Cold Arrow` + `Freezing Arrow`; `Fire Arrow` + `Exploding Arrow` → `Exploding Arrow` + `Immolation Arrow`!)
2. **Javelin & Spear Slot for `Riposte`:** Reclaiming **`Power Strike`** (redundant with `Charged Strike` / `Lightning Strike`) gives `Riposte` a clean Row 2 (Lvl 8) slot right alongside `Jab` and `Impale`!
3. **Conduction Co-Op Hooks:** Should Amazon's Fire/Cold Bow & Lightning Javelin skills receive Sorceress Conduction upgrades (matching Paladin & Assassin)?

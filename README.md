# Castalia

An opinionated overhaul of **Diablo II: Resurrected** built around a simple conviction: **a game world should feel like an intact, believable place to inhabit—and a few clear, honest rules, when pieced together carefully, can create near-infinite room for player creativity.**

> **Full Strategy Guide, Character Generator & Interactive Skill Compendium:**
> For complete interactive skill trees, live **Level 1 $\rightarrow$ 20 calculations**, synergies, Gem & Skull tables, all 33 Semantic Runes, and the browser-based **`.d2s` Character Generator**, visit **[https://grant0711.github.io/d2r-castalia/](https://grant0711.github.io/d2r-castalia/)** (or open **[`docs/site/index.html`](docs/site/index.html)** locally).

---

## Quick Start

### Who This Mod Is For & What to Expect
This mod is built for **veteran Diablo II players** who want to experiment with a reimagined skill and resource economy—experiencing a more grounded, tactical version of *Diablo II* rather than an overpowered power-fantasy.
- **Playthrough-Focused (Solo or Co-op)**: Designed to be played alone or with friends as a complete journey from Act 1 Normal through Act 5 Hell. There is no artificial endgame treadmill; once your playthrough is complete, the journey is complete.
- **What You See Is How It Works**:
  - Every monster prints its **elemental vulnerability, resistance, and combat trait** directly beneath its health bar.
  - Physical silhouettes tell the truth: if a monster is **small**, it is fast, numerous, and fragile; if it is **huge**, it is slow, solitary, and hits like a truck.
  - Intuitive connections reward paying attention to the world: town mystics and sages stock caster gear, heavy tower shields slow your block recovery in exchange for armor, and pulling on an enclosed greathelm narrows your light radius in the dark.

### The 7 Horadric Cube Recipes
Everything in the item and crafting economy revolves around **7 Horadric Cube recipes** using materials you find in the world and two tools sold in town (**`Blacksmith's Malus`**, bought from any town's Gamble screen, and **`Untempered Malus`**, bought from Charsi and tempered via her *Tools of the Trade* quest):

| Goal | Horadric Cube Inputs | Output |
| :--- | :--- | :--- |
| **1. Craft Any Item** | **Any Magic Item** + **1 Gem / Skull** + **2 Runes** | **Crafted Item** stamped with the Gem's stat + both Runes' stats *(scaled by Gem quality)* + `1–4` random affixes |
| **2. Distill a Unique / Set** | **Any Unique or Set Item** + **Blacksmith's Malus** + **Magic Jewel** | **Crafted Jewel** containing that Unique or Set item's **Top 4 signature stats** |
| **3. Punch Sockets** | **Unsocketed Weapon / Armor** + **Blacksmith's Malus** + **Perfect Skull** | Adds **1 to 2 Sockets** to the item *(works on Magic, Rare, Crafted, Set, or Unique)* |
| **4. Clear Sockets** | **Socketed Weapon / Armor** + **Blacksmith's Malus** + **Perfect Skull** | **Clears all sockets** on the item *(destroying socketed contents so you can re-socket)* |
| **5. Upgrade Item Base Tier** | **Normal or Exceptional Item** + **Tempered Malus** *(Charsi Quest)* | Upgrades the item's base tier (**Normal $\rightarrow$ Exceptional** or **Exceptional $\rightarrow$ Elite**, 3 per playthrough) |
| **6. Combine / Split Runes & Gems** | **`2x` Identical Gems/Runes** *—or—* **`1x` Rune + `1x` Gem** | **Upgrades** `2-to-1` into the next tier *—or—* **Splits** a Rune into lower runes (`50%` to `100%` recovery by Gem tier) |
| **7. Open a Lockbox** | **Crude / Iron / Ornate Lockbox** + **Matching Lockbox Key** *(Sold in Town)* | Unlocks the **Unique or Set item** sealed inside |

---

## Core Design Principles

1. **Simple Pieces, Infinite Combinations**:
   - Traditional Runewords are removed. Instead, **7 Gem & Skull Families** and **33 Semantic Runes** each grant strictly **one property per slot** with zero overlap.
   - Placing **any Magic item + 1 Gem/Skull + 2 Runes** into the Horadric Cube stamps what you see on the Gem and the two Runes directly onto your item, scaled by the quality of the Gem.
2. **Keeping the World Intact**:
   - Town Portals, Rejuvenation potions, and universal `Teleport` do not exist.
   - Health and Mana potions restore over time on a short cooldown, **Preparation Elixirs** (*Thawing*, *Antidote*, *Stamina*) provide long-duration expedition buffs, and **Wells** and **Recovery Shrines** act as tactical field checkpoints.
3. **Every Item Color Has Its Own Crown & No Free Immunity Breakers**:
   - **Magic (Blue)** items roll up to 2 affixes with higher single-stat ceilings and exclusive binary traits; **Rare (Yellow)** items roll up to 6 solid stats with low-level junk tiers pruned out; **Crafted (Orange)** items combine deterministic Gem + Rune stats with random rolls; **Uniques & Sets** offer build-defining traits or can be distilled into **Crafted Jewels**.
   - Sunder Charms and player sources of `-Enemy Elemental Resistance %` pierce do not exist; overcoming heavily resistant monsters requires a rounded toolkit across elements, physical damage, crowd control, and **10-Slot Mercenaries**.
4. **Less Screen Noise, Sharper Decisions & Rhythm in Combat**:
   - Monster density is lower, every combat zone spawns **strictly 1 random Unique Boss Pack**, breakable clutter is disabled, 100% of equipment drops are at least **Magic (Blue)**, and **26 Optional Exploration Dungeons** offer heightened challenge and rewards.
   - Reworked classes (**Paladin**, **Barbarian**, **Assassin**, and **Sorceress**) revolve around active combat rhythms rather than passive town pre-buffs. See **[The Castalia Compendium](docs/site/index.html)** for all 120 skill descriptions and calculations.
5. **A Gold Economy That Actually Matters**:
   - Vendor sell-back prices are capped low so Gold is earned by fighting monsters, opening **Super Chests**, and stacking **Gold Find**—and spent on equipment repairs, **Blacksmith's Maluses**, **Lockbox Keys**, **Untempered Maluses**, and **Act-Partitioned Magic Vendors**.

---

## Deterministic Build & Verification Pipeline

All mod data files (`castalia/data/`), invariant checks, and the strategy guide website ([`docs/site/index.html`](docs/site/index.html)) are built from a single deterministic pipeline so that documentation and in-game values can never drift:

```bash
./bin/d2r-build-mod.py
```

Running `./bin/d2r-build-mod.py`:
1. Transforms pristine reference tables from `vanilla-reference/` into `castalia/data/` (`game/Diablo II Resurrected/mods/castalia/castalia.mpq/data/`).
2. Runs the full invariant verification suite (`tools/mod_builder/verify.py`).
3. Rebuilds [`docs/site/index.html`](docs/site/index.html) (`tools/build_site.py`) directly from the compiled `.txt` and `.json` outputs in `castalia/data/`.

### Developer Documentation
- **Roadmap & Class Status**: [`docs/ROADMAP.md`](docs/ROADMAP.md)
- **Technical Architecture & CLI Reference**: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Per-Class Technical References**: [`docs/classes/`](docs/classes) (`paladin.md`, `barbarian.md`, `assassin.md`, `sorceress.md`, `amazon.md`)
- **Engine Reference & Pitfalls**: [`docs/engine/FUNCTIONS.md`](docs/engine/FUNCTIONS.md) & [`docs/engine/STATS_AND_PITFALLS.md`](docs/engine/STATS_AND_PITFALLS.md)

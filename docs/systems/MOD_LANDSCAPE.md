# Castalia — D2R Mod Landscape Analysis & Playtester Positioning

> **Snapshot Date:** 2026-11-25  
> **Source:** Nexus Mods **Diablo II: Resurrected** (`1,033` total mods) — full 28-day inventory (`timeRange=28`, 43 mods) + All-Time Top 160 by endorsements (`timeRange=allTime`).  
> **Purpose:** Understand what drives long-term popularity on D2R Nexus, how recent uploads fit into those trends, where Castalia sits, and how to recruit/convert alpha & beta co-op playtesters.

---

## 1. Landscape Breakdown (43 Mods in 28 Days)

| Archetype | Count | Share | Dominant Pattern |
| :--- | :---: | :---: | :--- |
| **Micro-Tweaks (Single Skill / Item / Cube / Drop)** | **16** | 37% | One-off D2RMM edits: rune downgrading, socket clearing, NPC rune/gem shops, single-skill multipliers (`Poison Dagger`, `Multiple Valkyries`), drop-rate sliders. |
| **D2RLoader Plugins & Save/Map Tooling** | **8** | 19% | Rapidly growing wave of native **D2RLoader C++ plugins** (`Gamble Stash Gold`, `Potion Auto-Belt`, `GrailTrackrr`, `Ragdoll Physics`, `A Darker Atmosphere`) plus brand-new **HD 3D Map/Level Editors**. |
| **Overhauls & Deep System Reworks** | **7** | 16% | Only **3** full-game overhauls (`New Sanctuary`, `BKDiablo The Ascension`, `The Shattered Scale`), **1** atmospheric overhaul (`A Darker Atmosphere`), and **3** focused system reworks (`Revamped Charms`, `Revamped Crafting`, `Classless Skill Trees`). |
| **Content, Maps & Endgame Extensions** | **6** | 14% | `Act VI - The Fallen Star` (prototype 6th Act), `The Abyss` endgame map, `Exalted Items` (4th tier above Elite), `Permanent Terror Zones`, `Boss Multiplier (1x–10x)`, `Legacy of Terror Unleashed`. |
| **Cosmetics, Models & Performance Mods** | **6** | 14% | Character model swaps (`Red Riding Hood Amazon`, `Playable Slinger`), `Bobblehead`, `Status Effect Tint Overhaul`, `Lighter Makeup`, `miniS Black Screen` (multiboxing). |

---

## 1B. All-Time Popularity Analysis (`1,033` Mods) & How the Last 28 Days Fit In

Looking at the **All-Time Top 50** by endorsements reveals the structural reality of the D2R Nexus audience:

### What Dominates All-Time Popularity
1. **The "Build-Your-Own Vanilla+" D2RMM Core Stack (42 of Top 50):**
   * `D2RMM` (`#1`, `5,303` endorsements / `350k` downloads) and `olegbl`'s 2022 starter suite (`19` of the Top 40 alone) dominate the endorsement leaderboard.
   * The top-endorsed individual mods are overwhelmingly **tedium & friction removers** (`Expanded Inventory` #2, `Expanded Stash` #4, `Stackable Runes/Gems` #5/#6, `Increase Stack Size` #10, `MercEquip` #12, `Socket Punching` #13, `Show Item Level` #15, `Expanded Cube` #19, `Decrease Clutter Drops` #33, `Skip Intro Videos` #36, `Numbered Rune Names` #38) and **power/loot accelerators** (`Increase Droprate` #3, `Increase Monster Density` #8, `Perfect Drops` #11, `CheatyMods` #14, `Singleplayer Runewords` #16, `Rune Easy Upgrade` #17, `Increase Sunder Charm Drops` #21, `Charm of Teleport` #34, `Remove Monster Immunities` #37, `Runes and Gems on Sale` #40).
2. **The Overhaul Breakout Proof Point — `D2R Reimagined` (`#9` Endorsements, `#2` All-Time Downloads):**
   * Although only **3** mods in the Top 50 are categorized as `Overhauls`, **`D2R Reimagined`** (`#9`, `1,749` endorsements, created 2024, actively updated Oct 2026) has **`337,167` downloads**—**#2 across the entire D2R Nexus**, nearly tying `D2RMM` itself (`350k`) and beating `Expanded Inventory` (`152k`) and `Increase Droprate` (`140k`) by **2.2×–2.4×**.
   * **Takeaway:** A cohesive, actively maintained total overhaul captures *far more repeat engagement and real players* than single micro-mods, even if legacy 2022 D2RMM tweaks hold higher raw endorsement counts from 4+ years of passive installs.
3. **2026 Patch Survival Matters:**
   * Almost every still-active Top 40 mod was updated in **2026** for D2R's *Reign of the Warlock* (3.3/3.4) patch. Consistent maintenance (`bin/d2r-vanilla-sync` + `bin/d2r-release`) is a major moat on Nexus.

### How the Last 28 Days Fit Into All-Time Trends
* **Commoditized Tail (Micro-Tweaks):** Most of the 16 micro-tweaks from the last 28 days (`AIO Droprate`, `NPC Sells Gems/Runes`, `Bulk Cubing`, `Unsocket Keep`, `Double Damage Poison Dagger`) are **remakes or niche variants of the 2022 `olegbl` D2RMM stack**. They have a low ceiling because those slots are already saturated.
* **The Real 2026 Frontier (2 New Waves That Didn't Exist in 2022):**
  1. **D2RLoader Native C++ Plugins** (`A Darker Atmosphere`, `Gamble Stash Gold`, `Potion Auto-Belt`, `GrailTrackrr`, `Ragdoll Physics`) — unlocking runtime behaviors `.txt` edits could never touch.
  2. **New Total Overhauls & Custom Acts/Maps** (`New Sanctuary`, `BKDiablo`, `The Shattered Scale`, `Act VI`, `D2R Level Editor`) — chasing `D2R Reimagined`'s 337k-download trail, though still overwhelmingly focused on endgame power creep.
* **Why Castalia's UX Choices Quietly Bridge the Gap:** Castalia *already* solves many of the legitimate QoL pain points behind the Top 40—**10-slot mercenaries** (`#12`), **zero-white clutter floor** (`#33`), **deterministic socket punching** (`#13`), **2-to-1 rune/gem upgrading & splitting** (`#17`), and **transparent monster traits**—while keeping them **diegetic and balanced** instead of turning the game into a cheat sandbox.

---

## 2. How Castalia Fits In (Strategic White Space)

1. **Uncontested Niche — Grounded, Diegetic Playthrough Overhaul:**
   * Almost every active overhaul (`New Sanctuary`, `BKDiablo`, `The Shattered Scale`) and content extension (`Exalted Items`, `Boss Multiplier`, `Permanent Terror Zones`) doubles down on **endgame power-creep fantasy**—Super/Uber TZs up to mlvl 106, item corruption, 4th-tier bases, relics, and faster loot piñatas.
   * **Nobody** in the active Nexus window is building what Castalia builds: a **playthrough-first, zero-runeword, zero-sunder-pierce, diegetic overhaul** designed to protect the *magic circle* (no Town Portals, honest monster silhouettes/traits, meaningful light radius/durability/gold, active combat rhythms, and tactical co-op roles).
2. **D2RLoader Is Clearly the Winning Co-Op Platform:**
   * Multiple high-effort projects now target **D2RLoader** natively rather than legacy D2RLAN, validating Castalia's choice to build and distribute around D2RLoader.
3. **Zero-Drift Compendium & `.d2s` Tooling Is a Differentiator:**
   * Most mods rely on static Nexus description walls that quickly drift from actual `.txt` values. Castalia's auto-generated Arreat Summit Compendium + live formula calculator + `.d2s` builder immediately signals polish and seriousness.

### 2B. Benchmark Comparison: D2R Reimagined vs. Castalia
**D2R Reimagined** (`337k` downloads, #2 most-downloaded D2R mod of all time) is the defining **maximalist, PoE-inspired solo power-sandbox** in D2R modding—and the cleanest philosophical foil for positioning Castalia:

| Dimension | **D2R Reimagined** | **Castalia** |
| :--- | :--- | :--- |
| **Design Ethos** | **Maximalist Sandbox** (PoE/PD2-style content & currency multiplication) | **Minimalist / Diegetic Systems** (*"Simple pieces, infinite combinations"*) |
| **Core Loop** | Fast solo gearing → endgame farming, corruption orbs, TZs to lvl 99 | Grounded Act 1 Normal → Act 5 Hell journey (solo or tactical co-op) |
| **Itemization & Crafting** | 1,400+ uniques, 220+ runewords, 1,000+ cube recipes, Corruption Orbs | **0 Runewords**, 7 Gems + 33 Semantic Runes, **7 Cube Recipes** you can memorize |
| **Immunities & Combat** | Elemental pierce on gear + Sunder + Melee Splash charm | **Zero player elemental pierce**; multi-element toolkits, CC, Stamina/Mana rhythms & 10-slot mercs |
| **Magic Circle / Friction** | Removes friction (huge bags, fast runes, teleport/splash) | Preserves *meaningful* friction (no Town Portals, no Rejuvs, real Gold/Durability/Light Radius) |
| **Multiplayer Feel** | D2RLoader supported, tuned primarily around solo P7/P8 melt | Built around **co-op roles** (`Conduction`, Healer/Resource Trinity, `maxhp`-escalating boss phases) |

**What Community Critiques of Reimagined Reveal:** On Reddit (`r/diablo2`, `r/Diablo_2_Resurrected`, `r/D2RReimagined`), players praise Reimagined's build diversity, polish, and D2RLoader integration—but repeatedly cite **power creep** (P7/P8 melting once geared), **over-accelerated progression**, **wiki/recipe bloat** (1,000+ cube recipes), and **spiky feast-or-famine pacing**. That exact burnout profile is Castalia's highest-converting target audience.

---

## 3. Marketing & Playtester Acquisition Strategy

### 3A. The Core Ask: "Install the Castalia Launcher → Join a D&D-Style Micro-Adventure"
Building the **[Castalia Launcher & Campaign Hub](file:///home/grant/games/d2r/docs/systems/LAUNCHER_SPEC.md)** fundamentally changes our marketing pitch—from selling a *balance mod* (high friction, invites armchair debate over removals) to selling a **1-click social experience**:

* **Old Ask (Mod-First — High Friction):** *"Extract this zip, configure D2RLoader, read our manifesto on why Runewords and Town Portals are gone, and trust us that it's fun."*
* **New Ask (Experience-First — Low Friction):** **"Install the Castalia Launcher and drop into a 2-hour, D&D-style Diablo II micro-adventure this week—or host your own."**
  * Players browse live scheduled campaigns in their local timezone, click an open seat, auto-sync the pinned Castalia version, generate a **level- and Act-matched Drop-In Starter-Kit character** straight into an isolated campaign profile, and jump into D2RLoader co-op in 60 seconds.
  * Once they're inside a live 4-player Act push—crafting their kit in town with 7 simple Cube recipes and feeling `Conduction`, `Second Wind`, and `Meditation` save the squad—Castalia's grounded design sells itself.

### 3B. Targeting Burned-Out D2R Reimagined & Maximalist ARPG Players (Primary Growth Channel)
**Who they are:** Veteran D2 players who installed D2R Reimagined (or PD2/PoE-style mods), loved the fresh skill trees and D2RLoader polish for 2–4 weeks, and then hit *maximalist fatigue*—alt-tabbing to a 1,000-recipe wiki, melting `/players 8` Hell in corrupted BiS gear, and missing the tense, readable magic circle of a real *Diablo II* playthrough. **Crucially, they already have D2RLoader installed**, eliminating the #1 onboarding barrier.

#### Messaging Pillars (Respectful Contrast — Never Trash-Talk Reimagined)
Acknowledge Reimagined as a great maximalist sandbox, and position Castalia as the **clean, grounded, co-op-adventure counterpart**:
1. **"D&D-Style Micro-Adventures in Diablo II."** — Install the Castalia Launcher to host or drop into scheduled 2-hour co-op sessions (no 500-hour solo grind required; drop-in Starter Kits match the Host's exact Level & Act).
2. **"7 Recipes. 0 Runewords. Zero Wiki Alt-Tabbing."** — Replace 1,000+ cube recipes and 220+ runewords with 7 Gem families, 33 single-stat Runes, and 7 Horadric Cube recipes you can memorize in 60 seconds.
3. **"No Power-Creep Treadmill — A Complete Journey."** — Designed for Act 1 Normal → Act 5 Hell where Magic, Rare, Crafted, Unique, and Set items each keep a real identity from Level 1 to Level 85, ending in a **Hall of Heroes** party chronicle.
4. **"Tactical Combat Rhythm Over Screen-Melting."** — Active class rhythms (Stamina Pendulum, Aura Mana Devotion, 15m Combo Orbs, Elemental Stances & Co-Op Conduction), honest monster silhouettes and vulnerability readouts right under their health bar, and zero free elemental pierce.

#### Acquisition Channels & Tactics
* **D2RLoader Community & Discord:** Reimagined players already live here. Lead with the launcher & live open seats (*"Tonight at 8 PM: 2 open seats for a Level 48 NM Act 3 Castalia micro-adventure — grab the Launcher to auto-sync & roll a Drop-In character in 60 seconds"*).
* **Reddit Comparison Threads (`r/diablo2`, `r/Diablo_2_Resurrected`, `r/D2RReimagined`):** Show up helpfully whenever players explicitly ask *"Is there a tighter, less power-crept alternative to Reimagined?"* or *"What's the best co-op overhaul for D2R?"* (where BTDiablo is currently the default answer).
* **Nexus Mods Landing Page & Compendium Hero:** Lead with the **Castalia Launcher** download + 30-second micro-adventure pitch, a clean 4-row feature contrast, and a direct link to the live **Castalia Compendium**.
* **Show, Don't Tell (20–30s Visual Proof Clips):** Short clips of tactile moments that sell the philosophy without a wall of text: clicking "Join" in the Launcher → crafting an orange item in town with 1 Gem + 2 Runes → monster trait readouts under health bars → Sorceress `Conduction` empowering a Paladin's `Fist of the Heavens` in co-op.

### 3C. Alpha/Beta Playtesters from the Mod Author Pool: Audience Segmentation & Conversion

Many of the authors posting single-item or single-skill D2RMM tweaks are **strong candidates for Castalia alpha/beta playtesting**: they already know how to install mods, navigate D2R's mod directories, and diagnose vanilla pain points—even if they lack the engineering bandwidth to architect a full overhaul.

However, recruiting them requires understanding **two distinct mindsets**:

### Tier A — Natural Philosophical Allies (Already Understand the Magic Circle)
These authors already demonstrate instincts aligned with Castalia's diegetic, grounded design:
* **`latedozer`** (*A Darker Atmosphere*, MIT-licensed D2RLoader plugin): The clearest philosophical match in the entire snapshot. Understands darkness, fog, light-radius meaning, non-trivial environmental tension, and grounded immersion. Top candidate for both early playtesting and technical/fork collaboration (see [`docs/ROADMAP.md`](file:///home/grant/games/d2r/docs/ROADMAP.md) Item 5).
* **`Sadie227`** (*Revamped Charms*, *Revamped Crafting*): Already designing around *playthrough-relevant crafting* and *preserving distinct Magic vs. Rare item identities*—directly adjacent to Castalia's "Every Item Color Has Its Own Crown" principle.
* **`DevilInLaw`** (*Status Effect Tint Overhaul*, VR immersion tweaks): Values visual immersion and breaking away from arcade-y defaults, even if some of their other mods are sandbox experiments.

### Tier B — Mod-Literate Micro-Tweak Authors (Require Subtle Framing & Conversion)
* **Why they are valuable:** They care deeply about D2R, actively experiment with offline/modded play, and are comfortable running modded setups.
* **The primary friction:** Their default mental model of "fun" is heavily conditioned by **modern ARPG / LoD endgame power creep** (bigger multipliers, vendor runes, infinite replenishing consumables, removing friction rather than making friction meaningful).
* **How to convert rather than alienate:**
  1. **Lead with Agency & Craft, Not Restrictions:** Never open a pitch with *"We deleted Runewords, Town Portals, and Teleport."* Lead with what comes alive: *"Every Magic, Rare, and Crafted drop is exciting from Act 1 Normal; 7 deterministic Horadric Cube recipes let you build custom gear out of Gems and Runes; every class has active combat rhythms and co-op synergies."*
  2. **Convert Through Live Co-Op, Not Manifestos:** A power-creep-trained player reading rules on paper may feel constrained; that same player experiencing a tense Act 2 tomb push where a Barbarian's `Second Wind`, a Paladin's `Meditation`, and a Sorceress's `Conduction` save the party *feels* the magic circle immediately. Invite them into **guided weekly co-op sessions** using Castalia's `.d2s` builder for frictionless onboarding.
  3. **Respect Their Curiosity About Systems:** Micro-tweak authors love peeking under the hood. Pointing them to the interactive **Compendium skill calculator** lets them theorycraft builds before ever launching the game, hooking their tinkerer instinct on Castalia's ruleset.

---

## 4. Technical & Design Signals Worth Tracking

* **Co-Op Summon Collision (`Summons Without Collision`, #1395):** Directly relevant to Castalia's planned Necromancer/Druid co-op readability guardrail (preventing summons from body-blocking melee teammates).
* **Save Isolation Validation (`D2R Hero Studio`, #1367):** The #1 most endorsed/downloaded upload of the month (`1,177` downloads) is a polished offline `.d2s` Hero Editor—confirming that Castalia's planned **`CSvBits` save isolation** ([`COOP_ENCOUNTERS.md`](file:///home/grant/games/d2r/docs/systems/COOP_ENCOUNTERS.md#L152-L165)) is necessary before running open community co-op campaigns.
* **Atmospheric Plugin Architecture (`A Darker Atmosphere`, #1391):** Proves D2RLoader PluginSDK ABI 4 plugins can live cleanly inside `mods/<mod>/d2rloader/plugins/` alongside standard `.txt`/JSON mod tables.
* **Emerging HD Map Tooling (`D2R Level Editor` #1417, `D2R map editor` #1383, `Act VI` #1418):** Early-stage, but worth watching long-term for potential custom Castalia expedition dungeons.

---

## 5. Complete 28-Day Nexus Mods Inventory (43 Mods)

### Full & System Overhauls (7)
| ID | Mod | Author | End / DL | Summary |
| :--- | :--- | :--- | :---: | :--- |
| `1360` | **Revamped Charms** | Sadie227 | 3 / 205 | Rebalances charm affixes; Large Charm niche; Rare charms enabled while apex affixes remain Magic-only. |
| `1397` | **New Sanctuary** | New Sanctuary | 2 / 205 | Full overhaul: Super/Uber TZs (mlvl 106), Standards of Heroes MF, Smithing Tools, item corruption. |
| `1365` | **BKDiablo The Ascension** | Kex & BaronBeefStick | 1 / 130 | Continuation/rebrand of BTDiablo ("Vanilla+" overhaul). |
| `1389` | **The Shattered Scale** | luukatyuo | 1 / 145 | Full overhaul: buffed relics, reworked cube recipes, tougher Hell, new zones. |
| `1401` | **Classless Skill Trees** | DevilInLaw | 1 / 87 | Pick up to 5 skill schools from any class across all classes. |
| `1391` | **A Darker Atmosphere** | latedozer | 0 / 153 | Endless night, darkness/fog + D2RLoader plugin for Act-specific storms, hazards, whispers & optional phantoms. |
| `1419` | **Revamped Crafting** | Sadie227 | 0 / 14 | Reworks crafting recipes to be usable during a normal playthrough instead of post-game only. |

### D2RLoader Plugins & Developer Tools (8)
| ID | Mod | Author | End / DL | Summary |
| :--- | :--- | :--- | :---: | :--- |
| `1367` | **D2R Hero Studio - Character Editor** | Sentry0001 | 10 / 1177 | Standalone Windows offline `.d2s` save/item/stash/quest editor. |
| `1402` | **D2R Ragdoll Physics Mod** | 4Spartah | 9 / 377 | Ragdoll physics for enemies + reactive scenery (D2RMM + D2RLoader). |
| `1371` | **Gamble Stash Gold** | Bnadit | 3 / 184 | D2RLoader plugin allowing gambling/buying directly from shared stash gold. |
| `1383` | **D2R map editor (prototype)** | josefkramer96 | 2 / 42 | Prototype D2R map editor for building custom maps. |
| `1379` | **Potion Auto-Belt VR** | DevilInLaw | 0 / 180 | D2RLoader plugin auto-refilling consumed belt columns from inventory. |
| `1398` | **GrailTrackrr - Live Holy Grail Tracker** | ccninja89 | 0 / 19 | D2RLoader plugin streaming live drops to web overlays/alerts. |
| `1417` | **D2R Level Editor** | loger444 | 0 / 4 | 3D HD map editor: place/move models, edit collision, create NPCs, import 3D models. |
| `1411` | **Hellstorm Maul** | NotThe001 | 0 / 9 | Single custom fire/storm maul item. |

### Content, Maps & Endgame Extensions (6)
| ID | Mod | Author | End / DL | Summary |
| :--- | :--- | :--- | :---: | :--- |
| `1369` | **Boss Multiplier - Endgame Bosses Only** | NoodleGod | 2 / 111 | Multiplies the 5 Act Bosses (`1x`–`10x`) via D2RMM. |
| `1386` | **Permanent Terror Zones** | stochacha | 2 / 162 | Customizable permanent TZ group toggling for RotW (D2RMM). |
| `1403` | **Legacy of Terror Unleashed** | latedozer | 1 / 161 | Permanently enables the Legacy of Terror event in modded play. |
| `1414` | **Exalted Items** | latedozer | 1 / 80 | Adds a 4th item base tier above Elite with Restoration Crystals in the cube. |
| `1390` | **New endgame map The Abyss** | josefkramer96 | 0 / 111 | Custom endgame farming zone built with the prototype map editor. |
| `1418` | **Act VI - The Fallen Star** | loger444 | 0 / 19 | Experimental 6th Act (new town, 6 NPCs, 9 areas, 6 bosses, quest chain). |

### Micro-Tweaks: Drops, Cube, Skills & QoL (16)
| ID | Mod | Author | End / DL | Summary |
| :--- | :--- | :--- | :---: | :--- |
| `1374` | **AIO Droprate** | kakalot289 | 4 / 271 | Configurable `itemratio.txt` + `TreasureClassEx.txt` drop rate/junk pruner. |
| `1376` | **Barbarian Heavy Axe Dual-Wielding** | DevilInLaw | 4 / 150 | Lets Barbarians dual-wield all 15 2H axes at configurable % damage (D2RMM). |
| `1388` | **Base Light Radius Increase** | DevilInLaw | 4 / 115 | Raises base light radius from 13 to 20 (D2RMM). |
| `1358` | **Carry Multiple Unique Objects** | luciano96369 | 3 / 240 | Removes unique-charm/item carry limit (D2RMM). |
| `1380` | **Necromancer Poison Dagger to Poison Weapon** | DevilInLaw | 2 / 67 | Lets Poison Dagger work with any weapon + configurable damage % (D2RMM). |
| `1394` | **Unsocket Keep** | Lucaliosse | 1 / 153 | Cube recipe: Socketed item + ID Scroll returns empty item + socketed contents. |
| `1395` | **Summons Without Collision** | Leaf16591 | 1 / 113 | Removes collision from player summons so they don't body-block. |
| `1415` | **NPC Sells Gem Jewels Runes and Charms** | luciano96369 | 1 / 128 | Town vendors sell gems, jewels, runes, and charms. |
| `1370` | **Bulk Cubing and Rune Downgrading** | Sadie227 | 0 / 127 | 2x/3x gem & rune upgrades (2-to-1, no gem) + 1-to-2 rune downgrading. |
| `1373` | **Replenishing Utility Items** | kakalot289 | 0 / 64 | Cube recipe adds Replenishes Quantity to tomes, keys, arrows, bolts, javelins. |
| `1375` | **Double Damage Poison Dagger** | gamaxe | 0 / 27 | 2x damage on Necromancer Poison Dagger. |
| `1387` | **Health Regen Charms** | latedozer | 0 / 118 | Large charms can roll % max-life replenish (or buy from Gheed, D2RMM). |
| `1392` | **Probabilistic Rune Downgrade** | k0102575 | 0 / 19 | Downgrade Eld–Zod runes with a Gheed hammer + 4 probabilistic outcomes (D2RMM). |
| `1399` | **Multiple Valkyries** | HossmannX | 0 / 70 | +1 Valkyrie every 5 skill levels (D2RMM). |
| `1408` | **NPC and Enemies Names - Merc Icon Patch** | ATGSleg | 0 / 42 | Compatibility patch removing a stray Merc icon in Kurast Docks. |
| `1413` | **Chronicle-style new accomplishments** | josefkramer96 | 0 / 59 | Adds Chronicle-style goals unlocking cosmetic effects. |

### Cosmetics, Models & Visual/Performance Mods (6)
| ID | Mod | Author | End / DL | Summary |
| :--- | :--- | :--- | :---: | :--- |
| `1378` | **Status Effect Tint Overhaul** | DevilInLaw | 2 / 40 | Tones down harsh bright green/blue poison & cold monster tints (D2RMM). |
| `1405` | **Red Riding Hood Amazon** | purerageone | 2 / 150 | Custom Amazon character model port (D2RMM). |
| `1400` | **D2R playable Slinger** | xjt0529 | 1 / 19 | Replaces Amazon model with enemy Slinger model. |
| `1410` | **miniS Black Screen Mod** | VeteranAMao | 1 / 25 | Blocks HD rendering for low-VRAM multiboxing. |
| `1368` | **Lighter Makeup for Assassin Face Reshape** | NudeMortals | 0 / 41 | Sub-patch tweaking Assassin face texture makeup. |
| `1412` | **D2R Bobblehead Mod** | 4Spartah | 0 / 42 | Classic 90s "Big Head Mode" (3x character/monster heads, D2RMM + D2RLoader). |

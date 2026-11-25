# Castalia "Expedition Mode" Design Plan

> **Core Concept:** Remove all **34 field Waypoints** (keeping only the **5 Town Waypoints** for Act-to-Act travel) alongside Castalia's existing **no-Town-Portal** design. Stepping outside town becomes a genuine, self-contained **dungeon-crawl expedition** from Town to Act Boss — living off field drops, shrines, on-the-go Horadric Cube crafting, and co-op class sustain.

---

## 1. Why Expedition Mode Fits Castalia

Castalia already removes Town Portals and Runewords, enforces real Mana/Stamina resource economies, and provides an on-the-go Horadric Cube crafting system (`390,000+` Gem/Rune recipes). Removing field Waypoints completes that loop:

- **Every departure from town is a commitment:** You prepare your belt, stash, and gear in town, then push outward as a party.
- **On-the-go progression:** Players craft upgrades in the field using the Horadric Cube with Magic/Rare bases, Gems, and Runes found along the way.
- **Co-op sustain roles become vital:** Without instant town trips for potions and healing, Paladin (`Prayer`, `Holy Bolt`, `Meditation`, `Vigor`), Barbarian (`Battle Command`, `Second Wind`, `Enduring Cry`), and Druid (`Life Totem`, `Mana Totem`) shift from "nice to have" to expedition-saving anchors.
- **Natural XP pacing:** Castalia's tuned XP curve already supports playing cleanly through each Act simply by clearing monsters along the route — no repetitive boss-waypoint farming loops required.

---

## 2. Technical Implementation (Minimal `.txt` Changes)

1. **`levels.txt`:**
   - Set `Waypoint = 255` on all **34 field levels**.
   - **Keep the 5 Town Waypoints** (`Act 1 - Town` through `Act 5 - Town`) active so characters can still travel backward from Act 4 / Act 5 to earlier Acts (since no NPC sails back from Act 4 → Act 3 or Act 5 → Act 4).
2. **`objects.txt`:**
   - Keep Town Waypoint pads active (`OperateFn = 23`), or selectively disable field Waypoint objects if any preset map tiles still spawn them when `Waypoint = 255` (`OperateFn = 0`, `Selectable0 = 0`, `Draw = 0`, `AutoMap = 0`).
3. **Optional Config Flag (`mod_config.json`):**
   - Gate behind `"expedition_mode": true/false` so it can be toggled cleanly during development and testing without breaking existing saves.

---

## 3. Required Economy & Field-Sustain Adjustments

Because town is currently a necessary stock-up point in Castalia, Expedition Mode requires targeted field-sustain tweaks while strictly preserving Castalia's core resource tensions:

1. **Field Potion Drop Rates & Superchest Windfalls (`TreasureClassEx.txt`):**
   - Increase `Potion` weights (Health, Mana, Rejuvenation, and Stamina/Antidote/Thawing) on regular monsters so active clearing steadily replenishes belts in the field.
   - Destructible pots/barrels are already removed in Castalia — **only Superchests remain**. Boost Superchest supply/potion weights so discovering a Superchest together feels like a true expedition windfall.
   - Double-check existing Act/Difficulty potion tier scaling (`hp3..hp5`, `mp3..mp5`) during implementation (already built in base Castalia).
2. **Gear Durability & Arrow/Bolt Resupply (Strict Diegetic Constraints):**
   - **Durability (NO Cube repair recipes):** Castalia already doubles weapon durability. We will **not** add non-diegetic Cube repair recipes — if a weapon breaks mid-expedition, the player must make a real survival choice: haul it in inventory until the next town/Act, swap to a found weapon, or leave it behind.
   - **Quivers (`aqv` / `cqv`):** Keep stack size strictly at **255** (nostalgia). Only bump field quiver drop rates slightly if playtesting shows Bow/Crossbow Amazons running dry mid-expedition.
3. **Identify Scarcity (Preserved Tension):**
   - **Never make Identify scrolls plentiful.** Scarcity of Identify scrolls is an intentional Castalia resource constraint — forcing players to decide whether to spend a scroll identifying a Magic item or throw it straight into the Horadric Cube unidentified.
4. **Shrines & Wells:**
   - Do **not** increase Shrine/Well spawn density; instead, consider slightly **decreasing their refresh delay** (`shrines.txt`) if long expeditions need extra sustain checkpoints.

---

## 4. Pure Expedition Pacing & Resistance Cohesion

Expedition Mode commits strictly to **Pure Expedition** (zero field Waypoints — no mid-Act checkpoint fallback). Because quest items (Horadric Staff, Khalim's Will, etc.) persist across sessions, multi-session Acts still preserve quest progress even when restarting from Town.

- **Act 1 & Act 4:** Compact, natural single-expedition arcs (Rogue Encampment → Catacombs 4; Pandemonium Fortress → Chaos Sanctuary).
- **Act 2, Act 3 & Act 5:** Longer multi-leg treks (e.g., Rocky Waste → Claw Viper Temple; Spider Forest → Kurast → Durance 3; Bloody Foothills → Worldstone Keep).
- **Expedition-Path Resistance Cohesion Audit (Important):**
  - Before finalizing Expedition Mode, audit monster resistance and vulnerability profiles **along each continuous expedition path** (e.g., Rocky Waste → Dry Hills → Far Oasis → Lost City → Valley of Snakes → Claw Viper Temple).
  - Keep resistance/immunity variability cohesive across a single expedition leg so a focused buildout can feasibly navigate the full leg from start to finish without slamming into contradictory immunity walls back-to-back (and consider aligning base Castalia's resistance map with expedition legs as well).
- **Co-Op Boss Quest Credit on Death:**
  - In D2R, a partied player who dies and respawns **in Town** still receives **Act Boss quest credit** (`Andariel`, `Duriel`, `Mephisto`, `Diablo`, `Baal`) when their party finishes the boss — so a single death during a boss fight does **not** force the party to re-walk the entire Act.
  - *Exception to keep in mind:* **Rite of Passage (Ancients)** requires players to be present and alive on Arreat Summit when the Ancients fall to receive quest credit.

---

## 5. Synergy with Dynamic Co-Op Encounters

Combined with [DYNAMIC_COOP_ENCOUNTERS_PLAN.md](file:///home/grant/games/d2r/docs/coop/DYNAMIC_COOP_ENCOUNTERS_PLAN.md), Expedition Mode turns Castalia co-op into a true party dungeon crawl:
- Every Act Boss is the climax of a real journey rather than a 45-second waypoint teleport farm.
- `coop_bounty` (`+MF` / `+GF`) and `Picks + NoDrop` Champion/Unique scaling reward parties for surviving the full trek together.
- Resource management (Mana, Stamina, Potions, Durability, Totems, Warcries, Auras) creates natural group pacing and memorable co-op call-outs.

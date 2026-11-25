# Castalia — Host-Driven Co-Op Campaigns & Drop-In Starter Kits

> **Core Concept:** Replace the infinite ARPG endgame treadmill with **D&D / West Marches–style co-op campaigns**. Hosts create bounded campaigns with a set schedule and advertise upcoming sessions. Returning players bring their existing characters, while new or drop-in players generate a **level- and Act-matched character** via Castalia's Starter-Kit abstraction—allowing anyone to fill an open seat at any point in a campaign without derailing the schedule.
>
> **For Hosts:** See the ready-to-use **[`HOST_TOOLKIT.md`](file:///home/grant/games/d2r/docs/systems/HOST_TOOLKIT.md)** for copy-paste Discord templates, session checklists, and table etiquette.

---

## 1. Why This Model Fits Castalia

1. **Solves Scheduling Attrition (The #1 Co-Op Campaign Killer):**
   * Traditional co-op playthroughs die when 1–2 players miss Week 4. By letting drop-in players spawn cleanly at the Host's exact **Level + Act/Difficulty** with a balanced Gem/Rune/Gold starter pouch, a Host can always run a full 4–6 player table every week.
2. **Turns "No Endgame Treadmill" Into a Feature:**
   * Every campaign has a clear beginning (Act 1 Normal—or a themed Nightmare/Hell One-Shot), a 6–10 session arc, and a definitive victory when Hell Baal falls, culminating in a **Hall of Heroes** chronicle.
3. **Showcases Castalia's Crafting & Co-Op Roles Immediately:**
   * A drop-in player arriving at Nightmare Act 3 (`lvl 48`) receives a tier-matched **Starter Kit** (Horadric Cube, ID Tome, Flawless/Normal Gems & Skulls, Runes, and level-bracket Gold). They spend 5 minutes in town buying Magic bases from the Act vendor and crafting their opening kit via Castalia's **7 Horadric Cube Recipes**—experiencing Castalia's economy and crafting loop in their very first 10 minutes.
4. **Zero-Friction Onboarding for Burned-Out Solo Players:**
   * New players don't have to commit to an 8-week grind from Level 1 to test Castalia. Joining a single scheduled session (or a 1-night Hell Act 1 One-Shot) lets them feel `Conduction`, `Second Wind`, `Meditation`, and escalating co-op bosses in live voice chat right away.

---

## 2. How a Host Runs a Campaign

### Step 1 — Create & Advertise the Campaign
A Host posts a new campaign in Discord `#campaign-board` (and later, via the Castalia Launcher / Campaign API):
* **Campaign Name & Schedule:** e.g., *"Thursday Night Pilgrimage — Thursdays 8:00–10:00 PM EST"*
* **Ruleset Preset:**
  * *Standard Pilgrimage* (Normal → Hell, default Castalia rules)
  * *Pure Expedition* ([`EXPEDITION_MODE.md`](file:///home/grant/games/d2r/docs/systems/EXPEDITION_MODE.md) — zero field Waypoints)
  * *Hardcore / Three-Lives* (strict survival house rules)
  * *One-Shot* (single-evening Act push starting at NM or Hell)
* **Current Session Snapshot:**
  * **Castalia Version:** e.g., `v0.4.2`
  * **Target Level & Waypoint:** e.g., `Level 48` · `Nightmare Act 3 (a3nm)`
  * **Open Seats & Needed Roles:** e.g., `2/5 seats open — looking for Frontline CC or Mana/HP Sustain`

### Step 2 — Join as a Returning Player *or* a Drop-In
Before each session, players RSVP for an open seat in one of two ways:

| Player Type | What They Bring | How It Works |
| :--- | :--- | :--- |
| **Returning Regular** | Their existing campaign `.d2s` character | Keeps their earned items, crafted jewels, and story continuity from prior sessions. |
| **Drop-In / New Player** *(or Role-Swapper)* | Freshly generated `.d2s` matched to the Host's current session | Clicks the Host's **Session Join Link** (pre-filled Compendium `.d2s` URL, e.g., `?level=48&wp=a3nm`), picks a class and builds their skill tree in the Compendium, downloads the `.d2s` into `Saved Games/.../mods/castalia/`, crafts their opening gear from the Starter Kit in town, and joins the Host's D2RLoader TCP/IP game. |

*(Players who drop in for Session 4 can keep that character and become regulars for Sessions 5–9!)*

### Step 3 — Session Completion & Hall of Heroes
* After each session, the Host updates the campaign's current **Level & Waypoint** for next week's RSVP post.
* When Hell Baal falls, the Host posts the party's **Hall of Heroes** entry (final roster, screenshots, build links, standout crafted items, death tally) and retires the campaign.

---

## 3. Abstracting the Starter Kit System

Castalia already has the foundational engine for this in [`tools/mod_builder/char_manager.py`](file:///home/grant/games/d2r/tools/mod_builder/char_manager.py) (`bin/d2r-char`) and the browser-side `.d2s` generator in [`tools/build_site.py`](file:///home/grant/games/d2r/tools/build_site.py) (`docs/site/index.html`, which already supports URL query parameters `?name=&class=&level=&wp=`).

To make drop-in characters feel **fair alongside returning regulars** (neither helplessly undergeared nor stronger than earned characters):

### Starter-Kit Calibration Rules
1. **Level-Bracketed Crafting Pouch (Already Built):**
   * Scales automatically across the 5 Gem/Skull tiers (`Chipped` → `Flawed` → `Normal` → `Flawless` → `Perfect`) + tier-appropriate Runes + level-bracket Gold (`defaultGoldForLevel`) + Horadric Cube + ID Tome.
   * Deliberately provides **raw crafting materials + Gold**, *not* pre-baked BiS Uniques—so drop-ins craft a solid, playable starter set in town in 5 minutes while still feeling excited to find upgrades during the session.
2. **Host-Shareable Deep Link (Zero Manual Config):**
   * The Host shares a single Compendium URL encoding the campaign's current state:
     ```text
     https://grant0711.github.io/d2r-castalia/?level=48&wp=a3nm&class=pal
     ```
   * Opening that link automatically sets Level, Act/Difficulty (including accurate quest skill points and `clvl - reqlevel + 1` skill caps), and starter-kit tier—all the drop-in player does is pick their class, allocate skills, and click **Download `.d2s`**.
3. **Future Starter-Kit Presets (Optional):**
   * **Standard Drop-In Kit (Default):** Balanced crafting pouch + Gold to match a typical mid-campaign character's power floor.
   * **Austere / Naked Kit:** For Ironman or hardcore purist hosts who want drop-ins to scavenge from scratch with minimal supplies.
   * **Catch-Up Kit:** For a returning regular who missed a week (re-levels their existing `.d2s` to the party's current level/WP without touching their items via `bin/d2r-char set`).

---

## 4. Phased Technical Rollout

| Phase | Infrastructure | Cost | What It Unlocks |
| :--- | :--- | :---: | :--- |
| **Phase 1 — Discord + Compendium Deep Links** *(Ready Almost Immediately)* | Discord `#campaign-board` + `#hall-of-heroes`, Compendium `.d2s` URL links, `update-castalia.ps1`, `CSvBits` save isolation | **$0/mo** | Hosts self-organize weekly schedules; drop-ins generate exact session-matched characters in 30 seconds; everyone plays via D2RLoader TCP/IP. |
| **Phase 2 — Castalia Desktop Launcher (Tauri)** | Lightweight Windows/Linux launcher wrapping `latest.json` + `D2RLoader.exe` | **$0/mo** | 1-click mod install/update, file integrity verification before co-op, built-in "Generate Drop-In Character" button straight into the save folder. |
| **Phase 3 — Campaign Coordinator API & Save Vault** | Tiny REST API + DB + `.d2s` blob storage | **~$5–15/mo** | In-launcher Campaign Browser (browse open schedules/seats, RSVP in-app), optional cloud `.d2s` vault for party-locked characters, automatic Hall of Heroes archiving on the Compendium. |

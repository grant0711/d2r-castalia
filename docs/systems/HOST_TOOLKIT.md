# Castalia — Campaign Host Toolkit & Field Guide

> **Audience:** Players who want to organize and host their own **Castalia** co-op campaign (or 1-night One-Shot) with friends or community members on D2RLoader.

---

## 1. What Is a Castalia Host?

You are **not** a D&D Dungeon Master who has to write storylines or manage spreadsheets—you are an **Expedition Leader**. Your job is simple and high-impact:

1. **Set a schedule and ruleset** (e.g., *Thursdays 8–10 PM EST, 4–5 players, Standard Pilgrimage*).
2. **Host the D2RLoader TCP/IP lobby** and keep the party on the same Castalia version.
3. **Publish each week's Campaign Snapshot** (current Level + Act/Waypoint) so returning regulars and drop-in guests can jump straight into the session.
4. **Protect the vibe of the table**—keeping the party moving together, welcoming drop-ins, and celebrating the journey through Hell Baal.

---

## 2. One-Time Host Setup (5 Minutes)

1. **Install Castalia & D2RLoader:**
   * Extract the latest `castalia-vX.Y.Z.zip` into your `Diablo II Resurrected/` folder so `mods/castalia/castalia.mpq/modinfo.json` exists.
   * Install **[D2RLoader](https://d2rloader.net)** and verify you can launch Castalia via `D2RLoader.exe` with the in-game multiplayer browser enabled.
2. **Confirm Connectivity:**
   * Host a quick test game via D2RLoader's multiplayer menu (public/unlisted Game ID or direct IP/VPN if playing with a private group) and verify a friend can join.
3. **Bookmark the Compendium:**
   * **[https://grant0711.github.io/d2r-castalia/](https://grant0711.github.io/d2r-castalia/)** — your table's live skill calculator, Gem/Rune/Cube reference, and drop-in `.d2s` Character Generator.

---

## 3. Starting a Campaign (Copy-Paste Discord Template)

Post this in `#campaign-board` to recruit your party:

```markdown
### [Campaign Name — e.g. "Thursday Night Pilgrimage"]
- **Host:** @YourName
- **Schedule:** Thursdays, 8:00–10:00 PM EST (2 hours)
- **Ruleset:** Standard Pilgrimage (or: Pure Expedition / Three-Lives / Hell Act 1 One-Shot)
- **Castalia Version:** v0.4.x
- **Current Progress:** Session 1 — Level 1, Normal Act 1 (`a1n`)
- **Seats:** 1/5 filled (4 open — regulars & drop-ins welcome!)
- **Needed Roles:** Any! (Especially welcome: Paladin Cleric, Barbarian Warcry Medic, Sorceress Conduction)
- **Drop-In Character Link:** https://grant0711.github.io/d2r-castalia/?level=1&wp=a1n
```

### Choosing a Ruleset Preset
* **Standard Pilgrimage (Best for First-Time Hosts):** Act 1 Normal → Act 5 Hell over ~6–10 weekly sessions. Characters are **party-locked** (no off-night solo farming).
* **Pure Expedition ([`EXPEDITION_MODE.md`](file:///home/grant/games/d2r/docs/systems/EXPEDITION_MODE.md)):** Zero field Waypoints + no Town Portals. Every departure from town is a supply-managed dungeon crawl.
* **Hardcore / Three-Lives:** True Hardcore, or softcore with a house rule (e.g., 3 lives per difficulty, or dead players wait until the current zone/boss is cleared).
* **Single-Night One-Shot (Best for Onboarding New Players):** Pick a mid/late-game slice (e.g., *Level 55, Nightmare Act 4–5* or *Level 65, Hell Act 1–2*). Everyone generates a fresh character using the Compendium Starter Kit link, spends 10 minutes crafting in town, and pushes straight for the Act Boss.

---

## 4. Running a Weekly Session (Host Checklist)

### 24 Hours Before Game Night
* Check `#releases` for any new Castalia patch (`🟢 Save-Compatible` updates are safe mid-campaign).
* Post a quick RSVP ping in your campaign thread with:
  * **Castalia Version** (`v0.4.x`)
  * **Current Level & Waypoint** (e.g., `Level 48 · Nightmare Act 3`)
  * **Open Seats** + **Drop-In Link**:
    ```text
    https://grant0711.github.io/d2r-castalia/?level=48&wp=a3nm
    ```

### 15 Minutes Before Start (Town Prep & Drop-In Onboarding)
* Open your D2RLoader lobby 10–15 minutes early and drop the Game ID in your campaign thread.
* **2-Second Version Check:** Have everyone confirm they see the same `Castalia vX.Y.Z` version before joining.
* **Drop-In Starter Kit Ritual (5–10 min):**
  * Drop-in players place their downloaded `.d2s` into `Saved Games/Diablo II Resurrected/mods/castalia/`.
  * Give them 5–10 minutes in town to buy Magic bases from the Act vendor and craft their opening gear from their Starter Kit (Cube + Gems/Skulls + Runes + Gold).
  * Encourage returning regulars to toss spare low-tier Gems/Runes or Magic bases to the drop-in—it builds instant party camaraderie.

### During the Session (Table Habits That Make Castalia Shine)
* **Give New Players the 30-Second Reset:** If someone is coming from vanilla D2R or D2R Reimagined, tell them up front: *"No Town Portals, no Runewords, no free immunity pierce. Every Magic/Rare drop and Gem/Rune matters, and we live or die as a squad."*
* **Stay Together:** With no Town Portals, splitting up breaks the rescue loop and wastes party auras/warcries (`Meditation`, `Second Wind`, `Battle Command`, `Conduction`). Move as a unit.
* **Call Out Landmarks & Traits:** Call out **Wells & Recovery Shrines** (your field checkpoints) and **monster vulnerabilities/traits** printed under enemy health bars.
* **Pool Loot Like a D&D Party:** Share Lockboxes, Keys, Gems, Runes, and class-specific Magic bases freely. Castalia has no endgame trade market—stronger teammates mean a smoother boss kill tonight.
* **Boss Death Rule to Remember:** In D2R, a partied player who dies and respawns in town still gets **Act Boss quest credit** when the party finishes the boss—*except* **The Ancients (Act 5)**, where everyone must be present and alive on Arreat Summit.

### End of Session (5 Minutes)
* Push to a clean stopping point—ideally the next **Town Waypoint** (your party's "Long Rest").
* Snap a quick party screenshot in town.
* Post a 3-line recap in your campaign thread with the **new Level & Waypoint** for next week's RSVP.

---

## 5. Handling Common Host Situations

| Situation | Recommended Host Move |
| :--- | :--- |
| **A regular misses a week** | Don't cancel! Fill the seat with a drop-in. When the regular returns next week, they can either play 1–2 levels behind (co-op XP catches them up quickly) or bump their level/WP cleanly via `d2r-char set` without touching their gear. |
| **A player wants to swap classes mid-campaign** | Welcome it! Let them retire their old character and roll a fresh Starter-Kit character at the party's current Level & Waypoint. |
| **Someone has a version mismatch** | Have them run `update-castalia.ps1` (or re-extract the pinned GitHub Release zip after deleting old `mods/castalia/castalia.mpq/`) and re-verify the version tag. |
| **Party hits a tough Hell immunity wall** | Pause in town, inspect the Compendium together, craft targeted elemental/physical swaps using the 7 Cube recipes, or adjust your 10-slot mercenaries' kits and auras. |

| **Random internet scanners hit your public `playit.gg` port** | Run `bin/d2r-tcp-guard --listen 127.0.0.1:4001 --target 127.0.0.1:4000` (or `castalia-tcp-guard.service`) and point your Playit tunnel's local port to `4001`. It drops TLS (`0x16 0x03`), HTTP, SSH, and burst probes before they reach D2RLoader. Use **Settings → Test Connection** in the Castalia Launcher to verify reachability before going live. |

---

## 6. Campaign Finale — Hall of Heroes Template

When Hell Baal falls, your campaign is complete! Post your chronicle in `#hall-of-heroes`:

```markdown
### 🏆 [Campaign Name] — Hell Baal Cleared!
- **Host:** @YourName | **Sessions:** 8 | **Ruleset:** Standard Pilgrimage | **Version:** v0.4.2
- **Final Party:**
  - @Player1 — Level 76 Paladin (Vengeance / Salvation Cleric)
  - @Player2 — Level 76 Barbarian (Shield Slam / Warcry Medic)
  - @Player3 — Level 75 Sorceress (Lightning / Conduction)
  - @Player4 — Level 75 Assassin (Combo Orb / Sentry)
- **Total Party Deaths:** 14
- **MVP Crafted Item / Best Moment:** [1–2 sentences + screenshot!]
```

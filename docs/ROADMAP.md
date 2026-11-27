# Castalia — Project Status & Next-Phase Roadmap

Quick orientation for picking up Castalia development cleanly on `master`.

---

## 1. Shipped & Playtested (On `master`)

### Core Systems & Economy
- **Zero-White / High Signal-to-Noise Drops** + 7 Gem/Skull families + 33 Semantic Runes + **7 Horadric Cube Recipes** (~394k rows; Runewords permanently disabled; zero player elemental/sunder pierce).
- **Global Martial Stamina & Stamina Fatigue:** Physical melee/martial skills cost 0 Mana and scale with Stamina (`50% → 100%` power; `0` stun below `33%` Stamina). Hidden combat-event `Stamina Fatigue` (`automagic` Groups `324`/`325`) applies D2R frame-normalized FRW/IAS/FCR/FHR/FBR slowdowns when fighting exhausted (Barbarian `Bloodlust` exempt + 1-frame wipe).
- **Global Stun Fatigue (`domeleeattack` / `attackedinmelee`):** Consecutive uninterrupted melee attacks taper stun duration (`100% → 75% → 50% → 25% → 0%` on Hit 5+) on `Smite`, `Charge`, and `Shield Slam`; resets immediately when struck in melee or after 5s.
- **5-Archetype Shield Damage & Durability Progression:** Brittle Bone/Skull (`3–7 / 15–25 / 36–60`, dur `24/36/48`) < Light < Medium < Heavy (`10–18 / 38–58 / 78–122`) < Spiked (`11–20 / 42–64 / 86–134`, `+10%` above Heavy).
- **Strategy Guide & Embedded `.d2s` Character Builder (`docs/site/index.html`):** Auto-generated from compiled mod tables, with Level + Difficulty/Act (including quest skill points) + D2R `clvl - reqlevel + 1` cap + direct `.d2s` download inside every class calculator tab.
- **Automated Verification (`python3 -m unittest -v`):** 37 unit tests covering engine contracts, 248-char calc length limits, zero elemental pierce, skill tree DAGs, Stamina/Stun/Conduction behavioral simulations, affixes, drops, and `.d2s` save generation.

### Class Overhauls
| Class | Status | Reference | Notes |
| :--- | :--- | :--- | :--- |
| **Paladin** | **30 / 30 Done & Playtested** | [`paladin.md`](file:///home/grant/games/d2r/docs/classes/paladin.md) | Aura Mana Devotion (17 auras scale power & radius to 0 at 0% Mana), 0-Mana recovery stances, Frontal Cleave `Vengeance`, Bouncing Chain `Blessed Hammer`, S-Curve Party `Conviction` (`+50%` self / `+33%` party), no-KB `Smite` + `Stun Fatigue`, rebalanced `Fist of the Heavens`. |
| **Barbarian** | **30 / 30 Done & Playtested** | [`barbarian.md`](file:///home/grant/games/d2r/docs/classes/barbarian.md) | Stamina Pendulum (Well-Rested / Stamina Spenders / Exhaustion), `Bloodlust` Fatigue immunity, 2.0s shared Warcry cadence (`Shout`/`BO`/`Enduring Cry` `25s → 120s`), no-delay `Shield Slam` + `Stun Fatigue`, `Frenzy` `+50%` velocity cap. |
| **Assassin** | **30 / 30 Done & Playtested** | [`assassin.md`](file:///home/grant/games/d2r/docs/classes/assassin.md) | All-weapon Martial Arts, 15m Charge-Up orbs (hold to imbue / release AoE at feet with level-scaled radius / spend into empowered Sentries), `Omnislash`. |
| **Sorceress** | **24 / 30 Done** | [`sorceress.md`](file:///home/grant/games/d2r/docs/classes/sorceress.md) | Fire (`10/10`), Lightning (`10/10`), 3 Elemental Stances, 3 Cross-Tree Passives (`Expansion`/`Stasis`/`Arc`), and 3-Passive `Conduction` (`target0`/`target1`/`goldlost`) complete. **6 Cold active spells remain.** |
| **Amazon** | **Planned** | [`amazon.md`](file:///home/grant/games/d2r/docs/classes/amazon.md) | Blueprint drafted (Cadence, Riposte/Countershot, Bow vs. Crossbow split). |
| **Druid** | **Upcoming** | — | Co-op Life/Mana Totem support design drafted in [`COOP_ENCOUNTERS.md`](file:///home/grant/games/d2r/docs/systems/COOP_ENCOUNTERS.md). |
| **Necromancer** | **Upcoming** | — | Leaner, tougher co-op summon army guardrail noted in [`COOP_ENCOUNTERS.md`](file:///home/grant/games/d2r/docs/systems/COOP_ENCOUNTERS.md). |

---

## 2. Next-Phase Queue (In Recommended Order)

1. **Finish Sorceress Cold Tree (`6 stubs`):**
   - Start at [`docs/classes/sorceress.md`](file:///home/grant/games/d2r/docs/classes/sorceress.md) and `./bin/d2r-sorc map cold`: `frost_dart`, `hoarfrost_burst`, `permafrost`, `whiteout`, `icicle_spear`, `frozen_orb`.
   - Follow [`docs/DIAGNOSTIC_PROTOCOL.md`](file:///home/grant/games/d2r/docs/DIAGNOSTIC_PROTOCOL.md) and balance Cold against Fire/Lightning with `bin/d2r-balance`.
2. **Amazon Overhaul:**
   - Flesh out and implement [`docs/classes/amazon.md`](file:///home/grant/games/d2r/docs/classes/amazon.md) (Cadence, Riposte/Countershot, Bow vs. Crossbow split, Martial Stamina integration).
3. **Druid & Necromancer Overhauls:**
   - Implement Druid (including stationary targetable Life/Mana Totems with `item_healafterkill`/`item_manaafterkill`) and Necromancer.
4. **Co-Op Campaign Systems & Community Launch Prep:**
   - **Campaign Launcher, CLI, Cloudflare Hub & Auto-Host Plugin (LIVE — `v0.4.3`):** [`docs/systems/LAUNCHER_SPEC.md`](file:///home/grant/games/d2r/docs/systems/LAUNCHER_SPEC.md), [`CAMPAIGN_PLAY.md`](file:///home/grant/games/d2r/docs/systems/CAMPAIGN_PLAY.md), [`HOST_TOOLKIT.md`](file:///home/grant/games/d2r/docs/systems/HOST_TOOLKIT.md) — shared `castalia_hub` engine, `bin/d2r-campaign` CLI, `bin/d2r-launcher` (detached `origin/release` worktree on Linux), Inno Setup **`CastaliaLauncher-Setup.exe`** + portable PSF-signed embeddable Python zip on Windows, `castalia-autohost.dll` in-game Host/Join Guide, `playit.gg` auto port-sync & stale-tunnel refresh, `bin/d2r-tcp-guard` scanner filter, native OS folder picker (`Browse...`), 1-click **Import Existing Character** + Solo **Respec**, **Test Host Connection** reachability probe, live Cloudflare Worker + D1 (`castalia-campaign-hub.d2rcastalia.workers.dev`) with Discord `#lfg-sessions` live/schedule bump + Google Calendar links, and Nexus Mods Alpha listing + YouTube gameplay video live. **Next:**
     - **Automated Nexus Mods Release Upload (`release-publish.yml`):** Configure `NEXUSMODS_API_KEY` (Personal API Key) + `NEXUSMODS_MOD_ID` / `NEXUSMODS_FILE_ID` repo variables and wire/test automated pure-data zip uploads on `release` merges.
     - **Trade-Window Stability Check:** 1-variable test of Host↔Joiner Trade window with `write_crash_dumps = true` in `d2rloader.toml`.
   - **Gated Release Pipeline (LIVE — `v0.4.3`):** [`docs/systems/RELEASE_MANAGEMENT.md`](file:///home/grant/games/d2r/docs/systems/RELEASE_MANAGEMENT.md) — Save-Aware SemVer, `bin/d2r-release` (bundling `castalia-autohost.dll`), `release-pr-gate.yml`, `release-publish.yml`, and `pages.yml` deploying from `release`. **Next:** configure `DISCORD_WEBHOOK_URL` secret for automatic release announcements.
   - Implement [`docs/systems/COOP_ENCOUNTERS.md`](file:///home/grant/games/d2r/docs/systems/COOP_ENCOUNTERS.md) (`maxhp`-gated monster escalation leveraging D2RLoader's 32,768-row ceilings, `coop_bounty` MF/GF, `Picks + NoDrop` co-op scaling, tempered Paladin `Vigor` Stamina Recovery, and **`CSvBits` save isolation**).
   - Optionally build [`docs/systems/EXPEDITION_MODE.md`](file:///home/grant/games/d2r/docs/systems/EXPEDITION_MODE.md) (zero field WPs, Superchest windfalls, expedition-leg resistance cohesion audit).
5. **Atmospheric Weather & D2RLoader Plugin Exploration (Candidate Fork):**
   - Evaluate forking and adapting **[`latedozer/Horror-mod`](https://github.com/latedozer/Horror-mod)** (*"A Darker Atmosphere"*, **MIT-licensed**, built for modern D2R + D2RLoader PluginSDK ABI 4) for Castalia:
     - **Data side (`d2rmm-mod/HorrorNight` → `tools/mod_builder/`):** Darker lighting/fog, reduced monster self-lighting & light radius (pairs naturally with Castalia's enclosed Greathelm light-radius tradeoff), plus storm missile/effect rows.
     - **Plugin side (`plugin/` → `mods/castalia/d2rloader/plugins/`):** Runtime D2RLoader C++ DLL driving Act-specific weather and environmental hazards (Act 1 rain/lightning, Act 2 sandstorms/dust devils, Act 3 monsoon, Act 4 ash storms/meteors, Act 5 blizzards/ice shards, ambient whispers, optional phantoms) with `.toml` tuning and an in-game toggle hotkey.

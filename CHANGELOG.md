# Castalia Changelog

All notable releases of **Castalia** (`d2r-castalia`) are documented here.
Versioning follows **Save-Aware SemVer** (`vMAJOR.MINOR.PATCH` — see [docs/systems/RELEASE_MANAGEMENT.md](docs/systems/RELEASE_MANAGEMENT.md)):
- `🟢 Save-Compatible` (`PATCH`): Drop-in safe mid-campaign.
- `🟡 Save-Compatible (Respec Recommended)` (`MINOR`): New class/system additions; characters load cleanly.
- `🔴 New Campaign Required` (`MAJOR`): Save-schema breaking change (e.g., `CSvBits` isolation).

---

## [v0.4.3] - 2026-11-27

**Save Compatibility:** 🟢 Save-Compatible (drop-in safe mid-campaign)

Playtest #2 co-op & economy tuning + Windows Installer: increased gold pile multipliers (+15%: 2.75/4.6/8.0), added Act-scaled monster potion drops (Hybrid Option C: 10% Act Junk trickle + 1 guaranteed on Champs/Uniques + 2 on SuperUniques), tuned NoDrop on Champs/Uniques/SuperUniques/Act Bosses/Super Chests to preserve exact P1 solo means while scaling drops cleanly with party size (P2-P5), tier-scaled Crafted levelreq offsets (-8/-10/-12/-15/-19), smoothed Barrage (70% base / +40% exhausted) and Increased Speed (+19% at slvl 1 -> +43% at slvl 20), added CastaliaLauncher-Setup.exe Windows installer + returning-character auto-import + Discord next-session bump.

## [v0.4.2] - 2026-11-26

**Save Compatibility:** 🟢 Save-Compatible (drop-in safe mid-campaign)

Playtest #1 fixes & Drop-In co-op polish: fixed early Act 1 Blood Moor/Cold Plains white & cracked drops (itemratio.txt), calibrated Act 1 Drop-In gold to 10,000g at Lv 15, gated Horadric Cube on Host possession, added exact Host quest & waypoint cloning onto new Drop-In saves, added auto-bump of campaign version on Host launch for same-minor patch releases, auto-restore of solo saves on campaign exit, and automatic stale playit tunnel refresh on Go Live.

## [v0.4.1] - 2026-11-26

**Save Compatibility:** 🟢 Save-Compatible (drop-in safe mid-campaign)

Launcher UX & scheduling polish: added Host Edit Schedule modal with explicit GMT+/- timezone selector, pre-filled default session timestamps, live Discord embed updates with localized countdowns, and 1-click Add to Google Calendar links.

## [v0.4.0] - 2026-11-26

**Save Compatibility:** 🟡 Save-Compatible (Respec Recommended)

First public Alpha release of Castalia! Includes the Castalia Campaign Launcher (Windows x64 & Linux), live Cloudflare Campaign Hub, castalia-autohost.dll D2RLoader plugin, 4 reworked classes (Paladin, Barbarian, Assassin, Sorceress), zero-Runeword Gem+Rune Cube crafting, and the updated Compendium.

## [v0.3.0] - 2026-11-25

**Save Compatibility:** 🟢 Initial Versioned Baseline

### Included in Baseline
- **Core Economy & Crafting:** Zero-White equipment drops, 7 Gem/Skull families, 33 Semantic Runes, 7 Horadric Cube recipes (~394k rows; Runewords permanently disabled; zero player elemental/sunder pierce).
- **Global Combat Systems:** Martial Stamina & Stamina Fatigue, Global Stun Fatigue (`Smite`, `Charge`, `Shield Slam`), 5-Archetype Shield Damage & Durability progression.
- **Class Overhauls:** Paladin (30/30), Barbarian (30/30), Assassin (30/30), Sorceress (24/30 — Fire, Lightning, Stances, Cross-Tree Passives & 3-Passive Conduction).
- **Tooling & Compendium:** Unified declarative `spec_engine` + `bin/d2r-class`, `.d2s` Character Builder embedded in `docs/site/index.html`, and gated `release` branch pipeline.

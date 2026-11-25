# Castalia Changelog

All notable releases of **Castalia** (`d2r-castalia`) are documented here.
Versioning follows **Save-Aware SemVer** (`vMAJOR.MINOR.PATCH` — see [docs/systems/RELEASE_MANAGEMENT.md](docs/systems/RELEASE_MANAGEMENT.md)):
- `🟢 Save-Compatible` (`PATCH`): Drop-in safe mid-campaign.
- `🟡 Save-Compatible (Respec Recommended)` (`MINOR`): New class/system additions; characters load cleanly.
- `🔴 New Campaign Required` (`MAJOR`): Save-schema breaking change (e.g., `CSvBits` isolation).

---

## [v0.3.0] - 2026-11-25

**Save Compatibility:** 🟢 Initial Versioned Baseline

### Included in Baseline
- **Core Economy & Crafting:** Zero-White equipment drops, 7 Gem/Skull families, 33 Semantic Runes, 7 Horadric Cube recipes (~394k rows; Runewords permanently disabled; zero player elemental/sunder pierce).
- **Global Combat Systems:** Martial Stamina & Stamina Fatigue, Global Stun Fatigue (`Smite`, `Charge`, `Shield Slam`), 5-Archetype Shield Damage & Durability progression.
- **Class Overhauls:** Paladin (30/30), Barbarian (30/30), Assassin (30/30), Sorceress (24/30 — Fire, Lightning, Stances, Cross-Tree Passives & 3-Passive Conduction).
- **Tooling & Compendium:** Unified declarative `spec_engine` + `bin/d2r-class`, `.d2s` Character Builder embedded in `docs/site/index.html`, and gated `release` branch pipeline.

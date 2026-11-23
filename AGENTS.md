# Castalia (D2R Mod) — Agent Fast-Path CLI Rules

## 1. Instant Character Creation, Modification & Respec (`bin/d2r-char`)
When the user asks to create, modify, reset, or list a character (e.g., *"Create a lvl 55 paladin at act3 nm"*), **DO NOT** inspect `char_manager.py`, grep the codebase, or reason from first principles. Run `/home/grant/games/d2r/bin/d2r-char` immediately in a single `run_command` call:

```bash
# Create a new character (automatically picks the matching Gem/Skull/Rune tier template, stash gold, quest bonuses & difficulty unlock):
/home/grant/games/d2r/bin/d2r-char create <NAME> --class <ama|sor|nec|pal|bar|dru|ass> --level <1..99> --wp <TARGET>

# Example: "Create a lvl 55 paladin at act3 nm" ->
/home/grant/games/d2r/bin/d2r-char create PAL --class pal --level 55 --wp a3nm

# Modify an existing character in place (keeping all their items intact):
/home/grant/games/d2r/bin/d2r-char set <NAME> [--class <cls>] [--level <1..99>] [--wp <TARGET>] [--stash-gold <N>]

# Refund all skill points (or --stats to also refund stat points) on an existing character:
/home/grant/games/d2r/bin/d2r-char reset <NAME> [--stats] [--level <N>] [--wp <TARGET>]

# List all saved characters or inspect the 5 Gem/Skull tier templates:
/home/grant/games/d2r/bin/d2r-char list
/home/grant/games/d2r/bin/d2r-char templates
```

### Waypoint (`--wp`) Target Codes
- `start` / `a1n`: Start at the beginning of Normal Act 1 (Rogue Encampment town WP unlocked)
- `a1n` .. `a5n`: Start at the **beginning** of Normal Act 1..5 (all preceding Acts completed, spawning in that Act's town with its town WP unlocked)
- `a1nm` .. `a5nm`: Start at the **beginning** of Nightmare Act 1..5 (all of Normal + preceding Nightmare Acts completed, spawning in that Act's town with its town WP unlocked)
- `a1h` .. `a5h`: Start at the **beginning** of Hell Act 1..5 (all of Normal & Nightmare + preceding Hell Acts completed, spawning in that Act's town with its town WP unlocked)
- `<act><diff>-done` (e.g. `a3nm-done`, `a5n-done`): Also complete all quests & waypoints *inside* that Act
- `all`: All 39 Waypoints and quests across Normal, Nightmare, and Hell completed

### Default Character Naming Convention
If the user does not specify a character name (e.g., *"Create a lvl 55 paladin at act3 nm"*), default `<NAME>` to the uppercase class short name: `PAL`, `BAR`, `ASS`, `SORC`, `AMA`, `NEC`, or `DRU`.

---

## 2. Sorceress Skill Iteration (`bin/d2r-sorc`) & Mod Build (`bin/d2r-build-mod.py`)
- **Session Handoff & Active Queue**: Read [`/home/grant/games/d2r/docs/sorc/HANDOFF.md`](file:///home/grant/games/d2r/docs/sorc/HANDOFF.md) and [`/home/grant/games/d2r/docs/sorc/STATUS.md`](file:///home/grant/games/d2r/docs/sorc/STATUS.md) first when resuming Sorceress skill development.
- Query Sorceress skill slots, engine functions, or patterns directly from the CLI without grepping:
  - `/home/grant/games/d2r/bin/d2r-sorc map`
  - `/home/grant/games/d2r/bin/d2r-sorc funcs [query]`
  - `/home/grant/games/d2r/bin/d2r-sorc patterns [slug]`
  - `/home/grant/games/d2r/bin/d2r-sorc show <slug>`
- Build & run invariant tests:
  - `/home/grant/games/d2r/bin/d2r-sorc build`
  - `/home/grant/games/d2r/bin/d2r-sorc test [slug]`
  - `python3 /home/grant/games/d2r/bin/d2r-build-mod.py [step...]`

---

## 3. Hard Castalia Design Boundaries (Never Violate)
- **Runewords are BANNED / DISABLED:** All Runewords in `runes.txt` are explicitly disabled (`complete = ""` in `tools/mod_builder/unique_sets.py`). Runes exist exclusively for direct socketing and Gem+Rune Horadric Cube crafting. **Never** suggest, analyze, or design around Runewords (`Enigma`, `Infinity`, `Dream`, `Dragon`, `Eternity`, `Spirit`, etc.) as playable items in Castalia.
- **Zero Player Elemental / Sunder Pierce:** Player skills and summons must never grant `passive_*_pierce` or `item_pierce_*_immunity`.
- **Controlled Vanilla Sync (`bin/d2r-vanilla-sync`):** After any Blizzard D2R patch, never blindly overwrite `vanilla-reference/` with `d2r-extract-txt`. Always run `bin/d2r-vanilla-sync stage` → `audit` → selective `apply` (`schema-only` / `accept` / `keep`).

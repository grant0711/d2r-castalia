---
name: d2r-char
description: >-
  Create, modify, reset, or inspect Diablo II: Resurrected (Castalia mod) character saves (.d2s)
  using /home/grant/games/d2r/bin/d2r-char. Activate this skill whenever the user asks to create a
  character of any class/level/act/difficulty, respec skills or stats, change waypoints or gold,
  or manage starter templates in tools/char_templates/.
---

# Castalia Character Manager (`bin/d2r-char`)

Do not inspect `tools/mod_builder/char_manager.py` or manipulate `.d2s` bytes manually when the user asks to create, modify, or reset a character. Run `/home/grant/games/d2r/bin/d2r-char` directly in a single command.

## Quick Commands

```bash
# 1. Create a character from the level-matched Gem/Skull/Rune tier template:
/home/grant/games/d2r/bin/d2r-char create <NAME> --class <ama|sor|nec|pal|bar|dru|ass> --level <1..99> --wp <TARGET>

# Example ("Create a lvl 55 paladin at act3 nm"):
/home/grant/games/d2r/bin/d2r-char create PAL --class pal --level 55 --wp a3nm

# 2. Modify an existing character's level, waypoints, gold, or class in place (keeping all their items):
/home/grant/games/d2r/bin/d2r-char set <NAME> [--class <cls>] [--level <1..99>] [--wp <TARGET>] [--stash-gold <N>] [--keep-skills] [--keep-stats]

# 3. Refund all skill points (add --stats to also reset attributes to base):
/home/grant/games/d2r/bin/d2r-char reset <NAME> [--stats] [--level <N>] [--wp <TARGET>]

# 4. List all saved characters or inspect the 5 Gem/Skull tier templates:
/home/grant/games/d2r/bin/d2r-char list
/home/grant/games/d2r/bin/d2r-char templates

# 5. Snapshot an in-game character save into tools/char_templates/<tier>.d2s:
/home/grant/games/d2r/bin/d2r-char save-template <NAME> --as <template_name>
```

## Automatic Level-Tier Template & Stash Gold Selection

`d2r-char create` preserves the template's `JM` item section 100% bit-for-bit untouched and automatically selects the template and Personal Stash Gold based on `--level`:

| Level | Template in `tools/char_templates/` | Auto Stash Gold | Contents |
| :--- | :--- | :---: | :--- |
| **1–9** | `default.d2s` | `0g` | 4x Belt Minor Healing Potions (`hp1`), no Cube/Gems/Runes |
| **10–14** | `tier1_chipped.d2s` | `60,000g` | Horadric Cube, Tome of ID, Belt Potions, Chipped Gems/Skulls & Lvl 4–12 Runes |
| **15–29** | `tier2_flawed.d2s` | `60,000g` (15–19) / `240,000g` (20–29) | Horadric Cube, Tome of ID, Belt Potions, Flawed Gems/Skulls & Lvl 12–26 Runes |
| **30–44** | `tier3_normal.d2s` | `315,000g` (30–39) / `535,000g` (40–44) | Horadric Cube, Tome of ID, Belt Potions, Normal Gems/Skulls & Lvl 28–38 Runes |
| **45–59** | `tier4_flawless.d2s` | `535,000g` (45–49) / `825,000g` (50–59) | Horadric Cube, Tome of ID, Belt Potions, Flawless Gems/Skulls & Lvl 38–52 Runes |
| **60+** | `tier5_perfect.d2s` | `1,240,000g` (60–69) / `1,450,000g` (70+) | Horadric Cube, Tome of ID, Belt Potions, Perfect Gems/Skulls & Lvl 48–68 Runes |

## Waypoint (`--wp`) Target Codes

- `a1n` .. `a5n`: Start at the **beginning** of Normal Act 1..5 (all prior Acts completed, spawning in that Act's town with its town WP unlocked)
- `a1nm` .. `a5nm`: Start at the **beginning** of Nightmare Act 1..5 (all of Normal + prior NM Acts completed, spawning in that Act's town with its town WP unlocked)
- `a1h` .. `a5h`: Start at the **beginning** of Hell Act 1..5 (all of Normal & NM + prior Hell Acts completed, spawning in that Act's town with its town WP unlocked)
- `<act><diff>-done` (e.g. `a3nm-done`): Also complete all quests and waypoints *inside* that Act
- `all`: All 39 Waypoints and quests across Normal, Nightmare, and Hell completed

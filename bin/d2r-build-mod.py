#!/usr/bin/env python3
"""
d2r-build-mod.py
Master deterministic pure-function mod builder for Diablo II: Resurrected.
Reads pristine vanilla .txt/JSON files from /home/grant/games/d2r/vanilla-reference/
and writes transformed files to /home/grant/games/d2r/my-mod/ parameterized by mod_config.json.
"""
import argparse
import os
import sys

sys.path.insert(0, "/home/grant/games/d2r/tools")

from build_site import build_site
from mod_builder.affixes import build_affixes_all, print_affix_summary
from mod_builder.books_shrines import build_books, build_books_shrines, build_shrines
from mod_builder.common import load_config
from mod_builder.cubemain import build_cubemain
from mod_builder.gamble_npc import build_gamble, build_gamble_npc, build_npc
from mod_builder.gems_runes import build_gems_runes
from mod_builder.itemratio import build_itemratio
from mod_builder.itemtypes_automagic import build_itemtypes_automagic
from mod_builder.misc_items import build_misc_all
from mod_builder.monsters import build_monsters_all, print_monster_summary
from mod_builder.skills import build_skills_all
from mod_builder.treasureclass import build_treasureclass
from mod_builder.unique_sets import build_unique_sets_all, print_anonymized_summary
from mod_builder.verify import verify_all
from mod_builder.weapons_armor import build_weapons_armor_all

STEPS = {
    "itemratio": build_itemratio,
    "npc": build_npc,
    "gamble": build_gamble,
    "gamble_npc": build_gamble_npc,
    "books": build_books,
    "shrines": build_shrines,
    "books_shrines": build_books_shrines,
    "itemtypes": build_itemtypes_automagic,
    "weapons_armor": build_weapons_armor_all,
    "affixes": build_affixes_all,
    "unique_sets": build_unique_sets_all,
    "misc": build_misc_all,
    "gems": build_gems_runes,
    "treasureclass": build_treasureclass,
    "cubemain": build_cubemain,
    "monsters": build_monsters_all,
    "skills": build_skills_all,
}


def main():
    parser = argparse.ArgumentParser(description="Build D2R Custom Solo Overhaul Mod Tables")
    parser.add_argument(
        "targets",
        nargs="*",
        default=["all"],
        help="Target module(s) to build (e.g. itemratio) or 'all'",
    )
    args = parser.parse_args()
    cfg = load_config()

    targets = list(STEPS.keys()) if "all" in args.targets else args.targets
    extra_steps = {
        "unique_summary": print_anonymized_summary,
        "affix_summary": print_affix_summary,
        "monster_summary": print_monster_summary,
    }
    for t in targets:
        if t == "verify":
            continue
        if t in extra_steps:
            extra_steps[t](cfg)
            continue
        if t not in STEPS:
            print(f"ERROR: Unknown target '{t}'. Available: {', '.join(STEPS.keys())}", file=sys.stderr)
            sys.exit(1)
        out = STEPS[t](cfg)
        print(f"[d2r-build-mod] Built {t} -> {out}")

    checks = verify_all(cfg)
    print(f"[d2r-build-mod] Verified {len(checks)} invariant suites: {', '.join(checks)}")
    site_out = build_site()
    print(f"[d2r-build-mod] Rebuilt strategy guide site -> {site_out}")


if __name__ == "__main__":
    main()

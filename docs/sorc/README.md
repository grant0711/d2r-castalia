# Sorceress iteration workflow

Design source of truth: the Sorceress blueprint (`sorceress_blueprint_v2.md` in the conversation artifacts)
and `tools/mod_builder/sorc/registry.py` (1:1 map with a design paragraph per skill).
Current state of every skill: `docs/sorc/STATUS.md` (generated). Per-skill history: `docs/sorc/<slug>.md`.

## The 1:1 rule
All 30 vanilla Sorceress rows are kept (same `*Id`, same row name, `charclass="sor"`, same icon frame).
A new skill = one vanilla row re-purposed, so saves and items keep working. Items that grant
"+N <vanilla skill>" now boost whichever new skill replaced that row.
Skill tab: page 1 Fire, page 2 Lightning, page 3 Cold; rows are the unlock tiers 1/8/16/24/32/40.
Prerequisites are cleared and the background arrows are removed until a tree is complete.

## Layers (later wins)
1. `registry.py` - layout, names, req level, tooltip text (always applied).
2. `specs/<slug>.json` - the active variant's patches to skills/skilldesc/missiles/states/itemstatcost.
3. `specs/_shared.json` - helper rows shared by several skills (stance states, helper skills, stats).
`state.json` records the active variant and status of each skill.

## Controlled experiment loop (one variable at a time)
```
d2r-sorc show <slug>                        # design + active patch + built diff + notes (rebuilds context)
d2r-sorc variant <slug> v1 -m "what ONE thing this tests"
d2r-sorc set <slug> "skills.txt/Fire Bolt.mana=0" -v v1     # <table>/<key>.<col>=<value>
d2r-sorc use <slug> v1
d2r-sorc build                              # skills tables + verify (~10s)
d2r-sorc char                               # refund SORC skill points (game closed / at char select)
# launch game, test, report what happened
d2r-sorc log <slug> "observed: ..."         # keep the result
d2r-sorc status <slug> wip|tested|done
d2r-sorc commit -m "cinder_lance v1: ..."   # checkpoint
```
- Revert a skill instantly: `d2r-sorc use <slug> baseline` (or any earlier variant) then `build`.
- Throw away uncommitted edits to one skill: `d2r-sorc revert <slug>`.
- One-off override without touching files: `SORC_VARIANTS="cinder_lance=v1,kindling=v2" d2r-sorc build`.
- Adding rows (new states, helper skills, missiles): use a new key plus `_clone=<existing key>`;
  `*Id` is assigned automatically. Unknown columns fail the build.
- Non-baseline variants show `[test variant: <name>]` in the skill tooltip so you can confirm in game
  which build you are testing. `stub` skills say they still behave as the vanilla row.

## Rules that keep context small
- Change one variable per variant; name the variant after it.
- Always `log` what you saw before moving on, then `commit`.
- Specs live in git, so any checkpoint is a `git checkout` away.

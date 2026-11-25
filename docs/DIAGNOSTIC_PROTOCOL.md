# Castalia — Controlled Skill & Mechanic Diagnostic Protocol

Use this protocol whenever implementing a new skill, experimenting with an unverified D2R engine function (`srvstfunc`/`srvdofunc`/`pSrvDoFunc`/`itemevent`), or debugging unexpected in-game behavior. **Never guess blindly or change 3 variables at once.**

---

## 1. Before Writing Any Code
1. **Check the verified references first:**
   - [`docs/engine/STATS_AND_PITFALLS.md`](file:///home/grant/games/d2r/docs/engine/STATS_AND_PITFALLS.md) — check repurposed stat IDs, state groups, and explicitly known-FALSE behaviors.
   - [`docs/engine/FUNCTIONS.md`](file:///home/grant/games/d2r/docs/engine/FUNCTIONS.md) — check proven `srvdofunc`, `pSrvDoFunc`, `pSrvHitFunc`, `pSrvDmgFunc` rows.
   - For Sorceress skills, run `/home/grant/games/d2r/bin/d2r-sorc patterns <slug>` and `/home/grant/games/d2r/bin/d2r-sorc funcs [query]`.
2. **Never assume an untested engine interaction works.** If a behavior is not explicitly documented as verified in `docs/engine/` or `docs/classes/`, state clearly that it is a hypothesis to test.

---

## 2. The 1-Variable Diagnostic Loop
When a skill or mechanic does not behave as expected in-game:

1. **Inspect the actual compiled TSV output first** (`game/Diablo II Resurrected/mods/castalia/castalia.mpq/data/global/excel/*.txt`) — verify formula length (`<= 248` chars), column values, and stat/state IDs before assuming a C++ quirk.
2. **List explicit hypotheses (H1, H2, H3)** — each falsifiable by a single test.
3. **Run a Baseline Control (Test 1):**
   - Strip the formula/mechanic down to the simplest possible control (short calc, no extra states, no extra dependencies) to prove the core hook works.
4. **Add a Temporary Visible Debug Signal When Testing Invisible States/Events:**
   - For hidden states (`stamina_fatigue`, `stun_fatigue`, `stun_reset`, etc.), temporarily attach a distinct visual `overlay1` (e.g. `"shout"`, `"energyshield"`) so in-game testing gives an unambiguous **YES / NO** signal on whether the event fired and whether the state cleared.
5. **Change strictly 1 variable per test iteration** and record the exact observed in-game result (`PASS` / `FAIL` / `PARTIAL`).
6. **Lock in the victory with a unit test** in `tests/test_skill_simulation.py` or `tests/test_engine_contracts.py` (and remove any temporary debug overlays or QA flags in `mod_config.json` before committing).

---

## 3. Pre-Commit Checklist
- [ ] All temporary debug overlays removed from `states.txt` / `common.py`.
- [ ] `tools/mod_builder/mod_config.json` has `"qa_blood_moor_boost": false`, `"qa_cube_starter_kit": false`, `"qa_conduction_test": false` (and `cubemain` / `treasureclass` rebuilt if any were toggled).
- [ ] `python3 -m unittest -v` passes 100% (`37+` tests, including `test_calc_formula_character_length_limits`).
- [ ] Any newly verified engine behavior or newly proven-FALSE pitfall is promoted into [`docs/engine/STATS_AND_PITFALLS.md`](file:///home/grant/games/d2r/docs/engine/STATS_AND_PITFALLS.md) and [`docs/classes/<class>.md`](file:///home/grant/games/d2r/docs/classes) (do not leave one-off diagnostic scratch logs in the repo).

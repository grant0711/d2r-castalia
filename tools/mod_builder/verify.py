#!/usr/bin/env python3
"""
verify.py
Automated, Non-Tautological TDD Test Suite Orchestrator for Castalia (D2R Overhaul Mod).
Executes the modular unittest suites under `tests/` at the end of d2r-build-mod.py:
  1. test_engine_contracts.py    — Referential integrity, function-to-column coupling rules, zero elemental/sunder pierce boundary, binary bounds
  2. test_skill_simulation.py    — Formula syntax/reference linting, monotonic scaling, Sorceress stance matrix & cross-stance fizzle simulation
  3. test_skill_trees.py         — Skill tree prerequisite DAG, canonical reqlevel gates (1/8/16/24/32/40), and UI connector arrow geometry
  4. test_world_invariants.py    — TreasureClassEx, objects.txt, shrines.txt, objpreset.txt, misc.txt, books.txt, charstats.txt
  5. test_item_invariants.py     — weapons.txt, armor.txt, automagic.txt staffmods, affixes, locked unique/set parity & oskill compatibility
  6. test_monster_invariants.py  — monstats.txt affinities/resistances/aidist, levels.txt density & Optional Dungeons, cubemain distillation, hireling 9-aura matrix
"""
import io
import os
import sys
import unittest
from typing import List

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TESTS_DIR = os.path.join(REPO_ROOT, "tests")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tests.fixture import clear_fixture_caches, read_mod_tsv as _read_mod_tsv


SUITE_DESCRIPTIONS = [
    "engine referential, function-column coupling & zero elemental/sunder pierce contracts",
    "behavioral skill formula linting, stance matrix & cross-stance fizzle simulation",
    "class skill tree prerequisite DAG, reqlevel gates & UI connector arrow geometry",
    "TreasureClassEx, objects.txt, shrines.txt & misc.txt world/drop invariants",
    "weapons/armor vendor progression, staffmod brackets, affixes & locked unique/set oskill compatibility",
    "monster affinities/resistance caps, optional dungeons, cubemain distillation & hireling 9-aura matrix",
]


def verify_all(cfg: dict = None) -> List[str]:
    """Run all modular test suites under tests/ and raise AssertionError if any fail."""
    clear_fixture_caches()
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=TESTS_DIR, pattern="test_*.py", top_level_dir=REPO_ROOT)

    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(suite)

    if not result.wasSuccessful():
        details = []
        for test_case, tb in result.failures + result.errors:
            details.append(f"--- {test_case} ---\n{tb}")
        raise AssertionError(
            f"Verification test suite failed ({len(result.failures)} failures, {len(result.errors)} errors):\n"
            + "\n".join(details)
        )

    return list(SUITE_DESCRIPTIONS)


if __name__ == "__main__":
    passed = verify_all()
    print(f"All {len(passed)} test suites passed:")
    for desc in passed:
        print(f"  [OK] {desc}")

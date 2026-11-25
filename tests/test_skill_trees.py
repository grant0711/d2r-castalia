"""
test_skill_trees.py
Skill Tree Prerequisite DAG, Level Gate Ordering, and UI Geometry Invariants.
Verifies that across our reworked classes (Paladin, Barbarian, Assassin, Sorceress):
1. All 30 class skills sit on unique (SkillPage, SkillRow, SkillColumn) grid slots
2. Every skill uses a canonical level gate in {1, 8, 16, 24, 32, 40}
3. Every prerequisite skill (reqskill1..3) belongs to the same class and has reqlevel <= dependent skill's reqlevel
4. Every same-page prerequisite edge connects valid grid coordinates (downward vertical, adjacent-row diagonal, or adjacent horizontal)
5. Sorceress registry (check_registry) passes with zero structural errors
"""
import unittest
from typing import Dict, Tuple

from tests.fixture import get_indexed_tables, read_mod_tsv
from mod_builder.classes.assassin.registry import check_registry as check_ass_registry
from mod_builder.classes.barbarian.registry import check_registry as check_bar_registry
from mod_builder.classes.paladin.registry import check_registry as check_pal_registry
from mod_builder.classes.sorceress.registry import check_registry as check_sor_registry


class TestSkillTrees(unittest.TestCase):
    """Graph and UI geometry invariants for all reworked class skill trees."""

    REWORKED_CLASSES = ("pal", "bar", "ass", "sor")
    VALID_REQLEVELS = {1, 8, 16, 24, 32, 40}

    def test_all_class_registries_integrity(self):
        for name, fn in (
            ("paladin", check_pal_registry),
            ("barbarian", check_bar_registry),
            ("assassin", check_ass_registry),
            ("sorceress", check_sor_registry),
        ):
            self.assertEqual(fn(), [], f"{name} registry check failed")

    def test_reworked_class_tree_grid_gates_and_prereq_dag(self):
        idx = get_indexed_tables()
        skills_by_name = idx["skills_by_name"]
        _, skill_rows = read_mod_tsv("skills.txt")
        _, desc_rows = read_mod_tsv("skilldesc.txt")
        desc_by_name = {r["skilldesc"]: r for r in desc_rows if r.get("skilldesc")}

        for cls_code in self.REWORKED_CLASSES:
            cls_skills = [r for r in skill_rows if r.get("charclass") == cls_code]
            self.assertEqual(
                len(cls_skills),
                30,
                f"Class {cls_code!r} must have exactly 30 skills, found {len(cls_skills)}",
            )

            seen_coords: Dict[Tuple[int, int, int], str] = {}
            for srow in cls_skills:
                sname = srow["skill"]
                req_lvl = int(srow.get("reqlevel") or "0")
                self.assertIn(
                    req_lvl,
                    self.VALID_REQLEVELS,
                    f"skills.txt ({sname}, class={cls_code}): reqlevel={req_lvl} not in {sorted(self.VALID_REQLEVELS)}",
                )

                sd_key = srow.get("skilldesc", "").strip()
                self.assertIn(sd_key, desc_by_name, f"skills.txt ({sname}): missing skilldesc {sd_key!r}")
                drow = desc_by_name[sd_key]

                page = int(drow.get("SkillPage") or "0")
                row = int(drow.get("SkillRow") or "0")
                col = int(drow.get("SkillColumn") or "0")
                if page > 0:
                    self.assertIn(page, (1, 2, 3), f"{sname}: invalid SkillPage={page}")
                    self.assertIn(row, (1, 2, 3, 4, 5, 6), f"{sname}: invalid SkillRow={row}")
                    self.assertIn(col, (1, 2, 3), f"{sname}: invalid SkillColumn={col}")
                    coord = (page, row, col)
                    self.assertNotIn(
                        coord,
                        seen_coords,
                        f"Class {cls_code!r} coordinate collision at {coord}: {sname} vs {seen_coords.get(coord)}",
                    )
                    seen_coords[coord] = sname

                for r_i in (1, 2, 3):
                    req_name = srow.get(f"reqskill{r_i}", "").strip()
                    if not req_name:
                        continue
                    self.assertIn(
                        req_name,
                        skills_by_name,
                        f"skills.txt ({sname}): reqskill{r_i}={req_name!r} does not exist",
                    )
                    req_row = skills_by_name[req_name]
                    self.assertEqual(
                        req_row.get("charclass"),
                        cls_code,
                        f"skills.txt ({sname}): cross-class prerequisite {req_name!r}",
                    )
                    parent_lvl = int(req_row.get("reqlevel") or "0")
                    self.assertLessEqual(
                        parent_lvl,
                        req_lvl,
                        f"skills.txt ({sname}, reqlevel={req_lvl}): depends on higher-level skill {req_name!r} (reqlevel={parent_lvl})",
                    )

                    parent_drow = desc_by_name.get(req_row.get("skilldesc", "").strip(), {})
                    p_page = int(parent_drow.get("SkillPage") or "0")
                    p_row = int(parent_drow.get("SkillRow") or "0")
                    p_col = int(parent_drow.get("SkillColumn") or "0")
                    if page > 0 and p_page == page:
                        is_valid_edge = (
                            (p_col == col and row > p_row)
                            or (abs(col - p_col) == 1 and row >= p_row)
                        )
                        self.assertTrue(
                            is_valid_edge,
                            f"skills.txt ({sname}): invalid UI arrow geometry from {req_name} (r={p_row},c={p_col}) to {sname} (r={row},c={col})",
                        )


if __name__ == "__main__":
    unittest.main()

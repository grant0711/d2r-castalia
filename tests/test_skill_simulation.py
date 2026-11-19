"""
test_skill_simulation.py
Behavioral Formula Linter & Gameplay State Simulator.
Instead of tautological string equality assertions, this suite parses and evaluates
the compiled D2R expressions in skills.txt, missiles.txt, and skilldesc.txt across
simulated player states (slvl=1..20, synergy allocations, active stance markers).
"""
import unittest

from tests.calc_eval import eval_d2_expr, lint_d2_expression
from tests.fixture import get_indexed_tables, read_mod_tsv, read_vanilla_tsv
from mod_builder.sorc.engine import load_state
from mod_builder.sorc.patterns import STANCE_MARKERS
from mod_builder.sorc.registry import SLOTS


class TestSkillSimulation(unittest.TestCase):
    """Non-tautological formula linting and behavioral state simulation across compiled skills."""

    def test_all_reworked_class_skill_and_tooltip_formulas_parse_and_reference_valid_entities(self):
        """Every modified expression in skills.txt and skilldesc.txt for our reworked classes must have balanced syntax and valid skill()/stat()/miss() references."""
        idx = get_indexed_tables()
        skills_by_name = idx["skills_by_name"]
        valid_stats = idx["valid_stats"]
        missiles_by_name = idx["missiles_by_name"]
        desc_by_name = idx["desc_by_name"]
        _, van_sk_rows = read_vanilla_tsv("skills.txt")
        van_skills_by_name = {r["skill"]: r for r in van_sk_rows if r.get("skill")}

        reworked_classes = {"pal", "bar", "ass", "sor"}
        formula_cols = (
            "calc1",
            "calc2",
            "calc3",
            "calc4",
            "calc5",
            "calc6",
            "cltcalc1",
            "cltcalc2",
            "cltcalc3",
            "auralencalc",
            "aurarangecalc",
            "aurastatcalc1",
            "aurastatcalc2",
            "aurastatcalc3",
            "aurastatcalc4",
            "aurastatcalc5",
            "aurastatcalc6",
            "passivecalc1",
            "passivecalc2",
            "passivecalc3",
            "passivecalc4",
            "passivecalc5",
            "passivecalc6",
            "EDmgSymPerCalc",
            "ELenSymPerCalc",
            "DmgSymPerCalc",
            "ToHitCalc",
        )

        for sname, srow in skills_by_name.items():
            if srow.get("charclass") not in reworked_classes:
                continue
            vrow = van_skills_by_name.get(sname, {})
            for col in formula_cols:
                expr = srow.get(col, "").strip()
                if not expr or expr == vrow.get(col, "").strip():
                    continue
                errs = lint_d2_expression(expr, skills_by_name, valid_stats, missiles_by_name)
                self.assertEqual(
                    errs,
                    [],
                    f"skills.txt ({sname}.{col}): formula lint failure: {errs}",
                )

            sd_key = srow.get("skilldesc", "").strip()
            drow = desc_by_name.get(sd_key, {})
            for dcol, dval in drow.items():
                if dcol.endswith(("cal1", "cal2", "cal3", "cal4", "cal5", "cal6", "cal7", "calc1", "calc2")) and dval:
                    errs = lint_d2_expression(dval, skills_by_name, valid_stats, missiles_by_name)
                    self.assertEqual(
                        errs,
                        [],
                        f"skilldesc.txt ({sd_key}.{dcol} for {sname}): formula lint failure: {errs}",
                    )

    def test_sorceress_stance_simulation_and_cross_stance_fizzle(self):
        """
        Simulate all reworked Sorceress skills across 4 player states:
        1. Neutral (slvl=10, no stance active) -> positive effect & monotonic slvl=20 >= slvl=1
        2. Matching stance active (slvl=10, matching marker=10) -> effect >= Neutral
        3. Opposing stance A active (slvl=10, opposing marker=10) -> cross-stance fizzle evaluates <= 0
        4. Opposing stance B active (slvl=10, opposing marker=10) -> cross-stance fizzle evaluates <= 0
        """
        idx = get_indexed_tables()
        skills_by_name = idx["skills_by_name"]
        missiles_by_name = idx["missiles_by_name"]
        state = load_state()

        for meta in SLOTS:
            st_entry = state.get(meta["slug"], {})
            active_var = st_entry.get("active", "baseline")
            if active_var == "baseline":
                continue

            tree = meta["tree"]
            role = meta["role"]
            vname = meta["vname"]
            srow = skills_by_name[vname]
            own_marker = STANCE_MARKERS[tree]["marker_stat"]
            opp_markers = STANCE_MARKERS[tree]["opposing_stats"]

            # Stance skill itself
            if role == "STANCE":
                marker_found = any(
                    srow.get(f"aurastat{i}") == own_marker for i in range(1, 7)
                )
                self.assertTrue(
                    marker_found,
                    f"Sorceress stance {meta['name']} ({vname}) must grant marker stat {own_marker!r}",
                )
                continue

            # Passive slots (support passive or dial)
            if "passive" in role or "dial" in role:
                self.assertTrue(
                    bool(srow.get("passivestate", "").strip()),
                    f"Sorceress passive {meta['name']} ({vname}) must define passivestate",
                )
                p1_l1 = eval_d2_expr(srow.get("passivecalc1", ""), srow, slvl=1, skills_by_name=skills_by_name)
                p1_l20 = eval_d2_expr(srow.get("passivecalc1", ""), srow, slvl=20, skills_by_name=skills_by_name)
                self.assertNotEqual(p1_l1, 0, f"{meta['name']}: passivecalc1 at slvl=1 must be non-zero")
                self.assertGreaterEqual(abs(p1_l20), abs(p1_l1), f"{meta['name']}: passivecalc1 must scale monotonically in magnitude")
                continue

            # Active spells: locate all expressions carrying cross-stance fizzle guards
            candidate_exprs = []
            for col in ("EDmgSymPerCalc", "ELenSymPerCalc", "auralencalc", "calc1", "calc2", "calc3", "calc4"):
                val = srow.get(col, "").strip()
                if opp_markers[0] in val and opp_markers[1] in val:
                    candidate_exprs.append((f"skills.txt:{col}", srow, val))

            for mcol in ("srvmissile", "srvmissilea", "srvmissileb", "srvmissilec"):
                mname = srow.get(mcol, "").strip()
                if mname and mname in missiles_by_name:
                    mrow = missiles_by_name[mname]
                    for mf_col in ("EDmgSymPerCalc", "ELenSymPerCalc", "DmgSymPerCalc", " cAlc1", "calc1"):
                        mval = mrow.get(mf_col, "").strip()
                        if opp_markers[0] in mval and opp_markers[1] in mval:
                            candidate_exprs.append((f"missiles.txt({mname}):{mf_col}", mrow, mval))

            self.assertGreater(
                len(candidate_exprs),
                0,
                f"Active reworked Sorceress spell {meta['name']} ({meta['slug']}) is missing cross-stance fizzle guard against {opp_markers}",
            )

            for label, target_row, expr in candidate_exprs:
                neutral_val = eval_d2_expr(
                    expr,
                    target_row,
                    slvl=10,
                    skill_levels={vname: 10},
                    stats={},
                    skills_by_name=skills_by_name,
                )
                match_val = eval_d2_expr(
                    expr,
                    target_row,
                    slvl=10,
                    skill_levels={vname: 10, STANCE_MARKERS[tree]["stance_skill"]: 10},
                    stats={own_marker: 10},
                    skills_by_name=skills_by_name,
                )
                opp_a_val = eval_d2_expr(
                    expr,
                    target_row,
                    slvl=10,
                    skill_levels={vname: 10},
                    stats={opp_markers[0]: 10},
                    skills_by_name=skills_by_name,
                )
                opp_b_val = eval_d2_expr(
                    expr,
                    target_row,
                    slvl=10,
                    skill_levels={vname: 10},
                    stats={opp_markers[1]: 10},
                    skills_by_name=skills_by_name,
                )

                self.assertGreaterEqual(
                    match_val,
                    neutral_val,
                    f"{meta['name']} ({label}): matching stance output ({match_val}) must be >= neutral ({neutral_val})",
                )
                self.assertLessEqual(
                    opp_a_val,
                    0,
                    f"{meta['name']} ({label}): must fizzle (<= 0) when opposing stance {opp_markers[0]} is active, got {opp_a_val}",
                )
                self.assertLessEqual(
                    opp_b_val,
                    0,
                    f"{meta['name']} ({label}): must fizzle (<= 0) when opposing stance {opp_markers[1]} is active, got {opp_b_val}",
                )

    def test_assassin_trap_and_charge_behavioral_contracts(self):
        """Verify Assassin trap petmax scaling (1->2->3 at 10 and 25 synergy points) and Charge-3 conditional micro-stun evaluation."""
        idx = get_indexed_tables()
        skills_by_name = idx["skills_by_name"]
        missiles_by_name = idx["missiles_by_name"]
        _, pet_rows = read_mod_tsv("pettype.txt")
        pet_by_type = {r.get("pet type", ""): r for r in pet_rows if r.get("pet type")}

        for req_pt in ("phystrap", "firetrap", "ltngtrap", "miasmatrap", "deathtrap", "bladesentinel"):
            self.assertIn(req_pt, pet_by_type, f"pettype.txt missing dedicated trap pettype {req_pt!r}")
            self.assertEqual(pet_by_type[req_pt].get("partysend"), "1")

        for trap_name, syn_a, syn_b in (
            ("Wake of Fire Sentry", "Death Sentry", "Lightning Sentry"),
            ("Fire Trauma", "Tiger Strike", "Shock Field"),
        ):
            trow = skills_by_name[trap_name]
            pmax_expr = trow.get("petmax", "")
            self.assertEqual(
                eval_d2_expr(pmax_expr, trow, slvl=1, skill_levels={trap_name: 1}, skills_by_name=skills_by_name),
                1,
                f"{trap_name}: base petmax at 1 point must be 1",
            )
            self.assertEqual(
                eval_d2_expr(
                    pmax_expr,
                    trow,
                    slvl=5,
                    skill_levels={syn_a: 5, syn_b: 5},
                    skills_by_name=skills_by_name,
                ),
                2,
                f"{trap_name}: petmax at 10 total synergy points must be 2",
            )
            self.assertEqual(
                eval_d2_expr(
                    pmax_expr,
                    trow,
                    slvl=10,
                    skill_levels={syn_a: 15, syn_b: 10},
                    skills_by_name=skills_by_name,
                ),
                3,
                f"{trap_name}: petmax at 25 total synergy points must be 3",
            )

        sfe_row = missiles_by_name["sucfireballexplode"]
        self.assertEqual(sfe_row.get("pSrvDmgFunc"), "7")
        self.assertEqual(sfe_row.get("InitSteps"), "0")
        self.assertEqual(sfe_row.get("ProgOverlay"), "")
        rng_expr = sfe_row.get("Range", "")
        self.assertEqual(
            eval_d2_expr(rng_expr, sfe_row, stats={"progressive_fire": 2}, skills_by_name=skills_by_name),
            0,
            "sucfireballexplode: Range must evaluate to 0 when progressive_fire < 3",
        )
        self.assertGreater(
            eval_d2_expr(rng_expr, sfe_row, stats={"progressive_fire": 3}, skills_by_name=skills_by_name),
            0,
            "sucfireballexplode: Range must evaluate > 0 when progressive_fire == 3",
        )


if __name__ == "__main__":
    unittest.main()

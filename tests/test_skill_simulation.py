"""
test_skill_simulation.py
Behavioral Formula Linter & Gameplay State Simulator.
Instead of tautological string equality assertions, this suite parses and evaluates
the compiled D2R expressions in skills.txt, missiles.txt, and skilldesc.txt across
simulated player states (slvl=1..20, synergy allocations, active stance markers).
"""
import unittest

from tests.calc_eval import eval_d2_expr, lint_d2_expression
from tests.fixture import get_indexed_tables, read_mod_tsv
from mod_builder.sorc.engine import active_variant, load_state
from mod_builder.sorc.patterns import STANCE_MARKERS
from mod_builder.sorc.registry import BY_SLUG, SLOTS


class TestSkillSimulation(unittest.TestCase):
    """Non-tautological formula linting and behavioral state simulation across compiled skills."""

    def test_all_reworked_class_skill_and_tooltip_formulas_parse_and_reference_valid_entities(self):
        """Every expression in skills.txt and skilldesc.txt for our reworked classes must have balanced syntax and valid skill()/stat()/miss() references."""
        idx = get_indexed_tables()
        skills_by_name = idx["skills_by_name"]
        valid_stats = idx["valid_stats"]
        missiles_by_name = idx["missiles_by_name"]
        desc_by_name = idx["desc_by_name"]

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
            for col in formula_cols:
                expr = srow.get(col, "").strip()
                if not expr:
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
        3. Opposing stance A active (slvl=10, opposing marker=10) -> cross-stance fizzle evaluates <= 1 (0 radius or 1-frame instant fizzle)
        4. Opposing stance B active (slvl=10, opposing marker=10) -> cross-stance fizzle evaluates <= 1
        """
        idx = get_indexed_tables()
        skills_by_name = idx["skills_by_name"]
        desc_by_name = idx["desc_by_name"]
        missiles_by_name = idx["missiles_by_name"]
        state = load_state()

        for meta in SLOTS:
            slug = meta["slug"]
            active_var = active_variant(slug, state)
            if active_var == "baseline":
                continue

            tree = meta["tree"]
            role = meta["role"]
            vname = meta["vname"]
            srow = skills_by_name[vname]
            drow = desc_by_name.get(srow.get("skilldesc", "").strip(), {})
            own_marker = STANCE_MARKERS[tree]["stat"]
            stance_vname = BY_SLUG[STANCE_MARKERS[tree]["stance_slug"]]["vname"]
            opp_markers = [STANCE_MARKERS[t]["stat"] for t in STANCE_MARKERS if t != tree]

            # 1. Stance skill itself
            if role == "STANCE":
                marker_found = any(
                    srow.get(f"aurastat{i}") == own_marker for i in range(1, 7)
                )
                self.assertTrue(
                    marker_found,
                    f"Sorceress stance {meta['name']} ({vname}) must grant marker stat {own_marker!r}",
                )
                c1_l1 = eval_d2_expr(srow.get("calc1", ""), srow, slvl=1, skills_by_name=skills_by_name)
                c1_l20 = eval_d2_expr(srow.get("calc1", ""), srow, slvl=20, skills_by_name=skills_by_name)
                self.assertGreater(c1_l20, c1_l1, f"{meta['name']}: stance boon calc1 must scale with level")
                continue

            # 2. Passive slots (support passive or dial)
            if "passive" in role or "dial" in role:
                calc_expr = srow.get("passivecalc1", "").strip() or srow.get("calc1", "").strip() or drow.get("desccalca1", "").strip()
                self.assertTrue(bool(calc_expr), f"Sorceress passive {meta['name']} must define a scaling expression")
                p1_l1 = eval_d2_expr(calc_expr, srow, slvl=1, skills_by_name=skills_by_name)
                p1_l20 = eval_d2_expr(calc_expr, srow, slvl=20, skills_by_name=skills_by_name)
                self.assertNotEqual(p1_l1, 0, f"{meta['name']}: passive scaling at slvl=1 must be non-zero")
                self.assertGreaterEqual(abs(p1_l20), abs(p1_l1), f"{meta['name']}: passive scaling must be monotonic")
                continue

            # 3. Mobility utility skills (flashfire, glacier_step, phase_step):
            #    MUST be strictly gated to their respective stance via restrict='2' and State1=sorc_stance_<tree>
            if "utility" in role:
                expected_state = STANCE_MARKERS[tree]["state"]
                self.assertEqual(
                    srow.get("restrict"),
                    "2",
                    f"Mobility skill {meta['name']} ({slug}) must have restrict='2' so it is only castable while its stance is active",
                )
                self.assertEqual(
                    srow.get("State1"),
                    expected_state,
                    f"Mobility skill {meta['name']} ({slug}) must have State1={expected_state!r} so it cannot be cast outside its stance",
                )
                continue

            # 3b. Cross-stance ally stance-transfer (Conduction): fizzles with no stance, succeeds in all 3 stances
            if slug == "afterglow":
                al_expr = srow.get("auralencalc", "").strip()
                mk_expr = srow.get("aurastatcalc1", "").strip()
                self.assertEqual(
                    eval_d2_expr(al_expr, srow, slvl=10, skill_levels={vname: 10}, stats={}, skills_by_name=skills_by_name),
                    1,
                    "Conduction must fizzle (auralencalc == 1) when no stance is active",
                )
                for idx_m, m_stat in enumerate(("skill_handofathena", "skill_decrepify", "skill_frenzy"), start=1):
                    self.assertGreater(
                        eval_d2_expr(al_expr, srow, slvl=10, skill_levels={vname: 10}, stats={m_stat: 1}, skills_by_name=skills_by_name),
                        1000,
                        f"Conduction must apply full duration in stance {m_stat}",
                    )
                    self.assertEqual(
                        eval_d2_expr(mk_expr, srow, slvl=10, skill_levels={vname: 10}, stats={m_stat: 1}, skills_by_name=skills_by_name),
                        idx_m * 1000,
                        f"Conduction marker must equal {idx_m * 1000} in stance {m_stat}",
                    )
                continue

            # 4. Offensive active spells: locate all expressions carrying cross-stance fizzle guards
            candidate_exprs = []
            for col in ("EDmgSymPerCalc", "ELenSymPerCalc", "auralencalc", "aurarangecalc", "calc1", "calc2", "calc3", "calc4", "cltcalc1"):
                val = srow.get(col, "").strip()
                if opp_markers[0] in val and opp_markers[1] in val:
                    candidate_exprs.append((f"skills.txt:{col}", srow, val))

            for mcol in ("srvmissile", "srvmissilea", "srvmissileb", "srvmissilec"):
                mname = srow.get(mcol, "").strip()
                if mname and mname in missiles_by_name:
                    mrow = missiles_by_name[mname]
                    for mf_col in ("Range", "Radius", "EDmgSymPerCalc", "ELenSymPerCalc", "DmgSymPerCalc", " cAlc1", "calc1"):
                        mval = mrow.get(mf_col, "").strip()
                        if opp_markers[0] in mval and opp_markers[1] in mval:
                            candidate_exprs.append((f"missiles.txt({mname}):{mf_col}", mrow, mval))

            self.assertGreater(
                len(candidate_exprs),
                0,
                f"Active reworked Sorceress spell {meta['name']} ({slug}) is missing cross-stance fizzle guard against {opp_markers}",
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
                    skill_levels={vname: 10, stance_vname: 10},
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

                if "SymPerCalc" in label:
                    self.assertGreaterEqual(
                        neutral_val,
                        0,
                        f"{meta['name']} ({label}): neutral synergy output ({neutral_val}) must be >= 0",
                    )
                else:
                    self.assertGreater(
                        neutral_val,
                        0,
                        f"{meta['name']} ({label}): neutral output ({neutral_val}) must be > 0",
                    )
                self.assertGreaterEqual(
                    match_val,
                    neutral_val,
                    f"{meta['name']} ({label}): matching stance output ({match_val}) must be >= neutral ({neutral_val})",
                )
                self.assertLess(
                    opp_a_val,
                    neutral_val,
                    f"{meta['name']} ({label}): opposing stance {opp_markers[0]} ({opp_a_val}) must be strictly < neutral ({neutral_val})",
                )
                self.assertLessEqual(
                    opp_a_val,
                    1,
                    f"{meta['name']} ({label}): must fizzle (<= 1) when opposing stance {opp_markers[0]} is active, got {opp_a_val}",
                )
                self.assertLess(
                    opp_b_val,
                    neutral_val,
                    f"{meta['name']} ({label}): opposing stance {opp_markers[1]} ({opp_b_val}) must be strictly < neutral ({neutral_val})",
                )
                self.assertLessEqual(
                    opp_b_val,
                    1,
                    f"{meta['name']} ({label}): must fizzle (<= 1) when opposing stance {opp_markers[1]} is active, got {opp_b_val}",
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
            eval_d2_expr(rng_expr, sfe_row, skill_levels={"Ass Trap Charge Consume": 2}, skills_by_name=skills_by_name),
            0,
            "sucfireballexplode: Range must evaluate to 0 when Ass Trap Charge Consume < 3",
        )
        self.assertGreater(
            eval_d2_expr(rng_expr, sfe_row, skill_levels={"Ass Trap Charge Consume": 3}, skills_by_name=skills_by_name),
            0,
            "sucfireballexplode: Range must evaluate > 0 when Ass Trap Charge Consume == 3",
        )

    def test_barbarian_stamina_pendulum_behavioral_contracts(self):
        """
        Simulate all 3 Barbarian Stamina Pendulum skill families across Full Stamina (100%),
        Half Stamina (50%), and Empty Stamina (0%):
          1. Stamina Spenders (Leap, Leap Attack, Whirlwind) -> degrade as Stamina falls
          2. Well-Rested Skills (Bash, Stun/Shield Slam, Concentrate) -> scale UP with current Stamina %
          3. Exhaustion / Last Stand Skills (Double Swing, Double Throw, Frenzy, Berserk) -> scale UP with missing Stamina %
        """
        idx = get_indexed_tables()
        skills_by_name = idx["skills_by_name"]

        full_stam = {"stamina": 25600, "maxstamina": 25600, "toblock": 50}
        half_stam = {"stamina": 12800, "maxstamina": 25600, "toblock": 50}
        empty_stam = {"stamina": 0, "maxstamina": 25600, "toblock": 50}

        # 1. Stamina Spenders degrade monotonically as Stamina falls
        for sk_name, col in (
            ("Leap", "calc1"),
            ("Leap", "calc2"),
            ("Leap", "calc3"),
            ("Leap Attack", "calc1"),
            ("Leap Attack", "calc2"),
            ("Leap Attack", "DmgSymPerCalc"),
            ("Whirlwind", "calc1"),
        ):
            row = skills_by_name[sk_name]
            expr = row.get(col, "")
            v_full = eval_d2_expr(expr, row, slvl=10, stats=full_stam, skills_by_name=skills_by_name)
            v_half = eval_d2_expr(expr, row, slvl=10, stats=half_stam, skills_by_name=skills_by_name)
            v_empty = eval_d2_expr(expr, row, slvl=10, stats=empty_stam, skills_by_name=skills_by_name)
            self.assertGreater(
                v_full,
                v_half,
                f"Barbarian {sk_name}.{col}: Full Stamina ({v_full}) must be > Half Stamina ({v_half})",
            )
            self.assertGreater(
                v_half,
                v_empty,
                f"Barbarian {sk_name}.{col}: Half Stamina ({v_half}) must be > Empty Stamina ({v_empty})",
            )

        # Leap Attack Landing Stun (calc4) scales linearly 100% -> 33% Stamina, hard cutoff (0) below 33%
        lpat_row = skills_by_name["Leap Attack"]
        stam_33 = {"stamina": 33 * 256, "maxstamina": 100 * 256}
        stam_32 = {"stamina": 32 * 256, "maxstamina": 100 * 256}
        lpat_full = eval_d2_expr(lpat_row["calc4"], lpat_row, slvl=10, stats=full_stam, skills_by_name=skills_by_name)
        lpat_half = eval_d2_expr(lpat_row["calc4"], lpat_row, slvl=10, stats=half_stam, skills_by_name=skills_by_name)
        lpat_33 = eval_d2_expr(lpat_row["calc4"], lpat_row, slvl=10, stats=stam_33, skills_by_name=skills_by_name)
        lpat_32 = eval_d2_expr(lpat_row["calc4"], lpat_row, slvl=10, stats=stam_32, skills_by_name=skills_by_name)
        self.assertGreater(lpat_full, lpat_half)
        self.assertGreater(lpat_half, lpat_33)
        self.assertGreater(lpat_33, 0)
        self.assertEqual(lpat_32, 0)
        self.assertEqual(
            eval_d2_expr(lpat_row["calc4"], lpat_row, slvl=10, stats=empty_stam, skills_by_name=skills_by_name),
            0,
        )

        # Universal Half-Power Stamina Rule (50% at empty -> 100% at full) on Paladin & Assassin physical/speed skills
        for sk_name, col, expect_zero_mana in (
            ("Sacrifice", "calc1", True),
            ("Smite", "calc1", True),
            ("Charge", "calc1", True),
            ("Charge", "calc2", True),
            ("Zeal", "calc2", True),
            ("Tiger Strike", "calc1", True),
            ("Dragon Talon", "calc2", True),
            ("Dragon Claw", "calc1", True),
            ("Dragon Flight", "calc1", False),
            ("Royal Strike", "calc1", False),
            ("Quickness", "aurastatcalc1", False),
            ("Quickness", "aurastatcalc2", False),
        ):
            row = skills_by_name[sk_name]
            if expect_zero_mana:
                self.assertEqual(row.get("mana", ""), "0", f"{sk_name} must be 0 mana")
            elif sk_name == "Dragon Flight":
                self.assertGreater(int(row.get("mana") or "0"), 0, "Dragon Flight must retain mana cost")
            v_full = eval_d2_expr(row[col], row, slvl=10, stats=full_stam, skills_by_name=skills_by_name)
            v_empty = eval_d2_expr(row[col], row, slvl=10, stats=empty_stam, skills_by_name=skills_by_name)
            self.assertGreater(v_full, 0, f"{sk_name}.{col} must be positive at full stamina")
            self.assertEqual(v_empty, v_full // 2, f"{sk_name}.{col} must halve at 0% stamina ({v_empty} vs {v_full}//2)")

        # Global Stamina Fatigue normalized inverse severity-vs-duration curve + Bloodlust & Merc exemptions
        sf_row = skills_by_name["Stamina Fatigue"]
        for pct, exp_frw, exp_ias, exp_fcr, exp_fhr, exp_len in (
            (100, 0, 0, 0, 0, 1),
            (65, 0, 0, 0, 0, 1),
            (50, -4, -3, -4, -2, 744),
            (25, -14, -12, -12, -6, 223),
            (10, -29, -24, -26, -13, 77),
            (0, -40, -33, -36, -18, 50),
        ):
            st = {"stamina": pct * 256, "maxstamina": 100 * 256}
            frw = eval_d2_expr(sf_row["aurastatcalc1"], sf_row, slvl=1, stats=st, skills_by_name=skills_by_name)
            ias = eval_d2_expr(sf_row["aurastatcalc2"], sf_row, slvl=1, stats=st, skills_by_name=skills_by_name)
            fcr = eval_d2_expr(sf_row["aurastatcalc3"], sf_row, slvl=1, stats=st, skills_by_name=skills_by_name)
            fhr = eval_d2_expr(sf_row["aurastatcalc4"], sf_row, slvl=1, stats=st, skills_by_name=skills_by_name)
            fbr = eval_d2_expr(sf_row["aurastatcalc5"], sf_row, slvl=1, stats=st, skills_by_name=skills_by_name)
            dur = eval_d2_expr(sf_row["auralencalc"], sf_row, slvl=1, stats=st, skills_by_name=skills_by_name)
            self.assertEqual((frw, ias, fcr, fhr, fbr), (exp_frw, exp_ias, exp_fcr, exp_fhr, exp_fhr), f"Stamina Fatigue at {pct}%")
            self.assertEqual(dur, exp_len, f"Stamina Fatigue duration at {pct}%: expected {exp_len}, got {dur}")
        # Barbarian Bloodlust (skill_chillingarmor > 0) and Mercenary (maxstamina = 0) are exempt
        # and Bloodlust also collapses auralencalc to 1 frame so any prior fatigue is wiped on first swing/hit
        self.assertEqual(
            eval_d2_expr(sf_row["auralencalc"], sf_row, slvl=1, stats={"stamina": 0, "maxstamina": 100 * 256, "skill_chillingarmor": 1}, skills_by_name=skills_by_name),
            1,
        )
        for col in ("aurastatcalc1", "aurastatcalc2", "aurastatcalc3", "aurastatcalc4", "aurastatcalc5"):
            self.assertEqual(
                eval_d2_expr(sf_row[col], sf_row, slvl=1, stats={"stamina": 0, "maxstamina": 100 * 256, "skill_chillingarmor": 1}, skills_by_name=skills_by_name),
                0,
            )
            self.assertEqual(
                eval_d2_expr(sf_row[col], sf_row, slvl=1, stats={"stamina": 0, "maxstamina": 0}, skills_by_name=skills_by_name),
                0,
            )

        # Paladin Aura Mana Devotion Curve (50-100%:100%, 25%:75%, 10%:50%, 5%:25%, 0%:0%)
        for aura_name, col in (
            ("Fanaticism", "aurastatcalc1"),
            ("Fanaticism", "passivecalc1"),
            ("Vigor", "aurastatcalc1"),
            ("Might", "aurastatcalc1"),
            ("Salvation", "aurastatcalc1"),
        ):
            arow = skills_by_name[aura_name]
            m100 = {"mana": 100 * 256, "maxmana": 100 * 256}
            m50 = {"mana": 50 * 256, "maxmana": 100 * 256}
            m25 = {"mana": 25 * 256, "maxmana": 100 * 256}
            m10 = {"mana": 10 * 256, "maxmana": 100 * 256}
            m05 = {"mana": 5 * 256, "maxmana": 100 * 256}
            m00 = {"mana": 0, "maxmana": 100 * 256}
            v100 = eval_d2_expr(arow[col], arow, slvl=10, stats=m100, skills_by_name=skills_by_name)
            v50 = eval_d2_expr(arow[col], arow, slvl=10, stats=m50, skills_by_name=skills_by_name)
            v25 = eval_d2_expr(arow[col], arow, slvl=10, stats=m25, skills_by_name=skills_by_name)
            v10 = eval_d2_expr(arow[col], arow, slvl=10, stats=m10, skills_by_name=skills_by_name)
            v05 = eval_d2_expr(arow[col], arow, slvl=10, stats=m05, skills_by_name=skills_by_name)
            v00 = eval_d2_expr(arow[col], arow, slvl=10, stats=m00, skills_by_name=skills_by_name)
            self.assertGreater(v100, 0)
            self.assertEqual(v50, v100, f"{aura_name}.{col} must hold 100% at 50% mana")
            self.assertEqual(v25, (v100 * 75) // 100, f"{aura_name}.{col} must be 75% at 25% mana")
            self.assertEqual(v10, (v100 * 50) // 100, f"{aura_name}.{col} must be 50% at 10% mana")
            self.assertEqual(v05, (v100 * 25) // 100, f"{aura_name}.{col} must be 25% at 5% mana")
            self.assertEqual(v00, 0, f"{aura_name}.{col} must extinguish (0) at 0% mana")

        # All Mana-Upkeep Paladin auras shrink aurarangecalc smoothly to 0 at 0% Mana (unmistakable co-op cue)
        for pulse_aura in ("Holy Fire", "Holy Freeze", "Holy Shock", "Sanctuary", "Fanaticism", "Vigor", "Concentration", "Salvation"):
            prow = skills_by_name[pulse_aura]
            ar_full = eval_d2_expr(prow["aurarangecalc"], prow, slvl=10, stats={"mana": 100 * 256, "maxmana": 100 * 256, "skill_enchant": 0}, skills_by_name=skills_by_name)
            ar_empty = eval_d2_expr(prow["aurarangecalc"], prow, slvl=10, stats={"mana": 0, "maxmana": 100 * 256, "skill_enchant": 0}, skills_by_name=skills_by_name)
            self.assertGreater(ar_full, 0)
            self.assertEqual(ar_empty, 0)

        # Zeal (up to 5 hits @ Lvl 18+) & Dragon Talon multi-hit counts degrade smoothly with Stamina (floor 2 / 1)
        zeal_row = skills_by_name["Zeal"]
        self.assertEqual(eval_d2_expr(zeal_row["calc1"], zeal_row, slvl=18, stats=full_stam, skills_by_name=skills_by_name), 5)
        self.assertEqual(eval_d2_expr(zeal_row["calc1"], zeal_row, slvl=18, stats=half_stam, skills_by_name=skills_by_name), 3)
        self.assertEqual(eval_d2_expr(zeal_row["calc1"], zeal_row, slvl=18, stats=empty_stam, skills_by_name=skills_by_name), 2)
        dt_row = skills_by_name["Dragon Talon"]
        self.assertEqual(eval_d2_expr(dt_row["calc1"], dt_row, slvl=18, stats=full_stam, skills_by_name=skills_by_name), 4)
        self.assertEqual(eval_d2_expr(dt_row["calc1"], dt_row, slvl=18, stats=half_stam, skills_by_name=skills_by_name), 3)
        self.assertEqual(eval_d2_expr(dt_row["calc1"], dt_row, slvl=18, stats=empty_stam, skills_by_name=skills_by_name), 2)

        # Universal Stun Exhaustion Rule (100% -> 33% linear, 0 below 33%) on Paladin Smite (no knockback) & Charge
        smite_row = skills_by_name["Smite"]
        self.assertEqual(smite_row["ResultFlags"], "")
        s_full = eval_d2_expr(smite_row["calc2"], smite_row, slvl=10, stats=full_stam, skills_by_name=skills_by_name)
        s_33 = eval_d2_expr(smite_row["calc2"], smite_row, slvl=10, stats=stam_33, skills_by_name=skills_by_name)
        s_32 = eval_d2_expr(smite_row["calc2"], smite_row, slvl=10, stats=stam_32, skills_by_name=skills_by_name)
        self.assertGreater(s_full, s_33)
        self.assertGreater(s_33, 0)
        self.assertEqual(s_32, 0)
        # Stun Fatigue decay (shortparam1 = 0..4 -> 100% -> 75% -> 50% -> 25% -> 0%)
        s_hit2 = eval_d2_expr(smite_row["calc2"], smite_row, slvl=10, stats={**full_stam, "shortparam1": 1}, skills_by_name=skills_by_name)
        s_hit5 = eval_d2_expr(smite_row["calc2"], smite_row, slvl=10, stats={**full_stam, "shortparam1": 4}, skills_by_name=skills_by_name)
        self.assertGreater(s_full, s_hit2)
        self.assertGreater(s_hit2, 0)
        self.assertEqual(s_hit5, 0)

        chg_row = skills_by_name["Charge"]
        c_full = 100 + eval_d2_expr(chg_row["ELenSymPerCalc"], chg_row, slvl=10, stats=full_stam, skills_by_name=skills_by_name)
        c_33 = 100 + eval_d2_expr(chg_row["ELenSymPerCalc"], chg_row, slvl=10, stats=stam_33, skills_by_name=skills_by_name)
        c_32 = 100 + eval_d2_expr(chg_row["ELenSymPerCalc"], chg_row, slvl=10, stats=stam_32, skills_by_name=skills_by_name)
        c_hit5 = 100 + eval_d2_expr(chg_row["ELenSymPerCalc"], chg_row, slvl=10, stats={**full_stam, "shortparam1": 4}, skills_by_name=skills_by_name)
        self.assertGreater(c_full, c_33)
        self.assertGreater(c_33, 0)
        self.assertEqual(c_32, 0)
        self.assertEqual(c_hit5, 0)

        # Barbarian Shield Slam (Stun) uses the same 100% -> 33% Stun Exhaustion + Stun Fatigue Rules
        stun_row = skills_by_name["Stun"]
        st_full = 100 + eval_d2_expr(stun_row["ELenSymPerCalc"], stun_row, slvl=10, stats=full_stam, skills_by_name=skills_by_name)
        st_33 = 100 + eval_d2_expr(stun_row["ELenSymPerCalc"], stun_row, slvl=10, stats=stam_33, skills_by_name=skills_by_name)
        st_32 = 100 + eval_d2_expr(stun_row["ELenSymPerCalc"], stun_row, slvl=10, stats=stam_32, skills_by_name=skills_by_name)
        st_hit5 = 100 + eval_d2_expr(stun_row["ELenSymPerCalc"], stun_row, slvl=10, stats={**full_stam, "shortparam1": 4}, skills_by_name=skills_by_name)
        self.assertEqual(st_full, 150)
        self.assertGreater(st_33, 0)
        self.assertEqual(st_32, 0)
        self.assertEqual(st_hit5, 0)

        # 2. Well-Rested Skills increase monotonically with Current Stamina %
        for sk_name, col in (
            ("Bash", "calc1"),
            ("Stun", "calc1"),
            ("Stun", "ELenSymPerCalc"),
            ("Concentrate", "calc1"),
            ("Concentrate", "aurastatcalc1"),
        ):
            row = skills_by_name[sk_name]
            expr = row.get(col, "")
            v_full = eval_d2_expr(expr, row, slvl=10, stats=full_stam, skills_by_name=skills_by_name)
            v_empty = eval_d2_expr(expr, row, slvl=10, stats=empty_stam, skills_by_name=skills_by_name)
            self.assertGreater(
                v_full,
                v_empty,
                f"Barbarian Well-Rested {sk_name}.{col}: Full Stamina ({v_full}) must be > Empty Stamina ({v_empty})",
            )

        # 3. Exhaustion / Last Stand Skills increase monotonically as Stamina is depleted (and boost further with Bloodlust)
        empty_with_bloodlust = {"stamina": 0, "maxstamina": 25600, "skill_chillingarmor": 1}
        for sk_name in ("Double Swing", "Double Throw", "Frenzy", "Berserk"):
            row = skills_by_name[sk_name]
            expr = row.get("calc1", "")
            v_full = eval_d2_expr(expr, row, slvl=10, stats=full_stam, skills_by_name=skills_by_name)
            v_empty = eval_d2_expr(expr, row, slvl=10, stats=empty_stam, skills_by_name=skills_by_name)
            v_blust = eval_d2_expr(
                expr,
                row,
                slvl=10,
                skill_levels={"Grim Ward": 10},
                stats=empty_with_bloodlust,
                skills_by_name=skills_by_name,
            )
            self.assertGreater(
                v_empty,
                v_full,
                f"Barbarian Exhaustion {sk_name}.calc1: Empty Stamina ({v_empty}) must be > Full Stamina ({v_full})",
            )
            self.assertGreater(
                v_blust,
                v_empty,
                f"Barbarian Exhaustion {sk_name}.calc1: Bloodlust active ({v_blust}) must be > unbuffed Empty Stamina ({v_empty})",
            )

    def test_conduction_coop_paladin_assassin_and_sorc_contracts(self):
        """Verify Conduction (skill_enchant 1=Fire, 2=Ltng, 3=Cold) co-op upgrades and zero solo regression."""
        idx = get_indexed_tables()
        skills_by_name = idx["skills_by_name"]
        missiles_by_name = idx["missiles_by_name"]

        solo = {"target0": 0, "target1": 0, "goldlost": 0, "mana": 100 * 256, "maxmana": 100 * 256}
        cond_fire = {"target0": 1050, "target1": 101, "goldlost": 76, "mana": 100 * 256, "maxmana": 100 * 256}
        cond_ltng = {"target0": 2050, "target1": 101, "goldlost": 76, "mana": 100 * 256, "maxmana": 100 * 256}
        cond_cold = {"target0": 3050, "target1": 101, "goldlost": 76, "mana": 100 * 256, "maxmana": 100 * 256}

        # 1. Assassin 3 Elemental Sentries: instant 3-charge deployment + orb preservation under matching Conduction
        sentry_specs = [
            ("Wake of Fire Sentry", 1, "progressive_fire", "item_slash_damage"),
            ("Lightning Sentry", 2, "progressive_lightning", "item_thrust_damage_percent"),
            ("Death Sentry", 3, "progressive_cold", "item_crush_damage"),
        ]
        for s_name, elem_id, orb_stat, buff_stat in sentry_specs:
            row = skills_by_name[s_name]
            match_st = {"target0": elem_id * 1000 + 50, "target1": 101, "goldlost": 76}
            other_st = {"target0": (1 if elem_id != 1 else 2) * 1000 + 50, "target1": 101, "goldlost": 76}
            # 0 orbs held -> 0 solo, 0 wrong conduction, 3 matching conduction
            self.assertEqual(eval_d2_expr(row["sumsk5calc"], row, slvl=10, stats=solo, skills_by_name=skills_by_name), 0)
            self.assertEqual(eval_d2_expr(row["sumsk5calc"], row, slvl=10, stats=other_st, skills_by_name=skills_by_name), 0)
            self.assertEqual(eval_d2_expr(row["sumsk5calc"], row, slvl=10, stats=match_st, skills_by_name=skills_by_name), 3)
            # Solo & matching conduction both keep standard 12-frame srvstfunc=39 duration;
            # sumsk5calc grants full 3-charge deployment with 0 orbs under matching Conduction.
            held_solo = {"target0": 0, orb_stat: 2, buff_stat: 50}
            self.assertEqual(eval_d2_expr(row["auralencalc"], row, slvl=10, stats=held_solo, skills_by_name=skills_by_name), 12)
            self.assertEqual(eval_d2_expr(row["aurastatcalc1"], row, slvl=10, stats=held_solo, skills_by_name=skills_by_name), 2)

        # 2. Assassin Charge-Up Releases (Modest @ Lvl 1 -> ~1/3 screen @ Lvl 20 -> wider under Expansion Conduction)
        fof = skills_by_name["Fists of Fire"]
        self.assertEqual(eval_d2_expr(fof["prgcalc1"], fof, slvl=1, stats=solo, skills_by_name=skills_by_name), 3)
        self.assertEqual(eval_d2_expr(fof["prgcalc1"], fof, slvl=20, stats=solo, skills_by_name=skills_by_name), 6)
        self.assertEqual(eval_d2_expr(fof["prgcalc1"], fof, slvl=20, stats=cond_fire, skills_by_name=skills_by_name), 9)
        self.assertEqual(eval_d2_expr(fof["prgcalc3"], fof, slvl=10, stats=solo, skills_by_name=skills_by_name), 8)
        self.assertEqual(eval_d2_expr(fof["prgcalc3"], fof, slvl=10, stats=cond_fire, skills_by_name=skills_by_name), 16)
        fof_fb = missiles_by_name["fof_pyroclasm_ball"]
        self.assertEqual(eval_d2_expr(fof_fb["Range"], fof_fb, slvl=1, stats=solo, skills_by_name=skills_by_name), 6)
        self.assertEqual(eval_d2_expr(fof_fb["Range"], fof_fb, slvl=20, stats=solo, skills_by_name=skills_by_name), 12)
        self.assertEqual(eval_d2_expr(fof_fb["Range"], fof_fb, slvl=20, stats=cond_fire, skills_by_name=skills_by_name), 18)

        boi = skills_by_name["Blades of Ice"]
        self.assertEqual(eval_d2_expr(boi["prgcalc1"], boi, slvl=1, stats=solo, skills_by_name=skills_by_name), 3)
        self.assertEqual(eval_d2_expr(boi["prgcalc1"], boi, slvl=20, stats=solo, skills_by_name=skills_by_name), 6)
        self.assertEqual(eval_d2_expr(boi["prgcalc1"], boi, slvl=20, stats=cond_cold, skills_by_name=skills_by_name), 10)
        self.assertEqual(eval_d2_expr(boi["prgcalc2"], boi, slvl=10, stats=cond_cold, skills_by_name=skills_by_name), 18)
        self.assertEqual(eval_d2_expr(boi["passivecalc2"], boi, slvl=10, stats=solo, skills_by_name=skills_by_name), 75)
        self.assertEqual(eval_d2_expr(boi["passivecalc2"], boi, slvl=10, stats=cond_cold, skills_by_name=skills_by_name), 150)
        self.assertEqual(eval_d2_expr(boi["ELenSymPerCalc"], boi, slvl=10, stats=solo, skills_by_name=skills_by_name), 0)
        self.assertEqual(eval_d2_expr(boi["ELenSymPerCalc"], boi, slvl=10, stats=cond_cold, skills_by_name=skills_by_name), 100)
        for mname, l1_r, l20_r, bonus_r in (
            ("royalstrikechaosice", 8, 16, 8),
            ("catapult cold ball", 8, 15, 8),
            ("catapult cold ball on", 12, 22, 12),
        ):
            mrow = missiles_by_name[mname]
            self.assertEqual(eval_d2_expr(mrow["Range"], mrow, slvl=1, stats=solo, skills_by_name=skills_by_name), l1_r)
            self.assertEqual(eval_d2_expr(mrow["Range"], mrow, slvl=20, stats=solo, skills_by_name=skills_by_name), l20_r)
            self.assertEqual(eval_d2_expr(mrow["Range"], mrow, slvl=20, stats=cond_cold, skills_by_name=skills_by_name), l20_r + bonus_r)

        cot = skills_by_name["Claws of Thunder"]
        self.assertEqual(eval_d2_expr(cot["prgcalc1"], cot, slvl=20, stats=solo, skills_by_name=skills_by_name), 4)
        self.assertEqual(eval_d2_expr(cot["prgcalc1"], cot, slvl=20, stats=cond_ltng, skills_by_name=skills_by_name), 2)
        self.assertGreater(
            eval_d2_expr(cot["aurarangecalc"], cot, slvl=10, stats=cond_ltng, skills_by_name=skills_by_name),
            eval_d2_expr(cot["aurarangecalc"], cot, slvl=10, stats=solo, skills_by_name=skills_by_name),
        )
        cotn = missiles_by_name["clawsofthundernova"]
        self.assertEqual(eval_d2_expr(cotn["Range"], cotn, slvl=1, stats=solo, skills_by_name=skills_by_name), 5)
        self.assertEqual(eval_d2_expr(cotn["Range"], cotn, slvl=20, stats=solo, skills_by_name=skills_by_name), 10)
        self.assertEqual(eval_d2_expr(cotn["Range"], cotn, slvl=20, stats=cond_ltng, skills_by_name=skills_by_name), 16)
        rscl = missiles_by_name["royalstrikechainlightning"]
        self.assertEqual(eval_d2_expr(rscl["Range"], rscl, slvl=1, stats=solo, skills_by_name=skills_by_name), 6)
        self.assertEqual(eval_d2_expr(rscl["Range"], rscl, slvl=20, stats=solo, skills_by_name=skills_by_name), 14)
        self.assertEqual(eval_d2_expr(rscl["Range"], rscl, slvl=20, stats=cond_ltng, skills_by_name=skills_by_name), 22)
        cot_sp = missiles_by_name["cot_conduction_spark"]
        self.assertEqual(eval_d2_expr(cot_sp["Range"], cot_sp, slvl=10, stats=solo, skills_by_name=skills_by_name), 0)
        self.assertEqual(eval_d2_expr(cot_sp["Range"], cot_sp, slvl=10, stats=cond_ltng, skills_by_name=skills_by_name), 6)
        # Tiger Strike & Cobra Strike Charge 1..3 level-scaled rings + Expansion Conduction
        for mname, l1_r, l20_r, bonus_r in (
            ("inferno sentry 1", 5, 8, 4),
            ("inferno sentry 2", 7, 12, 5),
            ("progressive radius damage", 9, 18, 7),
            ("unholybolt2", 5, 8, 4),
            ("unholybolt3", 7, 12, 5),
            ("unholybolt4", 9, 18, 7),
        ):
            mrow = missiles_by_name[mname]
            self.assertEqual(eval_d2_expr(mrow["Range"], mrow, slvl=1, stats=solo, skills_by_name=skills_by_name), l1_r)
            self.assertEqual(eval_d2_expr(mrow["Range"], mrow, slvl=20, stats=solo, skills_by_name=skills_by_name), l20_r)
            self.assertEqual(eval_d2_expr(mrow["Range"], mrow, slvl=20, stats=cond_fire, skills_by_name=skills_by_name), l20_r + bonus_r)

        # 3. Paladin 3 Elemental Auras
        for aura_name, elem_st in (("Holy Fire", cond_fire), ("Holy Shock", cond_ltng), ("Holy Freeze", cond_cold)):
            arow = skills_by_name[aura_name]
            r_solo = eval_d2_expr(arow["aurarangecalc"], arow, slvl=10, stats=solo, skills_by_name=skills_by_name)
            r_cond = eval_d2_expr(arow["aurarangecalc"], arow, slvl=10, stats=elem_st, skills_by_name=skills_by_name)
            self.assertEqual(r_cond, r_solo + 4, f"{aura_name}: radius should gain +4 sub-tiles under Conduction")
            self.assertEqual(eval_d2_expr(arow["perdelay"], arow, slvl=10, stats=solo, skills_by_name=skills_by_name), 50)
            self.assertEqual(eval_d2_expr(arow["perdelay"], arow, slvl=10, stats=elem_st, skills_by_name=skills_by_name), 35)
        hfrz = skills_by_name["Holy Freeze"]
        slow_solo = eval_d2_expr(hfrz["aurastatcalc1"], hfrz, slvl=10, stats=solo, skills_by_name=skills_by_name)
        slow_cold = eval_d2_expr(hfrz["aurastatcalc1"], hfrz, slvl=10, stats=cond_cold, skills_by_name=skills_by_name)
        self.assertEqual(slow_cold, slow_solo - 15)

        # 4. Paladin Fist of the Heavens & Vengeance
        fohd = missiles_by_name["fistoftheheavensdelay"]
        self.assertEqual(fohd["pSrvDoFunc"], "1")
        self.assertEqual(fohd["pSrvHitFunc"], "22")
        self.assertEqual(fohd["HitSubMissile1"], "fistoftheheavensbolt")
        fohb = missiles_by_name["fistoftheheavensbolt"]
        self.assertEqual(fohb["SubMissile1"], "foh_conduction_nova")
        foh_nova = missiles_by_name["foh_conduction_nova"]
        self.assertEqual(eval_d2_expr(foh_nova["Range"], foh_nova, slvl=10, stats=solo, skills_by_name=skills_by_name), 0)
        self.assertEqual(eval_d2_expr(foh_nova["Range"], foh_nova, slvl=10, stats=cond_fire, skills_by_name=skills_by_name), 0)
        self.assertEqual(eval_d2_expr(foh_nova["Range"], foh_nova, slvl=10, stats=cond_ltng, skills_by_name=skills_by_name), 10)

        veng = skills_by_name["Vengeance"]
        self.assertEqual(eval_d2_expr(veng["calc5"], veng, slvl=10, stats=solo, skills_by_name=skills_by_name), 13)
        self.assertEqual(eval_d2_expr(veng["calc7"], veng, slvl=10, stats=solo, skills_by_name=skills_by_name), 0)
        for st in (cond_fire, cond_ltng, cond_cold):
            self.assertEqual(eval_d2_expr(veng["calc5"], veng, slvl=10, stats=st, skills_by_name=skills_by_name), 20)
            self.assertEqual(eval_d2_expr(veng["calc7"], veng, slvl=10, stats=st, skills_by_name=skills_by_name), 2)
        self.assertEqual(eval_d2_expr(veng["ELenSymPerCalc"], veng, slvl=10, stats=cond_fire, skills_by_name=skills_by_name), 0)
        self.assertEqual(eval_d2_expr(veng["ELenSymPerCalc"], veng, slvl=10, stats=cond_cold, skills_by_name=skills_by_name), 100)

        # 5. Sorceress Option 1: matching Conduction activates stance bonuses without opposing-stance fizzle
        nova = skills_by_name["Nova"]
        pr_solo = eval_d2_expr(nova["calc3"], nova, slvl=10, stats=solo, skills_by_name=skills_by_name)
        pr_ltng = eval_d2_expr(nova["calc3"], nova, slvl=10, stats=cond_ltng, skills_by_name=skills_by_name)
        pr_fire = eval_d2_expr(nova["calc3"], nova, slvl=10, stats=cond_fire, skills_by_name=skills_by_name)
        self.assertEqual(pr_ltng, pr_solo + 4, "Pulse Ring must gain Overcharge bonus under Lightning Conduction")
        self.assertEqual(pr_fire, pr_solo, "Pulse Ring must NOT fizzle under Fire Conduction")

        # 6. QA Conduction hidden aura row & 3-passive independent Conduction encoding
        self.assertIn("QA Conduction", skills_by_name)
        qa = skills_by_name["QA Conduction"]
        self.assertEqual(qa["aurastate"], "sorc_conduction")
        self.assertEqual(qa["aurastat1"], "target0")
        self.assertEqual(qa["aurastat5"], "target1")
        self.assertEqual(qa["aurastat6"], "goldlost")

        cond = skills_by_name["Lightning Mastery"]
        self.assertEqual(cond.get("aurastat1", ""), "target0")
        self.assertEqual(cond.get("aurastat5", ""), "target1")
        self.assertEqual(cond.get("aurastat6", ""), "goldlost")
        fire_lv20 = eval_d2_expr(
            cond["aurastatcalc2"], cond, slvl=20,
            stats={"skill_handofathena": 1},
            skill_levels={"Enchant": 20},
            skills_by_name=skills_by_name,
        )
        fire_lv30 = eval_d2_expr(
            cond["aurastatcalc2"], cond, slvl=30,
            stats={"skill_handofathena": 1},
            skill_levels={"Enchant": 30},
            skills_by_name=skills_by_name,
        )
        self.assertEqual(fire_lv20, 30)
        self.assertEqual(fire_lv30, 30)
        # Independent encoding: Fire stance with 0 Expansion, 100 Stasis, 45 Arc at Conduction Lvl 20
        enc_t0 = eval_d2_expr(cond["aurastatcalc1"], cond, slvl=20, stats={"skill_handofathena": 1, "ironmaiden_level": 0}, skills_by_name=skills_by_name)
        enc_t1 = eval_d2_expr(cond["aurastatcalc5"], cond, slvl=20, stats={"skill_handofathena": 1, "conversion_maxhp": 100}, skills_by_name=skills_by_name)
        enc_gl = eval_d2_expr(cond["aurastatcalc6"], cond, slvl=20, stats={"skill_handofathena": 1, "lifetap_level": 45}, skills_by_name=skills_by_name)
        self.assertEqual((enc_t0, enc_t1, enc_gl), (1000, 101, 46))

        # Cross-class independent passive scaling (works regardless of Sorceress stance!)
        full_st = {"stamina": 100 * 256, "maxstamina": 100 * 256, "mana": 100 * 256, "maxmana": 100 * 256}
        mixed_fire = {**full_st, "target0": 1000, "target1": 101, "goldlost": 46}  # Fire stance, 0 Exp, 100 Sta, 45 Arc
        # Paladin Holy Shield duration gets +50% from Stasis=100 EVEN under Fire Conduction!
        hshd = skills_by_name["Holy Shield"]
        hs_solo = eval_d2_expr(hshd["auralencalc"], hshd, slvl=10, stats=full_st, skills_by_name=skills_by_name)
        hs_mix = eval_d2_expr(hshd["auralencalc"], hshd, slvl=10, stats=mixed_fire, skills_by_name=skills_by_name)
        self.assertEqual(hs_mix, (hs_solo * 150) // 100)
        # Paladin Might radius gets +0% when Expansion=0, +33% when Expansion=50
        might = skills_by_name["Might"]
        mg_solo = eval_d2_expr(might["aurarangecalc"], might, slvl=10, stats=full_st, skills_by_name=skills_by_name)
        mg_zero_exp = eval_d2_expr(might["aurarangecalc"], might, slvl=10, stats=mixed_fire, skills_by_name=skills_by_name)
        mg_max_exp = eval_d2_expr(might["aurarangecalc"], might, slvl=10, stats={**full_st, "target0": 1050}, skills_by_name=skills_by_name)
        self.assertEqual(mg_zero_exp, mg_solo)
        self.assertGreater(mg_max_exp, mg_solo)
        # Elemental aura (Holy Shock): Lightning stance + low Expansion/Arc vs high Expansion/Arc
        hshk = skills_by_name["Holy Shock"]
        hs_r_low = eval_d2_expr(hshk["aurarangecalc"], hshk, slvl=10, stats={**full_st, "target0": 2005, "goldlost": 1}, skills_by_name=skills_by_name)
        hs_r_max = eval_d2_expr(hshk["aurarangecalc"], hshk, slvl=10, stats={**full_st, "target0": 2050, "goldlost": 76}, skills_by_name=skills_by_name)
        hs_p_low = eval_d2_expr(hshk["perdelay"], hshk, slvl=10, stats={**full_st, "target0": 2005, "goldlost": 1}, skills_by_name=skills_by_name)
        hs_p_max = eval_d2_expr(hshk["perdelay"], hshk, slvl=10, stats={**full_st, "target0": 2050, "goldlost": 76}, skills_by_name=skills_by_name)
        self.assertGreater(hs_r_max, hs_r_low)
        self.assertEqual(hs_p_low, 50)
        self.assertEqual(hs_p_max, 35)
        # Barbarian Battle Orders duration (Stasis) & Assassin Shuriken chains (Arc)
        bo = skills_by_name["Battle Orders"]
        bo_solo = eval_d2_expr(bo["auralencalc"], bo, slvl=10, stats=full_st, skills_by_name=skills_by_name)
        bo_mix = eval_d2_expr(bo["auralencalc"], bo, slvl=10, stats=mixed_fire, skills_by_name=skills_by_name)
        self.assertEqual(bo_mix, (bo_solo * 150) // 100)
        shur = skills_by_name["Inferno Sentry"]
        sh_solo = eval_d2_expr(shur["calc1"], shur, slvl=10, stats=full_st, skills_by_name=skills_by_name)
        sh_mid = eval_d2_expr(shur["calc1"], shur, slvl=10, stats=mixed_fire, skills_by_name=skills_by_name)  # Arc=45 -> +1
        sh_max = eval_d2_expr(shur["calc1"], shur, slvl=10, stats={**full_st, "target0": 2050, "goldlost": 76}, skills_by_name=skills_by_name)  # Arc=75 -> +2
        self.assertEqual(sh_mid, sh_solo + 1)
        self.assertEqual(sh_max, sh_solo + 2)


if __name__ == "__main__":
    unittest.main()

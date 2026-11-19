"""
calc_eval.py
Pure-Python D2R skill/missile formula linter and behavioral simulator.
Evaluates D2R integer formulas (ln12, dm34, par1..8, clc1..6, edmn, edmx, edln,
skill('Name'.blvl), stat('name'.accr), ternary ? :, comparisons, arithmetic)
across simulated player states (slvl, synergy allocations, active stance markers).
"""
import re
from typing import Dict, List, Optional, Set, Tuple


_SKILL_REF_RE = re.compile(
    r"skill\('([^']+)'\.(lvl|blvl|rng|len|clc1|clc2|clc3|clc4|clc5|clc6|par1|par2|par3|par4|par5|par6|par7|par8)\)"
)
_STAT_REF_RE = re.compile(r"stat\('([^']+)'\.(accr|base)\)")
_MISSILE_REF_RE = re.compile(r"miss\('([^']+)'\.([A-Za-z0-9_]+)\)")


def lint_d2_expression(
    expr: str,
    skills_by_name: Dict[str, dict],
    valid_stats: Set[str],
    missiles_by_name: Optional[Dict[str, dict]] = None,
) -> List[str]:
    """
    Validate a D2R expression string for syntax and referential errors:
    - Balanced parentheses
    - Valid skill('SkillName'.prop) references against skills.txt
    - Valid stat('stat_name'.accr) references against itemstatcost.txt
    - Valid miss('MissileName'.prop) references against missiles.txt
    """
    errors: List[str] = []
    s = (expr or "").strip()
    if not s:
        return errors

    # 1. Balanced parentheses
    depth = 0
    in_quote = False
    for ch in s:
        if ch == "'":
            in_quote = not in_quote
        elif not in_quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth < 0:
                    errors.append(f"Unbalanced closing parenthesis in {s!r}")
                    break
    if in_quote:
        errors.append(f"Unclosed single quote in {s!r}")
    if depth != 0:
        errors.append(f"Unbalanced parentheses (depth={depth}) in {s!r}")

    # 2. Validate skill('...') references
    for m in _SKILL_REF_RE.finditer(s):
        sk_name = m.group(1)
        if sk_name not in skills_by_name:
            errors.append(f"Unknown skill {sk_name!r} in skill() reference within {s!r}")

    # 3. Validate stat('...') references
    for m in _STAT_REF_RE.finditer(s):
        st_name = m.group(1)
        if st_name not in valid_stats:
            errors.append(f"Unknown stat {st_name!r} in stat() reference within {s!r}")

    # 4. Validate miss('...') references
    if missiles_by_name is not None:
        for m in _MISSILE_REF_RE.finditer(s):
            ms_name = m.group(1)
            if ms_name not in missiles_by_name:
                errors.append(f"Unknown missile {ms_name!r} in miss() reference within {s!r}")

    return errors


def _d2_linear(a: int, b: int, slvl: int) -> int:
    return a + max(0, slvl - 1) * b


def _d2_diminishing(a: int, b: int, slvl: int) -> int:
    if slvl <= 0:
        return 0
    return int(((110 * slvl) * (b - a)) // (100 * (slvl + 6)) + a)


def _d2_mastery(row: dict, prefix: str, slvl: int) -> int:
    if slvl <= 0:
        return 0
    base = int(row.get(prefix) or "0")
    l1 = int(row.get(f"{prefix}Lev1") or "0")
    l2 = int(row.get(f"{prefix}Lev2") or str(l1))
    l3 = int(row.get(f"{prefix}Lev3") or str(l2))
    l4 = int(row.get(f"{prefix}Lev4") or str(l3))
    l5 = int(row.get(f"{prefix}Lev5") or str(l4))
    val = base
    for s in range(2, slvl + 1):
        if s <= 8:
            val += l1
        elif s <= 16:
            val += l2
        elif s <= 22:
            val += l3
        elif s <= 28:
            val += l4
        else:
            val += l5
    return val


def _d2_elen(row: dict, slvl: int) -> int:
    if slvl <= 0:
        return 0
    base = int(row.get("ELen") or "0")
    l1 = int(row.get("ELevLen1") or "0")
    l2 = int(row.get("ELevLen2") or str(l1))
    l3 = int(row.get("ELevLen3") or str(l2))
    val = base
    for s in range(2, slvl + 1):
        if s <= 8:
            val += l1
        elif s <= 16:
            val += l2
        else:
            val += l3
    return val


class _Parser:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0

    def _skip_ws(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def parse(self) -> int:
        val = self._parse_ternary()
        return int(val)

    def _parse_ternary(self) -> int:
        cond = self._parse_or()
        self._skip_ws()
        if self.pos < len(self.text) and self.text[self.pos] == "?":
            self.pos += 1
            t_val = self._parse_ternary()
            self._skip_ws()
            if self.pos < len(self.text) and self.text[self.pos] == ":":
                self.pos += 1
                f_val = self._parse_ternary()
                return t_val if cond != 0 else f_val
        return cond

    def _parse_or(self) -> int:
        left = self._parse_and()
        while True:
            self._skip_ws()
            if self.text[self.pos : self.pos + 2] == "||":
                self.pos += 2
                right = self._parse_and()
                left = 1 if (left != 0 or right != 0) else 0
            elif self.pos < len(self.text) and self.text[self.pos] == "|" and self.text[self.pos : self.pos + 2] != "||":
                self.pos += 1
                right = self._parse_and()
                left = 1 if (left != 0 or right != 0) else 0
            else:
                break
        return left

    def _parse_and(self) -> int:
        left = self._parse_cmp()
        while True:
            self._skip_ws()
            if self.text[self.pos : self.pos + 2] == "&&":
                self.pos += 2
                right = self._parse_cmp()
                left = 1 if (left != 0 and right != 0) else 0
            elif self.pos < len(self.text) and self.text[self.pos] == "&" and self.text[self.pos : self.pos + 2] != "&&":
                self.pos += 1
                right = self._parse_cmp()
                left = 1 if (left != 0 and right != 0) else 0
            else:
                break
        return left

    def _parse_cmp(self) -> int:
        left = self._parse_add()
        while True:
            self._skip_ws()
            matched = False
            for op in ("==", "!=", "<=", ">=", "<", ">"):
                if self.text[self.pos : self.pos + len(op)] == op:
                    self.pos += len(op)
                    right = self._parse_add()
                    if op == "==":
                        left = 1 if left == right else 0
                    elif op == "!=":
                        left = 1 if left != right else 0
                    elif op == "<=":
                        left = 1 if left <= right else 0
                    elif op == ">=":
                        left = 1 if left >= right else 0
                    elif op == "<":
                        left = 1 if left < right else 0
                    elif op == ">":
                        left = 1 if left > right else 0
                    matched = True
                    break
            if not matched:
                break
        return left

    def _parse_add(self) -> int:
        left = self._parse_mul()
        while True:
            self._skip_ws()
            if self.pos < len(self.text) and self.text[self.pos] in "+-":
                op = self.text[self.pos]
                self.pos += 1
                right = self._parse_mul()
                left = (left + right) if op == "+" else (left - right)
            else:
                break
        return left

    def _parse_mul(self) -> int:
        left = self._parse_unary()
        while True:
            self._skip_ws()
            if self.pos < len(self.text) and self.text[self.pos] in "*/":
                op = self.text[self.pos]
                self.pos += 1
                right = self._parse_unary()
                if op == "*":
                    left = left * right
                else:
                    left = int(left / right) if right != 0 else 0
            else:
                break
        return left

    def _parse_unary(self) -> int:
        self._skip_ws()
        if self.pos < len(self.text) and self.text[self.pos] == "-":
            self.pos += 1
            return -self._parse_unary()
        if self.pos < len(self.text) and self.text[self.pos] == "+":
            self.pos += 1
            return self._parse_unary()
        if self.pos < len(self.text) and self.text[self.pos] == "!":
            self.pos += 1
            return 1 if self._parse_unary() == 0 else 0
        return self._parse_primary()

    def _parse_primary(self) -> int:
        self._skip_ws()
        if self.pos < len(self.text) and self.text[self.pos] == "(":
            self.pos += 1
            val = self._parse_ternary()
            self._skip_ws()
            if self.pos < len(self.text) and self.text[self.pos] == ")":
                self.pos += 1
            return val
        for fn in ("min", "max", "rand"):
            if self.text[self.pos : self.pos + len(fn) + 1] == f"{fn}(":
                self.pos += len(fn) + 1
                a = self._parse_ternary()
                self._skip_ws()
                b = a
                if self.pos < len(self.text) and self.text[self.pos] == ",":
                    self.pos += 1
                    b = self._parse_ternary()
                self._skip_ws()
                if self.pos < len(self.text) and self.text[self.pos] == ")":
                    self.pos += 1
                if fn == "min":
                    return min(a, b)
                if fn == "max":
                    return max(a, b)
                return (a + b) // 2
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self.pos += 1
        if self.pos > start:
            return int(self.text[start : self.pos])
        return 0


def eval_d2_expr(
    expr: str,
    row: dict,
    slvl: int = 1,
    blvl: Optional[int] = None,
    skill_levels: Optional[Dict[str, int]] = None,
    stats: Optional[Dict[str, int]] = None,
    skills_by_name: Optional[Dict[str, dict]] = None,
    _depth: int = 0,
) -> int:
    """
    Evaluate a D2R formula string for a given skill/missile row at (slvl, blvl, skill_levels, stats).
    Matches D2R integer truncation and supports recursive clc1..6 / par1..8 / ln / dm / skill() / stat() expansion.
    """
    if _depth > 8 or not expr:
        return 0
    s = expr.strip()
    if not s:
        return 0
    if blvl is None:
        blvl = slvl
    skill_levels = skill_levels or {}
    stats = stats or {}
    skills_by_name = skills_by_name or {}

    def _p(idx: int) -> int:
        val = (row.get(f"Param{idx}") or "").strip()
        return int(val) if val.lstrip("-").isdigit() else 0

    def _c(idx: int) -> int:
        sub = (row.get(f"calc{idx}") or "").strip()
        return eval_d2_expr(sub, row, slvl, blvl, skill_levels, stats, skills_by_name, _depth + 1)

    # Replace skill('Name'.prop)
    def _repl_skill(m: re.Match) -> str:
        sk_name, prop = m.group(1), m.group(2)
        sk_lvl = skill_levels.get(sk_name, slvl if sk_name == row.get("skill") else 0)
        if prop in ("lvl", "blvl"):
            return str(sk_lvl)
        target_row = skills_by_name.get(sk_name, {})
        if prop == "rng":
            rv = eval_d2_expr(
                target_row.get("aurarangecalc", ""),
                target_row,
                max(1, sk_lvl),
                sk_lvl,
                skill_levels,
                stats,
                skills_by_name,
                _depth + 1,
            )
            return str(rv)
        if prop == "len":
            lv = eval_d2_expr(
                target_row.get("auralencalc", ""),
                target_row,
                max(1, sk_lvl),
                sk_lvl,
                skill_levels,
                stats,
                skills_by_name,
                _depth + 1,
            )
            return str(lv)
        if prop.startswith("par"):
            p_idx = int(prop[3:])
            pv = (target_row.get(f"Param{p_idx}") or "0").strip()
            return pv if pv.lstrip("-").isdigit() else "0"
        if prop.startswith("clc"):
            c_idx = int(prop[3:])
            cv = eval_d2_expr(
                target_row.get(f"calc{c_idx}", ""),
                target_row,
                max(1, sk_lvl),
                sk_lvl,
                skill_levels,
                stats,
                skills_by_name,
                _depth + 1,
            )
            return str(cv)
        return "0"

    s = _SKILL_REF_RE.sub(_repl_skill, s)

    # Replace stat('name'.accr)
    def _repl_stat(m: re.Match) -> str:
        st_name = m.group(1)
        return str(stats.get(st_name, 0))

    s = _STAT_REF_RE.sub(_repl_stat, s)

    # Replace miss('Name'.prop)
    s = _MISSILE_REF_RE.sub("0", s)

    # Replace lnAB and dmAB
    def _repl_ln(m: re.Match) -> str:
        a, b = int(m.group(1)), int(m.group(2))
        return str(_d2_linear(_p(a), _p(b), slvl))

    def _repl_dm(m: re.Match) -> str:
        a, b = int(m.group(1)), int(m.group(2))
        return str(_d2_diminishing(_p(a), _p(b), slvl))

    s = re.sub(r"\bln(\d)(\d)\b", _repl_ln, s)
    s = re.sub(r"\bdm(\d)(\d)\b", _repl_dm, s)

    # Replace par1..8, clc1..6, lvl, blvl, ulvl, edmn, edmx, edln, edns, enma, ma1..3, sy1..2
    sy1_val = eval_d2_expr(
        row.get("EDmgSymPerCalc", ""), row, slvl, blvl, skill_levels, stats, skills_by_name, _depth + 1
    )
    sy2_val = eval_d2_expr(
        row.get("ELenSymPerCalc", ""), row, slvl, blvl, skill_levels, stats, skills_by_name, _depth + 1
    )
    edmn = _d2_mastery(row, "EMin", slvl)
    edmx = _d2_mastery(row, "EMax", slvl)
    edln = _d2_elen(row, slvl)

    token_map = {
        "lvl": str(slvl),
        "blvl": str(blvl),
        "ulvl": str(max(1, slvl * 2)),
        "edmn": str(edmn * (100 + sy1_val) // 100),
        "edmx": str(edmx * (100 + sy1_val) // 100),
        "edln": str(edln * (100 + sy2_val) // 100),
        "edns": str((edmn * (100 + sy1_val) // 100) * 25 // 256),
        "edxs": str((edmx * (100 + sy1_val) // 100) * 25 // 256),
        "enma": str(int(row.get("mana") or "0") + max(0, slvl - 1) * int(row.get("lvlmana") or "0")),
        "sy1": str(sy1_val),
        "sy2": str(sy2_val),
        "ToHit": str(int(row.get("ToHit") or "0") + max(0, slvl - 1) * int(row.get("LevToHit") or "0")),
    }
    for i in range(1, 9):
        token_map[f"par{i}"] = str(_p(i))
    for i in range(1, 7):
        if f"clc{i}" in s:
            token_map[f"clc{i}"] = str(_c(i))

    def _repl_tok(m: re.Match) -> str:
        tok = m.group(0)
        return token_map.get(tok, "0")

    s = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\b", lambda m: m.group(0) if m.group(0) in ("min", "max", "rand") else _repl_tok(m), s)
    return _Parser(s).parse()

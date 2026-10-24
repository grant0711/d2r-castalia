"""
monsters.py
Step 10: Monsters, Zones, Bosses, Mercenaries, Summon Equipment, Experience & Character Stats.
Generates:
  - levels.txt (Deterministic 3-monster rosters, no guest soup, 0.42x MonDen, 1 random Unique boss pack)
  - monstats.txt (4 Monster Archetypes, 9-Biome Resist/Weakness Matrix, 5 Capstone Bosses, 5 Baal Waves, Summon buffs)
  - monprop.txt (Boss & monster properties)
  - superuniques.txt (Solo-tuned Baal Throne waves & Superuniques)
  - monequip.txt (4-Tier Custom Unique Equipment for Valkyrie, Shadow Warrior, Shadow Master)
  - difficultylevels.txt (Merc/Pet boss damage multipliers, Static Field floors)
  - hireling.txt (4 Distinct Act Mercenary Identities, 9 Act 2 Auras, no curse-overwriting Barb skills)
  - experience.txt (Solo Level 1-99 ExpRatio curve)
  - charstats.txt (2 SkillsPerLevel, 2.5x LifePerLevel, 1.75x ManaPerMagic, tactical Stamina)
"""
from mod_builder.common import read_excel_tsv as read_tsv, write_excel_tsv as write_tsv


def parse_int(val: str, default: int = 0) -> int:
    val = str(val).strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def scale_int(val: str, mult: float, min_val: int = 1) -> str:
    v = str(val).strip()
    if not v:
        return ""
    try:
        n = int(v)
    except ValueError:
        return v
    if n <= 0:
        return str(n)
    return str(max(min_val, int(round(n * mult))))

# ============================================================================
# 1. LEVELS.TXT — Deterministic 3-Monster Rosters, Density & Boss Packs
# ============================================================================

# Curated 3-monster rosters for Act 2 Open Desert (Zero Poison, Zero Maggots, Zero Zombies)
CURATED_ZONE_ROSTERS = {
    "Act 2 - Desert 1": ["vulture1", "sandleaper1", "slinger1"],          # Rocky Waste
    "Act 2 - Desert 2": ["vulture2", "pantherwoman1", "slinger5"],        # Dry Hills
    "Act 2 - Desert 3": ["swarm1", "vulture2", "scarab2"],                # Far Oasis
    "Act 2 - Desert 4": ["sandraider2", "pantherwoman3", "slinger2"],     # Lost City
    "Act 2 - Desert 5": ["sandleaper3", "scarab4", "pantherwoman4"],      # Canyon of the Magi
    "Act 2 - Sewer 1 B": ["skeleton5", "mummy2", "zombie5"],              # Move Plague Bearer into Sewers
}

# Stationary nest/spawner -> mobile counterpart for umon1..3 (since nests can't spawn as Uniques)
UMON_REPLACEMENTS = {
    "crownest1": "foulcrow1",
    "crownest2": "foulcrow2",
    "crownest3": "foulcrow3",
    "crownest4": "foulcrow4",
    "suckernest1": "mosquito1",
    "suckernest2": "mosquito2",
    "suckernest3": "mosquito3",
    "suckernest4": "mosquito4",
    "sarcophagus": "mummy2",
    "evilhut": "imp1",
    "minionspawner1": "minion1",
    "minionspawner2": "minion2",
    "minionspawner3": "minion3",
    "minionspawner4": "minion4",
    "minionspawner5": "minion5",
    "minionspawner6": "minion6",
    "minionspawner7": "minion7",
    "minionspawner8": "minion8",
}

FIXED_SKIP_ZONE_IDS = {"0", "1", "40", "75", "103", "109", "120", "133", "134", "135", "136"}


def build_levels(cfg: dict) -> str:
    headers, rows = read_tsv("levels.txt")
    for row in rows:
        name = row.get("Name", "")
        zid = row.get("Id", "")
        if not name or name == "Expansion" or zid in FIXED_SKIP_ZONE_IDS:
            continue

        monden_n = parse_int(row.get("MonDen(N)", ""))
        if monden_n <= 0:
            continue

        # Special handling for Moo Moo Farm (keep 1 monster: hellbovine)
        if name == "Act 1 - Moo Moo Farm":
            row["NumMon"] = "1"
            for d_col in ("MonDen", "MonDen(N)", "MonDen(H)"):
                val = parse_int(row.get(d_col, ""))
                if val > 0:
                    row[d_col] = str(max(240, int(round(val * 0.45))))
            for u_col in ("MonUMin", "MonUMax", "MonUMin(N)", "MonUMax(N)", "MonUMin(H)", "MonUMax(H)"):
                row[u_col] = "1"
            continue

        # 1. Deterministic 3-monster roster across Normal, Nightmare, and Hell (No Guest Soup)
        if name in CURATED_ZONE_ROSTERS:
            roster = list(CURATED_ZONE_ROSTERS[name])
        else:
            seen = []
            for i in range(1, 26):
                m = row.get(f"mon{i}", "").strip()
                if m and m not in seen:
                    seen.append(m)
            # If fewer than 3 in mon, pull from nmon
            for i in range(1, 26):
                if len(seen) >= 3:
                    break
                m = row.get(f"nmon{i}", "").strip()
                if m and m not in seen:
                    seen.append(m)
            roster = seen[:3]

        if roster:
            row["NumMon"] = str(len(roster))
            for i in range(1, 26):
                if i <= len(roster):
                    m = roster[i - 1]
                    row[f"mon{i}"] = m
                    row[f"nmon{i}"] = m
                    row[f"umon{i}"] = UMON_REPLACEMENTS.get(m, m)
                else:
                    row[f"mon{i}"] = ""
                    row[f"nmon{i}"] = ""
                    row[f"umon{i}"] = ""

        # 2. Scale Monster Density (~0.42x) for tactical solo pacing
        for d_col in ("MonDen", "MonDen(N)", "MonDen(H)"):
            val = parse_int(row.get(d_col, ""))
            if val > 0:
                row[d_col] = str(max(180, int(round(val * 0.42))))
            elif d_col == "MonDen" and name == "Act 5 - Siege 1":
                row[d_col] = "270"

        # 3. Strictly 1 Random Unique Boss Pack per combat zone
        for u_col in ("MonUMin", "MonUMax", "MonUMin(N)", "MonUMax(N)", "MonUMin(H)", "MonUMax(H)"):
            if parse_int(row.get(u_col, "")) > 0 or name == "Act 5 - Siege 1":
                row[u_col] = "1"

    return write_tsv("levels.txt", headers, rows)


# ============================================================================
# 2. MONSTATS.TXT, MONPROP.TXT & SUPERUNIQUES.TXT
# ============================================================================

HEAVY_BRUTE_BASES = {
    "brute2", "blunderbore1", "thornhulk1", "regurgitator1",
    "megademon1", "siegebeast1", "snowyeti1", "frozenhorror1", "hellbovine",
}

SWARMER_BASES = {
    "fallen1", "quillrat1", "foulcrow1", "sandleaper1", "swarm1",
    "scarab1", "vulture1", "mosquito1", "fetish1", "fetishblow1",
    "bonefetish1", "arach1", "frogdemon1", "vilechild1", "painworm1",
    "imp1", "minion1",
}

ARCANE_CASTER_BASES = {
    "fallenshaman1", "wraith1", "unraveler1", "willowisp1", "vampire1",
    "cantor1", "fetishshaman1", "skmage_pois1", "skmage_cold1",
    "skmage_fire1", "skmage_ltng1", "fingermage1", "vilemother1",
    "succubus1", "succubuswitch1", "putriddefiler1", "doomknight3",
}

# Family-wide elemental profile:
#   "weak": {res_type: normal_weakness_val} (scales up in NM and Hell so N < NM < H)
#   "strong": primary thematic element(s) for earlier immunity stretching when suited to the biome/family
FAMILY_RESIST_PROFILES = {
    # Act 1 / Undead / Construct / Beasts
    "skeleton1":       {"weak": {"Fi": -35, "Ma": -30}, "strong": ("Po", "Co")},
    "sk_archer1":      {"weak": {"Fi": -35, "Ma": -30}, "strong": ("Po", "Co")},
    "skmage_pois1":    {"weak": {"Fi": -40, "Dm": -20}, "strong": ("Po", "Ma")},
    "skmage_cold1":    {"weak": {"Fi": -40, "Dm": -20}, "strong": ("Co", "Po")},
    "skmage_fire1":    {"weak": {"Co": -40, "Dm": -20}, "strong": ("Fi", "Po")},
    "skmage_ltng1":    {"weak": {"Po": -35, "Dm": -20}, "strong": ("Li", "Ma")},
    "zombie1":         {"weak": {"Fi": -45, "Li": -30}, "strong": ("Po", "Co")},
    "fallen1":         {"weak": {"Co": -40, "Li": -30}, "strong": ("Fi",)},
    "fallenshaman1":   {"weak": {"Co": -40, "Dm": -25}, "strong": ("Fi", "Ma")},
    "quillrat1":       {"weak": {"Fi": -35, "Co": -30}, "strong": ("Po",)},
    "foulcrow1":       {"weak": {"Li": -40, "Fi": -30}, "strong": ("Co",)},
    "corruptrogue1":   {"weak": {"Po": -35, "Co": -30}, "strong": ("Fi", "Li")},
    "cr_archer1":      {"weak": {"Po": -35, "Dm": -20}, "strong": ("Fi", "Co")},
    "cr_lancer1":      {"weak": {"Po": -35, "Li": -30}, "strong": ("Co", "Fi")},
    "goatman1":        {"weak": {"Po": -35, "Co": -30}, "strong": ("Fi", "Li")},
    "brute2":          {"weak": {"Li": -40, "Fi": -35}, "strong": ("Co", "Dm")},
    "wraith1":         {"weak": {"Fi": -35, "Li": -30}, "strong": ("Dm", "Ma", "Po")},
    "bighead1":        {"weak": {"Co": -35, "Po": -30}, "strong": ("Li",)},
    "arach1":          {"weak": {"Fi": -40, "Co": -30}, "strong": ("Po",)},
    "vampire1":        {"weak": {"Fi": -40, "Li": -30}, "strong": ("Co", "Ma", "Po")},
    "fetish1":         {"weak": {"Co": -35, "Fi": -30}, "strong": ("Po",)},
    "fetishblow1":     {"weak": {"Co": -35, "Dm": -20}, "strong": ("Po",)},
    "fetishshaman1":   {"weak": {"Co": -40, "Dm": -20}, "strong": ("Fi", "Ma")},
    "bonefetish1":     {"weak": {"Fi": -40, "Ma": -30}, "strong": ("Po", "Co")},
    # Act 2 Desert / Tombs
    "sandleaper1":     {"weak": {"Co": -40, "Fi": -30}, "strong": ("Li",)},
    "pantherwoman1":   {"weak": {"Co": -35, "Po": -30}, "strong": ("Fi", "Li")},
    "slinger1":        {"weak": {"Co": -35, "Dm": -20}, "strong": ("Fi", "Li")},
    "slinger5":        {"weak": {"Co": -35, "Dm": -20}, "strong": ("Fi", "Po")},
    "vulture1":        {"weak": {"Li": -40, "Co": -30}, "strong": ("Fi",)},
    "swarm1":          {"weak": {"Fi": -45, "Co": -35}, "strong": ("Po", "Dm")},
    "scarab1":         {"weak": {"Co": -40, "Fi": -30}, "strong": ("Li", "Po")},
    "sandraider1":     {"weak": {"Co": -35, "Li": -30}, "strong": ("Fi",)},
    "sandmaggot1":     {"weak": {"Fi": -40, "Li": -35}, "strong": ("Po",)},
    "clawviper1":      {"weak": {"Fi": -35, "Po": -30}, "strong": ("Co", "Li")},
    "mummy1":          {"weak": {"Fi": -45, "Li": -30}, "strong": ("Po", "Co")},
    "unraveler1":      {"weak": {"Fi": -40, "Dm": -20}, "strong": ("Ma", "Po")},
    "baboon1":         {"weak": {"Po": -35, "Li": -30}, "strong": ("Fi", "Co")},
    "blunderbore1":    {"weak": {"Li": -40, "Ma": -30}, "strong": ("Dm", "Co")},
    "batdemon1":       {"weak": {"Co": -40, "Fi": -30}, "strong": ("Li",)},
    # Act 3 Jungle / Kurast / Zakarum
    "mosquito1":       {"weak": {"Fi": -40, "Li": -35}, "strong": ("Po",)},
    "thornhulk1":      {"weak": {"Fi": -45, "Po": -30}, "strong": ("Dm", "Co")},
    "frogdemon1":      {"weak": {"Li": -40, "Co": -35}, "strong": ("Po", "Fi")},
    "willowisp1":      {"weak": {"Dm": -25, "Fi": -35}, "strong": ("Li", "Po")},
    "zealot1":         {"weak": {"Li": -35, "Po": -35}, "strong": ("Ma", "Fi")},
    "cantor1":         {"weak": {"Po": -40, "Dm": -20}, "strong": ("Ma", "Co", "Li")},
    "councilmember1":  {"weak": {"Co": -35, "Po": -30}, "strong": ("Fi", "Li", "Ma")},
    # Act 4 Hell
    "vilemother1":     {"weak": {"Fi": -40, "Li": -35}, "strong": ("Po", "Co")},
    "vilechild1":      {"weak": {"Fi": -40, "Li": -35}, "strong": ("Po", "Co")},
    "fingermage1":     {"weak": {"Dm": -25, "Co": -35}, "strong": ("Ma", "Li")},
    "regurgitator1":   {"weak": {"Li": -40, "Ma": -30}, "strong": ("Po", "Dm")},
    "doomknight1":     {"weak": {"Li": -35, "Ma": -30}, "strong": ("Fi", "Po")},
    "doomknight2":     {"weak": {"Co": -35, "Dm": -20}, "strong": ("Li", "Fi")},
    "doomknight3":     {"weak": {"Dm": -25, "Li": -30}, "strong": ("Co", "Ma", "Po")},
    "megademon1":      {"weak": {"Co": -40, "Ma": -30}, "strong": ("Fi", "Po")},
    # Act 5 Highlands / Ice Caves / Worldstone
    "reanimatedhorde1":{"weak": {"Fi": -45, "Li": -30}, "strong": ("Co", "Po")},
    "siegebeast1":     {"weak": {"Li": -40, "Ma": -35}, "strong": ("Fi", "Dm")},
    "snowyeti1":       {"weak": {"Fi": -45, "Li": -30}, "strong": ("Co",)},
    "frozenhorror1":   {"weak": {"Fi": -45, "Li": -35}, "strong": ("Co",)},
    "minion1":         {"weak": {"Co": -35, "Li": -30}, "strong": ("Fi", "Co")},
    "suicideminion1":  {"weak": {"Co": -40, "Li": -35}, "strong": ("Fi", "Co")},
    "succubus1":       {"weak": {"Dm": -20, "Li": -35}, "strong": ("Fi", "Ma")},
    "succubuswitch1":  {"weak": {"Dm": -25, "Li": -35}, "strong": ("Ma", "Fi", "Co")},
    "overseer1":       {"weak": {"Co": -35, "Ma": -30}, "strong": ("Fi", "Li")},
    "imp1":            {"weak": {"Co": -40, "Li": -35}, "strong": ("Fi",)},
    "bloodlord1":      {"weak": {"Ma": -35, "Li": -30}, "strong": ("Dm", "Fi", "Co")},
    "deathmauler1":    {"weak": {"Fi": -35, "Ma": -30}, "strong": ("Li", "Co")},
    "putriddefiler1":  {"weak": {"Fi": -40, "Co": -35}, "strong": ("Po", "Ma")},
    "painworm1":       {"weak": {"Fi": -40, "Co": -35}, "strong": ("Po",)},
    "hellbovine":      {"weak": {"Fi": -35, "Li": -35}, "strong": ("Dm",)},
}

# Families that gain Magic Immunity (ResMa = 100) in Hell (and high Magic Res in NM)
HELL_MAGIC_IMMUNE_BASES = {
    "unraveler1", "wraith1", "cantor1", "succubuswitch1", "doomknight3",
}


def _scale_weakness_by_diff(base_w: int, diff_suffix: str, is_phys_or_mag: bool) -> int:
    """
    Ensure Normal < Nightmare < Hell for all negative resistances:
      - Elemental Weakness (e.g. -40 in Normal):
          Normal:    -40%
          Nightmare: -25% (+15%)
          Hell:      -10% (+30%)
      - Physical/Magic Weakness (e.g. -25 in Normal):
          Normal:    -25%
          Nightmare: -15% (+10%)
          Hell:       -5% (+20%)
    """
    if diff_suffix == "":
        return base_w
    if diff_suffix == "(N)":
        step = 10 if is_phys_or_mag else 15
        return min(-10 if is_phys_or_mag else -15, base_w + step)
    # Hell "(H)"
    step = 20 if is_phys_or_mag else 25
    return min(-5 if is_phys_or_mag else -10, base_w + step)


def _apply_weaknesses_and_magic_imm(row: dict, base_id: str) -> None:
    profile = FAMILY_RESIST_PROFILES.get(base_id, {"weak": {}, "strong": ()})
    weaknesses = profile["weak"]
    strong_elems = profile["strong"]
    all_res = ("Dm", "Ma", "Fi", "Li", "Co", "Po")

    orig_res = {
        diff: {r: parse_int(row.get(f"Res{r}{diff}", "")) for r in all_res}
        for diff in ("", "(N)", "(H)")
    }

    for diff_suffix in ("", "(N)", "(H)"):
        # Count existing immunities (>= 100) in this difficulty
        imm_count = sum(
            1 for r in all_res if orig_res[diff_suffix][r] >= 100
        )
        max_imm = 1 if diff_suffix in ("", "(N)") else 2

        for rtype in all_res:
            col = f"Res{rtype}{diff_suffix}"
            cur = orig_res[diff_suffix][rtype]
            normal_cur = orig_res[""][rtype]
            is_pm = rtype in ("Dm", "Ma")

            # 1. Keep native immunities (>= 100) intact
            if cur >= 100:
                continue

            # 2. If this element is one of the family's designated weaknesses AND this specific monster
            #    is not an elemental sub-variant of that element (normal_cur < 50 and cur < 100):
            if rtype in weaknesses and normal_cur < 50:
                w_val = _scale_weakness_by_diff(weaknesses[rtype], diff_suffix, is_pm)
                row[col] = str(w_val)
                continue

            # 3. Stretch positive / thematic resistances upward so immunities appear earlier when suited to the biome,
            #    and neutral resistances climb progressively from Normal -> Nightmare -> Hell
            is_thematic = (rtype in strong_elems) or (cur >= 33)
            if diff_suffix == "":
                # Normal: stretch high thematic resists (>= 70) to 100% Immune (max 1 immunity),
                # moderate thematic resists (33..69) to 65..85%, and keep neutrals at 0..15%
                if is_thematic and cur >= 70 and imm_count < max_imm and rtype != "Dm":
                    row[col] = "100"
                    imm_count += 1
                elif is_thematic and cur >= 40:
                    row[col] = str(min(85, cur + 20))
                elif rtype in strong_elems and cur > 0:
                    row[col] = str(min(75, cur + 25))
            elif diff_suffix == "(N)":
                # Nightmare: stretch thematic resists (>= 55, or >= 40 in primary strong_elems) to 100% Immune (max 1 immunity),
                # moderate thematic resists to 75..85%, and neutral elements to 25..35%
                if (
                    ((rtype in strong_elems and cur >= 45) or cur >= 60)
                    and imm_count < max_imm
                    and rtype != "Dm"
                ):
                    row[col] = "100"
                    imm_count += 1
                elif is_thematic and cur >= 25:
                    row[col] = str(min(85, max(65, cur + 25)))
                elif rtype in strong_elems:
                    row[col] = str(max(50, cur + 35))
                else:
                    # Neutral resistance in Nightmare: 20% (Dm/Ma) or 25% (Elemental)
                    floor_nm = 15 if is_pm else 25
                    row[col] = str(max(cur + 15, floor_nm))
            else:
                # Hell "(H)": stretch thematic resists (>= 60 or strong_elems >= 50) to 100% Immune (up to 2 immunities),
                # and raise neutral resistances to 50..65% (33..45% for Dm/Ma) so non-weakness hits face stiff resistance
                if (
                    ((rtype in strong_elems and cur >= 50) or cur >= 65)
                    and imm_count < max_imm
                    and rtype != "Dm"
                ):
                    row[col] = "100"
                    imm_count += 1
                elif is_thematic and cur >= 33:
                    row[col] = str(min(90, max(75, cur + 25)))
                else:
                    floor_h = 33 if is_pm else 50
                    row[col] = str(min(85, max(cur + 25, floor_h)))

    # Add Magic Immunity to select Arcane/Undead/Zakarum casters in Hell (and 75% Magic Res in NM)
    if base_id in HELL_MAGIC_IMMUNE_BASES:
        if parse_int(row.get("ResMa(N)", "")) < 75:
            row["ResMa(N)"] = "75"
        imm_count_h = sum(
            1 for r in all_res if parse_int(row.get(f"Res{r}(H)", "")) >= 100
        )
        if imm_count_h < 2:
            row["ResMa(H)"] = "100"


def _configure_capstone_bosses(row: dict, mon_id: str) -> bool:
    if mon_id == "andariel":
        row["Level"], row["Level(N)"], row["Level(H)"] = "14", "49", "76"
        row["Velocity"], row["Run"] = "7", "7"
        row["MonProp"] = "andariel"
        row["ToBlock"], row["ToBlock(N)"], row["ToBlock(H)"] = "0", "10", "15"
        # Progressive resists (N < NM < H):
        # Fire weakness: -50% (N) -> -35% (NM) -> -20% (H)
        # Phys weakness: -20% (N) -> -15% (NM) -> -10% (H)
        row["ResDm"], row["ResDm(N)"], row["ResDm(H)"] = "-20", "-15", "-10"
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "10", "25", "45"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "-50", "-35", "-20"
        row["ResLi"], row["ResLi(N)"], row["ResLi(H)"] = "35", "55", "75"
        row["ResCo"], row["ResCo(N)"], row["ResCo(H)"] = "35", "55", "75"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "80", "90", "95"
        for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            row[col] = scale_int(row[col], 1.75)
        for col in ("A1MinD", "A1MaxD", "A1MinD(N)", "A1MaxD(N)", "A1MinD(H)", "A1MaxD(H)"):
            row[col] = scale_int(row[col], 1.35)
        row["Exp"] = "28000"
        row["Exp(N)"] = scale_int(row["Exp(N)"], 28.0)
        row["Exp(H)"] = scale_int(row["Exp(H)"], 28.0)
        return True

    if mon_id == "duriel":
        row["Level"], row["Level(N)"], row["Level(H)"] = "21", "55", "84"
        # Weakness 1: Reduced movement speed so solo players can kite after his charge
        row["Velocity"], row["Run"] = "7", "10"
        row["MonProp"] = "duriel"
        row["ToBlock"], row["ToBlock(N)"], row["ToBlock(H)"] = "0", "0", "0"
        # Strengths: Holy Freeze (Sk4lvl=4), 50% Crushing Blow, 80/90/95 Cold Res, 35/45/55 Phys Res
        # Weaknesses: Fire & Ltng Res -35% (N) -> -25% (NM) -> -15% (H)
        row["Sk4lvl"] = "4"
        row["ResDm"], row["ResDm(N)"], row["ResDm(H)"] = "35", "45", "55"
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "20", "35", "50"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "-35", "-25", "-15"
        row["ResLi"], row["ResLi(N)"], row["ResLi(H)"] = "-35", "-25", "-15"
        row["ResCo"], row["ResCo(N)"], row["ResCo(H)"] = "80", "90", "95"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "45", "65", "80"
        for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            row[col] = scale_int(row[col], 1.70)
        for col in ("A1MinD", "A1MaxD", "A2MinD", "A2MaxD", "A1MinD(N)", "A1MaxD(N)", "A2MinD(N)", "A2MaxD(N)", "A1MinD(H)", "A1MaxD(H)", "A2MinD(H)", "A2MaxD(H)"):
            row[col] = scale_int(row[col], 1.30)
        row["Exp"] = "52000"
        row["Exp(N)"] = scale_int(row["Exp(N)"], 28.0)
        row["Exp(H)"] = scale_int(row["Exp(H)"], 28.0)
        return True

    if mon_id == "mephisto":
        row["Level"], row["Level(N)"], row["Level(H)"] = "26", "59", "87"
        row["MonProp"] = "mephisto"
        row["ToBlock"], row["ToBlock(N)"], row["ToBlock(H)"] = "0", "0", "0"
        # Strengths: +35% FCR/IAS, 75/85/90 Ltng & Cold Res, 70/80/90 Poison Res
        # Weaknesses: Phys Res -25% -> -15% -> -10% (0% Block), Fire & Magic Res -35% -> -25% -> -15%
        row["ResDm"], row["ResDm(N)"], row["ResDm(H)"] = "-25", "-15", "-10"
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "-35", "-25", "-15"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "-35", "-25", "-15"
        row["ResLi"], row["ResLi(N)"], row["ResLi(H)"] = "75", "85", "90"
        row["ResCo"], row["ResCo(N)"], row["ResCo(H)"] = "75", "85", "90"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "70", "80", "90"
        for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            row[col] = scale_int(row[col], 1.80)
        for col in ("A1MinD", "A1MaxD", "A1MinD(N)", "A1MaxD(N)", "A1MinD(H)", "A1MaxD(H)"):
            row[col] = scale_int(row[col], 1.35)
        row["Exp"] = "76000"
        row["Exp(N)"] = scale_int(row["Exp(N)"], 28.0)
        row["Exp(H)"] = scale_int(row["Exp(H)"], 28.0)
        return True

    if mon_id == "diablo":
        row["Level"], row["Level(N)"], row["Level(H)"] = "32", "63", "92"
        row["Velocity"], row["Run"] = "8", "10"
        row["MonProp"] = "diablo"
        row["ToBlock"], row["ToBlock(N)"], row["ToBlock(H)"] = "0", "10", "15"
        # Strengths: 75/85/90 Fire & 70/80/85 Ltng Res, 35% Deadly Strike, 25/35/45 Phys Res
        # Weaknesses: Cold Res -35% -> -25% -> -15%, Magic Res -30% -> -20% -> -10%
        row["ResDm"], row["ResDm(N)"], row["ResDm(H)"] = "25", "35", "45"
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "-30", "-20", "-10"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "75", "85", "90"
        row["ResLi"], row["ResLi(N)"], row["ResLi(H)"] = "70", "80", "85"
        row["ResCo"], row["ResCo(N)"], row["ResCo(H)"] = "-35", "-25", "-15"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "45", "60", "75"
        for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            row[col] = scale_int(row[col], 1.85)
        for col in ("A1MinD", "A1MaxD", "A2MinD", "A2MaxD", "A1MinD(N)", "A1MaxD(N)", "A2MinD(N)", "A2MaxD(N)", "A1MinD(H)", "A1MaxD(H)", "A2MinD(H)", "A2MaxD(H)"):
            row[col] = scale_int(row[col], 1.35)
        row["Exp"] = "116000"
        row["Exp(N)"] = scale_int(row["Exp(N)"], 28.0)
        row["Exp(H)"] = scale_int(row["Exp(H)"], 28.0)
        return True

    if mon_id == "baalcrab":
        row["Level"], row["Level(N)"], row["Level(H)"] = "42", "75", "99"
        row["MonProp"] = "baalcrab"
        row["ToBlock"], row["ToBlock(N)"], row["ToBlock(H)"] = "0", "10", "15"
        # Strengths: 55/65/75 Fire/Cold/Magic Res, 40% Open Wounds, 1.85x HP
        # Weaknesses: Phys Res -15% -> -10% -> 0%, Ltng & Pois Res -30% -> -20% -> -10%
        row["ResDm"], row["ResDm(N)"], row["ResDm(H)"] = "-15", "-10", "0"
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "55", "65", "75"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "55", "65", "75"
        row["ResLi"], row["ResLi(N)"], row["ResLi(H)"] = "-30", "-20", "-10"
        row["ResCo"], row["ResCo(N)"], row["ResCo(H)"] = "55", "65", "75"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "-30", "-20", "-10"
        for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            row[col] = scale_int(row[col], 1.85)
        for col in ("A1MinD", "A1MaxD", "A2MinD", "A2MaxD", "A1MinD(N)", "A1MaxD(N)", "A2MinD(N)", "A2MaxD(N)", "A1MinD(H)", "A1MaxD(H)", "A2MinD(H)", "A2MaxD(H)"):
            row[col] = scale_int(row[col], 1.35)
        row["Exp"] = "180000"
        row["Exp(N)"] = scale_int(row["Exp(N)"], 28.0)
        row["Exp(H)"] = scale_int(row["Exp(H)"], 28.0)
        return True

    return False


def _configure_baal_wave_monsters(row: dict, mon_id: str) -> bool:
    if mon_id not in ("unraveler5", "baalhighpriest", "venomlord", "baalminion1", "baalminion2", "baalminion3"):
        return False

    for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
        row[col] = scale_int(row[col], 2.10)
    for col in (
        "A1MinD", "A1MaxD", "A2MinD", "A2MaxD",
        "A1MinD(N)", "A1MaxD(N)", "A2MinD(N)", "A2MaxD(N)",
        "A1MinD(H)", "A1MaxD(H)", "A2MinD(H)", "A2MaxD(H)",
    ):
        if row.get(col, ""):
            row[col] = scale_int(row[col], 1.40)
    for col in ("Exp", "Exp(N)", "Exp(H)"):
        row[col] = scale_int(row[col], 4.8)

    # Progressive N -> NM -> H weaknesses & stretched strengths on Baal Throne Waves
    if mon_id == "unraveler5":
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "-40", "-25", "-15"
        row["ResDm"], row["ResDm(N)"], row["ResDm(H)"] = "-20", "-10", "-5"
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "75", "100", "100"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "75", "90", "100"
    elif mon_id == "baalhighpriest":
        row["ResCo"], row["ResCo(N)"], row["ResCo(H)"] = "-35", "-20", "-10"
        row["ResDm"], row["ResDm(N)"], row["ResDm(H)"] = "-20", "-10", "-5"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "65", "85", "100"
        row["ResLi"], row["ResLi(N)"], row["ResLi(H)"] = "65", "85", "95"
    elif mon_id == "venomlord":
        row["ResCo"], row["ResCo(N)"], row["ResCo(H)"] = "-40", "-25", "-15"
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "-30", "-20", "-10"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "80", "100", "100"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "75", "95", "100"
    elif mon_id in ("baalminion1", "baalminion2", "baalminion3"):
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "-35", "-20", "-10"
        row["ResLi"], row["ResLi(N)"], row["ResLi(H)"] = "-30", "-20", "-10"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "60", "95", "120"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "95", "95", "95"
    return True


def _configure_player_summons(row: dict, mon_id: str) -> bool:
    if mon_id in ("spiritwolf", "fenris", "druidbear"):
        row["Velocity"] = str(parse_int(row.get("Velocity", "9")) + 2)
        row["Run"] = str(parse_int(row.get("Run", "13")) + 2)
        for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            row[col] = scale_int(row[col], 1.35)
        for col in ("A1TH", "A1TH(N)", "A1TH(H)"):
            if row.get(col, ""):
                row[col] = scale_int(row[col], 1.40)
        for suffix in ("", "(N)", "(H)"):
            row[f"ResFi{suffix}"] = "50"
            row[f"ResLi{suffix}"] = "50"
            row[f"ResCo{suffix}"] = "50"
            row[f"ResPo{suffix}"] = "50"
        return True

    if mon_id in ("spiritofbarbs", "heartofwolverine", "oaksage"):
        row["Velocity"] = "10"
        row["Run"] = "14"
        for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            row[col] = scale_int(row[col], 2.50)
        for suffix in ("", "(N)", "(H)"):
            row[f"ResDm{suffix}"] = "75"
            row[f"ResMa{suffix}"] = "75"
            row[f"ResFi{suffix}"] = "75"
            row[f"ResLi{suffix}"] = "75"
            row[f"ResCo{suffix}"] = "75"
            row[f"ResPo{suffix}"] = "100"
        return True

    if mon_id in ("plaguepoppy", "cycleoflife", "vinecreature"):
        row["Velocity"] = "10"
        row["Run"] = "14"
        for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            row[col] = scale_int(row[col], 3.00)
        for suffix in ("", "(N)", "(H)"):
            row[f"ResDm{suffix}"] = "75"
            row[f"ResMa{suffix}"] = "75"
            row[f"ResFi{suffix}"] = "75"
            row[f"ResLi{suffix}"] = "75"
            row[f"ResCo{suffix}"] = "75"
            row[f"ResPo{suffix}"] = "100"
        return True

    if mon_id == "necromage":
        for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            row[col] = scale_int(row[col], 2.00)
        for suffix in ("", "(N)", "(H)"):
            row[f"ResFi{suffix}"] = "50"
            row[f"ResLi{suffix}"] = "50"
            row[f"ResCo{suffix}"] = "50"
            row[f"ResPo{suffix}"] = "75"
        return True

    if mon_id in ("valkyrie", "shadowwarrior", "shadowmaster"):
        row["Velocity"] = "11"
        row["Run"] = "15"
        for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            row[col] = scale_int(row[col], 1.35)
        return True

    return False


def build_monstats(cfg: dict) -> str:
    headers, rows = read_tsv("monstats.txt")
    for row in rows:
        mon_id = row.get("Id", "").strip()
        if not mon_id or mon_id == "Expansion":
            continue

        # 1. Capstone Bosses
        if _configure_capstone_bosses(row, mon_id):
            continue

        # 2. Solo-Tuned Baal Throne Room Wave Monsters
        if _configure_baal_wave_monsters(row, mon_id):
            continue

        # 3. Player Summons
        if _configure_player_summons(row, mon_id):
            continue

        # 4. Regular Spawnable Enemy Monsters
        if (
            row.get("isSpawn", "") != "1"
            or row.get("killable", "") != "1"
            or row.get("Align", "") != ""
            or row.get("boss", "") == "1"
            or row.get("primeevil", "") == "1"
        ):
            continue

        base_id = row.get("BaseId", "").strip()
        vel = parse_int(row.get("Velocity", "0"))
        if vel <= 0:
            # Stationary nests/spawners: scale HP by 1.5x and XP by 2.4x
            for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
                row[col] = scale_int(row[col], 1.50)
            for col in ("Exp", "Exp(N)", "Exp(H)"):
                row[col] = scale_int(row[col], 2.40)
            continue

        # Remove Open Desert Poison from Sand Leapers (sandleaper1..3)
        if mon_id in ("sandleaper1", "sandleaper2", "sandleaper3") and row.get("El1Type", "") == "pois":
            for c in (
                "El1Mode", "El1Type", "El1Pct", "El1MinD", "El1MaxD", "El1Dur",
                "El1Pct(N)", "El1MinD(N)", "El1MaxD(N)", "El1Dur(N)",
                "El1Pct(H)", "El1MinD(H)", "El1MaxD(H)", "El1Dur(H)",
            ):
                row[c] = ""

        # Classify into 4 Archetypes
        if base_id in HEAVY_BRUTE_BASES:
            row["MinGrp"], row["MaxGrp"] = "1", "2"
            if parse_int(row.get("PartyMin", "")) > 0:
                row["PartyMin"], row["PartyMax"] = "1", "1"
            row["Velocity"] = str(max(3, vel - 1))
            hp_mult, dmg_mult, ar_mult = 2.80, 1.50, 1.30
        elif base_id in SWARMER_BASES:
            row["MinGrp"], row["MaxGrp"] = "3", "5"
            if parse_int(row.get("PartyMin", "")) > 0:
                row["PartyMin"], row["PartyMax"] = "2", "3"
            row["Velocity"] = str(min(15, vel + 1))
            if parse_int(row.get("Run", "")) > 0:
                row["Run"] = str(min(18, parse_int(row["Run"]) + 1))
            hp_mult, dmg_mult, ar_mult = 1.85, 1.30, 1.25
        elif base_id in ARCANE_CASTER_BASES:
            row["MinGrp"], row["MaxGrp"] = "1", "2"
            if parse_int(row.get("PartyMin", "")) > 0:
                row["PartyMin"], row["PartyMax"] = "2", "3"
            hp_mult, dmg_mult, ar_mult = 2.10, 1.45, 1.30
        else:
            # Elite Infantry
            row["MinGrp"], row["MaxGrp"] = "2", "3"
            if parse_int(row.get("PartyMin", "")) > 0:
                row["PartyMin"], row["PartyMax"] = "1", "2"
            hp_mult, dmg_mult, ar_mult = 2.40, 1.40, 1.35

        # Scale HP
        for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            row[col] = scale_int(row[col], hp_mult)

        # Scale Physical, Skill & Elemental Damage
        for col in (
            "A1MinD", "A1MaxD", "A2MinD", "A2MaxD", "S1MinD", "S1MaxD",
            "A1MinD(N)", "A1MaxD(N)", "A2MinD(N)", "A2MaxD(N)", "S1MinD(N)", "S1MaxD(N)",
            "A1MinD(H)", "A1MaxD(H)", "A2MinD(H)", "A2MaxD(H)", "S1MinD(H)", "S1MaxD(H)",
            "El1MinD", "El1MaxD", "El1MinD(N)", "El1MaxD(N)", "El1MinD(H)", "El1MaxD(H)",
            "El2MinD", "El2MaxD", "El2MinD(N)", "El2MaxD(N)", "El2MinD(H)", "El2MaxD(H)",
        ):
            if row.get(col, ""):
                row[col] = scale_int(row[col], dmg_mult)

        # Scale Attack Rating
        for col in (
            "A1TH", "A2TH", "S1TH",
            "A1TH(N)", "A2TH(N)", "S1TH(N)",
            "A1TH(H)", "A2TH(H)", "S1TH(H)",
        ):
            if row.get(col, ""):
                row[col] = scale_int(row[col], ar_mult)

        # Scale Experience (3.84x — reduced 20% from 4.80x)
        xp_mult = float(cfg.get("pacing", {}).get("normal_monster_xp_multiplier", 3.84))
        for col in ("Exp", "Exp(N)", "Exp(H)"):
            row[col] = scale_int(row[col], xp_mult)

        # Apply Biome Weaknesses & Hell Magic Immunities
        _apply_weaknesses_and_magic_imm(row, base_id)

    return write_tsv("monstats.txt", headers, rows)


def build_monprop(cfg: dict) -> str:
    headers, rows = read_tsv("monprop.txt")
    by_id = {r.get("Id", ""): r for r in rows}

    def ensure_row(mid: str) -> dict:
        if mid not in by_id:
            nr = {h: "" for h in headers}
            nr["Id"] = mid
            nr["*eol"] = "0"
            rows.append(nr)
            by_id[mid] = nr
        return by_id[mid]

    # Andariel: +35% IAS across N/NM/H
    r_andy = ensure_row("andariel")
    for sfx in ("", " (N)", " (H)"):
        r_andy[f"prop1{sfx}"] = "swing2"
        r_andy[f"min1{sfx}"] = "35"
        r_andy[f"max1{sfx}"] = "35"

    # Duriel: 50% Crushing Blow across N/NM/H
    r_dur = ensure_row("duriel")
    for sfx in ("", " (N)", " (H)"):
        r_dur[f"prop1{sfx}"] = "crush"
        r_dur[f"min1{sfx}"] = "50"
        r_dur[f"max1{sfx}"] = "50"

    # Mephisto: +35% Cast Speed & +35% Attack Speed across N/NM/H
    r_meph = ensure_row("mephisto")
    for sfx in ("", " (N)", " (H)"):
        r_meph[f"prop1{sfx}"] = "cast2"
        r_meph[f"min1{sfx}"] = "35"
        r_meph[f"max1{sfx}"] = "35"
        r_meph[f"prop2{sfx}"] = "swing2"
        r_meph[f"min2{sfx}"] = "35"
        r_meph[f"max2{sfx}"] = "35"

    # Diablo: 35% Deadly Strike across N/NM/H
    r_diab = ensure_row("diablo")
    for sfx in ("", " (N)", " (H)"):
        r_diab[f"prop1{sfx}"] = "deadly"
        r_diab[f"min1{sfx}"] = "35"
        r_diab[f"max1{sfx}"] = "35"

    # Baal: 40% Open Wounds across N/NM/H
    r_baal = ensure_row("baalcrab")
    for sfx in ("", " (N)", " (H)"):
        r_baal[f"prop1{sfx}"] = "openwounds"
        r_baal[f"min1{sfx}"] = "40"
        r_baal[f"max1{sfx}"] = "40"

    return write_tsv("monprop.txt", headers, rows)


def build_superuniques(cfg: dict) -> str:
    headers, rows = read_tsv("superuniques.txt")
    baal_waves = {
        "Baal Subject 1": ("4", "4", "9"),   # Colenzo: 4 Warped Shamans, Fire Enchanted
        "Baal Subject 2": ("2", "2", "23"),  # Achmel: 2 Greater Mummies, Poison Enchanted
        "Baal Subject 3": ("3", "3", "17"),  # Bartuc: 3 Council High Priests, Lightning Enchanted
        "Baal Subject 4": ("3", "3", "6"),   # Ventar: 3 Venom Lords, Extra Fast
        "Baal Subject 5": ("3", "3", "5"),   # Lister: 3 Minions of Destruction, Extra Strong
    }
    for row in rows:
        su = row.get("Superunique", "").strip()
        if su in baal_waves:
            mn, mx, mod1 = baal_waves[su]
            row["MinGrp"] = mn
            row["MaxGrp"] = mx
            row["Mod1"] = mod1
        else:
            # Cap oversized Superunique minion packs (e.g. 8-9 minions -> 3-4) for solo play
            mn = parse_int(row.get("MinGrp", ""))
            mx = parse_int(row.get("MaxGrp", ""))
            if mn > 3:
                row["MinGrp"] = str(max(2, (mn + 1) // 2))
            if mx > 4:
                row["MaxGrp"] = str(max(3, (mx + 1) // 2))

    return write_tsv("superuniques.txt", headers, rows)


# ============================================================================
# 3. MONEQUIP.TXT — 4-Tier Custom Unique Equipment for Valkyrie & Shadows
# ============================================================================

def build_monequip(cfg: dict) -> str:
    headers, rows = read_tsv("monequip.txt")
    kept_rows = [
        r for r in rows
        if r.get("monster", "").strip() not in ("valkyrie", "shadowwarrior", "shadowmaster")
    ]

    def make_eq(mon: str, lvl: str, loc1: str, item1: str, loc2: str = "", item2: str = "") -> dict:
        r = {h: "" for h in headers}
        r["monster"] = mon
        r["oninit"] = "1"
        r["level"] = lvl
        r["item1"], r["loc1"], r["mod1"] = item1, loc1, "7"
        if item2:
            r["item2"], r["loc2"], r["mod2"] = item2, loc2, "7"
        r["*eol"] = "0"
        return r

    # Descending level order per monster & slot (27 -> 16 -> 8 -> 1) as required by D2R monequip evaluation
    summon_rows = [
        # Valkyrie: Weapon (rarm: vk4..vk1), Body Armor (tors: va4..va1), Helm (head: vh4..vh1)
        make_eq("valkyrie", "27", "rarm", "vk4", "tors", "va4"),
        make_eq("valkyrie", "16", "rarm", "vk3", "tors", "va3"),
        make_eq("valkyrie", "8",  "rarm", "vk2", "tors", "va2"),
        make_eq("valkyrie", "1",  "rarm", "vk1", "tors", "va1"),
        make_eq("valkyrie", "27", "head", "vh4"),
        make_eq("valkyrie", "16", "head", "vh3"),
        make_eq("valkyrie", "8",  "head", "vh2"),
        make_eq("valkyrie", "1",  "head", "vh1"),
        # Shadow Warrior: Main Claw (rarm: sw4..sw1), Off Claw (larm: so4..so1), Armor (tors: sa4..sa1), Helm (head: sh4..sh1)
        make_eq("shadowwarrior", "27", "rarm", "sw4", "larm", "so4"),
        make_eq("shadowwarrior", "16", "rarm", "sw3", "larm", "so3"),
        make_eq("shadowwarrior", "8",  "rarm", "sw2", "larm", "so2"),
        make_eq("shadowwarrior", "1",  "rarm", "sw1", "larm", "so1"),
        make_eq("shadowwarrior", "27", "tors", "sa4", "head", "sh4"),
        make_eq("shadowwarrior", "16", "tors", "sa3", "head", "sh3"),
        make_eq("shadowwarrior", "8",  "tors", "sa2", "head", "sh2"),
        make_eq("shadowwarrior", "1",  "tors", "sa1", "head", "sh1"),
        # Shadow Master: Main Claw (rarm: sw4..sw1), Off Claw (larm: so4..so1), Armor (tors: sa4..sa1), Helm (head: sh4..sh1)
        make_eq("shadowmaster", "27", "rarm", "sw4", "larm", "so4"),
        make_eq("shadowmaster", "16", "rarm", "sw3", "larm", "so3"),
        make_eq("shadowmaster", "8",  "rarm", "sw2", "larm", "so2"),
        make_eq("shadowmaster", "1",  "rarm", "sw1", "larm", "so1"),
        make_eq("shadowmaster", "27", "tors", "sa4", "head", "sh4"),
        make_eq("shadowmaster", "16", "tors", "sa3", "head", "sh3"),
        make_eq("shadowmaster", "8",  "tors", "sa2", "head", "sh2"),
        make_eq("shadowmaster", "1",  "tors", "sa1", "head", "sh1"),
    ]

    return write_tsv("monequip.txt", headers, kept_rows + summon_rows)


# ============================================================================
# 4. DIFFICULTYLEVELS.TXT — Boss vs Merc/Pet Multipliers & Static Field
# ============================================================================

def build_difficultylevels(cfg: dict) -> str:
    headers, rows = read_tsv("difficultylevels.txt")
    static_mins = {"Normal": "25", "Nightmare": "33", "Hell": "50"}
    for row in rows:
        name = row.get("Name", "").strip()
        if name not in static_mins:
            continue
        row["PrimeEvilDamagePercentVSMercenary"] = "125"
        row["PrimeEvilDamagePercentVSPet"] = "175"
        row["MercenaryDamagePercentVSBoss"] = "50"
        row["StaticFieldMin"] = static_mins[name]

    return write_tsv("difficultylevels.txt", headers, rows)


# ============================================================================
# 5. HIRELING.TXT — 4 Distinct Mercenary Act Identities
# ============================================================================

def build_hireling(cfg: dict) -> str:
    headers, rows = read_tsv("hireling.txt")

    def set_skill(row: dict, idx: int, skill: str, mode: str, chance: str, par: str, lvl: str, lvlperlvl: str) -> None:
        row[f"Skill{idx}"] = skill
        row[f"Mode{idx}"] = mode
        row[f"Chance{idx}"] = chance
        row[f"ChancePerLvl{idx}"] = par
        row[f"Level{idx}"] = lvl
        row[f"LvlPerLvl{idx}"] = lvlperlvl

    def clear_skill(row: dict, idx: int) -> None:
        set_skill(row, idx, "", "", "", "", "", "")

    # Act 2 9-Aura Matrix: (Difficulty, SubType) -> Aura Skill Name
    act2_auras = {
        ("1", "Combat"): "Prayer",
        ("1", "Defensive"): "Defiance",
        ("1", "Offensive"): "Blessed Aim",
        ("2", "Combat"): "Cleansing",
        ("2", "Defensive"): "Holy Freeze",
        ("2", "Offensive"): "Vigor",
        ("3", "Combat"): "Meditation",
        ("3", "Defensive"): "Salvation",
        ("3", "Offensive"): "Sanctuary",
    }

    phys_rogue_templates = []

    for row in rows:
        hid = row.get("Id", "").strip()
        act = row.get("Act", "").strip()
        diff = row.get("Difficulty", "").strip()
        sub = row.get("SubType", "").strip()

        # Global Mercenary Survivability Buff (+25% HP, +25% Def, stronger Resists)
        row["HP"] = scale_int(row["HP"], 1.25)
        row["HP/Lvl"] = scale_int(row["HP/Lvl"], 1.25)
        row["Defense"] = scale_int(row["Defense"], 1.25)
        row["Def/Lvl"] = scale_int(row["Def/Lvl"], 1.25)
        row["Resist"] = "50"
        row["Resist/Lvl"] = "8"

        # 1. Act 1 Rogue Scouts: Elemental Arrows + Tactical Curses
        if act == "1":
            if "Fire" in sub:
                curse = {"1": "Weaken", "2": "Life Tap", "3": "Lower Resist"}.get(diff, "Weaken")
                set_skill(row, 4, curse, "4", "14", "0", "1", "1")
                # Clone Fire Rogue row as template for Physical Bowazon Rogue
                phys_rogue_templates.append(dict(row))
            elif "Cold" in sub:
                curse = {"1": "Dim Vision", "2": "Decrepify", "3": "Decrepify"}.get(diff, "Decrepify")
                set_skill(row, 4, curse, "4", "14", "0", "1", "1")

        # 2. Act 2 Desert Mercenaries: 9 Distinct Utility/Defensive Auras
        elif act == "2":
            aura = act2_auras.get((diff, sub), "Prayer")
            set_skill(row, 2, aura, "1", "100", "0", "3", "2")

        # 3. Act 3 Iron Wolves: Spells + Elemental Masteries + Low-Level Elemental Pulse Aura
        elif act == "3":
            row["HP"] = scale_int(row["HP"], 1.15)
            row["Defense"] = scale_int(row["Defense"], 1.20)
            if "Fire" in sub:
                set_skill(row, 4, "Fire Mastery", "2", "100", "0", "1", "2")
                set_skill(row, 5, "Holy Fire", "1", "100", "0", "2", "1")
            elif "Cold" in sub:
                set_skill(row, 4, "Cold Mastery", "2", "100", "0", "1", "2")
                set_skill(row, 5, "Holy Freeze", "1", "100", "0", "2", "1")
            elif "Ltng" in sub:
                set_skill(row, 4, "Lightning Mastery", "2", "100", "0", "1", "2")
                set_skill(row, 5, "Holy Shock", "1", "100", "0", "2", "1")

        # 4. Act 5 Barbarian Warriors: Remove Battle Cry & Taunt (Never Overwrite Curses!) + Offensive Auras
        elif act == "5":
            if hid in ("30", "31", "32"):
                # 2H Barbarian: Bash + Stun + Might (N) / Concentration (NM/H) + Battle Orders
                aura = "Might" if diff == "1" else "Concentration"
                set_skill(row, 3, aura, "1", "100", "0", "3", "2")
                set_skill(row, 4, "Battle Orders", "4", "10", "0", "3", "1")
                clear_skill(row, 5)
            elif hid in ("33", "34", "35"):
                # 1H Frenzy Barbarian: Frenzy + Double Swing + Iron Skin + Might (N) / Fanaticism (NM/H)
                aura = "Might" if diff == "1" else "Fanaticism"
                set_skill(row, 2, "Double Swing", "14", "40", "0", "3", "2")
                set_skill(row, 3, "Iron Skin", "2", "100", "0", "2", "2")
                set_skill(row, 4, aura, "1", "100", "0", "2", "1")
                clear_skill(row, 5)

    # Append 3 Physical Bowazon Act 1 Rogue Scout rows (Id 36, 37, 38 for N, NM, H)
    diff_names = {"1": "Normal", "2": "Nightmare", "3": "Hell"}
    for idx_offset, tmpl in enumerate(phys_rogue_templates):
        diff = tmpl["Difficulty"]
        nr = dict(tmpl)
        nr["Id"] = str(36 + idx_offset)
        nr["SubType"] = f"Physical Bow - {diff_names.get(diff, 'Normal')}"
        set_skill(nr, 1, "Multiple Shot", "5", "45", "0", "2", "2")
        set_skill(nr, 2, "Strafe", "5", "25", "0", "1", "2")
        set_skill(nr, 3, "Inner Sight", "4", "10", "0", "2", "2")
        set_skill(nr, 4, "Amplify Damage", "4", "14", "0", "1", "1")
        clear_skill(nr, 5)
        rows.append(nr)

    return write_tsv("hireling.txt", headers, rows)


# ============================================================================
# 6. EXPERIENCE.TXT & CHARSTATS.TXT — Solo Level 1-99 Curve & Class Stats
# ============================================================================

def build_experience(cfg: dict) -> str:
    headers, rows = read_tsv("experience.txt")
    for row in rows:
        lvl_str = row.get("Level", "").strip()
        if not lvl_str.isdigit():
            continue
        lvl = int(lvl_str)
        cur_ratio = parse_int(row.get("ExpRatio", "1024"))
        if 68 <= lvl <= 75:
            row["ExpRatio"] = str(max(cur_ratio, 768))
        elif 76 <= lvl <= 80:
            row["ExpRatio"] = str(max(cur_ratio, 576))
        elif 81 <= lvl <= 85:
            row["ExpRatio"] = str(max(cur_ratio, 448))
        elif 86 <= lvl <= 90:
            row["ExpRatio"] = str(max(cur_ratio, 320))
        elif 91 <= lvl <= 95:
            row["ExpRatio"] = str(max(cur_ratio, 192))
        elif 96 <= lvl <= 98:
            row["ExpRatio"] = str(max(cur_ratio, 112))

    return write_tsv("experience.txt", headers, rows)


def build_charstats(cfg: dict) -> str:
    headers, rows = read_tsv("charstats.txt")
    playable = {"Amazon", "Sorceress", "Necromancer", "Paladin", "Barbarian", "Druid", "Assassin"}
    for row in rows:
        cls = row.get("class", "").strip()
        if cls not in playable:
            continue

        # 1. 2 Skill Points per Level-Up
        row["SkillsPerLevel"] = "2"

        # 2. +75% LifePerLevel (1.75x) & -25% LifePerVitality (0.75x) so base HP scales moderately with Level
        row["LifePerLevel"] = scale_int(row["LifePerLevel"], 1.75)
        row["LifePerVitality"] = scale_int(row["LifePerVitality"], 0.75)

        # 3. -25% ManaPerLevel (0.75x), +50% ManaPerMagic (1.50x), and slower base ManaRegen (160s for full bar)
        row["ManaPerLevel"] = scale_int(row["ManaPerLevel"], 0.75)
        row["ManaPerMagic"] = scale_int(row["ManaPerMagic"], 1.50)
        row["ManaRegen"] = "160"

        # 4. Tactical Stamina Curve (Running costs stamina by armor weight and scales steadily with Level/Vitality)
        row["StaminaPerLevel"] = "2"
        row["StaminaPerVitality"] = "3"
        row["RunDrain"] = "15" if cls == "Assassin" else "20"

        # 5. Standardized 100% Potion Scaling so hp1..hp5 / mp1..mp5 restore their exact stated cap over 3 seconds
        row["HealthPotionPercent"] = "100"
        row["ManaPotionPercent"] = "100"

    return write_tsv("charstats.txt", headers, rows)


def print_monster_summary(cfg: dict) -> None:
    _, v_rows = read_tsv("monstats.txt")
    build_monsters_all(cfg)
    import os
    from mod_builder.common import MOD_EXCEL
    with open(os.path.join(MOD_EXCEL, "monstats.txt"), "r", encoding="utf-8", newline="") as f:
        lines = [ln for ln in f.read().split("\r\n") if ln]
    m_headers = lines[0].split("\t")
    m_rows = [dict(zip(m_headers, ln.split("\t"))) for ln in lines[1:]]

    all_res = ("Dm", "Ma", "Fi", "Li", "Co", "Po")
    print("=== MONSTER IMMUNITY (>= 100%) & WEAKNESS (< 0%) COUNTS: VANILLA vs MOD ===")
    for diff_label, sfx in [("Normal", ""), ("Nightmare", "(N)"), ("Hell", "(H)")]:
        v_imm = {r: 0 for r in all_res}
        m_imm = {r: 0 for r in all_res}
        m_weak = {r: 0 for r in all_res}
        total = 0
        for vr, mr in zip(v_rows, m_rows):
            if (
                vr.get("isSpawn", "") != "1"
                or vr.get("killable", "") != "1"
                or vr.get("Align", "") != ""
                or vr.get("boss", "") == "1"
                or vr.get("primeevil", "") == "1"
                or parse_int(vr.get("Velocity", "0")) <= 0
            ):
                continue
            total += 1
            for r in all_res:
                col = f"Res{r}{sfx}"
                if parse_int(vr.get(col, "")) >= 100:
                    v_imm[r] += 1
                if parse_int(mr.get(col, "")) >= 100:
                    m_imm[r] += 1
                if parse_int(mr.get(col, "")) < 0:
                    m_weak[r] += 1
        print(f"\n[{diff_label}] ({total} spawnable enemy variants):")
        for r in all_res:
            b_neg = sum(1 for mr, vr in zip(m_rows, v_rows) if vr.get("isSpawn")=="1" and vr.get("killable")=="1" and vr.get("Align")=="" and vr.get("boss")!="1" and vr.get("primeevil")!="1" and parse_int(vr.get("Velocity","0"))>0 and parse_int(mr.get(f"Res{r}{sfx}","")) < 0)
            b_low = sum(1 for mr, vr in zip(m_rows, v_rows) if vr.get("isSpawn")=="1" and vr.get("killable")=="1" and vr.get("Align")=="" and vr.get("boss")!="1" and vr.get("primeevil")!="1" and parse_int(vr.get("Velocity","0"))>0 and 0 <= parse_int(mr.get(f"Res{r}{sfx}","")) < 50)
            b_med = sum(1 for mr, vr in zip(m_rows, v_rows) if vr.get("isSpawn")=="1" and vr.get("killable")=="1" and vr.get("Align")=="" and vr.get("boss")!="1" and vr.get("primeevil")!="1" and parse_int(vr.get("Velocity","0"))>0 and 50 <= parse_int(mr.get(f"Res{r}{sfx}","")) < 75)
            b_hi  = sum(1 for mr, vr in zip(m_rows, v_rows) if vr.get("isSpawn")=="1" and vr.get("killable")=="1" and vr.get("Align")=="" and vr.get("boss")!="1" and vr.get("primeevil")!="1" and parse_int(vr.get("Velocity","0"))>0 and 75 <= parse_int(mr.get(f"Res{r}{sfx}","")) < 100)
            print(f"  Res{r:2s}: Vanilla Imm={v_imm[r]:3d} -> Mod Imm={m_imm[r]:3d} | 75-99%={b_hi:3d} | 50-74%={b_med:3d} | 0-49%={b_low:3d} | Weak(<0%)={b_neg:3d}")

    print("\n=== SAMPLE PROGRESSION (Normal -> Nightmare -> Hell) ===")
    samples = ["zombie1", "skeleton4", "wraith2", "mummy3", "willowisp2", "cantor2", "megademon2", "snowyeti2"]
    m_by_id = {r["Id"]: r for r in m_rows}
    for sid in samples:
        r = m_by_id.get(sid)
        if not r:
            continue
        n_str = "/".join(f"{ x }:{r.get('Res'+x, '0')}" for x in all_res)
        nm_str = "/".join(f"{ x }:{r.get('Res'+x+'(N)', '0')}" for x in all_res)
        h_str = "/".join(f"{ x }:{r.get('Res'+x+'(H)', '0')}" for x in all_res)
        print(f"  {sid:14s} | N: [{n_str}] | NM: [{nm_str}] | H: [{h_str}]")


def build_monsters_all(cfg: dict) -> list[str]:
    return [
        build_levels(cfg),
        build_monstats(cfg),
        build_monprop(cfg),
        build_superuniques(cfg),
        build_monequip(cfg),
        build_difficultylevels(cfg),
        build_hireling(cfg),
        build_experience(cfg),
        build_charstats(cfg),
    ]

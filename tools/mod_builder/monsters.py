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
from mod_builder.common import (
    read_excel_tsv as read_tsv,
    read_strings_json,
    upsert_string_entries,
    write_excel_tsv as write_tsv,
    write_strings_json,
)


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

# Curated rosters for Act 2 Open Desert (Zero Poison, Zero Maggots, Zero Zombies in open desert)
# and Act 5 Bloody Foothills (Classic 1.09 Enslaved + Death Mauler physical siege onslaught)
CURATED_ZONE_ROSTERS = {
    "Act 2 - Desert 1": ["sandleaper1", "pantherwoman1", "scarab1", "vulture1", "slinger1"],  # Rocky Waste
    "Act 2 - Desert 2": ["sandleaper2", "pantherwoman2", "vulture2", "slinger5"],             # Dry Hills
    "Act 2 - Desert 3": ["crownest3", "swarm1", "scarab2", "vulture2"],                       # Far Oasis (no sandmaggot1)
    "Act 2 - Desert 4": ["sandraider2", "sandleaper3", "pantherwoman3", "slinger6"],          # Lost City (no zombie5)
    "Act 2 - Valley of the Kings": ["brute4", "pantherwoman4", "scarab4", "slinger4"],        # Canyon of the Magi (no sandmaggot3)
    "Act 2 - Sewer 1 B": ["skeleton4", "sandraider1", "mummy1", "sk_archer4"],                # Sewers 2 (zombie5 reserved for Ancient Tunnels)
    "Act 5 - Siege 1": ["minion1", "deathmauler1"],                                           # Bloody Foothills (1.09 pair)
}

# Purely Optional Exploration Dungeons (26 levels.txt rows across 22 named dungeons with zero quest objectives):
# Monsters in these zones are +20% more difficult and drop from dedicated '<TC> Opt' (+30% reward probability) tables.
OPTIONAL_DUNGEON_IDS = {
    "9", "13",          # Act 1: Cave Level 1 & 2
    "14",               # Act 1: Underground Passage Level 2
    "11", "15",         # Act 1: Hole Level 1 & 2
    "12", "16",         # Act 1: Pit Level 1 & 2
    "18", "19",         # Act 1: Crypt & Mausoleum
    "55", "59",         # Act 2: Stony Tomb Level 1 & 2
    "65",               # Act 2: Ancient Tunnels
    "84",               # Act 3: Arachnid Lair
    "86", "87", "90",   # Act 3: Swampy Pit Level 1, 2 & 3
    "95", "96",         # Act 3: Disused Fane & Forgotten Reliquary (Kurast Bazaar)
    "97", "98", "99",   # Act 3: Forgotten Temple, Ruined Fane & Disused Reliquary (Upper Kurast / Causeway)
    "116",              # Act 5: Drifter Cavern
    "119",              # Act 5: Icy Cellar
    "125", "126", "127" # Act 5: Abaddon, Pit of Acheron & Infernal Pit
}

# Minor same-family swaps in Non-Optional zones to free 8 monster IDs exclusively for Optional Dungeons
NON_OPT_ZONE_MONSTER_SWAPS = {
    "4":  {"zombie2": "zombie1"},             # Stony Field -> free zombie2 for Cave 1/2, Crypt, Mausoleum
    "17": {"zombie2": "zombie1"},             # Burial Grounds -> free zombie2
    "77": {"zombie4": "zombie3"},             # Great Marsh -> free zombie4 for Swampy Pit 2
    "6":  {"brute2": "brute1"},               # Black Marsh -> free brute2 for Hole 1/2
    "94": {"brute5": "brute4"},               # Ruined Temple -> free brute5 for Disused Fane / Forgotten Reliquary
    "5":  {"corruptrogue2": "corruptrogue1"}, # Dark Wood -> free corruptrogue2 for Underground Passage 2
    "10": {"corruptrogue2": "corruptrogue1"}, # Underground Passage 1 -> free corruptrogue2
    "7":  {"corruptrogue3": "corruptrogue4"}, # Tamoe Highland -> free corruptrogue3 for Pit 1/2
    "26": {"corruptrogue3": "corruptrogue4"}, # Monastery Gate -> free corruptrogue3
    "45": {"mummy3": "mummy2"},               # Valley of Snakes -> free mummy3 for Ancient Tunnels
    "58": {"mummy3": "mummy2"},               # Claw Viper Temple 1 -> free mummy3
    "61": {"mummy3": "mummy2"},               # Claw Viper Temple 2 -> free mummy3
}

# 30 shared zone monsters remapped in OPTIONAL_DUNGEON_IDS to unused same-BaseId vanilla rows in monstats.txt
OPT_MONSTER_REMAP = {
    "arach3": "arach2",
    "arach4": "arach6",
    "arach5": "arach7",
    "batdemon2": "batdemon6",
    "bighead3": "bighead6",
    "bloodlord2": "bloodlord4",
    "bonefetish4": "bonefetish6",
    "bonefetish5": "bonefetish7",
    "corruptrogue5": "corruptrogue6",
    "cr_archer1": "cr_archer6",
    "cr_archer2": "cr_archer7",
    "cr_archer3": "cr_archer8",
    "fallen2": "fallen5",
    "fallen3": "fallen6",
    "imp4": "imp6",
    "mosquito2": "mosquito3",
    "mummy4": "mummy6",
    "overseer3": "overseer5",
    "reanimatedhorde3": "reanimatedhorde6",
    "sandmaggot4": "sandmaggot3",
    "sandraider3": "sandraider5",
    "scarab1": "scarab6",
    "sk_archer1": "sk_archer6",
    "skeleton1": "skeleton6",
    "skmage_ltng4": "skmage_ltng5",
    "skmage_pois3": "skmage_pois5",
    "snowyeti4": "snowyeti3",
    "succubus3": "succubus6",
    "vampire2": "vampire6",
    "willowisp1": "willowisp2",
}

OPT_SUB_MONSTER_REMAP = {
    "minion3": "minion9",
    "minion4": "minion10",
    "maggotegg4": "maggotegg3",
    "maggotbaby4": "maggotbaby3",
    "frozenhorror1": "frozenhorror5",
}

OPT_FULL_MONSTER_REMAP = {**OPT_MONSTER_REMAP, **OPT_SUB_MONSTER_REMAP}
OPT_DST_TO_SRC = {dst: src for src, dst in OPT_FULL_MONSTER_REMAP.items()}

OPTIONAL_DUNGEON_MONSTER_IDS = {
    # 12 already-exclusive Optional Dungeon monster IDs
    "batdemon4", "bloodlord3", "clawviper5", "cr_archer5", "imp2", "overseer4",
    "scarab5", "skeleton3", "skeleton5", "skmage_ltng3", "snowyeti1", "succubus2",
    # 8 freed monster IDs made exclusive to Optional Dungeons
    "zombie2", "zombie4", "zombie5", "brute2", "brute5", "corruptrogue2", "corruptrogue3", "mummy3",
    # 35 remapped Optional Dungeon monster/minion/spawn/superunique IDs
    *OPT_FULL_MONSTER_REMAP.values(),
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

# 4-Tier Zone Density Matrix (Strictly <= 1.0x Vanilla MonDen)
# Tier 1 (1.00x Vanilla): High-density swarm jungles, bug tunnels & siege battlefields
ZONE_DENSITY_TIER_1_SWARM = {
    # Act 1
    "Act 1 - Wilderness 3",         # Stony Field
    "Act 1 - Cave 3",               # Underground Passage Level 1
    "Act 1 - Cave 3 Treasure",      # Underground Passage Level 2
    "Act 1 - Cave 5",               # Pit Level 1
    "Act 1 - Cave 5 Treasure",      # Pit Level 2
    # Act 2
    "Act 2 - Desert 3",             # Far Oasis
    "Act 2 - Lair 1 A",             # Maggot Lair Level 1
    "Act 2 - Lair 1 B",             # Maggot Lair Level 2
    "Act 2 - Lair 1 Treasure",      # Maggot Lair Level 3
    # Act 3
    "Act 3 - Jungle 1",             # Spider Forest
    "Act 3 - Jungle 2",             # Great Marsh
    "Act 3 - Jungle 3",             # Flayer Jungle
    "Act 3 - Spider 1",             # Arachnid Lair
    "Act 3 - Spider 2",             # Spider Cavern
    "Act 3 - Dungeon 1 A",          # Swampy Pit Level 1
    "Act 3 - Dungeon 1 B",          # Swampy Pit Level 2
    "Act 3 - Dungeon 1 Treasure",   # Swampy Pit Level 3
    "Act 3 - Dungeon 2 A",          # Flayer Dungeon Level 1
    "Act 3 - Dungeon 2 B",          # Flayer Dungeon Level 2
    "Act 3 - Dungeon 2 Treasure",   # Flayer Dungeon Level 3
    # Act 5
    "Act 5 - Siege 1",              # Bloody Foothills
    "Act 5 - Barricade 1",          # Frigid Highlands
    "Act 5 - Barricade 2",          # Arreat Plateau
}

# Tier 2 (0.75x Vanilla): Standard tactical wilderness, barracks, deserts, Kurast & WSK
ZONE_DENSITY_TIER_2_TACTICAL = {
    # Act 1
    "Act 1 - Wilderness 1",         # Blood Moor
    "Act 1 - Wilderness 4",         # Dark Wood
    "Act 1 - Wilderness 5",         # Black Marsh
    "Act 1 - Wilderness 6",         # Tamoe Highland
    "Act 1 - Barracks",             # Barracks
    "Act 1 - Jail 1",               # Jail Level 1
    "Act 1 - Jail 2",               # Jail Level 2
    "Act 1 - Jail 3",               # Jail Level 3
    "Act 1 - Catacombs 1",          # Catacombs Level 1
    "Act 1 - Catacombs 2",          # Catacombs Level 2
    "Act 1 - Catacombs 3",          # Catacombs Level 3
    "Act 1 - Tristram",             # Tristram
    # Act 2
    "Act 2 - Desert 1",             # Rocky Waste
    "Act 2 - Desert 2",             # Dry Hills
    "Act 2 - Desert 4",             # Lost City
    "Act 2 - Desert 5",             # Valley of Snakes
    "Act 2 - Valley of the Kings",  # Canyon of the Magi
    "Act 2 - Arcane",               # Arcane Sanctuary
    # Act 3
    "Act 3 - Kurast 1",             # Lower Kurast
    "Act 3 - Kurast 2",             # Kurast Bazaar
    "Act 3 - Kurast 3",             # Upper Kurast
    "Act 3 - Kurast 4",             # Kurast Causeway
    "Act 3 - Travincal",            # Travincal
    # Act 4
    "Act 4 - Mesa 1",               # Outer Steppes
    "Act 4 - Mesa 3",               # City of the Damned
    "Act 4 - Lava 1",               # River of Flame
    # Act 5
    "Act 5 - Barricade Snow",       # Frozen Tundra
    "Act 5 - Ice Cave 1",           # Crystalline Passage
    "Act 5 - Ice Cave 1A",          # Frozen River
    "Act 5 - Ice Cave 2",           # Glacial Trail
    "Act 5 - Ice Cave 3",           # The Ancients' Way
    "Act 5 - Baal Temple 1",        # Worldstone Keep Level 1
    "Act 5 - Baal Temple 2",        # Worldstone Keep Level 2
    "Act 5 - Baal Temple 3",        # Worldstone Keep Level 3
    "Act 5 - Throne Room",          # Throne of Destruction
}

# Tier 3 (0.66x Vanilla): Dense tomb chambers, cellars & viper temples
ZONE_DENSITY_TIER_3_TOMB = {
    # Act 1
    "Act 1 - Crypt 3 A",            # Tower Cellar Level 1
    "Act 1 - Crypt 3 B",            # Tower Cellar Level 2
    "Act 1 - Crypt 3 C",            # Tower Cellar Level 3
    "Act 1 - Crypt 3 D",            # Tower Cellar Level 4
    "Act 1 - Crypt 3 E",            # Tower Cellar Level 5
    # Act 2
    "Act 2 - Corrupt Harem 1",      # Harem Level 2
    "Act 2 - Basement 1",           # Palace Cellar Level 1
    "Act 2 - Basement 2",           # Palace Cellar Level 2
    "Act 2 - Basement 3",           # Palace Cellar Level 3
    "Act 2 - Tomb 1 A",             # Stony Tomb Level 1
    "Act 2 - Tomb 1 Treasure",      # Stony Tomb Level 2
    "Act 2 - Tomb 2 A",             # Halls of the Dead Level 1
    "Act 2 - Tomb 2 B",             # Halls of the Dead Level 2
    "Act 2 - Tomb 2 Treasure",      # Halls of the Dead Level 3
    "Act 2 - Tomb 3 A",             # Claw Viper Temple Level 1
    "Act 2 - Tomb 3 Treasure",      # Claw Viper Temple Level 2
    "Act 2 - Tomb Tal 1",           # Tal Rasha's Tomb 1
    "Act 2 - Tomb Tal 2",           # Tal Rasha's Tomb 2
    "Act 2 - Tomb Tal 3",           # Tal Rasha's Tomb 3
    "Act 2 - Tomb Tal 4",           # Tal Rasha's Tomb 4
    "Act 2 - Tomb Tal 5",           # Tal Rasha's Tomb 5
    "Act 2 - Tomb Tal 6",           # Tal Rasha's Tomb 6
    "Act 2 - Tomb Tal 7",           # Tal Rasha's Tomb 7
    # Act 3
    "Act 3 - Sewer 1",              # Kurast Sewers Level 1
    "Act 3 - Sewer 2",              # Kurast Sewers Level 2
}


def get_zone_density_multiplier(zone_name: str) -> float:
    if zone_name in ZONE_DENSITY_TIER_1_SWARM:
        return 1.00
    if zone_name in ZONE_DENSITY_TIER_2_TACTICAL:
        return 0.75
    if zone_name in ZONE_DENSITY_TIER_3_TOMB:
        return 0.66
    # Tier 4 (0.50x Vanilla): Sparse Dread / Juggernaut zones (Mausoleum, Crypt, Cold Plains,
    # Durance of Hate, Kurast Temples, Chaos Sanctuary, Nihlathak Halls, Abaddon/Acheron/Infernal Pit, etc.)
    return 0.50


def build_levels(cfg: dict) -> str:
    headers, rows = read_tsv("levels.txt")
    for row in rows:
        name = row.get("Name", "")
        zid = row.get("Id", "")
        if not name or name == "Expansion" or zid in FIXED_SKIP_ZONE_IDS:
            continue

        # Strictly 1 Random Unique Boss Pack per combat zone (including preset floors & Bloody Foothills)
        for u_col in ("MonUMin", "MonUMax", "MonUMin(N)", "MonUMax(N)", "MonUMin(H)", "MonUMax(H)"):
            if parse_int(row.get(u_col, "")) > 0 or name == "Act 5 - Siege 1":
                row[u_col] = "1"

        monden_n = parse_int(row.get("MonDen(N)", ""))
        if monden_n <= 0 and not row.get("mon1", "").strip():
            continue

        tier_mult = get_zone_density_multiplier(name)

        # Special handling for Moo Moo Farm (keep 1 monster: hellbovine, Tier 4 0.50x density)
        if name == "Act 1 - Moo Moo Farm":
            row["NumMon"] = "1"
            for d_col in ("MonDen", "MonDen(N)", "MonDen(H)"):
                val = parse_int(row.get(d_col, ""))
                if val > 0:
                    row[d_col] = str(max(1, int(round(val * tier_mult))))
            for u_col in ("MonUMin", "MonUMax", "MonUMin(N)", "MonUMax(N)", "MonUMin(H)", "MonUMax(H)"):
                if parse_int(row.get(u_col, "")) > 0:
                    row[u_col] = "1"
            continue

        # 1. Zone Monster Rosters:
        #    - Act 2 Open Desert: Curated zero-poison / zero-maggot / zero-zombie desert rosters
        #    - Act 5: Remove all Nightmare/Hell "Guest" monsters so Act 5 spawns the exact same
        #      native Act 5 monsters across Normal, Nightmare, and Hell
        #    - All other Act 1-4 zones: Preserve full vanilla monster rosters (mon, nmon, umon, NumMon)
        if name in CURATED_ZONE_ROSTERS:
            roster = list(CURATED_ZONE_ROSTERS[name])
            orig_num = parse_int(row.get("NumMon", "3"), 3)
            row["NumMon"] = str(min(orig_num, len(roster)))
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
        elif name.startswith("Act 5 -"):
            # Strip Act 1 guest monsters from Bloody Foothills (Act 5 - Siege 1) and sync mon -> nmon/umon
            act5_guest_exclude = {"sk_archer6", "quillrat6", "bighead6"}
            seen = []
            for i in range(1, 26):
                m = row.get(f"mon{i}", "").strip()
                if m and m not in act5_guest_exclude and m not in seen:
                    seen.append(m)
            if seen:
                orig_num = parse_int(row.get("NumMon", "3"), 3)
                row["NumMon"] = str(min(orig_num, len(seen)))
                for i in range(1, 26):
                    if i <= len(seen):
                        m = seen[i - 1]
                        row[f"mon{i}"] = m
                        row[f"nmon{i}"] = m
                        row[f"umon{i}"] = UMON_REPLACEMENTS.get(m, m)
                    else:
                        row[f"mon{i}"] = ""
                        row[f"nmon{i}"] = ""
                        row[f"umon{i}"] = ""

        # 2. Scale Monster Density by 4-Tier Matrix (1.00x / 0.75x / 0.66x / 0.50x, never exceeding vanilla)
        #    For Bloody Foothills (Act 5 - Siege 1), also enable its 650 Tier 1 Swarm density in Normal
        for d_col in ("MonDen", "MonDen(N)", "MonDen(H)"):
            val = parse_int(row.get(d_col, ""))
            if val > 0:
                row[d_col] = str(max(1, int(round(val * tier_mult))))
            elif d_col == "MonDen" and name == "Act 5 - Siege 1":
                row[d_col] = "650"

        # 3. Strictly 1 Random Unique Boss Pack per combat zone
        for u_col in ("MonUMin", "MonUMax", "MonUMin(N)", "MonUMax(N)", "MonUMin(H)", "MonUMax(H)"):
            if parse_int(row.get(u_col, "")) > 0:
                row[u_col] = "1"

        # 4. Disambiguate Non-Optional vs Optional Exploration Dungeon monster rosters:
        #    - In NON_OPT_ZONE_MONSTER_SWAPS zones, swap the 8 shared monster IDs to same-family peers
        #    - In OPTIONAL_DUNGEON_IDS (26 purely optional dungeon rows), remap shared monsters via OPT_MONSTER_REMAP
        if zid in NON_OPT_ZONE_MONSTER_SWAPS:
            swap_map = NON_OPT_ZONE_MONSTER_SWAPS[zid]
            for i in range(1, 26):
                for m_prefix in ("mon", "nmon", "umon"):
                    col = f"{m_prefix}{i}"
                    cur_m = row.get(col, "").strip()
                    if cur_m in swap_map:
                        row[col] = swap_map[cur_m]
        elif zid in OPTIONAL_DUNGEON_IDS:
            for i in range(1, 26):
                for m_prefix in ("mon", "nmon", "umon"):
                    col = f"{m_prefix}{i}"
                    cur_m = row.get(col, "").strip()
                    if cur_m in OPT_MONSTER_REMAP:
                        row[col] = OPT_MONSTER_REMAP[cur_m]

    return write_tsv("levels.txt", headers, rows)


# ============================================================================
# 2. MONSTATS.TXT, MONPROP.TXT & SUPERUNIQUES.TXT
# ============================================================================

HEAVY_BRUTE_BASES = {
    "zombie1", "brute2", "mummy1", "blunderbore1", "thornhulk1",
    "regurgitator1", "megademon1", "reanimatedhorde1", "siegebeast1",
    "snowyeti1", "frozenhorror1", "bloodlord1", "hellbovine",
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

RES_COLOR_LABELS = {
    "Dm": "ÿc4Physicalÿc0",
    "Ma": "ÿc8Magicÿc0",
    "Fi": "ÿc1Fireÿc0",
    "Li": "ÿc9Lightningÿc0",
    "Co": "ÿc3Coldÿc0",
    "Po": "ÿc2Poisonÿc0",
}

NEUTRAL_FAMILIES = {
    "quillrat1",      # Quill Rat -> Bush Barb (5)
    "foulcrow1",      # Foul Crow -> Cloud Stalker (4)
    "sandraider1",    # Sand Raider -> Assailant (5)
    "baboon1",        # Dune Beast -> Temple Guard (5)
    "vulture1",       # Carrion Bird -> Winged Nightmare (4)
    "sandleaper1",    # Sand Leaper -> Cliff Lurker (5)
    "frogdemon1",     # Swamp Dweller -> Slime Prince (3)
    "deathmauler1",   # Death Mauler -> Death Brigadier (5)
    "painworm1",      # Pain Worm -> Anguish Worm (5)
    "vilechild1",     # Flesh Beast -> Grotesque Wyrm (3)
    "maggotbaby1",    # Sand Maggot Young -> World Killer Young (hatched children)
}

NEUTRAL_MONSTER_IDS = {
    "minion1",
    "minion2",
    "suicideminion1",
    "suicideminion2",
    "arach1",
    "arach2",
}


def _parse_monster_tier(mon_id: str, base_id: str) -> int:
    if base_id == "slinger5":
        return 1 if mon_id == "slinger5" else 2
    i = len(mon_id) - 1
    while i >= 0 and mon_id[i].isdigit():
        i -= 1
    num_str = mon_id[i + 1 :]
    return int(num_str) if num_str else 1


def _get_monster_affinity(
    mon_id: str, base_id: str, tier_idx: int
) -> tuple[str | None, int, str | None, int]:
    """
    Return (vuln_elem, vuln_steps, res_elem, res_steps) for a monster:
      - Difficulty baselines: Normal = 10%, Nightmare = 20%, Hell = 30%
      - Step interval = 35% (1 step = ±35%, 2 steps = ±70%, capped at 99% in Hell)
      - Distribution across the 301 native progression monsters:
          * ~1/2 (49.8%, 150/301): Both ("Vulnerable: X | Resists: Y")
          * ~1/3 (33.6%, 101/301): Single-Affinity ("Vulnerable: X" OR "Resists: Y")
          * ~1/6 (16.6%,  50/301): Neither / Neutral (10% / 20% / 30%, no subtitle)
    """
    t_weak = 1 if tier_idx <= 2 else 2
    t_res = 1 if tier_idx <= 2 else 2

    # 1. NEITHER / NEUTRAL (~1/6 = 16.6%, 50/301 progression monsters)
    if base_id in NEUTRAL_FAMILIES or mon_id in NEUTRAL_MONSTER_IDS:
        return (None, 0, None, 0)

    # 2. SINGLE-AFFINITY (~1/3 = 33.6%, 101/301 progression monsters)
    # A) Only Resists ("Resists: <Element>")
    if base_id in {"corruptrogue1", "cr_archer1", "cr_lancer1", "goatman1"}:
        return (None, 0, "Co", t_res)
    if base_id in {"brute2", "hellbovine", "blunderbore1"}:
        return (None, 0, "Dm", t_res if base_id != "blunderbore1" else 2)
    if base_id in {"pantherwoman1", "slinger1", "slinger5"}:
        return (None, 0, "Fi", t_res)
    if base_id == "zealot1":
        return (None, 0, "Ma", t_res)
    if base_id in {"overseer1", "imp1"}:
        return (None, 0, "Fi", t_res)
    if base_id == "fallen1":
        return (None, 0, "Fi", 2)

    # B) Only Vulnerable ("Vulnerable: <Element>")
    if base_id in {"skeleton1", "sk_archer1"}:
        return ("Fi", t_weak, None, 0)
    if base_id in {"fetish1", "fetishblow1"}:
        return ("Fi", t_weak, None, 0)
    if base_id == "batdemon1":
        return ("Co", t_weak, None, 0)
    if base_id == "mosquito1":
        return ("Fi", t_weak, None, 0)
    if base_id == "swarm1":
        return ("Fi", t_weak, None, 0)
    if base_id in {"succubus1", "succubuswitch1"}:
        return ("Dm", t_weak if base_id == "succubus1" else 2, None, 0)

    # 3. BOTH ("Vulnerable: <Element> | Resists: <Element>") (~1/2 = 49.8%, 150/301 progression monsters)
    if base_id in {"zombie1", "mummy1", "vilemother1", "putriddefiler1", "skmage_pois1"}:
        return ("Fi", 2, "Po", 2)
    if base_id == "sandmaggot1":
        return ("Fi", t_weak, "Po", 2)
    if base_id == "arach1":
        if mon_id == "arach4":  # Flame Spider
            return ("Co", 2, "Fi", 2)
        return ("Fi", t_weak, "Po", 2)
    if base_id in {"fallenshaman1", "fetishshaman1", "skmage_fire1", "councilmember1", "megademon1", "baalhighpriest", "venomlord"}:
        return ("Co", 2, "Fi", 2)
    if base_id == "bighead1":
        return ("Co", t_weak, "Li", 2)
    if base_id == "scarab1":
        return ("Co", 2, "Li", 2)
    if base_id in {"wraith1", "siegebeast1", "bloodlord1"}:
        return ("Ma", 2, "Dm", 2)
    if base_id == "willowisp1":
        return ("Dm", 2, "Li", 2)
    if base_id == "clawviper1":
        return ("Fi", t_weak, "Co", 2)
    if base_id in {"vampire1", "skmage_cold1", "reanimatedhorde1", "snowyeti1", "frozenhorror1"}:
        return ("Fi", 2, "Co", 2)
    if base_id == "thornhulk1":
        return ("Fi", 2, "Dm", 2)
    if base_id == "unraveler1":
        return ("Fi", 2, "Ma", 2)
    if base_id == "bonefetish1":
        return ("Ma", 2, "Po", 2)
    if base_id in {"cantor1", "fingermage1", "doomknight3"}:
        return ("Dm", 2, "Ma", 2)
    if base_id == "regurgitator1":
        return ("Li", 2, "Po", 2)
    if base_id in {"doomknight1", "baalminion1"}:
        return ("Ma", 2, "Fi", 2)
    if base_id == "doomknight2":
        return ("Co", 2, "Li", 2)
    if base_id == "skmage_ltng1":
        return ("Po", 2, "Li", 2)
    if base_id in {"minion1", "suicideminion1"}:
        if any(mon_id.endswith(s) for s in ("3", "6", "8")):
            return ("Fi", 2, "Co", 2)
        return ("Co", 2, "Fi", 2)

    return (None, 0, None, 0)


def _apply_affinity_resists(
    row: dict,
    vuln_elem: str | None,
    vuln_steps: int,
    res_elem: str | None,
    res_steps: int,
) -> None:
    """
    Set Normal (10%), Nightmare (20%), and Hell (30%) baseline resistances across all 6 damage types,
    shifted by -35% * vuln_steps for vuln_elem and +35% * res_steps for res_elem (capped at 99%).
    """
    for rtype in ("Dm", "Ma", "Fi", "Li", "Co", "Po"):
        if rtype == vuln_elem and vuln_steps > 0:
            delta = -35 * vuln_steps
        elif rtype == res_elem and res_steps > 0:
            delta = 35 * res_steps
        else:
            delta = 0
        row[f"Res{rtype}"] = str(min(99, 10 + delta))
        row[f"Res{rtype}(N)"] = str(min(99, 20 + delta))
        row[f"Res{rtype}(H)"] = str(min(99, 30 + delta))


def _apply_monster_resistances(
    row: dict, base_id: str, mon_id: str = ""
) -> tuple[str | None, str | None]:
    tier_idx = _parse_monster_tier(mon_id, base_id)
    v_el, v_st, r_el, r_st = _get_monster_affinity(mon_id, base_id, tier_idx)
    _apply_affinity_resists(row, v_el, v_st, r_el, r_st)
    return v_el, r_el


def _configure_capstone_bosses(row: dict, mon_id: str) -> bool:
    if mon_id == "andariel":
        row["Level"], row["Level(N)"], row["Level(H)"] = "14", "49", "76"
        row["Velocity"], row["Run"] = "9", "9"
        row["aidist"], row["aidist(N)"], row["aidist(H)"] = "45", "50", "55"
        row["Crit"] = "25"
        row["Sk1lvl"], row["Sk2lvl"] = "4", "4"
        row["MonProp"] = "andariel"
        row["ToBlock"], row["ToBlock(N)"], row["ToBlock(H)"] = "10", "15", "20"
        # Progressive resists (N < NM < H):
        # Fire weakness: -40% (N) -> -30% (NM) -> -15% (H)
        # Phys weakness: -10% (N) -> -5% (NM) -> 0% (H)
        row["ResDm"], row["ResDm(N)"], row["ResDm(H)"] = "-10", "-5", "0"
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "15", "30", "50"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "-40", "-30", "-15"
        row["ResLi"], row["ResLi(N)"], row["ResLi(H)"] = "35", "55", "75"
        row["ResCo"], row["ResCo(N)"], row["ResCo(H)"] = "35", "55", "75"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "80", "90", "95"
        for col, mult in (("minHP", 2.85), ("maxHP", 2.85), ("MinHP(N)", 3.15), ("MaxHP(N)", 3.15), ("MinHP(H)", 3.45), ("MaxHP(H)", 3.45)):
            row[col] = scale_int(row[col], mult)
        for col, mult in (("A1MinD", 1.75), ("A1MaxD", 1.75), ("A1MinD(N)", 1.90), ("A1MaxD(N)", 1.90), ("A1MinD(H)", 2.10), ("A1MaxD(H)", 2.10)):
            row[col] = scale_int(row[col], mult)
        for col, mult in (("El1MinD", 2.00), ("El1MaxD", 2.00), ("El1MinD(N)", 2.25), ("El1MaxD(N)", 2.25), ("El1MinD(H)", 2.50), ("El1MaxD(H)", 2.50)):
            if row.get(col, ""):
                row[col] = scale_int(row[col], mult)
        for col, mult in (("AC", 1.35), ("AC(N)", 1.45), ("AC(H)", 1.55)):
            row[col] = scale_int(row[col], mult)
        for col, mult in (("A1TH", 1.45), ("A1TH(N)", 1.60), ("A1TH(H)", 1.75)):
            row[col] = scale_int(row[col], mult)
        # Signed 16-bit safe (<= 32767) Exp % ratios of monlvl.txt L-XP:
        # Normal: ~33.8k XP (~77% of lvl 14->15), NM: ~1.73M XP (~37% of lvl 49->50), Hell: ~10.9M XP (~23% of lvl 76->77)
        row["Exp"], row["Exp(N)"], row["Exp(H)"] = "20000", "28000", "28000"
        return True

    if mon_id == "duriel":
        row["Level"], row["Level(N)"], row["Level(H)"] = "22", "55", "85"
        # Relentless arena pursuit (Velocity 9 / Run 13) + higher Charge/Jab/Smite/HolyFreeze levels
        row["Velocity"], row["Run"] = "9", "13"
        row["aidist"], row["aidist(N)"], row["aidist(H)"] = "45", "50", "55"
        row["Crit"] = "25"
        row["Sk1lvl"], row["Sk2lvl"], row["Sk3lvl"], row["Sk4lvl"] = "7", "18", "10", "5"
        row["MonProp"] = "duriel"
        row["ToBlock"], row["ToBlock(N)"], row["ToBlock(H)"] = "0", "0", "0"
        # Strengths: Holy Freeze (Sk4lvl=5), 50% Crushing Blow, 80/90/95 Cold Res, 40/50/60 Phys Res
        # Weaknesses: Fire & Ltng Res -30% (N) -> -20% (NM) -> -10% (H)
        row["ResDm"], row["ResDm(N)"], row["ResDm(H)"] = "40", "50", "60"
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "25", "40", "55"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "-30", "-20", "-10"
        row["ResLi"], row["ResLi(N)"], row["ResLi(H)"] = "-30", "-20", "-10"
        row["ResCo"], row["ResCo(N)"], row["ResCo(H)"] = "80", "90", "95"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "45", "65", "80"
        for col, mult in (("minHP", 2.75), ("maxHP", 2.75), ("MinHP(N)", 3.05), ("MaxHP(N)", 3.05), ("MinHP(H)", 3.35), ("MaxHP(H)", 3.35)):
            row[col] = scale_int(row[col], mult)
        for col in ("A1MinD", "A1MaxD", "A2MinD", "A2MaxD"):
            row[col] = scale_int(row[col], 1.75)
        for col in ("A1MinD(N)", "A1MaxD(N)", "A2MinD(N)", "A2MaxD(N)"):
            row[col] = scale_int(row[col], 1.90)
        for col in ("A1MinD(H)", "A1MaxD(H)", "A2MinD(H)", "A2MaxD(H)"):
            row[col] = scale_int(row[col], 2.10)
        for col, mult in (("AC", 1.40), ("AC(N)", 1.50), ("AC(H)", 1.60)):
            row[col] = scale_int(row[col], mult)
        for col, mult in (("A1TH", 1.50), ("A2TH", 1.50), ("A1TH(N)", 1.65), ("A2TH(N)", 1.65), ("A1TH(H)", 1.80), ("A2TH(H)", 1.80)):
            if row.get(col, ""):
                row[col] = scale_int(row[col], mult)
        # Signed 16-bit safe (<= 32767) Exp % ratios of monlvl.txt L-XP:
        # Normal: ~90.8k XP (~35% of lvl 22->23), NM: ~2.59M XP (~33% of lvl 55->56), Hell: ~14.8M XP
        row["Exp"], row["Exp(N)"], row["Exp(H)"] = "25000", "29000", "29000"
        return True

    if mon_id == "mephisto":
        row["Level"], row["Level(N)"], row["Level(H)"] = "26", "59", "87"
        row["Velocity"], row["Run"] = "9", "10"
        row["aidist"], row["aidist(N)"], row["aidist(H)"] = "45", "50", "55"
        row["Crit"] = "25"
        row["Sk1lvl"], row["Sk2lvl"], row["Sk3lvl"], row["Sk4lvl"], row["Sk5lvl"], row["Sk6lvl"] = "8", "8", "9", "8", "4", "8"
        row["MonProp"] = "mephisto"
        row["ToBlock"], row["ToBlock(N)"], row["ToBlock(H)"] = "0", "0", "0"
        # Strengths: +40% FCR/IAS, 75/85/90 Ltng & Cold Res, 70/80/90 Poison Res
        # Weaknesses: Phys Res -20% -> -10% -> -5% (0% Block), Fire & Magic Res -30% -> -20% -> -10%
        row["ResDm"], row["ResDm(N)"], row["ResDm(H)"] = "-20", "-10", "-5"
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "-30", "-20", "-10"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "-30", "-20", "-10"
        row["ResLi"], row["ResLi(N)"], row["ResLi(H)"] = "75", "85", "90"
        row["ResCo"], row["ResCo(N)"], row["ResCo(H)"] = "75", "85", "90"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "70", "80", "90"
        for col, mult in (("minHP", 2.85), ("maxHP", 2.85), ("MinHP(N)", 3.15), ("MaxHP(N)", 3.15), ("MinHP(H)", 3.50), ("MaxHP(H)", 3.50)):
            row[col] = scale_int(row[col], mult)
        for col, mult in (("A1MinD", 1.70), ("A1MaxD", 1.70), ("A1MinD(N)", 1.85), ("A1MaxD(N)", 1.85), ("A1MinD(H)", 2.05), ("A1MaxD(H)", 2.05)):
            row[col] = scale_int(row[col], mult)
        for col, mult in (("AC", 1.35), ("AC(N)", 1.45), ("AC(H)", 1.55)):
            row[col] = scale_int(row[col], mult)
        for col, mult in (("A1TH", 1.45), ("A1TH(N)", 1.60), ("A1TH(H)", 1.75)):
            row[col] = scale_int(row[col], mult)
        # Signed 16-bit safe (<= 32767) Exp % ratios of monlvl.txt L-XP:
        # Normal: ~140.8k XP (~22% of lvl 26->27), NM: ~3.39M XP (~31% of lvl 59->60), Hell: ~16.2M XP
        row["Exp"], row["Exp(N)"], row["Exp(H)"] = "28000", "30000", "30000"
        return True

    if mon_id == "diablo":
        row["Level"], row["Level(N)"], row["Level(H)"] = "32", "63", "92"
        row["Velocity"], row["Run"] = "9", "12"
        row["aidist"], row["aidist(N)"], row["aidist(H)"] = "45", "50", "55"
        row["Crit"] = "28"
        row["Sk1lvl"], row["Sk2lvl"], row["Sk3lvl"], row["Sk4lvl"], row["Sk5lvl"], row["Sk6lvl"] = "6", "6", "7", "5", "7", "10"
        row["MonProp"] = "diablo"
        row["ToBlock"], row["ToBlock(N)"], row["ToBlock(H)"] = "10", "15", "20"
        # Strengths: 75/85/90 Fire & 70/80/85 Ltng Res, 40% Deadly Strike, 30/40/50 Phys Res
        # Weaknesses: Cold Res -30% -> -20% -> -10%, Magic Res -25% -> -15% -> -10%
        row["ResDm"], row["ResDm(N)"], row["ResDm(H)"] = "30", "40", "50"
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "-25", "-15", "-10"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "75", "85", "90"
        row["ResLi"], row["ResLi(N)"], row["ResLi(H)"] = "70", "80", "85"
        row["ResCo"], row["ResCo(N)"], row["ResCo(H)"] = "-30", "-20", "-10"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "45", "60", "75"
        for col, mult in (("minHP", 2.95), ("maxHP", 2.95), ("MinHP(N)", 3.25), ("MaxHP(N)", 3.25), ("MinHP(H)", 3.60), ("MaxHP(H)", 3.60)):
            row[col] = scale_int(row[col], mult)
        for col in ("A1MinD", "A1MaxD", "A2MinD", "A2MaxD"):
            row[col] = scale_int(row[col], 1.75)
        for col in ("A1MinD(N)", "A1MaxD(N)", "A2MinD(N)", "A2MaxD(N)"):
            row[col] = scale_int(row[col], 1.90)
        for col in ("A1MinD(H)", "A1MaxD(H)", "A2MinD(H)", "A2MaxD(H)"):
            row[col] = scale_int(row[col], 2.10)
        for col, mult in (("AC", 1.40), ("AC(N)", 1.50), ("AC(H)", 1.60)):
            row[col] = scale_int(row[col], mult)
        for col, mult in (("A1TH", 1.50), ("A2TH", 1.50), ("A1TH(N)", 1.65), ("A2TH(N)", 1.65), ("A1TH(H)", 1.80), ("A2TH(H)", 1.80)):
            if row.get(col, ""):
                row[col] = scale_int(row[col], mult)
        # Signed 16-bit safe (<= 32767) Exp % ratios of monlvl.txt L-XP:
        # Normal: ~234.1k XP (~22% of lvl 32->33), NM: ~4.42M XP (~28% of lvl 63->64), Hell: ~18.8M XP
        row["Exp"], row["Exp(N)"], row["Exp(H)"] = "31000", "31000", "31000"
        return True

    if mon_id == "baalcrab":
        row["Level"], row["Level(N)"], row["Level(H)"] = "42", "75", "99"
        row["Velocity"], row["Run"] = "8", "10"
        row["aidist"], row["aidist(N)"], row["aidist(H)"] = "45", "50", "55"
        row["Crit"] = "30"
        row["Sk1lvl"], row["Sk2lvl"], row["Sk3lvl"], row["Sk4lvl"], row["Sk6lvl"], row["Sk7lvl"] = "4", "4", "4", "4", "5", "5"
        row["MonProp"] = "baalcrab"
        row["ToBlock"], row["ToBlock(N)"], row["ToBlock(H)"] = "10", "15", "20"
        # Strengths: 55/65/75 Fire/Cold/Magic Res, 45% Open Wounds
        # Weaknesses: Phys Res -10% -> -5% -> 0%, Ltng & Pois Res -25% -> -15% -> -10%
        row["ResDm"], row["ResDm(N)"], row["ResDm(H)"] = "-10", "-5", "0"
        row["ResMa"], row["ResMa(N)"], row["ResMa(H)"] = "55", "65", "75"
        row["ResFi"], row["ResFi(N)"], row["ResFi(H)"] = "55", "65", "75"
        row["ResLi"], row["ResLi(N)"], row["ResLi(H)"] = "-25", "-15", "-10"
        row["ResCo"], row["ResCo(N)"], row["ResCo(H)"] = "55", "65", "75"
        row["ResPo"], row["ResPo(N)"], row["ResPo(H)"] = "-25", "-15", "-10"
        for col, mult in (("minHP", 3.00), ("maxHP", 3.00), ("MinHP(N)", 3.35), ("MaxHP(N)", 3.35), ("MinHP(H)", 3.75), ("MaxHP(H)", 3.75)):
            row[col] = scale_int(row[col], mult)
        for col in ("A1MinD", "A1MaxD", "A2MinD", "A2MaxD"):
            row[col] = scale_int(row[col], 1.75)
        for col in ("A1MinD(N)", "A1MaxD(N)", "A2MinD(N)", "A2MaxD(N)"):
            row[col] = scale_int(row[col], 1.90)
        for col in ("A1MinD(H)", "A1MaxD(H)", "A2MinD(H)", "A2MaxD(H)"):
            row[col] = scale_int(row[col], 2.10)
        for col, mult in (("AC", 1.40), ("AC(N)", 1.50), ("AC(H)", 1.60)):
            row[col] = scale_int(row[col], mult)
        for col, mult in (("A1TH", 1.50), ("A2TH", 1.50), ("A1TH(N)", 1.65), ("A2TH(N)", 1.65), ("A1TH(H)", 1.80), ("A2TH(H)", 1.80)):
            if row.get(col, ""):
                row[col] = scale_int(row[col], mult)
        # Signed 16-bit safe (<= 32767) Exp % ratios of monlvl.txt L-XP:
        # Normal: ~475.2k XP (~19% of lvl 42->43), NM: ~8.02M XP (~18% of lvl 75->76), Hell: ~22.5M XP
        row["Exp"], row["Exp(N)"], row["Exp(H)"] = "32000", "32000", "32000"
        return True

    return False


def _configure_baal_wave_monsters(
    row: dict, mon_id: str
) -> tuple[bool, str | None, str | None]:
    if mon_id not in ("unraveler5", "baalhighpriest", "venomlord", "baalminion1", "baalminion2", "baalminion3"):
        return False, None, None

    row["aidist"], row["aidist(N)"], row["aidist(H)"] = "42", "46", "50"
    row["Crit"] = "20"
    for col, mult in (("minHP", 2.40), ("maxHP", 2.40), ("MinHP(N)", 2.75), ("MaxHP(N)", 2.75), ("MinHP(H)", 3.10), ("MaxHP(H)", 3.10)):
        row[col] = scale_int(row[col], mult)
    for col in (
        "A1MinD", "A1MaxD", "A2MinD", "A2MaxD", "S1MinD", "S1MaxD",
        "El1MinD", "El1MaxD", "El2MinD", "El2MaxD", "El3MinD", "El3MaxD",
        "A1MinD(N)", "A1MaxD(N)", "A2MinD(N)", "A2MaxD(N)", "S1MinD(N)", "S1MaxD(N)",
        "El1MinD(N)", "El1MaxD(N)", "El2MinD(N)", "El2MaxD(N)", "El3MinD(N)", "El3MaxD(N)",
        "A1MinD(H)", "A1MaxD(H)", "A2MinD(H)", "A2MaxD(H)", "S1MinD(H)", "S1MaxD(H)",
        "El1MinD(H)", "El1MaxD(H)", "El2MinD(H)", "El2MaxD(H)", "El3MinD(H)", "El3MaxD(H)",
    ):
        if row.get(col, ""):
            row[col] = scale_int(row[col], 1.60)
    for i in range(1, 9):
        sk_lvl = parse_int(row.get(f"Sk{i}lvl", "0"))
        if sk_lvl > 0:
            row[f"Sk{i}lvl"] = str(sk_lvl + 6)
    for col in ("AC", "AC(N)", "AC(H)"):
        if row.get(col, ""):
            row[col] = scale_int(row[col], 1.35)
    for col in ("A1TH", "A2TH", "A1TH(N)", "A2TH(N)", "A1TH(H)", "A2TH(H)"):
        if row.get(col, ""):
            row[col] = scale_int(row[col], 1.45)
    for col in ("Exp", "Exp(N)", "Exp(H)"):
        row[col] = scale_int(row[col], 4.8)

    # Apply the 10%/20%/30% difficulty baseline with ±70% (2x35%) steps and 99% cap
    if mon_id == "unraveler5":
        v_el, r_el = "Fi", "Ma"
    elif mon_id in ("baalhighpriest", "venomlord"):
        v_el, r_el = "Co", "Fi"
    else:  # baalminion1..3
        v_el, r_el = "Ma", "Fi"

    _apply_affinity_resists(row, v_el, 2, r_el, 2)
    return True, v_el, r_el


def _configure_quest_superuniques(row: dict, mon_id: str) -> bool:
    """
    Configure dedicated Quest & Act Sub-Boss SuperUniques (Blood Raven, Griswold, The Smith,
    Radament, Summoner, Izual, Hephasto, Nihlathak, The Ancients, Cow King, Dark Elder, Coldworm)
    so their HP, damage, velocity, defense, AR, critical strike chance, skill levels, and AI
    aggro distance scale progressively across Normal -> Nightmare -> Hell while exaggerating
    each boss's distinct combat character.
    """
    quest_boss_ids = {
        "bloodraven", "griswold", "smith", "radament", "summoner",
        "maggotqueen1", "maggotqueen2", "maggotqueen3", "maggotqueen4", "maggotqueen5",
        "darkelder", "izual", "hephasto",
        "nihlathakboss", "ancientbarb1", "ancientbarb2", "ancientbarb3",
        "cowking",
    }
    if mon_id not in quest_boss_ids:
        return False

    row["aidist"], row["aidist(N)"], row["aidist(H)"] = "42", "46", "50"
    row["Crit"] = "22"

    # Cap any >= 100% resistance at 99% so no quest boss triggers native "Immune to X"
    for rtype in ("Dm", "Ma", "Fi", "Li", "Co", "Po"):
        for sfx in ("", "(N)", "(H)"):
            col = f"Res{rtype}{sfx}"
            if parse_int(row.get(col, "0")) >= 100:
                row[col] = "99"

    # Progressive HP multipliers (Normal 2.8x -> Nightmare 3.2x -> Hell 3.6x)
    # Summoner & Nihlathak start with very low vanilla glass-cannon HP (129 / 191), so give them a 4.0x..5.0x pool
    if mon_id in ("summoner", "nihlathakboss"):
        hp_n, hp_nm, hp_h = 3.80, 4.40, 5.00
    elif mon_id in ("ancientbarb1", "ancientbarb2", "ancientbarb3"):
        hp_n, hp_nm, hp_h = 2.40, 2.75, 3.10
    else:
        hp_n, hp_nm, hp_h = 2.85, 3.25, 3.65

    for col, mult in (
        ("minHP", hp_n), ("maxHP", hp_n),
        ("MinHP(N)", hp_nm), ("MaxHP(N)", hp_nm),
        ("MinHP(H)", hp_h), ("MaxHP(H)", hp_h),
    ):
        if row.get(col, ""):
            row[col] = scale_int(row[col], mult)

    # Progressive Physical & Elemental Damage (Normal 1.65x -> Nightmare 1.85x -> Hell 2.05x)
    for col, mult in (
        ("A1MinD", 1.65), ("A1MaxD", 1.65), ("A2MinD", 1.65), ("A2MaxD", 1.65), ("S1MinD", 1.65), ("S1MaxD", 1.65),
        ("El1MinD", 1.65), ("El1MaxD", 1.65), ("El2MinD", 1.65), ("El2MaxD", 1.65),
        ("A1MinD(N)", 1.85), ("A1MaxD(N)", 1.85), ("A2MinD(N)", 1.85), ("A2MaxD(N)", 1.85), ("S1MinD(N)", 1.85), ("S1MaxD(N)", 1.85),
        ("El1MinD(N)", 1.85), ("El1MaxD(N)", 1.85), ("El2MinD(N)", 1.85), ("El2MaxD(N)", 1.85),
        ("A1MinD(H)", 2.05), ("A1MaxD(H)", 2.05), ("A2MinD(H)", 2.05), ("A2MaxD(H)", 2.05), ("S1MinD(H)", 2.05), ("S1MaxD(H)", 2.05),
        ("El1MinD(H)", 2.05), ("El1MaxD(H)", 2.05), ("El2MinD(H)", 2.05), ("El2MaxD(H)", 2.05),
    ):
        if row.get(col, ""):
            row[col] = scale_int(row[col], mult)

    # Progressive Defense (1.35x -> 1.45x -> 1.55x) & Attack Rating (1.45x -> 1.60x -> 1.75x)
    for col, mult in (("AC", 1.35), ("AC(N)", 1.45), ("AC(H)", 1.55)):
        if row.get(col, ""):
            row[col] = scale_int(row[col], mult)
    for col, mult in (
        ("A1TH", 1.45), ("A2TH", 1.45), ("S1TH", 1.45),
        ("A1TH(N)", 1.60), ("A2TH(N)", 1.60), ("S1TH(N)", 1.60),
        ("A1TH(H)", 1.75), ("A2TH(H)", 1.75), ("S1TH(H)", 1.75),
    ):
        if row.get(col, ""):
            row[col] = scale_int(row[col], mult)

    # Velocity & Character-Specific Exaggeration
    vel = parse_int(row.get("Velocity", "0"))
    run_v = parse_int(row.get("Run", "0"))
    if vel > 0:
        row["Velocity"] = str(min(14, vel + 2))
    if run_v > 0:
        row["Run"] = str(min(18, run_v + 2))

    # Boost all active quest boss skills by +6 levels
    for i in range(1, 9):
        sk_lvl = parse_int(row.get(f"Sk{i}lvl", "0"))
        if sk_lvl > 0:
            row[f"Sk{i}lvl"] = str(sk_lvl + 6)

    if mon_id in (
        "bloodraven", "griswold", "smith", "radament", "maggotqueen1",
        "summoner", "izual", "hephasto", "nihlathakboss",
    ):
        row["MonProp"] = mon_id

    for col in ("Exp", "Exp(N)", "Exp(H)"):
        if row.get(col, ""):
            row[col] = scale_int(row[col], 4.8)

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

    if mon_id == "wakeofdestruction":
        row["aidist"] = "25"
        for sfx in ("", "(N)", "(H)"):
            row[f"aidel{sfx}"] = "11"
            row[f"aip2{sfx}"] = "14"
            row[f"aip3{sfx}"] = "18"
            row[f"aip4{sfx}"] = "15"
        row["SendSkills"] = "31"
        row["Skill2"] = "Wake of Fire Sentry"
        row["Skill3"] = "Fists of Fire"
        row["Skill4"] = "Ass Trap Charge Consume"
        row["Skill5"] = "Fire Trauma"
        return True

    if mon_id == "infernosentry":
        row["aidist"] = "25"
        for sfx in ("", "(N)", "(H)"):
            row[f"aidel{sfx}"] = "4"
            row[f"aip2{sfx}"] = "4"
            row[f"aip3{sfx}"] = "5"
            row[f"aip4{sfx}"] = "25"
        row["Level"] = "30"
        row["Level(N)"] = "60"
        row["Level(H)"] = "85"
        row["A1TH"] = "9999"
        row["A1TH(N)"] = "9999"
        row["A1TH(H)"] = "9999"
        row["MonProp"] = "infernosentry"
        row["SendSkills"] = "31"
        row["Skill1"] = "mon inferno sentry"
        row["Sk1mode"] = "S2"
        row["Sk1lvl"] = "1"
        row["Skill2"] = "Fire Trauma"
        row["Sk2mode"] = "S1"
        row["Sk2lvl"] = "0"
        row["Skill3"] = "Tiger Strike"
        row["Skill4"] = "Ass Trap Charge Consume"
        row["Skill5"] = "Shock Field"
        return True

    if mon_id == "chargeboltsentry":
        row["Code"] = "e9"
        row["MonStatsEx"] = "wakeofdestruction"
        row["aidist"] = "25"
        for sfx in ("", "(N)", "(H)"):
            row[f"aidel{sfx}"] = "5"
            row[f"aip2{sfx}"] = "5"
            row[f"aip3{sfx}"] = "6"
            row[f"aip4{sfx}"] = "25"
        row["SendSkills"] = "31"
        row["Skill1"] = "BoltSentry"
        row["Sk1mode"] = "S2"
        row["Sk1lvl"] = "1"
        row["Skill2"] = "Charged Bolt Sentry"
        row["Sk2mode"] = "S1"
        row["Sk2lvl"] = "0"
        row["Skill3"] = "Cobra Strike"
        row["Skill4"] = "Ass Trap Charge Consume"
        row["Skill5"] = "Fire Trauma"
        return True

    if mon_id == "lightningsentry":
        row["Code"] = "e9"
        row["MonStatsEx"] = "wakeofdestruction"
        row["AI"] = "AssassinSentry"
        row["aidist"] = "25"
        for sfx in ("", "(N)", "(H)"):
            row[f"aidel{sfx}"] = "7"
            row[f"aip1{sfx}"] = "100"
            row[f"aip2{sfx}"] = "8"
            row[f"aip3{sfx}"] = "9"
            row[f"aip4{sfx}"] = "25"
        row["SendSkills"] = "31"
        row["Skill1"] = "sentry lightning"
        row["Sk1mode"] = "S2"
        row["Sk1lvl"] = "1"
        row["Skill2"] = "Lightning Sentry"
        row["Sk2mode"] = "S1"
        row["Sk2lvl"] = "0"
        row["Skill3"] = "Claws of Thunder"
        row["Skill4"] = "Ass Trap Charge Consume"
        row["Skill5"] = "Wake of Fire Sentry"
        return True

    if mon_id == "deathsentry":
        row["Code"] = "e9"
        row["MonStatsEx"] = "wakeofdestruction"
        row["AI"] = "AssassinSentry"
        row["aidist"] = "25"
        for sfx in ("", "(N)", "(H)"):
            row[f"aidel{sfx}"] = "1"
            row[f"aip1{sfx}"] = "100"
            row[f"aip2{sfx}"] = "1"
            row[f"aip3{sfx}"] = "1"
            row[f"aip4{sfx}"] = "25"
        row["SendSkills"] = "31"
        row["Skill1"] = "mon death sentry"
        row["Sk1mode"] = "S2"
        row["Sk1lvl"] = "1"
        row["Skill2"] = "Death Sentry"
        row["Sk2mode"] = "S1"
        row["Sk2lvl"] = "0"
        row["Skill3"] = "Blades of Ice"
        row["Skill4"] = "Ass Trap Charge Consume"
        row["Skill5"] = "Wake of Fire Sentry"
        return True

    return False


def _configure_trap_entities(row: dict, mon_id: str) -> bool:
    """
    Configure stationary chest/environmental trap entities ('a trap' in monstats.txt)
    so their Level, attack damage, and skill scaling progress across Normal, Nightmare, and Hell
    with high min-max roll variance (hitting ~50% of expected character Life at 50% resistance).
    """
    if mon_id not in (
        "trap-firebolt",
        "trap-horzmissile",
        "trap-vertmissile",
        "trap-poisoncloud",
        "trap-lightning",
        "trap-melee",
        "trap-nova",
    ):
        return False

    row["Level"], row["Level(N)"], row["Level(H)"] = "18", "48", "78"
    if row.get("Skill1"):
        row["Sk1lvl"] = "4"
    if row.get("Skill2"):
        row["Sk2lvl"] = "4"

    if mon_id in ("trap-horzmissile", "trap-vertmissile", "trap-melee"):
        row["A1MinD"], row["A1MaxD"] = "95", "300"
        row["A1MinD(N)"], row["A1MaxD(N)"] = "360", "980"
        row["A1MinD(H)"], row["A1MaxD(H)"] = "680", "1750"
        row["A1TH"], row["A1TH(N)"], row["A1TH(H)"] = "3500", "6500", "9500"

    if mon_id in ("trap-horzmissile", "trap-vertmissile") and row.get("El1Type") == "pois":
        row["El1MinD"], row["El1MaxD"], row["El1Dur"] = "60", "140", "150"
        row["El1MinD(N)"], row["El1MaxD(N)"], row["El1Dur(N)"] = "180", "380", "150"
        row["El1MinD(H)"], row["El1MaxD(H)"], row["El1Dur(H)"] = "340", "680", "150"

    return True


def _get_descstr_pool() -> list[tuple[int, str, str]]:
    """
    Return a deterministic list of (id, Key, source_file)
    for .tbl-backed string keys (id < 23000) safe to use in monstats.txt DescStr.
    Strictly uses the 108 legacy unused D2bnetHelp* keys from bnet.json so that zero
    existing vanilla keys in monsters.json (which also holds rare item affixes like GhoulRI
    and interactive object names like TrappDoor) are ever overwritten.
    """
    b_str = read_strings_json("bnet.json")

    pool: list[tuple[int, str, str]] = []
    for e in b_str:
        if e["Key"].startswith("D2bnetHelp") and e["id"] < 23000:
            pool.append((e["id"], e["Key"], "bnet.json"))

    return pool


TACTICAL_DESCSTR_MAP = {
    "drains mana": "Drains Mana",
    "homing missiles": "Drains Mana",
    "drains mana and stamina": "Drains Mana & Stamina",
    "drains stamina": "Drains Stamina",
    "stun attack": "Stun Attack",
    "steals life": "Steals Life",
}


def _format_monster_affinity_desc(
    vuln_elem: str | None, res_elem: str | None, orig_desc_key: str = ""
) -> str:
    parts: list[str] = []
    if vuln_elem:
        parts.append(f"Vulnerable: {RES_COLOR_LABELS[vuln_elem]}")
    if res_elem:
        parts.append(f"Resists: {RES_COLOR_LABELS[res_elem]}")
    tactical_tag = TACTICAL_DESCSTR_MAP.get(orig_desc_key)
    if tactical_tag:
        parts.append(tactical_tag)
    return " | ".join(parts)


def build_monstats(cfg: dict) -> str:
    headers, rows = read_tsv("monstats.txt")
    desc_pool = _get_descstr_pool()
    text_to_key: dict[str, str] = {}
    pool_idx = 0

    def assign_desc_str(
        r: dict, vuln_elem: str | None, res_elem: str | None, orig_d: str = ""
    ) -> None:
        nonlocal pool_idx
        desc_text = _format_monster_affinity_desc(vuln_elem, res_elem, orig_d)
        if not desc_text:
            r["DescStr"] = ""
            return
        if desc_text not in text_to_key:
            if pool_idx >= len(desc_pool):
                raise RuntimeError(f"Exhausted .tbl DescStr pool ({len(desc_pool)} keys)")
            _, k_name, _ = desc_pool[pool_idx]
            pool_idx += 1
            text_to_key[desc_text] = k_name
        r["DescStr"] = text_to_key[desc_text]

    for row in rows:
        mon_id = row.get("Id", "").strip()
        if not mon_id or mon_id == "Expansion":
            continue
        orig_desc = row.get("DescStr", "").strip()

        # 0. Act 1 Rogue Mercenary: Enable equipping Arrows (bowq) in off-hand (slot_left_arm)
        if mon_id == "roguehire":
            row["leftArmItemType"] = "bowq"

        # 1. Capstone Bosses
        if _configure_capstone_bosses(row, mon_id):
            continue

        # 2. Solo-Tuned Baal Throne Room Wave Monsters
        is_wave, wave_v_el, wave_r_el = _configure_baal_wave_monsters(row, mon_id)
        if is_wave:
            assign_desc_str(row, wave_v_el, wave_r_el, orig_desc)
            continue

        # 2b. Quest SuperUniques & Act Minibosses (Blood Raven, Griswold, The Smith, Radament,
        #     The Summoner, Izual, Hephasto, Nihlathak, Coldworm, The Ancients, Cow King)
        if _configure_quest_superuniques(row, mon_id):
            continue

        # 3. Player Summons
        if _configure_player_summons(row, mon_id):
            continue

        # 3b. Stationary Chest & Environmental Trap Entities
        if _configure_trap_entities(row, mon_id):
            continue

        base_id = row.get("BaseId", "").strip()

        # Cap any >= 100% resistance at 99% on killable enemy structures/spawners/sub-entities
        # (excluding Bone Prison and Turret wall objects which use Poison res >= 200 to prevent poison states)
        if (
            row.get("killable", "") == "1"
            and row.get("Align", "") == ""
            and not base_id.startswith("boneprison")
            and base_id != "turret1"
        ):
            for rtype in ("Dm", "Ma", "Fi", "Li", "Co", "Po"):
                for sfx in ("", "(N)", "(H)"):
                    col = f"Res{rtype}{sfx}"
                    if parse_int(row.get(col, "0")) >= 100:
                        row[col] = "99"

        # 4. Regular Spawnable Enemy Monsters (plus maggotbaby1..6 hatched children & putriddefiler1..5)
        if (
            (row.get("isSpawn", "") != "1" and base_id != "maggotbaby1")
            or row.get("killable", "") != "1"
            or row.get("Align", "") != ""
            or (row.get("boss", "") == "1" and base_id != "putriddefiler1")
            or row.get("primeevil", "") == "1"
        ):
            continue

        vel = parse_int(row.get("Velocity", "0"))
        if vel <= 0:
            # Stationary nests/spawners: scale HP by 1.5x, XP by 2.4x, and off-screen aggro radius
            row["aidist"], row["aidist(N)"], row["aidist(H)"] = "38", "42", "46"
            for col in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
                row[col] = scale_int(row[col], 1.50)
            for col in ("Exp", "Exp(N)", "Exp(H)"):
                row[col] = scale_int(row[col], 2.40)
            continue

        # Progressive Off-Screen AI Aggro Distance (1.1x Normal -> 1.2x Nightmare -> 1.3x Hell
        # over D2R's default 35-subtile AI radius: 38 / 42 / 46 subtiles)
        row["aidist"], row["aidist(N)"], row["aidist(H)"] = "38", "42", "46"
        ai_type = row.get("AI", "").strip()
        ai_dist_col = {
            "Zombie": "aip2",
            "Mummy": "aip1",
            "QuillRat": "aip1",
            "Vampire": "aip3",
            "ElementalBeast": "aip2",
            "FrogDemon": "aip8",
            "Tentacle": "aip6",
            "TentacleHead": "aip6",
        }.get(ai_type)
        if ai_dist_col:
            for sfx, mult, floor_v in (("", 1.15, 35), ("(N)", 1.25, 38), ("(H)", 1.35, 42)):
                col_name = f"{ai_dist_col}{sfx}"
                if parse_int(row.get(col_name, "0")) > 0:
                    row[col_name] = scale_int(row[col_name], mult, min_val=floor_v)

        # Remove Open Desert Poison from Sand Leapers (sandleaper1..3)
        if mon_id in ("sandleaper1", "sandleaper2", "sandleaper3") and row.get("El1Type", "") == "pois":
            for c in (
                "El1Mode", "El1Type", "El1Pct", "El1MinD", "El1MaxD", "El1Dur",
                "El1Pct(N)", "El1MinD(N)", "El1MaxD(N)", "El1Dur(N)",
                "El1Pct(H)", "El1MinD(H)", "El1MaxD(H)", "El1Dur(H)",
            ):
                row[c] = ""

        # Align zombie3 (Catacombs 3-4) and mummy4 (Tal Rasha's Tombs) base TCs with their earliest Act
        # so they never drop next-Act TCs early (while still auto-upgrading via group/level when spawned in Act 3 NM/H)
        if mon_id == "zombie3":
            for tcol in (
                "TreasureClass", "TreasureClassChamp", "TreasureClassUnique",
                "TreasureClassDesecratedChamp", "TreasureClassDesecratedUnique",
                "TreasureClass(N)", "TreasureClassChamp(N)", "TreasureClassUnique(N)",
                "TreasureClassDesecratedChamp(N)", "TreasureClassDesecratedUnique(N)",
                "TreasureClass(H)", "TreasureClassChamp(H)", "TreasureClassUnique(H)",
                "TreasureClassDesecratedChamp(H)", "TreasureClassDesecratedUnique(H)",
            ):
                if row.get(tcol, "").startswith("Act 2"):
                    row[tcol] = "Act 1" + row[tcol][5:]
        elif mon_id == "mummy4":
            for tcol in (
                "TreasureClass", "TreasureClassChamp", "TreasureClassUnique",
                "TreasureClassDesecratedChamp", "TreasureClassDesecratedUnique",
                "TreasureClass(N)", "TreasureClassChamp(N)", "TreasureClassUnique(N)",
                "TreasureClassDesecratedChamp(N)", "TreasureClassDesecratedUnique(N)",
                "TreasureClass(H)", "TreasureClassChamp(H)", "TreasureClassUnique(H)",
                "TreasureClassDesecratedChamp(H)", "TreasureClassDesecratedUnique(H)",
            ):
                if row.get(tcol, "").startswith("Act 3"):
                    row[tcol] = "Act 2" + row[tcol][5:].replace(" B", " C")

        # Assign Skeleton monster families ('<TC> Skel') so they have a subtle ~2.5x-3.1x higher probability
        # of dropping Skulls over other Gems while preserving 75% regular Gem drops
        if base_id in (
            "skeleton1",
            "sk_archer1",
            "skmage_pois1",
            "skmage_cold1",
            "skmage_fire1",
            "skmage_ltng1",
            "bonefetish1",
            "doomknight1",
            "doomknight2",
            "doomknight3",
        ):
            for tcol in (
                "TreasureClass", "TreasureClassChamp", "TreasureClassUnique",
                "TreasureClassDesecratedChamp", "TreasureClassDesecratedUnique",
                "TreasureClass(N)", "TreasureClassChamp(N)", "TreasureClassUnique(N)",
                "TreasureClassDesecratedChamp(N)", "TreasureClassDesecratedUnique(N)",
                "TreasureClass(H)", "TreasureClassChamp(H)", "TreasureClassUnique(H)",
                "TreasureClassDesecratedChamp(H)", "TreasureClassDesecratedUnique(H)",
            ):
                tval = row.get(tcol, "").strip()
                if tval and not tval.endswith(" Skel"):
                    row[tcol] = f"{tval} Skel"

        # Classify into 4 Archetypes (strictly clamping group/party sizes to never exceed vanilla)
        van_min_grp = parse_int(row.get("MinGrp", ""), 1)
        van_max_grp = parse_int(row.get("MaxGrp", ""), 1)
        van_p_min = parse_int(row.get("PartyMin", ""), 0)
        van_p_max = parse_int(row.get("PartyMax", ""), 0)

        if base_id in HEAVY_BRUTE_BASES:
            if row.get("MinGrp", ""):
                row["MinGrp"] = str(min(van_min_grp, 1))
            if row.get("MaxGrp", ""):
                row["MaxGrp"] = str(min(van_max_grp, 2))
            if van_p_min > 0:
                row["PartyMin"] = str(min(van_p_min, 1))
                row["PartyMax"] = str(min(van_p_max, 1))
            # Never increase a Heavy Brute's walk speed above vanilla (keep zombie1..5 at Velocity=1, Run=2)
            row["Velocity"] = str(min(vel, max(1, vel - 1)))
            if base_id == "zombie1" and parse_int(row.get("Run", "0")) > 0:
                row["Run"] = str(min(parse_int(row["Run"]), 2))
            row["Crit"] = "15"
            hp_mult, dmg_mult, ar_mult, sk_bonus = 3.40, 1.70, 1.50, 4
        elif base_id in SWARMER_BASES:
            # Preserve 100% vanilla MinGrp, MaxGrp, PartyMin, PartyMax so swarm packs match vanilla count
            row["Velocity"] = str(min(15, vel + 2))
            if parse_int(row.get("Run", "")) > 0:
                row["Run"] = str(min(18, parse_int(row["Run"]) + 2))
            row["Crit"] = "10"
            hp_mult, dmg_mult, ar_mult, sk_bonus = 1.30, 1.20, 1.25, 2
        elif base_id in ARCANE_CASTER_BASES:
            # Preserve full vanilla Shaman minion retinues on Fallen/Fetish Shamans; cap other casters
            if base_id not in ("fallenshaman1", "fetishshaman1"):
                if row.get("MinGrp", ""):
                    row["MinGrp"] = str(min(van_min_grp, 2))
                if row.get("MaxGrp", ""):
                    row["MaxGrp"] = str(min(van_max_grp, 3))
                if van_p_min > 0:
                    row["PartyMin"] = str(min(van_p_min, 2))
                    row["PartyMax"] = str(min(van_p_max, 3))
            row["Crit"] = "12"
            hp_mult, dmg_mult, ar_mult, sk_bonus = 2.15, 1.50, 1.35, 6
        else:
            # Elite Infantry
            if row.get("MinGrp", ""):
                row["MinGrp"] = str(min(van_min_grp, 2))
            if row.get("MaxGrp", ""):
                row["MaxGrp"] = str(min(van_max_grp, 4))
            if van_p_min > 0:
                row["PartyMin"] = str(min(van_p_min, 1))
                row["PartyMax"] = str(min(van_p_max, 2))
            row["Crit"] = "12"
            hp_mult, dmg_mult, ar_mult, sk_bonus = 2.50, 1.45, 1.40, 4

        # Boost monster skill levels by archetype (+2 Swarmers, +4 Infantry/Brutes, +6 Arcane Casters)
        for i in range(1, 9):
            sk_lvl = parse_int(row.get(f"Sk{i}lvl", "0"))
            if sk_lvl > 0:
                row[f"Sk{i}lvl"] = str(sk_lvl + sk_bonus)

        # Dedicated SuperUnique monster classes (Council Members, Infector/Seis/Vizier,
        # Shenk, Pindleskin, Frozenstein, etc.) get heightened Crit, off-screen aggro, and +2 extra skill levels
        if mon_id in (
            "corruptrogue4", "councilmember1", "councilmember2", "councilmember3",
            "unraveler3", "megademon3", "doomknight3", "fingermage3", "fetishshaman4",
            "clawviper3", "thornhulk3", "reanimatedhorde5", "snowyeti4", "siegebeast3",
            "overseer1", "minionspawner1",
        ):
            row["Crit"] = "18"
            row["aidist"], row["aidist(N)"], row["aidist(H)"] = "42", "46", "50"
            for i in range(1, 9):
                sk_lvl = parse_int(row.get(f"Sk{i}lvl", "0"))
                if sk_lvl > 0:
                    row[f"Sk{i}lvl"] = str(sk_lvl + 2)

        # Scale HP progressively across Normal, Nightmare (+10%), and Hell (+20%)
        for sfx, prog in (("", 1.00), ("(N)", 1.10), ("(H)", 1.20)):
            min_c = "minHP" if sfx == "" else f"MinHP{sfx}"
            max_c = "maxHP" if sfx == "" else f"MaxHP{sfx}"
            row[min_c] = scale_int(row[min_c], hp_mult * prog)
            row[max_c] = scale_int(row[max_c], hp_mult * prog)

        # Scale Defense progressively across Normal, Nightmare, and Hell
        for sfx, ac_mult in (("", 1.15), ("(N)", 1.25), ("(H)", 1.35)):
            ac_col = f"AC{sfx}"
            if row.get(ac_col, ""):
                row[ac_col] = scale_int(row[ac_col], ac_mult)

        # Scale Physical, Skill & Elemental Damage (El1..El3) progressively across Normal, Nightmare (+8%), and Hell (+18%)
        for sfx, prog in (("", 1.00), ("(N)", 1.08), ("(H)", 1.18)):
            for prefix in (
                "A1MinD", "A1MaxD", "A2MinD", "A2MaxD", "S1MinD", "S1MaxD",
                "El1MinD", "El1MaxD", "El2MinD", "El2MaxD", "El3MinD", "El3MaxD",
            ):
                col = f"{prefix}{sfx}"
                if row.get(col, ""):
                    row[col] = scale_int(row[col], dmg_mult * prog)

        # Scale Attack Rating progressively across Normal, Nightmare (+8%), and Hell (+15%)
        for sfx, prog in (("", 1.00), ("(N)", 1.08), ("(H)", 1.15)):
            for prefix in ("A1TH", "A2TH", "S1TH"):
                col = f"{prefix}{sfx}"
                if row.get(col, ""):
                    row[col] = scale_int(row[col], ar_mult * prog)

        # Scale Experience (3.84x — reduced 20% from 4.80x)
        xp_mult = float(cfg.get("pacing", {}).get("normal_monster_xp_multiplier", 3.84))
        for col in ("Exp", "Exp(N)", "Exp(H)"):
            row[col] = scale_int(row[col], xp_mult)

        # Apply 10%/20%/30% difficulty baseline with ±35%/±70% steps and 99% cap
        v_el, r_el = _apply_monster_resistances(row, base_id, mon_id)

        # Populate concise custom affinity + tactical subtitle via DescStr (or clear DescStr if Neutral)
        assign_desc_str(row, v_el, r_el, orig_desc)

    # 5. Optional Exploration Dungeon Monsters:
    #    a) Clone the 34 remapped shared monsters/minions/spawns (src_id -> dst_id) preserving dst_id's Id and *hcIdx
    by_id = {r.get("Id", "").strip(): r for r in rows if r.get("Id", "").strip()}
    for src_id, dst_id in OPT_FULL_MONSTER_REMAP.items():
        src_r = by_id[src_id]
        dst_r = by_id[dst_id]
        keep_id = dst_r["Id"]
        keep_hc = dst_r.get("*hcIdx", "")
        for k, v in src_r.items():
            dst_r[k] = v
        dst_r["Id"] = keep_id
        dst_r["*hcIdx"] = keep_hc

    #    b) Scale all 55 Optional Dungeon monsters by +20% difficulty (1.20x HP, Damage, AR, Defense, XP),
    #       remap their minion1/minion2/spawn references, and assign '<TC> Opt' (+30% reward probability) TCs
    opt_tc_cols = (
        "TreasureClass", "TreasureClassChamp", "TreasureClassUnique",
        "TreasureClassDesecratedChamp", "TreasureClassDesecratedUnique",
        "TreasureClass(N)", "TreasureClassChamp(N)", "TreasureClassUnique(N)",
        "TreasureClassDesecratedChamp(N)", "TreasureClassDesecratedUnique(N)",
        "TreasureClass(H)", "TreasureClassChamp(H)", "TreasureClassUnique(H)",
        "TreasureClassDesecratedChamp(H)", "TreasureClassDesecratedUnique(H)",
    )
    for opt_id in OPTIONAL_DUNGEON_MONSTER_IDS:
        orow = by_id[opt_id]
        for hcol in ("minHP", "maxHP", "MinHP(N)", "MaxHP(N)", "MinHP(H)", "MaxHP(H)"):
            if orow.get(hcol, ""):
                orow[hcol] = scale_int(orow[hcol], 1.20)
        for scol in (
            "AC", "AC(N)", "AC(H)",
            "Exp", "Exp(N)", "Exp(H)",
            "A1TH", "A2TH", "S1TH",
            "A1TH(N)", "A2TH(N)", "S1TH(N)",
            "A1TH(H)", "A2TH(H)", "S1TH(H)",
            "A1MinD", "A1MaxD", "A2MinD", "A2MaxD", "S1MinD", "S1MaxD",
            "El1MinD", "El1MaxD", "El2MinD", "El2MaxD", "El3MinD", "El3MaxD",
            "A1MinD(N)", "A1MaxD(N)", "A2MinD(N)", "A2MaxD(N)", "S1MinD(N)", "S1MaxD(N)",
            "El1MinD(N)", "El1MaxD(N)", "El2MinD(N)", "El2MaxD(N)", "El3MinD(N)", "El3MaxD(N)",
            "A1MinD(H)", "A1MaxD(H)", "A2MinD(H)", "A2MaxD(H)", "S1MinD(H)", "S1MaxD(H)",
            "El1MinD(H)", "El1MaxD(H)", "El2MinD(H)", "El2MaxD(H)", "El3MinD(H)", "El3MaxD(H)",
        ):
            if orow.get(scol, ""):
                orow[scol] = scale_int(orow[scol], 1.20)
        for mref_col in ("minion1", "minion2", "spawn"):
            mref_val = orow.get(mref_col, "").strip()
            if mref_val in OPT_FULL_MONSTER_REMAP:
                orow[mref_col] = OPT_FULL_MONSTER_REMAP[mref_val]
        for tcol in opt_tc_cols:
            tval = orow.get(tcol, "").strip()
            if tval and not tval.endswith(" Opt"):
                orow[tcol] = f"{tval} Opt"

    # Write allocated .tbl-backed DescStr entries to monsters.json and bnet.json
    pool_by_key = {k_name: (eid, src) for eid, k_name, src in desc_pool}
    m_updates: list[tuple[int, str, str]] = []
    b_updates: list[tuple[int, str, str]] = []
    for desc_text, k_name in text_to_key.items():
        eid, src = pool_by_key[k_name]
        m_updates.append((eid, k_name, desc_text))
        if src == "bnet.json":
            b_updates.append((eid, k_name, desc_text))

    m_entries = upsert_string_entries(read_strings_json("monsters.json"), m_updates)
    write_strings_json("monsters.json", m_entries)
    if b_updates:
        b_entries = upsert_string_entries(read_strings_json("bnet.json"), b_updates)
        write_strings_json("bnet.json", b_entries)

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

    def set_progressive_props(mid: str, prop_specs: list[tuple[str, str, str, str]]) -> None:
        r = ensure_row(mid)
        for idx, (prop_code, val_n, val_nm, val_h) in enumerate(prop_specs, start=1):
            for sfx, val in (("", val_n), (" (N)", val_nm), (" (H)", val_h)):
                r[f"prop{idx}{sfx}"] = prop_code
                r[f"min{idx}{sfx}"] = val
                r[f"max{idx}{sfx}"] = val

    # Act Capstone Bosses — Progressive Signature Properties across Normal -> Nightmare -> Hell
    set_progressive_props("andariel", [
        ("swing2",      "35", "45", "55"),  # +35%/45%/55% IAS
        ("move2",       "25", "35", "45"),  # +25%/35%/45% FRW
        ("pierce-pois", "15", "25", "35"),  # -15%/-25%/-35% Enemy Poison Resist
    ])
    set_progressive_props("duriel", [
        ("crush",       "50", "60", "70"),  # 50%/60%/70% Crushing Blow
        ("swing2",      "25", "35", "45"),  # +25%/35%/45% IAS
        ("deadly",      "25", "35", "45"),  # 25%/35%/45% Deadly Strike
    ])
    set_progressive_props("mephisto", [
        ("cast2",       "40", "50", "60"),  # +40%/50%/60% FCR
        ("swing2",      "40", "50", "60"),  # +40%/50%/60% IAS
        ("pierce-ltng", "15", "25", "35"),  # -15%/-25%/-35% Enemy Lightning Resist
        ("pierce-cold", "15", "25", "35"),  # -15%/-25%/-35% Enemy Cold Resist
    ])
    set_progressive_props("diablo", [
        ("deadly",      "40", "50", "60"),  # 40%/50%/60% Deadly Strike
        ("cast2",       "30", "40", "50"),  # +30%/40%/50% FCR
        ("pierce-fire", "15", "25", "35"),  # -15%/-25%/-35% Enemy Fire Resist
        ("pierce-ltng", "15", "25", "35"),  # -15%/-25%/-35% Enemy Lightning Resist
    ])
    set_progressive_props("baalcrab", [
        ("openwounds",  "45", "55", "65"),  # 45%/55%/65% Open Wounds
        ("crush",       "35", "45", "55"),  # 35%/45%/55% Crushing Blow
        ("cast2",       "30", "40", "50"),  # +30%/40%/50% FCR
    ])

    # Quest SuperUniques — Exaggerated Character-Specific Properties across Normal -> Nightmare -> Hell
    set_progressive_props("bloodraven", [
        ("swing2",      "30", "40", "50"),
        ("move2",       "25", "35", "45"),
        ("deadly",      "20", "30", "40"),
    ])
    set_progressive_props("griswold", [
        ("crush",       "35", "45", "55"),
        ("swing2",      "20", "30", "40"),
    ])
    set_progressive_props("smith", [
        ("crush",       "45", "55", "65"),
        ("swing2",      "30", "40", "50"),
        ("move2",       "20", "30", "40"),
    ])
    set_progressive_props("radament", [
        ("cast2",       "35", "45", "55"),
        ("pierce-pois", "15", "25", "35"),
    ])
    set_progressive_props("maggotqueen1", [
        ("pierce-pois", "20", "30", "40"),
        ("openwounds",  "35", "45", "55"),
    ])
    set_progressive_props("summoner", [
        ("cast2",       "40", "50", "60"),
        ("pierce-cold", "15", "25", "35"),
        ("pierce-fire", "15", "25", "35"),
    ])
    set_progressive_props("izual", [
        ("crush",       "40", "50", "60"),
        ("swing2",      "30", "40", "50"),
        ("pierce-cold", "20", "30", "40"),
    ])
    set_progressive_props("hephasto", [
        ("crush",       "45", "55", "65"),
        ("deadly",      "30", "40", "50"),
        ("swing2",      "25", "35", "45"),
    ])
    set_progressive_props("nihlathakboss", [
        ("cast2",       "35", "45", "55"),
        ("pierce-fire", "15", "25", "35"),
    ])

    r_trap = ensure_row("ass_trap")
    for sfx in ("", " (N)", " (H)"):
        r_trap[f"prop1{sfx}"] = "aura"
        r_trap[f"par1{sfx}"] = "Ass Trap Charge Consume"
        r_trap[f"min1{sfx}"] = "1"
        r_trap[f"max1{sfx}"] = "1"

    # Register the item_openwounds event callback on infernosentry with baseline -1 (<= 0%, matching vanilla druidhawk stupidity -1 -1)
    # so Fire Trauma's passivestat3 (+51 at 3 charges) activates 50% Open Wounds only when deployed with 3 Tiger Strike charges.
    r_inf = ensure_row("infernosentry")
    for sfx in ("", " (N)", " (H)"):
        r_inf[f"prop1{sfx}"] = "openwounds"
        r_inf[f"min1{sfx}"] = "-1"
        r_inf[f"max1{sfx}"] = "-1"

    return write_tsv("monprop.txt", headers, rows)


def build_monumod(cfg: dict) -> str:
    """
    Configure Unique, Champion, and Minion global stat multipliers in monumod.txt (`constants` column)
    so elite packs scale UP progressively across Normal -> Nightmare -> Hell instead of shrinking
    as in vanilla (where Unique HP % drops 300 -> 200 -> 100 and Champion HP % drops 200 -> 150 -> 100).
    """
    headers, rows = read_tsv("monumod.txt")
    progressive_constants = {
        "1":  "125",  # Minion HitPoints % Bonus (Normal)      [Vanilla: 100]
        "2":  "150",  # Minion HitPoints % Bonus (Nightmare)   [Vanilla: 75]
        "3":  "175",  # Minion HitPoints % Bonus (Hell)        [Vanilla: 50]
        "4":  "220",  # Champion HitPoints % Bonus (Normal)    [Vanilla: 200]
        "5":  "260",  # Champion HitPoints % Bonus (Nightmare) [Vanilla: 150]
        "6":  "300",  # Champion HitPoints % Bonus (Hell)      [Vanilla: 100]
        "7":  "320",  # Unique HitPoints % Bonus (Normal)      [Vanilla: 300]
        "8":  "380",  # Unique HitPoints % Bonus (Nightmare)   [Vanilla: 200]
        "9":  "450",  # Unique HitPoints % Bonus (Hell)        [Vanilla: 100]
        "10": "110",  # Champion Attack Rating % Bonus         [Vanilla: 75]
        "11": "135",  # Champion Damage % Bonus                [Vanilla: 100]
        "12": "85",   # Minion Attack Rating % Bonus           [Vanilla: 50]
        "13": "150",  # Unique Attack Rating % Bonus           [Vanilla: 100]
        "14": "100",  # Minion Strong % Bonus                  [Vanilla: 75]
        "15": "185",  # Unique Strong % Bonus                  [Vanilla: 150]
    }
    for row in rows:
        uid = row.get("id", "").strip()
        if uid in progressive_constants:
            row["constants"] = progressive_constants[uid]
    return write_tsv("monumod.txt", headers, rows)


def build_superuniques(cfg: dict) -> str:
    headers, rows = read_tsv("superuniques.txt")
    baal_waves = {
        "Baal Subject 1": ("4", "4", "9",  "8"),   # Colenzo: 4 Warped Shamans, Fire Enchanted + Magic Resistant
        "Baal Subject 2": ("2", "2", "23", "8"),   # Achmel: 2 Greater Mummies, Poison Enchanted + Magic Resistant
        "Baal Subject 3": ("3", "3", "17", "6"),   # Bartuc: 3 Council High Priests, Lightning Enchanted + Extra Fast
        "Baal Subject 4": ("3", "3", "6",  "27"),  # Ventar: 3 Venom Lords, Extra Fast + Spectral Hit
        "Baal Subject 5": ("3", "3", "5",  "27"),  # Lister: 3 Minions of Destruction, Extra Strong + Spectral Hit
    }
    # Give single-mod SuperUniques a thematic second modifier so every SuperUnique
    # has at least 2 baseline elite modifiers (plus Nightmare/Hell random bonuses)
    thematic_second_mod = {
        "Corpsefire":         "5",   # Spectral Hit + Extra Strong
        "Coldcrow":           "26",  # Cold Enchanted + Multiple Shot
        "The Countess":       "6",   # Fire Enchanted + Extra Fast
        "Griswold":           "5",   # Cursed + Extra Strong
        "The Smith":          "6",   # Extra Strong + Extra Fast
        "Radament":           "8",   # Extra Fast + Magic Resistant
        "The Summoner":       "9",   # Extra Strong + Fire Enchanted
        "Taintbreeder":       "6",   # Magic Resistant + Extra Fast
        "Grand Vizier of Chaos": "8",  # Extra Strong + Fire Enchanted + Magic Resistant (via Mod2 if open)
        "Siege Boss":         "28",  # Extra Strong + Stone Skin
        "Ancient Barbarian 1": "5",  # Talic: Extra Fast + Extra Strong
        "Ancient Barbarian 2": "28", # Madawc: Shout + Stone Skin
        "Ancient Barbarian 3": "27", # Korlic: Leap Attack + Spectral Hit
        "Bonesaw Breaker":    "6",   # Extra Strong + Magic Resistant + Extra Fast
        "Dac Farren":         "5",   # Cold Enchanted + Extra Strong
        "Megaflow Rectifier": "27",  # Eldritch: Extra Fast + Spectral Hit
        "Eyeback Unleashed":  "27",  # Extra Strong + Extra Fast + Spectral Hit
        "Threash Socket":     "5",   # Cursed + Extra Strong
        "Pindleskin":         "6",   # Fire Enchanted + Extra Fast
        "Snapchip Shatter":   "5",   # Cursed + Cold Enchanted + Extra Strong
        "Sharp Tooth Sayer":  "5",   # Extra Fast + Extra Strong
        "Frozenstein":        "5",   # Cold Enchanted + Mana Burn + Extra Strong
    }
    for row in rows:
        su = row.get("Superunique", "").strip()
        if su in baal_waves:
            mn, mx, mod1, mod2 = baal_waves[su]
            row["MinGrp"] = mn
            row["MaxGrp"] = mx
            row["Mod1"] = mod1
            row["Mod2"] = mod2
        else:
            # Cap oversized Superunique minion packs (e.g. 8-9 minions -> 3-4) for solo play
            mn = parse_int(row.get("MinGrp", ""))
            mx = parse_int(row.get("MaxGrp", ""))
            if mn > 3:
                row["MinGrp"] = str(max(2, (mn + 1) // 2))
            if mx > 4:
                row["MaxGrp"] = str(max(3, (mx + 1) // 2))

            if su in thematic_second_mod:
                new_mod = thematic_second_mod[su]
                if not row.get("Mod2") or row.get("Mod2") == "0":
                    row["Mod2"] = new_mod
                elif (not row.get("Mod3") or row.get("Mod3") == "0") and row.get("Mod1") != new_mod and row.get("Mod2") != new_mod:
                    row["Mod3"] = new_mod

            # Disambiguate Non-Optional vs Optional Dungeon SuperUnique Classes & TCs:
            if su == "Treehead WoodFist":
                row["Class"] = "brute3"
            elif su == "The Countess":
                row["Class"] = "corruptrogue4"
            elif su in ("Coldcrow", "Bonebreak", "Snapchip Shatter"):
                cur_cls = row.get("Class", "").strip()
                if cur_cls in OPT_FULL_MONSTER_REMAP:
                    row["Class"] = OPT_FULL_MONSTER_REMAP[cur_cls]
                for tc_col in ("TC", "TC Desecrated", "TC(N)", "TC(N) Desecrated", "TC(H)", "TC(H) Desecrated"):
                    tval = row.get(tc_col, "").strip()
                    if tval and not tval.endswith(" Opt"):
                        row[tc_col] = f"{tval} Opt"

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
    elite_dmg_bonus = {"Normal": "100", "Nightmare": "110", "Hell": "120"}
    for row in rows:
        name = row.get("Name", "").strip()
        if name not in static_mins:
            continue
        row["PrimeEvilDamagePercentVSMercenary"] = "125"
        row["PrimeEvilDamagePercentVSPet"] = "175"
        row["MercenaryDamagePercentVSBoss"] = "50"
        row["StaticFieldMin"] = static_mins[name]
        row["UniqueDamageBonus"] = elite_dmg_bonus[name]
        row["ChampionDamageBonus"] = elite_dmg_bonus[name]
        # Ensure Blacksmith's Malus (bml) in the co-opted Gambling UI always spawns as Magic (0% Rare/Set/Unique)
        row["GambleRare"] = "0"
        row["GambleSet"] = "0"
        row["GambleUnique"] = "0"
        row["GambleUber"] = "0"
        row["GambleUltra"] = "0"

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

    # Act 2 9-Aura Matrix mapped by Hireling Id:
    #   Normal (Diff 1):    Id 6 = Thorns,     Id 7 = Defiance,    Id 8 = Blessed Aim
    #   Nightmare (Diff 2): Id 9/30 = Cleansing, Id 10/31 = Holy Freeze, Id 11/32 = Vigor
    #   Hell (Diff 3):      Id 12/33 = Meditation, Id 13/34 = Salvation, Id 14/35 = Sanctuary
    act2_by_id = {
        "6":  ("Thorns",      "skillname103", "Thorns-Normal"),
        "7":  ("Defiance",    "skillname104", "Defiance-Normal"),
        "8":  ("Blessed Aim", "skillname108", "BlessedAim-Normal"),
        "9":  ("Cleansing",   "skillname109", "Cleansing-Nightmare"),
        "30": ("Cleansing",   "skillname109", "Cleansing-Nightmare"),
        "10": ("Holy Freeze", "skillname114", "HolyFreeze-Nightmare"),
        "31": ("Holy Freeze", "skillname114", "HolyFreeze-Nightmare"),
        "11": ("Vigor",       "skillname115", "Vigor-Nightmare"),
        "32": ("Vigor",       "skillname115", "Vigor-Nightmare"),
        "12": ("Meditation",  "skillname120", "Meditation-Hell"),
        "33": ("Meditation",  "skillname120", "Meditation-Hell"),
        "13": ("Salvation",   "skillname125", "Salvation-Hell"),
        "34": ("Salvation",   "skillname125", "Salvation-Hell"),
        "14": ("Sanctuary",   "skillname119", "Sanctuary-Hell"),
        "35": ("Sanctuary",   "skillname119", "Sanctuary-Hell"),
    }

    phys_rogue_templates = []

    for row in rows:
        hid = row.get("Id", "").strip()
        ver = row.get("Version", "").strip()
        act = row.get("Act", "").strip()
        diff = row.get("Difficulty", "").strip()
        sub = row.get("*SubType", "").strip()

        # Global Mercenary Survivability Buff (+25% HP, +25% Def) + Rescaled Resistance Curve (+0.75%/lvl = 3/4% per lvl for 10-slot gear balance)
        row["HP"] = scale_int(row["HP"], 1.25)
        row["HP/Lvl"] = scale_int(row["HP/Lvl"], 1.25)
        row["Defense"] = scale_int(row["Defense"], 1.25)
        row["Def/Lvl"] = scale_int(row["Def/Lvl"], 1.25)
        lvl_base = parse_int(row.get("Level", "1"), 1)
        base_res = str((lvl_base * 3) // 4)
        for res_col in ("ResistFire", "ResistCold", "ResistLightning", "ResistPoison"):
            row[res_col] = base_res
            row[f"{res_col}/Lvl"] = "3"

        # 1. Act 1 Rogue Scouts: Strictly 3 Active Skills (Curse/Debuff + 2 Elemental Arrows, dropping S4 Inner Sight)
        if act == "1":
            orig_s1_lvl = str(max(4, parse_int(row.get("Level1", "4"), 4)))
            orig_s1_lpl = row.get("LvlPerLvl1", "10") or "10"
            if hid in ("0", "2", "4") or "Fire" in sub:
                if ver == "100":
                    phys_rogue_templates.append(dict(row))
                curse = {"1": "Weaken", "2": "Life Tap", "3": "Lower Resist"}.get(diff, "Weaken")
                set_skill(row, 1, curse, "4", "15", "0", orig_s1_lvl, orig_s1_lpl)
            elif hid in ("1", "3", "5") or "Ice" in sub or "Cold" in sub:
                curse = {"1": "Dim Vision", "2": "Slow Missiles", "3": "Decrepify"}.get(diff, "Decrepify")
                set_skill(row, 1, curse, "4", "15", "0", orig_s1_lvl, orig_s1_lpl)
            for s_idx in (2, 3):
                if row.get(f"Skill{s_idx}", "").strip():
                    row[f"Level{s_idx}"] = str(max(4, parse_int(row.get(f"Level{s_idx}", "4"), 4)))
                    row[f"Chance{s_idx}"] = str(max(15, parse_int(row.get(f"Chance{s_idx}", "15"), 15)))
            clear_skill(row, 4)
            clear_skill(row, 5)

        # 2. Act 2 Desert Mercenaries: 9 Distinct Utility/Defensive Auras (3 per Difficulty)
        elif act == "2":
            aura, hdesc, new_sub = act2_by_id.get(hid, ("Prayer", "skillname99", sub))
            if row.get("Skill1", "").strip():
                row["Level1"] = str(max(4, parse_int(row.get("Level1", "4"), 4)))
            orig_lvl2 = str(max(4, parse_int(row.get("Level2", "4"), 4)))
            orig_lpl2 = row.get("LvlPerLvl2", "7") or "7"
            row["*SubType"] = new_sub
            row["HireDesc"] = hdesc
            set_skill(row, 2, aura, "1", "100", "0", orig_lvl2, orig_lpl2)
            clear_skill(row, 3)
            clear_skill(row, 4)
            clear_skill(row, 5)

        # 3. Act 3 Iron Wolves: 3 Active Spells (Skill1..3, Mode=7) + 1 Passive Elemental Mastery (Skill4, Mode=5)
        elif act == "3":
            row["HP"] = scale_int(row["HP"], 1.15)
            row["Defense"] = scale_int(row["Defense"], 1.20)
            for s_idx in (1, 2, 3):
                if row.get(f"Skill{s_idx}", "").strip():
                    row[f"Level{s_idx}"] = str(max(4, parse_int(row.get(f"Level{s_idx}", "4"), 4)))
                    row[f"Chance{s_idx}"] = str(max(15, parse_int(row.get(f"Chance{s_idx}", "15"), 15)))
            s1_lvl = str(max(4, parse_int(row.get("Level1", "4"), 4)))
            if hid in ("15", "18", "21") or "Fire" in sub:
                set_skill(row, 4, "Fire Mastery", "5", "0", "0", s1_lvl, "8")
            elif hid in ("16", "19", "22") or "Cold" in sub:
                set_skill(row, 4, "Cold Mastery", "5", "0", "0", s1_lvl, "8")
            elif hid in ("17", "20", "23") or "Ltng" in sub:
                set_skill(row, 4, "Lightning Mastery", "5", "0", "0", s1_lvl, "8")
            clear_skill(row, 5)

        # 4. Act 5 Barbarian Warriors: 3 Active/Aura Skills in Skill1..3 + Optional Passive in Skill4
        elif act == "5":
            s1_lvl = str(max(5, parse_int(row.get("Level1", "5"), 5)))
            s1_lpl = row.get("LvlPerLvl1", "7") or "7"
            s1_ch = str(max(15, parse_int(row.get("Chance1", "22"), 22)))
            s1_cpl = row.get("ChancePerLvl1", "0") or "0"
            s2_lvl = str(max(5, parse_int(row.get("Level2", "5"), 5)))
            s2_lpl = row.get("LvlPerLvl2", "8") or "8"
            s2_ch = str(max(15, parse_int(row.get("Chance2", "15"), 15)))
            s2_cpl = row.get("ChancePerLvl2", "0") or "0"
            if hid in ("24", "25", "26", "27", "28", "29"):
                # 2H Barbarian: Bash (S1) + Battle Orders (S2) + Might (N) / Concentration (NM/H) (S3)
                aura, hdesc = ("Might", "skillname98") if diff == "1" else ("Concentration", "skillname113")
                row["HireDesc"] = hdesc
                set_skill(row, 1, "Bash", "4", s2_ch, s2_cpl, s2_lvl, s2_lpl)
                set_skill(row, 2, "Battle Orders", "4", "15", "0", s2_lvl, "5")
                set_skill(row, 3, aura, "1", "100", "0", s2_lvl, "6")
                clear_skill(row, 4)
                clear_skill(row, 5)
            elif hid in ("36", "37", "38"):
                # 1H Frenzy Barbarian: Frenzy (S1) + Double Swing (S2) + Might (N) / Fanaticism (NM/H) (S3) + Iron Skin (S4 Passive)
                aura, hdesc = ("Might", "skillname98") if diff == "1" else ("Fanaticism", "skillname122")
                row["HireDesc"] = hdesc
                set_skill(row, 1, "Frenzy", "4", s1_ch, s1_cpl, s1_lvl, s1_lpl)
                set_skill(row, 2, "Double Swing", "4", "35", "0", s1_lvl, "7")
                set_skill(row, 3, aura, "1", "100", "0", s2_lvl, "6")
                set_skill(row, 4, "Iron Skin", "5", "0", "0", s2_lvl, "6")
                clear_skill(row, 5)

    # Append Physical Bowazon Act 1 Rogue Scout rows (Id 39, 40, 41 for N, NM, H across all Version=100 level brackets)
    diff_info = {
        "1": ("39", "Normal", "Inner Sight"),
        "2": ("40", "Nightmare", "Cloak of Shadows"),
        "3": ("41", "Hell", "Amplify Damage"),
    }
    for tmpl in phys_rogue_templates:
        diff = tmpl["Difficulty"].strip()
        new_id, diff_name, support_skill = diff_info.get(diff, ("39", "Normal", "Inner Sight"))
        nr = dict(tmpl)
        nr["Id"] = new_id
        nr["*SubType"] = f"PhysBow - {diff_name}"
        nr["HireDesc"] = "skillname12"
        s1_lvl = str(max(4, parse_int(tmpl.get("Level1", "4"), 4)))
        s1_lpl = tmpl.get("LvlPerLvl1", "10") or "10"
        s2_ch = str(max(15, parse_int(tmpl.get("Chance2", "25"), 25)))
        s2_cpl = tmpl.get("ChancePerLvl2", "5") or "5"
        s2_lvl = str(max(4, parse_int(tmpl.get("Level2", "4"), 4)))
        s2_lpl = tmpl.get("LvlPerLvl2", "10") or "10"
        s3_ch = str(max(15, parse_int(tmpl.get("Chance3", "15"), 15)))
        s3_cpl = tmpl.get("ChancePerLvl3", "4") or "4"
        s3_lvl = str(max(4, parse_int(tmpl.get("Level3", "4"), 4)))
        s3_lpl = tmpl.get("LvlPerLvl3", "5") or "5"
        set_skill(nr, 1, support_skill, "4", "15", "0", s1_lvl, s1_lpl)
        set_skill(nr, 2, "Multiple Shot", "4", s2_ch, s2_cpl, s2_lvl, s2_lpl)
        set_skill(nr, 3, "Strafe", "4", s3_ch, s3_cpl, s3_lvl, s3_lpl)
        set_skill(nr, 4, "Critical Strike", "5", "0", "0", s3_lvl, s3_lpl)
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
    playable = {"Amazon", "Sorceress", "Necromancer", "Paladin", "Barbarian", "Druid", "Assassin", "Warlock"}
    for row in rows:
        cls = row.get("class", "").strip()
        if not cls or cls == "Expansion":
            continue

        # Remove starting Scroll of Town Portal (tsc) from all classes
        for i in range(1, 11):
            if row.get(f"item{i}", "").strip() == "tsc":
                row[f"item{i}"] = "0"
                row[f"item{i}loc"] = ""
                row[f"item{i}count"] = "0"

        if cls not in playable:
            continue

        # 1. 2 Skill Points per Level-Up
        row["SkillsPerLevel"] = "2"

        # 2. Double previous mod LifePerLevel (2 * 1.75x = 3.5x vanilla -> +7.00 HP/lvl for Barb/Pal/Ama/Ass/War,
        #    +5.00 HP/lvl for Nec/Dru, +3.50 HP/lvl for Sorc) & restore vanilla LifePerVitality (1.0x)
        row["LifePerLevel"] = str(int(scale_int(row["LifePerLevel"], 1.75)) * 2)

        # 3. Double previous mod ManaPerLevel (2 * 0.75x = 1.5x vanilla -> +1.50 Mana/lvl for Barb,
        #    +2.00 Mana/lvl for Pal/Ama/Ass/War, +3.00 Mana/lvl for Sorc/Nec/Dru), restore vanilla ManaPerMagic (1.0x),
        #    and keep slower base ManaRegen (160s for full bar)
        row["ManaPerLevel"] = str(int(scale_int(row["ManaPerLevel"], 0.75)) * 2)
        row["ManaRegen"] = "160"

        # 4. Tactical Stamina Curve & +11% Base Run Velocity (9 -> 10 sub-tiles/sec, keeping WalkVelocity at 6)
        row["RunVelocity"] = "10"
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
        build_monumod(cfg),
        build_superuniques(cfg),
        build_monequip(cfg),
        build_difficultylevels(cfg),
        build_hireling(cfg),
        build_experience(cfg),
        build_charstats(cfg),
    ]

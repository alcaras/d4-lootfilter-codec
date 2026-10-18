"""Confirmed SNO IDs for the D4 loot filter.

Source: DiabloTools/d4data json/CoreTOC_flat.json at build 3.2.1.73552
(installed game: 3.2.2.73764). The source was validated by checking that every
ID previously seen in an in-game export maps to the expected internal name.
Affix IDs marked as confirmed below survived an in-game import/export: the
filter keeps one canonical ID per stat and drops other variants on import.
Affix IDs are the current (dwFlags 1027) versions; the pre-Season-4 legacy
copies (dwFlags 1155, e.g. 577051 CritChance) are deliberately left out.
Slot labels come from each affix's arAllowedItemLabels and each ItemType's
arItemLabels (26 Amulet, 19 Ring, 28 Gloves, 29 Boots, 16 Helm, 17 Chest,
30 Pants, 0 weapons).
"""

# --- Affixes (SNO group 104) ---------------------------------------------
CDR = 1829560                 # S04_CooldownReductionCDR           Amulet Helm Gloves Ring (+offhand)
DEXTERITY = 1829562           # S04_CoreStat_Dexterity
MOVE_SPEED = 1829598          # S04_Movement_Speed                 Amulet Boots
ENERGY_REGEN = 1924656        # S04_Resource_Per_Second_Energy     Helm Chest Boots Pants
ALL_SKILLS = 2571274          # X2_SkillRankBonus_AllSkills
# The filter uses ONE canonical ID per stat for every slot. Confirmed by an
# in-game import/export: the game kept these and dropped the slot variants
# 1829584 (S04_CritChanceJewelry), 2602170 (X2_Damage_to_Vulnerable_Greater),
# 2602184 (X2_DamageType_Poison_Greater) and 2605602 (X2_Life_Greater).
CRIT_CHANCE = 1829582         # S04_CritChance
VULN_DMG = 1834112            # S04_Damage_to_Vulnerable
POISON_DMG = 2558715          # X2_DamageType_Poison
MAX_LIFE = 1829592            # S04_Life
DANCE_OF_KNIVES = 1997105     # X1_SkillRankBonus_Rogue_Special_DanceOfKnives  Gloves

# Confirmed canonical by in-game import/export (the game dropped the
# X2_*_Greater / per-weapon / 2H / ArmorPercent alternates).
ALL_DAMAGE = 1829588          # S04_Damage_All
LIFE_ON_HIT = 1924627         # S04_LifePerHit
ARMOR = 1829554               # S04_Armor
SUBTERFUGE = 1928771          # S04_SkillRankBonus_Rogue_Category_Subterfuge
WEAPON_DMG = 2620563          # X2_Fast_Weapon_Damage_1HAxe (used for every weapon type)
DOT_DMG = 1829590             # S04_Damage_DoT (Damage Over Time Multiplier)
ALL_RESIST = 1834296          # S04_Resistance_All
BARRIER_GEN = 2517794         # S11_BarrierGeneration
POISON_RESIST = 1829620       # S04_Resistance_Single_Poison

# --- Item types (SNO group 98) --------------------------------------------
HELM = 446830
CHEST = 446829                # ChestArmor
GLOVES = 446833
PANTS = 446831                # Legs
BOOTS = 446832
AMULET = 446837
RING = 446836
SWORD = 446796
DAGGER = 446809
CROSSBOW = 446825             # Crossbow2H
BOW = 446823
CHARM = 2288901
SEAL = 2326144                # HoradricSeal

# --- Unique items (SNO group 73) ------------------------------------------
DEATHS_PAVANE = 1219220             # Pants_Unique_Rogue_100
ETNAS_LOST_DAGGER = 2580865         # 1HDagger_Unique_Rogue_003_x2
ETNAS_LOST_DAGGER_CHARM = 2589692   # Talisman_Charm_Unique_1HDagger_Unique_Rogue_003_x2
PENITENT_GREAVES = 208264           # Boots_Unique_Generic_001
PENITENT_GREAVES_CHARM = 2583994    # Talisman_Charm_Unique_Boots_Unique_Generic_001
COWL_OF_THE_NAMELESS = 494989       # Helm_Unique_Rogue_001
SHROUDED_GIFT = 2582107             # Pants_Unique_Rogue_001_x2
SEAL_OF_THE_DIAMOND_MIND = 2622269  # Talisman_Seal_MythicUnique_03
LEORICS_CROWN = 2647147             # Helm_Unique_Generic_005
FIST_OF_THE_IRON_ROSE = 2580715     # Gloves_Unique_Rogue_001_x2

# --- Talisman sets (filter condition type 9) -------------------------------
SPELLBOUND_STEEL = 2296522          # Talisman_Rogue_04
SIGHTLESS = 2296524                 # Talisman_Rogue_05
# Every equipment item type, as used in Maxroll's published hide rules
# (testdata/maxroll_*.txt, so accepted by the game).
GEAR_TYPES = [446819, 446827, 446813, 446802, 446826, 446832, 446823, 446799, 446836,
              446805, 1462897, 446778, 446809, 446831, 446837, 446834, 446801, 446804,
              446830, 446788, 446825, 446796, 1495597, 446803, 446833, 446829, 2312856]
GEAR_TYPE_NAMES = {446819: "Wand", 446827: "Totem", 446813: "Polearm", 446802: "Two-Handed Axe",
    446826: "Focus", 446799: "Two-Handed Sword", 446805: "Two-Handed Scythe", 1462897: "Glaive",
    446778: "Mace", 446834: "Shield", 446801: "Axe", 446804: "Scythe", 446788: "Two-Handed Mace",
    1495597: "Quarterstaff", 446803: "Staff", 2312856: "Flail"}
# Not accepted by the filter's item-type condition (dropped on import): Rune 446840,
# ConditionRune 446841, EffectRune 446842. Runes can't be targeted by type.

# Affix IDs the in-game filter is confirmed to accept (survived an in-game
# import/export). maxroll_import.py maps Maxroll's per-slot variants onto these.
CONFIRMED_AFFIXES = [
    CDR, DEXTERITY, MOVE_SPEED, ENERGY_REGEN, ALL_SKILLS, CRIT_CHANCE, VULN_DMG,
    POISON_DMG, MAX_LIFE, DANCE_OF_KNIVES, ALL_DAMAGE, LIFE_ON_HIT, ARMOR,
    SUBTERFUGE, WEAPON_DMG, DOT_DMG, ALL_RESIST, BARRIER_GEN, POISON_RESIST,
]

NAMES = {**GEAR_TYPE_NAMES,
    CDR: "Cooldown Reduction", DEXTERITY: "Dexterity", MOVE_SPEED: "Movement Speed",
    ENERGY_REGEN: "Energy Regeneration", ALL_SKILLS: "+ to All Skills",
    CRIT_CHANCE: "Critical Strike Chance", VULN_DMG: "Vulnerable Damage Multiplier",
    POISON_DMG: "Poison Damage Multiplier", MAX_LIFE: "Maximum Life",
    DANCE_OF_KNIVES: "+ to Dance of Knives",
    ALL_DAMAGE: "All Damage Multiplier", LIFE_ON_HIT: "Life On Hit", ARMOR: "Armor",
    SUBTERFUGE: "+ to Subterfuge Skills", WEAPON_DMG: "Weapon Damage",
    DOT_DMG: "Damage Over Time Multiplier", ALL_RESIST: "All Resistance",
    BARRIER_GEN: "Barrier Generation", POISON_RESIST: "Poison Resistance",
    HELM: "Helm", CHEST: "Chest Armor", GLOVES: "Gloves", PANTS: "Pants", BOOTS: "Boots",
    AMULET: "Amulet", RING: "Ring", SWORD: "Sword", DAGGER: "Dagger", CROSSBOW: "Crossbow",
    BOW: "Bow", CHARM: "Charm", SEAL: "Horadric Seal",
    DEATHS_PAVANE: "Death's Pavane", ETNAS_LOST_DAGGER: "Etna's Lost Dagger",
    ETNAS_LOST_DAGGER_CHARM: "Etna's Lost Dagger (charm)",
    PENITENT_GREAVES: "Penitent Greaves", PENITENT_GREAVES_CHARM: "Penitent Greaves (charm)",
    COWL_OF_THE_NAMELESS: "Cowl of the Nameless", SHROUDED_GIFT: "Shrouded Gift",
    SEAL_OF_THE_DIAMOND_MIND: "Seal of the Diamond Mind",
    LEORICS_CROWN: "Leoric's Crown", FIST_OF_THE_IRON_ROSE: "Fist of the Iron Rose",
    SPELLBOUND_STEEL: "Spellbound Steel (set)", SIGHTLESS: "the Sightless (set)",
    # Death Trap Rogue uniques (appear in testdata/export_original.txt)
    1612292: "DT unique Chest_Unique_Rogue_100", 1704785: "DT unique Boots_Unique_Rogue_100",
    470539: "DT unique Pants_Unique_Rogue_004", 2424373: "DT unique 1HDagger_Unique_Generic_001",
    2589684: "Sea Lord's Fine Gloves (charm)",
}

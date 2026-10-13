# d4-lootfilter-codec

Decode, edit and build **Diablo IV in-game Loot Filter** import strings from Python, using rule and affix names instead of clicking through the UI.

- `d4filter.py`: codec for the share strings. It is a hand-rolled protobuf wire codec, and it round-trips real game exports **byte-for-byte**.
- `ids.py`: affix, item type and unique IDs, **checked against the live game** (see below).
- `maxroll_import.py`: pulls each slot's wanted stats and tempers from a Maxroll build guide into `build.json`, mapped onto filter-accepted IDs.
- `build_dok_tiers.py`: a worked example that builds a Dance of Knives Rogue leveling filter that only highlights upgrades over your equipped gear.

Checked on game build **3.2.2.73764** (Season 15). IDs can change between patches; see [Verifying IDs](#verifying-ids-against-the-game).

## Quick start

```bash
python d4filter.py decode "<import string>"      # -> JSON
python d4filter.py table  "<import string>"      # -> readable rule table
python d4filter.py encode my_filter.json         # -> import string
python d4filter.py test                          # round-trip every export in testdata/ (your own; not in the repo)
python build_dok_tiers.py                        # -> examples/dok_tiers.txt
```

Requires only Python 3.8+ and has no dependencies.

## Format

The share string is `base64(protobuf)`. The schema matches [fnuecke/diablo4-loot-filter-viewer](https://github.com/fnuecke/diablo4-loot-filter-viewer), whose web viewer is handy for checking a string.

```
Filter    1 Rule (repeated)   2 name   3, 4 unknown varints (version-like; take them from a recent export)
Rule      1 name   2 action (0 Show, 1 Hide text label, 2 Recolor, 3 Hide)
          3 color fixed32 0xAARRGGBB   4 Condition (repeated, ALL must match)   5 enabled
Condition 1 type   2 IDs (repeated fixed32)   3 pairs {1, 2}   4 value   5 value2   6 flag
```

| Type | Condition | Fields |
|---|---|---|
| 0 | Item Power range | 4 min, 5 max (max clamped to 900) |
| 1 | Rarity | 4 mask: 1 Common, 2 Magic, 4 Rare, 8 Legendary, 16 Unique, 32 Mythic, 64 Talisman Set |
| 2 | Item properties | 4 mask: 1 None, 4 Ancestral |
| 3 | Codex upgrade | 6 = 1 |
| 4 | Greater Affix check | 4 required count |
| 5 | Item type | 2 item type IDs |
| 6 | Has required affixes | 2 affix IDs, 3 greater-affix pairs, **4 = "Must have at least N of the selected affixes"** |
| 7 | Has optional affixes | same as 6 |
| 8 | Specific unique | 2 item IDs |
| 9 | Talisman set bonus | 2 set IDs, 3 (set, item) pairs |

## Findings from in-game round trips

These came from importing generated strings and re-exporting them from the game. They aren't documented elsewhere as far as I know.

1. **One canonical affix ID per stat.** Game data has several affixes per stat (per-slot or per-weapon variants, `X2_*_Greater` versions, pre-Season-4 legacy copies). The filter accepts exactly one ID per stat for every slot and **silently drops the others on import**. For example, Vulnerable Damage is `1834112` (`S04_Damage_to_Vulnerable`) even on amulets and gloves, and Weapon Damage is `2620563` (`X2_Fast_Weapon_Damage_1HAxe`) for every weapon type.
2. **Rule names longer than 24 characters are dropped.** The rule then shows as "Rule #N".
3. **Zero values are written explicitly** (`action = 0`, `enabled = 0`, `type = 0`). A stock proto3 encoder omits them, so its output won't match the game's bytes. That's why the codec is hand-rolled.
4. Header fields 3 and 4 change between exports (seen: `2/2`, `3/1`, `2/1`, `1/1`). Copying them from a recent export works.
5. **The Item Power range maximum is clamped to 900.** Minimum values are kept as sent.
6. **Tempered lines count toward affix conditions; socketed gems don't.** A duplicate stat (rolled plus tempered) counts twice.
7. **One rule can combine "Has Required Affixes" and "Has Optional Affixes"**, each with its own "at least N". That's how you get "must have X, plus at least one of Y/Z". Affix *values* can't be filtered on: the condition only stores which affixes, how many, and Greater Affix marks.

## Confirmed IDs

Affixes: every ID below survived an in-game import/export.

| Stat | ID | Internal name |
|---|---|---|
| Critical Strike Chance | 1829582 | S04_CritChance |
| Vulnerable Damage Multiplier | 1834112 | S04_Damage_to_Vulnerable |
| Poison Damage Multiplier | 2558715 | X2_DamageType_Poison |
| All Damage Multiplier | 1829588 | S04_Damage_All |
| Weapon Damage (all weapons) | 2620563 | X2_Fast_Weapon_Damage_1HAxe |
| Dexterity | 1829562 | S04_CoreStat_Dexterity |
| Maximum Life | 1829592 | S04_Life |
| Life On Hit | 1924627 | S04_LifePerHit |
| Armor | 1829554 | S04_Armor |
| Movement Speed | 1829598 | S04_Movement_Speed |
| Cooldown Reduction | 1829560 | S04_CooldownReductionCDR |
| Energy Regeneration | 1924656 | S04_Resource_Per_Second_Energy |
| + to All Skills | 2571274 | X2_SkillRankBonus_AllSkills |
| + to Dance of Knives | 1997105 | X1_SkillRankBonus_Rogue_Special_DanceOfKnives |
| + to Subterfuge Skills | 1928771 | S04_SkillRankBonus_Rogue_Category_Subterfuge |
| Damage Over Time Multiplier | 1829590 | S04_Damage_DoT |
| All Resistance | 1834296 | S04_Resistance_All |
| Barrier Generation | 2517794 | S11_BarrierGeneration |

Rejected by the game: 1829584 `S04_CritChanceJewelry`, 2602170 `X2_Damage_to_Vulnerable_Greater`, 2602184 `X2_DamageType_Poison_Greater`, 2605602 `X2_Life_Greater`, 2602166 `X2_Damage_All_Greater`, 1924589 `S04_ArmorPercent`, 2625638 / 2625642 `X2_LifePerHit_*`, and the per-weapon `X2_*_Weapon_Damage_*` variants.

Item types: Helm 446830, Chest 446829, Gloves 446833, Pants 446831, Boots 446832, Amulet 446837, Ring 446836, Sword 446796, Dagger 446809, Crossbow 446825, Bow 446823, Charm 2288901, Horadric Seal 2326144.

Uniques (item IDs; charm versions are separate IDs): Death's Pavane 1219220, Etna's Lost Dagger 2580865 (charm 2589692), Penitent Greaves 208264 (charm 2583994).

## Verifying IDs against the game

IDs are SNO IDs. Candidate names come from [DiabloTools/d4data](https://github.com/DiabloTools/d4data) (`json/CoreTOC_flat.json`: group 104 is Affix, 98 ItemType, 73 Item). To confirm one:

1. Add the candidate IDs to a rule. Including every plausible variant is fine.
2. Import the string in-game, export it again, and decode the export.
3. The IDs still present are the ones the game accepts. Record them in `ids.py`.

## Importing stat priorities from Maxroll

```bash
python maxroll_import.py "https://maxroll.gg/d4/build-guides/dance-of-knives-rogue-leveling-guide"
```

This fetches the planner behind a Maxroll build guide (or a planner link) and writes `build.json`: per slot, the wanted stats and the tempers, from the first profile whose name contains "Leveling" (or `--profile NAME`). Maxroll lists per-slot affix variants (e.g. `X2_Damage_to_Vulnerable_Greater` on gloves), which the in-game filter drops on import. Variants with the same underlying game attributes are the same stat, so each is mapped onto the ID confirmed in-game. Stats without a confirmed ID get a best guess and are flagged for one in-game import/export check. For the DoK leveling guide every stat maps to a confirmed ID, and the generated filter is byte-identical to the hand-built one.

It uses the same public endpoints as [d4lf](https://github.com/d4lfteam/d4lf)'s importer (`planners.maxroll.gg` and Maxroll's game data). Both are undocumented and may change. Downloads are cached in `.cache/` for a day.

Maxroll planners also include ready-made in-game filters ("Maxroll Light / Medium / Strict", generic endgame filters); the codec round-trips them byte-for-byte.

## Example: Dance of Knives leveling upgrade filter

The script writes your filter to `examples/dok_tiers.txt`. It reads your gear from `equipped.json` (Item Power and stat names as shown on the tooltip), for example:

```json
{"helm": {"item": "Some Helm", "ip": 412, "rarity": "Legendary", "tempers_left": 1,
          "stats": ["Dexterity", "Maximum Life"], "tempers": ["Maximum Life"]}}
```

Slots: `helm, chest, gloves, pants, boots, amulet, ring1, ring2, ranged, mainhand, offhand`. `equipped.json`, `build.json`, `examples/` and `testdata/` are personal and git-ignored. Wanted stats per slot are lines 1–4 of [Maxroll's Season 15 DoK leveling guide](https://maxroll.gg/d4/build-guides/dance-of-knives-rogue-leveling-guide) stat priority; the hammer line is the temper, which you add yourself, so it isn't counted. For each slot the script counts the wanted stats on your equipped piece (N) and only lights up items with at least its Item Power:

| Color | Meaning |
|---|---|
| Magenta `#FF00FF` | N+1 or more wanted stats: a real upgrade. Also target uniques and endgame jackpots (ancestral Greater CDR, Greater + to All Skills) |
| Cyan `#00FFFF` | N wanted stats: same as your equipped piece, which shows cyan itself |
| Dim teal `#4A9AA5` | Melee weapon with at least equipped Item Power, any stats (Dance of Knives uses the melee weapons) |
| Red `#FF3030` | Codex upgrade (nothing else is red) |
| Pale pink `#FFA0D0` | Legendary-or-better Horadric Seal to sell |
| No color | Salvage |

Boots and amulets must also have Movement Speed. Rings and melee weapons compare against the weaker of the pair.

The colors avoid Diablo IV's own rarity colors (white, blue, yellow, orange, tan, purple, green), so a recolor can't be mistaken for an item's rarity. While leveling, update a slot and rebuild:

```bash
python build_dok_tiers.py helm=270 boots=310
```

The filter name carries a version number (`DoK Upgrades vN`) so you can tell in-game which one is loaded. The full rule table is written to `examples/dok_tiers.md`.

### Changelog

- **v17**: the melee Item-Power-only tier (dim teal) is any rarity again, so Magic weapons that might be a DPS upgrade still show; the stat tiers stay Rare or better.
- **v16**: weapon rules require Rare or better (Magic and Normal items can't be tempered).
- **v15**: the build prints temper reminders for untempered Rare-or-better equipped pieces (existing tempers are never replaced while leveling) (`equipped.json` records rarity and temper attempts left).
- **v12**: `equipped.json` separates dropped stats from tempers (only dropped stats set the bar; the filter counts tempered lines but not gems); wanted stats now come from `build.json`, generated by `maxroll_import.py` from the guide's planner; the output is byte-identical to the hand-built v12.
- **v11**: the Item-Power-only weapon tier covers melee weapons only, since Dance of Knives doesn't use the ranged weapon's damage. 24/25 rules.
- **v10**: colors are relative to your equipped piece (cyan = same number of wanted stats, magenta = more); `equipped.json` holds your gear's stats by name; wanted lists are exactly Maxroll's lines 1–4 (temper stats like Poison Damage, and + to Dance of Knives, removed); ranged and melee weapons split. 25/25 rules.
- **v9**: Item Power floors are now "at least equipped" instead of "higher than equipped", so your equipped piece shows its own color for comparison.
- **v8**: boots and amulet (the only slots that roll Movement Speed) only light up when the item has Movement Speed: cyan with Movement Speed alone, magenta with Movement Speed plus another wanted stat.
- **v7**: one meaning per color. Seal (Sell) moves to pale pink, and GA CDR and All Skills move to magenta, so red means only Codex upgrade.
- **v6**: Item Power maximum set to 900 (the game clamps it); dropped the three disabled endgame Hide rules; GA CDR fixed from "at least 2" to "at least 1" of its single affix. 22/25 rules.
- **v5**: per-slot Item Power floors from equipped gear, so only upgrades light up; 2 tiers per slot plus a weapon Item-Power-only tier.
- **v4**: colors moved off Diablo IV's native rarity hues.
- **v3**: 3 tiers per slot group using "Must have at least N"; WoW-style colors.
- **v1 and v2**: first leveling filter; v2 fixed a dropped rule name (over 24 characters) and non-canonical affix IDs.

## Credits

- [DiabloTools/d4data](https://github.com/DiabloTools/d4data): game data extracts and SNO names
- [d4lfteam/d4lf](https://github.com/d4lfteam/d4lf): showed the Maxroll planner and game-data endpoints
- [fnuecke/diablo4-loot-filter-viewer](https://github.com/fnuecke/diablo4-loot-filter-viewer) and [bmbernie/Diablo-4-Loot-Filter-Reverse-Engineered](https://github.com/bmbernie/Diablo-4-Loot-Filter-Reverse-Engineered): earlier format work
- Stat priorities in the example: Maxroll's DoK leveling guide by Avarilyn

Not affiliated with Blizzard Entertainment. Diablo is a trademark of Blizzard Entertainment, Inc. This tool only reads and writes the share strings the game itself imports and exports; it does not touch game files or the running game.

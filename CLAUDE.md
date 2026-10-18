# Diablo IV loot filter: working notes

This repo builds import strings for Diablo IV's in-game Loot Filter. The main use is a leveling filter that highlights upgrades over the gear a character is wearing. Format details and confirmed IDs are in README.md; this file covers how to work on it.

## Characters
Each character has its own folder `chars/<key>/` (git-ignored, personal):
- `settings.json`: name, class, build, filter name prefix, Maxroll guide and profile, target uniques, preferences
- `build.json`: wanted stats and tempers per slot, from the guide
- `equipped.json`: the gear the character wears
- `filter_version.txt` and `filter.{txt,json,md}`: the generated filter

| Key | Character | Class / build | Filter name |
|---|---|---|---|
| `alcara` | Alcara | Rogue, Dance of Knives (poison), Maxroll endgame guide, Midgame profile (from level 70) | DoK Upgrades vN |

All characters' screenshots land in the same folder. The character name is shown in the character panel ("ALCARA"), so use it to tell which character a screenshot belongs to. If it's unclear, ask.

## Hard rules
- **The Diablo IV install is read-only.** Never write to game files, inject into the game, or touch the running game. Read the screenshots folder only.
- **Don't trust an affix ID until the game has accepted it.** The filter keeps one ID per stat and silently drops others on import. A new ID is confirmed only after an in-game import, export, and decode shows it survived. Record confirmed IDs in `ids.py` (`CONFIRMED_AFFIXES`).
- **Give import strings via the clipboard, never retyped.** After a build, copy `chars/<key>/filter.txt` with `python -c "import sys;sys.stdout.write(open('chars/<key>/filter.txt').read().strip())" | clip.exe` (or PowerShell `Set-Clipboard`) and check the length. A retyped 2,000-character string once got garbled and was rejected.
- **Game limits:** at most 25 rules, rule names up to 24 characters (longer names are dropped), and the Item Power maximum is clamped to 900.
- **Colors:** one meaning per color, never a Diablo rarity color (white, blue, yellow, orange, tan, purple, green). Magenta = likely upgrade: more wanted stats than equipped (or all of them once the equipped piece has all; also target uniques and jackpots). Cyan = sidegrade, shown only for slots whose equipped piece has 3+ wanted stats (`sidegrade_from`); otherwise sidegrades are hidden (the player wants minimal time in town). Dim teal = weapon at or above equipped Item Power (`ip_only_group`, optional; also needs the group's `must` stat if it has one; drop it once Torment drops are all at the cap). Red = Codex upgrade only (it can't see stat value, only that the power is new or better). Pale pink = legendary seal to sell, unless `keep_legendary_seals` makes them magenta. The build script asserts this.

## Gear update (the usual loop)
1. The player hovers each changed **equipped** item and presses the in-game screenshot key. Files land in `Documents\Diablo IV\Screenshots`.
2. Work out which character the screenshots are for. Read the files newer than that character's `_screenshots_processed_through` in `equipped.json`, and skip anything that isn't an EQUIPPED tooltip. Another character's screenshots may be interleaved; skip those too.
3. Update `chars/<key>/equipped.json` per slot:
   - `ip`: the item's Item Power
   - `stats`: the stats it dropped with, as tooltip names
   - `tempers`: tempered lines, shown with a distinct icon; recorded but not counted
   - `rarity`
   - `tempers_left`: the first number of "Tempers: X/Y" (rerolls remaining)
   - Ignore socketed gems and runes.
   - Rings and paired weapons compare against the weaker of the pair.
4. Bump `chars/<key>/filter_version.txt` and run `python build_filter.py <key>`. Skip the bump if the filter string didn't change, for example when only tempers changed.
5. Copy the string to the clipboard and report the changes and any `TEMPER` reminders.

The player's gear and filters are private: `chars/` and `testdata/` are git-ignored and stay local, and gear updates are never committed. Only commit and push changes to code or docs (the public repo is github.com/alcaras/d4-lootfilter-codec), staging files by name. The synergy explorer files (`synergy.py`, `skills.py`, `dpscalc.py`, `reports/`) belong to a separate project and are git-ignored here.

The player's preferences (carry over to new characters unless told otherwise): while leveling, boots and amulet must have Movement Speed (drop the amulet one at endgame if the guide's amulet doesn't use it); weapon stat tiers must be Rare or better; below `rare_plus_from_ip` (600 for Alcara) the dim-teal Item Power tier and 2-affix rules are any rarity, and from it up Magic and Common items are never marked; existing tempers are never replaced while leveling (temper better drops instead); weapons are swapped as soon as a better one drops and are not tempered while leveling, so they get no temper reminders; only clearly better swaps (about 5%+) are worth the materials.

## New character
1. Create `chars/<key>/settings.json` (copy `chars/alcara/settings.json` and edit): name, class, build, `filter_prefix` (keep rule names within 24 characters), guide URL and profile, `uniques` (unique item IDs to always highlight; IDs not yet in `ids.py` need a name in `unique_names`), `must`, `rare_plus_only`, `ip_only_group`, `no_temper_reminder`, `sidegrade_from`, `rare_plus_from_ip`, `skip_slots` (slots settled by a unique: no stat tiers), `no_sidegrade` (slots with no cyan tier), `ancestral_only` (slots whose tiers require Ancestral), `keep_legendary_seals` (Legendary seals magenta instead of pale-pink sell), `extra_rules` (build-specific magenta rules such as talisman sets or runes: `[{"name", "conditions"}]`), `min_wanted` (per-slot floor on wanted stats for the upgrade tier, counting the `must` stat, e.g. `{"Ring": 3}`).
2. `python maxroll_import.py <guide URL> --char <key> [--profile NAME]` writes its `build.json`. Any IDs it flags as unconfirmed need one in-game import/export check. It skips a unique's fixed lines and runeword effects and prints the unique's item ID, to add to `uniques`.
3. If the class is new, add its weapon slot groups to `CLASS_GROUPS` in `build_filter.py` (e.g. two-handers, shields, off-hand focus or totem). Their item type IDs need confirming in-game like affix IDs. Main stats differ too (Paladin: Strength; Warlock: Willpower; see DAMAGE.md for the per-class damage values).
4. Start `equipped.json` from a full set of gear screenshots, then build. Add the character to the table above.

## New season or patch
1. Re-run `maxroll_import.py` for each character.
2. Run `python d4filter.py test`: every export in `testdata/` must round-trip byte-for-byte.
3. Patches can change IDs or format. Ask the player for a fresh in-game export, add it to `testdata/`, and confirm it still decodes. Header fields 3 and 4 are taken from the newest export.

## Endgame filter (after the guide's Midgame profile is imported)
The leveling filter gets noisy at Torment, where most drops share the Item Power cap. Tighten it slot by slot as gear settles:
- A slot filled by a unique or strong legendary power: `skip_slots` plus an `extra_rules` entry for an Ancestral copy (`unique` + `properties` mask 4), or `min_wanted` high enough that only near-perfect rares show.
- Weapons: `ancestral_only`, and a `must` stat (e.g. Damage Over Time) so off-build weapons stay dark.
- Talisman sets and target seals: `extra_rules` with `talisman_set`; runes can't be targeted (all rune item types are dropped on import).
- After adding a new ID or condition type, ask for an in-game export and confirm it survived (add it to `testdata/`).

## Upgrade questions
For "is this item better?" (the play-companion conventions are in ../CLAUDE.md) use the bucket model in DAMAGE.md: get the comparison tooltip plus the character sheet's offensive stats, compute the ratio per bucket, and say plainly when a result is within about 5% or depends on unmodelled effects.

## Files
- `DAMAGE.md`: the damage model (buckets, formula, confidence, poison-build notes).
- `d4filter.py`: the codec (`decode`, `encode`, `table`, `test`).
- `ids.py`: confirmed SNO IDs.
- `maxroll_import.py`: Maxroll planner → `chars/<key>/build.json`. Its downloads are cached in `.cache/`.
- `build_filter.py`: builds a character's filter from its folder.
- `testdata/` (local only): the player's real game exports and Maxroll's published filters, used as round-trip tests.

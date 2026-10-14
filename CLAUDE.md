# Diablo IV loot filter: working notes

This repo builds import strings for Diablo IV's in-game Loot Filter. The main use is a leveling filter that highlights upgrades over the gear you're wearing. Format details and confirmed IDs are in README.md; this file covers how to work on it.

## Hard rules
- **The Diablo IV install is read-only.** Never write to game files, inject into the game, or touch the running game. Read the screenshots folder only.
- **Don't trust an affix ID until the game has accepted it.** The filter keeps one ID per stat and silently drops others on import. A new ID is confirmed only after an in-game import, export, and decode shows it survived. Record confirmed IDs in `ids.py` (`CONFIRMED_AFFIXES`).
- **Give import strings via the clipboard, never retyped.** After a build, run `Get-Content -Raw examples/dok_tiers.txt | % { $_.Trim() } | Set-Clipboard` and check the length. A retyped 2,000-character string once got garbled and was rejected.
- **Game limits:** at most 25 rules, rule names up to 24 characters (longer names are dropped), and the Item Power maximum is clamped to 900.
- **Colors:** one meaning per color, never a Diablo rarity color (white, blue, yellow, orange, tan, purple, green). Magenta = likely upgrade: more wanted stats than equipped (or all of them once the equipped piece has all; also target uniques and jackpots). Cyan = sidegrade, shown only for slots whose equipped piece has 3+ wanted stats (SIDEGRADE_FROM); otherwise sidegrades are hidden (the player wants minimal time in town). Dim teal = melee weapon at or above equipped Item Power. Red = Codex upgrade only. Pale pink = legendary seal to sell. The build script asserts this.

## Gear update (the usual loop)
1. The player hovers each changed **equipped** item and presses the in-game screenshot key. Files land in `Documents\Diablo IV\Screenshots`.
2. Read the files newer than `_screenshots_processed_through` in `equipped.json` and skip anything that isn't an EQUIPPED tooltip.
3. Update `equipped.json` per slot:
   - `ip`: the item's Item Power
   - `stats`: the stats it dropped with, as tooltip names
   - `tempers`: tempered lines, shown with a distinct icon; recorded but not counted
   - `rarity`
   - `tempers_left`: the first number of "Tempers: X/Y"
   - Ignore socketed gems and runes.
   - Rings and melee weapons compare against the weaker of the pair.
4. Bump the number in `filter_version.txt` (local), and run `python build_dok_tiers.py`. Feature changes also get a README changelog line. Skip the bump if the filter string didn't change, for example when only tempers changed.
5. Copy the string to the clipboard and report the changes and any `TEMPER` reminders.

The player's gear and filter are private: `equipped.json`, `build.json`, `filter_version.txt`, `examples/` and `testdata/` are git-ignored and stay local. Gear updates are never committed. Only commit and push changes to code or docs (the public repo is github.com/alcaras/d4-lootfilter-codec).

The player's preferences: boots and amulet must have Movement Speed; weapon stat tiers (magenta) must be Rare or better, but the dim-teal melee Item Power tier is any rarity (Magic weapons can still be a DPS upgrade); existing tempers are never replaced while leveling (temper better drops instead). Weapons are swapped as soon as a better one drops and are not tempered while leveling, so they get no temper reminders.

## New season, patch, or build
1. `python maxroll_import.py <maxroll guide URL>` regenerates `build.json` (wanted stats and tempers per slot). Any IDs it flags as unconfirmed need one in-game import/export check.
2. Run `python d4filter.py test`: every export in `testdata/` must round-trip byte-for-byte.
3. Patches can change IDs or format. Ask the player for a fresh in-game export, add it to `testdata/`, and confirm it still decodes. Header fields 3 and 4 are taken from the newest export.
4. For a different build, edit the build-specific parts of `build_dok_tiers.py`: the target uniques, `MUST`, `RARE_PLUS_ONLY`, and the filter name.
5. Start `equipped.json` fresh from screenshots of the new character.

## Upgrade questions
For "is this item better?" use the bucket model in DAMAGE.md: get the comparison tooltip plus the character sheet's offensive stats, compute the ratio per bucket, and say plainly when a result is within about 5% or depends on unmodelled effects.

## Files
- `DAMAGE.md`: the damage model (buckets, formula, confidence, poison-build notes).
- `d4filter.py`: the codec (`decode`, `encode`, `table`, `test`).
- `ids.py`: confirmed SNO IDs.
- `maxroll_import.py`: Maxroll planner → `build.json`. Its downloads are cached in `.cache/`.
- `build_dok_tiers.py`: builds the filter from `build.json` and `equipped.json`, then writes `examples/dok_tiers.{txt,json,md}`.
- `testdata/` (local only): the player's real game exports and Maxroll's published filters, used as round-trip tests.

# Diablo IV damage model (Season 15, patch 3.2.x)

A working model for comparing gear. It's good for ratios ("is item B better than A?"), not for exact DPS. Within about 5% it's too close to call.

## Formula
```
Damage = Weapon Damage × Skill %
       × Core stat factor            1 + stat × per-point value (Rogue: 1.25% per 10 Dex)
       × (1 + Σ [+] bonuses)         one additive bucket
       × (1 + Σ damage-bucket [x])   All Damage + matching damage-type multiplier + weapon gem
       × Π separate [x] sources      aspects, unique powers, legendary Paragon nodes, glyph [x], skills
       × crit factor                 direct hits only
       × Vulnerable factor           vs. Vulnerable enemies only
       × DoT factor                  damage over time only
```

Same bucket: values add. Different buckets: values multiply. A bonus is worth the most in the bucket that is smallest for you.

## Buckets
| Bucket | What goes in | Factor |
|---|---|---|
| Additive `[+]` | Every `[+]`: "damage to …", elemental/Poison damage `[+]`, Vulnerable damage `[+]`, Critical Strike Damage `[+]` (on crits), tempers, Paragon, glyphs | `1 + sum`; dilutes as it grows |
| Damage `[x]` | All Damage Multiplier, damage-type multiplier (e.g. Poison), gem in weapon (Emerald = Poison, Diamond = All) | `1 + sum` |
| Separate `[x]` | Each aspect, unique power, legendary node, `[x]` glyph bonus, skill upgrade | each its own factor |
| Crit | Base ×1.5, Crit Damage Multiplier `[x]`, Crit Damage `[+]` | `(A + CD+) / A × 1.5 × (1 + CDM)`, averaged: `1 + CC × (factor − 1)`, where A = 1 + additive bucket |
| Vulnerable | Base ×1.2, Vulnerable Damage Multiplier `[x]` | `1.2 × (1 + VDM)` |
| Damage over Time | DoT Multiplier `[x]` | `1 + DoTM` |

Overpower (since Lord of Hatred): each stack adds 15% `[+]` to the additive bucket. Effects that consume stacks are usually separate `[x]`.

## Evidence and confidence
- **The game data confirms the bucket names.** Maxroll's 3.2.1 game data defines `Bucketed_Multiplicative_Damage`, `…_Damage_Type`, `…_Damage_Type_FireHoly`, `…_Crit_Damage`, `…_Vulnerable_Health_Damage` and `…_DoT_Damage`. d4data's 3.1.0 `attributes.json` tags each damage attribute as summed (operator 0) or multiplied (operator 7, the `Multiplicative_*` attributes).
- **Not in the data:** the code that combines buckets. Blizzard has only confirmed that same-type gear multipliers add together. That All Damage and damage-type multipliers share one bucket is the community calculators' assumption; the data names them as separate attributes.
- **Core stat value:** Rogue 1.25% per 10 Dexterity, from the 3.2.1 patch notes via d4guides. Maxroll's archived beginner article (1% per 9) is outdated.
- Sources: [d4guides damage calculation (Oct 2026, 3.2.2)](https://d4guides.gg/en/guides/mechanics/damage-calculation-in-diablo-4-how-your-damage-works), [Maxroll Damage for Beginners (archived)](https://maxroll.gg/d4/getting-started/damage-for-beginners), Maxroll `data.min.json`, [DiabloTools/d4data](https://github.com/DiabloTools/d4data).

## Poison Dance of Knives specifics
- **Poison is damage over time, so it can't crit.** Crit Chance and Crit Damage only boost the direct hits of Dance of Knives. Weigh crit stats by the build's direct-hit share, which is unknown; ask, or treat crit as worth about half.
- **DoT Multiplier is its own bucket** and applies to all poison. It's underrated relative to Maxroll's leveling stat list.
- **Vulnerable Multiplier is its own bucket.** It's strong if Vulnerable uptime is high (Accursed Touch via Vampiric Curse, Biting Cold on cold hits).
- **Poison Damage Multiplier and All Damage share the damage bucket**, so they're worth less stacked together.
- **Poison tempers `[+]` sit in the diluted additive bucket**, so they're the weakest damage stat late game.

## Comparing two items
1. Need: the comparison tooltip (candidate next to equipped) and the character sheet's offensive stats (Dexterity, crit chance and damage, additive damage %, Vulnerable damage).
2. List what changes per bucket when swapping. Compute each bucket's factor before and after, and multiply the ratios.
3. Weapons: the weapon-damage ratio counts almost one-for-one (DPS on the tooltip).
4. Report the estimated % change, which buckets drove it, and anything unmodelled (aspect conditions, uptime, defense via the tooltip's Toughness).

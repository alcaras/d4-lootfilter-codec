"""Dance of Knives leveling filter that highlights upgrades over your gear.

Wanted stats per slot come from build.json, which maxroll_import.py pulls from
the Maxroll guide's planner (the guide's stat priority lines 1-4; tempers are
listed separately and not counted). equipped.json records what you wear: Item Power, the stats it
dropped with ("stats") and your tempers ("tempers", recorded but not counted:
drops never have tempers, and you'd temper the new piece the same way).
Socketed gems are ignored, as the game's filter ignores them too. For each slot
the script counts how many wanted stats your equipped piece dropped with (N)
and only lights up items with at least its Item Power:
  Magenta   = likely upgrade: N+1 or more wanted stats (or, once the
              equipped piece has every wanted stat, any piece with all of
              them); also target uniques and endgame jackpots (GA CDR,
              All Skills). Sidegrades (same count) are deliberately not
              shown, to keep time in town short.
  Dim teal  = melee weapon with at least equipped Item Power, any stats
              (Dance of Knives uses the melee weapons; the bow is only
              there for its aspect)
  Red       = Codex upgrade (new/better aspect) -- red means only this
  Pale pink = Legendary-or-better Horadric Seal to sell
  No color  = salvage
Boots and amulet must have Movement Speed (the only slots that roll it): it
goes into "Has Required Affixes" and the other wanted stats into "Has Optional
Affixes", with the counts adjusted accordingly.
Colors avoid D4's native rarity hues (white, blue, yellow, orange, tan,
purple, green) so a recolor can't be mistaken for an item's rarity.
The version number goes into the filter name so you can tell in-game which
one is loaded; bump VERSION and add a CHANGELOG line for every change.

Update equipped.json (Item Power and stat names as shown on the tooltip) when
you swap gear, or just the Item Power from the command line, then rebuild:
  python build_dok_tiers.py
  python build_dok_tiers.py helm=270 boots=310
Rings and melee weapons use the weaker of the pair (lower Item Power, fewer
wanted stats).

Writes examples/dok_tiers.{json,txt,md}.
"""
import json
import os
import sys

import d4filter
from ids import *

HERE = os.path.dirname(os.path.abspath(__file__))
# Filter version: kept in a local, git-ignored file. Bump it for every new filter.
VERSION_FILE = os.path.join(HERE, "filter_version.txt")
VERSION = int(open(VERSION_FILE).read()) if os.path.exists(VERSION_FILE) else 1
old = d4filter.decode(open(os.path.join(HERE, "testdata", "export_original.txt")).read())
latest = d4filter.decode(open(os.path.join(HERE, "testdata", "export_v8_after_import.txt")).read())
keep = {r["name"].strip(): r for r in old["rules"]}

UP, IP_ONLY, CODEX, SELL = "#FF00FF", "#4A9AA5", "#FF3030", "#FFA0D0"
IP_MAX = 900    # the game clamps the Item Power range maximum to 900

# Wanted stats come from build.json (python maxroll_import.py <guide URL>).
# Your own preferences on top of the guide:
MUST = {"boots": MOVE_SPEED, "amulet": MOVE_SPEED}   # slot must have this stat
NO_TEMPER_REMINDER = {"mainhand", "offhand", "ranged"}   # weapons get replaced too fast
RARE_PLUS_ONLY = {"Ranged", "Melee"}   # stat tiers: Magic/Normal can't be tempered
# (the melee Item-Power-only tier stays any rarity: a Magic weapon can still
# be a DPS upgrade, and the tooltip's DPS comparison decides)
RARE_PLUS = {"type": "rarity", "mask": 4 | 8 | 16 | 32 | 64}   # Rare and up
MELEE = [SWORD, DAGGER]
RANGED = [CROSSBOW, BOW]
# (label, build/equipped slot keys, item types)
GROUPS = [
    ("Helm", ["helm"], [HELM]), ("Chest", ["chest"], [CHEST]),
    ("Gloves", ["gloves"], [GLOVES]), ("Pants", ["pants"], [PANTS]),
    ("Boots", ["boots"], [BOOTS]), ("Amulet", ["amulet"], [AMULET]),
    ("Ring", ["ring1", "ring2"], [RING]), ("Ranged", ["ranged"], RANGED),
    ("Melee", ["mainhand", "offhand"], MELEE),
]
build = json.load(open(os.path.join(HERE, "build.json"), encoding="utf-8"))
SLOTS = []
for label, keys, types in GROUPS:
    wanted = []
    for k in keys:
        for w in build["slots"][k]["wanted"]:
            NAMES.setdefault(w["id"], w["name"])   # unconfirmed IDs keep Maxroll's name
            if w["id"] not in wanted:
                wanted.append(w["id"])
    must = MUST.get(keys[0])
    SLOTS.append((label, keys, types, [i for i in wanted if i != must], must))
unconfirmed = sorted({(w["id"], w["name"]) for s in build["slots"].values()
                      for w in s["wanted"] if not w["confirmed"]})

eq_path = os.path.join(HERE, "equipped.json")
equipped = json.load(open(eq_path))
# "_screenshots_processed_through" records the newest Documents\Diablo IV\Screenshots
# file already read into equipped.json, so a gear update only needs newer ones.
for arg in sys.argv[1:]:
    key, ip = arg.split("=")
    if key not in equipped:
        sys.exit(f"unknown slot {key!r}; use one of {', '.join(equipped)}")
    equipped[key]["ip"] = int(ip)
if sys.argv[1:]:
    json.dump(equipped, open(eq_path, "w"), indent=2)


def count(key, wanted):
    """Wanted stats (by tooltip name) on an equipped piece."""
    return sum(NAMES[i] in equipped[key]["stats"] for i in wanted)


def rule(name, color, *conds, action="recolor"):
    return {"name": name, "action": action, "color": color, "enabled": True,
            "conditions": list(conds)}


def slot_rules(label, keys, types, wanted, must):
    floor = min(equipped[k]["ip"] for k in keys)
    if must is None:
        have = min(count(k, wanted) for k in keys)
    else:   # count the other wanted stats; pieces without the must stat count as 0
        have = min(count(k, wanted) if NAMES[must] in equipped[k]["stats"] else 0
                   for k in keys)
    base = [{"type": "item_type", "ids": types},
            {"type": "item_power", "min": floor, "max": IP_MAX}]
    if label in RARE_PLUS_ONLY:
        base.append(RARE_PLUS)

    def affixes(n):
        if must is None:
            return [{"type": "affixes", "ids": wanted, "mode": n}] if n else []
        conds = [{"type": "affixes", "ids": [must], "mode": 1}]
        if n:
            conds.append({"type": "optional_affixes", "ids": wanted, "mode": n})
        return conds

    # Only likely upgrades: more wanted stats than equipped. Once the equipped
    # piece has every wanted stat, a piece with all of them at higher Item
    # Power is the upgrade instead.
    n = min(have + 1, len(wanted))
    out = [rule(f"{label} up", UP, *base, *affixes(n))]
    summary.append((label, floor, have + (must is not None), len(wanted) + (must is not None)))
    return out


summary = []
rules = [rule("DoK Uniques", UP, {"type": "unique", "ids": [
    DEATHS_PAVANE, ETNAS_LOST_DAGGER, ETNAS_LOST_DAGGER_CHARM,
    PENITENT_GREAVES, PENITENT_GREAVES_CHARM]})]
tiers = [slot_rules(*s) for s in SLOTS]
rules += [r for t in tiers for r in t]
rules.append(rule("Melee IP only", IP_ONLY, {"type": "item_type", "ids": MELEE},
                  {"type": "item_power",
                   "min": min(equipped[k]["ip"] for k in ("mainhand", "offhand")),
                   "max": IP_MAX}))
rules.append(rule("Codex Upgrade", CODEX, {"type": "codex", "flag": 1}))
# GA CDR as originally exported asked for "at least 2" of a single affix,
# which can never match; it needs "at least 1".
ga_cdr = json.loads(json.dumps(keep["GA CDR"]))
for c in ga_cdr["conditions"]:
    if c["type"] == "affixes":
        c["mode"] = 1
rules += [dict(keep["Legendary Seal (Sell)"], color=SELL),
          dict(ga_cdr, color=UP), dict(keep["All Skills"], color=UP)]
assert {r["color"] for r in rules} <= {UP, IP_ONLY, CODEX, SELL}, "one meaning per color"

flt = {"name": f"DoK Upgrades v{VERSION}", "rules": rules,
       "f3": latest["f3"], "f4": latest["f4"]}
assert len(rules) <= 25, len(rules)
assert all(len(r["name"]) <= 24 for r in rules), "names over 24 chars are dropped"
assert not any(r["action"] == "hide" and r["enabled"] for r in rules)
for r in rules:
    for c in r["conditions"]:
        for i in c.get("ids", []):
            assert i in NAMES, (r["name"], i)

s = d4filter.encode(flt)
assert d4filter.encode(d4filter.decode(s)) == s
json.dump(flt, open(os.path.join(HERE, "examples", "dok_tiers.json"), "w"), indent=2)
open(os.path.join(HERE, "examples", "dok_tiers.txt"), "w").write(s + "\n")
open(os.path.join(HERE, "examples", "dok_tiers.md"), "w", encoding="utf-8").write(
    d4filter.table(d4filter.decode(s)) + "\n")
print(f"v{VERSION}, {len(rules)}/25 rules, from {build['profile']!r} of planner {build['planner']}")
# Temper reminders: untempered Rare-or-better equipped pieces. While leveling,
# existing tempers are never replaced; new drops get tempered instead.
for key, slot in build["slots"].items():
    piece = equipped.get(key)
    if not piece or piece.get("rarity", "Magic") in ("Common", "Magic"):
        continue
    if key in NO_TEMPER_REMINDER:
        continue
    missing = [t for t in slot["tempers"] if t not in piece.get("tempers", [])]
    left = piece.get("tempers_left")
    if missing and not piece.get("tempers") and left != 0:
        attempts = "attempts left unknown" if left is None else f"{left} attempt(s) left"
        print(f"TEMPER {key}: {', '.join(missing)} ({piece['item']}, {attempts})")
if unconfirmed:
    print("NOT YET CONFIRMED in-game (import, export, and check they survive):",
          ", ".join(f"{i} {n}" for i, n in unconfirmed))
for label, floor, have, total in summary:
    print(f"  {label:7} IP >= {floor:3}  equipped has {have}/{total} wanted")
print(s)

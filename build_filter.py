"""Leveling loot filter that highlights upgrades over a character's gear.

  python build_filter.py <char> [slot=ip ...]      e.g. python build_filter.py alcara helm=270

Everything per character lives in chars/<char>/ (git-ignored, personal):
  settings.json   name, class, filter name, guide, uniques, preferences
  build.json      wanted stats per slot (python maxroll_import.py <guide> --char <char>)
  equipped.json   the gear you wear
  filter_version.txt, filter.{txt,json,md}   the generated filter

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
  Cyan      = sidegrade, only in slots whose equipped piece already has
              SIDEGRADE_FROM+ wanted stats: same count, at least its Item
              Power; compare the rolls
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
one is loaded; bump filter_version.txt for every new filter.

Rings and paired weapons use the weaker of the pair (lower Item Power, fewer
wanted stats). Weapon slot groups are per class (CLASS_GROUPS); a new class
needs its groups added, with item type IDs confirmed in-game.
"""
import json
import os
import sys

import d4filter
from ids import *

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) < 2 or "=" in sys.argv[1]:
    chars_dir = os.path.join(HERE, "chars")
    chars = sorted(os.listdir(chars_dir)) if os.path.isdir(chars_dir) else []
    sys.exit("usage: python build_filter.py <char> [slot=ip ...]; characters: "
             + (", ".join(chars) or "none"))
CHAR = sys.argv[1]
CHAR_DIR = os.path.join(HERE, "chars", CHAR)
settings = json.load(open(os.path.join(CHAR_DIR, "settings.json"), encoding="utf-8"))
# Filter version: kept in the character's folder. Bump it for every new filter.
VERSION_FILE = os.path.join(CHAR_DIR, "filter_version.txt")
VERSION = int(open(VERSION_FILE).read()) if os.path.exists(VERSION_FILE) else 1
old = d4filter.decode(open(os.path.join(HERE, "testdata", "export_original.txt")).read())
latest = d4filter.decode(open(os.path.join(HERE, "testdata", "export_v8_after_import.txt")).read())
keep = {r["name"].strip(): r for r in old["rules"]}

UP, SIDE, IP_ONLY, CODEX, SELL = "#FF00FF", "#00FFFF", "#4A9AA5", "#FF3030", "#FFA0D0"
# Sidegrades (same wanted-stat count, at least equipped Item Power) are only
# shown for slots whose equipped piece already has this many wanted stats:
# by then most remaining upgrades are better rolls, not more stats.
SIDEGRADE_FROM = settings.get("sidegrade_from", 3)
IP_MAX = 900    # the game clamps the Item Power range maximum to 900

# Wanted stats come from build.json (python maxroll_import.py <guide URL>).
# The character's own preferences on top of the guide (settings.json):
BY_NAME = {v: k for k, v in NAMES.items()}
MUST = {slot: BY_NAME[name] for slot, name in settings.get("must", {}).items()}
NO_TEMPER_REMINDER = set(settings.get("no_temper_reminder", []))
# Per-slot floor on wanted stats (counting the must stat) for the upgrade tier, e.g. {"Ring": 3} when the
# equipped piece holds something the stats can't see (a Soulstone splinter).
MIN_WANTED = settings.get("min_wanted", {})
# Weapon stat tiers listed here need Rare or better (Magic/Normal can't be
# tempered); the Item-Power-only weapon tier stays any rarity, since a Magic
# weapon can still be a DPS upgrade.
RARE_PLUS_ONLY = set(settings.get("rare_plus_only", []))
RARE_PLUS = {"type": "rarity", "mask": 4 | 8 | 16 | 32 | 64}   # Rare and up
# From this Item Power up, Magic and Common items are never marked: a rule that
# a Magic item could still pass (2 or fewer required affixes, or the Item Power
# tier) is split into an any-rarity part below it and a Rare-or-better part above.
RARE_PLUS_FROM = settings.get("rare_plus_from_ip", IP_MAX + 1)
ARMOR_GROUPS = [
    ("Helm", ["helm"], [HELM]), ("Chest", ["chest"], [CHEST]),
    ("Gloves", ["gloves"], [GLOVES]), ("Pants", ["pants"], [PANTS]),
    ("Boots", ["boots"], [BOOTS]), ("Amulet", ["amulet"], [AMULET]),
    ("Ring", ["ring1", "ring2"], [RING]),
]
# (label, build/equipped slot keys, item types) for each class's weapons.
CLASS_GROUPS = {
    "rogue": [("Ranged", ["ranged"], [CROSSBOW, BOW]),
              ("Melee", ["mainhand", "offhand"], [SWORD, DAGGER])],
}
if settings["class"] not in CLASS_GROUPS:
    sys.exit(f"no weapon slot groups for class {settings['class']!r} yet: add them to CLASS_GROUPS")
GROUPS = ARMOR_GROUPS + CLASS_GROUPS[settings["class"]]
WEAPON_TYPES = {label: types for label, _, types in CLASS_GROUPS[settings["class"]]}
WEAPON_KEYS = {label: keys for label, keys, _ in CLASS_GROUPS[settings["class"]]}
build = json.load(open(os.path.join(CHAR_DIR, "build.json"), encoding="utf-8"))
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

eq_path = os.path.join(CHAR_DIR, "equipped.json")
equipped = json.load(open(eq_path))
# "_screenshots_processed_through" records the newest Documents\Diablo IV\Screenshots
# file already read into equipped.json, so a gear update only needs newer ones.
for arg in sys.argv[2:]:
    key, ip = arg.split("=")
    if key not in equipped:
        sys.exit(f"unknown slot {key!r}; use one of {', '.join(equipped)}")
    equipped[key]["ip"] = int(ip)
if sys.argv[2:]:
    json.dump(equipped, open(eq_path, "w"), indent=2)


def count(key, wanted):
    """Wanted stats (by tooltip name) on an equipped piece."""
    return sum(NAMES[i] in equipped[key]["stats"] for i in wanted)


def rule(name, color, *conds, action="recolor"):
    return {"name": name, "action": action, "color": color, "enabled": True,
            "conditions": list(conds)}


def rare_split(r):
    """Apply rare_plus_from_ip to a rule a Magic item could pass."""
    conds = r["conditions"]
    ip = next(c for c in conds if c["type"] == "item_power")
    if RARE_PLUS in conds or ip["min"] > IP_MAX or RARE_PLUS_FROM > IP_MAX:
        return [r]
    if ip["min"] >= RARE_PLUS_FROM:
        return [dict(r, conditions=conds + [RARE_PLUS])]
    low = [dict(c, max=RARE_PLUS_FROM - 1) if c is ip else c for c in conds]
    high = [dict(c, min=RARE_PLUS_FROM) if c is ip else c for c in conds]
    return [dict(r, conditions=low), dict(r, name=r["name"] + " R", conditions=high + [RARE_PLUS])]


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
    n = min(max(have + 1, MIN_WANTED.get(label, 0) - (must is not None)), len(wanted))
    # Magic items have at most 2 affixes, so only rules needing 2 or fewer can match them.
    split = lambda r, k: rare_split(r) if k + (must is not None) <= 2 else [r]
    out = split(rule(f"{label} up", UP, *base, *affixes(n)), n)
    total_have = have + (must is not None)
    if total_have >= SIDEGRADE_FROM and n > have:   # n == have: magenta already covers it
        out += split(rule(f"{label} same", SIDE, *base, *affixes(have)), have)
    summary.append((label, floor, have + (must is not None), len(wanted) + (must is not None)))
    return out


summary = []
rules = []
if settings.get("uniques"):
    rules.append(rule(settings.get("uniques_rule", "Target Uniques"), UP,
                      {"type": "unique", "ids": settings["uniques"]}))
tiers = [slot_rules(*s) for s in SLOTS]
rules += [r for t in tiers for r in t if r["color"] == UP]
rules += [r for t in tiers for r in t if r["color"] == SIDE]
ip_group = settings.get("ip_only_group")
if ip_group:   # weapon at or above equipped Item Power, any stats (but the group's must stat)
    ip_must = MUST.get(WEAPON_KEYS[ip_group][0])
    rules += rare_split(rule(f"{ip_group} IP only", IP_ONLY,
                      {"type": "item_type", "ids": WEAPON_TYPES[ip_group]},
                      {"type": "item_power",
                       "min": min(equipped[k]["ip"] for k in WEAPON_KEYS[ip_group]),
                       "max": IP_MAX},
                      *([{"type": "affixes", "ids": [ip_must], "mode": 1}] if ip_must else [])))
rules.append(rule("Codex Upgrade", CODEX, {"type": "codex", "flag": 1}))
# GA CDR as originally exported asked for "at least 2" of a single affix,
# which can never match; it needs "at least 1".
ga_cdr = json.loads(json.dumps(keep["GA CDR"]))
for c in ga_cdr["conditions"]:
    if c["type"] == "affixes":
        c["mode"] = 1
rules += [dict(keep["Legendary Seal (Sell)"], color=SELL),
          dict(ga_cdr, color=UP), dict(keep["All Skills"], color=UP)]
assert {r["color"] for r in rules} <= {UP, SIDE, IP_ONLY, CODEX, SELL}, "one meaning per color"

flt = {"name": f"{settings['filter_prefix']} v{VERSION}", "rules": rules,
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
json.dump(flt, open(os.path.join(CHAR_DIR, "filter.json"), "w"), indent=2)
open(os.path.join(CHAR_DIR, "filter.txt"), "w").write(s + "\n")
open(os.path.join(CHAR_DIR, "filter.md"), "w", encoding="utf-8").write(
    d4filter.table(d4filter.decode(s)) + "\n")
print(f"{settings['name']} ({settings['class']}): v{VERSION}, {len(rules)}/25 rules, "
      f"from {build['profile']!r} of planner {build['planner']}")
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

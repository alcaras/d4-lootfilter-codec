"""Import wanted stats per slot from a Maxroll build guide or planner.

  python maxroll_import.py <maxroll guide or planner URL> [--profile NAME] [--char NAME | --out PATH]

Fetches the planner behind the guide (planners.maxroll.gg JSON, the same
public endpoint d4lf's importer uses) and Maxroll's game data, picks a planner
profile (default: the first whose name contains "Leveling"), and writes
build.json: per slot, the wanted stats (the item's explicit affixes) and the
tempers.

Maxroll lists per-slot affix variants (e.g. X2_Damage_to_Vulnerable_Greater
on gloves), but the in-game filter only accepts one ID per stat and silently
drops the others. Variants with the same underlying game attributes are the
same stat, so each one is mapped onto the ID confirmed in-game
(ids.CONFIRMED_AFFIXES). Stats without a confirmed ID get a best guess and
are flagged: confirm them with one in-game import/export and add them to
ids.py.

Downloads are cached in .cache/ for a day.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

from ids import CONFIRMED_AFFIXES, NAMES

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
UA = {"User-Agent": "d4-lootfilter-codec (github.com/alcaras/d4-lootfilter-codec)"}
PLANNER_API = "https://planners.maxroll.gg/profiles/d4/"
GAME_DATA = "https://assets-ng.maxroll.gg/d4-tools/game/data.min.json?latest"
PLANNER_LINK = re.compile(r"https://maxroll\.gg/d4/planner/([A-Za-z0-9]+)")

# planner equipment slot -> our slot key
SLOTS = {"4": "helm", "5": "chest", "13": "gloves", "14": "pants", "15": "boots",
         "18": "amulet", "16": "ring1", "17": "ring2", "10": "ranged",
         "11": "mainhand", "12": "offhand"}

TEMPER_NAMES = [  # substring of the temper affix name -> readable name
    ("LifeMax", "Maximum Life"), ("MovementSpeed", "Movement Speed"),
    ("Type_Poison", "Poison Damage"), ("to_DoT", "Damage over Time"),
    ("Armor", "Armor"), ("Resistance", "Resistance"), ("CritChance", "Critical Strike Chance"),
    ("CDR", "Cooldown Reduction"), ("to_Close", "Damage to Close Enemies"),
]


def fetch(url, cache_name, max_age=86400):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, cache_name)
    if not (os.path.exists(path) and time.time() - os.path.getmtime(path) < max_age):
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
            f.write(r.read())
    return open(path, encoding="utf-8").read()


def planner_id(url):
    m = PLANNER_LINK.search(url)
    if m:
        return m.group(1)
    page = fetch(url.split("#")[0], "guide_" + re.sub(r"\W+", "_", url.split("#")[0])[-80:] + ".html")
    ids = sorted(set(PLANNER_LINK.findall(page)))
    if len(ids) != 1:
        sys.exit(f"expected one planner link in the guide, found {ids or 'none'}")
    return ids[0]


def attr_key(affix):
    """The stat an affix grants: its game attributes, ignoring formula/rolls."""
    return tuple(sorted((a["id"], a.get("param")) for a in affix.get("attributes", [])))


def prettify_temper(name):
    for needle, label in TEMPER_NAMES:
        if needle in name:
            return label
    return re.sub(r"_?Tier\d+$", "", name.replace("Tempered_", "")).replace("_", " ")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--profile", help="planner profile name (default: first containing 'Leveling')")
    ap.add_argument("--char", help="write chars/<char>/build.json")
    ap.add_argument("--out", help="output path (default: chars/<char>/build.json, else build.json)")
    args = ap.parse_args()
    if not args.out:
        args.out = (os.path.join(HERE, "chars", args.char, "build.json") if args.char
                    else os.path.join(HERE, "build.json"))

    pid = planner_id(args.url)
    planner = json.loads(json.loads(fetch(PLANNER_API + pid, f"planner_{pid}.json"))["data"])
    game = json.loads(fetch(GAME_DATA, "maxroll_game_data.json"))
    affixes = {v["id"]: dict(v, name=k) for k, v in game["affixes"].items() if isinstance(v, dict)}

    profiles = planner["profiles"]
    if args.profile:
        matches = [p for p in profiles if p["name"] == args.profile]
    else:
        matches = [p for p in profiles if "leveling" in p["name"].lower()]
    if not matches:
        sys.exit("profiles: " + ", ".join(repr(p["name"]) for p in profiles))
    profile = matches[0]

    canonical = {attr_key(affixes[i]): i for i in CONFIRMED_AFFIXES if i in affixes}

    def resolve(nid):
        a = affixes.get(nid)
        if a is None:
            return {"id": nid, "name": f"unknown {nid}", "maxroll": nid, "confirmed": False}
        key = attr_key(a)
        if key in canonical:
            cid = canonical[key]
            return {"id": cid, "name": NAMES[cid], "maxroll": a["name"], "confirmed": True}
        # Best guess: the plain S04_ version if one exists, else the shortest
        # same-stat affix name without slot/greater suffixes.
        same = [b for b in affixes.values()
                if attr_key(b) == key and b.get("flags") in (1027, 1091) and b.get("itemLabels")]
        same.sort(key=lambda b: (not b["name"].startswith("S04_"),
                                 any(t in b["name"] for t in ("Greater", "Jewelry", "2H", "Lesser")),
                                 len(b["name"])))
        guess = same[0] if same else a
        return {"id": guess["id"], "name": guess["name"], "maxroll": a["name"], "confirmed": False}

    slots = {}
    for slot_no, key in SLOTS.items():
        idx = profile["items"].get(slot_no)
        if idx is None:
            continue
        item = planner["items"][str(idx)]
        wanted = [resolve(e["nid"]) for e in item.get("explicits", [])]
        tempers = [prettify_temper(affixes[t["nid"]]["name"]) if t["nid"] in affixes else str(t["nid"])
                   for t in item.get("tempered", [])]
        slots[key] = {"item": item.get("name") or item["id"], "wanted": wanted, "tempers": tempers}

    out = {"source": args.url, "planner": pid, "profile": profile["name"],
           "game_data_version": game.get("version"), "slots": slots}
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)

    print(f"Planner {pid}, profile {profile['name']!r}, game data {game.get('version')}")
    unconfirmed = []
    for key, s in slots.items():
        names = [w["name"] + ("" if w["confirmed"] else " (?)") for w in s["wanted"]]
        print(f"  {key:8} {', '.join(names)}  | temper: {', '.join(s['tempers']) or '-'}")
        unconfirmed += [w for w in s["wanted"] if not w["confirmed"]]
    if unconfirmed:
        print("\nNot yet confirmed in-game (best guess; verify with an import/export):")
        for w in {w["id"]: w for w in unconfirmed}.values():
            print(f"  {w['id']} {w['name']}  (Maxroll: {w['maxroll']})")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()

"""Diablo IV in-game Loot Filter import/export codec.

The share string is base64(protobuf). The game writes every field explicitly
(including zero values such as action=0 or enabled=0), so this is a hand-rolled
wire codec rather than generated protobuf code: proto3 would drop the zeros and
the bytes would no longer match.

Usage:
  python d4filter.py decode <string|file>        -> JSON on stdout
  python d4filter.py encode <file.json>          -> import string on stdout
  python d4filter.py table  <string|file|json>   -> markdown table of rules
  python d4filter.py test                        -> round-trip self test

JSON shape (see leveling_filter.json for a full example):
  {"name": str, "f3": 2, "f4": 2, "rules": [
     {"name": str, "action": "show"|"hide_label"|"recolor"|"hide"|int,
      "color": "#RRGGBB" | "#AARRGGBB", "enabled": bool,
      "conditions": [ {"type": "<kind>", ...fields...}, ... ]}]}

Condition kinds and their fields (field numbers in brackets):
  item_power   [1=0]  min [4], max [5]
  rarity       [1=1]  mask [4]  1 Common 2 Magic 4 Rare 8 Legendary 16 Unique
                                32 Mythic 64 Talisman Set (confirmed in-game)
  properties   [1=2]  mask [4]  1 None, 4 Ancestral
  codex        [1=3]  flag [6]
  ga_check     [1=4]  value [4] (required GA count), flag [6]
  item_type    [1=5]  ids [2]
  affixes      [1=6]  "Has Required Affixes": ids [2], greater [3] ([a, b] pairs),
                      mode [4] = "Must have at least N of the selected affixes"
  optional_affixes [1=7]  same fields as affixes
  unique       [1=8]  ids [2]
  talisman_set [1=9]  ids [2], greater [3] ((set id, item id) pairs)
Schema agrees with github.com/fnuecke/diablo4-loot-filter-viewer.

Game limits seen in practice: a rule name longer than 24 characters is dropped
on import (the rule shows as "Rule #N"), and the game keeps only one canonical
affix ID per stat (e.g. 1834112 for Vulnerable Damage) and silently drops the
slot-specific duplicates.
Any optional field is only written when present in the JSON, in ascending
field-number order, which is how the game writes it.
"""
import base64
import json
import os
import sys

from ids import NAMES

# --------------------------------------------------------------------------
# wire level
# --------------------------------------------------------------------------
VARINT, I64, LEN, I32 = 0, 1, 2, 5


def read_varint(b, i):
    r = s = 0
    while True:
        c = b[i]
        i += 1
        r |= (c & 0x7F) << s
        s += 7
        if c < 0x80:
            return r, i


def parse(b):
    """Return [(field, wiretype, value)] in wire order. LEN values stay bytes."""
    out, i = [], 0
    while i < len(b):
        key, i = read_varint(b, i)
        f, w = key >> 3, key & 7
        if w == VARINT:
            v, i = read_varint(b, i)
        elif w == I32:
            v = int.from_bytes(b[i:i + 4], "little")
            i += 4
        elif w == I64:
            v = int.from_bytes(b[i:i + 8], "little")
            i += 8
        elif w == LEN:
            n, i = read_varint(b, i)
            v = bytes(b[i:i + n])
            i += n
        else:
            raise ValueError(f"unsupported wire type {w} at offset {i}")
        out.append((f, w, v))
    if i != len(b):
        raise ValueError("trailing bytes")
    return out


def varint(n):
    if n < 0:
        raise ValueError("negative varint")
    out = bytearray()
    while True:
        c = n & 0x7F
        n >>= 7
        if n:
            out.append(c | 0x80)
        else:
            out.append(c)
            return bytes(out)


def key(f, w):
    return varint((f << 3) | w)


def f_varint(f, v):
    return key(f, VARINT) + varint(int(v))


def f_fixed32(f, v):
    return key(f, I32) + int(v).to_bytes(4, "little")


def f_bytes(f, v):
    return key(f, LEN) + varint(len(v)) + v


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------
ACTIONS = {0: "show", 1: "hide_label", 2: "recolor", 3: "hide"}
ACTION_IDS = {v: k for k, v in ACTIONS.items()}
COND_KINDS = {0: "item_power", 1: "rarity", 2: "properties", 3: "codex",
              4: "ga_check", 5: "item_type", 6: "affixes", 7: "optional_affixes",
              8: "unique", 9: "talisman_set"}
COND_IDS = {v: k for k, v in COND_KINDS.items()}
# field number -> (json key, wire type); per condition kind
COND_FIELDS = {
    "item_power": {4: "min", 5: "max"},
    "rarity": {4: "mask"},
    "properties": {4: "mask"},
    "codex": {6: "flag"},
    "ga_check": {4: "value", 6: "flag"},
    "item_type": {2: "ids"},
    "affixes": {2: "ids", 3: "greater", 4: "mode"},
    "optional_affixes": {2: "ids", 3: "greater", 4: "mode"},
    "unique": {2: "ids"},
    "talisman_set": {2: "ids", 3: "greater"},
}


def _expect(cond, f, w, got):
    if w != got:
        raise ValueError(f"unexpected wire type {w} for field {f} in {cond}")


def decode_condition(b):
    fields = parse(b)
    if not fields or fields[0][0] != 1:
        raise ValueError("condition without leading type field")
    t = fields[0][2]
    kind = COND_KINDS.get(t, t)
    names = COND_FIELDS.get(kind, {})
    c = {"type": kind}
    for f, w, v in fields[1:]:
        name = names.get(f)
        if name is None:
            raise ValueError(f"unknown field {f} in condition {kind}")
        if name == "ids":
            _expect(kind, f, w, I32)
            c.setdefault("ids", []).append(v)
        elif name == "greater":
            _expect(kind, f, w, LEN)
            inner = parse(v)
            if [(x[0], x[1]) for x in inner] != [(1, I32), (2, I32)]:
                raise ValueError(f"unexpected greater-affix entry {inner}")
            c.setdefault("greater", []).append([inner[0][2], inner[1][2]])
        else:
            _expect(kind, f, w, VARINT)
            c[name] = v
    return c


def encode_condition(c):
    kind = c["type"]
    t = COND_IDS[kind] if isinstance(kind, str) else kind
    out = f_varint(1, t)
    for f, name in sorted(COND_FIELDS[COND_KINDS[t]].items()):
        if name not in c:
            continue
        if name == "ids":
            out += b"".join(f_fixed32(f, i) for i in c["ids"])
        elif name == "greater":
            out += b"".join(f_bytes(f, f_fixed32(1, a) + f_fixed32(2, g))
                            for a, g in c["greater"])
        else:
            out += f_varint(f, c[name])
    return out


def color_str(v):
    return f"#{v & 0xFFFFFF:06X}" if v >> 24 == 0xFF else f"#{v:08X}"


def color_int(s):
    s = s.lstrip("#")
    return int(s, 16) | (0xFF000000 if len(s) == 6 else 0)


def decode_rule(b):
    r = {}
    for f, w, v in parse(b):
        if f == 1 and w == LEN:
            r["name"] = v.decode("utf-8")
        elif f == 2 and w == VARINT:
            r["action"] = ACTIONS.get(v, v)
        elif f == 3 and w == I32:
            r["color"] = color_str(v)
        elif f == 4 and w == LEN:
            r.setdefault("conditions", []).append(decode_condition(v))
        elif f == 5 and w == VARINT:
            r["enabled"] = bool(v)
        else:
            raise ValueError(f"unknown rule field {f}/{w}")
    return r


def encode_rule(r):
    a = r["action"]
    out = f_bytes(1, r["name"].encode("utf-8")) if "name" in r else b""
    out += f_varint(2, ACTION_IDS[a] if isinstance(a, str) else a)
    out += f_fixed32(3, color_int(r["color"]))
    out += b"".join(f_bytes(4, encode_condition(c)) for c in r.get("conditions", []))
    out += f_varint(5, 1 if r.get("enabled", True) else 0)
    return out


def decode(s):
    b = base64.b64decode(s.strip())
    flt = {"name": None, "rules": []}
    for f, w, v in parse(b):
        if f == 1 and w == LEN:
            flt["rules"].append(decode_rule(v))
        elif f == 2 and w == LEN:
            flt["name"] = v.decode("utf-8")
        elif f in (3, 4) and w == VARINT:
            flt[f"f{f}"] = v
        else:
            raise ValueError(f"unknown filter field {f}/{w}")
    return flt


def encode(flt):
    out = b"".join(f_bytes(1, encode_rule(r)) for r in flt["rules"])
    out += f_bytes(2, flt["name"].encode("utf-8"))
    for f in (3, 4):
        if f"f{f}" in flt:
            out += f_varint(f, flt[f"f{f}"])
    return base64.b64encode(out).decode("ascii")


# --------------------------------------------------------------------------
# pretty printing
# --------------------------------------------------------------------------
def name_of(i):
    return f"{NAMES.get(i, '??? UNKNOWN')} ({i})"


def describe_condition(c):
    k = c["type"]
    if k in ("item_type", "unique"):
        label = "Item type" if k == "item_type" else "Unique"
        return f"{label} any of: " + ", ".join(name_of(i) for i in c["ids"])
    if k in ("affixes", "optional_affixes"):
        label = "Required" if k == "affixes" else "Optional"
        s = f"{label} affixes, at least {c.get('mode')} of: " + ", ".join(name_of(i) for i in c["ids"])
        if c.get("greater"):
            s += "; Greater required: " + ", ".join(name_of(a) for a, _ in c["greater"])
        return s
    if k == "rarity":
        names = ["Common", "Magic", "Rare", "Legendary", "Unique", "Mythic", "Talisman Set"]
        return "Rarity: " + ", ".join(n for b, n in enumerate(names) if c["mask"] >> b & 1)
    if k == "properties":
        return {1: "Properties: None", 4: "Properties: Ancestral",
                5: "Properties: None or Ancestral"}.get(c["mask"], f"Properties mask {c['mask']}")
    if k == "ga_check":
        return f"At least {c.get('value')} Greater Affix(es)"
    if k == "codex":
        return "Codex Upgrade Check"
    if k == "item_power":
        return "Item Power " + " ".join(f"{x} {c[x]}" for x in ("min", "max") if x in c)
    return json.dumps(c)


def table(flt):
    lines = [f"Filter: **{flt['name']}** ({len(flt['rules'])} rules)", "",
             "| # | Rule | Action | Color | On | Conditions (all must match) |",
             "|---|---|---|---|---|---|"]
    for n, r in enumerate(flt["rules"], 1):
        conds = "<br>".join(describe_condition(c) for c in r.get("conditions", []))
        lines.append(f"| {n} | {r.get('name', '(no name)')} | {r['action']} | {r['color']} | "
                     f"{'yes' if r.get('enabled', True) else 'no'} | {conds} |")
    return "\n".join(lines)


def _load(arg):
    if os.path.isfile(arg):
        text = open(arg, encoding="utf-8").read()
        if arg.endswith(".json"):
            return json.loads(text)
        return decode(text)
    return decode(arg)


def selftest():
    """Every real game export in testdata/ must round-trip byte-for-byte."""
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata")
    if not os.path.isdir(here) or not os.listdir(here):
        sys.exit("No testdata/: put real in-game export strings there (one per .txt file).")
    for fn in sorted(os.listdir(here)):
        src = open(os.path.join(here, fn)).read().strip()
        flt = decode(src)
        again = encode(json.loads(json.dumps(flt)))  # through JSON, like real use
        assert again == src, f"round-trip mismatch: {fn}"
        print(f"OK {fn}: {len(flt['rules'])} rules, "
              f"{len(base64.b64decode(src))} bytes round-trip byte-for-byte")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("decode", "encode", "table", "test"):
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "test":
        selftest()
    elif cmd == "decode":
        print(json.dumps(_load(sys.argv[2]), indent=2))
    elif cmd == "encode":
        print(encode(_load(sys.argv[2])))
    elif cmd == "table":
        print(table(_load(sys.argv[2])))

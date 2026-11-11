"""Data-driven crafting. Recipes ask for material *tags and power*, not single items,
so 160 different materials feed a handful of rules."""
from data_items import ALL, DIFFS, ITEMS
from data_weapons import RARITIES

HEAL = ("reishi", "dust", "sekki")
BODY = ("bone", "fang", "thread", "cloth", "ribbon")
SOUL = ("mask", "ore")
CATS = ("potion", "upgrade", "key", "evo")
TAGS = HEAL + BODY + SOUL


def _inp(tags, pw, qty):
    return {"tags": list(tags), "pw": min(3, pw), "qty": qty}   # power >3 is too rare per tag; quantity scales instead


def _build():
    rec = {}
    # potions: one recipe per power tier and kind
    for kind in ("hp", "reiatsu"):
        by_tier = {}
        for x in ITEMS:
            e = x.get("effect") or {}
            if x["subtype"] == "potion" and e.get("type") == kind:
                by_tier.setdefault(RARITIES.index(x["rarity"]), x["_id"])
        for tier, iid in sorted(by_tier.items()):
            pw = tier + 1
            rid = f"pt_{kind}_{pw}"
            rec[rid] = {"id": rid, "cat": "potion", "out": iid, "inputs": [_inp(HEAL, pw, 1 + pw)],
                        "coins": int(ALL[iid]["base_price"] * 0.5), "min_level": 1}
    # dungeon keys
    for x in ITEMS:
        e = x.get("effect") or {}
        if e.get("type") == "key":
            df = DIFFS.index(e["diff"])
            rid = "ky_" + x["_id"]
            rec[rid] = {"id": rid, "cat": "key", "out": x["_id"],
                        "inputs": [_inp(BODY, df + 1, 2 + df), _inp(SOUL, df + 1, 1 + df // 2)],
                        "coins": int(x["base_price"] * 0.6), "min_level": 1}
    # evolution items
    for x in ITEMS:
        e = x.get("effect") or {}
        if e.get("type") == "evo":
            s = e["stage"]
            rid = "ev_" + x["_id"]
            rec[rid] = {"id": rid, "cat": "evo", "out": x["_id"],
                        "inputs": [_inp(SOUL, s + 1, 2 + 2 * s), _inp(HEAL, s + 1, 2 + s)],
                        "coins": 1500 * s, "min_level": [1, 15, 35, 60, 90][s]}
    return rec


RECIPES = _build()

# ---- armor upgrade: next-rarity armor, preferring the same "flavour" (adjective) ---------------------------
_ARMORS = [x for x in ITEMS if x["subtype"] == "armor"]
_POS = {x["_id"]: i for i, x in enumerate(_ARMORS)}


def upgrade_of(item_id: str):
    src = ALL.get(item_id)
    if not src or src.get("subtype") != "armor":
        return None
    ri = RARITIES.index(src["rarity"])
    sd = src["stats"]["def"]
    pool = [x for x in _ARMORS if RARITIES.index(x["rarity"]) == ri + 1 and x["stats"]["def"] > sd]
    if not pool:
        return None
    same = [x for x in pool if _POS[x["_id"]] % 16 == _POS[item_id] % 16]
    return min(same or pool, key=lambda x: (x["stats"]["def"], x["_id"]))["_id"]


def upgrade_recipe(item_id: str):
    out = upgrade_of(item_id)
    if not out:
        return None
    pw = RARITIES.index(ALL[out]["rarity"]) + 1
    return {"id": "up_" + item_id, "cat": "upgrade", "src": item_id, "out": out,
            "inputs": [_inp(BODY, pw, 3)], "coins": int(ALL[out]["base_price"] * 0.5),
            "min_level": ALL[out].get("level_req", 1)}


def get_recipe(rid: str):
    if rid.startswith("up_"):
        return upgrade_recipe(rid[3:])
    return RECIPES.get(rid)


# ---- pure material planning ------------------------------------------------------------------------------------
def mat_candidates(inv_items: dict, tags, pw):
    out = []
    for iid, q in inv_items.items():
        e = (ALL.get(iid) or {}).get("effect") or {}
        if q > 0 and e.get("type") == "mat" and e["tag"] in tags and e["pw"] >= pw:
            out.append((e["pw"], ALL[iid]["base_price"], iid))
    return [iid for _, _, iid in sorted(out)]   # weakest sufficient material first


def plan(inv_items: dict, recipe: dict):
    """-> list[(item_id, qty)] to consume (cheapest sufficient first), or None if short."""
    left = dict(inv_items)
    take = []
    if recipe.get("src"):
        if left.get(recipe["src"], 0) < 1:
            return None
        left[recipe["src"]] -= 1
        take.append((recipe["src"], 1))
    for inp in recipe["inputs"]:
        need = inp["qty"]
        for iid in mat_candidates(left, inp["tags"], inp["pw"]):
            n = min(left[iid], need)
            if n:
                take.append((iid, n))
                left[iid] -= n
                need -= n
            if need <= 0:
                break
        if need > 0:
            return None
    return take


def missing(inv_items: dict, recipe: dict):
    """How many more materials are needed per input slot (for the panel)."""
    left = dict(inv_items)
    out = []
    for inp in recipe["inputs"]:
        need = inp["qty"]
        for iid in mat_candidates(left, inp["tags"], inp["pw"]):
            n = min(left[iid], need)
            left[iid] -= n
            need -= n
            if need <= 0:
                break
        out.append(max(0, need))
    return out

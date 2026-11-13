"""Pure rules of the shared world (no I/O): variables, modifiers, event kinds,
territory and season maths. Texts live in the locale files (ev_*, wv_*)."""
import math
from datetime import datetime, timezone

from data_races import LOCATIONS

LOC_IDS = list(LOCATIONS)
VAR_START = {"threat": 20.0, "stability": 70.0}
REISHI_START = 50.0
SEI_LOCS = ("soul_society", "seireitei", "rukongai", "karakura", "zaraki_district", "sokyoku_hill",
            "shinigami_academy", "inuzuri", "senzaikyu", "maggot_nest")
HOLLOW_LOCS = ("rukongai", "karakura", "hueco_mundo", "las_noches", "dangai", "valley_screams", "forest_menos", "fake_karakura", "garganta_tunnel")
KEY_PTS = {"normal": 1, "hard": 2, "nightmare": 4, "abyss": 8, "legendary": 16}

# kind -> data. pts: points per action. locs: where the action must happen (None = anywhere).
# mods: multipliers while the event is active (applied in `locs_mod` places only, None = everywhere).
EVENTS = {
    "garganta": {"icon": "🌀", "pts": {"pve_win": 1, "elite_win": 3, "dungeon_clear": 5, "key": 1},
                 "locs": None, "mods": {"enemy": 1.20, "drop": 1.40, "xp": 1.10, "coin": 1.0}, "mod_locs": HOLLOW_LOCS,
                 "win": {"threat": -15.0, "stability": 0.0}, "lose": {"threat": 10.0, "stability": -5.0}},
    "siege": {"icon": "🏯", "pts": {"explore": 1, "pve_win": 1, "elite_win": 2, "boss_hit": 2, "key": 1},
              "locs": SEI_LOCS, "mods": {"enemy": 1.15, "drop": 1.0, "xp": 1.15, "coin": 1.10}, "mod_locs": SEI_LOCS,
              "win": {"threat": 0.0, "stability": 25.0}, "lose": {"threat": 3.0, "stability": -15.0}},
    "wandenreich": {"icon": "✝️", "pts": {"pve_win": 1, "elite_win": 2, "pvp_win": 3, "boss_hit": 2, "dungeon_clear": 4, "key": 1},
                    "locs": None, "mods": {"enemy": 1.30, "drop": 1.20, "xp": 1.25, "coin": 1.0}, "mod_locs": None,
                    "win": {"threat": -10.0, "stability": 10.0}, "lose": {"threat": 5.0, "stability": -12.0}},
    "winter_war": {"icon": "🌑", "pts": {"pve_win": 1, "elite_win": 2, "pvp_win": 3, "boss_hit": 2, "dungeon_clear": 4, "key": 1},
                   "locs": ("karakura", "fake_karakura", "hueco_mundo", "las_noches", "forest_menos"), "mods": {"enemy": 1.25, "drop": 1.25, "xp": 1.20, "coin": 1.10},
                   "mod_locs": ("karakura", "fake_karakura", "hueco_mundo", "las_noches", "forest_menos"),
                   "win": {"threat": -12.0, "stability": 8.0}, "lose": {"threat": 8.0, "stability": -10.0}},
    "dangai": {"icon": "🌌", "pts": {"explore": 1, "pve_win": 1, "elite_win": 2, "dungeon_clear": 6, "key": 1},
               "locs": ("dangai", "royal_palace", "soul_king"), "mods": {"enemy": 1.20, "drop": 1.30, "xp": 1.30, "coin": 1.0},
               "mod_locs": ("dangai", "royal_palace", "soul_king"),
               "win": {"threat": -5.0, "stability": 15.0}, "lose": {"threat": 4.0, "stability": -8.0}},
}
EVENT_KINDS = list(EVENTS)


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(v)))


def week_id(now: float = None) -> str:
    y, w, _ = datetime.fromtimestamp(now if now is not None else __import__("time").time(), timezone.utc).isocalendar()
    return f"{y}-W{w:02d}"


def day_id(now: float = None) -> str:
    return datetime.fromtimestamp(now if now is not None else __import__("time").time(), timezone.utc).strftime("%Y-%m-%d")


def event_mods(event: dict, loc: str) -> dict:
    """Multipliers of the active event at a location (1.0 when none apply)."""
    out = {"enemy": 1.0, "drop": 1.0, "xp": 1.0, "coin": 1.0}
    if not event or event.get("status") != "active":
        return out
    ev = EVENTS.get(event.get("kind"))
    if not ev:
        return out
    if ev["mod_locs"] is None or loc in ev["mod_locs"]:
        out.update(ev["mods"])
    return out


def world_mods(ws: dict, loc: str, st: dict, event: dict = None) -> dict:
    """All multipliers the world applies at `loc`. Pure: ws is the world_state doc."""
    ws = ws or {}
    threat = clamp(ws.get("threat", VAR_START["threat"]))
    stab = clamp(ws.get("stability", VAR_START["stability"]))
    reishi = clamp((ws.get("reishi") or {}).get(loc, REISHI_START))
    em = event_mods(event, loc)
    return {
        "enemy": max(1.0, (1 + threat / 100 * float(st["world_enemy_k"]))) * em["enemy"],
        "drop": (1 + (reishi - 50) / 50 * float(st["world_drop_k"])) * em["drop"],
        "xp": (1 + (stab - 50) / 50 * float(st["world_stab_xp_k"])) * em["xp"],
        "coin": em["coin"],
        "price": max(0.7, 1 + (threat - 50) / 100 * float(st["world_price_k"])),
        "threat": threat, "stability": stab, "reishi": reishi,
    }


def boss_hp_scale(active_players: int, threat: float, st: dict) -> float:
    ref = max(1, int(st["boss_hp_players_ref"]))
    pop = max(1.0, math.sqrt(max(1, active_players) / ref))
    thr = 1 + clamp(threat) / 100 * float(st["boss_hp_threat_k"])
    return min(float(st["boss_hp_scale_cap"]), pop * thr)


def boss_gap_seconds(st: dict, threat: float, rng) -> int:
    lo, hi = int(st["boss_min_minutes"]), int(st["boss_max_minutes"])
    base = rng.randint(min(lo, hi), max(lo, hi)) * 60
    k = 1 - clamp(threat) / 100 * float(st["world_boss_interval_k"])
    return max(300, int(base * max(0.4, k)))


def event_goal(active_players: int, st: dict) -> int:
    g = int(st["event_goal_per_player"]) * max(1, active_players)
    return max(int(st["event_goal_min"]), min(int(st["event_goal_cap"]), g))


def event_pts(kind: str, action: str, loc: str, n: int = 1) -> int:
    ev = EVENTS.get(kind)
    if not ev or action not in ev["pts"]:
        return 0
    if ev["locs"] is not None and action not in ("key",) and loc not in ev["locs"]:
        return 0
    return ev["pts"][action] * n


def pick_event_kind(ws: dict, st: dict, rng) -> str:
    """Which event the world is ready for (None = nothing). Threat and stability drive it."""
    threat, stab = clamp(ws.get("threat", 20)), clamp(ws.get("stability", 70))
    if threat >= float(st["event_threat_trigger"]):
        return "garganta"
    if stab <= float(st["event_stab_trigger"]):
        return "siege"
    if rng.random() < float(st["event_random_chance"]):
        return rng.choice(EVENT_KINDS)
    return None


def terr_pick_owner(scores: dict, prev_owner, min_score: int):
    """Weekly winner. The incumbent keeps the land on a tie; nobody wins below min_score."""
    if not scores:
        return prev_owner
    best_g, best = max(scores.items(), key=lambda kv: (kv[1], kv[0] == prev_owner))
    if best < min_score:
        return prev_owner
    if prev_owner and prev_owner in scores and scores[prev_owner] >= best:
        return prev_owner
    return best_g


def soft_reset_rating(rating: float, mean: float, k: float) -> int:
    return int(round(rating + (mean - rating) * k))


def season_pts_boss(share: float, killed: bool) -> int:
    return int(round(100 * share * (1.0 if killed else 0.4)))

"""Admin panel extras: pick from a list instead of typing ids.

  adbs / adbc / adbg  world boss picker: list -> detail card -> spawn exactly that boss
  adev / adec / adeg  world event picker: list -> detail card -> start that event (adee ends the running one)
  adi* / adip         item picker: category -> rarity -> page -> tap an item -> send `<player id> [count]`
  adz* / adzp         summon picker: rarity -> page -> tap a summon -> send `<player id> [count]`

Every action re-checks its permission level when pressed and again when the typed input arrives (the ASK table of
handlers_adminpanel does that for the two typed steps). Everything is written to the admin log.
"""
import logging

from admin_fa import EVENT_FA
from admin_panel_logic import parse_amount
from data_bosses import BOSS_BY_ID, BOSSES
from data_chars import CHAR_BY_ID, CHARS
from data_items import ALL
from data_weapons import RARITIES, RARITY_FA, RARITY_ICON
from database import col, game_settings
from handlers_admin import alog
from handlers_adminpanel import (ASK, T, _back, _deny, _need, _pending_set, _reply_id, _target_or_none, user_card)
from i18n import esc, fnum
from service_economy import inv_add
from ui import Out, action, head, nav

log = logging.getLogger("senka.adminplus")
PER = 8

CAT_FA = {"kido_card": "کارت کیدو", "material": "متریال", "armor": "زره", "accessory": "اکسسوری", "key": "کلید", "weapon": "سلاح",
          "potion": "معجون", "cosmetic": "ظاهری", "relic": "یادگار", "book": "کتاب", "evolution": "تکامل", "egg": "تخم",
          "charm": "طلسم", "quincy": "کوئینسی", "race_card": "کارت تکنیک نژادی",
          "temper": "سنگ آبدیده‌سازی", "inner_key": "کلید دنیای درون"}
CAT_ICON = {"kido_card": "🔮", "material": "🧱", "armor": "🛡", "accessory": "💍", "key": "🗝", "weapon": "⚔️", "potion": "🧪",
            "cosmetic": "🎨", "relic": "🏺", "book": "📖", "evolution": "🧬", "egg": "🥚", "charm": "🧿", "quincy": "✝️", "race_card": "🎴",
            "temper": "🪨", "inner_key": "🗝"}
CATS = [c for c in CAT_FA if any(v["category"] == c for v in ALL.values())]
TRAIT_FA = {"bleed": "خونریزی", "armor": "زره‌دار", "enrage": "خشم", "regen": "بازسازی", "dodge": "چابک", "decay": "پوسیدگی",
            "burn": "سوزش", "poison": "زهر", "illusion": "توهم"}

ASK["give_pick"] = (60, "بفرست: `<آیدی پلیر> [تعداد]` تا این آیتم به او داده شود:", "Send: `<player id> [count]` to give this item:", ("adi", ""))
ASK["give_summon"] = (60, "بفرست: `<آیدی پلیر> [تعداد]` تا این احضار به او داده شود:", "Send: `<player id> [count]` to give this summon:", ("adz", ""))


def _pages(n: int) -> int:
    return max(1, -(-n // PER))


def _page(arg, default=0) -> int:
    s = (arg or "").strip()
    return int(s) if s.lstrip("-").isdigit() else default


def _nm(d: dict, ctx) -> str:
    return d["name_fa" if ctx.lang == "fa" else "name_en"]


def _pager(page: int, pages: int, code: str, pre: str = ""):
    row = []
    if page > 0:
        row.append(("◀️", code, f"{pre}{page - 1}", False, "none"))
    if page < pages - 1:
        row.append(("▶️", code, f"{pre}{page + 1}", False, "none"))
    return row


# ---- world boss picker -------------------------------------------------------------------------------------------
async def _active_boss():
    return await col("boss_sessions").find_one({"scope": "global", "active": True})


@action("adbs")
async def boss_pick_list(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    page = max(0, min(_page(arg), _pages(len(BOSSES)) - 1))
    act = await _active_boss()
    chunk = BOSSES[page * PER:(page + 1) * PER]
    rows = [[(f"Lv{b['level']} · {_nm(b, ctx)}", "adbc", f"{b['_id']}:{page}", False, "none")] for b in chunk]
    pg = _pager(page, _pages(len(BOSSES)), "adbs")
    if pg:
        rows.append(pg)
    rows.append(_back(ctx, "adw", ""))
    cur = ""
    if act:
        cur = T(ctx, f"\n⚠️ باس فعال: <b>{esc(_nm(act, ctx))}</b> ({fnum(max(0, act['hp']), ctx.lang)}/{fnum(act['max_hp'], ctx.lang)}). اول باید پایانش بدی.\n",
                f"\n⚠️ Active boss: <b>{esc(_nm(act, ctx))}</b> ({max(0, act['hp'])}/{act['max_hp']}). End it first.\n")
    return Out(head(ctx, "ttl_adm") + T(ctx, f"👹 <b>انتخاب باس</b> | صفحه {fnum(page + 1, ctx.lang)}/{fnum(_pages(len(BOSSES)), ctx.lang)}\nیک باس را بزن تا مشخصاتش را ببینی.",
                                         f"👹 <b>Pick a boss</b> | page {page + 1}/{_pages(len(BOSSES))}\nTap one to see its card.") + cur, rows)


@action("adbc")
async def boss_pick_card(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    bid, _, p = (arg or "").partition(":")
    b = BOSS_BY_ID.get(bid)
    if not b:
        return Out(alert="?")
    page = _page(p)
    fa = ctx.lang == "fa"
    act = await _active_boss()
    trait = b.get("trait")
    lines = [f"👹 <b>{esc(_nm(b, ctx))}</b>",
             T(ctx, f"سطح {fnum(b['level'], ctx.lang)} · جان پایه {fnum(b['hp'], ctx.lang)} · حمله {fnum(b['attack'], ctx.lang)} · دفاع {fnum(b['defense'], ctx.lang)}",
               f"Level {b['level']} · base HP {b['hp']:,} · ATK {b['attack']} · DEF {b['defense']}")]
    if trait:
        lines.append(T(ctx, f"ویژگی: {TRAIT_FA.get(trait, trait)}", f"Trait: {trait}"))
    epi = b.get("epi_fa" if fa else "epi_en")
    if epi:
        lines.append(f"<i>{esc(epi)}</i>")
    lines.append(T(ctx, "جان نهایی با تعداد بازیکن‌ها و تهدید دنیا مقیاس می‌شود.", "Final HP scales with active players and world threat."))
    rows = []
    if act:
        lines.append(T(ctx, "\n⚠️ الان یک باس فعال است؛ تا تمام نشود اسپان جدید ممکن نیست.", "\n⚠️ A boss is already active; a new one cannot spawn until it ends."))
        rows.append([(T(ctx, "🛑 پایان باس فعلی", "🛑 End current boss"), "adbe", f"{bid}:{page}")])
    else:
        rows.append([(T(ctx, "✅ اسپان همین باس", "✅ Spawn this boss"), "adbg", bid)])
    rows.append(_back(ctx, "adbs", str(page)))
    return Out(head(ctx, "ttl_adm") + "\n".join(lines), rows)


@action("adbe")
async def boss_pick_end(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    await col("boss_sessions").update_many({"scope": "global", "active": True}, {"$set": {"expires_at": 0}})
    await alog(ctx.uid, "world_boss_end", None, None, None, "panel picker")
    out = await boss_pick_card(ctx, arg)
    out.alert = T(ctx, "باس پایان یافت؛ چند لحظه‌ی دیگر اسلات آزاد می‌شود.", "Boss ended; the slot frees up in a moment.")
    return out


@action("adbg")
async def boss_pick_go(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    b = BOSS_BY_ID.get((arg or "").strip())
    if not b:
        return Out(alert="?")
    from service_world import spawn_boss
    import handlers_world
    doc = await spawn_boss(boss_id=b["_id"])
    if not doc:
        return Out(alert=T(ctx, "یک باس فعال است یا اسپان نشد.", "A boss is active or the spawn failed."))
    try:
        await handlers_world.post_global_boss(ctx.bot, doc)
    except Exception:
        log.exception("boss announce failed")
    await alog(ctx.uid, "world_boss_spawn", b["_id"], None, {"name": b["name_en"]}, "panel picker")
    return Out(head(ctx, "ttl_adm") + T(ctx, f"✅ باس <b>{esc(b['name_fa'])}</b> اسپان شد.", f"✅ Spawned <b>{esc(b['name_en'])}</b>."),
               [[(T(ctx, "👹 انتخاب باس دیگر", "👹 Pick another"), "adbs", "0")], _back(ctx, "adw", "")])


# ---- world event picker -------------------------------------------------------------------------------------------
def _ev_name(kind, ctx):
    return EVENT_FA.get(kind, kind) if ctx.lang == "fa" else kind


@action("adev")
async def event_pick_list(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    from data_world import EVENTS
    from service_worldcore import get_world
    _, ev = await get_world(force=True)
    rows = [[(f"{d['icon']} {_ev_name(k, ctx)}", "adec", k, False, "none")] for k, d in EVENTS.items()]
    cur = ""
    if ev:
        rows.append([(T(ctx, "🛑 پایان رویداد فعلی", "🛑 End current event"), "adee", "")])
        cur = T(ctx, f"\n⚠️ رویداد فعال: <b>{_ev_name(ev['kind'], ctx)}</b> ({fnum(ev['progress'], ctx.lang)}/{fnum(ev['goal'], ctx.lang)}).",
                f"\n⚠️ Active event: <b>{ev['kind']}</b> ({ev['progress']}/{ev['goal']}).")
    rows.append(_back(ctx, "adw", ""))
    return Out(head(ctx, "ttl_adm") + T(ctx, "🌀 <b>انتخاب رویداد</b>\nیکی را بزن تا مشخصاتش را ببینی.", "🌀 <b>Pick an event</b>\nTap one to see its card.") + cur, rows)


@action("adec")
async def event_pick_card(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    from data_world import EVENTS
    k = (arg or "").strip()
    d = EVENTS.get(k)
    if not d:
        return Out(alert="?")
    st = await game_settings()
    m = d["mods"]
    lines = [f"{d['icon']} <b>{_ev_name(k, ctx)}</b>",
             T(ctx, f"مدت: {fnum(int(st['event_duration_minutes']), ctx.lang)} دقیقه",
               f"Duration: {int(st['event_duration_minutes'])} min"),
             T(ctx, f"قدرت دشمن ×{m['enemy']} · دراپ ×{m['drop']} · XP ×{m['xp']} · سکه ×{m['coin']}",
               f"Enemy ×{m['enemy']} · drop ×{m['drop']} · XP ×{m['xp']} · coins ×{m['coin']}"),
             T(ctx, f"برد: تهدید {d['win']['threat']:+g}، ثبات {d['win']['stability']:+g}", f"Win: threat {d['win']['threat']:+g}, stability {d['win']['stability']:+g}"),
             T(ctx, f"باخت: تهدید {d['lose']['threat']:+g}، ثبات {d['lose']['stability']:+g}", f"Lose: threat {d['lose']['threat']:+g}, stability {d['lose']['stability']:+g}")]
    return Out(head(ctx, "ttl_adm") + "\n".join(lines),
               [[(T(ctx, "✅ شروع این رویداد", "✅ Start this event"), "adeg", k)], _back(ctx, "adev", "")])


@action("adeg")
async def event_pick_go(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    from data_world import EVENTS
    from service_worldstate import event_start
    k = (arg or "").strip()
    if k not in EVENTS:
        return Out(alert="?")
    doc = await event_start(k)
    if not doc:
        return Out(alert=T(ctx, "رویداد دیگری فعال است.", "Another event is already running."))
    await alog(ctx.uid, "world_event_start", k, None, None, "panel picker")
    return Out(head(ctx, "ttl_adm") + T(ctx, f"✅ رویداد <b>{_ev_name(k, ctx)}</b> شروع شد.", f"✅ Event <b>{k}</b> started."),
               [[(T(ctx, "🌀 رویداد دیگر", "🌀 Another event"), "adev", "")], _back(ctx, "adw", "")])


@action("adee")
async def event_pick_end(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    from service_worldstate import event_end
    res = await event_end()  # success when the goal was reached
    await alog(ctx.uid, "world_event_end", None, None, None, "panel picker")
    out = await event_pick_list(ctx, "")
    out.alert = T(ctx, "پایان یافت ✅", "Ended ✅") if res else T(ctx, "رویدادی فعال نبود.", "No active event.")
    return out


# ---- item picker ---------------------------------------------------------------------------------------------------
def _items(cat: str, rar: str):
    return sorted((i for i, v in ALL.items() if v["category"] == cat and not v.get("retired") and (rar == "x" or v["rarity"] == rar)),
                  key=lambda i: (RARITIES.index(ALL[i]["rarity"]), ALL[i]["name_en"]))


@action("adi")
async def item_pick_cats(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    fa = ctx.lang == "fa"
    btns = [(f"{CAT_ICON.get(c, '📦')} {CAT_FA[c] if fa else c}", "adir", c, False, "none") for c in CATS]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    rows.append(_back(ctx, "ade", ""))
    return Out(head(ctx, "ttl_adm") + T(ctx, "🎒 <b>انتخاب آیتم</b>\nدسته را انتخاب کن:", "🎒 <b>Pick an item</b>\nChoose a category:"), rows)


@action("adir")
async def item_pick_rarity(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    cat = (arg or "").strip()
    if cat not in CATS:
        return Out(alert="?")
    fa = ctx.lang == "fa"
    present = [r for r in RARITIES if _items(cat, r)]
    btns = [(f"{RARITY_ICON[r]} {RARITY_FA[r] if fa else r} ({fnum(len(_items(cat, r)), ctx.lang)})", "adil", f"{cat}:{r}:0", False, "none") for r in present]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    rows.append([(T(ctx, f"📋 همه ({fnum(len(_items(cat, 'x')), ctx.lang)})", f"📋 All ({len(_items(cat, 'x'))})"), "adil", f"{cat}:x:0", False, "none")])
    rows.append(_back(ctx, "adi", ""))
    return Out(head(ctx, "ttl_adm") + f"{CAT_ICON.get(cat, '')} <b>{CAT_FA[cat] if fa else cat}</b>\n" + T(ctx, "رده را انتخاب کن:", "Choose a rarity:"), rows)


@action("adil")
async def item_pick_list(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    cat, rar, p = ((arg or "").split(":") + ["", "x", "0"])[:3]
    if cat not in CATS or (rar != "x" and rar not in RARITIES):
        return Out(alert="?")
    ids = _items(cat, rar)
    page = max(0, min(_page(p), _pages(len(ids)) - 1))
    from data_races import RACES
    race_tag = lambda v: (" · " + RACES[v["race"]]["name_fa" if ctx.lang == "fa" else "name_en"]) if v.get("race") in RACES else ""  # noqa: E731
    rows = [[(f"{RARITY_ICON[ALL[i]['rarity']]} {_nm(ALL[i], ctx)}{race_tag(ALL[i])}"[:60], "adip", i, False, "none")] for i in ids[page * PER:(page + 1) * PER]]
    pg = _pager(page, _pages(len(ids)), "adil", f"{cat}:{rar}:")
    if pg:
        rows.append(pg)
    rows.append(_back(ctx, "adir", cat))
    return Out(head(ctx, "ttl_adm") + T(ctx, f"🎒 {CAT_FA[cat]} | صفحه {fnum(page + 1, ctx.lang)}/{fnum(_pages(len(ids)), ctx.lang)}\nیک آیتم را بزن تا به پلیر بدهی.",
                                         f"🎒 {cat} | page {page + 1}/{_pages(len(ids))}\nTap an item to give it to a player."), rows)


@action("adip")
async def item_pick_chosen(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    iid = (arg or "").strip()
    it = ALL.get(iid)
    if not it:
        return Out(alert="?")
    await _pending_set(ctx.uid, "give_pick", target=iid, chat_id=ctx.chat_id)
    need, fa_t, en_t, _b = ASK["give_pick"]
    return Out(head(ctx, "ttl_adm") + f"{RARITY_ICON[it['rarity']]} <b>{esc(_nm(it, ctx))}</b>\n" + esc(T(ctx, fa_t, en_t)) + "\n\n"
               + esc(T(ctx, "برای لغو: «لغو» بفرست.", "To cancel: send «cancel».")), [_back(ctx, "adi", "")])


# ---- summon picker -------------------------------------------------------------------------------------------------
def _chars(rar: str):
    return [c for c in CHARS if c["rarity"] == rar]


@action("adz")
async def summon_pick_rarity(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    fa = ctx.lang == "fa"
    btns = [(f"{RARITY_ICON[r]} {RARITY_FA[r] if fa else r} ({fnum(len(_chars(r)), ctx.lang)})", "adzl", f"{r}:0", False, "none") for r in RARITIES if _chars(r)]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    rows.append(_back(ctx, "ade", ""))
    return Out(head(ctx, "ttl_adm") + T(ctx, "🎴 <b>دادن احضار</b>\nرده را انتخاب کن:", "🎴 <b>Give a summon</b>\nChoose a rarity:"), rows)


@action("adzl")
async def summon_pick_list(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    rar, _, p = (arg or "").partition(":")
    if rar not in RARITIES:
        return Out(alert="?")
    cs = _chars(rar)
    page = max(0, min(_page(p), _pages(len(cs)) - 1))
    rows = [[(f"{RARITY_ICON[rar]} {_nm(c, ctx)}", "adzp", c["_id"], False, "none")] for c in cs[page * PER:(page + 1) * PER]]
    pg = _pager(page, _pages(len(cs)), "adzl", f"{rar}:")
    if pg:
        rows.append(pg)
    rows.append(_back(ctx, "adz", ""))
    return Out(head(ctx, "ttl_adm") + T(ctx, f"🎴 {RARITY_FA[rar]} | صفحه {fnum(page + 1, ctx.lang)}/{fnum(_pages(len(cs)), ctx.lang)}\nیک احضار را بزن.",
                                         f"🎴 {rar} | page {page + 1}/{_pages(len(cs))}\nTap a summon."), rows)


@action("adzp")
async def summon_pick_chosen(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    c = CHAR_BY_ID.get((arg or "").strip())
    if not c:
        return Out(alert="?")
    await _pending_set(ctx.uid, "give_summon", target=c["_id"], chat_id=ctx.chat_id)
    need, fa_t, en_t, _b = ASK["give_summon"]
    return Out(head(ctx, "ttl_adm") + f"{RARITY_ICON[c['rarity']]} <b>{esc(_nm(c, ctx))}</b>\n" + esc(T(ctx, fa_t, en_t)) + "\n\n"
               + esc(T(ctx, "برای لغو: «لغو» بفرست.", "To cancel: send «cancel».")), [_back(ctx, "adz", "")])


# ---- typed step (called by handlers_adminpanel._run_input for names it does not know) ---------------------------------
async def run_input(ctx, name, pend, raw):
    """Returns an Out, or None when `name` is not one of ours."""
    if name not in ("give_pick", "give_summon"):
        return None
    tid, rest, u = await _target_or_none(raw, 0, check_level=False, reply_id=_reply_id(ctx), single_arg=True)
    if u is None:
        return Out(T(ctx, "کاربر پیدا نشد.", "User not found."), [_back(ctx, "adu", "")])
    if u == "protected":
        return Out(T(ctx, "اجازه نداری.", "Not allowed."), [_back(ctx)])
    n = parse_amount(rest.split()[0], 1, 999) if rest.split() else 1
    if n is None:
        raise ValueError(raw)
    what = pend.get("target")
    if name == "give_pick":
        if what not in ALL:
            raise ValueError(raw)
        from service_raceweapon import ADMIN_GIVE_MSG, admin_give
        res = await admin_give(tid, what, n)
        if res not in ("ok", "equipped"):
            return Out(T(ctx, *ADMIN_GIVE_MSG[res]), [_back(ctx, "adi", "")])
        await alog(ctx.uid, "give_item", tid, None, {"item": what, "n": n}, "panel picker")
    else:
        if what not in CHAR_BY_ID:
            raise ValueError(raw)
        await col("gacha").update_one({"user_id": tid}, {"$inc": {f"chars.{what}": n}, "$setOnInsert": {"since_rare": 0, "since_leg": 0, "total": 0}}, upsert=True)
        await alog(ctx.uid, "give_summon", tid, None, {"char": what, "n": n}, "panel picker")
    return await user_card(ctx, tid)

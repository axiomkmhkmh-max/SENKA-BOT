"""Zanpakuto progression: bond, Mastery training, Shikai / Bankai (and each race's equivalent) release.
State lives in characters.zanpakuto = {blade_id, bond, mastery, shikai, bankai}; combat reads it in service_combat.build_player.
Mastery grows by real use: every PvE win while released (+1) and the daily Training Grounds (energy cost, daily cap)."""
import time

from data_items import ALL, iname
from data_misc import FORMS
from data_world import day_id
from database import bump_counter, col, counter_get, game_settings, try_cooldown
from i18n import fnum
from service_player import get_char, spend_energy
from ui import SEP, Out, action, nav

T = {  # key -> (fa, en)
    "title": ("\u26a1 \u0632\u0627\u0646\u067e\u0627\u06a9\u062a\u0648", "\u26a1 Zanpakut\u014d"),
    "body": ("\u062a\u06cc\u063a\u0647: <b>{blade}</b>\n\U0001f517 \u067e\u06cc\u0648\u0646\u062f: <b>{bond}</b>\n\U0001f4aa \u0645\u0647\u0627\u0631\u062a (Mastery): <b>{mastery}</b>/{cap}\n\n{f1}: {s1}\n{f2}: {s2}\n\n\U0001f3cb\ufe0f \u062a\u0645\u0631\u06cc\u0646 \u0627\u0645\u0631\u0648\u0632: {left}/{daily} (\u0647\u0631 \u0628\u0627\u0631 {gain} \u0645\u0647\u0627\u0631\u062a\u060c {cost} \u0627\u0646\u0631\u0698\u06cc)\n\u0647\u0631 \u067e\u06cc\u0631\u0648\u0632\u06cc PvE \u0628\u0627 \u0634\u06a9\u0644 \u0622\u0632\u0627\u062f\u0634\u062f\u0647 \u06f1 \u0645\u0647\u0627\u0631\u062a \u0645\u06cc\u200c\u062f\u0647\u062f.",
             "Blade: <b>{blade}</b>\n\U0001f517 Bond: <b>{bond}</b>\n\U0001f4aa Mastery: <b>{mastery}</b>/{cap}\n\n{f1}: {s1}\n{f2}: {s2}\n\n\U0001f3cb\ufe0f Training today: {left}/{daily} ({gain} Mastery each, {cost} energy)\nEvery PvE win while released gives +1 Mastery."),
    "on": ("\u2705 \u0641\u0639\u0627\u0644", "\u2705 unlocked"),
    "off": ("\U0001f512 \u0642\u0641\u0644 ({need})", "\U0001f512 locked ({need})"),
    "need_s": ("\u0633\u0637\u062d {lv} \u0648 \u067e\u06cc\u0648\u0646\u062f {bond}", "Lv.{lv}, bond {bond}"),
    "need_b": ("\u0633\u0637\u062d {lv}\u060c \u0645\u0631\u062d\u0644\u0647\u200c\u06cc \u0627\u0648\u0644 \u0648 \u0645\u0647\u0627\u0631\u062a {m}", "Lv.{lv}, first form and Mastery {m}"),
    "b_train": ("\U0001f3cb\ufe0f \u062a\u0645\u0631\u06cc\u0646", "\U0001f3cb\ufe0f Train"),
    "b_rel1": ("\U0001f525 \u0622\u0632\u0627\u062f\u0633\u0627\u0632\u06cc {f}", "\U0001f525 Unlock {f}"),
    "b_rel2": ("\U0001f4a5 \u0622\u0632\u0627\u062f\u0633\u0627\u0632\u06cc {f}", "\U0001f4a5 Unlock {f}"),
    "locked": ("\u0634\u0631\u0627\u06cc\u0637 \u0647\u0646\u0648\u0632 \u06a9\u0627\u0645\u0644 \u0646\u06cc\u0633\u062a.", "Requirements not met yet."),
    "done1": ("\U0001f525 {f} \u0622\u0632\u0627\u062f \u0634\u062f! \u0642\u062f\u0631\u062a \u0646\u0628\u0631\u062f\u062a \u0628\u0627\u0644\u0627 \u0631\u0641\u062a.", "\U0001f525 {f} unlocked! Your battle power rose."),
    "done2": ("\U0001f4a5 {f} \u0622\u0632\u0627\u062f \u0634\u062f! \u0627\u06cc\u0646 \u0642\u062f\u0631\u062a \u0645\u0647\u0627\u0631\u062a \u0645\u06cc\u200c\u06af\u06cc\u0631\u062f.", "\U0001f4a5 {f} unlocked! Mastery now amplifies it."),
    "wait": ("\u06a9\u0645\u06cc \u0635\u0628\u0631 \u06a9\u0646.", "Slow down a moment."),
    "cap": ("\u0633\u0642\u0641 \u062a\u0645\u0631\u06cc\u0646 \u0627\u0645\u0631\u0648\u0632 \u067e\u0631 \u0634\u062f\u0647.", "Today's training cap is reached."),
    "energy": ("\u0627\u0646\u0631\u0698\u06cc \u06a9\u0627\u0641\u06cc \u0646\u06cc\u0633\u062a.", "Not enough energy."),
    "maxed": ("\u0645\u0647\u0627\u0631\u062a \u0628\u0647 \u062d\u062f\u0627\u06a9\u062b\u0631 \u0631\u0633\u06cc\u062f\u0647.", "Mastery is maxed."),
    "trained": ("\U0001f3cb\ufe0f +{g} \u0645\u0647\u0627\u0631\u062a!", "\U0001f3cb\ufe0f +{g} Mastery!"),
    "noreg": ("\u0627\u0628\u062a\u062f\u0627 \u062b\u0628\u062a\u200c\u0646\u0627\u0645 \u06a9\u0646.", "Register first."),
}


def _t(lang, key, **kw):
    fa, en = T[key]
    s = fa if lang == "fa" else en
    return s.format(**kw) if kw else s


async def _state(uid):
    ch = await get_char(uid)
    if not ch:
        return None, None
    wid = ch.get("weapon_id") or ""
    z = dict(ch.get("zanpakuto") or {})
    if wid and not z.get("blade_id"):
        await col("characters").update_one({"user_id": uid, "zanpakuto.blade_id": {"$exists": False}}, {"$set": {"zanpakuto.blade_id": wid}})
        z["blade_id"] = wid
    z["bond"] = max(int((ch.get("bond") or {}).get(wid, 0)), int(z.get("bond", 0)))
    z["mastery"] = int(z.get("mastery", 0))
    return ch, z


@action("znp")
async def zanpakuto_panel(ctx, arg):
    ch, z = await _state(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    gs = await game_settings()
    f1, f2 = (FORMS.get(ch["race"]) or FORMS["human"])
    f1, f2 = f1[0 if ctx.lang == "fa" else 1], f2[0 if ctx.lang == "fa" else 1]
    lv, bond = int(ch["level"]), z["bond"]
    n1 = (int(gs["znp_shikai_level"]), int(gs["znp_shikai_bond"]))
    n2 = (int(gs["znp_bankai_level"]), int(gs["znp_bankai_mastery"]))
    s1 = _t(ctx.lang, "on") if z.get("shikai") else _t(ctx.lang, "off", need=_t(ctx.lang, "need_s", lv=n1[0], bond=n1[1]))
    s2 = _t(ctx.lang, "on") if z.get("bankai") else _t(ctx.lang, "off", need=_t(ctx.lang, "need_b", lv=n2[0], m=n2[1]))
    left = max(0, int(gs["znp_train_daily"]) - await counter_get(f"znp:train:{ctx.uid}:{day_id()}"))
    body = _t(ctx.lang, "body", blade=iname(z.get("blade_id") or "", ctx.lang) or "-", bond=fnum(bond, ctx.lang),
              mastery=fnum(z["mastery"], ctx.lang), cap=fnum(int(gs["znp_mastery_cap"]), ctx.lang), f1=f1, s1=s1, f2=f2, s2=s2,
              left=left, daily=int(gs["znp_train_daily"]), gain=int(gs["znp_train_gain"]), cost=int(gs["znp_train_energy"]))
    rows = [[(_t(ctx.lang, "b_train"), "ztrn", "")]]
    if not z.get("shikai") and lv >= n1[0] and bond >= n1[1]:
        rows.append([(_t(ctx.lang, "b_rel1", f=f1), "zrel", "1")])
    if z.get("shikai") and not z.get("bankai") and lv >= n2[0] and z["mastery"] >= n2[1]:
        rows.append([(_t(ctx.lang, "b_rel2", f=f2), "zrel", "2")])
    rows.append(nav(ctx))
    return Out(f"\u2694\ufe0f <b>\U0001d5b2\U0001d5a4\U0001d5ad\U0001d5aa\U0001d5a0</b> | <b>{_t(ctx.lang, 'title')}</b>\n{SEP}\n" + body, rows)


@action("ztrn")
async def zanpakuto_train(ctx, arg):
    ch, z = await _state(ctx.uid)
    if not ch:
        return Out(alert=_t(ctx.lang, "noreg"))
    gs = await game_settings()
    cap = int(gs["znp_mastery_cap"])
    if z["mastery"] >= cap:
        return Out(alert=_t(ctx.lang, "maxed"))
    if await try_cooldown(f"znp:train:cd:{ctx.uid}", 3):
        return Out(alert=_t(ctx.lang, "wait"))
    daily = int(gs["znp_train_daily"])
    if await counter_get(f"znp:train:{ctx.uid}:{day_id()}") >= daily:
        return Out(alert=_t(ctx.lang, "cap"))
    ok, _cur, _nxt = await spend_energy(ctx.uid, int(gs["znp_train_energy"]))
    if not ok:
        return Out(alert=_t(ctx.lang, "energy"))
    if not await bump_counter(f"znp:train:{ctx.uid}:{day_id()}", 1, daily):
        from service_extras import add_energy
        await add_energy(ctx.uid, int(gs["znp_train_energy"]))
        return Out(alert=_t(ctx.lang, "cap"))
    gain = int(gs["znp_train_gain"])
    await col("characters").update_one({"user_id": ctx.uid, "zanpakuto.mastery": {"$lt": cap}},
                                       {"$inc": {"zanpakuto.mastery": gain}})
    out = await zanpakuto_panel(ctx, "")
    out.text = _t(ctx.lang, "trained", g=gain) + "\n" + out.text
    return out


@action("zrel")
async def zanpakuto_release(ctx, arg):
    ch, z = await _state(ctx.uid)
    if not ch:
        return Out(alert=_t(ctx.lang, "noreg"))
    gs = await game_settings()
    lv, f = int(ch["level"]), (FORMS.get(ch["race"]) or FORMS["human"])
    if arg == "1":
        if z.get("shikai") or lv < int(gs["znp_shikai_level"]) or z["bond"] < int(gs["znp_shikai_bond"]):
            return Out(alert=_t(ctx.lang, "locked"))
        r = await col("characters").update_one({"user_id": ctx.uid, "zanpakuto.shikai": {"$ne": True}},
                                               {"$set": {"zanpakuto.shikai": True, "zanpakuto.shikai_at": int(time.time())}})
        key, name = "done1", f[0]
    elif arg == "2":
        if (not z.get("shikai")) or z.get("bankai") or lv < int(gs["znp_bankai_level"]) or z["mastery"] < int(gs["znp_bankai_mastery"]):
            return Out(alert=_t(ctx.lang, "locked"))
        r = await col("characters").update_one({"user_id": ctx.uid, "zanpakuto.shikai": True, "zanpakuto.bankai": {"$ne": True}},
                                               {"$set": {"zanpakuto.bankai": True, "zanpakuto.bankai_at": int(time.time())}})
        key, name = "done2", f[1]
    else:
        return Out(alert=_t(ctx.lang, "locked"))
    if not r.modified_count:  # double tap
        return await zanpakuto_panel(ctx, "")
    out = await zanpakuto_panel(ctx, "")
    out.text = _t(ctx.lang, key, f=name[0 if ctx.lang == "fa" else 1]) + "\n" + out.text
    return out

"""Player-facing race evolution, faction enlistment and Kidō panels (Story mode is retired; its saved data is kept)."""
from ui import Out, action, head, nav
from database import col
from i18n import fnum
from service_bleach_systems import (RACE_PATHS, KIDO, FACTIONS, race_state, evolve,  # noqa: F401
    kido_state, learn_kido, cast_kido, faction_state, join_faction)

@action("blhub")
async def bleach_hub(ctx, arg):
    if not await race_state(ctx.uid):
        return Out(ctx.t("not_registered"))
    rows = [
        [(ctx.t("m_znp"), "znp", "")],
        [(ctx.t("m_rpath"), "rpath", "")],
        [(ctx.t("m_kido"), "kidop", "")],
        [(ctx.t("m_skm"), "skm", "")],
        [(ctx.t("m_faction"), "fctp", "")],
        nav(ctx),
    ]
    return Out(head(ctx, "ttl_bleach_hub") + ctx.t("bleach_hub_body"), rows)

@action("rpath")
async def race_panel(ctx, arg):
    """The race's one evolution path (data_evolution): every stage, its level gate and what it grants."""
    from data_crafting import evo_stage
    from data_evolution import EVO_PATHS
    from data_races import LEVEL_GATES, RACES
    from service_player import get_char
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    L = ctx.lang
    cur = evo_stage(ch)
    race = RACES[ch["race"]]["name_fa" if L == "fa" else "name_en"]
    lines = [ctx.t("evo_path_head", race=race)]
    from data_race_tech import RACE_TECH, tech_name
    techs = RACE_TECH.get(ch["race"]) or {}
    for i, (title, _add, desc) in enumerate(EVO_PATHS[ch["race"]]):
        mark = "✅" if i < cur else "▶️" if i == cur else "🔒"
        lines.append(ctx.t("evo_path_line", mark=mark, title=title[0 if L == "fa" else 1], lvl=fnum(LEVEL_GATES[i], L),
                           desc=desc[0 if L == "fa" else 1]))
    if techs:  # every race technique is open from level 1; evolution only adds power
        names = ("، " if L == "fa" else ", ").join(tech_name(t, L) for t in techs.values())
        lines.append(("\n✨ تکنیک‌های نژادت (همه از لِوِل ۱ باز): " if L == "fa" else "\n✨ Your race techniques (all open from level 1): ") + names)
    rows = [[(ctx.t("b_evo_open"), "evo", "")]] if cur < len(EVO_PATHS[ch["race"]]) - 1 else []
    rows.append(nav(ctx))
    return Out(head(ctx, "ttl_race_path") + "\n".join(lines), rows)


@action("revo")
async def race_evolve_action(ctx, arg):
    """Old button: evolution is one system now (the trial), so it opens the evolution panel."""
    from handlers_world import evolution_panel
    return await evolution_panel(ctx, arg)


@action("kidop")
async def kido_panel(ctx,arg):
    s=await kido_state(ctx.uid)
    if not s:return Out(ctx.t("not_registered"))
    lines=[ctx.t("kido_body",reiatsu=fnum(s["reiatsu"],ctx.lang)),""]
    if not s.get("eligible"):
        lines.append(ctx.t("kido_race"))
    rows=[]
    for key,data in s["available"]:
        learned=key in s["learned"]
        name=data["fa"] if ctx.lang=="fa" else data["name"]
        lines.append(("✅ " if learned else "▫️ ")+f"{name} · {data['type']} · {data['cost']} RE")
        if not learned:rows.append([(ctx.t("b_kido_learn",name=name),"kidol",key)])
    rows.append([(("🃏 کارت‌های کیدو" if ctx.lang=="fa" else "🃏 Kidō cards"),"kidoc",""),
                 (("📜 رساله‌ها" if ctx.lang=="fa" else "📜 Treatises"),"kidot","")])
    rows.append(nav(ctx))
    return Out(head(ctx,"ttl_kido")+"\n".join(lines),rows)

@action("kidoc")
async def kido_cards(ctx,arg):
    """Kidō cards: one per spell. A card opens when the spell is learned; locked cards show only the level needed."""
    from service_bleach_systems import KIDO
    s=await kido_state(ctx.uid)
    if not s:return Out(ctx.t("not_registered"))
    L=ctx.lang
    learned=set(s["learned"])
    # starting spells (given at registration / legacy defaults) are known in combat too, so their cards are open
    doc=await col("characters").find_one({"user_id":ctx.uid},{"kido":1,"race":1})
    if (doc or {}).get("race") in ("shinigami","visored"):  # only these races use Kidō in combat
        for n in ((doc or {}).get("kido") or {}).get("had",[]) or []:
            learned.add(f"hado{int(n)}")
        for n in ((doc or {}).get("kido") or {}).get("bak",[]) or []:
            learned.add(f"bakudo{int(n)}")
    total=len(KIDO)
    got=sum(1 for k in KIDO if k in learned)
    head_line=(f"🃏 کارت‌های کیدو: {got}/{total}" if L=="fa" else f"🃏 Kidō cards: {got}/{total}")
    from data_crafting import kido_collection_bonus
    cb=kido_collection_bonus(doc or {})
    lines=[head_line,(f"🏆 جایزه‌ی کالکشن: +{cb['dmg']*100:.1f}٪ آسیب · +{cb['def']*100:.1f}٪ دفاع · +{cb['crit']*100:.2f}٪ شانس بحرانی" if L=="fa"
          else f"🏆 Collection bonus: +{cb['dmg']*100:.1f}% damage · +{cb['def']*100:.1f}% defence · +{cb['crit']*100:.2f}% crit"),""]
    for key,d in KIDO.items():
        if key in learned:
            name=d["name"]
            desc=d.get("fa","") if L=="fa" else ""
            lines.append(f"✅ <b>{name}</b> · {d['type']} · Lv.{d['level']} · {d['cost']}{'' if d['type'] == 'Kaidō' else '%'} RE")
            if desc: lines.append(f"<i>{desc}</i>")
        else:
            lines.append(("🔒 ??? · " if L=="fa" else "🔒 ??? · ")+f"{d['type']} · Lv.{d['level']}")
    rows=[]
    # Kidō cards the player owns (they land in the bag) are shown here, to learn straight from the Kidō panel
    from data_items import ALL, iname
    from fmt import effect_text
    from service_economy import inv_get
    inv=await inv_get(ctx.uid)
    # numbered Hadō / Bakudō cards only: the Treatise books (رساله) have their own panel
    owned=[(i,q) for i,q in inv["items"].items() if q>0 and ((ALL.get(i) or {}).get("effect") or {}).get("type")=="kido"]
    known=((doc or {}).get("kido") or {})
    extras=0
    if owned:
        lines+=["",("🎴 <b>کارت‌های تو (در کوله)</b>" if L=="fa" else "🎴 <b>Your cards (in the bag)</b>")]
        owned.sort(key=lambda x:(x[0] and (ALL[x[0]]["effect"]["branch"],ALL[x[0]]["effect"]["num"])))
        for i,q in owned[:12]:
            e=ALL[i]["effect"]
            dup=e["num"] in (known.get(e["branch"]) or [])
            lines.append(f"• {iname(i,L)} ×{fnum(q,L)}"+((" ♻️" if dup else ""))+f"\n  <i>{effect_text(ctx,ALL[i])}</i>")
            rows.append([((f"📖 یادگیری: {iname(i,L)}" if L=="fa" else f"📖 Learn: {iname(i,L)}")[:60],"kidou",i)])
        if len(owned)>12:
            lines.append(f"… +{fnum(len(owned)-12,L)}")
        for i,q in owned:
            e=ALL[i]["effect"]
            extras+=q if e["num"] in (known.get(e["branch"]) or []) else q-1
    if extras>0:
        rows.append([((f"♻️ تبدیل کارت‌های اضافی به تجربه ({fnum(extras,L)})" if L=="fa" else f"♻️ Convert extra cards to XP ({fnum(extras,L)})"),"kidoq","")])
    rows.append(nav(ctx,("kidop","")))
    return Out(head(ctx,"ttl_kido")+"\n".join(lines),rows)


@action("kidoq")
async def kido_convert_extras(ctx,arg):
    """Turn every extra Kidō card (a spell already known, or a second copy of an unknown one) into XP."""
    from data_items import ALL
    from data_race_rules import race_allows
    from service_economy import inv_get, inv_remove, add_xp, DUP_CARD_XP_BASE, DUP_CARD_XP_PER_NUM
    L=ctx.lang
    doc=await col("characters").find_one({"user_id":ctx.uid},{"kido":1,"race":1})
    if not doc or not race_allows(doc.get("race"),"kd"):
        out=await kido_cards(ctx,"")
        out.alert=("📜 فقط شینیگامی و ویزورد کیدو دارن." if L=="fa" else "📜 Only Shinigami and Visored use Kidō.")
        return out
    known=doc.get("kido") or {}
    inv=await inv_get(ctx.uid)
    n_cards,total=0,0
    for i,q in list(inv["items"].items()):
        e=(ALL.get(i) or {}).get("effect") or {}
        if q<=0 or e.get("type")!="kido":
            continue
        extra=q if e["num"] in (known.get(e["branch"]) or []) else q-1
        if extra>0 and await inv_remove(ctx.uid,i,extra):
            n_cards+=extra
            total+=(DUP_CARD_XP_BASE+DUP_CARD_XP_PER_NUM*int(e["num"]))*extra
    if total>0:
        await add_xp(ctx.uid,total,"kido_dup",apply_rate=False)
    out=await kido_cards(ctx,"")
    out.alert=((f"♻️ {fnum(n_cards,L)} کارت اضافی تبدیل شد؛ +{fnum(total,L)} تجربه." if n_cards else "کارت اضافی‌ای نداری.") if L=="fa"
               else (f"♻️ {fnum(n_cards,L)} extra card(s) converted: +{fnum(total,L)} XP." if n_cards else "No extra cards."))
    return out


@action("kidot")
async def kido_treatises(ctx,arg):
    """The Kidō Treatises (رساله‌ی کیدو): books with their own panel, each with what it really does."""
    from data_items import ALL, iname
    from fmt import effect_text
    from service_economy import inv_get
    L=ctx.lang
    inv=await inv_get(ctx.uid)
    owned=sorted((i,q) for i,q in inv["items"].items() if q>0 and (ALL.get(i) or {}).get("category")=="book" and str((ALL.get(i) or {}).get("name_fa","")).startswith("رساله"))
    lines=[("📜 <b>رساله‌های کیدو</b> — کتاب‌هایی که با خوندنشون پاداش می‌گیری." if L=="fa" else "📜 <b>Kidō Treatises</b> — books that reward you when read."),""]
    rows=[]
    if not owned:
        lines.append("هیچ رساله‌ای تو کوله‌ات نیست." if L=="fa" else "You have no Treatise in the bag.")
    for i,q in owned[:15]:
        lines.append(f"• {iname(i,L)} ×{fnum(q,L)}\n  <i>{effect_text(ctx,ALL[i])}</i>")
        rows.append([((f"📖 خوندن: {iname(i,L)}" if L=="fa" else f"📖 Read: {iname(i,L)}")[:60],"kidob",i)])
    if len(owned)>15:
        lines.append(f"… +{fnum(len(owned)-15,L)}")
    rows.append(nav(ctx,("kidop","")))
    return Out(head(ctx,"ttl_kido")+"\n".join(lines),rows)


@action("kidob")
async def kido_read_treatise(ctx,arg):
    from service_economy import use_item
    r,extra=await use_item(ctx.uid,arg)
    out=await kido_treatises(ctx,"")
    L=ctx.lang
    if r=="ok":
        out.alert=ctx.t("us_ok",n=fnum(extra if isinstance(extra,int) else 0,L))
    elif r=="race":
        out.alert=("📜 فقط شینیگامی و ویزورد می‌تونن کیدو یاد بگیرن؛ مصرف نشد." if L=="fa" else "📜 Only Shinigami and Visored can learn Kidō; not used.")
    else:
        out.alert=ctx.t("us_"+r,n=extra or 0)
    return out


@action("kidou")
async def kido_use_card(ctx,arg):
    """Learn a Kidō card from the bag inside the Kidō panel, then show the cards again."""
    from service_economy import use_item
    r,extra=await use_item(ctx.uid,arg)
    out=await kido_cards(ctx,"")
    if r=="ok":
        out.alert=(f"✅ کیدوی شماره‌ی {fnum(extra,ctx.lang)} یاد گرفته شد." if ctx.lang=="fa" else f"✅ Kidō #{extra} learned.")
    elif r=="race":
        out.alert=("📜 فقط شینیگامی و ویزورد کیدو یاد می‌گیرن." if ctx.lang=="fa" else "📜 Only Shinigami and Visored learn Kidō.")
    else:
        out.alert=ctx.t("us_"+r,n=extra or 0)
    return out

@action("kidol")
async def kido_learn_action(ctx,arg):
    status,s=await learn_kido(ctx.uid,arg)
    if status=="ok":return Out(ctx.t("kido_learned"),[nav(ctx,("kidop",""))])
    if status=="known":return Out(alert=ctx.t("kido_known"))
    if status=="race":return Out(alert=ctx.t("kido_race"))
    return Out(alert=ctx.t("kido_unavailable"))

@action("kidox")  # was registered as "kidoc" too, which replaced the Kidō cards panel: the cards button only showed an alert
async def kido_cast_action(ctx,arg):
    status,data=await cast_kido(ctx.uid,arg)
    # Spells are cast by the battle engine; cast_kido only reports "combat_only"/"locked"/"race".
    return Out(alert=ctx.t("kido_unavailable"))

@action("fctp")
async def faction_panel(ctx,arg):
    s=await faction_state(ctx.uid)
    if not s:return Out(ctx.t("not_registered"))
    if s["faction"]:
        f=FACTIONS[s["faction"]]; name=f["fa"] if ctx.lang=="fa" else f["en"]
        return Out(head(ctx,"ttl_faction")+ctx.t("faction_member",name=name,rank=s["rank"]),[nav(ctx)])
    rows=[]
    for key,f in FACTIONS.items():
        if s["race"] in f["races"]:rows.append([(f["fa"] if ctx.lang=="fa" else f["en"],"fctj",key)])
    rows.append(nav(ctx))
    return Out(head(ctx,"ttl_faction")+ctx.t("faction_intro"),rows)

@action("fctj")
async def faction_join_action(ctx,arg):
    status,s=await join_faction(ctx.uid,arg)
    if status!="ok":return Out(alert=ctx.t("faction_race"))
    f=FACTIONS[arg]; name=f["fa"] if ctx.lang=="fa" else f["en"]
    return Out(ctx.t("faction_joined",name=name),[nav(ctx,("fctp",""))])

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
        text = desc[0 if L == "fa" else 1]
        opened = [tech_name(t, L) for t in techs.values() if t["unlock"] == i]
        if opened:
            text += (" · تکنیک: " + "، ".join(opened)) if L == "fa" else (" · technique: " + ", ".join(opened))
        lines.append(ctx.t("evo_path_line", mark=mark, title=title[0 if L == "fa" else 1], lvl=fnum(LEVEL_GATES[i], L), desc=text))
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
    rows.append([(("🃏 کارت‌های کیدو" if ctx.lang=="fa" else "🃏 Kidō cards"),"kidoc","")])
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
    lines=[head_line,""]
    for key,d in KIDO.items():
        if key in learned:
            name=d["name"]
            desc=d.get("fa","") if L=="fa" else ""
            lines.append(f"✅ <b>{name}</b> · {d['type']} · Lv.{d['level']} · {d['cost']} RE")
            if desc: lines.append(f"<i>{desc}</i>")
        else:
            lines.append(("🔒 ??? · " if L=="fa" else "🔒 ??? · ")+f"{d['type']} · Lv.{d['level']}")
    rows=[nav(ctx,("kidop",""))]
    return Out(head(ctx,"ttl_kido")+"\n".join(lines),rows)

@action("kidol")
async def kido_learn_action(ctx,arg):
    status,s=await learn_kido(ctx.uid,arg)
    if status=="ok":return Out(ctx.t("kido_learned"),[nav(ctx,("kidop",""))])
    if status=="known":return Out(alert=ctx.t("kido_known"))
    if status=="race":return Out(alert=ctx.t("kido_race"))
    return Out(alert=ctx.t("kido_unavailable"))

@action("kidoc")
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

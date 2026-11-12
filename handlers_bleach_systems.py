"""Player-facing race evolution, story arcs, faction enlistment and Kidō panels."""
from ui import Out, action, head, nav
from i18n import fnum
from service_bleach_systems import (RACE_PATHS, STORY_ARCS, KIDO, FACTIONS, race_state, evolve,
    story_state, start_story, advance_story, kido_state, learn_kido, cast_kido, faction_state, join_faction)

@action("blhub")
async def bleach_hub(ctx, arg):
    if not await race_state(ctx.uid):
        return Out(ctx.t("not_registered"))
    rows = [
        [(ctx.t("m_znp"), "znp", "")],
        [(ctx.t("m_rpath"), "rpath", "")],
        [(ctx.t("m_story"), "storyp", "")],
        [(ctx.t("m_kido"), "kidop", "")],
        [(ctx.t("m_faction"), "fctp", "")],
        nav(ctx),
    ]
    return Out(head(ctx, "ttl_bleach_hub") + ctx.t("bleach_hub_body"), rows)

@action("rpath")
async def race_panel(ctx,arg):
    s=await race_state(ctx.uid)
    if not s:return Out(ctx.t("not_registered"))
    path=RACE_PATHS.get(s["race"],RACE_PATHS["human"])
    lines=[ctx.t("race_path_body", stage=s["current"][3], level=fnum(s["level"],ctx.lang), wins=fnum(s["progress_count"],ctx.lang)),""]
    for i,p in enumerate(path):
        mark="✅" if i<s["stage"] else "▶️" if i==s["stage"] else "🔒"
        lines.append(f"{mark} {p[3]} — Lv.{p[1]} / {p[2]} wins")
    rows=[[ (ctx.t("b_race_evolve"),"revo","") ]] if s["next"] else []
    rows.append(nav(ctx))
    return Out(head(ctx,"ttl_race_path")+"\n".join(lines),rows)

@action("revo")
async def race_evolve_action(ctx,arg):
    status,data=await evolve(ctx.uid)
    if status=="requirements":return Out(ctx.t("race_path_need",level=fnum(data["level"],ctx.lang),wins=fnum(data["wins"],ctx.lang)),[[ (ctx.t("b_back"),"rpath","") ],nav(ctx)])
    if status=="max":return Out(ctx.t("race_path_max"),[nav(ctx, ("rpath",""))])
    if status=="release_required":return Out(ctx.t("race_path_release",release=data["release"]),[nav(ctx,("znp",""))])
    if status!="ok":return Out(alert=ctx.t("error"))
    return Out(ctx.t("race_path_up",stage=data["current"][3]),[nav(ctx,("rpath",""))])

@action("storyp")
async def story_panel(ctx,arg):
    s=await story_state(ctx.uid)
    if not s:return Out(ctx.t("not_registered"))
    rows=[]; lines=[ctx.t("story_intro"),""]
    if s["active"]:
        arc=s["active"]; lines.append(ctx.t("story_active",arc=arc["fa"] if ctx.lang=="fa" else arc["en"],step=s["doc"].get("step",0)+1))
        rows.append([(ctx.t("b_story_advance"),"stadv","")])
    for a in s["available"][:8]:
        label=a["fa"] if ctx.lang=="fa" else a["en"]
        rows.append([(label,"ststart",a["id"])])
    completed=s["doc"].get("completed",[])
    lines.append(ctx.t("story_completed",count=len(completed)))
    rows.append(nav(ctx))
    return Out(head(ctx,"ttl_story")+"\n".join(lines),rows)

@action("ststart")
async def story_start_action(ctx,arg):
    status,s=await start_story(ctx.uid,arg)
    if status!="ok":return Out(alert=ctx.t("story_locked"))
    arc=s["active"]; label=arc["fa"] if ctx.lang=="fa" else arc["en"]
    return Out(ctx.t("story_started",arc=label),[nav(ctx,("storyp",""))])

@action("stadv")
async def story_advance_action(ctx,arg):
    status,s=await advance_story(ctx.uid)
    if status=="none":return Out(alert=ctx.t("story_none"))
    if status=="need_win":return Out(ctx.t("story_need_win"),[nav(ctx,("storyp",""))])
    if status=="complete":return Out(ctx.t("story_complete"),[nav(ctx,("storyp",""))])
    if status=="step":return Out(ctx.t("story_step",step=s["doc"].get("step",0)+1),[nav(ctx,("storyp",""))])
    return Out(alert=ctx.t("error"))

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
    rows.append(nav(ctx))
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

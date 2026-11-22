"""Skins (اسکین‌ها): the collection page (`skn`), one skin (`sks`), equip (`ske`) and take off (`sku`).
Rules live in data_skins (pure) and service_skins (DB). This module only draws."""
from data_skins import RARITIES, RARITY_FA, RARITY_ICON, SKINS, bonus_text, skin_by_id
from i18n import esc
from service_skins import equip_skin, owned_and_equipped, unequip_skin
from ui import SEP, Out, action, nav


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _title(sub: str = "") -> str:
    return f"⚔️ <b>𝖲𝖤𝖭𝖪𝖠</b> | <b>اسکین‌ها / Skins</b>\n{SEP}\n" + (f"{sub}\n" if sub else "")


def _nm(ctx, s: dict) -> str:
    return s["fa"] if ctx.lang == "fa" else s["en"]


@action("skn")
async def skins_home(ctx, arg):
    owned, cur = await owned_and_equipped(ctx.uid)
    owned_set = set(owned)
    lines = [T(ctx, "یک اسکین بپوش تا بونوس‌هایش فعال شود. فقط یکی همزمان فعال است.",
               "Wear a skin to turn its bonuses on. Only one is active at a time."),
             T(ctx, "اسکین‌ها از گردونه‌ها و پاداش ایونت‌ها می‌آیند.", "Skins come from wheels and event rewards."), ""]
    if cur and cur in SKINS:
        s = SKINS[cur]
        lines.append(f"✅ {T(ctx, 'فعال', 'Active')}: {s['icon']} <b>{esc(_nm(ctx, s))}</b>")
        lines.append(f"   {bonus_text(s, ctx.lang)}")
    else:
        lines.append(T(ctx, "هیچ اسکینی فعال نیست.", "No skin is active."))
    lines.append(f"\n🎭 {T(ctx, 'مجموعه‌ی تو', 'Your collection')}: <b>{len(owned_set & set(SKINS))}/{len(SKINS)}</b>")
    rows = []
    for rar in RARITIES:
        have = [sid for sid, s in SKINS.items() if s["rarity"] == rar and sid in owned_set]
        total = sum(1 for s in SKINS.values() if s["rarity"] == rar)
        lines.append(f"{RARITY_ICON[rar]} {T(ctx, RARITY_FA[rar], rar)}: {len(have)}/{total}")
        for pair in [have[i:i + 2] for i in range(0, len(have), 2)]:
            rows.append([(("✅ " if sid == cur else "") + f"{SKINS[sid]['icon']} {_nm(ctx, SKINS[sid])}", "sks", sid) for sid in pair])
    if cur:
        rows.append([(T(ctx, "🧥 درآوردن اسکین", "🧥 Take off"), "sku", "")])
    rows.append(nav(ctx, ("whl", "")))
    return Out(_title() + "\n".join(lines), rows)


@action("sks")
async def skin_page(ctx, arg):
    s = skin_by_id(arg)
    owned, cur = await owned_and_equipped(ctx.uid)
    if not s or arg not in owned:
        return Out(alert=T(ctx, "⚠️ این اسکین را نداری.", "⚠️ You do not own this skin."))
    text = (_title() + f"{s['icon']} <b>{esc(_nm(ctx, s))}</b> {RARITY_ICON[s['rarity']]} {T(ctx, RARITY_FA[s['rarity']], s['rarity'])}\n"
            f"{bonus_text(s, ctx.lang)}")
    rows = []
    if cur == arg:
        rows.append([(T(ctx, "🧥 درآوردن", "🧥 Take off"), "sku", "")])
    else:
        rows.append([(T(ctx, "👕 پوشیدن", "👕 Wear"), "ske", arg)])
    rows.append(nav(ctx, ("skn", "")))
    return Out(text, rows)


@action("ske")
async def skin_equip(ctx, arg):
    r = await equip_skin(ctx.uid, arg)
    if r != "ok":
        return Out(alert=T(ctx, "⚠️ این اسکین را نداری.", "⚠️ You do not own this skin."))
    return await skins_home(ctx, "")


@action("sku")
async def skin_off(ctx, arg):
    await unequip_skin(ctx.uid)
    return await skins_home(ctx, "")

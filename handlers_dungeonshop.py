"""Dungeon shop: spend dungeon points (DP) on chests that pay coins and an item."""
from data_weapons import RARITIES
from fmt import nm, rarity_name
from i18n import fnum
from database import game_settings
from service_dungeonshop import BOXES, DP_BY_DIFF, RELIC_ODDS, buy_box, dp_balance
from ui import Out, action, head, nav


async def _shop(ctx, note=""):
    L, fa = ctx.lang, ctx.lang == "fa"
    bal = await dp_balance(ctx.uid)
    DP_DAILY_CAP = int((await game_settings())["dp_daily_cap"])
    lines = [(f"{b['icon']} {b['fa' if fa else 'en']}: {fnum(b['cost'], L)} 💠 → " +
              (f"سکه ({fnum(b['coins'][0], L)}–{fnum(b['coins'][1], L)}) + یک آیتم فقط «{rarity_name(RARITIES[b['rar'][0]], L)}» یا «{rarity_name(RARITIES[b['rar'][1]], L)}»"
               f" + {fnum(round(RELIC_ODDS[k][0] * 100), L)}٪ شانس یادگار تکامل" + (" + جایزه‌ی دوم (مواد، معجون یا کتاب)" if k == "gold" else "") if fa else
               f"coins ({fnum(b['coins'][0], L)}–{fnum(b['coins'][1], L)}) + one item, only {rarity_name(RARITIES[b['rar'][0]], L)} or {rarity_name(RARITIES[b['rar'][1]], L)}"
               f" + {round(RELIC_ODDS[k][0] * 100)}% chance of an evolution relic" + (" + a second prize (materials, potions or a book)" if k == "gold" else ""))) for k, b in BOXES.items()]
    info = (f"دانجن‌ها (جز ورطه و افسانه‌ای) سکه نمی‌دن؛ با کلیر کامل هر دانجن دانجن پوینت و تجربه‌ی بیشتر می‌گیری و با شانس کمی آیتم مخصوص دانجن هم دراپ می‌شه (پایه: عادی {DP_BY_DIFF['normal']}، افسانه‌ای {DP_BY_DIFF['legendary']}، و هرچه سطح دانجن بالاتر، بیشتر). سقف روزانه: {fnum(DP_DAILY_CAP, L)}."
            if fa else
            f"Dungeons (except Abyss and Legendary) pay no coins: every full clear pays dungeon points and extra XP, with a small chance of a dungeon-only special item (base: normal {DP_BY_DIFF['normal']}, legendary {DP_BY_DIFF['legendary']}, more in higher-level dungeons). Daily cap: {fnum(DP_DAILY_CAP, L)}.")
    body = (f"💠 <b>{'شاپ دانجن' if fa else 'Dungeon Shop'}</b>\n{'موجودی' if fa else 'Balance'}: {fnum(bal, L)} 💠\n\n"
            + "\n".join(lines) + "\n\n" + info + (("\n\n" + note) if note else ""))
    rows = [[(f"{b['icon']} {b['fa' if fa else 'en']} · {fnum(b['cost'], L)}", "dpb", k)] for k, b in BOXES.items()]
    rows.append(nav(ctx, ("dgn", "")))
    return Out(head(ctx, "ttl_dgn") + body, rows)


@action("dps")
async def dungeon_shop(ctx, arg):
    return await _shop(ctx)


@action("dpb")
async def dungeon_shop_buy(ctx, arg):
    L, fa = ctx.lang, ctx.lang == "fa"
    status, res = await buy_box(ctx.uid, arg)
    if status == "poor":
        return Out(alert=("دانجن پوینتت کافی نیست." if fa else "Not enough dungeon points."))
    if status != "ok":
        return Out()
    b = BOXES[arg]
    name = b["fa" if fa else "en"]
    q = f" ×{fnum(res['qty'], L)}" if res.get("qty", 1) > 1 else ""
    got = (f"🎁 {name} باز شد:\n🪙 {fnum(res['coins'], L)}\n🎁 «{nm(res['item'], L)}»{q}" if fa
           else f"🎁 {name} opened:\n🪙 {fnum(res['coins'], L)}\n🎁 «{nm(res['item'], L)}»{q}")
    if (res.get("bonus") or {}).get("stone"):
        got += "\n🪨 " + ("سنگ آبدیده‌سازی!" if fa else "A Tempering Stone!")
    if (res.get("bonus") or {}).get("item"):
        got += (f"\n✨ جایزه‌ی دوم: «{nm(res['bonus']['item'], L)}» ×{fnum(res['bonus']['qty'], L)}" if fa
                else f"\n✨ Second prize: «{nm(res['bonus']['item'], L)}» ×{fnum(res['bonus']['qty'], L)}")
    if res.get("relic"):
        got += (f"\n🧬 بخت یارت بود: «{nm(res['relic'], L)}» (یادگار تکامل)" if fa
                else f"\n🧬 Lucky: «{nm(res['relic'], L)}» (evolution relic)")
    if res.get("pity"):
        got += "\n🍀 ضمانت جعبه فعال شد." if fa else "\n🍀 Chest pity kicked in."
    return await _shop(ctx, got)

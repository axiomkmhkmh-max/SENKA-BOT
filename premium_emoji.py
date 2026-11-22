"""Premium (custom) emoji for every message the bot sends.

How it works: a request middleware on the bot session rewrites the text / caption of outgoing messages and wraps every
emoji found in PREMIUM_EMOJI in  <tg-emoji emoji-id="...">emoji</tg-emoji>.  Nothing else in the bot has to change.

Telegram only renders them when the bot owner has Telegram Premium, in private / group / supergroup chats.  Everyone else
(and every place that cannot show them) just sees the normal emoji, because the plain emoji stays inside the tag.

Set the env var PREMIUM_EMOJI=0 to switch the whole thing off without touching code.
Packs: GameEmoji, NewsEmoji.  GameEmoji wins when both packs have the same emoji.
"""
import logging
import os
import re

log = logging.getLogger("premium_emoji")

PREMIUM_EMOJI_NEWS = {
    "👀": "5210956306952758910", "🙂": "5461117441612462242", "⚡️": "5456140674028019486",
    "☄️": "5224607267797606837", "🛍": "5229064374403998351", "⛔️": "5260293700088511294",
    "🚫": "5240241223632954241", "❗️": "5274099962655816924", "‼️": "5440660757194744323",
    "⁉️": "5314504236132747481", "❓": "5436113877181941026", "⚠️": "5447644880824181073",
    "🌐": "5447410659077661506", "💬": "5443038326535759644", "💭": "5467538555158943525",
    "📊": "5231200819986047254", "🔼": "5449683594425410231", "🔽": "5447183459602669338",
    "🕯": "5451882707875276247", "📈": "5244837092042750681", "📉": "5246762912428603768",
    "✔️": "5206607081334906820", "❌": "5210952531676504517", "🆒": "5222079954421818267",
    "🔔": "5458603043203327669", "🥸": "5391112412445288650", "🤡": "5269531045165816230",
    "🫦": "5395444514028529554", "📌": "5397782960512444700", "💵": "5409048419211682843",
    "💸": "5233326571099534068", "💱": "5402186569006210455", "▶️": "5264919878082509254",
    "🔴": "5411225014148014586", "🟢": "5416081784641168838", "➡️": "5416117059207572332",
    "🔥": "5424972470023104089", "💥": "5276032951342088188", "🎙": "5294339927318739359",
    "🎤": "5224736245665511429", "📣": "5424818078833715060", "🤫": "5431609822288033666",
    "👎": "5449875686837726134", "🗣️": "5460795800101594035", "🔍": "5231012545799666522",
    "🛡": "5251203410396458957", "🔗": "5271604874419647061", "🖥": "5282843764451195532",
    "©": "5323442290708985472", "ℹ️": "5334544901428229844", "👍": "5337080053119336309",
    "⏸": "5359543311897998264", "💯": "5341498088408234504", "🔄": "5375338737028841420",
    "🔝": "5415655814079723871", "🆕": "5382357040008021292", "🔜": "5440621591387980068",
    "📍": "5391032818111363540", "➕": "5397916757333654639", "💎": "5427168083074628963",
    "⭐️": "5438496463044752972", "✨": "5325547803936572038", "👑": "5217822164362739968",
    "🗑": "5445267414562389170", "🔖": "5222444124698853913", "✉️": "5253742260054409879",
    "🔒": "5296369303661067030", "😮": "5303479226882603449", "📎": "5305265301917549162",
    "⚙️": "5341715473882955310", "🎮": "5361741454685256344", "🔈": "5388632425314140043",
    "⌛": "5386367538735104399", "⬇️": "5406745015365943482", "☀️": "5402477260982731644",
    "🌧": "5399913388845322366", "🌛": "5449569374065152798", "❄️": "5449449325434266744",
    "🌈": "5409109841538994759", "💧": "5393512611968995988", "🗓": "5413879192267805083",
    "💡": "5422439311196834318", "🥇": "5440539497383087970", "🥈": "5447203607294265305",
    "🥉": "5453902265922376865", "🎵": "5463107823946717464", "🆓": "5406756500108501710",
    "✏️": "5395444784611480792", "🚨": "5395695537687123235", "🏠": "5416041192905265756",
    "🚩": "5460755126761312667", "🎉": "5461151367559141950",
}

PREMIUM_EMOJI_GAME = {
    "👍": "5465465194056525619", "🥰": "5465262274031659421", "👋": "5462910521739063094",
    "👎": "5465225015190367274", "😂": "5463121572137022242", "🤟": "5463412289883353404",
    "😴": "5462990652943904884", "💩": "5465198330558557107", "🤝": "5463256910851546817",
    "🗡": "5463277406435422003", "🛡": "5465154440287757794", "🌡": "5463054218459884779",
    "😵": "5463274047771000031", "👉": "5463392464314315076", "🤕": "5463156928307801722",
    "💊": "5463081281048818043", "🚫": "5462882007451185227", "⚰️": "5463186335948878489",
    "🔝": "5463071033256848094", "⬆️": "5463122435425448565", "❓": "5463139580934892960",
    "👌": "5463423955014529788", "🔓": "5465443379917629504", "🪙": "5463046637842608206",
    "⛔️": "5463358164705489689", "🤬": "5463335865235288297", "🛠": "5462921117423384478",
    "💀": "5463250708918711044", "💪": "5463413771647069835", "🎣": "5463406036410969564",
    "⏫": "5462995330163289902", "🙈": "5463345378587849154", "🖕": "5462957817918926146",
    "📦": "5463172695132745432", "🔮": "5463092727136661235", "😭": "5463137996091962323",
    "📀": "5462956611033117422", "🔇": "5462990730253319917", "🎂": "5454089058345042483",
    "⌛️": "5454415424319931791", "☝️": "5453958478454341679", "🧙‍♀️": "5454136337345037322",
    "👥": "5453957997418004470", "🍽": "5454246314277619140", "⚔️": "5454014806950429357",
    "👏": "5454092060527181056", "❌": "5454350746407419714", "🔋": "5454125707300978880",
    "✉️": "5454113432284446338", "🔫": "5454177848203951217", "😱": "5454182632797521992",
    "🕹": "5453921696354419743", "🥹": "5453966029006846697", "🚑": "5453870826761765894",
    "🪖": "5454168390685965478", "✋": "5454380420336466255", "🛍": "5453901475648390219",
    "🎖": "5229045747130843073", "🧠": "5226639745106330551", "💣": "5226813248900187912",
    "🌜": "5226662903569989373", "👁": "5228822494730797152", "💔": "5226829990682707583",
    "🏆": "5226431245918942763", "👾": "5226893221191237996", "🙏": "5228878926306101271",
    "⭐️": "5226928895189598791", "👑": "5229011542011299168", "🛒": "5226656353744862682",
    "😈": "5228962845672096235", "⁉️": "5226618356169194833", "0️⃣": "5226929552319594190",
    "🔄": "5226702984204797593", "🔙": "5253997076169115797", "🔥": "5256047523620995497",
    "💋": "5253922906378881072", "🙅‍♂️": "5258160767789711124", "⏱": "5373236586760651455",
    "🤙": "5373110220232870002", "😨": "5373153324524650873", "😎": "5372965329511139384",
    "💰": "5375312095346704820", "🖥": "5375099322666859339", "🚩": "5373304760776541441",
    "☀️": "5373021138316186413", "🔪": "5373239082136650704", "🗑": "5372825386591732174",
    "💸": "5373174941095050893", "😧": "5375331860786200544", "🤜": "5375161616872520280",
    "😡": "5373261050894370026", "❗️": "5373059848856421989",
}

# GameEmoji overrides NewsEmoji for any emoji both packs have
PREMIUM_EMOJI = {**PREMIUM_EMOJI_NEWS, **PREMIUM_EMOJI_GAME}

MAX_PER_TEXT = 50  # Telegram caps entities per message

_VS16 = "\ufe0f"
_VS16_OR_NOT = _VS16 + "?"


def _strip(e):
    return e.replace(_VS16, "")


# one id per emoji, whatever the variation selector; every char may carry an optional U+FE0F
_BY_PLAIN = {_strip(k): v for k, v in PREMIUM_EMOJI.items()}
_EMOJI_RE = re.compile(
    "(?<!\u200d)(?:"
    + "|".join(
        "".join(re.escape(c) + _VS16_OR_NOT for c in k)
        for k in sorted(_BY_PLAIN, key=len, reverse=True)
    )
    + ")(?![\u200d\U0001F3FB-\U0001F3FF])"
)
_TAG_RE = re.compile(r"(<[^>]*>)")
_TAG_NAME_RE = re.compile(r"<\s*(/?)\s*([a-zA-Z][\w-]*)")
_SKIP_TAGS = {"tg-emoji", "code", "pre"}


def apply(text):
    """Wrap known emoji in <tg-emoji> tags (HTML text). Leaves tags, <code>, <pre> and existing tg-emoji alone."""
    if not text or not isinstance(text, str):
        return text
    count = 0

    def sub(m):
        nonlocal count
        if count >= MAX_PER_TEXT:
            return m.group(0)
        eid = _BY_PLAIN.get(_strip(m.group(0)))
        if not eid:
            return m.group(0)
        count += 1
        return f'<tg-emoji emoji-id="{eid}">{m.group(0)}</tg-emoji>'

    out, skip = [], 0
    for part in _TAG_RE.split(text):
        if part.startswith("<") and part.endswith(">"):
            m = _TAG_NAME_RE.match(part)
            if m and m.group(2).lower() in _SKIP_TAGS and not part.endswith("/>"):
                skip = max(0, skip - 1) if m.group(1) else skip + 1
            out.append(part)
        elif skip:
            out.append(part)
        else:
            out.append(_EMOJI_RE.sub(sub, part))
    return "".join(out)


_TEXT_FIELD = {
    "SendMessage": "text", "EditMessageText": "text",
    "SendPhoto": "caption", "SendVideo": "caption", "SendAnimation": "caption", "SendDocument": "caption",
    "SendAudio": "caption", "SendVoice": "caption", "EditMessageCaption": "caption",
}


def _patch(method):
    """Rewrite the method's text/caption in place; returns (field, original) or None if nothing changed."""
    field = _TEXT_FIELD.get(type(method).__name__)
    if not field:
        return None
    pm = getattr(method, "parse_mode", None)
    if pm is None or (isinstance(pm, str) and pm.upper() != "HTML"):
        return None  # explicit plain text / another parse mode: leave alone (the bot's default is HTML)
    if getattr(method, "entities" if field == "text" else "caption_entities", None):
        return None
    original = getattr(method, field, None)
    if not isinstance(original, str):
        return None
    new = apply(original)
    if new == original:
        return None
    setattr(method, field, new)
    return field, original


def install(bot):
    """Hook the middleware into the bot. Safe to call once at startup."""
    if os.environ.get("PREMIUM_EMOJI", "1").strip().lower() in ("0", "false", "off", "no"):
        log.info("premium emoji: disabled by PREMIUM_EMOJI env var")
        return
    from aiogram.client.session.middlewares.base import BaseRequestMiddleware
    from aiogram.exceptions import TelegramBadRequest

    class PremiumEmojiMiddleware(BaseRequestMiddleware):
        async def __call__(self, make_request, bot, method):
            patched = None
            try:
                patched = _patch(method)
            except Exception:
                log.exception("premium emoji patch failed; sending the original text")
            try:
                return await make_request(bot, method)
            except TelegramBadRequest as e:
                # e.g. a channel / chat that cannot show custom emoji: resend with the normal emoji
                if patched and any(w in str(e).lower() for w in ("emoji", "entit", "parse")):
                    setattr(method, patched[0], patched[1])
                    return await make_request(bot, method)
                raise

    bot.session.middleware(PremiumEmojiMiddleware())
    log.info("premium emoji: %s emoji mapped", len(_BY_PLAIN))

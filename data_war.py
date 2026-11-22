"""⚔️ Event battlefield: every world event is a war between two factions from the Bleach story.

Players of the event's races join their side automatically; races the story leaves out pick a side once (locked until
the war ends). On the battlefield a player fights the enemy faction's soldiers (NPCs), AI copies of real enemy players
("shadows") of a similar level, and once per war the enemy general. Wins give war points to the player's side.

Fairness (the problems this file solves with numbers, the logic is in service_war):
  * population: a side's score is weighed by how many of its players actually won a fight (balance factor, clamped),
    so the side with more players does not win just by being bigger;
  * comeback: a side clearly behind gets a rally bonus on every win;
  * level gaps: shadows are picked from a level window around the attacker, NPCs are built at the attacker's level;
  * farming: beating the same shadow again pays less and then nothing; fights per war are capped; brand-new accounts
    cannot join; the side choice is locked;
  * offline players: a player's shadow defends them — when it beats an attacker, its owner's side gets a point.
Pure data and maths, no I/O."""

# faction id: (fa, en, icon, NPC signature race for enemy_sig)
FACTIONS = {
    "gotei": ("گوتی ۱۳", "Gotei 13", "🏯", None),
    "aizen": ("ارتش آیزن", "Aizen's Army", "🌑", "hollow"),
    "wandenreich": ("وندن‌رایش", "Wandenreich", "✝️", "quincy"),
    "hollows": ("سپاه هالوها", "Hollow Horde", "🌀", "hollow"),
    "ryoka": ("ریوکاها", "The Ryoka", "🔥", None),
    "bount": ("بونت‌ها", "The Bounts", "🩸", None),
    "xcution": ("اکسکیوشن", "Xcution", "🃏", None),
    "red": ("تیم سرخ", "Red Team", "🔴", None),
    "white": ("تیم سفید", "White Team", "⚪", None),
    "darkones": ("تاریک‌زادگان", "The Dark Ones", "🌘", None),
    "div11": ("دسته‌ی یازدهم", "11th Division", "🗡", None),
    "div2": ("دسته‌ی دوم", "2nd Division", "🥷", None),
}

# event kind: (side a, side b, races that join a, races that join b). Races in neither list choose a side.
WARS = {
    "garganta": ("hollows", "gotei", ("hollow", "arrancar"), ("shinigami", "visored", "quincy", "fullbringer", "human")),
    "siege": ("ryoka", "gotei", ("quincy", "fullbringer", "human"), ("shinigami",)),
    "wandenreich": ("wandenreich", "gotei", ("quincy",), ("shinigami", "visored")),
    "winter_war": ("aizen", "gotei", ("hollow", "arrancar"), ("shinigami", "visored")),
    "dangai": ("bount", "gotei", (), ("shinigami",)),
    "soul_festival": ("red", "white", (), ()),
    "hogyoku_awakening": ("aizen", "ryoka", ("hollow", "arrancar"), ("fullbringer", "human", "quincy")),
    "reishi_storm": ("xcution", "gotei", ("fullbringer",), ("shinigami",)),
    # event pack 2
    "black_eclipse": ("darkones", "gotei", (), ("shinigami",)),
    "hollow_tide": ("hollows", "gotei", ("hollow", "arrancar"), ("shinigami", "visored", "quincy", "fullbringer", "human")),
    "soul_bazaar": ("red", "white", (), ()),
    "shinigami_drill": ("div11", "div2", (), ()),
    # event pack 3 (Nov 22)
    "core_rift": ("hollows", "gotei", ("hollow", "arrancar"), ("shinigami", "visored", "quincy", "fullbringer", "human")),
    "kenpachi_rampage": ("div11", "div2", (), ()),
    "blade_festival": ("red", "white", (), ()),
    "mask_masquerade": ("red", "white", (), ()),
}
FRIENDLY = ("soul_festival", "soul_bazaar", "shinigami_drill", "blade_festival", "mask_masquerade")   # a festival match: the losing team keeps more of the reward

# the story behind each war, one line (fa, en)
WAR_STORY = {
    "garganta": ("گارگانتا باز شده و سپاه هالوها به کاراکورا و سیرتی سرازیر شده‌اند.", "The Garganta is open and the Hollow Horde pours into Karakura and the Seireitei."),
    "siege": ("ریوکاها از دروازه‌ی سیرتی رد شده‌اند؛ گوتی ۱۳ باید جلوی نفوذشان را بگیرد.", "The Ryoka have broken through the Seireitei gate; the Gotei 13 must stop the invasion."),
    "wandenreich": ("وندن‌رایش اعلام جنگ کرده؛ اشتیرن‌ریترها بانکای‌ها را می‌دزدند.", "The Wandenreich has declared war; the Sternritter are stealing Bankai."),
    "winter_war": ("جنگ زمستانی در کاراکورای قلابی: ارتش آیزن در برابر کاپیتان‌ها.", "The Winter War in Fake Karakura: Aizen's Army against the captains."),
    "dangai": ("بونت‌ها از دنگای به جامعه‌ی ارواح رسیده‌اند و روح‌ها را می‌بلعند.", "The Bounts reached Soul Society through the Dangai and are devouring souls."),
    "soul_festival": ("جشنواره‌ی ارواح: مسابقه‌ی دوستانه‌ی تیم سرخ و تیم سفید، مثل روز ورزش آکادمی.", "The Soul Festival: a friendly Red vs White match, like the Academy's sports day."),
    "hogyoku_awakening": ("هوگیوکو بیدار شده؛ ارتش آیزن در برابر یاران ایچیگو.", "The Hōgyoku has awakened; Aizen's Army against Ichigo's friends."),
    "reishi_storm": ("در طوفان ریشی، اکسکیوشن قدرت روحی را می‌مکد و گوتی ۱۳ به مقابله آمده.", "In the reishi storm Xcution siphons spiritual power, and the Gotei 13 strike back."),
    "black_eclipse": ("خورشید سیاه شد و تاریک‌زادگان از دره‌ی فریادها بیرون آمده‌اند؛ گوتی ۱۳ باید جلویشان را بگیرد.", "The sun went black and the Dark Ones climbed out of the Valley of Screams; the Gotei 13 must hold them back."),
    "hollow_tide": ("موج هالوها از سرزمین‌های تاریک سرازیر شده؛ سپاه هالوها در برابر همه.", "A tide of Hollows pours from the dark lands: the Hollow Horde against everyone."),
    "soul_bazaar": ("مسابقه‌ی دوستانه‌ی بازار ارواح: تیم سرخ و تیم سفید سر جایزه‌های بازار رقابت می‌کنند.", "The Soul Bazaar's friendly match: the Red and White teams compete for the bazaar's prizes."),
    "shinigami_drill": ("رزمایش گوتی: دسته‌ی یازدهمِ کنپاچی در برابر دسته‌ی دومِ سوی‌فون، دوستانه.", "The Gotei drill: Kenpachi's 11th Division against Suì-Fēng's 2nd, as friends."),
    "core_rift": ("شکافی از هسته‌ی روح باز شده؛ هالوها از آن بیرون می‌ریزند و گوتی ۱۳ باید آن را ببندد.", "A rift of raw Soul Core energy has opened; Hollows pour out and the Gotei 13 must seal it."),
    "kenpachi_rampage": ("کنپاچی از شادی نبرد افسار پاره کرده؛ دسته‌ی یازدهم و دسته‌ی دوم بر سر مهار او رقابت می‌کنند.", "Kenpachi is out of control with joy of battle; the 11th and 2nd Divisions race to contain him."),
    "blade_festival": ("جشن تیغه‌ها: تیم سرخ و تیم سفید در یک مسابقه‌ی دوستانه‌ی شمشیرزنی.", "The Blade Festival: a friendly swordsmanship match between the Red and White teams."),
    "mask_masquerade": ("مهمانی نقاب‌ها: تیم سرخ و تیم سفید با ماسک‌های جشن، دوستانه رقابت می‌کنند.", "The Masquerade of Masks: Red and White teams compete in festival masks, as friends."),
}

# soldiers of each faction (fa, en): what a player fights when they pick "enemy soldier"
SOLDIERS = {
    "gotei": [("شینیگامی بی‌رده", "Unseated Shinigami"), ("افسر رده‌دار دسته‌ی ۱۱", "11th Division Seated Officer"),
              ("قاتل اونمیتسوکیدو", "Onmitsukidō Assassin"), ("جادوگر سپاه کیدو", "Kidō Corps Caster"),
              ("گشت کِیگون", "Keigun Patrol"), ("محقق دسته‌ی ۱۲", "12th Division Researcher")],
    "aizen": [("گیلیان", "Gillian"), ("آجوکاس", "Adjuchas"), ("آرانکار نومروس", "Numeros Arrancar"),
              ("سرباز اکسکیاس", "Exequias Soldier"), ("فراکسیون اسپادا", "Espada Fracción"), ("هالوی مصنوعی آیزن", "Aizen's Artificial Hollow")],
    "wandenreich": [("سرباز یاگدآرمه", "Jagdarmee Soldier"), ("گارد شوتس‌اشتافل", "Schutzstaffel Guard"),
                    ("کماندار کوئینسی", "Quincy Archer"), ("سرباز سایه‌ی وندن‌رایش", "Wandenreich Shadow Trooper"),
                    ("آرانکار اسیر یاگدآرمه", "Captive Arrancar of the Jagdarmee"), ("پیشقراول بلوت", "Blut Vanguard")],
    "hollows": [("هالوی سرگردان", "Stray Hollow"), ("گیلیان", "Gillian"), ("آجوکاس گرسنه", "Starving Adjuchas"),
                ("دسته‌ی هالوها", "Hollow Pack"), ("هالوی بلعنده", "Devourer Hollow"), ("منوس گرانده", "Menos Grande")],
    "ryoka": [("گرازسوار گانجو", "Ganju's Boar Rider"), ("آتش‌باز خاندان شیبا", "Shiba Clan Fireworker"),
              ("انسان روح‌دار کاراکورا", "Spirit-aware Karakura Human"), ("کوئینسی سرگردان", "Wandering Quincy"),
              ("فول‌برینگر تازه‌کار", "Novice Fullbringer"), ("شاگرد اوراهارا", "Urahara's Apprentice")],
    "bount": [("عروسک بونت", "Bount Doll"), ("مزدور بونت", "Bount Mercenary"), ("روح‌خوار سرگردان", "Wandering Soul-eater"),
              ("عروسک مصنوعی اوگاکی", "Ugaki's Artificial Doll"), ("شکارچی نیمه‌شب بونت", "Midnight Bount Hunter"),
              ("خادم عمارت بونت", "Bount Mansion Servant")],
    "xcution": [("فول‌برینگر اکسکیوشن", "Xcution Fullbringer"), ("عروسک خانه‌ی ریروکا", "Riruka's Dollhouse Doll"),
                ("مزدور گینجو", "Ginjō's Hireling"), ("پیک ساعت گیریکو", "Giriko's Clock Herald"),
                ("آواتار بازی یوکیو", "Yukio's Game Avatar"), ("بادیگارد اکسکیوشن", "Xcution Bodyguard")],
    "red": [("دانشجوی آکادمی (سرخ)", "Academy Student (Red)"), ("قهرمان کندوی سرخ", "Red Kendō Champion"),
            ("استاد کیدوی آکادمی", "Academy Kidō Tutor"), ("عضو انجمن زنان شینیگامی", "Shinigami Women's Association Member"),
            ("رقصنده‌ی جشنواره", "Festival Dancer"), ("آتش‌بازِ جشن", "Festival Fireworker")],
    "white": [("دانشجوی آکادمی (سفید)", "Academy Student (White)"), ("قهرمان کندوی سفید", "White Kendō Champion"),
              ("استاد هاکودای آکادمی", "Academy Hakuda Tutor"), ("عضو انجمن مردان شینیگامی", "Shinigami Men's Association Member"),
              ("طبال جشنواره", "Festival Drummer"), ("پرچمدار جشن", "Festival Banner-bearer")],
    "darkones": [("بلنک سرگردان", "Wandering Blank"), ("روح طردشده", "Rejected Soul"), ("تاریک‌زاده", "Dark One"),
                 ("سایه‌ی دره‌ی فریادها", "Valley of Screams Shade"), ("زنجیر شکسته‌ی سرنوشت", "Broken Chain of Fate"), ("نگهبان خورشید سیاه", "Black Sun Warden")],
    "div11": [("شینیگامی بی‌رده‌ی دسته‌ی ۱۱", "Unseated 11th Division Shinigami"), ("جنگجوی تشنه‌ی نبرد", "Battle-Mad Brawler"),
              ("افسر رده‌دار دسته‌ی ۱۱", "11th Division Seated Officer"), ("شمشیرزن بی‌سپر", "Shieldless Swordsman"),
              ("مبارز کوچه‌های زاراکی", "Zaraki Alley Fighter"), ("هم‌رزم کنپاچی", "Kenpachi's Comrade")],
    "div2": [("قاتل اونمیتسوکیدو", "Onmitsukidō Assassin"), ("گشت کِیگون", "Keigun Patrol"), ("نگهبان زندان شین‌اونو", "Maggot's Nest Guard"),
             ("پیک سایه", "Shadow Courier"), ("شینیگامی بی‌رده‌ی دسته‌ی ۲", "Unseated 2nd Division Shinigami"), ("شکارچی شونپو", "Shunpo Hunter")],
}
OFFICERS = {
    "gotei": ("ستوان گوتی", "Gotei Lieutenant"), "aizen": ("پریواران اسپادا", "Privarón Espada"),
    "wandenreich": ("اشتیرن‌ریتر", "Sternritter"), "hollows": ("آجوکاس گله‌دار", "Pack-leader Adjuchas"),
    "ryoka": ("محافظ کوکاکو", "Kūkaku's Bodyguard"), "bount": ("بونت کهنه‌کار", "Veteran Bount"),
    "xcution": ("مجری اکسکیوشن", "Xcution Enforcer"), "red": ("کاپیتان تیم سرخ", "Red Team Captain"),
    "white": ("کاپیتان تیم سفید", "White Team Captain"), "darkones": ("ارباب تاریک‌زادگان", "Dark One Lord"),
    "div11": ("ستوان دسته‌ی ۱۱", "11th Division Lieutenant"), "div2": ("فرمانده‌ی اونمیتسوکیدو", "Onmitsukidō Commander"),
}
# the enemy general, by the attacker's level tier (<30, 30-59, 60-89, 90+)
GENERALS = {
    "gotei": [("ایکاکو مادارامه", "Ikkaku Madarame"), ("رنجی آبارای", "Renji Abarai"), ("بیاکویا کوچیکی", "Byakuya Kuchiki"), ("کنپاچی زاراکی", "Kenpachi Zaraki")],
    "aizen": [("دوردونی", "Dordoni"), ("گریمجو جگرجاک", "Grimmjow Jaegerjaquez"), ("اولکیورا شیفر", "Ulquiorra Cifer"), ("سوسکه آیزن", "Sōsuke Aizen")],
    "wandenreich": [("باز-بی", "Bazz-B"), ("اس نوت", "Äs Nödt"), ("یوگرام هاشوالث", "Jugram Haschwalth"), ("یوهاباخ", "Yhwach")],
    "hollows": [("شریکر", "Shrieker"), ("گرند فیشر", "Grand Fisher"), ("باراگان لوئیزنبارن", "Barragan Luisenbarn"), ("ایچیگوی واستو لورد", "Vasto Lorde Ichigo")],
    "ryoka": [("گانجو شیبا", "Ganju Shiba"), ("یاسوتورا سادو", "Yasutora Sado"), ("اوریو ایشیدا", "Uryū Ishida"), ("ایچیگو کوروساکی", "Ichigo Kurosaki")],
    "bount": [("یوشینو سوما", "Yoshino Sōma"), ("اوگاکی", "Ugaki"), ("گو کوگا", "Gō Koga"), ("جین کاریا", "Jin Kariya")],
    "xcution": [("جکی تریستان", "Jackie Tristan"), ("گیریکو کوتسوزاوا", "Giriko Kutsuzawa"), ("شوکورو تسوکیشیما", "Shūkurō Tsukishima"), ("کوگو جینجو", "Kūgo Ginjō")],
    "red": [("یاچیرو کوساجیشی", "Yachiru Kusajishi"), ("رانگیکو ماتسوموتو", "Rangiku Matsumoto"), ("کوکاکو شیبا", "Kūkaku Shiba"), ("یوروئیچی شیهوئین", "Yoruichi Shihōin")],
    "white": [("نانائو ایسه", "Nanao Ise"), ("روکیا کوچیکی", "Rukia Kuchiki"), ("رتسو اونوهانا", "Retsu Unohana"), ("جوشیرو اوکیتاکه", "Jūshirō Ukitake")],
    "darkones": [("ریان", "Riyan"), ("بنین", "Benin"), ("مو", "Mū"), ("گانریو", "Ganryū")],
    "div11": [("یومیچیکا آیاسه‌گاوا", "Yumichika Ayasegawa"), ("ایکاکو مادارامه", "Ikkaku Madarame"), ("یاچیرو کوساجیشی", "Yachiru Kusajishi"), ("کنپاچی زاراکی", "Kenpachi Zaraki")],
    "div2": [("ماره‌چیو اوماِدا", "Marechiyo Ōmaeda"), ("فرمانده‌ی گروه اعدام", "Executive Militia Commander"), ("سوی‌فون", "Suì-Fēng"), ("یوروئیچی شیهوئین", "Yoruichi Shihōin")],
}

# ---- numbers ---------------------------------------------------------------------------------------------------------------
WAR_PTS = {"npc": 1, "officer": 2, "shadow": 3, "general": 10}
OFFICER_CHANCE = 0.20           # an enemy soldier is sometimes an officer: stronger, 2 points
OFFICER_SCALE = 1.35
GENERAL_SCALE = 2.4
GENERAL_UNLOCK_WINS = 5         # the general challenges you after this many wins in the war (once per war)
WAR_FIGHT_CAP = 40              # battlefield fights per player per war
SHADOW_WINDOWS = (5, 10, 18)    # level windows tried in order when looking for an enemy shadow
SHADOW_REPEAT = (1.0, 0.5, 0.0)  # points for the 1st, 2nd, 3rd+ win against the same shadow in one war
SHADOW_DEF_CAP = 15             # points a player's shadow can earn for its side by defending, per war
RALLY_BEHIND = 0.85             # a side under 85% of the other side's weighed score ...
RALLY_BONUS = 0.25              # ... gets +25% points on every win
BALANCE_MIN, BALANCE_MAX = 0.6, 2.5
FIGHT_K = {"npc": (1.0, 1.0), "officer": (1.3, 1.3), "shadow": (1.6, 1.5), "general": (3.0, 3.0)}  # (XP, coins) x normal fight
GENERAL_COINS = 2000            # extra purse for beating the general, x (1 + level / 10)
GENERAL_RELIC = 0.35
GENERAL_STONE = 0.15
# end of the war
REWARD_COINS = 1500             # x (1 + level / 10) x side result x performance
REWARD_XP = 1200
SIDE_MULT = {"win": 1.0, "lose": 0.45, "friendly_lose": 0.7, "draw": 0.7}
MIN_PTS_REWARD = 2              # war points needed for the end-of-war reward
PTS_FULL = 10                   # the end reward reaches its full size at this many points (fewer points, smaller share)
STONE_PTS = 10                  # Tempering Stones at the end of the war only for fighters with at least this many points
WIN_ITEM_PTS = 10               # winners with this many points: a chance of a purple-or-better item
WIN_ITEM_CHANCE = 0.25
GLORY_XP = 0.05                 # winners with 5+ points: +5% XP for 24 hours
GLORY_PTS = 5
GLORY_SECONDS = 24 * 3600


def war_of(kind: str):
    return WARS.get(kind)


def auto_side(kind: str, race: str):
    """'a' / 'b' for races the story places, None for races that choose."""
    w = WARS.get(kind)
    if not w:
        return None
    if race in w[2]:
        return "a"
    if race in w[3]:
        return "b"
    return None


def other(side: str) -> str:
    return "b" if side == "a" else "a"


def faction_of(kind: str, side: str) -> str:
    w = WARS[kind]
    return w[0] if side == "a" else w[1]


def tier(level: int) -> int:
    return 0 if level < 30 else 1 if level < 60 else 2 if level < 90 else 3


def general_of(faction: str, level: int):
    return GENERALS[faction][tier(level)]


def balance(act_side: int, act_other: int) -> float:
    """Weight of one side's points: the average active size over this side's active size, clamped."""
    if act_side <= 0:
        return 0.0
    mean = (act_side + act_other) / 2
    return max(BALANCE_MIN, min(BALANCE_MAX, mean / act_side))


def weighed(pts: dict, act: dict) -> dict:
    """{'a': score, 'b': score} after the population balance."""
    a, b = int(pts.get("a", 0)), int(pts.get("b", 0))
    na, nb = int(act.get("a", 0)), int(act.get("b", 0))
    return {"a": a * balance(na, nb), "b": b * balance(nb, na)}


def shares(pts: dict, act: dict) -> dict:
    """Percent of the war each side holds (50/50 before anyone scores)."""
    w = weighed(pts, act)
    tot = w["a"] + w["b"]
    if tot <= 0:
        return {"a": 50, "b": 50}
    a = round(100 * w["a"] / tot)
    return {"a": a, "b": 100 - a}


def rally(side: str, pts: dict, act: dict) -> bool:
    w = weighed(pts, act)
    mine, theirs = w[side], w[other(side)]
    return theirs >= 5 and mine < theirs * RALLY_BEHIND


def winner(pts: dict, act: dict):
    w = weighed(pts, act)
    if w["a"] == w["b"]:
        a, b = int(pts.get("a", 0)), int(pts.get("b", 0))
        return None if a == b else ("a" if a > b else "b")
    return "a" if w["a"] > w["b"] else "b"


def shadow_points(my_level: int, foe_level: int, wins_before: int) -> int:
    """Points for beating a shadow: 3, one more against a clearly higher level, one less against a clearly lower one;
    then the repeat factor for beating the same shadow again in this war."""
    base = WAR_PTS["shadow"] + (1 if foe_level >= my_level + 4 else -1 if foe_level <= my_level - 4 else 0)
    k = SHADOW_REPEAT[min(wins_before, len(SHADOW_REPEAT) - 1)]
    return int(base * k)


def with_rally(pts: int, on: bool) -> int:
    if not on or pts <= 0:
        return pts
    return pts + max(1, int(pts * RALLY_BONUS + 0.5))


def end_reward(level: int, pts: int, side_avg: float, result: str):
    """(xp, coins) of the end-of-war reward. result: win / lose / friendly_lose / draw."""
    perf = (0.6 + 0.4 * min(2.0, pts / max(1.0, side_avg))) * (0.4 + 0.6 * min(1.0, pts / PTS_FULL))
    lk = 1 + level / 10
    m = SIDE_MULT[result]
    return int(REWARD_XP * lk * m * perf), int(REWARD_COINS * lk * m * perf)

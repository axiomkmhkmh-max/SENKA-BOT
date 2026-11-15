"""In-game guide topics (راهنما). Pure text, keyed by language. Add a topic here and a button in handlers_panels.

Every number below is taken from the code (service_player, engine, data_races), so the guide and the game agree.
"""

STATS_TOPIC = {
    "fa": (
        "📊 <b>استت‌ها</b>\n"
        "━━━━━━━━━━━━━━\n"
        "هر کاراکتر پنج استت دارد. هر استت یک عدد پایه از نژادت می‌گیرد و بعد با امتیازهایی که با بالا رفتن لول می‌گیری زیاد می‌شود.\n\n"
        "⚔️ <b>زنجوتسو</b> — قدرت ضربه‌ی تیغه.\n"
        "کل آسیب حمله‌ی معمولی و ضربه‌ی سنگین را بالا می‌برد و میزان آسیب ضربه‌ی کاری (کریت) را زیاد می‌کند.\n\n"
        "🔮 <b>کیدو</b> — قدرت جادوهای کیدو.\n"
        "آسیب هادو را بالا می‌برد و قدرت باکودو (سپر و گرفتن) را هم زیاد می‌کند.\n\n"
        "🛡️ <b>هاکودا</b> — بدنه و دفاع.\n"
        "جون بیشینه را بالا می‌برد (هر امتیاز ۸ جون) و آسیب دریافتی تو را کم می‌کند.\n\n"
        "💨 <b>هوهو</b> — سرعت و چابکی.\n"
        "شانس جاخالی دادن، شانس کریت کوچک و ترتیب حمله‌ی تو در نوبت را بالا می‌برد.\n\n"
        "✨ <b>ریاتسو</b> — منبع انرژی معنوی.\n"
        "ریاتسوی بیشینه‌ات را بالا می‌برد (هر امتیاز ۱۲ واحد)، و ریاتسو برای رهاسازی گتسوگا و مهارت‌های ویژه لازم است.\n\n"
        "<b>امتیاز می‌گیری از کجا؟</b>\n"
        "هر لول سه امتیاز می‌دهد و در لول‌های مضرب ۵ یک امتیاز اضافه. امتیازها را با دکمه‌ی ➕ زیر هر استت خرج می‌کنی.\n\n"
        "<b>سقف نرم (افت بازده)</b>\n"
        "تا ۱۰۰ امتیاز هر امتیاز کامل حساب می‌شود. از ۱۰۰ تا ۲۰۰ فقط ۸۰٪، از ۲۰۰ تا ۵۰۰ فقط ۵۰٪، و بالاتر از ۵۰۰ فقط ۳۰٪. "
        "یعنی زیاد کردن یک استت خیلی بالا صرفه‌ی کمتری دارد؛ بهتره بین استت‌ها پخش کنی.\n\n"
        "<b>نکته:</b> نژاد و مسیر تکامل هم روی استت‌ها اثر دارن (مثلاً شینیگامی زنجوتسو و کیدوی بیشتری می‌گیرد و آرانکار هاکودا و ریاتسو)."
    ),
    "en": (
        "📊 <b>Stats</b>\n"
        "━━━━━━━━━━━━━━\n"
        "Every character has five stats. Each starts from your race's base value and grows with the points you earn by levelling up.\n\n"
        "⚔️ <b>Zanjutsu</b> — blade power.\n"
        "Raises the damage of normal attacks and heavy strikes, and makes critical hits hit harder.\n\n"
        "🔮 <b>Kidō</b> — spell power.\n"
        "Raises Hadō damage, and the strength of Bakudō (shields and binds).\n\n"
        "🛡️ <b>Hakuda</b> — body and defence.\n"
        "Raises max HP (8 per point) and reduces the damage you take.\n\n"
        "💨 <b>Hoho</b> — speed and agility.\n"
        "Raises your dodge chance, a small critical bonus, and your place in the turn order.\n\n"
        "✨ <b>Reiatsu</b> — spiritual energy.\n"
        "Raises max reiatsu (12 per point). Reiatsu pays for Getsuga and other special moves.\n\n"
        "<b>Where do points come from?</b>\n"
        "Each level gives 3 points, and every 5th level gives 1 extra. Spend them with the ➕ buttons under each stat.\n\n"
        "<b>Soft cap (diminishing returns)</b>\n"
        "The first 100 points count fully. From 100 to 200 they count 80%, from 200 to 500 they count 50%, and above 500 they count 30%. "
        "Pushing one stat very high pays less, so spread your points.\n\n"
        "<b>Note:</b> your race and evolution path also shape these (a Shinigami gets more Zanjutsu and Kidō, an Arrancar more Hakuda and Reiatsu)."
    ),
}

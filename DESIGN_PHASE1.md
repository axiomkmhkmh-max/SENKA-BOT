# SENKA — طراحی فاز ۱ (بدون کد)

## ۰. یافته‌های کد فعلی که طراحی روی آن‌ها بنا شده

- آیتم‌ها در `data_items.py` با `PLAN` ساخته می‌شوند و فیلد `eff` دارند. فقط ۶ نوع `eff` وجود دارد: `hp`، `reiatsu`، `xp`، `kido`، `pet`، `key`.
- برای `material`، `relic`، `cosmetic`، `evolution` هیچ `eff` ای ساخته نمی‌شود. `material` فقط در فورج (`service_economy.py` خط ~۳۹۲) مصرف می‌شود.
- ۱۱ لوکیشن در `LOCATIONS` (`data_races.py`): soul_society، rukongai، karakura، seireitei، hueco_mundo، las_noches، dangai، wandenreich، royal_palace، soul_king، valley_screams.
- تکامل نژاد فقط با `LEVEL_GATES = [1, 15, 35, 60, 90]` و فقط به‌صورت عنوان (`race_title`) است. هیچ آزمون یا آیتمی ندارد.
- باس در `boss_sessions` به‌ازای `chat_id` ساخته می‌شود. پرداخت در `_pay` انجام می‌شود (سهم از `contrib`).
- تنظیمات live: `GAME_DEFAULTS` در `config.py` و `set <key> <value>`.
- ایندکس‌ها در `database.py` (دیکشنری `specs`). TTL با `expireAfterSeconds` استفاده شده است.

**اصل طراحی:** اثر هر آیتم از یک فیلد `eff` داده‌محور خوانده می‌شود. یک رجیستری `EFFECTS = {type: handler}` در فایل جدید `service_effects.py` منطق را نگه می‌دارد و `use`، `item_card` و engine همه از همان استفاده می‌کنند. if/else پراکنده نداریم.

---

## ۱. جدول «category ← اثر»

| category | وضع فعلی | نقش جدید | `eff` جدید | کجا اعمال می‌شود |
|---|---|---|---|---|
| material | فقط فورج | ورودی craft: معجون، ارتقای زره، کلید دانجن؛ ورودی فورج هم می‌ماند | `{type:"mat", tag:"bone\|reishi\|thread\|ore\|dust\|fang\|cloth\|mask\|ribbon\|sekki", pw:1..6}` | `data_crafting.py` (recipeها بر اساس tag و pw، نه آیتم تکی) |
| relic | بی‌اثر | بافِ پسیو؛ حداکثر ۲ اسلات فعال | `{type:"relic", buff:{xp_loc:{loc,pct}} \| {threat_down:n} \| {drop_pct:n} \| {coin_pct:n}}` | `service_effects.passive_mods(ch)` |
| evolution | بی‌اثر | آیتم آزمون تکامل | `{type:"evo", race:..., stage:n}` | `service_player.evolve()` و `race_title` |
| cosmetic | بی‌اثر | aura/trail/banner؛ نمایش کنار نام + بافِ کوچک + شهرت | `{type:"cosm", slot:"aura\|trail\|banner", glyph:"✨", fame:n, buff:{...}}` | `fmt.display_name(ch)` در رتبه‌بندی، لاگ نبرد و فید دنیا |
| egg/pet | `pet` وجود دارد ولی بی‌اثر | تخم ← تفریخ (با گشت) ← همراه فعال با نقش واقعی | `{type:"pet", tier, role:"fang\|heal\|luck"}` | engine (fang: آسیب)، گشت (luck: دراپ)، شروع نبرد (heal: شفا) |
| book | فقط XP | مهارت، کیدو یا بافِ موقت | `{type:"book", grant:"skill:<id>" \| "kido:<br>:<n>" \| "buff:<key>:<pct>:<min>"}` | `use` ← `service_effects` |
| key | فقط دانجن | ورودی رویداد دنیا هم هست | `{type:"key", dungeon, diff, world:["garganta","siege"]}` | رویدادهای دنیا |
| kido_card / تیغه / زره / اکسسوری | جداگانه | اثر متنی واقعاً در engine اعمال شود | موجود، بررسی فیلد `fx` | `engine.py` و `service_combat.py`؛ تست پوشش‌دهنده‌ی همه‌ی fxها |
| potion | hp/reiatsu | بدون تغییر (فقط craftable) | — | — |

**نمایش:** `item_card` یک خط اثر از `EFFECTS[type].describe(eff, lang)` می‌گیرد. متن‌ها با کلید `fx_<type>` در locale ها هستند.

**ضرایب در `GAME_DEFAULTS`:** `relic_slots`، `relic_effect_mult`، `craft_cost_mult`، `craft_daily_cap`، `pet_fang_pct`، `pet_heal_pct`، `pet_luck_pct`، `egg_hatch_explores`، `cosmetic_fame_cap`، `book_buff_minutes`، `evo_item_required`.

**ورودی craft (`data_crafting.py`):** هر recipe شامل `out`، `inputs:[{tag,pw,qty}]`، `coins`، `min_level`، `cooldown` است. ورودی‌ها بر اساس tag تطبیق می‌خورند تا ۱۶۰ ماده‌ی متفاوت در recipeهای کمی استفاده شوند.

---

## ۲. Schema مجموعه‌های جدید و تغییرات

همه‌ی نوشتن‌ها با `find_one_and_update` / `$inc` / `$setOnInsert` و کلید یکتا (`tx_key`) برای جلوگیری از دوبل‌شدن.

### `world_state` (سند واحد `_id:"world"`)
```
{ _id:"world", rev:int,
  vars:{ threat:float(0..100), stability:float(0..100) },
  reishi:{ <loc_id>: float(0..100) },
  event:{ id, kind, started_at, ends_at, hp?, goal?, progress, contrib:{uid:n} } | null,
  boss:{ sid } | null,
  season:{ id, started_at, ends_at },
  updated_at }
```
- تغییر متغیرها فقط با `$inc` و clamp (pipeline update یا `$min/$max` در ادامه).
- `rev` برای بررسی تغییرات در cache محلی (TTL حدود ۱۰ ثانیه) استفاده می‌شود.

### `world_boss` (جایگزین `boss_sessions` برای باس جهانی؛ قدیمی می‌ماند)
```
{ _id:sid, boss_id, level, hp, max_hp, active, spawn_at, expires_at,
  contrib:{uid:dmg}, hits, last_hitter, announce:[{chat_id,msg_id}] }
```
- ایندکس: `(active)`. اعلان به همه‌ی `groups` ثبت‌شده با ویرایش پیام‌ها انجام می‌شود (محدودیت نرخ).

### `world_events`
```
{ _id, kind, started_at, ends_at, params, result }   // آرشیو، TTL 90 روز
```

### `world_log` (World Chronicle)
```
{ at, kind, ref, text_key, args:{...}, uid? }          // TTL 14 روز
```
ایندکس `(at desc)`. متن از `text_key` و `args` در زمان نمایش و به زبان بیننده ساخته می‌شود.

### `territories`
```
{ _id:<loc_id>, owner:{type:"guild", id}, since, points:{<guild_id>:n}, last_decay, income_pool }
```
- مشارکت: `$inc points.<gid>`؛ تصرف وقتی `points` گیلد غالب از آستانه‌ی `terr_capture_pts` رد شود و با فاصله‌ی `terr_margin` از دومی.
- Decay دوره‌ای برای جلوگیری از قفل‌شدن.

### `world_marks` (ردپای بازیکن در لوکیشن)
```
{ loc, uid, kind:"grave|trace|gift|bounty", payload, created_at, expire_at, claimed_by }
```
TTL روی `expire_at`. ایندکس `(loc, kind, expire_at)`.

### `bounties`
```
{ _id, target_uid, issuer, amount, status, expire_at }
```

### `seasons`
```
{ _id:"s<N>", started_at, ends_at, rewards_paid:bool, top:[...] }
```

### تغییرات روی سندهای فعلی (فیلدهای جدید با مقدار پیش‌فرض، بدون migration اجباری)
- `characters`: `relics:[]` (≤۲)، `cosmetic:{aura,trail,banner}`، `pet:{id,tier,role,hatch_left}`، `evo_stage:int`، `fame:int`، `world:{day,xp,coins,events}` برای سقف روزانه.
- خواندن همیشه با `ch.get(field, default)`.
- `groups`: `world_announce:bool = true` (امکان خاموش‌کردن اعلان).

---

## ۳. متغیرهای دنیا و اثرشان

| متغیر | محدوده | چه چیزی آن را بالا/پایین می‌برد | اثر روی بازی |
|---|---|---|---|
| **Hollow Threat** | 0–100 | بالا: گشت و دانجن بدون شکار، شکست باس، رویداد Garganta؛ پایین: کشتن هالو، relic کاهش‌دهنده | نرخ spawn باس ← کوتاه‌تر، قدرت دشمنان گشت (+٪)، آستانه‌ی رویداد Garganta |
| **Seireitei Stability** | 0–100 | بالا: کشتن باس، موفقیت دانجن، قلمروهای نگه‌داری‌شده؛ پایین: محاصره و تهاجم | نرخ دراپ، تخفیف/افزایش قیمت بازار (سقف ±۱۰٪)، آستانه‌ی Siege |
| **Reishi Level** (هر لوکیشن) | 0–100 | مصرف مواد و آیتم‌های reishi، گشت جمعی؛ با زمان به ۵۰ برمی‌گردد | XP/کوین گشت همان لوکیشن (±۱۰٪)، شانس دراپ مواد |
| **Threat Event Meter** | 0–∞ | جمع کارهای جمعی | شروع/پایان رویدادها |

هر متغیر یک «ضریب اثر» دارد (`world_threat_enemy_pct`, `world_stab_drop_pct`, ...) در `GAME_DEFAULTS`. برگشت به میانگین: `world_decay_per_hour`.

**سقف مشارکت (ضد-سوءاستفاده):** هر کاربر در روز حداکثر `world_daily_points_cap` امتیاز به متغیرهای دنیا می‌دهد. حساب‌های جدید (زیر `world_min_level` یا زیر `world_min_age_hours`) مشارکتشان صفر حساب می‌شود.

---

## ۴. رویدادهای دنیا

| رویداد | شرط شروع | اثر هم‌زمان | جایزه |
|---|---|---|---|
| **Garganta Opens** | Threat ≥ ۷۰ | spawn هالو بیشتر، دشمنان گشت قوی‌تر | سهم از امتیاز کشتن؛ Threat کاهش می‌یابد |
| **Seireitei Siege** | Stability ≤ ۳۰ | باس جهانی سخت‌تر؛ مشارکت دفاع | XP/کوین/دراپ؛ Stability بالا می‌رود |
| **Wandenreich Invasion** | زمان‌بندی (هفتگی) | باس رویداد + قلمروها در خطر | جایزه ویژه و relic |

- شروع/پایان با scheduler فعلی (lease تک‌نمونه) و `world_state.event` انجام می‌شود.
- جایزه‌ی مشارکت با آستانه‌ی حداقل (`event_min_points`) و ثبت یکتا (`tx_key = "evt:<id>:<uid>"`) پرداخت می‌شود.

---

## ۵. باس جهانی واحد

- در هر لحظه یک سند فعال در `world_boss`. spawn با `find_one_and_update` روی `world_state.boss` اتمیک (فقط اگر `null` باشد).
- `boss_hit` با `$inc hp:-dmg` و `$inc contrib.<uid>` و clamp و پرچم kill (شرط `hp > 0` در فیلتر) انجام می‌شود تا kill دوبل نشود.
- اعلان: پست در همه‌ی `groups` ثبت‌شده؛ ویرایش با throttle (`boss_edit_interval`). چت خصوصی: پنل «باس جهانی» در منو.
- لیدربورد سهم بازیکن‌ها در پنل.
- مهاجرت: `boss_sessions` قدیمی ادامه می‌یابد تا تمام شود؛ spawn جدید فقط جهانی.

---

## ۶. قلمرو، اثر بازیکن روی بازیکن، فصل‌ها (خلاصه)

- **قلمرو:** مالک ← بافِ کوچک (`terr_buff_pct`) + `terr_income_pct` از درآمد گشت آن لوکیشن (از `income_pool`، نه از جیب بازیکن). ضد-سوءاستفاده: فقط اعضای حداقل N روز عضو گیلد امتیاز می‌دهند و سقف روزانه دارند؛ cooldown تغییر مالک.
- **اثر بازیکن روی بازیکن:** `world_marks` (قبر/رد ریاتسو/هدیه/باونتی) با سقف تعداد در لوکیشن و سقف روزانه برای هر کاربر؛ اضافه بر آن cooldown.
- **فصل:** هر `season_days` روز: ریست نرم رتبه‌ی PvP (`rating = 1000 + (rating-1000)*season_keep`) و صفر شدن مشارکت دنیا، با جایزه‌ی ۳ نفر برتر و آستانه‌ی مشارکت.
- **Chronicle:** ۵ آیتم آخر در پنل «خانه» و «نقشه».

---

## ۷. فایل‌های جدید و تغییرات (برای فازهای بعد)

| فایل | مسئولیت |
|---|---|
| `service_effects.py` (جدید) | رجیستری `EFFECTS`، `passive_mods`، `use_item` |
| `data_crafting.py` (جدید) | recipeها و tagها |
| `service_worldstate.py` (جدید) | world_state، متغیرها، رویدادها، chronicle، season |
| `service_territory.py` (جدید) | قلمرو |
| `handlers_world.py` (جدید) | پنل دنیا، باس جهانی، قلمرو |
| `database.py` | ایندکس و TTL مجموعه‌های جدید |
| `config.py` | کلیدهای جدید `GAME_DEFAULTS` |
| `engine.py`، `service_combat.py` | اعمال pet/relic/fx |
| `fmt.py`، `locale_fa.py`، `locale_en.py` | `item_card` و متن‌ها |
| `handlers_admin.py` | دستورهای `world ...` |
| `tests/` | تست واحد منطق خالص |

---

## ۸. ریسک‌ها و پرسش‌ها برای تأیید شما

1. **باس قدیمی per-group:** جایگزین کامل شود یا گروه‌ها گزینه‌ی «باس محلی» هم داشته باشند؟ (پیشنهاد: جایگزین کامل.)
2. **اسلات relic:** ۲ اسلات ثابت یا بازشونده با لول؟ (پیشنهاد: ۱ اسلات از لول ۲۰ و اسلات دوم از لول ۵۰.)
3. **pet:** فقط یک همراه فعال؟ (پیشنهاد: بله.)
4. **قلمرو:** فقط گیلد یا جوخه (squad) هم؟ (پیشنهاد: هر دو با `owner.type`.)
5. **اعلان به همه‌ی گروه‌ها:** با تعداد زیاد گروه، محدودیت نرخ تلگرام (حدود ۲۰ پیام در دقیقه به گروه‌ها) صف‌بندی لازم دارد؛ اعلان‌ها با تأخیر کوتاه پخش می‌شوند.
6. **تعادل:** ضرایب همه با `set` تغییر می‌کنند؛ مقادیر اولیه محافظه‌کارانه‌اند (اثر هر relic حداکثر ۵٪).

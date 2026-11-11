"""Texts for the six retention loops (merged into the main tables by i18n.py)."""

FA = {
    # ---- menu / titles / buttons ----
    "m_twr": "🗼 برج روح", "m_dsp": "🧭 اعزام", "m_whl": "🎡 چرخ اوراهارا", "m_sat": "🎖️ درجه‌ی گوتی", "m_inr": "🌌 دنیای درون",
    "ttl_twr": "برج روح", "ttl_dsp": "اعزام", "ttl_whl": "چرخ شانس اوراهارا", "ttl_sat": "درجه‌ی گوتی", "ttl_inr": "دنیای درون",
    "b_tgo": "🗼 صعود", "b_tlb": "🏅 رتبه‌ی این هفته", "b_dclaim": "🎁 دریافت جایزه", "b_dsend": "➕ اعزام کاراکتر",
    "b_spin_free": "🎡 چرخش رایگان", "b_spin_paid": "🎡 چرخش ({cost} 🪙)", "b_sclaim": "🎁 جایزه‌ی ارتقا", "b_inr_again": "🌌 دیدار بعدی",
    # ---- tower ----
    "tw_body": ("برج روح بی‌پایان است. هر طبقه دشمنی قوی‌تر از قبلی دارد و هر ۵ طبقه یک نگهبان 👑 جایزه‌ی ویژه می‌دهد.\n"
                "HP و ریاتسو بین طبقه‌ها همراهت می‌آید (کمی ترمیم می‌شود). اگر سقوط کنی، دفعه‌ی بعد از ابتدای همان بلوک ۵تایی شروع می‌کنی.\n\n"
                "🏆 بهترین طبقه: <b>{best}</b>\n📅 رکورد این هفته: <b>{wk}</b>\n🚩 شروع از طبقه: <b>{start}</b>\n"
                "⚡ هزینه‌ی هر صعود: {cost} انرژی\n🎁 طبقه‌های پاداش‌دار امروز: {left}/{cap}"),
    "tw_e_busy": "اول نبردِ پیش‌رویت را تمام کن.", "tw_e_energy": "انرژی کافی نداری ⚡",
    "tw_floor": "🗼 طبقه {n}", "tw_floor_boss": "🗼 طبقه {n} — 👑 نگهبان", "tw_floor_n": "طبقه {n}",
    "tw_lb": "🏅 برترین‌های برج در این هفته",
    "tw_win": "✅ طبقه {n} پاک شد!\n+{xp} XP، +{coins} 🪙", "tw_nopay": "سقف پاداش امروز پر شده؛ ولی طبقه ثبت می‌شود.",
    "tw_record": "🏆 رکورد جدید: طبقه {n}!", "tw_milestone": "🎁 پاداش نقطه‌عطف: +{coins} 🪙",
    "tw_fall": "💀 در طبقه {n} سقوط کردی. بهترین رکوردت: طبقه {best}.", "tw_next": "➡️ طبقه‌ی بعد منتظر توست؛ زخم‌هایت همراهت هستند.",
    "b_tnext": "➡️ طبقه‌ی بعد", "b_tretry": "🗼 صعود دوباره",
    # ---- chain ----
    "ch_line": "🔥 زنجیره ×{n} (+{pct}٪ پاداش)", "ch_lost": "💔 زنجیره‌ی {n} تایی شکست.", "ch_bonus": "🎁 پاداش زنجیره: {item}",
    # ---- dispatch ----
    "ds_body": ("همراهانت را به ماموریت بفرست؛ وقتی برگشتند جایزه می‌گیری، حتی اگر آفلاین باشی.\nنقش‌ها: {roles}\n\n"
                "اسلات‌ها: {used}/{slots}"),
    "ds_hours": "{h} ساعت", "ds_pick_m": "ماموریت را انتخاب کن:", "ds_pick_c": "کدام کاراکتر برود؟",
    "ds_nochars": "هیچ کاراکتر آزادی نداری. از «احضار» کاراکتر بگیر.",
    "ds_e_bad": "انتخاب نامعتبر.", "ds_e_level": "سطحت برای این ماموریت کم است.", "ds_e_notowned": "این کاراکتر را نداری.",
    "ds_e_busy": "این کاراکتر هم‌اکنون در ماموریت است.", "ds_e_slots": "همه‌ی اسلات‌ها پر است.", "ds_e_none": "هنوز ماموریتی تمام نشده.",
    "ds_sent": "🧭 اعزام شد!", "ds_done": "🎁 ماموریت‌ها تمام شد:",
    # ---- wheel ----
    "wh_body": "اوراهارا هر روز یک چرخش رایگان می‌دهد؛ شاید این بار جکپات بیاید!\n\n{prizes}\n\nچرخش اضافه: {cost} 🪙",
    "wh_free": "✨ امروز یک چرخش رایگان داری.", "wh_extra": "چرخش رایگان امروز را زده‌ای. چرخش اضافه: {n} بار، هرکدام {cost} 🪙.",
    "wh_none": "برای امروز تمام شد؛ فردا برگرد.",
    "wh_e_used": "امروز چرخش نداری.", "wh_e_limit": "سقف چرخش امروز پر شد.", "wh_e_funds": "سکه‌ی کافی نداری.",
    # ---- seat ----
    "sat_now": "درجه‌ی فعلی: {icon} <b>{name}</b>\nامتیاز فصل: <b>{pts}</b>", "sat_next": "{icon} {name} — {n} امتیاز مانده",
    "sat_hint": "امتیاز فصل را با شرکت در باس جهانی، رویدادها و قلمروها می‌گیری. درجه‌ات کنار اسمت نمایش داده می‌شود.",
    "sat_claimed": "🎖️ ارتقا مبارک! +{coins} 🪙 و:", "sat_e_none": "جایزه‌ی ارتقای جدیدی نداری.",
    # ---- inner world ----
    "inr_none": "این هفته به سقف دیدارهای دنیای درونت ({cap}) رسیده‌ای. هفته‌ی بعد برگرد.",
    "inr_intro": "🌌 به دنیای درونت قدم می‌گذاری. دیدار باقی‌مانده این هفته: {left}/{cap}", "inr_blade": "روح تیغه",
    "inr_e_limit": "این هفته دیدار دیگری نداری.", "inr_e_stale": "این صحنه تمام شده.", "inr_e_bad": "انتخاب نامعتبر.",
    "inr_bond": "💞 پیوند با تیغه: +{n}", "inr_buff": "✨ {key} +{pct}٪ تا {m} دقیقه",
    "buff_xp_pct": "XP", "buff_coin_pct": "سکه", "buff_drop_pct": "شانس دراپ",
}

EN = {
    "m_twr": "🗼 Soul Tower", "m_dsp": "🧭 Dispatch", "m_whl": "🎡 Urahara's Wheel", "m_sat": "🎖️ Gotei Seat", "m_inr": "🌌 Inner World",
    "ttl_twr": "Soul Tower", "ttl_dsp": "Dispatch", "ttl_whl": "Urahara's Wheel", "ttl_sat": "Gotei Seat", "ttl_inr": "Inner World",
    "b_tgo": "🗼 Ascend", "b_tlb": "🏅 This week's ranking", "b_dclaim": "🎁 Collect rewards", "b_dsend": "➕ Send a character",
    "b_spin_free": "🎡 Free spin", "b_spin_paid": "🎡 Spin ({cost} 🪙)", "b_sclaim": "🎁 Promotion reward", "b_inr_again": "🌌 Next visit",
    "tw_body": ("The Soul Tower never ends. Every floor is tougher than the last, and every 5th floor a Warden 👑 guards a special reward.\n"
                "HP and reiatsu carry between floors (with a little healing). If you fall, your next run starts at the first floor of that 5-floor block.\n\n"
                "🏆 Best floor: <b>{best}</b>\n📅 This week: <b>{wk}</b>\n🚩 Start floor: <b>{start}</b>\n"
                "⚡ Cost per ascent: {cost} energy\n🎁 Rewarded floors today: {left}/{cap}"),
    "tw_e_busy": "Finish the fight in front of you first.", "tw_e_energy": "Not enough energy ⚡",
    "tw_floor": "🗼 Floor {n}", "tw_floor_boss": "🗼 Floor {n} — 👑 Warden", "tw_floor_n": "Floor {n}",
    "tw_lb": "🏅 Tower's best this week",
    "tw_win": "✅ Floor {n} cleared!\n+{xp} XP, +{coins} 🪙", "tw_nopay": "Today's reward cap is reached, but the floor still counts.",
    "tw_record": "🏆 New record: floor {n}!", "tw_milestone": "🎁 Milestone bonus: +{coins} 🪙",
    "tw_fall": "💀 You fell on floor {n}. Your best: floor {best}.", "tw_next": "➡️ The next floor awaits; your wounds walk with you.",
    "b_tnext": "➡️ Next floor", "b_tretry": "🗼 Ascend again",
    "ch_line": "🔥 Chain ×{n} (+{pct}% rewards)", "ch_lost": "💔 Your {n}-win chain is broken.", "ch_bonus": "🎁 Chain bonus: {item}",
    "ds_body": ("Send your companions on missions; they bring rewards back even while you're offline.\nRoles: {roles}\n\n"
                "Slots: {used}/{slots}"),
    "ds_hours": "{h}h", "ds_pick_m": "Choose a mission:", "ds_pick_c": "Who goes?",
    "ds_nochars": "No free characters. Summon some first.",
    "ds_e_bad": "Invalid choice.", "ds_e_level": "Your level is too low for this mission.", "ds_e_notowned": "You don't own this character.",
    "ds_e_busy": "That character is already away.", "ds_e_slots": "All slots are in use.", "ds_e_none": "No mission has finished yet.",
    "ds_sent": "🧭 Dispatched!", "ds_done": "🎁 Missions complete:",
    "wh_body": "Urahara gives one free spin a day; maybe today is the jackpot!\n\n{prizes}\n\nExtra spin: {cost} 🪙",
    "wh_free": "✨ You have a free spin today.", "wh_extra": "Free spin used. Extra spins left: {n}, {cost} 🪙 each.",
    "wh_none": "That's all for today; come back tomorrow.",
    "wh_e_used": "No spins left today.", "wh_e_limit": "Daily spin limit reached.", "wh_e_funds": "Not enough coins.",
    "sat_now": "Current rank: {icon} <b>{name}</b>\nSeason points: <b>{pts}</b>", "sat_next": "{icon} {name} — {n} points to go",
    "sat_hint": "Earn season points from the world boss, events and territories. Your rank shows next to your name.",
    "sat_claimed": "🎖️ Promoted! +{coins} 🪙 and:", "sat_e_none": "No new promotion reward.",
    "inr_none": "You've used all your Inner World visits this week ({cap}). Come back next week.",
    "inr_intro": "🌌 You step into your inner world. Visits left this week: {left}/{cap}", "inr_blade": "your blade's spirit",
    "inr_e_limit": "No visits left this week.", "inr_e_stale": "That scene has passed.", "inr_e_bad": "Invalid choice.",
    "inr_bond": "💞 Bond with your blade: +{n}", "inr_buff": "✨ {key} +{pct}% for {m} min",
    "buff_xp_pct": "XP", "buff_coin_pct": "Coins", "buff_drop_pct": "Drop rate",
}

"""Environment settings and admin-tunable game defaults."""
import os

# bag slots: what a new player starts with, slots per upgrade, ceiling (BAG_OLD_START is the pre-v2 start, used once by the migration)
BAG_START, BAG_STEP, BAG_MAX, BAG_OLD_START = 100, 20, 300, 50
BAG_PER_LEVEL = 1   # free bag slots for every level a character gains (existing bags get them once in main.migrate_world)


def _int(name, default):
    try:
        return int(str(os.getenv(name, default)).strip())
    except (TypeError, ValueError):
        return default


class Settings:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN", "").strip()
        self.mongodb_uri = os.getenv("MONGODB_URI", "").strip()
        self.database_name = os.getenv("DATABASE_NAME", "senka").strip() or "senka"
        self.owner_id = _int("OWNER_ID", 0)
        self.environment = os.getenv("ENVIRONMENT", "production").strip()
        self.log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        self.hmac_secret = os.getenv("HMAC_SECRET", "").strip()
        self.port = _int("PORT", 8080)
        self.drop_pending = _int("DROP_PENDING_UPDATES", 0) == 1
        # Telegram log channel: "@username" or numeric id (-100...). The bot must be an admin there. Empty = DB-only logging.
        self.notify_updates = _int("NOTIFY_UPDATES", 1) == 1  # message every player to press /start after a new deploy
        self.log_channel = os.getenv("LOG_CHANNEL", "@senkalog").strip()
        # Mandatory join: a player must be a member of the channel and the group before the bot plays with them.
        # The bot must be an admin in both. JOIN_GROUP_ID is the group's numeric id (-100...); an invite link cannot
        # be resolved to it, so until it is set the group is not checked (a warning is logged at start).
        self.join_gate = _int("JOIN_GATE", 1) == 1
        self.join_channel = os.getenv("JOIN_CHANNEL", "@SenkaChannel").strip()
        self.join_channel_url = os.getenv("JOIN_CHANNEL_URL", "https://t.me/SenkaChannel").strip()
        self.join_group_id = _int("JOIN_GROUP_ID", 0)
        self.join_group_url = os.getenv("JOIN_GROUP_URL", "https://t.me/+4rDKHnpMhcFhYTY8").strip()


settings = Settings()

# Starting values. All of them can be overridden live from the admin panel
# (stored in MongoDB `settings` collection, document _id="game").
GAME_DEFAULTS = {
    "butterfly_on": 1, "butterfly_cooldown": 1800, "herald_window": 600,  # Hell Butterfly, Hollow Herald countdown (seconds)
    "maintenance": False,
    "xp_rate": 1.0, "coin_rate": 1.0, "drop_rate": 1.0,
    "div_min_level": 10, "div_change_cost": 3000, "div_k": 1.0,  # allegiance: min level, change price, bonus strength
    "hlf_min_level": 40, "hlf_cost": 15000, "hlf_chance": 0.65,  # Hollowfication ritual (Shinigami -> Visored)
    # world boss feel: bigger numbers, team combos and signature strikes (all live-tunable)
    "boss_dmg_mult": 6.0, "boss_hp_mult": 4.0, "boss_combo_window": 8, "boss_combo_step": 0.05, "boss_combo_cap": 10,
    "boss_special_chance": 0.12, "boss_special_mult": 2.5,
    # burst phase: one hit of at least boss_burst_dmg puts the boss in a special state against that player for
    # boss_burst_seconds. The bar is the larger of boss_burst_dmg and boss_burst_pct of the boss's max HP, so it grows with the boss.
    # mode 1 = the player gets an extra boss_burst_cd seconds of cooldown, 2 = the boss takes
    # (1 - boss_burst_reduce) less damage from that player meanwhile, 3 = both. boss_burst_dmg 0 AND boss_burst_pct 0 = off.
    "boss_burst_dmg": 100000, "boss_burst_pct": 0.10, "boss_burst_announce_gap": 60, "boss_burst_mode": 1, "boss_burst_cd": 20, "boss_burst_seconds": 30, "boss_burst_reduce": 0.5,
    "xp_curve_k": 1.5,  # level-up difficulty: XP needed per level is multiplied by this (live: `set xp_curve_k 2.2`)
    "boss_min_minutes": 45, "boss_max_minutes": 60,  # gap between world bosses (was a fixed 120)
    "boss_duration_minutes": 20, "boss_min_level": 5, "boss_hit_cooldown": 10,
    "energy_max": 100, "explore_cost": 10, "energy_regen_seconds": 300,
    "start_coins": 500, "travel_cooldown": 60,
    "pvp_min_level": 15, "pvp_gain_min": 25, "pvp_gain_max": 40,
    "pvp_loss_min": 20, "pvp_loss_max": 30, "pvp_pair_daily_cap": 3,
    "pvp_full_xp_wins": 10, "pvp_turn_seconds": 30, "pvp_max_turns": 200,
    "market_seller_fee": 0.05, "market_buyer_fee": 0.02, "market_slots": 5,
    "market_hours": 72, "auction_snipe_seconds": 60, "auction_extend_seconds": 120,
    "gacha_cost": 1500, "gacha_pity_legendary": 80, "gacha_pity_rare": 10,
    "dp_daily_cap": 4000,  # dungeon points one player can earn per day (was a fixed 1500)
    "dg_special_on": 1, "dg_special_day_cap": 6,  # dungeon-only special items: on/off, most drops per player per day
    "dp_pity_bronze": 4, "dp_pity_silver": 3, "dp_pity_gold": 3,  # dungeon chests: this many in a row without a better item guarantees one (0 = off)
    "gacha_mythic_cap": 10,  # most Mythic results one player can get from summons, ever (0 = no limit)
    "guild_create_cost": 5000, "guild_min_level": 20, "squad_change_days": 7,
    "minigame_daily_xp_cap": 500, "hollow_daily_xp_cap": 50,
    "referral_reward": 200,
    # ---- shared world (service_worldcore / service_worldstate) ----------------
    "world_threat_drift_hour": 0.8, "world_threat_win": 0.12, "world_threat_boss_kill": 8.0,
    "world_threat_boss_flee": 6.0, "world_threat_dungeon": 1.2,
    "world_stab_hunt": 0.08, "world_stab_decay_hour": 0.5, "world_reishi_hunt": 0.25,
    "world_reishi_craft": 0.4, "world_reishi_decay": 0.10,
    "world_enemy_k": 0.25, "world_drop_k": 0.20, "world_price_k": 0.20, "world_stab_xp_k": 0.10,
    "world_boss_interval_k": 0.40,
    # ---- global boss -----------------------------------------------------------
    "boss_hp_players_ref": 10, "boss_hp_scale_cap": 8.0, "boss_hp_threat_k": 0.5,
    # world boss HP = random base (min..max) x players online right now (seen in the last boss_online_minutes)
    "boss_hp_base_min": 100000, "boss_hp_base_max": 200000, "boss_online_minutes": 15,
    "boss_main_share": 0.003, "boss_pool_cap": 25, "boss_daily_paid": 8,
    "boss_min_age_minutes": 60, "boss_refresh_seconds": 120, "boss_broadcast_cap": 300,
    # ---- world events ------------------------------------------------------------
    "event_enabled": True, "event_min_gap_minutes": 180, "event_duration_minutes": 120,
    "event_goal_per_player": 6, "event_goal_min": 40, "event_goal_cap": 4000,
    # no cap on ordinary event points any more; only dungeon KEYS offered to an event are capped per day, and that cap grows with activity
    "event_key_cap_base": 16, "event_key_cap_step_actions": 300, "event_key_cap_step_pts": 8, "event_key_cap_max": 160,
    "event_reward_xp": 400, "event_reward_coins": 600,
    "event_threat_trigger": 70, "event_stab_trigger": 28, "event_random_chance": 0.10,
    # ---- item roles -----------------------------------------------------------------
    "relic_slots": 2, "relic_k": 1.0, "pet_k": 1.0, "evo_bonus_pct": 0.02, "evo_trial_scale": 1.3,
    "cosmetic_fame_xp": 0.0025, "cosmetic_fame_cap": 0.05, "craft_cost_k": 1.0,
    "temper_max": 5, "temper_def_pct": 0.05, "buff_max_minutes": 180,
    # ---- territories ------------------------------------------------------------------
    "terr_enabled": True, "terr_min_members": 3, "terr_min_level": 10, "terr_min_age_hours": 24,
    "terr_daily_cap": 60, "terr_min_score": 40, "terr_buff_pct": 0.05, "terr_tax_pct": 0.05,
    "terr_tax_daily_cap": 20000,
    # ---- player to player ------------------------------------------------------------------
    "trace_cost": 100, "trace_cooldown": 3600, "trace_max_active": 3, "trace_hours": 24,
    "trace_reward_coins": 60, "trace_find_daily": 10, "trace_owner_xp": 15, "trace_owner_daily": 5,
    "trace_find_chance": 0.25, "grave_cooldown_hours": 6,
    "aid_energy": 20, "aid_xp": 10, "aid_daily_send": 5, "aid_daily_recv": 5, "aid_min_level": 5,
    "bounty_min": 500, "bounty_max_total": 100000, "bounty_fee": 0.10, "bounty_hours": 72,
    "bounty_daily_claims": 3, "bounty_min_level": 15, "presence_minutes": 30,
    # ---- seasons ----------------------------------------------------------------------------
    # ---- retention loops (tower / chain / dispatch / wheel / inner world) -------------------------
    "tower_energy": 10, "tower_daily_floors": 30, "tower_heal": 0.20,
    "raid_min_msgs": 35, "raid_cooldown": 1800, "raid_ttl": 900, "raid_hp": 4000, "raid_menos_chance": 0.2, "raid_menos_mult": 4,
    "raid_daily_cap": 8, "raid_min_level": 3, "raid_strike_cd": 12, "raid_dmg_k": 1.0,
    # --- NEW BLEACH VIRAL SYSTEM ---
    "espada_min_level": 10, "espada_cd": 300, "hog_min_level": 10, "hog_steal_cd_hours": 2,
    "hog_shield_minutes": 30, "hog_pen_hours": 3,
    "hog_rounds": 3, "hog_min_power_ratio": 0.5, "hog_target_lock": 60,  # Hōgyoku duel: best of N, weakest allowed challenger, holder lock (s)
    "type_min_msgs": 45, "type_cooldown": 2400, "type_ttl": 90, "type_daily_cap": 10,
    "quincy_enabled": True, "quincy_interval_hours": 4, "quincy_active_minutes": 30, "quincy_max_groups": 20, "quincy_hp": 6000,
    "quincy_ttl_minutes": 10, "quincy_lock_minutes": 60,
    "znp_train_energy": 10, "znp_train_daily": 10, "znp_train_gain": 5, "znp_mastery_cap": 1000,
    "znp_shikai_level": 20, "znp_shikai_bond": 50, "znp_bankai_level": 60, "znp_bankai_mastery": 150,
    "chain_cap": 10, "chain_step": 0.05, "chain_expire_hours": 12, "chain_bonus_every": 5,
    "chain_shield_min": 10, "chain_shield_hours": 24,  # a long chain survives one loss per window
    "shop_disc_5": 0.05, "shop_disc_10": 0.10, "shop_disc_25": 0.15,  # Urahara bulk-buy discounts
    "dispatch_slots": 3, "dispatch_k": 0.6, "dispatch_time_k": 1.0, "dispatch_energy": 15,
    "wheel_cost": 800, "wheel_extra_daily": 3, "inner_weekly": 3,
    # ---- 100 wheels (Soul Core) ----------------------------------------------------------------
    "wheel2_enabled": True, "wheel_free_daily": 1, "pity_leg": 30, "pity_myth": 90,
    "core_quest_chance": 0.03, "core_dungeon_chance": 0.03, "core_day_cap": 1,
    # ---- group drops, Soul Artifacts, Artifact Exchange, log channel -------------------------------
    "drop_enabled": True, "drop_min_msgs": 30, "drop_min_users": 3, "drop_chance": 0.6, "drop_cooldown_minutes": 60,
    "drop_ttl_seconds": 180, "drop_daily_per_user": 6, "drop_min_level": 3, "drop_artifact_chance": 0.12, "drop_art_pity_hours": 6,
    "drop_player_enabled": True, "drop_player_min_level": 10, "drop_player_min_age_hours": 24, "drop_player_cooldown": 3600,
    "drop_player_daily": 3, "drop_pair_daily": 2,
    "art_k": 1.0, "art_fee": 0.10, "art_price_min": 2000, "art_price_max": 10000000, "art_list_hours": 72,
    "log_enabled": True, "log_nav": False,
    "season_days": 30, "season_soft_reset": 0.25, "season_daily_pts_cap": 400, "season_min_pts": 30,
    "season_top_coins": 50000, "season_part_coin_per_pt": 5, "new_acct_minutes": 60,
    # ---- Guild Quest Board (adventure mode; tables in data_guildquest.py) ------------------------
    "gq_daily": 5, "gq_xp_k": 1.3, "gq_final_xp_mult": 2.0, "gq_coin_base": 300, "gq_coin_rank_k": 0.25,
}


def validate_settings():
    missing = [k for k, v in {"BOT_TOKEN": settings.bot_token,
                              "MONGODB_URI": settings.mongodb_uri,
                              "HMAC_SECRET": settings.hmac_secret}.items() if not v]
    if missing:
        raise RuntimeError("Missing environment variables: " + ", ".join(missing))
    if len(settings.hmac_secret) < 32:
        raise RuntimeError("HMAC_SECRET must contain at least 32 characters.")
    if settings.owner_id <= 0:
        raise RuntimeError("OWNER_ID must be your numeric Telegram user id.")

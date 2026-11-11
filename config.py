"""Environment settings and admin-tunable game defaults."""
import os


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


settings = Settings()

# Starting values. All of them can be overridden live from the admin panel
# (stored in MongoDB `settings` collection, document _id="game").
GAME_DEFAULTS = {
    "maintenance": False,
    "xp_rate": 1.0, "coin_rate": 1.0, "drop_rate": 1.0,
    "boss_min_minutes": 120, "boss_max_minutes": 120,
    "boss_duration_minutes": 20, "boss_min_level": 5, "boss_hit_cooldown": 10,
    "energy_max": 100, "explore_cost": 10, "energy_regen_seconds": 300,
    "start_coins": 500, "travel_cooldown": 60,
    "pvp_min_level": 15, "pvp_gain_min": 25, "pvp_gain_max": 40,
    "pvp_loss_min": 20, "pvp_loss_max": 30, "pvp_pair_daily_cap": 3,
    "pvp_full_xp_wins": 10, "pvp_turn_seconds": 30, "pvp_max_turns": 30,
    "market_seller_fee": 0.05, "market_buyer_fee": 0.02, "market_slots": 5,
    "market_hours": 72, "auction_snipe_seconds": 60, "auction_extend_seconds": 120,
    "gacha_cost": 1500, "gacha_pity_legendary": 80, "gacha_pity_rare": 10,
    "guild_create_cost": 5000, "guild_min_level": 20, "squad_change_days": 7,
    "minigame_daily_xp_cap": 500, "hollow_daily_xp_cap": 50,
    "referral_reward": 200,
    # ---- shared world (service_worldcore / service_worldstate) ----------------
    "world_threat_drift_hour": 0.8, "world_threat_win": 0.12, "world_threat_boss_kill": 8.0,
    "world_threat_boss_flee": 6.0, "world_threat_dungeon": 1.2,
    "world_stab_patrol": 0.08, "world_stab_decay_hour": 0.5, "world_reishi_patrol": 0.25,
    "world_reishi_craft": 0.4, "world_reishi_decay": 0.10,
    "world_enemy_k": 0.25, "world_drop_k": 0.20, "world_price_k": 0.20, "world_stab_xp_k": 0.10,
    "world_boss_interval_k": 0.40,
    # ---- global boss -----------------------------------------------------------
    "boss_hp_players_ref": 10, "boss_hp_scale_cap": 8.0, "boss_hp_threat_k": 0.5,
    "boss_main_share": 0.003, "boss_pool_cap": 25, "boss_daily_paid": 8,
    "boss_min_age_minutes": 60, "boss_refresh_seconds": 120, "boss_broadcast_cap": 300,
    # ---- world events ------------------------------------------------------------
    "event_enabled": True, "event_min_gap_minutes": 180, "event_duration_minutes": 120,
    "event_goal_per_player": 6, "event_goal_min": 40, "event_goal_cap": 4000,
    "event_daily_pts_cap": 150, "event_reward_xp": 400, "event_reward_coins": 600,
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
    "tower_energy": 15, "tower_daily_floors": 30, "tower_heal": 0.20,
    "chain_cap": 10, "chain_step": 0.05, "chain_expire_hours": 12, "chain_bonus_every": 5,
    "dispatch_slots": 3, "dispatch_k": 0.6, "dispatch_time_k": 1.0, "dispatch_energy": 15,
    "wheel_cost": 800, "wheel_extra_daily": 3, "inner_weekly": 3,
    "season_days": 30, "season_soft_reset": 0.25, "season_daily_pts_cap": 400, "season_min_pts": 30,
    "season_top_coins": 50000, "season_part_coin_per_pt": 5, "new_acct_minutes": 60,
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

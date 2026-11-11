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
    "boss_min_minutes": 45, "boss_max_minutes": 45,
    "boss_duration_minutes": 10, "boss_min_level": 5, "boss_hit_cooldown": 10,
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

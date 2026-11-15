"""Owner-only blades. A blade in this list works only for the owner account; everyone else's copy falls back to
the generic release. The list lives in the `settings` document `znp_owner_only` so the owner can change it live
with /znplock. Until that document is written, the built-in default below applies."""
from config import settings
from database import col

DEFAULT_OWNER_ONLY = ["hyorinmaru"]  # Dayguren Hyōrinmaru: kept for the owner


async def owner_only_blades() -> set:
    d = await col("settings").find_one({"_id": "znp_owner_only"}) or {}
    if "ids" in d:
        return set(d.get("ids") or [])
    return set(DEFAULT_OWNER_ONLY)


async def blade_allowed(uid, blade_id) -> bool:
    """True when this player may use the blade (every non-locked blade, or the owner for a locked one)."""
    if not blade_id:
        return True
    if blade_id not in await owner_only_blades():
        return True
    return uid == settings.owner_id


async def set_owner_only(blade_id: str, on: bool) -> None:
    current = await owner_only_blades()
    current = set(current) | {blade_id} if on else set(current) - {blade_id}
    await col("settings").update_one({"_id": "znp_owner_only"}, {"$set": {"ids": sorted(current)}}, upsert=True)

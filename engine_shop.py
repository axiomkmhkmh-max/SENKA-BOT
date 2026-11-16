"""Pure shop maths (no database): quantities offered and the volume discount."""
SHOP_QTYS = (1, 5, 10, 25)


def bulk_discount(qty: int, st: dict) -> float:
    """Volume discount for Urahara's shop: the biggest tier whose quantity the order reaches (capped at 90%)."""
    pct = 0.0
    for q, key in ((5, "shop_disc_5"), (10, "shop_disc_10"), (25, "shop_disc_25")):
        if qty >= q:
            pct = max(pct, float(st.get(key, 0)))
    return min(max(pct, 0.0), 0.9)

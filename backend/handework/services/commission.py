import json
import os
from decimal import Decimal


def commission_bps(service=None, shop=False):
    default = int(os.getenv("PLATFORM_FEE_BPS", "1200"))
    override = int(os.getenv("SHOP_FEE_BPS", str(default))) if shop else json.loads(os.getenv("SERVICE_FEE_BPS_JSON","{}")).get(service, default)
    promo = json.loads(os.getenv("PROMOTIONAL_FEE_BPS_JSON","{}")).get("shop" if shop else service, override)
    if any(type(rate) is not int or not 0 <= rate <= 10000 for rate in (default, override, promo)):
        raise ValueError("Invalid commission configuration")
    return min(promo, override)


def commission(amount, bps):
    return (amount * Decimal(bps) / Decimal(10000)).quantize(Decimal("0.01"))

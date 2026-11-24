import os
import secrets
from decimal import Decimal
from flask import Blueprint, jsonify, request
from ..extensions import db, limiter
from ..models import Role, ShopOrder, ShopOrderItem
from ..security import current_user, role_required
from ..services.paystack import Paystack
from ..services.shop_catalog import PRODUCTS

bp = Blueprint("shop", __name__)


def published_products():
    confirmed = {item.strip() for item in os.getenv("SHOP_PUBLISHED_PRODUCT_IDS", "").split(",")}
    return {key: value for key, value in PRODUCTS.items() if key in confirmed}


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"))


@bp.get("/shop/products")
def products():
    return jsonify({"items": [{"id": key, **{**value, "price": float(value["price"])}} for key, value in published_products().items()]})


@bp.get("/shop/orders")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def orders():
    user = current_user()
    query = ShopOrder.query.order_by(ShopOrder.created_at.desc())
    if user.role != Role.ADMIN:
        query = query.filter_by(buyer_id=user.id)
    return jsonify({"items": [order.public() for order in query.limit(100).all()]})


@bp.get("/shop/orders/<reference>")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def order(reference):
    user = current_user()
    query = ShopOrder.query.filter_by(reference=reference)
    if user.role != Role.ADMIN:
        query = query.filter_by(buyer_id=user.id)
    return jsonify({"order": query.first_or_404().public()})


@bp.post("/shop/orders/<reference>/verify")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
def verify_order(reference):
    user = current_user()
    query = ShopOrder.query.filter_by(reference=reference).with_for_update()
    if user.role != Role.ADMIN:
        query = query.filter_by(buyer_id=user.id)
    order = query.first_or_404()
    if order.status in {"refunded", "paid"}:
        return jsonify({"order": order.public()})
    try:
        provider = Paystack().verify_transaction(order.provider_reference or order.reference)
    except Exception:
        return jsonify({"message": "Payment verification is temporarily unavailable", "code": "verification_unavailable"}), 502
    data = provider.get("data") or {}
    expected_amount = int(round(float(order.total) * 100))
    if data.get("status") == "success" and data.get("amount") == expected_amount and data.get("currency") == order.currency:
        from datetime import datetime, timezone
        order.status = "paid"
        order.paid_at = order.paid_at or datetime.now(timezone.utc)
        order.provider_payload = provider
        db.session.commit()
        return jsonify({"order": order.public()})
    order.provider_payload = provider
    db.session.commit()
    return jsonify({"order": order.public(), "message": "Payment has not been confirmed yet"}), 202


@bp.post("/shop/orders")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
@limiter.limit("8 per minute")
def create_order():
    user = current_user()
    data = request.get_json(silent=True) or {}
    requested = data.get("items") or []
    if not requested:
        return jsonify({"message": "Your cart is empty", "code": "empty_cart"}), 422

    normalised = []
    subtotal = Decimal("0.00")
    catalog = published_products()
    if not isinstance(requested, list) or any(not isinstance(row, dict) for row in requested):
        return jsonify({"message": "Invalid cart"}), 422
    for row in requested:
        product_id = str(row.get("product_id") or "").strip()
        product = catalog.get(product_id)
        try:
            quantity = int(row.get("quantity") or 0)
        except (TypeError, ValueError):
            quantity = 0
        if not product or quantity < 1 or quantity > 20:
            return jsonify({"message": "One or more cart items are invalid", "code": "invalid_cart"}), 422
        line_total = (product["price"] * quantity).quantize(Decimal("0.01"))
        subtotal += line_total
        normalised.append((product_id, product, quantity, line_total))

    fulfilment = str(data.get("fulfilment") or "delivery").lower()
    if fulfilment not in {"delivery", "pickup"}:
        return jsonify({"message": "Choose delivery or office pickup", "code": "invalid_fulfilment"}), 422

    full_name = str(data.get("full_name") or "").strip()[:160]
    phone = str(data.get("phone") or user.phone or "").strip()[:32]
    email = str(data.get("email") or user.email or "").strip().lower()[:254]
    area = str(data.get("area") or "").strip()[:140]
    address = str(data.get("address") or "").strip()[:500]
    if not full_name or not phone or not email:
        return jsonify({"message": "Name, phone and email are required", "code": "missing_contact"}), 422
    if fulfilment == "delivery" and (not area or not address):
        return jsonify({"message": "Delivery area and address are required", "code": "missing_delivery_address"}), 422

    delivery_fee = money(os.getenv("SHOP_DELIVERY_FEE_GHS", "35")) if fulfilment == "delivery" else Decimal("0.00")
    total = (subtotal + delivery_fee).quantize(Decimal("0.01"))
    reference = f"HEW-SHOP-{secrets.token_hex(6).upper()}"
    pickup_note = os.getenv("SHOP_PICKUP_NOTE", "Pickup location and collection window will be confirmed after payment.") if fulfilment == "pickup" else None

    order = ShopOrder(
        reference=reference,
        buyer_id=user.id,
        status="pending_payment",
        currency="GHS",
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total=total,
        fulfilment=fulfilment,
        full_name=full_name,
        phone=phone,
        email=email,
        area=area or None,
        address=address or None,
        pickup_note=pickup_note,
        provider_reference=reference,
    )
    db.session.add(order)
    db.session.flush()
    for product_id, product, quantity, line_total in normalised:
        db.session.add(ShopOrderItem(
            order_id=order.id,
            product_id=product_id,
            product_name=product["name"],
            category=product["category"],
            unit_price=product["price"],
            quantity=quantity,
            line_total=line_total,
        ))

    callback_base = os.getenv("PUBLIC_WEB_URL", "http://localhost:3000").rstrip("/")
    callback_url = f"{callback_base}/shop?shop_order={reference}"
    try:
        provider = Paystack().initialize_transaction(
            email=email,
            amount_ghs=total,
            reference=reference,
            callback_url=callback_url,
            metadata={"kind": "shop_order", "order_reference": reference, "buyer_id": user.id, "fulfilment": fulfilment},
        )
    except Exception:
        db.session.rollback()
        return jsonify({"message": "Payment checkout could not be started. Check PAYSTACK_SECRET_KEY and try again.", "code": "provider_unavailable"}), 502

    order.provider_payload = provider
    db.session.commit()
    provider_data = provider.get("data") or {}
    return jsonify({
        "order": order.public(),
        "authorization_url": provider_data.get("authorization_url"),
        "access_code": provider_data.get("access_code"),
    }), 201

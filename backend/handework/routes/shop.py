import os
from datetime import datetime, timezone
from uuid import UUID, uuid5
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from flask import Blueprint, current_app, jsonify, request
from ..extensions import db, limiter
from ..models import AuditLog, FileAsset, Role, ShopOrder, ShopOrderItem, ShopProductMedia
from ..security import current_user, role_required
from ..services.paystack import Paystack, checkout_enabled, checkout_url
from .payments import verify_charge
from ..services.commission import commission, commission_bps
from ..services.shop_catalog import PRODUCTS
from ..services.storage import upload_file, metadata_for, private_download_url, delete_object

bp = Blueprint("shop", __name__)


def published_products():
    confirmed = {item.strip() for item in os.getenv("SHOP_PUBLISHED_PRODUCT_IDS", "").split(",")}
    return {key: value for key, value in PRODUCTS.items() if key in confirmed}


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"))


@bp.get("/shop/products")
def products():
    images={row.product_id:row.file_asset_id for row in ShopProductMedia.query.all()}
    assets={asset.id:asset for asset in FileAsset.query.filter(FileAsset.id.in_(list(images.values()))).all()} if images else {}
    return jsonify({"items": [{"id": key, **{**value, "price": float(value["price"])},"image":private_download_url(assets[images[key]].url,300) if key in images and images[key] in assets else None} for key, value in published_products().items()]})


@bp.get("/admin/shop-media")
@role_required(Role.ADMIN)
def shop_media():
    rows=ShopProductMedia.query.order_by(ShopProductMedia.product_id).all()
    items=[]
    for row in rows:
        asset=db.session.get(FileAsset,row.file_asset_id)
        if asset and not asset.deleted_at: items.append({"product_id":row.product_id,"file_asset_id":asset.id,"image_url":private_download_url(asset.url,300)})
    return jsonify({"items":items})


@bp.put("/admin/shop-products/<product_id>/image")
@role_required(Role.ADMIN)
def put_shop_image(product_id):
    if product_id not in PRODUCTS: return jsonify({"message":"Unknown shop product"}),404
    previous=ShopProductMedia.query.filter_by(product_id=product_id).first()
    try:
        stored=upload_file(request.files.get("file"),current_user().id,"shop_image",private=True)
        asset=FileAsset(owner_id=current_user().id,purpose="shop_image",**metadata_for(stored));db.session.add(asset);db.session.flush()
        if previous:
            old_asset=db.session.get(FileAsset,previous.file_asset_id);previous.file_asset_id=asset.id
            if old_asset:
                asset.replaces_asset_id = old_asset.id
                old_asset.deleted_at = datetime.now(timezone.utc)
        else:
            old_asset=None;db.session.add(ShopProductMedia(product_id=product_id,file_asset_id=asset.id))
        db.session.add(AuditLog(actor_id=current_user().id,action="shop.image.upload",entity_type="shop_product",entity_id=product_id,after={"asset_id":asset.id,"sha256":asset.sha256}));db.session.commit()
    except ValueError as error:
        db.session.rollback()
        if "stored" in locals():
            try: delete_object(stored.url)
            except Exception: current_app.logger.exception("Invalid shop image cleanup failed")
        return jsonify({"message":str(error)}),422
    except RuntimeError as error:
        db.session.rollback()
        if "stored" in locals():
            try: delete_object(stored.url)
            except Exception: current_app.logger.exception("Failed shop image cleanup failed")
        return jsonify({"message":str(error)}),503
    except Exception:
        db.session.rollback()
        if "stored" in locals():
            try: delete_object(stored.url)
            except Exception: current_app.logger.exception("Shop image transaction cleanup failed")
        raise
    if old_asset:
        try: delete_object(old_asset.url)
        except Exception: current_app.logger.exception("Replaced shop image cleanup failed")
    return jsonify({"product_id":product_id,"image_url":private_download_url(asset.url,300)}),201


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
    verify_charge(order)
    db.session.commit()
    return jsonify(order=order.public()), 200 if order.status == "paid" else 202


@bp.post("/shop/orders")
@role_required(Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
@limiter.limit("8 per minute")
def create_order():
    user = current_user()
    data = request.get_json(silent=True) or {}
    if not checkout_enabled(user):
        return jsonify(message="Payments are disabled"), 503
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
    key = request.headers.get("Idempotency-Key", "")
    if not 1 <= len(key) <= 100:
        return jsonify(message="Idempotency-Key required"), 400
    reference = "HEW-SHOP-" + uuid5(UUID(user.id), key).hex[:23]
    existing = ShopOrder.query.filter_by(reference=reference).with_for_update().first()
    if existing:
        prior=[(i.product_id,i.quantity) for i in ShopOrderItem.query.filter_by(order_id=existing.id)]
        if (sorted(prior)!=sorted((i[0],i[2]) for i in normalised) or existing.total!=total or existing.fulfilment!=fulfilment
                or (existing.full_name,existing.phone,existing.email,existing.area or "",existing.address or "")!=(full_name,phone,email,area,address)):
            return jsonify(message="Checkout key belongs to a different order"),409
        return jsonify(order=existing.public(), authorization_url=(existing.provider_payload or {}).get("authorization_url")), 200
    pickup_note = os.getenv("SHOP_PICKUP_NOTE", "Pickup location and collection window will be confirmed after payment.") if fulfilment == "pickup" else None

    order = ShopOrder(
        reference=reference,
        buyer_id=user.id,
        status="pending_payment",
        currency="GHS",
        platform_fee=commission(subtotal, commission_bps(shop=True)),
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
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return jsonify(message="Checkout already requested"), 409
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

    db.session.commit()
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

    result = provider.get("data") or {}
    if result.get("reference") != reference or not checkout_url(result):
        return jsonify(message="Checkout requires reconciliation"), 502
    order.provider_payload = {"authorization_url": checkout_url(result)}
    db.session.commit()
    provider_data = provider.get("data") or {}
    return jsonify({
        "order": order.public(),
        "authorization_url": provider_data.get("authorization_url"),
        "access_code": provider_data.get("access_code"),
    }), 201

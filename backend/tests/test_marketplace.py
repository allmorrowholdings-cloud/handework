def test_distance_search_returns_only_verified_available(client,artisan):
    response=client.get("/v1/artisans/search?service=plumb&coordinates=5.56,-0.18&distance_km=10")
    assert response.status_code==200
    items=response.get_json()["items"]
    assert len(items)==1
    assert items[0]["id"]==artisan["profile_id"]
    assert items[0]["verified"] is True
    assert items[0]["distance_km"]<2


def test_unknown_service_has_no_fake_results(client,artisan):
    response=client.get("/v1/artisans/search?service=spaceship+pilot&coordinates=5.56,-0.18")
    assert response.status_code==200
    assert response.get_json()["items"]==[]


def test_artisan_submits_private_payout_name_check(client,artisan):
    response=client.post("/v1/artisans/me/verifications",data={"kind":"payout_name","value":"Kojo Test"},headers=artisan["headers"])
    assert response.status_code==201
    checks=client.get("/v1/artisans/me/verifications",headers=artisan["headers"]).get_json()["items"]
    assert checks[0]["kind"]=="payout_name"
    assert "file_url" not in checks[0]


def test_search_returns_float_coordinates_for_map_markers(client, artisan):
    response = client.get("/v1/artisans/search?service=plumb&coordinates=5.556,-0.182")
    assert response.status_code == 200
    item = response.get_json()["items"][0]
    assert item["latitude"] == 5.556
    assert item["longitude"] == -0.182


def test_search_rejects_non_numeric_distance(client):
    response = client.get("/v1/artisans/search?service=Plumbing&distance_km=nearby")
    assert response.status_code == 422


def test_published_course_is_listed_only_for_approved_provider(client, app):
    from handework.extensions import db
    from handework.models import Course, TrainingProvider
    with app.app_context():
        provider = TrainingProvider(name="Test College", institution_type="tvet", verification_status="approved")
        db.session.add(provider); db.session.flush()
        course = Course(provider_id=provider.id, title="Test plumbing", trade="Plumbing", delivery_mode="in_person", published=True)
        db.session.add(course); db.session.commit()
    response = client.get("/v1/training/courses")
    assert response.status_code == 200
    assert response.get_json()["items"][0]["provider"] == "Test College"


def test_guest_problem_search_without_coordinates(client, artisan, monkeypatch):
    monkeypatch.setattr("handework.routes.marketplace.geocode", lambda location: None)
    result = client.get("/v1/artisans/search", query_string={
        "service": "My tap is leaking", "location": "Osu, Accra"
    }).get_json()
    assert [person["id"] for person in result["items"]] == [artisan["profile_id"]]
    assert result["meta"]["coordinates_used"] is False
    assert not client.get("/v1/artisans/search?location=Tamale").json["items"]


def test_shop_only_lists_confirmed_products(client, monkeypatch):
    from handework.services.shop_catalog import PRODUCTS
    monkeypatch.delenv("SHOP_PUBLISHED_PRODUCT_IDS", raising=False)
    assert client.get("/v1/shop/products").json == {"items": []}
    selected = next(iter(PRODUCTS))
    monkeypatch.setenv("SHOP_PUBLISHED_PRODUCT_IDS", selected)
    assert [row["id"] for row in client.get("/v1/shop/products").json["items"]] == [selected]

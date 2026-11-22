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

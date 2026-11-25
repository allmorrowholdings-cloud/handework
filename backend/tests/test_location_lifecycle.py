import pytest
from handework.models import Booking
from handework.extensions import db
from handework.services import maps


def test_location_to_dispatch_and_private_route(client, artisan, customer, monkeypatch):
    calls=[]
    def fetch(url,params):
        calls.append((url,params))
        if url.endswith("/search"):
            return [{"lat":"5.556","lon":"-0.182","display_name":"Osu, Accra"}]
        if url.endswith("/reverse"):
            return {"lat":"5.556","lon":"-0.182","display_name":"Osu, Accra"}
        return {"routes":[{"distance":1011,"duration":174,"geometry":{"type":"LineString","coordinates":[[-.183,5.559],[-.182,5.556]]}}]}
    monkeypatch.setattr(maps,"fetch",fetch)
    monkeypatch.setenv("GEOCODING_PROVIDER","nominatim")
    monkeypatch.setenv("NOMINATIM_BASE_URL","https://location.example.test")
    monkeypatch.setenv("OSRM_BASE_URL","https://routes.example.test")
    monkeypatch.setenv("ROUTING_PROVIDER","osrm")
    pin=client.get("/v1/locations/search?q=Osu").json["items"][0]
    gps=f"{pin['lat']},{pin['lon']}"
    assert client.get("/v1/locations/reverse",query_string={"coordinates":gps}).json["items"][0]["label"]=="Osu, Accra"
    assert client.patch("/v1/artisans/me",headers=artisan["headers"],json={"latitude":5.559,"longitude":-.183,"radius_km":8}).status_code==200
    assert client.get("/v1/artisans/search",query_string={"service":"Plumbing","coordinates":gps}).json["items"][0]["distance_km"]>0
    assert not client.get("/v1/artisans/search?coordinates=6.5,-0.2").json["items"]
    payload={"service":"Plumbing","description":"Repair tap","address":"Osu, Accra","area":"Osu","city":"Accra","contact_phone":"0244000001","coordinates":gps,"smart_dispatch":True}
    booking=client.post("/v1/bookings",json=payload,headers=customer["headers"]).json
    assert booking["artisan"]["id"]==artisan["profile_id"]
    assert float(db.session.get(Booking,booking["id"]).latitude)==pin["lat"]
    path="/v1/bookings/"+booking["id"]+"/route"
    assert client.get(path).status_code==401
    route=client.get(path,headers=customer["headers"]).json
    assert route["distance_m"]==1011 and route["duration_s"]==174 and route["geometry"]["type"]=="LineString"
    assert calls[-1][0].startswith("https://routes.example.test/route/v1/driving/")


def test_missing_provider_and_unknown_distances(client,artisan,monkeypatch):
    monkeypatch.setenv("GEOCODING_PROVIDER","nominatim")
    monkeypatch.setenv("NOMINATIM_BASE_URL","https://nominatim.openstreetmap.org")
    assert client.get("/v1/locations/search?q=Accra").status_code==503
    assert client.get("/v1/artisans/search?service=Plumbing").json["items"][0]["distance_km"] is None
    assert client.get("/v1/locations/reverse?coordinates=nan,0").status_code==422
    assert client.patch("/v1/artisans/me",headers=artisan["headers"],json={"latitude":95,"longitude":0}).status_code==422

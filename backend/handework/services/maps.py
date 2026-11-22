import os
import httpx


def geocode(query, country="GH"):
    token = os.getenv("MAPBOX_SECRET_TOKEN")
    if not token: return None
    response = httpx.get("https://api.mapbox.com/search/geocode/v6/forward", params={"q": query, "country": country, "limit": 1, "access_token": token}, timeout=15)
    response.raise_for_status(); features = response.json().get("features", [])
    if not features: return None
    coordinates = features[0]["geometry"]["coordinates"]
    return float(coordinates[1]), float(coordinates[0])


def route_distance_km(origin, destination, profile="mapbox/driving"):
    token = os.getenv("MAPBOX_SECRET_TOKEN")
    if not token: return None
    coordinates = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    response = httpx.get(f"https://api.mapbox.com/directions/v5/{profile}/{coordinates}", params={"overview": "false", "access_token": token}, timeout=15)
    response.raise_for_status(); routes = response.json().get("routes", [])
    return routes[0]["distance"] / 1000 if routes else None

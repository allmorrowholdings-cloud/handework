"""OSM geocoding and directions. Provider URLs and credentials are server-owned."""
import os
from math import isfinite
from urllib.parse import urlsplit
import httpx


class LocationUnavailable(Exception):
    pass


def point(latitude, longitude):
    try:
        lat, lon = float(latitude), float(longitude)
        if isfinite(lat) and isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    except (TypeError, ValueError):
        pass
    raise ValueError("Invalid WGS84 coordinates")


def fetch(url, params):
    try:
        response = httpx.get(url, params=params, timeout=8, headers={"User-Agent":"handEwork/1.0"})
        response.raise_for_status()
        return response.json()
    except (ValueError, httpx.HTTPError):
        raise LocationUnavailable("Location provider is temporarily unavailable") from None


def endpoint(name):
    base = os.getenv(name, "").rstrip("/")
    host = urlsplit(base).hostname
    if not host or host in {"nominatim.openstreetmap.org","router.project-osrm.org","routing.openstreetmap.de"}:
        raise LocationUnavailable("Configure a hosted or private location service")
    return base


def places(query=None, coordinates=None, country="gh"):
    provider = os.getenv("GEOCODING_PROVIDER","geoapify" if os.getenv("GEOAPIFY_API_KEY") else "nominatim")
    reverse = coordinates is not None
    if provider == "nominatim":
        base = endpoint("NOMINATIM_BASE_URL")
        params = {"format":"jsonv2","addressdetails":1}
        if reverse:
            result = fetch(base+"/reverse", {**params,"lat":coordinates[0],"lon":coordinates[1]})
            rows = [result] if result.get("lat") else []
        else:
            rows = fetch(base+"/search",{**params,"q":query,"countrycodes":country.lower(),"limit":5})
        return [{"label":r["display_name"],"lat":float(r["lat"]),"lon":float(r["lon"])} for r in rows]
    if provider == "geoapify" and os.getenv("GEOAPIFY_API_KEY"):
        params = {"apiKey":os.environ["GEOAPIFY_API_KEY"],"format":"json"}
        params.update({"lat":coordinates[0],"lon":coordinates[1]} if reverse else {"text":query,"filter":"countrycode:"+country.lower(),"limit":5})
        name = "reverse" if reverse else "search"
        rows = fetch("https://api.geoapify.com/v1/geocode/"+name,params).get("results",[])
        return [{"label":r["formatted"],"lat":r["lat"],"lon":r["lon"]} for r in rows]
    if provider == "mapbox" and os.getenv("MAPBOX_SECRET_TOKEN"):
        params = {"access_token":os.environ["MAPBOX_SECRET_TOKEN"],"permanent":"true"}
        params.update({"latitude":coordinates[0],"longitude":coordinates[1]} if reverse else {"q":query,"country":country,"limit":5})
        rows = fetch("https://api.mapbox.com/search/geocode/v6/"+("reverse" if reverse else "forward"),params)["features"]
        return [{"label":r["properties"]["full_address"],"lon":r["geometry"]["coordinates"][0],"lat":r["geometry"]["coordinates"][1]} for r in rows]
    raise LocationUnavailable("Geocoding provider requires configuration")


def geocode(query, country="GH"):
    try:
        rows = places(query=query,country=country)
        return point(rows[0]["lat"],rows[0]["lon"]) if rows else None
    except LocationUnavailable:
        return None  # Area/city discovery remains available, with distance unknown.


def driving_route(origin, destination):
    provider = os.getenv("ROUTING_PROVIDER","geoapify" if os.getenv("GEOAPIFY_API_KEY") else "osrm")
    coords = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    if provider=="geoapify" and os.getenv("GEOAPIFY_API_KEY"):
        rows = fetch("https://api.geoapify.com/v1/routing",{"waypoints":f"{origin[0]},{origin[1]}|{destination[0]},{destination[1]}",
                                                            "mode":"drive","apiKey":os.environ["GEOAPIFY_API_KEY"]}).get("features",[])
        if rows:
            row=rows[0]
            return {"geometry":row["geometry"],"distance_m":row["properties"]["distance"],"duration_s":row["properties"]["time"],"provider":"Geoapify"}
    elif provider in {"osrm","mapbox"}:
        params={"overview":"full","geometries":"geojson"}
        if provider=="mapbox":
            if not os.getenv("MAPBOX_SECRET_TOKEN"):
                raise LocationUnavailable("Mapbox directions require a configured token")
            url="https://api.mapbox.com/directions/v5/mapbox/driving/"
            params["access_token"]=os.environ["MAPBOX_SECRET_TOKEN"]
        else:
            url=endpoint("OSRM_BASE_URL")+"/route/v1/driving/"
        rows=fetch(url+coords,params).get("routes",[])
        if rows:
            row=rows[0]
            return {"geometry":row["geometry"],"distance_m":row["distance"],"duration_s":row["duration"],"provider":provider}
    return None


def route_distance_km(origin, destination, profile=None):
    route = driving_route(origin,destination)
    return route["distance_m"]/1000 if route else None

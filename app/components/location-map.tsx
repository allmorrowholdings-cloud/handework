"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Map as MapLibreMap, Marker } from "maplibre-gl";
import type { LineString, MultiLineString } from "geojson";

export type MapPoint = {
  id: string;
  display_name: string;
  trade?: string;
  latitude?: number | null;
  longitude?: number | null;
};
export type RouteGeometry = LineString | MultiLineString;

type Props = {
  items: MapPoint[];
  coordinates?: string;
  onPick?: (lat: number, lon: number) => void;
  route?: RouteGeometry;
};

function validPoint(lat: number, lon: number) {
  return Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
}

function mapCenter(coordinates: string, items: MapPoint[]) {
  const parts = coordinates.split(",").map(Number);
  if (parts.length === 2 && validPoint(parts[0], parts[1])) {
    return {lat: parts[0], lon: parts[1]};
  }
  const first = items.find(item => item.latitude != null && item.longitude != null && validPoint(item.latitude, item.longitude));
  return first ? {lat: first.latitude!, lon: first.longitude!} : {lat: 7.9, lon: -1.1};
}

function EmbeddedMap({items, coordinates}: Props) {
  const center = mapCenter(coordinates ?? "", items);
  const bbox = [center.lon - 0.19, center.lat - 0.12, center.lon + 0.19, center.lat + 0.12].join(",");
  const src = `https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(bbox)}&layer=mapnik&marker=${encodeURIComponent(`${center.lat},${center.lon}`)}`;

  return (
    <div className="hw-osm-primary">
      <iframe title="Location map" src={src} loading="lazy" referrerPolicy="strict-origin-when-cross-origin" />

    </div>
  );
}

const geoapifyKey = process.env.NEXT_PUBLIC_GEOAPIFY_API_KEY;
const styleUrl = geoapifyKey
  ? `https://maps.geoapify.com/v1/styles/osm-bright/style.json?apiKey=${geoapifyKey}`
  : process.env.NEXT_PUBLIC_MAP_STYLE_URL || "https://tiles.openfreemap.org/styles/liberty";

function InteractiveMap({items,coordinates="",onPick,route}: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const pickRef = useRef(onPick);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => { pickRef.current = onPick; }, [onPick]);
  useEffect(() => {
    let cancelled = false;
    let map: MapLibreMap | null = null;
    setReady(false);
    setFailed(false);
    void import("maplibre-gl").then(lib => {
      if (cancelled || !container.current) return;
      map = new lib.Map({container: container.current,style: styleUrl, center: [-1.1, 7.9], zoom: 5});
      mapRef.current = map;
      map.addControl(new lib.NavigationControl(), "top-right");
      map.on("click", event => pickRef.current?.(event.lngLat.lat, event.lngLat.lng));
      map.on("load", () => { if (!cancelled) { setReady(true); setFailed(false); } });
      map.on("error", event => {
        console.warn("handEwork map resource error", event.error?.message);
        if (!cancelled && !map?.isStyleLoaded()) setFailed(true);
      });
    }).catch(() => { if (!cancelled) setFailed(true); });
    return () => { cancelled = true; map?.remove(); mapRef.current = null; };
  }, [attempt]);
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    let cancelled = false;
    const markers: Marker[] = [];
    void import("maplibre-gl").then(lib => {
      if (cancelled) return;
      const bounds = new lib.LngLatBounds();
      function add(lat:number,lon:number,title:string) {
        if (!validPoint(lat,lon)) return;
        const marker = new lib.Marker({color: "#da6620"}).setLngLat([lon,lat]).setPopup(new lib.Popup().setText(title)).addTo(map!);
        markers.push(marker);
        bounds.extend([lon,lat]);
      }
      for (const item of items) if (item.latitude != null && item.longitude != null) add(item.latitude,item.longitude,[item.display_name,item.trade].filter(Boolean).join(" · "));
      const xy = coordinates.split(",").map(Number);
      if (xy.length === 2 && validPoint(xy[0],xy[1])) add(xy[0],xy[1],"Selected location");
      if (map.getLayer("job-route")) map.removeLayer("job-route");
      if (map.getSource("job-route")) map.removeSource("job-route");
      if (route) {
        map.addSource("job-route", {type:"geojson",data:{type:"Feature",properties:{},geometry:route}});
        map.addLayer({id:"job-route",type:"line",source:"job-route",paint:{"line-width":5,"line-color":"#da6620"}});
        const lines = route.type === "LineString" ? [route.coordinates] : route.coordinates;
        lines.forEach(line => line.forEach(point => bounds.extend([point[0],point[1]])));
      }
      if (!bounds.isEmpty()) map.fitBounds(bounds,{padding:44,maxZoom:15,duration:0});
    });
    return () => {cancelled=true;markers.forEach(marker=>marker.remove());};
  }, [ready,coordinates,items,route]);
  if (failed) {
    return <div className="hw-interactive-map-recovery">
      <EmbeddedMap items={items} coordinates={coordinates}/>
      {onPick && <p>Pin selection is temporarily unavailable. Use GPS or enter the location manually.</p>}
      <button type="button" onClick={() => setAttempt(value=>value+1)}>Try interactive map</button>
    </div>;
  }
  return <div ref={container} className="real-map" style={{minHeight:290}} aria-label="Interactive map" />;
}

export function LocationMap(props: Props) {
  const [pinsVisible, setPinsVisible] = useState(false);
  const mappedCount = useMemo(() => props.items.filter(item => item.latitude != null && item.longitude != null && validPoint(item.latitude,item.longitude)).length, [props.items]);
  // Do not replace click-to-select job pins or route geometry with a read-only iframe.
  if (props.onPick || props.route) return <InteractiveMap {...props}/>;
  return <div className="hw-map-experience">
    {pinsVisible && mappedCount ? <InteractiveMap {...props}/> : <EmbeddedMap {...props}/>}
    {mappedCount > 0 && <button type="button" className="hw-map-pins-switch" aria-pressed={pinsVisible} onClick={() => setPinsVisible(value=>!value)}>{pinsVisible ? "Show street map" : `Show ${mappedCount} professional ${mappedCount === 1 ? "pin" : "pins"}`}</button>}
  </div>;
}

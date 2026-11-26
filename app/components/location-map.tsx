"use client";
import { useEffect, useRef, useState } from "react";
import type { Map as InteractiveMap, Marker } from "maplibre-gl";
import type { LineString, MultiLineString } from "geojson";
export type MapPoint={id:string;display_name:string;trade?:string;latitude?:number|null;longitude?:number|null};
export type RouteGeometry=LineString|MultiLineString;
// HANDEWORK_GEOAPIFY_MAP_2026
// Geoapify free tier permits commercial use with visible attribution.
// A browser key is intentionally public; restrict its domains in Geoapify.
const geoapifyKey = process.env.NEXT_PUBLIC_GEOAPIFY_API_KEY?.trim();
const styleUrl = geoapifyKey
  ? `https://maps.geoapify.com/v1/styles/osm-bright-smooth/style.json?apiKey=${encodeURIComponent(geoapifyKey)}`
  : null;

export function LocationMap({items,coordinates="",onPick,route}:{items:MapPoint[];coordinates?:string;onPick?:(lat:number,lon:number)=>void;route?:RouteGeometry}){
  const container=useRef<HTMLDivElement>(null);
  const instance=useRef<InteractiveMap|null>(null);
  const pick=useRef(onPick);
  const [ready,setReady]=useState(false);
  const [error,setError]=useState("");
  const [fallback,setFallback]=useState(false);
  const [retry,setRetry]=useState(0);
  useEffect(()=>{pick.current=onPick},[onPick]);
  useEffect(()=>{
    let disposed=false;
    setReady(false);
    setError("");
    setFallback(false);
    // A viewable fallback works before an API key is configured; never reuse
    // an unreliable or unauthorized public tile endpoint automatically.
    if (!styleUrl) {
      setFallback(true);
      setError("Interactive professional pins will be available after the Geoapify map key is configured.");
      return;
    }
    void import("maplibre-gl").then(lib=>{
      if(disposed||!container.current)return;
      const map=new lib.Map({container:container.current,style:styleUrl,center:[-1.1,7.9],zoom:5});
      instance.current=map;
      map.addControl(new lib.NavigationControl(),"top-right");
      map.on("click",e=>pick.current?.(e.lngLat.lat,e.lngLat.lng));
      let initialLoadCompleted = false;
      map.on("load", () => {
        if (disposed) return;
        initialLoadCompleted = true;
        setFallback(false);
        setReady(true);
        setError("");
      });
      map.on("error", event => {
        if (disposed) return;

        console.warn(
          "handEwork map resource error",
          event.error?.message
        );

        if (!initialLoadCompleted) {
          setError("The primary map provider is unavailable. Showing a backup map.");
          setFallback(true);
        } else {
          // A single failed tile does not mean the loaded map is unusable.
          setError("");
        }
      });
      map.on("idle", () => {
        if (!disposed && map.areTilesLoaded() && map.isStyleLoaded()) {
          setError("");
        }
      });
    }).catch(() => {
      if (!disposed) {
        setError("The primary map provider is unavailable. Showing a backup map.");
        setFallback(true);
      }
    });
    return ()=>{disposed=true;instance.current?.remove();instance.current=null};
  },[retry]);
  useEffect(()=>{
    const map=instance.current;
    if(!ready||!map)return;
    let disposed=false;const markers:Marker[]=[];
    void import("maplibre-gl").then(lib=>{
      if(disposed)return;
      const bounds=new lib.LngLatBounds();
      const add=(lon:number,lat:number,label:string)=>{
        const marker=new lib.Marker({color:"#d8541b"}).setLngLat([lon,lat]).setPopup(new lib.Popup().setText(label)).addTo(map);
        markers.push(marker);bounds.extend([lon,lat]);
      };
      for(const p of items)if(p.latitude!=null&&p.longitude!=null)add(p.longitude,p.latitude,[p.display_name,p.trade].filter(Boolean).join(" ? "));
      const xy=coordinates.split(",").map(Number);
      if(xy.length===2&&xy.every(Number.isFinite)&&Math.abs(xy[0])<=90&&Math.abs(xy[1])<=180)add(xy[1],xy[0],"Selected location");
      if(map.getLayer("job-route"))map.removeLayer("job-route");
      if(map.getSource("job-route"))map.removeSource("job-route");
      if(route){
        map.addSource("job-route",{type:"geojson",data:{type:"Feature",properties:{},geometry:route}});
        map.addLayer({id:"job-route",type:"line",source:"job-route",paint:{"line-width":5,"line-color":"#d8541b"}});
        const lines=route.type==="LineString"?[route.coordinates]:route.coordinates;
        lines.forEach(line=>line.forEach(p=>bounds.extend([p[0],p[1]])));
      }
      if(!bounds.isEmpty())map.fitBounds(bounds,{padding:44,maxZoom:15,duration:0});
    });
    return ()=>{disposed=true;markers.forEach(m=>m.remove())};
  },[ready,coordinates,items,route]);
  const xy = coordinates.split(",").map(Number);
  const center = xy.length === 2 && xy.every(Number.isFinite) && Math.abs(xy[0]) <= 90 && Math.abs(xy[1]) <= 180
    ? {lat:xy[0],lon:xy[1]}
    : (() => { const p = items.find(item => item.latitude != null && item.longitude != null); return p ? {lat:p.latitude!,lon:p.longitude!} : {lat:7.9,lon:-1.1}; })();
  const bbox = [center.lon-.19,center.lat-.12,center.lon+.19,center.lat+.12].join(",");
  const fallbackUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(bbox)}&layer=mapnik&marker=${encodeURIComponent(`${center.lat},${center.lon}`)}`;
  const googleUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${center.lat},${center.lon}`)}`;
  return <><div className="real-map" style={{minHeight:290,display:fallback ? "none" : undefined}} ref={container} aria-label="Interactive location map"/>
    {fallback && <div className="hw-map-backup"><iframe src={fallbackUrl} title="Backup location map" loading="lazy" referrerPolicy="strict-origin-when-cross-origin"/><p>Backup map view. <a href={googleUrl} target="_blank" rel="noopener noreferrer">Open in Google Maps</a></p></div>}
    {error && <div className="hw-map-notice" role="status">
      <span>{error}</span>
      <button type="button" onClick={() => setRetry(value => value + 1)}>
        Retry map
      </button>
    </div>}</>;
}

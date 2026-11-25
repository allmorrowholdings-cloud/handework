"use client";
import { useEffect, useRef, useState } from "react";
import type { Map as InteractiveMap, Marker } from "maplibre-gl";
import type { LineString, MultiLineString } from "geojson";
export type MapPoint={id:string;display_name:string;trade?:string;latitude?:number|null;longitude?:number|null};
export type RouteGeometry=LineString|MultiLineString;
const styleUrl=process.env.NEXT_PUBLIC_MAP_STYLE_URL||"https://tiles.openfreemap.org/styles/liberty";

export function LocationMap({items,coordinates="",onPick,route}:{items:MapPoint[];coordinates?:string;onPick?:(lat:number,lon:number)=>void;route?:RouteGeometry}){
  const container=useRef<HTMLDivElement>(null);
  const instance=useRef<InteractiveMap|null>(null);
  const pick=useRef(onPick);
  const [ready,setReady]=useState(false);
  const [error,setError]=useState("");
  useEffect(()=>{pick.current=onPick},[onPick]);
  useEffect(()=>{
    let disposed=false;
    void import("maplibre-gl").then(lib=>{
      if(disposed||!container.current)return;
      const map=new lib.Map({container:container.current,style:styleUrl,center:[-1.1,7.9],zoom:5});
      instance.current=map;
      map.addControl(new lib.NavigationControl(),"top-right");
      map.on("click",e=>pick.current?.(e.lngLat.lat,e.lngLat.lng));
      map.on("load",()=>{if(!disposed){setReady(true);setError("")}});
      map.on("error",()=>{if(!disposed)setError("Some map resources could not load.")});
    }).catch(()=>setError("The interactive map is unavailable on this device."));
    return ()=>{disposed=true;instance.current?.remove();instance.current=null};
  },[]);
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
  return <><div className="real-map" style={{minHeight:290}} ref={container} aria-label="Interactive location map"/>{error&&<small role="status">{error}</small>}</>;
}

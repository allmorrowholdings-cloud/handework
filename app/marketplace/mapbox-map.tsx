"use client";

import { useEffect, useRef } from "react";

type Point={id:string;display_name:string;trade:string;latitude?:number|null;longitude?:number|null};
export function MapboxMap({items,coordinates}:{items:Point[];coordinates:string}){
  const container=useRef<HTMLDivElement|null>(null);
  useEffect(()=>{let map:{remove:()=>void}|undefined;const token=process.env.NEXT_PUBLIC_MAPBOX_TOKEN;if(!container.current||!token)return;void import("mapbox-gl").then((module)=>{if(!container.current)return;const mapbox=module.default;mapbox.accessToken=token;const center=coordinates.split(",").map(Number);const start=center.length===2&&center.every(Number.isFinite)?[center[1],center[0]]:[-0.187,5.604];const instance=new mapbox.Map({container:container.current,style:"mapbox://styles/mapbox/streets-v12",center:start as [number,number],zoom:11});instance.addControl(new mapbox.NavigationControl(),"top-right");items.filter((item)=>item.latitude!=null&&item.longitude!=null).forEach((item)=>{const marker=document.createElement("button");marker.className="real-map-marker";marker.type="button";marker.setAttribute("aria-label",`${item.display_name}, ${item.trade}`);new mapbox.Marker({element:marker}).setLngLat([item.longitude!,item.latitude!]).setPopup(new mapbox.Popup({offset:20}).setText(`${item.display_name} · ${item.trade}`)).addTo(instance)});map=instance});return()=>map?.remove()},[items,coordinates]);
  if(!process.env.NEXT_PUBLIC_MAPBOX_TOKEN)return <div className="map-token-note">Add NEXT_PUBLIC_MAPBOX_TOKEN to activate the interactive map.</div>;
  return <div ref={container} className="real-map" aria-label="Interactive map of matching artisans"/>;
}

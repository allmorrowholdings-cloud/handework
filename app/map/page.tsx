"use client";
import {useEffect,useState} from "react";
import {LocationMap,type MapPoint} from "../components/location-map";
import {api} from "../../lib/api";
export default function MobileMap(){
  const [coordinates,setCoordinates]=useState("");const [items,setItems]=useState<MapPoint[]>([]);
  const [notice,setNotice]=useState("");
  useEffect(()=>{const params=new URLSearchParams(window.location.hash.slice(1));
    const initial=params.get("coordinates")||"";
    void Promise.resolve().then(()=>setCoordinates(initial));
    api<{items:MapPoint[]}>("/v1/artisans/search?"+params).then(data=>setItems(data.items)).catch(e=>setNotice(e.message));
  },[]);
  return <main><LocationMap items={items} coordinates={coordinates}/>{notice&&<p role="status">{notice}</p>}</main>;
}

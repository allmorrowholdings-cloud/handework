"use client";
import { useRef, useState } from "react";
import { api } from "../../lib/api";
import { LocationMap, type MapPoint } from "./location-map";
const empty:MapPoint[]=[];
type Place={label:string;lat:number;lon:number};
export function LocationPicker({value,onSelect}:{value:string;onSelect:(coordinates:string,label?:string)=>void}){
  const [query,setQuery]=useState("");const [results,setResults]=useState<Place[]>([]);const [notice,setNotice]=useState("");
  const generation=useRef(0);
  async function select(lat:number,lon:number,label?:string){
    const seq=++generation.current;
    const coords=lat.toFixed(7)+","+lon.toFixed(7);
    onSelect(coords,label);setResults([]);setNotice("Pin selected");
    if(!label)try{
      const data=await api<{items:Place[]}>("/v1/locations/reverse?coordinates="+encodeURIComponent(coords));
      if(seq===generation.current&&data.items[0])onSelect(coords,data.items[0].label);
    }catch{if(seq===generation.current)setNotice("Location selected. Confirm your street address below.")}
  }
  async function search(){
    const seq=++generation.current;
    try{const data=await api<{items:Place[]}>("/v1/locations/search?q="+encodeURIComponent(query));
      if(seq===generation.current){setResults(data.items);setNotice(data.items.length?"Select an address":"No matching addresses")}}
    catch(e){if(seq===generation.current)setNotice(e instanceof Error?e.message:"Address search unavailable")}
  }
  return <div className="action-form"><label>Search address or landmark<input value={query} onChange={e=>{generation.current++;setQuery(e.target.value);setResults([])}}/></label>
    <div><button type="button" disabled={query.trim().length<2} onClick={()=>void search()}>Find address</button> <button type="button" onClick={()=>{if(!navigator.geolocation){setNotice("GPS unavailable on this device");return}const seq=++generation.current;navigator.geolocation.getCurrentPosition(p=>{if(seq===generation.current)void select(p.coords.latitude,p.coords.longitude)},()=>setNotice("Location unavailable. Search or select a map pin."),{timeout:15000,enableHighAccuracy:true})}}>Use my location</button></div>
    {results.map(r=><button type="button" key={r.label+r.lat+r.lon} onClick={()=>void select(r.lat,r.lon,r.label)}>{r.label}</button>)}
    <LocationMap coordinates={value} items={empty} onPick={(lat,lon)=>void select(lat,lon)}/>
    <small>{value ? "Service location selected" : "Choose the location of your job."}</small>{notice&&<small role="status">{notice}</small>}
    <small>Address search: <a href="https://www.geoapify.com/">Geoapify</a></small></div>
}

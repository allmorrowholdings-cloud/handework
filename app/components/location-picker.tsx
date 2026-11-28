"use client";
import { useRef, useState } from "react";
import { api } from "../../lib/api";
import regions from "../../lib/ghana-places.json";
type Place={label:string;lat:number;lon:number};
export function LocationPicker({value,onSelect}:{value:string;onSelect:(coordinates:string,label?:string)=>void}){
  const [query,setQuery]=useState("");const [results,setResults]=useState<Place[]>([]);const [notice,setNotice]=useState("");
  const generation=useRef(0);
  const [regionId,setRegionId]=useState(""); const [districtId,setDistrictId]=useState("");
  const region=regions.find(r=>r.id===regionId); const district=region?.districts.find(d=>d.id===districtId);
  async function select(lat:number,lon:number,label?:string){
    const seq=++generation.current;
    const coords=lat.toFixed(7)+","+lon.toFixed(7);
    onSelect(coords,label);setResults([]);setNotice("Location selected");
    if(!label)try{
      const data=await api<{items:Place[]}>("/v1/locations/reverse?coordinates="+encodeURIComponent(coords));
      if(seq===generation.current&&data.items[0])onSelect(coords,data.items[0].label);
    }catch{if(seq===generation.current)setNotice("Location selected. Confirm your street address below.")}
  }
  async function search(address=query){
    const seq=++generation.current;
    try{const data=await api<{items:Place[]}>("/v1/locations/search?q="+encodeURIComponent(address));
      if(seq===generation.current){setResults(data.items);setNotice(data.items.length?"Select an address":"No matching addresses")}}
    catch(e){if(seq===generation.current)setNotice(e instanceof Error?e.message:"Address search unavailable")}
  }
  return <div className="action-form"><label>Search address or landmark<input value={query} onChange={e=>{generation.current++;setQuery(e.target.value);setResults([])}}/></label>
    <div><button type="button" disabled={query.trim().length<2} onClick={()=>void search()}>Find address</button> <button type="button" onClick={()=>{if(!navigator.geolocation){setNotice("GPS unavailable on this device");return}const seq=++generation.current;navigator.geolocation.getCurrentPosition(p=>{if(seq===generation.current)void select(p.coords.latitude,p.coords.longitude)},()=>{if(seq===generation.current)setNotice("Location unavailable. Choose a town or search an address.")},{timeout:15000,enableHighAccuracy:true})}}>Use my location</button></div>
    {results.map(r=><button type="button" key={r.label+r.lat+r.lon} onClick={()=>void select(r.lat,r.lon,r.label)}>{r.label}</button>)}
    <details><summary>Choose region, district and town</summary><label>Region<select value={regionId} onChange={e=>{generation.current++;setRegionId(e.target.value);setDistrictId("");setResults([])}}><option value="">Choose region</option>{regions.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select></label><label>District<select value={districtId} disabled={!region} onChange={e=>{generation.current++;setDistrictId(e.target.value);setResults([])}}><option value="">Choose district</option>{region?.districts.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}</select></label><label>Town<select value="" disabled={!district} onChange={e=>{if(!e.target.value)return;const address=`${e.target.value}, ${district?.name}, ${region?.name}, Ghana`;setQuery(address);void search(address)}}><option value="">Choose town</option>{district?.towns.map((t,i)=><option key={`${t.name}-${i}`}>{t.name}</option>)}</select></label><small>Confirm a returned address to save coordinates. If no result appears, try a nearby landmark or GPS.</small></details>
    <small>{value ? "Service location selected" : "Choose the location of your job."}</small>{notice&&<small role="status">{notice}</small>}
    <small>Address search: <a href="https://www.geoapify.com/">Geoapify</a></small></div>
}

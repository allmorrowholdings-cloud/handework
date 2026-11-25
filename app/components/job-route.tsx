"use client";
import {useState} from "react";
import {api} from "../../lib/api";
import {LocationMap,type MapPoint,type RouteGeometry} from "./location-map";
const empty:MapPoint[]=[];
type Route={geometry:RouteGeometry;distance_m:number;duration_s:number;provider:string};
export function JobRoute({id}:{id:string}){
  const [route,setRoute]=useState<Route|null>(null);const [notice,setNotice]=useState("");const [busy,setBusy]=useState(false);
  return <section className="app-card"><h2>Travel to job</h2><button disabled={busy} onClick={async()=>{setBusy(true);try{setRoute(await api<Route>("/v1/bookings/"+id+"/route"));setNotice("")}catch(e){setRoute(null);setNotice(e instanceof Error?e.message:"Directions unavailable")}finally{setBusy(false)}}}>Get driving route</button>
    {route&&<><p>{(route.distance_m/1000).toFixed(1)} km ? estimated driving time {Math.ceil(route.duration_s/60)} min from the artisan?s service location</p><LocationMap items={empty} route={route.geometry}/><small>Directions by {route.provider}</small></>}{notice&&<p role="status">{notice}</p>}</section>
}

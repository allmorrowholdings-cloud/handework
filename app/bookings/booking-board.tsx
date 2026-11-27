"use client";
import {useEffect,useMemo,useState} from "react";
import Link from "next/link";
import {api} from "../../lib/api";
import {useInstalledApp} from "../components/installed-app-mode";

type Booking={id:string;reference?:string;service?:string;status?:string;created_at?:string};
type Filter="current"|"completed"|"cancelled";
const settled=new Set(["completed","cancelled","refunded"]);

export function BookingBoard(){
 const installed=useInstalledApp();
 const [filter,setFilter]=useState<Filter>("current");
 const [bookings,setBookings]=useState<Booking[]|null>(null);
 const [error,setError]=useState(false);
 useEffect(()=>{const controller=new AbortController();api<{items:Booking[]}>("/v1/bookings",{signal:controller.signal})
   .then(({items})=>{if(!controller.signal.aborted)setBookings(items)})
   .catch(()=>{if(!controller.signal.aborted)setError(true)});
   return()=>controller.abort();},[]);
 const filtered=useMemo(()=>bookings?.filter(job=> filter==="completed"?job.status==="completed":filter==="cancelled"?["cancelled","refunded"].includes(job.status??""):!settled.has(job.status??""))??[],[bookings,filter]);
 const newHref=installed?"/app/book":"/bookings/new";
 return <div className="hw-booking-board">
   <div className="hw-booking-filters" role="group" aria-label="Filter bookings">{(["current","completed","cancelled"] as const).map(k=><button key={k} type="button" aria-pressed={filter===k} className={filter===k?"active":""} onClick={()=>setFilter(k)}>{k[0].toUpperCase()+k.slice(1)}</button>)}</div>
   {error?<div className="hw-board-empty" role="alert"><h3>Bookings could not load</h3><p>Check your connection and reopen this page. Your existing bookings remain saved.</p></div>:!bookings?<p className="hw-board-loading" role="status">Loading bookings…</p>:filtered.length?<div className="record-list hw-premium-records">{filtered.map(job=><div className="record-row" key={job.id}><div><b>{job.service||"Service booking"}</b><span>{[job.reference,job.status?.replaceAll("_"," ")].filter(Boolean).join(" · ")}</span></div><Link href={"/bookings/"+encodeURIComponent(job.id)}>View booking</Link></div>)}</div>:<div className="hw-board-empty"><h3>{filter==="current"?"Nothing in progress":"No "+filter+" bookings"}</h3><p>{filter==="current"?"When you book a professional, updates will appear here.":"Your records will appear here when their status changes."}</p>{filter==="current"&&<Link className="button button-orange" href={newHref}>Choose a service</Link>}</div>}
 </div>;
}

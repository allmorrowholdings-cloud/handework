"use client";
import {useCallback,useEffect,useState} from "react";
import {api} from "../../../lib/api";
type Case={id:string;booking_id:string;reason:string;description:string;status:string;responses:{actor:string;message:string;url?:string}[]};
export function DisputeDesk(){
  const [rows,setRows]=useState<Case[]>([]);const [notice,setNotice]=useState("");const [busy,setBusy]=useState(false);
  const load=useCallback(()=>api<{items:Case[]}>("/v1/admin/disputes").then(r=>setRows(r.items)).catch(e=>setNotice(e.message)),[]);
  useEffect(()=>{void load()},[load]);
  return <>{rows.map(c=><section className="app-card" key={c.id}><h3>{c.reason} ? {c.status}</h3><small>Booking {c.booking_id}</small><p>{c.description}</p>{c.responses.map((r,i)=><p key={i}>{r.message} {r.url&&<a href={r.url} target="_blank" rel="noreferrer">Review evidence</a>}</p>)}
    {c.status==="open"&&<form className="action-form" onSubmit={async e=>{e.preventDefault();setBusy(true);try{await api("/v1/admin/disputes/"+c.id+"/decision",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.currentTarget)))});await load();setNotice("Decision recorded. Process the authorized refund or release in Payment operations.")}catch(e){setNotice(e instanceof Error?e.message:"Decision unavailable")}finally{setBusy(false)}}}>
    <label>Decision<select name="decision"><option value="release_to_artisan">Release to artisan</option><option value="refund_customer">Refund customer</option><option value="split">Refund part and release remainder</option><option value="no_action">Close without financial action</option></select></label><label>Customer refund for split (GHS)<input name="refund_amount" type="number" min=".01" step=".01"/></label><label>Investigation and decision<textarea required name="resolution"/></label><button disabled={busy}>Record decision</button></form>}</section>)}{!rows.length&&<p>No recorded disputes</p>}{notice&&<p role="status">{notice}</p>}</>
}

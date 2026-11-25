"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../../../lib/api";

type Earnings={last_four?:string;earnings:{id:string;reference:string;net:string;settlement?:string}[];operations:{id:string;payment_id:string;amount:string;status:string}[]};
export function Withdrawals(){
  const [data,setData]=useState<Earnings|null>(null);const [notice,setNotice]=useState("");const [busy,setBusy]=useState(false);
  const load=useCallback(()=>api<Earnings>("/v1/artisan/payouts").then(setData).catch(e=>setNotice(e.message)),[]);
  useEffect(()=>{void load()},[load]);
  async function withdraw(e:FormEvent<HTMLFormElement>){
    e.preventDefault();const form=e.currentTarget;const fields=new FormData(form);const id=String(fields.get("payment"));
    setBusy(true);
    try{
      await api("/v1/artisan/earnings/"+id+"/withdraw",{method:"POST",headers:{"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({password:fields.get("password")})});
      setNotice("Transfer submitted for provider confirmation");form.reset();await load();
    }catch(e){setNotice(e instanceof Error?e.message:"Withdrawal unavailable")}finally{setBusy(false)}
  }
  const eligible=data?.earnings.filter(p=>p.settlement&&!data.operations.some(o=>o.payment_id===p.id&&["pending","success"].includes(o.status)))??[];
  return <section className="app-card"><h2>Withdraw earnings</h2>
    {data?.last_four&&<p>Verified payout account ending in {data.last_four}</p>}
    {eligible.length&&data?.last_four?<form onSubmit={withdraw} className="action-form"><label>Settled earning<select name="payment">{eligible.map(p=><option key={p.id} value={p.id}>{p.reference} ? GHS {p.net}</option>)}</select></label><label>Account password<input type="password" required name="password" autoComplete="current-password"/></label><button className="button button-orange" disabled={busy}>Request transfer</button></form>:<p>{data?"A withdrawal requires settled earnings and a verified payout account.":"Loading earnings?"}</p>}
    <h3>Withdrawal history</h3>{data?.operations.map(o=><div key={o.id} className="record-row"><span>{o.id}</span><b>GHS {o.amount} ? {o.status}</b></div>)}
    <button onClick={()=>void load()}>Refresh earnings</button>{notice&&<p role="status">{notice}</p>}</section>
}

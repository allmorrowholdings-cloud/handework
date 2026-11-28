"use client";
import { useState, type FormEvent } from "react";
import { api } from "../../../lib/api";
type Result = {id:string;display_name:string;trade:string;secondary_services:string;readiness:{ready:boolean;missing:string[]}};
const labels:Record<string,string>={active_account:"Account must be active",approved:"Verification approval required",declared_service:"Declare a profession or service",located:"Save a service location and radius",accepting_work:"Enable working availability"};
export function ProfessionalReadiness(){
 const [id,setId]=useState("");const [result,setResult]=useState<Result|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState("");
 async function lookup(e:FormEvent<HTMLFormElement>){e.preventDefault();if(busy)return;setBusy(true);setError("");setResult(null);try{setResult(await api<Result>(`/v1/admin/professional-readiness/${encodeURIComponent(id.trim())}`))}catch(e){setError(e instanceof Error?e.message:"Unable to load profile.")}finally{setBusy(false)}}
 return <div><form className="action-form" onSubmit={lookup}><label>Professional profile ID<input required value={id} onChange={e=>setId(e.target.value)} maxLength={36}/></label><button className="button button-dark" disabled={busy}>{busy?"Checking…":"Check readiness"}</button></form>{error&&<p role="alert">{error}</p>}{result&&<section aria-live="polite"><h3>{result.display_name}</h3><p>{result.trade} · {result.secondary_services}</p><p>{result.readiness.ready?"Basic marketplace setup complete":"Work setup required"}</p>{result.readiness.missing.length>0&&<ul>{result.readiness.missing.map(key=><li key={key}>{labels[key]||key}</li>)}</ul>}<p>Readiness does not guarantee a match for a particular service, location or time.</p></section>}</div>
}

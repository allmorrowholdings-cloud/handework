"use client";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../../../lib/api";

export function RecipientForm(){
  const [notice,setNotice]=useState("");const [busy,setBusy]=useState(false);
  const [kind,setKind]=useState("ghipss");
  const [institutions,setInstitutions]=useState<{code:string;name:string}[]>([]);
  useEffect(()=>{let active=true;api<{items:{code:string;name:string}[]}>("/v1/artisan/payout-institutions?type="+kind).then(r=>{if(active)setInstitutions(r.items)}).catch(e=>{if(active)setNotice(e.message)});return ()=>{active=false}},[kind]);
  async function register(e:FormEvent<HTMLFormElement>){
    e.preventDefault();const form=e.currentTarget;setBusy(true);
    try{
      const data=await api<{last_four:string}>("/v1/artisan/payout-recipient",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(form)))});
      form.reset();setNotice("Verified account ending in "+data.last_four);
    }catch(e){setNotice(e instanceof Error?e.message:"Verification unavailable")}finally{setBusy(false)}
  }
  return <form onSubmit={register} className="app-card action-form"><h2>Payout account</h2>
    <label>Account type<select name="type" value={kind} onChange={e=>{setKind(e.target.value);setInstitutions([])}}><option value="ghipss">Ghana bank account</option><option value="mobile_money">Mobile money</option></select></label>
    <label>Provider bank or network code<input name="bank_code" list="payout-institutions" required/><datalist id="payout-institutions">{institutions.map(i=><option key={i.code} value={i.code}>{i.name}</option>)}</datalist></label><label>Account or mobile number<input required name="account_number" inputMode="numeric"/></label>
    <label>Confirm account password<input name="password" type="password" required autoComplete="current-password"/></label>
    <button disabled={busy} className="button button-orange">Verify payout account</button>{notice&&<p role="status">{notice}</p>}</form>
}

"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "../../lib/api";

export function ReferralPanel() {
  const [code,setCode]=useState(""); const [notice,setNotice]=useState("");
  useEffect(()=>{api<{code:string}>("/v1/referrals").then((body)=>setCode(body.code)).catch((error)=>setNotice(error.message));},[]);
  async function validate(event:FormEvent<HTMLFormElement>){event.preventDefault();const data=new FormData(event.currentTarget);setNotice("");try{const body=await api<{discount:number;currency:string}>("/v1/promo-codes/validate",{method:"POST",body:JSON.stringify({code:data.get("code"),amount:data.get("amount")})});setNotice(`Valid discount: ${body.currency} ${body.discount.toFixed(2)}. It will be applied when the booking is paid.`)}catch(caught){setNotice(caught instanceof Error?caught.message:"Code could not be validated")}}
  return <div className="app-columns"><section className="app-card referral-card"><h2>Invite skilled hands or customers.</h2><p>Rewards are credited only after the referred person completes a qualifying first job.</p>{code?<button className="button button-dark" onClick={()=>navigator.clipboard.writeText(code)}>{code} · COPY</button>:<button className="button button-dark" disabled>Loading verified code…</button>}</section><aside className="app-card"><div className="card-head"><h2>Validate a promo code</h2></div><form className="promo-form" onSubmit={validate}><input required name="code" aria-label="Promo code" placeholder="Enter code"/><input required name="amount" type="number" min="1" aria-label="Booking amount" placeholder="Booking amount in GHS"/><button>Check code</button></form>{notice&&<p className="data-note" role="status">{notice}</p>}</aside></div>;
}

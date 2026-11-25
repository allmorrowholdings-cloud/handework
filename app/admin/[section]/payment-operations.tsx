"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../../../lib/api";

type Row = Record<string, string | null>;
type Records = Record<"payments" | "orders" | "operations" | "audit", Row[]>;
const titles = {payments:"Booking transactions", orders:"Shop purchases", operations:"Refunds and payouts", audit:"Audit history"};

export function PaymentOperations() {
  const [records,setRecords]=useState<Records|null>(null);
  const [summary,setSummary]=useState<{metrics:Record<string,number>;chargebacks:Row[];discrepancies:Row[]}|null>(null);
  const [group,setGroup]=useState<keyof Records>("payments");
  const [query,setQuery]=useState("");
  const [notice,setNotice]=useState("");
  const [busy,setBusy]=useState(false);
  const [key,setKey]=useState("");
  const [action,setAction]=useState("verify");
  const load=useCallback(()=>Promise.all([api<Records>("/v1/admin/payment-operations"),api<NonNullable<typeof summary>>("/v1/admin/payment-summary")]).then(([data,totals])=>{setRecords(data);setSummary(totals)}).catch(e=>setNotice(e.message)),[]);
  useEffect(()=>{void load()},[load]);
  const rows=(records?.[group]??[]).filter(row=>Object.values(row).join(" ").toLowerCase().includes(query.toLowerCase()));
  const fields=Object.keys(rows[0]??{});
  function exportRows(){
    const cell=(s:string)=>'"'+(/^[=+@\-]/.test(s)?"'":"")+s.replaceAll('"','""')+'"';
    const csv=[fields,...rows.map(row=>fields.map(f=>String(row[f]??"")))].map(values=>values.map(cell).join(",")).join("\r\n");
    const url=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
    const link=document.createElement("a");link.href=url;link.download="handework-"+group+".csv";link.click();URL.revokeObjectURL(url);
  }
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();
    const form=event.currentTarget;
    const data=Object.fromEntries(new FormData(form));
    const id=encodeURIComponent(String(data.id).trim());
    const requestKey=key||crypto.randomUUID();
    setKey(requestKey);setBusy(true);setNotice("");
    try{
      const path=action==="release"?`/v1/bookings/${id}/release`:action==="shop_refund"?`/v1/admin/shop-orders/${id}/refund`:action==="reconcile"?`/v1/admin/payment-operations/${id}/reconcile`:`/v1/payments/${id}/${action}`;
      const body=Object.fromEntries(Object.entries(data).filter(([k,v])=>k!=="id"&&v!==""));
      const result=await api<{status?:string}>(path,{method:"POST",headers:{"Idempotency-Key":requestKey},body:JSON.stringify({...body,merchant_funded:body.merchant_funded==="on"})});
      setNotice(result.status??(action==="release"?"Release recorded":"Settlement confirmed"));setKey("");form.reset();await load();
    }catch(e){setNotice(e instanceof Error?e.message:"Request failed")}finally{setBusy(false)}
  }
  return <>{summary&&<><div className="stat-grid">{Object.entries(summary.metrics).map(([label,units])=><div className="app-card" key={label}><small>{label}</small><h3>GHS {(units/100).toFixed(2)}</h3></div>)}</div><h3>Chargebacks</h3>{summary.chargebacks.length?summary.chargebacks.map(c=><p key={c.id}>{c.reference} ? {c.status} {c.resolution} <button onClick={async()=>{try{await api("/v1/admin/payment-disputes/"+c.id+"/verify",{method:"POST"});await load()}catch(e){setNotice(e instanceof Error?e.message:"Verification failed")}}}>Recheck</button></p>):<p>No recorded chargebacks</p>}<h3>Reconciliation exceptions</h3>{summary.discrepancies.length?summary.discrepancies.map(j=><p key={j.id}>{j.id} ? {j.error} ? {j.attempts} attempts</p>):<p>No outstanding job errors</p>}</>}<div className="two-fields"><label>Records<select value={group} onChange={e=>setGroup(e.target.value as keyof Records)}>{Object.entries(titles).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><label>Search by reference, ID or status<input value={query} onChange={e=>setQuery(e.target.value)}/></label></div>
    <p>Latest 200 records per category</p><button type="button" disabled={!rows.length} onClick={exportRows}>Export filtered CSV</button>
    <div style={{overflowX:"auto"}}>{rows.length?<table><thead><tr>{fields.map(f=><th key={f}>{f.replaceAll("_"," ")}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={r.id??r.reference??i}>{fields.map(f=><td key={f}>{r[f]??"?"}</td>)}</tr>)}</tbody></table>:<p>{records?"No matching records":"Loading records?"}</p>}</div>
    <form className="action-form" onSubmit={submit} onChange={()=>setKey("")}><h2>Financial operations</h2><label>Action<select value={action} onChange={e=>setAction(e.target.value)}>
      {Object.entries({verify:"Verify charge",release:"Authorize booking release",settlement:"Verify settlement",refund:"Request booking refund",shop_refund:"Request shop refund",payout:"Submit artisan payout",reconcile:"Reconcile refund or transfer"}).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
    <label>{action==="reconcile"?"Operation ID":action==="shop_refund"?"Shop order ID":action==="release"?"Booking ID":"Payment ID"}<input name="id" required/></label>
    {action==="settlement"&&<><label>Paystack settlement ID<input name="settlement_id" required/></label>{["batch_page","transaction_page"].map(k=><label key={k}>{k.replace("_"," ")}<input type="number" min="1" defaultValue="1" name={k}/></label>)}</>}
    {["refund","shop_refund"].includes(action)&&<label>Refund amount (GHS)<input required min="0.01" step="0.01" name="amount" type="number"/></label>}
    {action==="refund"&&<label><input type="checkbox" name="merchant_funded"/>Authorize ALLMORROW to fund this refund if the artisan has already been paid.</label>}
    {action==="reconcile"&&<label>Paystack refund ID (for uncertain submissions)<input name="refund_id"/></label>}
    {["refund","payout","shop_refund"].includes(action)&&<label>Confirm administrator password<input required name="password" type="password" autoComplete="current-password"/></label>}
    <button className="button button-orange" disabled={busy}>{busy?"Processing?":"Submit action"}</button></form>{notice&&<p role="status">{notice}</p>}</>
}

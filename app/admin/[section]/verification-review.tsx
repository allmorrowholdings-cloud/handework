"use client";

import { FormEvent, useState, useEffect } from "react";
import { api } from "../../../lib/api";

type Check = { id: string; kind: string; file_url?: string; payout_name?: string };
export function VerificationReview() {
  const [rows,setRows]=useState<Check[] | null>(null);
  const [notice,setNotice]=useState("");
  const [saving,setSaving]=useState(false);
  useEffect(()=>{
    const controller=new AbortController();
    api<{items:Check[]}>("/v1/admin/verifications",{signal:controller.signal}).then(body=>setRows(body.items))
      .catch(()=>{if(!controller.signal.aborted)setNotice("Verification records could not load. Reload to try again.");});
    return ()=>controller.abort();
  },[]);
  async function review(event: FormEvent<HTMLFormElement>, id:string) {
    event.preventDefault();
    if(saving)return;
    const data=Object.fromEntries(new FormData(event.currentTarget));
    setSaving(true);
    try {
      await api(`/v1/admin/verifications/${id}/decision`,{method:"POST",body:JSON.stringify(data)});
      setRows(current=>current?.filter(row=>row.id!==id) ?? []);
      setNotice("Decision recorded.");
    } catch { setNotice("Decision could not be confirmed. Refresh the queue before trying again."); }
    finally {setSaving(false);}
  }
  return <>{!rows && !notice && <p>Loading verification records...</p>}{rows?.length===0 && <p>No checks are waiting for review.</p>}
    {rows?.map(row=><form key={row.id} className="app-card action-form" onSubmit={event=>void review(event,row.id)}>
      <h3>{row.kind.replaceAll("_"," ")}</h3>{row.file_url && <a href={row.file_url} target="_blank" rel="noopener noreferrer">Review private document</a>}{row.payout_name && <p>{row.payout_name}</p>}
      <label>Decision<select name="decision" required defaultValue=""><option value="">Choose a decision</option><option value="replacement_required">Request replacement</option><option value="rejected">Reject</option><option value="approved">Approve</option></select></label>
      <label>Review notes<textarea name="reason" required maxLength={500}/></label><button className="button button-orange" disabled={saving}>Record decision</button>
    </form>)}<p role="status">{notice}</p></>;
}

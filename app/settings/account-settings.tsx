"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "../../lib/api";

type User = { first_name:string; last_name:string; email:string; phone:string; notification_preferences:{push:boolean;whatsapp:boolean;sms:boolean} };

export function AccountSettings() {
  const [user, setUser] = useState<User|null>(null); const [notice, setNotice] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { api<{user:User}>("/v1/auth/me").then((body)=>setUser(body.user)).catch((error)=>setNotice(error.message)); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!user) return; setBusy(true); setNotice(""); try { const body=await api<{user:User}>("/v1/auth/me",{method:"PATCH",body:JSON.stringify(user)}); setUser(body.user); setNotice("Changes saved."); } catch(caught) { setNotice(caught instanceof Error?caught.message:"Changes could not be saved"); } finally { setBusy(false); } }
  if (!user) return <div className="loading-line"><span />{notice || "Loading account…"}</div>;
  const set=(field:keyof User,value:unknown)=>setUser((current)=>current?{...current,[field]:value}:current);
  const preference=(field:keyof User["notification_preferences"],value:boolean)=>setUser((current)=>current?{...current,notification_preferences:{...current.notification_preferences,[field]:value}}:current);
  return <form className="app-card settings-form" onSubmit={submit}><h2>Personal details</h2><div className="two-fields"><label>First name<input value={user.first_name} onChange={(event)=>set("first_name",event.target.value)}/></label><label>Last name<input value={user.last_name} onChange={(event)=>set("last_name",event.target.value)}/></label></div><label>Email address<input type="email" value={user.email} disabled/></label><label>Mobile number<input type="tel" value={user.phone} onChange={(event)=>set("phone",event.target.value)}/></label><h2>Notifications</h2><label className="setting-row"><span><b>Push notifications</b><small>Job and payment alerts on your device</small></span><input type="checkbox" checked={user.notification_preferences.push} onChange={(event)=>preference("push",event.target.checked)}/></label><label className="setting-row"><span><b>WhatsApp updates</b><small>Time-sensitive booking updates</small></span><input type="checkbox" checked={user.notification_preferences.whatsapp} onChange={(event)=>preference("whatsapp",event.target.checked)}/></label><label className="setting-row"><span><b>SMS fallback</b><small>Critical alerts when data is unavailable</small></span><input type="checkbox" checked={user.notification_preferences.sms} onChange={(event)=>preference("sms",event.target.checked)}/></label>{notice&&<p className="form-error" role="status">{notice}</p>}<button className="button button-orange" disabled={busy}>{busy?"Saving…":"Save changes"}</button></form>;
}

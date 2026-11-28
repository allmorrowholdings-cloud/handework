"use client";

import { ChangeEvent, useCallback, useEffect, useState } from "react";
import { api } from "../../../lib/api";

const checks = [
  { kind: "government_id", title: "Government ID", text: "Ghana Card or accepted passport" },
  { kind: "live_selfie", title: "Live selfie", text: "A current, clear photo from your device" },
  { kind: "trade_proof", title: "Trade proof", text: "Certificate, apprenticeship letter or work evidence" },
  { kind: "payout_name", title: "Payout name", text: "Must match the verified identity" },
];

type Check = { id?: string; kind: string; status: string; decision_reason?: string };

export function VerificationManager() {
  const [items, setItems] = useState<Check[]>([]);
  const [profileStatus, setProfileStatus] = useState("draft");
  const [notice, setNotice] = useState("");
  const [busyKind, setBusyKind] = useState<string | null>(null);

  const load = useCallback((signal?: AbortSignal) =>
    api<{ items: Check[]; profile_status: string }>("/v1/artisans/me/verifications", { signal })
      .then(body => {
        if (signal?.aborted) return;
        setItems(body.items ?? []);
        setProfileStatus(body.profile_status ?? "draft");
      })
      .catch(caught => {
        if (!signal?.aborted) setNotice(caught instanceof Error ? caught.message : "Verification status could not be loaded");
      }), []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function upload(kind: string, event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusyKind(kind); setNotice("");
    const form = new FormData(); form.append("kind", kind); form.append("file", file);
    try {
      await api("/v1/artisans/me/verifications", { method: "POST", body: form });
      setNotice("File received. It is now pending admin review.");
      await load();
    } catch (caught) {
      setNotice(caught instanceof Error ? caught.message : "Verification could not be uploaded");
    } finally {
      setBusyKind(null); event.target.value = "";
    }
  }

  async function payout() {
    const value = window.prompt("Enter the full name on the mobile-money or bank payout account");
    if (!value?.trim()) return;
    setBusyKind("payout_name"); setNotice("");
    const form = new FormData(); form.append("kind", "payout_name"); form.append("value", value.trim());
    try {
      await api("/v1/artisans/me/verifications", { method: "POST", body: form });
      setNotice("Payout name received. It is now pending admin review.");
      await load();
    } catch (caught) {
      setNotice(caught instanceof Error ? caught.message : "Payout name could not be submitted");
    } finally { setBusyKind(null); }
  }

  const complete = checks.filter(check => items.some(item => item.kind === check.kind && item.status === "approved")).length;
  return <div className="app-card verify-card">
    <div className="verify-intro"><span>{Math.round(complete / checks.length * 100)}%</span><div><h2>{profileStatus === "approved" ? "Profile verified" : "Complete your checks"}</h2><p>{profileStatus === "approved" ? "Your checks are approved. Set your service location and availability to receive nearby requests." : "Your profile stays private until required checks are approved."}</p></div></div>
    {checks.map((check, index) => {
      const row = items.find((item) => item.kind === check.kind);
      const status = row?.status ?? "not submitted";
      const approved = status === "approved";
      const pending = status === "pending";
      const actionText = busyKind === check.kind ? "Uploading…" : approved ? "Approved" : pending ? "Replace file" : "Upload file";
      return <div className={`verify-row verification-${status.replaceAll(" ", "-")}`} key={check.kind}>
        <span>0{index + 1}</span>
        <div><b>{check.title}</b><small>{approved ? check.text : row?.decision_reason || check.text}</small><em>{pending ? "Pending admin review" : approved ? "" : ["replacement_required","rejected"].includes(status) ? "Action required" : "Not submitted"}</em></div>
        {check.kind === "payout_name" ?
          <button type="button" disabled={approved || busyKind === check.kind} onClick={payout}>{busyKind === check.kind ? "Saving…" : approved ? "Approved" : pending ? "Update name" : "Add payout name"}</button> :
          <label className={`verify-upload ${approved ? "disabled" : ""}`} htmlFor={`verification-${check.kind}`}>{actionText}<input id={`verification-${check.kind}`} disabled={approved || busyKind === check.kind} type="file" accept="image/jpeg,image/png,image/webp,application/pdf" onChange={(event) => void upload(check.kind, event)} /></label>}
      </div>;
    })}
    {profileStatus === "approved" && <p><a href="/artisan/profile">Service location</a> · <a href="/artisan/availability">Availability</a></p>}
    {notice && <p className="data-note" role="status">{notice}</p>}

  </div>;
}

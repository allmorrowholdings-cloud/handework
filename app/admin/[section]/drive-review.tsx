"use client";
import { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { DriveAnchor, type Submission } from "../../components/drive-links";

export function DriveReview() {
  const [status, setStatus] = useState("pending");
  const [items, setItems] = useState<Submission[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api<{items:Submission[]}>("/v1/admin/drive-submissions?status=" + status, {signal:controller.signal})
      .then(data => { setItems(data.items); setMessage(data.items.length ? "" : "No submissions in this queue."); })
      .catch(error => { if (!controller.signal.aborted) setMessage(error.message); });
    return () => controller.abort();
  }, [status, revision]);
  async function decide(item: Submission, decision: string, note: string) {
    setBusy(true);
    try {
      await api("/v1/admin/drive-submissions/" + item.id + "/review", {
        method:"POST", body:JSON.stringify({status:decision, note, version:item.version}),
      });
      setItems(current => current.filter(row => row.id !== item.id));
      setMessage("Review recorded.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Review failed."); }
    finally { setBusy(false); }
  }
  return <section><p>Approval accepts this submission for its stated purpose. Drive controls access, and the owner can change the content after review.</p>
    <label>Review status <select value={status} disabled={busy} onChange={e => {setItems([]); setStatus(e.target.value);}}>
      {["pending","approved","rejected"].map(value => <option key={value}>{value}</option>)}</select></label>{" "}
    <button disabled={busy} onClick={() => setRevision(x => x + 1)}>Refresh queue</button>
    <p role="status">{message}</p>
    {items.map(item => <article className="app-card" key={item.id + ":" + item.version}>
      <DriveAnchor item={item}/><p>{item.owner_name} · {item.purpose.replaceAll("_", " ")}{item.course_title && " · " + item.course_title}</p>
      {item.status === "pending" ? <form className="action-form" onSubmit={event => {
        event.preventDefault();
        const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
        if (submitter) void decide(item, submitter.value, String(new FormData(event.currentTarget).get("note") ?? ""));
      }}><label>Feedback (optional)<textarea name="note" maxLength={500}/></label><div>
        <button value="approved" disabled={busy}>Approve</button>{" "}<button value="rejected" disabled={busy}>Reject</button>
      </div></form> : <p>{item.review_note}</p>}
    </article>)}
  </section>;
}

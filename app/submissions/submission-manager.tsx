"use client";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../../lib/api";
import { DriveAnchor, type Submission } from "../components/drive-links";

const endpoint = "/v1/drive-submissions";
const labels: Record<string, string> = {
  portfolio: "Portfolio", training_resource: "Training resource", course_material: "Course material",
  supporting_document: "Non-sensitive supporting document",
};

export function SubmissionManager() {
  const [items, setItems] = useState<Submission[]>([]);
  const [courses, setCourses] = useState<{id: string; title: string}[]>([]);
  const [role, setRole] = useState("");
  const [purpose, setPurpose] = useState("supporting_document");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    const init = {signal: controller.signal};
    Promise.all([api<{user:{role:string}}>("/v1/auth/me", init), api<{items:Submission[]}>(endpoint, init),
      api<{items:{id:string;title:string}[]}>("/v1/training/courses", init)])
      .then(([account, submissions, catalog]) => {
        setRole(account.user.role); setItems(submissions.items); setCourses(catalog.items);
        const initial = new URLSearchParams(window.location.search).get("purpose");
        if (initial && Object.hasOwn(labels, initial) && (initial !== "portfolio" || account.user.role === "artisan")) setPurpose(initial);
      }).catch(error => { if (!controller.signal.aborted) setMessage(error.message); });
    return () => controller.abort();
  }, []);

  async function save(method: string, data: object, id = "") {
    setBusy(true); setMessage("");
    try {
      await api(endpoint + (id ? "/" + id : ""), {method, body: JSON.stringify(data)});
      setItems((await api<{items:Submission[]}>(endpoint)).items);
      setEditing(""); setMessage(method === "DELETE" ? "Link removed." : "Link submitted for review.");
      return true;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Request failed.");
      return false;
    } finally { setBusy(false); }
  }
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    if (await save("POST", {...Object.fromEntries(new FormData(form)), purpose})) {
      for (const name of ["title", "url"]) {
        const field = form.elements.namedItem(name);
        if (field instanceof HTMLInputElement) field.value = "";
      }
    }
  }
  return <>
    <form className="app-card action-form" onSubmit={submit}>
      <h2>Submit an external link</h2>
      <p>Use Drive for non-sensitive material. Keep IDs, selfies, KYC, payout verification and booking or dispute evidence in the private handEwork upload forms.</p>
      <label>Purpose<select name="purpose" value={purpose} onChange={e => setPurpose(e.target.value)}>
        {Object.entries(labels).filter(([key]) => key !== "portfolio" || role === "artisan").map(([key, label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      {purpose === "course_material" && <label>Course<select name="course_id" required defaultValue=""><option value="">Choose a published course</option>
        {courses.map(course => <option value={course.id} key={course.id}>{course.title}</option>)}</select></label>}
      <p>{purpose === "supporting_document" ? "You and handEwork administrators can see this submission." : "Approved links appear on the public portfolio or training page."} Your Drive sharing settings control who can open the file or folder.</p>
      <label>Title<input name="title" required maxLength={180}/></label>
      <label>Google Drive sharing link<input name="url" type="url" required maxLength={2048}/></label>
      <button className="button button-dark" disabled={!role || busy}>Submit link</button>
    </form>
    <p role="status">{message}</p>
    <section className="app-card"><h2>Submitted links</h2>
      {role && !items.length && <p>You have no submitted links.</p>}
      {items.map(item => <article key={item.id} className="action-form">
        <DriveAnchor item={item}/><small>{labels[item.purpose]} · {item.status}</small>
        {item.review_note && <p>Reviewer feedback: {item.review_note}</p>}
        {editing === item.id ? <form className="action-form" onSubmit={event => {
          event.preventDefault(); void save("PUT", {url:new FormData(event.currentTarget).get("url"), version:item.version}, item.id);
        }}><label>Replacement Drive link<input name="url" type="url" required maxLength={2048}/></label>
          <small>Replacing this link sends it back for review.</small><button disabled={busy}>Save replacement</button>
          <button type="button" onClick={() => setEditing("")}>Cancel</button></form>
        : <div><button disabled={busy} onClick={() => setEditing(item.id)}>Replace link</button>{" "}
          <button disabled={busy} onClick={() => { if (window.confirm("Remove this link from handEwork?")) void save("DELETE", {version:item.version}, item.id); }}>Remove link</button></div>}
      </article>)}
    </section>
  </>;
}

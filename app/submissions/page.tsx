import { AppShell } from "../components/app-shell";
import { SubmissionManager } from "./submission-manager";

export default function Submissions() {
  return <AppShell title="My Google Drive submissions"><section className="app-content narrow-content">
    <SubmissionManager/>
  </section></AppShell>;
}

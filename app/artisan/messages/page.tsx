import { AppShell } from "../../components/app-shell";
import { LiveRecords } from "../../components/live-records";

export default function ArtisanMessagesPage(){
  return <AppShell role="artisan" title="Messages" note="Private job conversations stay attached to the work record."><section className="app-content"><div className="messages-layout"><aside className="app-card thread-list"><div className="card-head"><h2>Job conversations</h2></div><LiveRecords endpoint="/v1/conversations" linkBase="/artisan/messages" emptyTitle="No conversation yet" emptyText="A private thread opens when an assigned or accepted booking has a conversation record." /></aside><section className="app-card chat-empty"><h2>Select a job conversation</h2><p>Keep scope changes, arrival updates, evidence and approvals inside handEwork.</p></section></div></section></AppShell>;
}

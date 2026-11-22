import { AppShell } from "../../components/app-shell";
import { LiveRecords } from "../../components/live-records";

export default function ArtisanJobsPage() {
  return <AppShell role="artisan" title="Jobs" note="Requests, accepted work, progress and completion in one artisan record.">
    <section className="app-content"><div className="app-card full-card"><div className="card-head"><h2>Your jobs</h2></div><LiveRecords endpoint="/v1/bookings" linkBase="/artisan/jobs" emptyTitle="No jobs yet" emptyText="Approved, available artisans receive matching requests here. When a customer accepts your quote, the same record continues through payment and completion." /></div></section>
  </AppShell>;
}

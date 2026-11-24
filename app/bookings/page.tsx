import Link from "next/link";
import { AppShell } from "../components/app-shell";
import { LiveRecords } from "../components/live-records";

export default function BookingsPage() { return <AppShell title="Bookings" note="Every accepted scope, schedule change and payment stays attached to the job." action={<Link className="button button-orange" href="/bookings/new">New booking</Link>}><section className="app-content"><div className="app-card full-card"><div className="card-head"><h2>All bookings</h2><div className="segmented"><button className="selected">Current</button><button>Completed</button><button>Cancelled</button></div></div><LiveRecords endpoint="/v1/bookings" emptyTitle="No booking yet" emptyText="Start with the service, location and time. You choose an artisan before any payment is requested." action={{href:"/bookings/new",label:"Find an artisan"}} /></div></section></AppShell>; }

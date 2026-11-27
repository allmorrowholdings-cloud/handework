import Link from "next/link";
import { AppShell } from "../components/app-shell";
import { BookingBoard } from "./booking-board";

export default function BookingsPage() { return <AppShell title="Bookings" note="Every accepted scope, schedule change and payment stays attached to the job." action={<Link className="button button-orange" href="/bookings/new" data-website-only="true">Book a professional</Link>}><section className="app-content"><div className="app-card full-card"><div className="card-head"><h2>Your booking records</h2></div><BookingBoard /></div></section></AppShell>; }

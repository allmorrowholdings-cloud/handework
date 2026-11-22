import { AppShell } from "../../components/app-shell";import { AvailabilityEditor } from "./editor";
export default function Availability(){return <AppShell role="artisan" title="Availability" note="Instant bookings are offered only inside hours you mark as available."><section className="app-content narrow-content"><AvailabilityEditor/></section></AppShell>}

import { AppShell } from "../../../components/app-shell";
import { BookingRecord } from "../../../bookings/[id]/booking-record";

export default async function ArtisanJobDetail({params}:{params:Promise<{id:string}>}) {
  const {id}=await params;
  return <AppShell role="artisan" title="Job record" note="Scope, quote, status, payment protection and completion."><section className="app-content"><BookingRecord id={id} messageBase="/artisan/messages" /></section></AppShell>;
}

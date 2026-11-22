import { AppShell } from "../../components/app-shell";
import { BookingRecord } from "./booking-record";
export default async function BookingDetail({params}:{params:Promise<{id:string}>}){const{id}=await params;return <AppShell title="Booking record" note={`Reference ${id}`}><section className="app-content"><BookingRecord id={id}/></section></AppShell>}

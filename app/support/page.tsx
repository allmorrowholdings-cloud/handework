import Link from "next/link";
import { Header } from "../components/header";
import { Footer } from "../components/footer";
import { SupportForm } from "./support-form";

const topics = { booking: "A booking or artisan", payment: "Payment, refund or payout", account: "Account or verification", safety: "Safety concern", business: "Business account", partnership: "TVET partnership" };
export default async function Support({ searchParams }: { searchParams: Promise<{ topic?: string }> }){
  const { topic = "" } = await searchParams;
  const selected = Object.hasOwn(topics, topic) ? topic : "";
  return <main className="paper-page"><Header/><section className="inner-hero support-hero"><div className="shell"><h1>What do you need help with?</h1><p>For an active job, include its booking reference so we can review the right details.</p></div></section><section className="section shell support-layout"><nav className="support-topics" aria-label="Support topics">{Object.entries(topics).map(([key,label])=><Link className={selected===key?"button button-orange":"text-link"} key={key} href={`/support?topic=${key}#support-request`}>{label}</Link>)}</nav><div id="support-request"><SupportForm key={selected} initialTopic={selected}/></div></section><Footer/></main>}

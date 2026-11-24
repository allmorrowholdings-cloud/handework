import Link from "next/link";
import { Header } from "../../components/header";
import { Footer } from "../../components/footer";

export default function Pro() {
  return <main className="paper-page"><Header />
    <section className="inner-hero"><div className="shell"><h1>handEwork Pro</h1>
      <p>Your workspace for bookings, availability, earnings and professional evidence.</p>
      <Link className="button button-orange" href="/artisan/dashboard">Open professional workspace</Link>
    </div></section>
    <section className="section shell editorial-grid">{[
      ["/artisan/profile","Professional profile","Set your trade, service area and professional details."],
      ["/artisan/workproof","WorkProof","Manage the evidence behind your professional record."],
      ["/artisan/availability","Availability","Choose the days and hours you can accept work."],
      ["/training","Training","Explore published programmes and their providers."],
    ].map(([href,title,detail])=><article key={href}><h2><Link href={href}>{title}</Link></h2><p>{detail}</p></article>)}</section><Footer /></main>;
}

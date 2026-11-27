import Link from "next/link";
import { Header } from "../components/header";
import { Footer } from "../components/footer";
export const metadata = { title: "Contact handEwork", description: "Get help with handEwork bookings, professional profiles and training." };
export default function ContactPage() {
  return <main className="paper-page"><Header />
    <section className="inner-hero"><div className="shell"><p className="hw-section-label">CONTACT HANDEWORK</p><h1>We are here to help you move forward.</h1><p>Questions about a booking, your professional profile, training or working with handEwork? Start with the right support path.</p></div></section>
    <section className="section shell hw-contact-grid">
      <article><h2>Help with a booking or account</h2><p>Share your job reference and describe what you need. Our support process keeps the issue connected to the right record.</p><Link className="button button-orange" href="/support">Contact support</Link></article>
      <article><h2>Join as a skilled professional</h2><p>Build a visible professional profile and begin documenting your work.</p><Link className="button button-orange" href="/join/artisan">Work with handEwork</Link></article>
      <article><h2>Training and skill development</h2><p>See available programmes and course details from participating providers.</p><Link className="button button-orange" href="/training">Explore training</Link></article>
    </section><Footer /></main>;
}

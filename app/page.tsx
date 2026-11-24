import Link from "next/link";
import { Header } from "./components/header";
import { Footer } from "./components/footer";
import { LocationSearch } from "./components/location-search";

import { services } from "../lib/services";
import { Professionals } from "./components/professionals";
import { DemoVideo } from "./components/demo-video";

export default function Home() {
  return (
    <main className="home-market">
      <Header />
      <section className="hero hero-light" id="top">
        <div className="shell hero-grid hero-grid-visual">
          <div className="hero-copy">
            <h1>Get it done.</h1>
            <p className="hero-lede">Find skilled professionals in Ghana for the things you need fixed, made or maintained.</p>
            <LocationSearch />
          </div>
          <div className="home-hammer" aria-hidden="true">
            <img src="/handework-hammer.webp" width={1024} height={1024} alt="" fetchPriority="high" />
          </div>
        </div>
      </section>

      <nav className="trust-links shell" aria-label="Booking safeguards">
        <Link href="/safety">Professional verification</Link><Link href="/how-it-works">Agreed quotations</Link><Link href="/safety">Completion approval</Link>
      </nav>

      <section className="section shell service-showcase" id="services">
        <div className="section-head"><div><h2>What needs doing?</h2><p>Start with the work. We’ll help you find the right hands.</p></div><Link className="text-link" href="/marketplace">View all services</Link></div>
        <div className="service-visual-grid">{services.map((service) => (
          <Link className="service-visual-card" href={`/marketplace?service=${encodeURIComponent(service.name)}`} key={service.name}>
            <div className="service-visual-media">
              <picture>
                <source media="(prefers-reduced-motion: reduce)" srcSet={`/services/home/stills/${service.image}.webp`} />
                <img src={`/services/home/${service.image}.webp`} alt="" loading="lazy" decoding="async" />
              </picture>
            </div>
            <div className="service-visual-copy"><div><h3>{service.name}</h3><p>{service.note}</p></div></div>
          </Link>
        ))}</div>
      </section>

      <Professionals />

      <section className="shell journey-story" id="how-it-works">
        <h2>How it works</h2>
        <ol><li><strong>Describe the work</strong><p>Tell us what needs attention, where the job is and when you need help.</p></li>
          <li><strong>Agree on the details</strong><p>Review the professional, scope and quote before committing to payment.</p></li>
          <li><strong>Review the result</strong><p>Follow the job record, check the finished work and approve completion or raise a concern.</p></li></ol>
      </section>
      <section className="demo-band"><div className="shell demo-layout">
        <div><h2>See good work<br />in action.</h2><p>Follow a job from the first request to the finishing touches.</p><Link className="text-link" href="/bookings/new">Describe your job</Link></div>
        <DemoVideo />
      </div></section>
      <section className="shell reputation-story">
        <div><h2>Good work leaves proof.</h2><p>Look for WorkProof on a professional&apos;s profile. It brings together completed bookings, reviewed work evidence and customer feedback so you can see the experience behind the name.</p><Link className="text-link" href="/marketplace">Explore professionals</Link></div>
        <div><h2>Your skill. Your future.</h2><p>Set your service area, respond to requests and build a record of the work you deliver.</p><Link className="text-link" href="/join/artisan">Join as a professional</Link></div>
      </section>
      <section className="shell ecosystem-links" aria-label="Professional resources"><Link href="/artisan/pro">Professional workspace</Link><Link href="/shop">Artisan shop</Link><Link href="/training">Training opportunities</Link></section>
      <section className="shell booking-faq"><h2>Before you book</h2>
        <details><summary>When do I pay?</summary><p>Describing a job is free. Once you accept a quote, the booking shows the payment step. Paying for the job and approving release to the professional are separate actions.</p></details>
        <details><summary>What if the price changes?</summary><p>Review the proposed change in your booking before agreeing to the new amount. Your decision stays with the job record.</p></details>
        <details><summary>What if someone misses the appointment or the work needs attention?</summary><p>Keep the messages and photos with your booking and contact <Link href="/support">support</Link> with the reference. Support can review the record and explain the next step.</p></details>
      </section>
      <section className="final-cta"><div className="shell final-inner"><div><h2>Ready to get it done?</h2></div><Link className="button button-cream" href="/marketplace">Find an artisan</Link></div></section>
      <Footer />
    </main>
  );
}

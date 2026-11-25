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

      <section className="home-process" id="how-it-works" aria-labelledby="home-process-title">
        <div className="shell home-process-grid">
          <div className="home-process-copy">
            <span className="home-eyebrow">A simpler way to get things done</span>
            <h2 id="home-process-title">How it works</h2>
            <ol className="home-steps">
              <li>
                <span className="home-step-number" aria-hidden="true">01</span>
                <div>
                  <h3>Describe the work</h3>
                  <p>Tell us what needs attention, where the job is and when you need help.</p>
                </div>
              </li>
              <li>
                <span className="home-step-number" aria-hidden="true">02</span>
                <div>
                  <h3>Agree on the details</h3>
                  <p>Review the professional, scope and quote before committing to payment.</p>
                </div>
              </li>
              <li>
                <span className="home-step-number" aria-hidden="true">03</span>
                <div>
                  <h3>Review the result</h3>
                  <p>Follow the job record, check the finished work and approve completion or raise a concern.</p>
                </div>
              </li>
            </ol>
            <Link className="home-process-cta" href="/bookings/new">
              Describe your job <span aria-hidden="true">→</span>
            </Link>
          </div>
          <div className="home-process-media">
            <DemoVideo />
          </div>
        </div>
      </section>
      <nav className="trust-links shell" aria-label="Booking safeguards">
        <Link href="/safety">Professional verification</Link><Link href="/how-it-works">Agreed quotations</Link><Link href="/safety">Completion approval</Link>
      </nav>

      <section className="section shell service-showcase" id="services">
        <div className="section-head"><div><h2>What needs doing?</h2><p>Start with the work. We’ll help you find the right hands.</p></div><Link className="text-link" href="/marketplace">View all services</Link></div>
        <div className="service-visual-grid">{services.filter((service) => service.name !== "Catering").map((service) => (
          <Link className="service-visual-card" href={`/marketplace?service=${encodeURIComponent(service.name)}`} key={service.name}>
            <div className="service-visual-media">
              <img
                src={`/services/home/drive/${service.image}.webp`}
                alt=""
                loading="lazy"
                decoding="async"
                width={960}
                height={640}
              />
            </div>
            <div className="service-visual-copy"><div><h3>{service.name}</h3><p>{service.note}</p></div></div>
          </Link>
        ))}</div>
      </section>

      <Professionals />

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

import Link from "next/link";
import { Header } from "./components/header";
import { Footer } from "./components/footer";
import { LocationSearch } from "./components/location-search";

import { services } from "../lib/services";
import { Professionals } from "./components/professionals";
import { DemoVideo } from "./components/demo-video";
import { WorkforceSignal } from "./components/workforce-signal";
import { PlatformTicker } from "./components/platform-ticker";
import { SafetyVideo } from "./components/safety-video";
import { PwaHomeGate } from "./components/pwa-home-gate";


export default function Home() {
  return (
    <PwaHomeGate><main className="home-market">
      <Header />
      <section className="hero hero-light" id="top">
        <div className="shell hero-grid hero-grid-visual">
          <div className="hero-copy">
            <h1>Get it done.</h1>
            <p className="hero-lede">Find skilled professionals for the things you need fixed, made or maintained.</p>
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

            <h2 id="home-process-title">How it works</h2>
            <ol className="home-steps">
              <li>
                <span className="home-step-number" aria-hidden="true">01</span>
                <div>
                  <h3>Describe your job</h3>
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

      {/* HANDEWORK_PWA_GPS_INTEGRATIONS_2026 */}
      <PlatformTicker />
      <section className="section shell service-showcase" id="services">
        <div className="section-head"><div><h2>What needs doing?</h2><p>Start with the work. We’ll help you find the right hands.</p></div><Link className="text-link" href="/marketplace">View all services</Link></div>
        <div className="service-visual-grid">{services.filter((service) => service.name !== "Catering").map((service) => (
          <Link className="service-visual-card" href={`/marketplace?service=${encodeURIComponent(service.name)}`} key={service.name}>
            <div className="service-visual-media">
              <picture>
                <source media="(prefers-reduced-motion: reduce)" srcSet={`/services/home/animated/stills/${service.image}.webp`} />
                <img
                  src={`/services/home/animated/${service.image}.webp`}
                  alt=""
                  loading="lazy"
                  decoding="async"
                  width={360}
                  height={240}
                />
              </picture>
            </div>
            <div className="service-visual-copy"><div><h3>{service.name}</h3><p>{service.note}</p></div></div>
          </Link>
        ))}</div>
      </section>

      <section className="home-evidence" aria-labelledby="home-evidence-title">
        <div className="shell">
          <h2 id="home-evidence-title">A stronger future for skilled work.</h2>
          <div className="home-workforce-signal" aria-label="National workforce context">
            <WorkforceSignal />
          </div>
        </div>
      </section>
      <Professionals />

      <section className="home-workproof" aria-labelledby="home-workproof-title">
        <div className="shell home-workproof-grid">
          <div className="home-workproof-intro">
            <h2 id="home-workproof-title">Good work leaves proof.</h2>
            <p>Skills deserve recognition. Build your work history, portfolio and reputation with every completed job.</p>
            <div className="home-workproof-actions">
              <Link href="/join/artisan" className="home-process-cta">Build your reputation</Link>
            </div>
          </div>
          <div className="home-workproof-illustration">
            <img src="/workproof-kwame-illustration.png" width={1122} height={1402} loading="lazy" decoding="async" alt="Illustrative WorkProof interface concept. The person, job counts, reviews and ratings shown are examples, not real handEwork records." />
          </div>
        </div>
      </section>
      {/* HANDEWORK_SAFETY_DRIVE_EMBED_2026 */}
      <section
        className="home-safety"
        aria-labelledby="home-safety-title"
      >
        <div className="shell home-safety-inner">
          <div className="home-safety-heading">

            <h2 id="home-safety-title">
              Know how your job is protected.
            </h2>

            <p>
              From professional verification to clearer
              job records and support, see how handEwork
              helps you manage work with confidence.
            </p>
          </div>

          <SafetyVideo />

          <Link href="/safety" className="home-safety-link">
            Explore safety and trust

          </Link>
        </div>
      </section>


      <section className="shell booking-faq" aria-labelledby="home-faq-title">
        <div className="home-faq-heading">
          <h2 id="home-faq-title">Before you book</h2>
          <p>A few answers to help you get started.</p>
        </div>
        <div className="home-faq-list">
          <details>
            <summary>When do I pay?</summary>
            <p>Describing a job is free. Once you accept a quote, the booking shows the payment step. Paying for the job and approving release to the professional are separate actions.</p>
          </details>
          <details>
            <summary>What if the price changes?</summary>
            <p>Review the proposed change in your booking before agreeing to the new amount. Your decision stays with the job record.</p>
          </details>
          <details>
            <summary>What if someone misses the appointment or the work needs attention?</summary>
            <p>Keep the messages and photos with your booking and contact <Link href="/support">support</Link> with the reference. Support can review the record and explain the next step.</p>
          </details>
          <details>
            <summary>How can I tell whether a professional has been verified?</summary>
            <p>Look for a verified status on the professional&apos;s profile. Verification involves reviewing identity and trade information, but it is not a guarantee of a particular outcome. Review their work details and keep your agreements inside the booking.</p>
          </details>
          <details>
            <summary>What if I cannot find someone available for my job?</summary>
            <p>Try another location, service or distance in <Link href="/marketplace">Find an artisan</Link>. You can also <Link href="/bookings/new">describe your job</Link> to start a request. Availability and responses depend on real professionals using handEwork.</p>
          </details>
        </div>
      </section>
      <section className="final-cta"><div className="shell final-inner"><div><h2>Ready to get it done?</h2></div><Link className="button button-cream" href="/marketplace">Find an artisan</Link></div></section>
      <Footer />
    </main></PwaHomeGate>
  );
}

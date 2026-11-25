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
          <span className="home-eyebrow">Skilled work matters</span>
          <h2 id="home-evidence-title">A stronger future for skilled work.</h2>
          <p className="home-evidence-lede">
            Ghana's tradespeople keep homes, businesses and communities moving.
            handEwork brings clearer service discovery and professional work records.
          </p>
          <div className="home-evidence-grid">
            <div>
              <strong>1.6M+</strong>
              <span>Craft and related trades workers in Ghana</span>
              <small>Ghana Statistical Service, 2021 Census — national workforce, not handEwork registrations</small>
            </div>
            <div>
              <strong>8</strong>
              <span>Featured service categories</span>
              <small>Explore skilled services on handEwork</small>
            </div>
            <div>
              <strong>3</strong>
              <span>Clear steps in the booking journey</span>
              <small>Describe, agree and review</small>
            </div>
          </div>
          <a className="home-evidence-source"
             href="https://census2021.statsghana.gov.gh/gssmain/fileUpload/reportthemesub/2021%20PHC%20General%20Report%20Vol%203E_Economic%20Activity.pdf"
             target="_blank" rel="noopener noreferrer">
            Source: Ghana Statistical Service, 2021 Population and Housing Census
          </a>
        </div>
      </section>
      <Professionals />

      <section className="home-workproof" aria-labelledby="home-workproof-title">
        <div className="shell home-workproof-grid">
          <div className="home-workproof-intro">
            <span className="home-eyebrow">WorkProof by handEwork</span>
            <h2 id="home-workproof-title">Good work leaves proof.</h2>
            <p>Skills deserve recognition. Explore completed work, approved portfolio evidence and customer feedback where available on verified professional profiles.</p>
            <div className="home-workproof-actions">
              <Link href="/marketplace" className="home-process-cta">Explore professionals <span aria-hidden="true">→</span></Link>
              <Link href="/join/artisan" className="home-workproof-link">Build your reputation</Link>
            </div>
          </div>
          <div className="home-workproof-panel">
            <div className="home-workproof-panel-head">
              <span className="home-workproof-brand">h<span>E</span></span>
              <strong>WorkProof</strong>
              <small>Professional credibility</small>
            </div>
            <div className="home-workproof-feature">
              <span>01</span>
              <div><h3>Completed work</h3><p>See recorded jobs completed through handEwork.</p></div>
            </div>
            <div className="home-workproof-feature">
              <span>02</span>
              <div><h3>Portfolio evidence</h3><p>Explore reviewed examples of professional work.</p></div>
            </div>
            <div className="home-workproof-feature">
              <span>03</span>
              <div><h3>Customer feedback</h3><p>Read published reviews where available.</p></div>
            </div>
            <p className="home-workproof-disclaimer">Feature overview, not a fictional professional profile.</p>
          </div>
        </div>
      </section>
      <section className="shell ecosystem-links" aria-label="Professional resources"><Link href="/artisan/pro">Professional workspace</Link><Link href="/shop">Artisan shop</Link><Link href="/training">Training opportunities</Link></section>
      <section className="shell booking-faq" aria-labelledby="home-faq-title">
        <div className="home-faq-heading">
          <span className="home-eyebrow">Good to know</span>
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
        </div>
      </section>
      <section className="final-cta"><div className="shell final-inner"><div><h2>Ready to get it done?</h2></div><Link className="button button-cream" href="/marketplace">Find an artisan</Link></div></section>
      <Footer />
    </main>
  );
}

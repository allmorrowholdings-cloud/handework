import Link from "next/link";
import { Header } from "./components/header";
import { Footer } from "./components/footer";
import { LocationSearch } from "./components/location-search";

const services: Array<{code:string;name:string;note:string;image:string|null;visual?:"paint"|"masonry"}> = [
  { code: "01", name: "Plumbing", note: "Stop leaks and fit new taps.", image: "/services/home/plumbing.gif" },
  { code: "02", name: "Carpentry", note: "Fix doors or commission furniture.", image: "/services/home/carpentry.gif" },
  { code: "03", name: "Welding", note: "Repair gates or build custom metalwork.", image: "/services/home/welding.webp" },
  { code: "04", name: "Painting", note: "Refresh rooms and exterior walls.", image: "/services/home/painting.webp" },
  { code: "05", name: "Masonry", note: "Build block walls and patch plaster.", image: "/services/home/masonry.gif" },
  { code: "06", name: "Tailoring", note: "Alter clothes or get a custom fit.", image: "/services/home/tailoring.gif" },
  { code: "07", name: "Hairdressing", note: "Book braids, cuts, or styling.", image: "/services/home/hair-beauty.webp" },
  { code: "08", name: "Makeup artist", note: "Get makeup for events and photos.", image: "/services/home/makeup.webp" },
  { code: "09", name: "Catering", note: "Feed your guests without the cooking.", image: "/services/home/food-events.webp" },
];

const safeguards = [
  ["Identity checked", "Artisans submit an ID, a live photo and their trade details before receiving the verified mark."],
  ["Money held safely", "Payment stays in handEwork escrow until the agreed work is completed and approved."],
  ["Work recorded", "Scope, chat, progress photos, changes and approvals remain attached to the booking."],
];

export default function Home() {
  return (
    <main className="home-market">
      <Header />
      <section className="hero hero-light" id="top">
        <div className="hero-noise" aria-hidden="true" />
        <div className="shell hero-grid hero-grid-visual">
          <div className="hero-copy">
            <span className="hero-kicker">Repairs, installations &amp; custom work</span>
            <h1>Get work done<br />with skilled hands.</h1>
            <p className="hero-lede">Find local artisans. See their past work, agree on the price and materials, and follow the job in one place.</p>
            <LocationSearch />
            <p><Link className="text-link" href="/bookings/new">Describe a job instead <span aria-hidden="true">→</span></Link></p>
            <div className="hero-quick">
              <span>Popular:</span>
              <Link href="/marketplace?service=Plumbing">Plumbing</Link>
              <Link href="/marketplace?service=Hairdressing">Hairdressing</Link>
              <Link href="/marketplace?service=Carpentry">Carpentry</Link>
            </div>
          </div>

          <div className="home-hammer">
            <picture>
              <img src="/handework-hammer.webp" alt="A hand gripping a hammer breaks through concrete" width={1024} height={1024} />
            </picture>
          </div>
        </div>
      </section>

      <section className="section shell service-showcase" id="services">
        <div className="section-head"><div><h2>What needs doing?</h2><p>Start with the work. We’ll help you find the right hands.</p></div><Link className="text-link" href="/marketplace">View all services <span>↗</span></Link></div>
        <div className="service-visual-grid">{services.map((service) => (
          <Link className="service-visual-card" href={`/marketplace?service=${encodeURIComponent(service.name)}`} key={service.name}>
            <div className={`service-visual-media ${service.visual ? `service-visual-generated ${service.visual}` : ""}`}>{service.image ? <img src={service.image} alt="" loading="lazy" /> : <div className="service-material-art" aria-hidden="true"><span /><span /><span /></div>}</div>
            <div className="service-visual-copy"><span className="service-code">{service.code}</span><div><h3>{service.name}</h3><p>{service.note}</p></div><span className="service-arrow" aria-hidden="true">↗</span></div>
          </Link>
        ))}</div>
      </section>

      <section className="job-card-band">
        <div className="shell job-card-layout">
          <div>
            <h2>One job card. No chasing for answers.</h2>
            <p>The quote, messages, photos, and approval stay with the job, so you and your artisan can see what changed and what you agreed to.</p>
          </div>
          <div className="work-order" aria-label="How handEwork booking works">
            <div className="ticket-top"><span>handEwork / JOB CARD</span><strong>EXAMPLE</strong></div>
            <div className="ticket-body">
              <span className="ticket-number">#001</span>
              <h3>Fix a leaking kitchen tap</h3>
              <ol>
                <li><b>01</b><span><strong>Work agreed</strong><small>Replace the worn seal and check for leaks.</small></span></li>
                <li><b>02</b><span><strong>Repair photo added</strong><small>The artisan shares the finished work.</small></span></li>
                <li><b>03</b><span><strong>Work approved</strong><small>The customer confirms the leak is fixed. Payment is released.</small></span></li>
              </ol>
            </div>
            <div className="ticket-edge"><span>Built for the hands that build</span><span>handEwork</span></div>
          </div>
        </div>
      </section>

      <section className="section proof-section" id="trust"><div className="shell proof-grid">
        <div className="proof-intro"><h2>Hire with confidence.</h2><p>handEwork keeps the important parts visible to both sides. No scattered screenshots. No unclear payment promises.</p><Link className="button button-orange" href="/how-it-works">See how protection works</Link></div>
        <div className="proof-list">{safeguards.map(([title, detail], index) => <article key={title}><span>0{index + 1}</span><div><h3>{title}</h3><p>{detail}</p></div></article>)}</div>
      </div></section>

      <section className="section shell artisan-call" id="artisans">
        <div className="artisan-lettering" aria-hidden="true">HANDS</div>
        <div className="artisan-copy"><h2>Your skill should be easier to find.</h2><p>Create a verified work profile, set where and when you work, receive bookings, build a public record and get paid without chasing.</p><div className="button-row"><Link className="button button-dark" href="/join/artisan">Join as an artisan</Link><Link className="text-link" href="/artisan/pro">Explore handEwork Pro <span>↗</span></Link></div></div>
        <div className="artisan-board"><div className="board-label">WORK PROFILE</div><div className="board-line"><span>01</span><b>Show proof, not paperwork</b></div><div className="board-line"><span>02</span><b>Choose your radius and hours</b></div><div className="board-line"><span>03</span><b>Keep work and earnings together</b></div><div className="board-stamp">SKILL<br />COUNTS.</div></div>
      </section>

      <section className="shop-teaser section"><div className="shell shop-teaser-grid">
        <div><h2>Tools made easier to own.</h2><p>Browse branded trade tools, kits and essentials at discounted prices. Shop by craft, add to cart, then choose delivery or office pickup.</p><div className="button-row"><Link className="button button-orange" href="/shop">Explore the artisan shop</Link><Link className="text-link" href="/join/artisan">Work with handEwork <span>↗</span></Link></div></div>
        <div className="shop-teaser-art"><img src="/artisan-toolbox.webp" alt="Patterned wooden toolbox filled with hand tools" loading="lazy" width={960} height={960} /></div>
      </div></section>

      <section className="final-cta"><div className="shell final-inner"><div><h2>Ready to get it done?</h2></div><Link className="button button-cream" href="/marketplace">Find an artisan <span>→</span></Link></div></section>
      <Footer />
    </main>
  );
}

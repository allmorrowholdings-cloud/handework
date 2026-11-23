import Link from "next/link";
import { Header } from "./components/header";
import { Footer } from "./components/footer";
import { LocationSearch } from "./components/location-search";

const services = [
  { code: "01", name: "Plumbing", note: "Stop leaks and fit new taps.", image: "plumbing" },
  { code: "02", name: "Carpentry", note: "Fix doors or commission furniture.", image: "carpentry" },
  { code: "03", name: "Welding", note: "Repair gates or build custom metalwork.", image: "welding" },
  { code: "04", name: "Painting", note: "Refresh rooms and exterior walls.", image: "painting" },
  { code: "05", name: "Masonry", note: "Build block walls and patch plaster.", image: "masonry" },
  { code: "06", name: "Tailoring", note: "Alter clothes or get a custom fit.", image: "tailoring" },
  { code: "07", name: "Hairdressing", note: "Book braids, cuts, or styling.", image: "hair-beauty" },
  { code: "08", name: "Makeup artist", note: "Get makeup for events and photos.", image: "makeup" },
  { code: "09", name: "Catering", note: "Feed your guests without the cooking.", image: "food-events" },
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
            <span className="hero-kicker">Artisan services in Ghana</span>
            <h1>Get work done<br />with skilled hands.</h1>
            <p className="hero-lede">Find a verified artisan near you. Agree on the work and materials, follow the repair photos, and approve the finished job.</p>
            <LocationSearch />
          </div>
          <article className="hero-job-example" aria-labelledby="example-job-title">
            <header><span>Example job card</span><img src="/handework-hammer.webp" width="80" height="80" alt="" /></header>
            <h2 id="example-job-title">A leaking kitchen tap in Osu</h2>
            <dl>
              <div><dt>Scope</dt><dd>Replace the worn seal and test the tap.</dd></div>
              <div><dt>Quote</dt><dd>You agree on labour and materials before work begins.</dd></div>
              <div><dt>Sign-off</dt><dd>Review the repair photo and confirm the leak is fixed.</dd></div>
            </dl>
          </article>
        </div>
      </section>

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
            <div className="service-visual-copy"><span className="service-code">{service.code}</span><div><h3>{service.name}</h3><p>{service.note}</p></div></div>
          </Link>
        ))}</div>
      </section>

      <section className="section proof-section" id="trust"><div className="shell proof-grid">
        <div className="proof-intro"><h2>Hire with confidence.</h2><p>handEwork keeps the important parts visible to both sides. No scattered screenshots. No unclear payment promises.</p><Link className="button button-orange" href="/how-it-works">See how protection works</Link></div>
        <div className="proof-list">{safeguards.map(([title, detail], index) => <article key={title}><span>0{index + 1}</span><div><h3>{title}</h3><p>{detail}</p></div></article>)}</div>
      </div></section>

      <section className="section shell artisan-call" id="artisans">
        <div className="artisan-lettering" aria-hidden="true">HANDS</div>
        <div className="artisan-copy"><h2>Your skill should be easier to find.</h2><p>Create a verified work profile, set where and when you work, receive bookings, build a public record and get paid without chasing.</p><div className="button-row"><Link className="button button-dark" href="/join/artisan">Join as an artisan</Link><Link className="text-link" href="/artisan/pro">Explore handEwork Pro</Link></div></div>
        <div className="artisan-board"><div className="board-label">WORK PROFILE</div><div className="board-line"><span>01</span><b>Show proof, not paperwork</b></div><div className="board-line"><span>02</span><b>Choose your radius and hours</b></div><div className="board-line"><span>03</span><b>Keep work and earnings together</b></div><div className="board-stamp">SKILL<br />COUNTS.</div></div>
      </section>

      <section className="shop-teaser section"><div className="shell shop-teaser-grid">
        <div><h2>Tools made easier to own.</h2><p>Browse branded trade tools, kits and essentials at discounted prices. Shop by craft, add to cart, then choose delivery or office pickup.</p><div className="button-row"><Link className="button button-orange" href="/shop">Explore the artisan shop</Link><Link className="text-link" href="/join/artisan">Work with handEwork</Link></div></div>
        <div className="shop-teaser-art"><img src="/artisan-toolbox.webp" alt="Patterned wooden toolbox filled with hand tools" loading="lazy" width={960} height={960} /></div>
      </div></section>

      <section className="final-cta"><div className="shell final-inner"><div><h2>Ready to get it done?</h2></div><Link className="button button-cream" href="/marketplace">Find an artisan</Link></div></section>
      <Footer />
    </main>
  );
}

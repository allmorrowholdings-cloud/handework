import Link from "next/link";
import { Header } from "./components/header";
import { Footer } from "./components/footer";
import { LocationSearch } from "./components/location-search";

import { services } from "../lib/services";
import { DemoVideo } from "./components/demo-video";

export default function Home() {
  return (
    <main className="home-market">
      <link rel="preconnect" href="https://embed.figma.com" />
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
          <div className="home-hammer" aria-hidden="true">
            <img src="/handework-hammer.webp" width={1024} height={1024} alt="" fetchPriority="high" />
          </div>
        </div>
      </section>

      <section className="section shell homepage-demos" id="trust" aria-label="handEwork demos">
        <div>
          <h2>Try the handEwork prototype</h2>
          <iframe
            className="prototype-player"
            title="Interactive handEwork prototype on Figma"
            src="https://embed.figma.com/proto/j0w4a2nKe5XfVyq7xF9SAH/Untitled?node-id=8-3&p=f&scaling=fit-width&footer=false&viewport-controls=false&content-scaling=fixed&page-id=6%3A3&starting-point-node-id=8%3A2&embed-host=share"
            width="390"
            height="844"
            loading="eager"
            allowFullScreen
          />
        </div>
        <DemoVideo />
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

import { Header } from "../components/header";
import { Footer } from "../components/footer";
import { ShopClient } from "./shop-client";

export default function ShopPage(){
  return <main className="shop-page"><Header/><section className="shop-hero"><div className="shell shop-hero-grid"><div><h1>Better tools.<br/>Better work.</h1><p>Branded tools, trade kits and essentials priced below standard retail for the people who build, repair, create and serve.</p></div><div className="shop-hero-art"><img src="/services/welding.png" alt="handEwork branded welding tools"/></div></div></section><ShopClient/><section className="shop-artisan-cta"><div className="shell"><div><h2>Work with handEwork.</h2><p>Verified artisans can build WorkProof, receive jobs and unlock artisan-only offers.</p></div><a className="button button-cream" href="/join/artisan">Join as an artisan →</a></div></section><Footer/></main>
}

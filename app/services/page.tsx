import Link from "next/link";
import { Header } from "../components/header";
import { Footer } from "../components/footer";
import { serviceGuides } from "../../lib/service-guides";
export const metadata = {title:"Find skilled services in Ghana",description:"Explore service guides for plumbing, electrical work, AC repair, CCTV, cleaning, architecture and more. Prepare a job request with handEwork.",alternates:{canonical:"/services"}};
export default function ServicesPage(){return <main className="paper-page"><Header/><section className="shell hw-growth-intro"><p className="hw-section-label">THE RIGHT HANDS FOR THE JOB</p><h1>What needs doing?</h1><p>Explore skilled services, understand what to include in your request and check for suitable professionals in your area.</p></section><section className="shell hw-guide-grid" aria-label="Service guides">{serviceGuides.map(s=><Link className="hw-growth-card" key={s.slug} href={`/services/${s.slug}`}><h2>{s.name}</h2><p>{s.intro}</p><span>Explore service →</span></Link>)}</section><Footer/></main>}

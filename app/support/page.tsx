import { Header } from "../components/header";
import { Footer } from "../components/footer";
import { SupportForm } from "./support-form";

export default function Support(){return <main className="paper-page"><Header/><section className="inner-hero support-hero"><div className="shell"><h1>What do you need help with?</h1><p>For an active job, open the booking first. That keeps your scope, payment and messages attached to the support request.</p></div></section><section className="section shell support-layout"><div className="support-topics">{["A booking or artisan","Payment, refund or payout","Account or verification","Safety concern","Business account","TVET partnership"].map((item)=><button type="button" key={item}>{item}<span>→</span></button>)}</div><SupportForm/></section><Footer/></main>}

import { SupportForm } from "../support/support-form";
import { Header } from "../components/header";
import { Footer } from "../components/footer";
export const metadata = {title:"Contact and support",description:"Get help with handEwork bookings, accounts, payments, verification and training partnerships.",alternates:{canonical:"/contact"}};
export default function ContactPage(){return <main className="paper-page hw-contact-page"><Header/><section className="shell hw-contact-single"><aside><h1>Good work starts with a conversation.</h1><p>Need help with a job, your account or a partnership? Tell us how we can help.</p><h2>Get it done with skilled hands.</h2><p>For immediate danger, contact local emergency services first.</p></aside><div id="support-request"><SupportForm/></div></section><Footer/></main>}

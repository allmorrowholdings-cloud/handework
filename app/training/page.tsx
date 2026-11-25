import Link from "next/link";
import { TrainingLinks } from "./training-links";
import { Header } from "../components/header";
import { Footer } from "../components/footer";
import { LiveRecords } from "../components/live-records";

export default function Training() {
  return <main className="paper-page">
    <Header />
    <section className="inner-hero"><div className="shell"><h1>Find the next skill or prove the one you have.</h1><p>handEwork partners with approved TVET institutions and training providers. Courses appear only after the institution and programme are verified.</p></div></section>
    <section className="section shell"><div className="app-card training-empty"><LiveRecords endpoint="/v1/training/courses" emptyTitle="No verified course published yet" emptyText="Live enrolment dates, city, fees, delivery method and issuing institution appear after provider approval." variant="training" /></div></section>
    <section className="section shell"><h2>Training resources and course materials</h2><TrainingLinks/><Link className="text-link" href="/submissions?purpose=training_resource">Submit a Google Drive resource</Link></section>
    <Footer />
  </main>;
}

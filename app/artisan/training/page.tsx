import Link from "next/link";
import { AppShell } from "../../components/app-shell";
import { LiveRecords } from "../../components/live-records";
import { TrainingLinks } from "../../training/training-links";
export default function ArtisanTraining(){return <AppShell role="artisan" title="Training" note="Find the next skill or prove the one you have."><section className="app-content"><div className="app-card"><h2>Verified training opportunities</h2><p>Courses appear only after the institution and programme are verified.</p><LiveRecords endpoint="/v1/training/courses" emptyTitle="No verified course published yet" emptyText="Live enrolment dates, city, fees, delivery method and issuing institution appear after provider approval." variant="training"/></div><div className="app-card"><h2>Training resources and course materials</h2><TrainingLinks/><Link href="/submissions?purpose=training_resource">Submit a Google Drive resource</Link></div></section></AppShell>}

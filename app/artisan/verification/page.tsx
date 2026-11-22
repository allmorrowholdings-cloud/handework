import { AppShell } from "../../components/app-shell";import { VerificationManager } from "./manager";
export default function Verification(){return <AppShell role="artisan" title="Verification" note="Identity checks protect customers, artisans and payouts."><section className="app-content narrow-content"><VerificationManager/></section></AppShell>}

import { AppShell } from "../components/app-shell";
import { ReferralPanel } from "./referral-panel";
export default function Referrals(){return <AppShell title="Referrals & promo codes" note="Valid rewards are created by the API after eligibility checks."><section className="app-content"><ReferralPanel/></section></AppShell>}

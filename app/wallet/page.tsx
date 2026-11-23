import { AppShell } from "../components/app-shell";
import { WalletPanel } from "./wallet-panel";
export default function WalletPage(){return <AppShell title="Wallet & payments" note="See the payments and transfers recorded for your jobs."><section className="app-content"><WalletPanel/></section></AppShell>}

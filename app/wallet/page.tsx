import { AppShell } from "../components/app-shell";
import { WalletPanel } from "./wallet-panel";
export default function WalletPage(){return <AppShell title="Wallet & payments" note="Mobile-money charges, escrow holds, refunds and payouts are reconciled from provider webhooks."><section className="app-content"><WalletPanel/></section></AppShell>}

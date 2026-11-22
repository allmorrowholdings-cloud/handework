import { AppShell } from "../../components/app-shell";
import { WalletPanel } from "../../wallet/wallet-panel";

export default function ArtisanEarningsPage(){
  return <AppShell role="artisan" title="Earnings" note="Completed-job releases, available balance and payout ledger for your artisan account."><section className="app-content"><WalletPanel/></section></AppShell>;
}

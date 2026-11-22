import { AppShell } from "../../components/app-shell";import { PortfolioManager } from "./manager";
export default function Portfolio(){return <AppShell role="artisan" title="Portfolio" note="Upload only work you completed and have permission to publish."><section className="app-content"><PortfolioManager/></section></AppShell>}

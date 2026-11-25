import { AppShell } from "../../components/app-shell";import { PortfolioManager } from "./manager";
import Link from "next/link";
export default function Portfolio(){return <AppShell role="artisan" title="Portfolio" note="Upload only work you completed and have permission to publish."><section className="app-content"><PortfolioManager/><Link className="text-link" href="/submissions?purpose=portfolio">Submit or manage a Google Drive portfolio link</Link></section></AppShell>}

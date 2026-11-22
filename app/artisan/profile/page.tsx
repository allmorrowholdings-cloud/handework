import { AppShell } from "../../components/app-shell";import { ProfileEditor } from "./editor";
export default function ArtisanProfile(){return <AppShell role="artisan" title="Work profile" note="This information controls how customers understand and find your services."><section className="app-content narrow-content"><ProfileEditor/></section></AppShell>}

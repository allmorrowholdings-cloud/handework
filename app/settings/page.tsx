import { AppShell } from "../components/app-shell";
import { AccountSettings } from "./account-settings";
export default function Settings(){return <AppShell title="Account settings" note="Manage your profile, privacy, communication and security."><section className="app-content narrow-content"><AccountSettings/></section></AppShell>}

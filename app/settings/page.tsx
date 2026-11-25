import { BrowserPushSettings } from "./browser-push-settings";
import { AuthenticatorSettings } from "./authenticator-settings";
import { AppShell } from "../components/app-shell";
import { AccountSettings } from "./account-settings";

export default function Settings() {
  return (
    <AppShell title="Settings" note="Make handEwork work the way you do.">
      <section className="app-content hw-settings">
        <aside className="hw-settings-nav">
          <span className="hw-kicker">YOUR ACCOUNT</span>
          <h2>Preferences</h2>
          <nav aria-label="Settings navigation">
            <a href="#personal">Personal details <span>01</span></a>
            <a href="#security">Account security <span>02</span></a>
            <a href="#notifications">Browser notifications <span>03</span></a>
          </nav>
          <div className="hw-settings-note">
            <strong>Built around you.</strong>
            <p>Manage how you access handEwork and stay connected.</p>
          </div>
        </aside>
        <div className="hw-settings-body">
          <div id="personal"><AccountSettings /></div>
          <div id="security"><AuthenticatorSettings /></div>
          <div id="notifications"><BrowserPushSettings /></div>
        </div>
      </section>
    </AppShell>
  );
}

"use client";
import {useInstalledApp} from "./components/installed-app-mode";
export default function Loading(){const installed=useInstalledApp();return installed?<div className="hw-app-page-loader" role="status" aria-label="Opening handEwork"><img src="/app-welcome-logo.svg" alt="" width={240} height={80}/></div>:<p role="status" className="shell">Loading…</p>}

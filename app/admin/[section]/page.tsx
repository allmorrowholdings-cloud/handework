import { AppShell } from "../../components/app-shell";
import { LiveRecords } from "../../components/live-records";

const sections = {
  verifications: { title: "KYC queue", empty: "No verification waiting", text: "Government ID, live selfie, trade proof and payout-name checks appear here." },
  disputes: { title: "Dispute desk", empty: "No open dispute", text: "Cases retain their booking, evidence, resolution and financial-action audit trail." },
  payments: { title: "Payment exceptions", empty: "No payment exception", text: "Pending, failed and refund-pending transactions appear here for reconciliation." },
  risk: { title: "Risk review", empty: "No risk event waiting", text: "Blocked and review-level signals appear here for a human decision." },
  analytics: { title: "Live analytics", empty: "No analytics response", text: "Booking, completion, payment, dispute and verification totals load from the admin API." },
} as const;

export default async function AdminSection({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  const copy = sections[section as keyof typeof sections] ?? sections.risk;

  return <AppShell role="admin" title={copy.title} note="Protected by the server-side admin role and recorded in the audit log.">
    <section className="app-content">
      <div className="app-card full-card">
        <div className="card-head"><h2>Current records</h2></div>
        <LiveRecords endpoint={`/v1/admin/${section}`} emptyTitle={copy.empty} emptyText={copy.text} variant="admin" />
      </div>
    </section>
  </AppShell>;
}

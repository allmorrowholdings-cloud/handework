import { AppShell } from "../../components/app-shell";
import { LiveRecords } from "../../components/live-records";

import { DisputeDesk } from "./dispute-desk";
import { PaymentOperations } from "./payment-operations";
import { notFound } from "next/navigation";
import { VerificationReview } from "./verification-review";
import { DriveReview } from "./drive-review";
import { ShopMediaManager } from "./shop-media";

const sections = {
  "drive-submissions": { title: "Google Drive link review", empty: "", text: "" },
  verifications: { title: "KYC queue", empty: "No verification waiting", text: "Government ID, live selfie, trade proof and payout-name checks appear here." },
  disputes: { title: "Dispute desk", empty: "No open dispute", text: "Cases retain their booking, evidence, resolution and financial-action audit trail." },
  payments: { title: "Payment operations", empty: "No payment exception", text: "Pending, failed and refund-pending transactions appear here for reconciliation." },
  risk: { title: "Risk review", empty: "No risk event waiting", text: "Blocked and review-level signals appear here for a human decision." },
  analytics: { title: "Live analytics", empty: "No analytics response", text: "Booking, payment and verification totals appear here." },
  media: { title: "Shop product media", empty: "No product images", text: "Upload approved product photography for the shop catalog." },
} as const;

export default async function AdminSection({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (!Object.hasOwn(sections, section)) notFound();
  const copy = sections[section as keyof typeof sections];

  return <AppShell role="admin" title={copy.title} note="Review records for this area of operations.">
    <section className="app-content">
      <div className="app-card full-card">
        <div className="card-head"><h2>Current records</h2></div>
        {section === "drive-submissions" ? <DriveReview/> : section === "disputes" ? <DisputeDesk/> : section === "payments" ? <PaymentOperations/> : section === "verifications" ? <VerificationReview /> : section === "media" ? <ShopMediaManager/> : <LiveRecords endpoint={`/v1/admin/${section}`} emptyTitle={copy.empty} emptyText={copy.text} variant="admin" />}
      </div>
    </section>
  </AppShell>;
}

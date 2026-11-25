import Link from "next/link";
import { notFound } from "next/navigation";
import { AccountEmailForm } from "./account-email-form";

export default async function AccountEmailPage({ params }: { params: Promise<{ action: string }> }) {
  const { action } = await params;
  if (action !== "verify" && action !== "reset") notFound();
  return <main className="shell section"><div className="auth-box">
    <h1>{action === "reset" ? "Reset your password" : "Verify your email"}</h1>
    <AccountEmailForm action={action}/>
    <Link href="/auth/sign-in">Back to sign in</Link>
  </div></main>;
}

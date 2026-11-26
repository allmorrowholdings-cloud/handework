import Image from "next/image";

export function AuthSide({ heading = "Every job. Clearly recorded." }: { heading?: string }) {
  return <aside className="auth-art" aria-label="handEwork professionals">
    <Image className="auth-team-image" src="/auth-team.webp" alt="Two skilled professionals with painting and cleaning equipment" width={1122} height={1402} priority />
    <div className="auth-team-shade" aria-hidden="true" />
    <div className="auth-art-caption"><h2>{heading}</h2></div>
  </aside>;
}

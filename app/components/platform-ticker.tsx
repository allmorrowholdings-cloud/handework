export function PlatformTicker() {
  const providers = ["Supabase", "Vercel", "Gmail", "Paystack", "Firebase"];
  return <section className="hw-platforms" aria-labelledby="hw-platforms-heading">
    <div className="shell hw-platforms-intro">
      <h2 id="hw-platforms-heading">Technology behind handEwork</h2>
      <p>Platforms and services referenced by our application. Their inclusion does not imply endorsement.</p>
    </div>
    <div className="hw-platforms-window" aria-label="Supabase, Vercel, Gmail, Paystack, Firebase">
      <div className="hw-platforms-track">
        {[...providers, ...providers].map((name, index) => <span className="hw-platform-chip" key={`${name}-${index}`} aria-hidden={index >= providers.length}>{name}</span>)}
      </div>
    </div>
  </section>;
}

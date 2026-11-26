const platforms = [
  { name: "Gmail", src: "/platform-logos/gmail.png" },
  { name: "Vercel", src: "/platform-logos/vercel.png" },
  { name: "Firebase", src: "/platform-logos/firebase.png" },
  { name: "Paystack", src: "/platform-logos/paystack.png" },
];

export function PlatformTicker() {
  return (
    <section className="hw-platforms hw-platform-logos" aria-label="Platforms used by handEwork">
      <div className="hw-platforms-window">
        <div className="hw-platforms-track">
          {[0, 1].map(group => (
            <ul className="hw-platform-logo-list" key={group} aria-hidden={group === 1 ? "true" : undefined}>
              {platforms.map(platform => (
                <li key={platform.name}>
                  <img
                    src={platform.src}
                    alt={group === 0 ? platform.name : ""}
                    width={2048}
                    height={682}
                    loading="lazy"
                    decoding="async"
                  />
                </li>
              ))}
            </ul>
          ))}
        </div>
      </div>
    </section>
  );
}

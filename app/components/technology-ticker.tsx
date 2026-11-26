const technologies = ["Next.js", "React", "TypeScript", "Flask", "MySQL", "Redis", "MapLibre"];

export function TechnologyTicker() {
  return (
    <section className="home-technology" aria-label="Technology behind handEwork">
      <div className="shell home-technology-heading">
        <div>
          <p className="home-technology-kicker">BEHIND THE PLATFORM</p>
          <h2>Built with tools for real-world work.</h2>
        </div>
        <p>Technology in our application stack. Names shown identify tools used, not endorsements or certifications.</p>
      </div>
      <div className="home-technology-window">
        <div className="home-technology-track">
          <ul className="home-technology-list">
            {technologies.map(name => <li key={name}><span className="home-technology-glyph" aria-hidden="true" />{name}</li>)}
          </ul>
          <ul className="home-technology-list" aria-hidden="true">
            {technologies.map(name => <li key={name}><span className="home-technology-glyph" aria-hidden="true" />{name}</li>)}
          </ul>
        </div>
      </div>
    </section>
  );
}
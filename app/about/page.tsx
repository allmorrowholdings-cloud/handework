import { MarketingPage } from "../components/marketing-page";
export default function About() {
  return <MarketingPage
    eyebrow="About handEwork"
    title="Skill deserves the same respect as any other profession."
    intro="A welder is a professional. So is a tailor, plumber, cleaner, hairdresser, carpenter or painter. What they build, repair and create matters. handEwork exists to make their skills, livelihoods and careers more visible."
    cta={{ label: "Build your professional profile", href: "/join/artisan" }}
    sections={[
      { title: "A profession, not a lesser option", text: "Practical work is often judged by whether someone has a white-collar job, not by the quality of what they do. Professional identity should follow demonstrated skill, reliability and completed work." },
      { title: "Your work becomes your reputation", text: "With a portfolio, verified job records and WorkProof, professionals can show evidence of what they have done and build a history customers can review." },
      { title: "The difficult first step after vocational school", text: "Graduating is a milestone. Finding your first paying customers can be harder. handEwork helps new professionals present themselves, establish credibility and connect with opportunities without promising instant jobs." },
      { title: "Keep learning without unnecessary barriers", text: "Explore short, practical training opportunities as your career grows. Availability, delivery format, location and cost depend on the training provider; useful options should be easier to discover." },
      { title: "Customers deserve clarity too", text: "Find professionals by their skills, review the work, discuss the scope, see the quote and keep messages, changes and approvals connected to the booking." },
      { title: "Built in Ghana, designed to grow", text: "We begin with the everyday realities of vocational work and household services in Ghana, while designing for skills and customers beyond borders." },
      { title: "Part of ALLMORROW Holdings Ltd.", text: "handEwork is an ALLMORROW product. Building everything you need next." }
    ]}
  />;
}

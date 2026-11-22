import { Header } from "../../components/header";
import { Footer } from "../../components/footer";
import { PublicArtisanProfile } from "./profile";

export default async function ArtisanPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <main className="paper-page"><Header /><PublicArtisanProfile id={id} /><Footer /></main>;
}

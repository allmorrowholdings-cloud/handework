import Link from "next/link";
import { AppShell } from "../../../components/app-shell";
import { ChatRoom } from "../../../messages/[id]/chat-room";

export default async function ArtisanConversation({params}:{params:Promise<{id:string}>}) {
  const {id}=await params;
  return <AppShell role="artisan" title="Job conversation" note="Authenticated messages and attachments remain attached to this job." action={<Link className="button button-dark" href="/artisan/messages">All conversations</Link>}><section className="app-content"><div className="app-card"><ChatRoom id={id}/></div></section></AppShell>;
}

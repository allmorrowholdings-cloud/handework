import React, { useEffect, useRef, useState } from "react";
import { Image, Linking, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { useLocalSearchParams } from "expo-router";
import * as ImagePicker from "expo-image-picker";
import { io, Socket } from "socket.io-client";
import { api, API_URL, getAccessToken, upload } from "../../src/api/client";
import { colors, space } from "../../src/theme";

type Thread = { id: string; booking_id: string };
type Message = { id: string; sender_id: string; body?: string; media_url?: string; media_type?: string; created_at: string };

export default function Chat() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [conversation, setConversation] = useState<Thread | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [messageText, setMessageText] = useState("");
  const [notice, setNotice] = useState("");
  const socket = useRef<Socket | null>(null);
  const busyRef = useRef(false);
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      setLoading(true);
      setNotice("");
      setConversation(null);
      setMessages([]);
    });
    api<{ items: Thread[] }>("/v1/conversations").then(async (data) => {
      if (!active) return;
      const thread = data.items.find((item) => item.booking_id === id);
      if (!thread) {
        setNotice("Chat opens after an artisan accepts the booking.");
        return;
      }
      setConversation(thread);
      const result = await api<{ items: Message[] }>(`/v1/conversations/${thread.id}/messages`);
      if (!active) return;
      setMessages(result.items);
      const token = await getAccessToken();
      if (!active) return;
      socket.current = io(API_URL, { transports: ["websocket"] });
      socket.current.on("connect", () => socket.current?.emit(
        "join.conversation",
        { conversation_id: thread.id, token },
        (reply: { ok?: boolean; message?: string }) => {
          if (!reply?.ok) setNotice(reply?.message ?? "Live chat could not connect.");
        },
      ));
      socket.current.on("message.created", (row: Message) => setMessages((previous) => (
        previous.some((item) => item.id === row.id) ? previous : [...previous, row]
      )));
    }).catch((error) => { if (active) setNotice(error.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; socket.current?.disconnect(); socket.current = null; };
  }, [id, revision]);

  async function sendMessage(media?: { url: string; type: string }) {
    if (!conversation || (!messageText.trim() && !media)) return;
    const row = await api<Message>(`/v1/conversations/${conversation.id}/messages`, {
      method: "POST",
      body: JSON.stringify({ body: messageText.trim(), media_url: media?.url, media_type: media?.type }),
    });
    setMessages((previous) => previous.some((item) => item.id === row.id) ? previous : [...previous, row]);
    setMessageText("");
  }

  async function runAction(action: () => Promise<void>) {
    if (busyRef.current || !conversation) return;
    busyRef.current = true; setBusy(true); setNotice("");
    try { await action(); } catch (error) { setNotice(error instanceof Error ? error.message : "Message could not be sent."); }
    finally { busyRef.current = false; setBusy(false); }
  }

  async function attach() {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: .75 });
    if (result.canceled) return;
    const asset = result.assets[0];
    const uploaded = await upload("/v1/uploads", {
      uri: asset.uri,
      name: asset.fileName ?? "job-photo.jpg",
      type: asset.mimeType ?? "image/jpeg",
    }, { purpose: "chat_media", booking_id: id });
    await sendMessage({ url: uploaded.url, type: "image" });
  }

  return <KeyboardAvoidingView style={s.page} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={90}>
    <ScrollView contentContainerStyle={s.messages}>
      {messages.map((row) => <View style={s.bubble} key={row.id}>
        {row.media_url && (row.media_type === "image" || row.media_type?.startsWith("image/") ? <Image source={{uri:row.media_url}} style={s.image} resizeMode="contain" accessibilityLabel="Job photo" onError={()=>setNotice("Photo unavailable. Refresh the conversation to try again.")}/> : <Pressable accessibilityRole="link" onPress={()=>{if(row.media_url?.startsWith("https://"))Linking.openURL(row.media_url).catch(()=>setNotice("Attachment could not be opened."));}}><Text style={s.attachment}>Open attachment</Text></Pressable>)}
        {!!row.body && <Text style={s.body}>{row.body}</Text>}
        <Text style={s.time}>{new Date(row.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</Text>
      </View>)}
      {loading && <Text style={s.notice}>Loading conversation…</Text>}
      {!!notice && <Text accessibilityLiveRegion="polite" style={s.notice}>{notice}</Text>}
      <Pressable accessibilityRole="button" disabled={loading||busy} onPress={()=>setRevision(v=>v+1)}><Text style={s.notice}>Refresh conversation</Text></Pressable>
    </ScrollView>
    <View style={s.composer}>
      <Pressable accessibilityLabel="Attach photo" disabled={busy||loading||!conversation} onPress={()=>void runAction(attach)}><Text style={s.plus}>+</Text></Pressable>
      <TextInput style={s.input} value={messageText} onChangeText={setMessageText} placeholder="Message about this job" placeholderTextColor="#A49B8F" multiline maxLength={4000} editable={!busy && !!conversation} />
      <Pressable accessibilityRole="button" disabled={busy||loading||!conversation||!messageText.trim()} onPress={()=>void runAction(()=>sendMessage())}><Text style={s.send}>{busy?"WAIT…":"SEND"}</Text></Pressable>
    </View>
  </KeyboardAvoidingView>;
}

const s = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.paper },
  messages: { padding: space.md, gap: 10, flexGrow: 1, justifyContent: "flex-end" },
  bubble: { maxWidth: "85%", alignSelf: "flex-end", padding: 12, backgroundColor: colors.cream, borderLeftWidth: 3, borderColor: colors.orange },
  body: { fontSize: 12, lineHeight: 18, color: colors.ink },
  time: { fontSize: 7, color: colors.muted, marginTop: 5 },
  image: {width: 220, maxWidth:"100%", height: 180, borderRadius: 8, marginBottom: 6},
  attachment: { fontSize: 8, fontWeight: "900", color: colors.orange, marginBottom: 5 },
  notice: { textAlign: "center", color: colors.muted, fontSize: 11 },
  composer: { minHeight: 66, flexDirection: "row", alignItems: "center", gap: 10, padding: 10, borderTopWidth: 1, borderColor: colors.line, backgroundColor: colors.white },
  plus: { width: 38, height: 38, textAlign: "center", textAlignVertical: "center", fontSize: 23, color: colors.white, backgroundColor: colors.ink },
  input: { flex: 1, maxHeight: 90, fontSize: 12, color: colors.ink },
  send: { fontSize: 9, fontWeight: "900", color: colors.orange },
});

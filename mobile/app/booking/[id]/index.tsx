import React, { useCallback, useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { api } from "../../../src/api/client";
import { useAuth } from "../../../src/auth/context";
import { Button, Empty, Field, Loading } from "../../../src/components/ui";
import { colors, space } from "../../../src/theme";

type Booking={id:string;reference:string;service:string;description:string;area:string;city:string;status:string;agreed_amount?:number;currency:string};
type Quote={id:string;artisan_name:string;amount:number;currency:string;note?:string;status:string};
type JobChange={id:string;description:string;extra_amount:string;current_total:string;new_total:string;status:string};
type Detail={booking:Booking;quotes:Quote[];changes?:JobChange[];conversation_id?:string};

export default function BookingDetail(){
  const{id}=useLocalSearchParams<{id:string}>();const{user}=useAuth();const[detail,setDetail]=useState<Detail|null>(null);const[loading,setLoading]=useState(true);const[network,setNetwork]=useState("mtn");const[phone,setPhone]=useState(user?.phone??"");const[amount,setAmount]=useState("");const[quoteNote,setQuoteNote]=useState("");const[notice,setNotice]=useState("");
  const [busy,setBusy]=useState(false);const [extra,setExtra]=useState("");const [changeNote,setChangeNote]=useState("");
  const load=useCallback(()=>api<Detail>(`/v1/bookings/${id}`).then(setDetail).catch((error)=>setNotice(error.message)).finally(()=>setLoading(false)),[id]);useEffect(()=>{load()},[load]);
  async function action(path:string,body:object={}){setBusy(true);setNotice("");try{await api(path,{method:"POST",body:JSON.stringify(body)});await load()}catch(caught){setNotice(caught instanceof Error?caught.message:"Action failed")}finally{setBusy(false)}}
  async function pay(){setNotice("");try{const result=await api<{reference:string}>("/v1/payments/mobile-money",{method:"POST",headers:{"Idempotency-Key":`${id}-${Date.now()}`},body:JSON.stringify({booking_id:id,phone,network})});setNotice(`Payment request ${result.reference} sent. Approve it on your phone.`)}catch(caught){setNotice(caught instanceof Error?caught.message:"Could not start payment")}}
  if(loading)return <Loading/>;if(!detail)return <Empty title="Booking not available" text={notice||"Check your connection and account access."}/>;const{booking,quotes,changes=[],conversation_id}=detail;
  const money=(amount:string|number)=>`${booking.currency} ${Number(amount).toFixed(2)}`;
  return <ScrollView style={s.page} contentContainerStyle={s.content} keyboardShouldPersistTaps="handled"><Text style={s.ref}>{booking.reference}</Text><Text style={s.title}>{booking.service.toUpperCase()}</Text><Text style={s.status}>{booking.status.replaceAll("_"," ").toUpperCase()}</Text><View style={s.card}><Text style={s.cardTitle}>JOB SCOPE</Text><Text style={s.body}>{booking.description}</Text><Text style={s.meta}>{booking.area}, {booking.city}</Text></View><View style={s.timeline}>{["REQUESTED","QUOTE ACCEPTED","PAYMENT SECURED","WORK STARTED","APPROVED"].map((item,index)=><View style={s.step} key={item}><View style={[s.dot,index===0&&s.dotOn]}/><Text style={s.stepText}>{item}</Text></View>)}</View>
    {booking.agreed_amount!=null&&<View style={s.card}>
      <Text accessibilityRole="header" style={s.quoteAmount}>Job price changes</Text>
      <Text style={s.body}>Original quote: {money(booking.agreed_amount)}</Text>
      <Text style={s.body}>Approval records your agreement. It does not charge you or change the amount already held.</Text>
      {changes.map((change)=><View key={change.id} style={s.quote}>
        <Text style={s.quoteAmount}>{change.description}</Text>
        <Text style={s.body}>{change.status==="pending"?(booking.status==="in_progress"?"Awaiting approval":"Not approved — job no longer in progress"):change.status==="approved"?"Approved":"Declined"}</Text>
        <Text style={s.body}>Previously agreed: {money(change.current_total)}</Text>
        <Text style={s.body}>Extra cost: +{money(change.extra_amount)}</Text>
        <Text style={s.quoteAmount}>{change.status==="approved"?"Approved total":"Proposed total"}: {money(change.new_total)}</Text>
        {user?.role==="customer"&&booking.status==="in_progress"&&change.status==="pending"&&<>
          <Button label="Approve change" disabled={busy} onPress={()=>action(`/v1/bookings/${id}/changes/${change.id}/decision`,{decision:"approved"})}/>
          <Button dark label="Decline change" disabled={busy} onPress={()=>action(`/v1/bookings/${id}/changes/${change.id}/decision`,{decision:"declined"})}/>
          {conversation_id&&<Button dark label="Ask a question in chat" onPress={()=>router.push(`/chat/${id}`)}/>}
        </>}
      </View>)}
      {user?.role==="artisan"&&booking.status==="in_progress"&&!changes.some((change)=>change.status==="pending")&&<>
        <Field label="What changed?" value={changeNote} onChangeText={setChangeNote} multiline maxLength={500}/>
        <Field label={`Extra cost (${booking.currency})`} value={extra} onChangeText={setExtra} keyboardType="decimal-pad"/>
        <Button label="Send for approval" disabled={busy||!changeNote.trim()||!extra.trim()} onPress={()=>action(`/v1/bookings/${id}/changes`,{description:changeNote,extra_amount:extra})}/>
      </>}
    </View>}
    {user?.role==="artisan"&&["requested","quoted"].includes(booking.status)&&<View style={s.card}><Text style={s.cardTitle}>SUBMIT QUOTE</Text><Field label="Amount in GHS" value={amount} onChangeText={setAmount} keyboardType="decimal-pad"/><Field label="Scope note" value={quoteNote} onChangeText={setQuoteNote} multiline/><Button label="SEND QUOTE →" onPress={()=>action(`/v1/bookings/${id}/quotes`,{amount,note:quoteNote})}/></View>}
    {user?.role==="customer"&&quotes.map((quote)=><View style={s.quote} key={quote.id}><View><Text style={s.quoteName}>{quote.artisan_name}</Text><Text style={s.meta}>{quote.note||"No additional note"}</Text></View><Text style={s.quoteAmount}>{quote.currency} {quote.amount.toFixed(2)}</Text>{quote.status==="submitted"&&booking.status==="quoted"&&<Pressable onPress={()=>action(`/v1/bookings/${id}/quotes/${quote.id}/accept`)}><Text style={s.accept}>ACCEPT</Text></Pressable>}</View>)}
    {user?.role==="customer"&&booking.status==="accepted"&&<View style={s.card}><Text style={s.cardTitle}>SECURE PAYMENT</Text><Text style={s.amount}>{booking.currency} {booking.agreed_amount?.toFixed(2)}</Text><Field label="Mobile money phone" value={phone} onChangeText={setPhone} keyboardType="phone-pad"/><Field label="Network: mtn, telecel or atmoney" value={network} onChangeText={setNetwork}/><Button label="SEND PAYMENT PROMPT →" onPress={pay}/></View>}
    {user?.role==="artisan"&&booking.status==="funded"&&<Button label="MARK EN ROUTE →" onPress={()=>action(`/v1/bookings/${id}/status`,{status:"en_route"})}/>} {user?.role==="artisan"&&booking.status==="en_route"&&<Button label="START WORK →" onPress={()=>action(`/v1/bookings/${id}/status`,{status:"in_progress"})}/>} {user?.role==="artisan"&&booking.status==="in_progress"&&<Button label="SUBMIT COMPLETION →" onPress={()=>action(`/v1/bookings/${id}/status`,{status:"completion_submitted"})}/>} {user?.role==="customer"&&booking.status==="completion_submitted"&&<Button label="APPROVE AND RELEASE →" onPress={()=>action(`/v1/bookings/${id}/release`)}/>} {!!notice&&<Text accessibilityLiveRegion="polite" style={s.notice}>{notice}</Text>}<Button dark label="OPEN JOB Chat →" onPress={()=>router.push(`/chat/${id}`)}/></ScrollView>;
}
const s=StyleSheet.create({page:{flex:1,backgroundColor:colors.paper},content:{width:"100%",maxWidth:720,alignSelf:"center",padding:space.lg,paddingBottom:70,gap:16},ref:{fontSize:9,fontWeight:"600",color:colors.orange,letterSpacing:1},title:{fontSize:37,fontWeight:"600",letterSpacing:-2,color:colors.ink},status:{alignSelf:"flex-start",paddingHorizontal:10,paddingVertical:5,backgroundColor:colors.lime,fontSize:8,fontWeight:"600"},card:{padding:18,borderWidth:1,borderColor:colors.line,backgroundColor:colors.white,gap:13},cardTitle:{fontSize:9,fontWeight:"600",letterSpacing:1,color:colors.orange},body:{fontSize:13,lineHeight:20,color:colors.ink},meta:{fontSize:10,color:colors.muted},amount:{fontSize:28,fontWeight:"600",color:colors.ink},timeline:{marginVertical:4},step:{height:43,flexDirection:"row",alignItems:"center",gap:12,borderLeftWidth:1,borderColor:colors.line,paddingLeft:17},dot:{position:"absolute",left:-5,width:9,height:9,backgroundColor:colors.line},dotOn:{backgroundColor:colors.orange},stepText:{fontSize:9,fontWeight:"600",color:colors.muted},notice:{padding:11,backgroundColor:colors.cream,color:colors.ink,fontSize:10,lineHeight:16},quote:{padding:15,borderWidth:1,borderColor:colors.line,backgroundColor:colors.white,gap:9},quoteName:{fontSize:12,fontWeight:"600",color:colors.ink},quoteAmount:{fontSize:18,fontWeight:"600",color:colors.ink},accept:{alignSelf:"flex-start",padding:9,color:colors.white,backgroundColor:colors.orange,fontSize:8,fontWeight:"600"}});

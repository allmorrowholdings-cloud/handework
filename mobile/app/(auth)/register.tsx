import React,{useState}from"react";
import{KeyboardAvoidingView,Platform,Pressable,SafeAreaView,ScrollView,StyleSheet,Text,View}from"react-native";
import{router,useLocalSearchParams}from"expo-router";
import{AllmorrowMark,Button,Field,Logo}from"../../src/components/ui";
import{useAuth}from"../../src/auth/context";
import{api,saveSession}from"../../src/api/client";
import{colors,space}from"../../src/theme";

export default function Register(){
 const params=useLocalSearchParams<{role?:string}>();const artisan=params.role==="artisan";
 const{register,refresh}=useAuth();const[step,setStep]=useState(0);
 const[data,setData]=useState({first_name:"",last_name:"",email:"",phone:"",password:"",trade:"",years_experience:"0",city:"Accra",area:"",radius_km:"10"});
 const[busy,setBusy]=useState(false),[error,setError]=useState("");
 const set=(key:keyof typeof data,value:string)=>setData(prev=>({...prev,[key]:value}));
 function check(){if(step===0&&(!data.first_name.trim()||!data.last_name.trim()||!data.email.trim()||!data.phone.trim()||data.password.length<12)){setError("Add your name, email, phone and a password of at least 12 characters.");return false}
 if(step===1&&!data.trade.trim()){setError("Tell us your main trade.");return false}if(step===2&&(!data.city.trim()||!data.area.trim())){setError("Enter your city and home area.");return false}return true}
 async function continueWithAccount(){setError("");if(!check())return;if(artisan&&step<2){setStep(v=>v+1);return}
 setBusy(true);try{if(artisan){const response=await api<{access_token:string;refresh_token?:string}>("/v1/auth/register-artisan",{method:"POST",body:JSON.stringify({...data,years_experience:Number(data.years_experience)||0,radius_km:Number(data.radius_km)||10})});await saveSession(response.access_token,response.refresh_token);await refresh();router.replace("/artisan/dashboard")}
 else await register(data)}catch(e){setError(e instanceof Error?e.message:"Could not create your account")}finally{setBusy(false)}}
 return <SafeAreaView style={s.safe}><KeyboardAvoidingView behavior={Platform.OS==="ios"?"padding":undefined} style={{flex:1}}><ScrollView contentContainerStyle={s.page} keyboardShouldPersistTaps="handled"><Logo/>
 <View style={s.header}><Text style={s.kicker}>{artisan?`FOR PROFESSIONALS · ${step+1} OF 3`:"NEW CUSTOMER"}</Text><Text style={s.title}>{!artisan?"Create your account.":step===0?"Let's get to know you.":step===1?"What do you do?":"Where do you work?"}</Text><Text style={s.subtitle}>{artisan?"Build your work profile in a few steps.":"Book trusted skilled work."}</Text></View>
 {(!artisan||step===0)&&<><Field label="First name" value={data.first_name} onChangeText={v=>set("first_name",v)}/><Field label="Last name" value={data.last_name} onChangeText={v=>set("last_name",v)}/><Field label="Email address" keyboardType="email-address" autoCapitalize="none" value={data.email} onChangeText={v=>set("email",v)}/><Field label="Mobile number" keyboardType="phone-pad" value={data.phone} onChangeText={v=>set("phone",v)} placeholder="+233"/><Field label="Create password (12+ characters)" secureTextEntry value={data.password} onChangeText={v=>set("password",v)}/></>}
 {artisan&&step===1&&<><Field label="Main trade" value={data.trade} onChangeText={v=>set("trade",v)} placeholder="Plumbing, tailoring, painting…"/><Field label="Years of experience" keyboardType="number-pad" value={data.years_experience} onChangeText={v=>set("years_experience",v)}/></>}
 {artisan&&step===2&&<><Field label="City" value={data.city} onChangeText={v=>set("city",v)}/><Field label="Home area" value={data.area} onChangeText={v=>set("area",v)}/><Field label="Travel radius in kilometres" keyboardType="number-pad" value={data.radius_km} onChangeText={v=>set("radius_km",v)}/><Text style={s.subtitle}>Your public profile requires identity and trade verification before it can receive work.</Text></>}
 {!!error&&<Text accessibilityRole="alert" style={s.error}>{error}</Text>}
 <Button label={busy?"Please wait…":artisan&&step<2?"Continue →":artisan?"Create professional profile →":"Create account"} onPress={()=>void continueWithAccount()} disabled={busy}/>
 {artisan&&step>0&&<Pressable accessibilityRole="button" style={s.back} onPress={()=>setStep(x=>x-1)}><Text style={s.backText}>← Back</Text></Pressable>}
 <Pressable accessibilityRole="button" style={s.back} onPress={()=>router.replace("/(auth)/sign-in")}><Text style={s.backText}>Already registered? Sign in</Text></Pressable><AllmorrowMark/></ScrollView></KeyboardAvoidingView></SafeAreaView>
}
const s=StyleSheet.create({safe:{flex:1,backgroundColor:colors.paper},page:{padding:space.lg,paddingTop:space.xl,paddingBottom:60,gap:17},header:{gap:11,marginVertical:24},kicker:{fontSize:11,fontWeight:"700",letterSpacing:1.3,color:colors.orange},title:{fontSize:39,lineHeight:44,fontWeight:"700",letterSpacing:-1.8,color:colors.ink},subtitle:{color:colors.muted,fontSize:14,lineHeight:22},error:{color:colors.danger,backgroundColor:"#F7DDD8",padding:13,borderRadius:10},back:{minHeight:46,justifyContent:"center",alignItems:"center"},backText:{color:colors.orange,fontSize:14,fontWeight:"700"}});

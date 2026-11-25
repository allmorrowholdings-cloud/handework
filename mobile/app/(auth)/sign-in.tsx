import React,{useState}from"react";import{KeyboardAvoidingView,Platform,SafeAreaView,StyleSheet,Text,View}from"react-native";import{router}from"expo-router";import{AllmorrowMark,Button,Field,Logo}from"../../src/components/ui";import{useAuth}from"../../src/auth/context";import{colors,space}from"../../src/theme";
export default function SignIn(){const{signIn}=useAuth();const[email,setEmail]=useState("");const[password,setPassword]=useState("");const[secondFactor,setSecondFactor]=useState(false);const[totpCode,setTotpCode]=useState("");const[busy,setBusy]=useState(false);const[error,setError]=useState("");async function submit(){setBusy(true);setError("");try{await signIn(email,password,secondFactor?totpCode:undefined)}catch(e){
      const details=(e as {details?:{code?:string}})?.details;
      if(["totp_required","totp_invalid","totp_locked"].includes(details?.code??"")){
        setSecondFactor(true);
      }
      setError(e instanceof Error?e.message:"Could not sign in")
    }finally{setBusy(false)}}return <SafeAreaView style={s.safe}><KeyboardAvoidingView behavior={Platform.OS==="ios"?"padding":undefined} style={s.page}><Logo/><View style={s.box}><Text style={s.kicker}>Welcome back</Text><Text style={s.title}>Continue your work.</Text><Text style={s.lede}>Bookings, messages and protected payments stay with your account.</Text><Field label="Email address" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address"/><Field label="Password" value={password} onChangeText={setPassword} secureTextEntry/>{secondFactor&&<View style={{gap:10}}>
      <Text style={s.lede}>Two-step verification</Text>
      <Field
        label="Authenticator or recovery code"
        value={totpCode}
        onChangeText={setTotpCode}
        autoCapitalize="none"
        autoCorrect={false}
        maxLength={24}
        editable={!busy}
      />
      <Text style={s.lede}>
        Enter your current authenticator code or an emergency recovery code.
      </Text>
    </View>}
    {!!error&&<Text style={s.error}>{error}</Text>}<Button label={busy?"Please wait…":"Sign in securely →"} disabled={busy||!email||!password||(secondFactor&&!totpCode.trim())} onPress={submit}/><Text style={s.link} onPress={()=>router.push("/(auth)/register")}>New to handEwork? Create an account</Text></View><Text style={s.back} onPress={()=>router.back()}>← Back</Text><AllmorrowMark/></KeyboardAvoidingView></SafeAreaView>}
const s=StyleSheet.create({safe:{flex:1,backgroundColor:colors.paper},page:{flex:1,padding:space.lg,paddingTop:space.xl},box:{marginTop:"auto",marginBottom:"auto",gap:17},kicker:{fontSize:9,fontWeight:"600",letterSpacing:1.4,color:colors.orange},title:{fontSize:43,lineHeight:42,fontWeight:"600",letterSpacing:-2.5,color:colors.ink},lede:{fontSize:13,lineHeight:20,color:colors.muted,marginBottom:10},error:{padding:10,backgroundColor:"#F7DDD8",color:colors.danger,fontSize:11},link:{textAlign:"center",color:colors.orange,fontSize:11,fontWeight:"600"},back:{fontSize:10,color:colors.muted,fontWeight:"600"}})

import React,{useEffect}from"react";
import{Pressable,SafeAreaView,StyleSheet,Text,View}from"react-native";
import{router}from"expo-router";
import{useAuth}from"../src/auth/context";
import{AllmorrowMark,Button,Logo}from"../src/components/ui";
import{colors,space}from"../src/theme";
export default function Welcome(){
 const {user,loading}=useAuth();
 useEffect(()=>{if(!loading&&user)router.replace("/(tabs)")},[loading,user]);
 if(loading||user)return <SafeAreaView style={s.safe}><View style={s.loading}><Logo light/><Text style={s.sub}>from ALLMORROW</Text></View></SafeAreaView>;
 return <SafeAreaView style={s.safe}><View style={s.page}><View style={s.brand}><Logo light/><View style={s.bar}/><Text style={s.sub}>from ALLMORROW</Text></View><View style={s.actions}><Text style={s.title}>Ready when you are.</Text><Text style={s.body}>Skilled work deserves a place to grow.</Text><Button label="Sign in" onPress={()=>router.push("/(auth)/sign-in")}/><Pressable accessibilityRole="button" style={s.secondary} onPress={()=>router.push("/(auth)/register")}><Text style={s.secondaryText}>Create customer account</Text></Pressable><Pressable accessibilityRole="button" style={s.professional} onPress={()=>router.push("/(auth)/register?role=artisan")}><Text style={s.professionalText}>Work with handEwork</Text></Pressable></View><AllmorrowMark/></View></SafeAreaView>
}
const s=StyleSheet.create({safe:{flex:1,backgroundColor:colors.ink},page:{flex:1,padding:space.lg,justifyContent:"space-between"},loading:{flex:1,alignItems:"center",justifyContent:"center",gap:20},brand:{marginTop:85,alignItems:"center",gap:18},bar:{height:3,width:70,backgroundColor:colors.orange},sub:{fontSize:10,color:"#FFFFFF99",letterSpacing:2},actions:{gap:13},title:{fontSize:39,lineHeight:43,fontWeight:"700",color:colors.white,letterSpacing:-1.8},body:{fontSize:15,color:"#FFFFFFBB",marginBottom:8},secondary:{minHeight:52,borderRadius:10,borderWidth:1,borderColor:"#FFFFFF77",alignItems:"center",justifyContent:"center"},secondaryText:{fontSize:14,fontWeight:"700",color:colors.white},professional:{minHeight:52,alignItems:"center",justifyContent:"center"},professionalText:{fontSize:14,fontWeight:"700",color:colors.orange}})

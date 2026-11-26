import React from "react";
import {Pressable,ScrollView,StyleSheet,Text,View} from "react-native";
import {router} from "expo-router";
import {useAuth} from "../../src/auth/context";
import {Button} from "../../src/components/ui";
import {colors,space} from "../../src/theme";
export default function AppHome(){const {user}=useAuth();return <ScrollView style={s.page} contentContainerStyle={s.content}>
  <View style={s.top}><Text style={s.greeting}>{user?.first_name?`Hello, ${user.first_name}`:"Welcome"}</Text><Pressable accessibilityRole="button" accessibilityLabel="Account settings" style={s.avatar} onPress={()=>router.push("/(tabs)/account")}><Text style={s.initial}>{user?.first_name?.[0]?.toUpperCase()??"A"}</Text></Pressable></View>
  <View style={s.hero}><Text accessibilityRole="header" style={s.title}>What do you need done?</Text><Button label="Choose a service" onPress={()=>router.push("/booking/new")}/></View>
</ScrollView>}
const s=StyleSheet.create({page:{flex:1,backgroundColor:colors.paper},content:{padding:space.lg,paddingBottom:100,flexGrow:1},top:{flexDirection:"row",alignItems:"center",justifyContent:"space-between"},greeting:{fontSize:14,color:colors.muted},avatar:{height:44,width:44,borderRadius:22,backgroundColor:colors.orange,alignItems:"center",justifyContent:"center"},initial:{color:colors.white,fontSize:20,fontWeight:"700"},hero:{flex:1,justifyContent:"center",gap:32,paddingVertical:70},title:{fontSize:Math.min(48,42),fontWeight:"700",letterSpacing:-2,lineHeight:48,color:colors.ink}})

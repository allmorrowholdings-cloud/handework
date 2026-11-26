import React from "react";
import {Pressable,ScrollView,StyleSheet,Text,View} from "react-native";
import {router} from "expo-router";
import {colors,space} from "../../src/theme";
const entries=[{label:"Overview",path:"/(tabs)/overview"},{label:"Bookings",path:"/(tabs)/bookings"},{label:"Messages",path:"/(tabs)/messages"},{label:"Notifications",path:"/notifications"},{label:"Referrals",path:"/referrals"},{label:"Support & disputes",path:"/disputes"}];
export default function Activities(){return <ScrollView style={s.root} contentContainerStyle={s.content}><Text style={s.eyebrow}>YOUR WORK</Text><Text style={s.title}>Activities</Text>{entries.map(item=><Pressable key={item.label} accessibilityRole="button" style={s.item} onPress={()=>router.push(item.path as never)}><Text style={s.label}>{item.label}</Text><Text style={s.arrow}>›</Text></Pressable>)}</ScrollView>}
const s=StyleSheet.create({root:{flex:1,backgroundColor:colors.paper},content:{padding:space.lg,paddingBottom:90},eyebrow:{fontSize:11,fontWeight:"700",color:colors.orange},title:{fontSize:39,letterSpacing:-1.5,fontWeight:"700",color:colors.ink,marginBottom:22},item:{minHeight:64,borderBottomWidth:1,borderColor:colors.line,flexDirection:"row",alignItems:"center",justifyContent:"space-between"},label:{fontSize:17,fontWeight:"600",color:colors.ink},arrow:{fontSize:26,color:colors.orange}})

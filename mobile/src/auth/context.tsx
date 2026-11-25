import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { router } from "expo-router";
import { api, clearSession, saveSession } from "../api/client";

type User={id:string;first_name:string;last_name:string;email:string;phone:string;phone_verified?:boolean;email_verified?:boolean;role:"customer"|"artisan"|"admin"};
type Auth={user:User|null;loading:boolean;signIn:(email:string,password:string,totpCode?:string)=>Promise<void>;register:(data:Record<string,string>)=>Promise<void>;signOut:()=>Promise<void>;refresh:()=>Promise<void>};
const Context=createContext<Auth|null>(null);

export function AuthProvider({children}:{children:React.ReactNode}){
  const[user,setUser]=useState<User|null>(null);const[loading,setLoading]=useState(true);
  async function refresh(){try{const body=await api<{user:User}>("/v1/auth/me");setUser(body.user)}catch{setUser(null)}finally{setLoading(false)}}
  useEffect(()=>{const task=setTimeout(()=>{void refresh()},0);return()=>clearTimeout(task)},[]);
  async function signIn(email:string,password:string,totpCode?:string){const body=await api<{access_token:string;refresh_token:string;user:User}>("/v1/auth/login",{method:"POST",body:JSON.stringify({email,password,totp_code:totpCode})});await saveSession(body.access_token,body.refresh_token);setUser(body.user);router.replace(body.user.role==="artisan"?"/artisan/dashboard":"/(tabs)")}
  async function register(data:Record<string,string>){const body=await api<{access_token:string;refresh_token:string;user:User}>("/v1/auth/register",{method:"POST",body:JSON.stringify(data)});await saveSession(body.access_token,body.refresh_token);setUser(body.user);router.replace("/(tabs)")}
  async function signOut(){await clearSession();setUser(null);router.replace("/")}
  const value=useMemo(()=>({user,loading,signIn,register,signOut,refresh}),[user,loading]);return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useAuth(){const value=useContext(Context);if(!value)throw new Error("useAuth must be inside AuthProvider");return value}

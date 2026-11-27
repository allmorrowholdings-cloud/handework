"use client";
import { useEffect, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { SupportForm } from "../../support/support-form";
import { api } from "../../../lib/api";
type Role = "customer" | "artisan" | "admin";
export default function HelpPage() {
  const [role,setRole]=useState<Role | null>(null);
  useEffect(()=>{let live=true;api<{user:{role:string}}>("/v1/auth/me").then(x=>{if(live&&["customer","artisan","admin"].includes(x.user.role))setRole(x.user.role as Role)}).catch(()=>{});return()=>{live=false}},[]);
  if (!role) return null;
  return <AppShell role={role} title="Help & support" note="Keep questions and disputes connected to the right job record."><section className="app-content narrow-content"><SupportForm/></section></AppShell>;
}

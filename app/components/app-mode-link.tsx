"use client";
import Link from "next/link";
import {useEffect,useState} from "react";
export function AppProfessionalLink({children}:{children:React.ReactNode}){
  const [installed,setInstalled]=useState(false);
  useEffect(()=>{const frame=window.requestAnimationFrame(()=>setInstalled(window.matchMedia("(display-mode: standalone)").matches||((navigator as Navigator&{standalone?:boolean}).standalone===true)));return()=>window.cancelAnimationFrame(frame)},[]);
  return <Link href={installed?"/app/professional":"/join/artisan"}>{children}</Link>;
}

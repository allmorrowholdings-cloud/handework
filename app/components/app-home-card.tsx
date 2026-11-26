"use client";
import Link from "next/link";
import {useEffect,useState} from "react";
export function AppHomeCard(){const [standalone,setStandalone]=useState(false);useEffect(()=>{const frame=window.requestAnimationFrame(()=>setStandalone(window.matchMedia("(display-mode: standalone)").matches||((navigator as Navigator&{standalone?:boolean}).standalone===true)));return()=>window.cancelAnimationFrame(frame)},[]);if(!standalone)return null;return <section className="hw-app-home-book"><h2>What do you need done?</h2><Link href="/app/book">Choose a service <span aria-hidden="true">→</span></Link></section>}

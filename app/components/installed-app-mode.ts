"use client";
import {useSyncExternalStore} from "react";
const query="(display-mode: standalone)";
function snapshot(){return typeof window!=="undefined" &&
  (window.matchMedia(query).matches || ("standalone" in navigator &&
  (navigator as Navigator & {standalone?:boolean}).standalone===true));}
function subscribe(notify:()=>void){const m=window.matchMedia(query);m.addEventListener("change",notify);return()=>m.removeEventListener("change",notify)}
export function useInstalledApp(){return useSyncExternalStore(subscribe,snapshot,()=>false)}

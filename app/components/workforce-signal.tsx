"use client";
import { useEffect, useRef, useState } from "react";

export function WorkforceSignal() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [number, setNumber] = useState(1.6);
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    if (typeof IntersectionObserver === "undefined") { const frame = requestAnimationFrame(() => setVisible(true)); return () => cancelAnimationFrame(frame); }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setVisible(true); observer.disconnect(); }
    }, { threshold: 0.3 });
    observer.observe(root);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!visible || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let frame = 0;
    const started = performance.now();
    const animate = (now: number) => {
      const fraction = Math.min(1, (now - started) / 1150);
      const eased = 1 - Math.pow(1 - fraction, 3);
      setNumber(Math.round(eased * 16) / 10);
      if (fraction < 1) frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [visible]);
  return <div ref={ref} className={visible ? "signal-visible" : ""}>
    <strong className="workforce-figure" aria-label="1.6 million plus">{number.toFixed(1)}M+</strong>
    <span className="workforce-label">Craft and related trades workers in Ghana</span>
    <svg className="workforce-line" viewBox="0 0 600 70" role="img" aria-label="Line connecting three points">
      <path className="signal-path" d="M36 35 H564" fill="none" />
      <circle className="signal-dot" cx="36" cy="35" r="8" />
      <circle className="signal-dot" cx="300" cy="35" r="8" />
      <circle className="signal-dot" cx="564" cy="35" r="8" />
    </svg>
    <div className="signal-benefits" aria-label="Three ways handEwork helps">
      <div><h3>Discover skilled hands</h3><p>Find professionals for the work you need done.</p></div>
      <div><h3>Manage the job clearly</h3><p>Keep the quote, schedule and updates together.</p></div>
      <div><h3>Build work reputation</h3><p>Recognise verified skills and completed work through WorkProof.</p></div>
    </div>
  </div>;
}
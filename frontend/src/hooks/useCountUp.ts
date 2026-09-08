import { useEffect, useRef, useState } from "react";

/** Smoothly animates toward `value` on every change (exponential easing). */
export function useCountUp(value: number, duration = 900): number {
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const from = fromRef.current;
    const start = performance.now();
    const delta = value - from;

    const step = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(from + delta * eased);
      if (p < 1) rafRef.current = requestAnimationFrame(step);
      else fromRef.current = value;
    };

    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      fromRef.current = value;
    };
  }, [value, duration]);

  return display;
}

export function formatMetric(value: number, decimals = 0): string {
  if (Math.abs(value) >= 100000) return value.toExponential(1);
  return value.toLocaleString("en-IN", { maximumFractionDigits: decimals });
}
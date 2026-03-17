import { useState, useEffect, useRef } from "react";
import { getEngineUrl } from "./useWorldData";

export interface MarketSummary {
  [location: string]: {
    [skill: string]: number; // pressure
  };
}

export function useMarketData(pollInterval = 5000) {
  const [summary, setSummary] = useState<MarketSummary>({});
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const fetch_ = async () => {
    try {
      const res = await fetch(`${getEngineUrl()}/market`, {
        signal: AbortSignal.timeout(4000),
      });
      if (!res.ok) return;
      const data = await res.json();
      if (mountedRef.current) setSummary(data.summary || {});
    } catch {}
  };

  useEffect(() => {
    mountedRef.current = true;
    fetch_();
    const schedule = () => {
      timerRef.current = setTimeout(() => {
        fetch_().then(() => { if (mountedRef.current) schedule(); });
      }, pollInterval);
    };
    schedule();
    return () => {
      mountedRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [pollInterval]);

  return summary;
}

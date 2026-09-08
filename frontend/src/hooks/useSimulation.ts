import { useEffect } from "react";
import { useSimStore } from "../stores/sim";

const WS_URL = import.meta.env.VITE_WS_URL ?? (() => {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/ws/sim`;
})();

export function useSimulation() {
  const applyMessage = useSimStore((s) => s.applyMessage);
  const setConnected = useSimStore((s) => s.setConnected);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retry = 0;
    let closed = false;

    const connect = () => {
      if (closed) return;
      ws = new WebSocket(WS_URL);
      ws.onopen = () => {
        retry = 0;
        setConnected(true);
      };
      ws.onmessage = (ev) => {
        try {
          applyMessage(JSON.parse(ev.data));
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!closed) {
          retry = Math.min(retry + 1, 5);
          setTimeout(connect, 800 * retry);
        }
      };
      ws.onerror = () => ws?.close();
    };

    connect();
    return () => {
      closed = true;
      ws?.close();
    };
  }, [applyMessage, setConnected]);
}
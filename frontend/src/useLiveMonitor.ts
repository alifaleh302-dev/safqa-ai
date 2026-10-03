import { useEffect, useRef, useState } from "react";
import { getToken } from "./api";
import type { Decision, Event as AppEvent, Message } from "./types";

interface LiveState {
  messages: Message[];
  decisions: Decision[];
  events: AppEvent[];
  connected: boolean;
}

function wsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const token = getToken() ?? "";
  return `${proto}//${window.location.host}/api/ws?token=${encodeURIComponent(token)}`;
}

/**
 * Subscribes to the backend live feed. Reconnects automatically with backoff,
 * so a dropped socket (server restart, sleep) recovers without a page reload.
 */
export function useLiveMonitor(active: boolean): LiveState {
  const [messages, setMessages] = useState<Message[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [events, setEvents] = useState<AppEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const retryRef = useRef(0);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!active) return;
    let ws: WebSocket | null = null;
    let closed = false;

    const connect = () => {
      if (closed) return;
      ws = new WebSocket(wsUrl());

      ws.onopen = () => {
        retryRef.current = 0;
        setConnected(true);
      };

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data) as { type: string; data: unknown };
          if (msg.type === "snapshot") {
            const data = msg.data as { messages: Message[]; decisions: Decision[] };
            setMessages(data.messages ?? []);
            setDecisions(data.decisions ?? []);
          } else if (msg.type === "message") {
            const m = msg.data as Message;
            setMessages((prev) => [m, ...prev.filter((x) => x.id !== m.id)].slice(0, 200));
          } else if (msg.type === "decision") {
            const d = msg.data as Decision;
            setDecisions((prev) => [d, ...prev.filter((x) => x.id !== d.id)].slice(0, 200));
          } else if (msg.type === "event") {
            const e = msg.data as AppEvent;
            setEvents((prev) => [e, ...prev.filter((x) => x.id !== e.id)].slice(0, 200));
          }
        } catch {
          /* ignore malformed frames */
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (closed) return;
        // Exponential backoff capped at 10s.
        retryRef.current += 1;
        const delay = Math.min(10000, 500 * 2 ** retryRef.current);
        timerRef.current = window.setTimeout(connect, delay);
      };

      ws.onerror = () => ws?.close();
    };

    connect();

    return () => {
      closed = true;
      if (timerRef.current) window.clearTimeout(timerRef.current);
      ws?.close();
    };
  }, [active]);

  return { messages, decisions, events, connected };
}

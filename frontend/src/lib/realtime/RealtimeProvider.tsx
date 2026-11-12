"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { useSound } from "@/lib/sound/SoundProvider";

import {
  addNotice,
  socketUrl,
  soundFor,
  toNotice,
  type Notice,
  type RealtimeEvent,
} from "./events";

type Listener = (event: RealtimeEvent) => void;

interface RealtimeValue {
  connected: boolean;
  notices: Notice[];
  clearNotices: () => void;
  subscribe: (listener: Listener) => () => void;
}

const RealtimeContext = createContext<RealtimeValue | null>(null);

/**
 * One WebSocket per signed-in tab. Reconnects with back-off; if the socket
 * cannot connect, screens still work and refresh when opened.
 */
export function RealtimeProvider({ children }: { children: ReactNode }) {
  const { play } = useSound();
  const [connected, setConnected] = useState(false);
  const [notices, setNotices] = useState<Notice[]>([]);
  const listeners = useRef(new Set<Listener>());

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retry = 0;
    let timer: number | undefined;
    let stopped = false;

    const connect = () => {
      if (stopped || typeof WebSocket === "undefined") return;
      socket = new WebSocket(socketUrl(window.location));
      socket.onopen = () => {
        retry = 0;
      };
      socket.onmessage = (message) => {
        let event: RealtimeEvent;
        try {
          event = JSON.parse(String(message.data)) as RealtimeEvent;
        } catch {
          return;
        }
        if (event.type === "ready") {
          setConnected(true);
          return;
        }
        const notice = toNotice(event);
        if (notice) setNotices((list) => addNotice(list, notice));
        const sound = soundFor(event);
        if (sound) play(sound);
        listeners.current.forEach((l) => l(event));
      };
      socket.onclose = (close) => {
        setConnected(false);
        if (stopped || close.code === 4401 || close.code === 4403) return;
        retry = Math.min(retry + 1, 6);
        timer = window.setTimeout(connect, 1000 * 2 ** retry);
      };
    };
    connect();
    const keepAlive = window.setInterval(() => {
      if (socket?.readyState === WebSocket.OPEN) socket.send("ping");
    }, 25_000);
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      window.clearInterval(keepAlive);
      socket?.close();
    };
  }, [play]);

  const subscribe = useCallback((listener: Listener) => {
    listeners.current.add(listener);
    return () => {
      listeners.current.delete(listener);
    };
  }, []);
  const clearNotices = useCallback(() => setNotices([]), []);

  return (
    <RealtimeContext.Provider value={{ connected, notices, clearNotices, subscribe }}>
      {children}
    </RealtimeContext.Provider>
  );
}

const OFFLINE: RealtimeValue = {
  connected: false,
  notices: [],
  clearNotices: () => undefined,
  subscribe: () => () => undefined,
};

export function useRealtime(): RealtimeValue {
  return useContext(RealtimeContext) ?? OFFLINE;
}

/** Run ``handler`` for events whose type starts with ``prefix``. */
export function useRealtimeEvent(prefix: string, handler: Listener) {
  const { subscribe } = useRealtime();
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(
    () => subscribe((event) => event.type.startsWith(prefix) && ref.current(event)),
    [subscribe, prefix],
  );
}

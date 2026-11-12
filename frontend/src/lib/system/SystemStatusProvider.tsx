"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { ApiError } from "@/lib/api/client";
import {
  fetchReadiness,
  platformState,
  type PlatformState,
  type ReadinessReport,
} from "@/lib/api/health";

const POLL_INTERVAL_MS = 30_000;

interface SystemStatusValue {
  report: ReadinessReport | null;
  error: ApiError | null;
  state: PlatformState;
  loading: boolean;
  lastChecked: Date | null;
  requestId: string | null;
  refresh: () => void;
}

const SystemStatusContext = createContext<SystemStatusValue | null>(null);

/**
 * One shared readiness poller for the whole shell (header indicator, command
 * centre and system page read the same data). Polling pauses while the tab is
 * hidden.
 */
export function SystemStatusProvider({ children }: { children: ReactNode }) {
  const [report, setReport] = useState<ReadinessReport | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);
  const inflight = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    inflight.current?.abort();
    const controller = new AbortController();
    inflight.current = controller;
    setLoading(true);
    try {
      const response = await fetchReadiness({ signal: controller.signal, timeoutMs: 6000 });
      if (controller.signal.aborted) return;
      setReport(response.data);
      setRequestId(response.requestId);
      setError(null);
    } catch (cause) {
      if (controller.signal.aborted) return;
      setError(
        cause instanceof ApiError
          ? cause
          : new ApiError({ status: 0, code: "unknown", message: String(cause), requestId: null }),
      );
      setReport(null);
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
        setLastChecked(new Date());
      }
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, POLL_INTERVAL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
      inflight.current?.abort();
    };
  }, [refresh]);

  const value = useMemo<SystemStatusValue>(
    () => ({
      report,
      error,
      state: loading && !report && !error ? "checking" : platformState(report, error),
      loading,
      lastChecked,
      requestId,
      refresh: () => void refresh(),
    }),
    [report, error, loading, lastChecked, requestId, refresh],
  );

  return <SystemStatusContext.Provider value={value}>{children}</SystemStatusContext.Provider>;
}

export function useSystemStatus(): SystemStatusValue {
  const context = useContext(SystemStatusContext);
  if (!context) throw new Error("useSystemStatus must be used inside <SystemStatusProvider>");
  return context;
}

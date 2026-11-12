"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, send } from "./client";

export interface Resource<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => Promise<void>;
}

/** GET a resource and keep it in state. ``path === null`` skips the request. */
export function useResource<T>(path: string | null): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(path !== null);

  const reload = useCallback(async () => {
    if (path === null) return;
    setLoading(true);
    try {
      const response = await send<T>("GET", path);
      setData(response.data);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load data.");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { data, error, loading, reload };
}

/** Turn any thrown value into a message suitable for FormError. */
export function errorMessage(e: unknown, fallback = "The action failed."): string {
  return e instanceof ApiError ? e.message : fallback;
}

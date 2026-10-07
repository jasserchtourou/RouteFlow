"use client";

import { useCallback, useEffect, useState } from "react";

const PREFIX = "routeflow:";

/**
 * State remembered in localStorage (per browser). Renders `initial` first and applies the saved
 * value after mount, so server and client markup agree. Storage can be unavailable (private
 * windows, blocked site data): every access is guarded and the UI simply works without it.
 */
export function useStoredState<T>(key: string, initial: T): [T, (next: T) => void] {
  const [value, setValue] = useState<T>(initial);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(PREFIX + key);
      if (raw !== null) setValue(JSON.parse(raw) as T);
    } catch {
      // Unreadable or malformed: keep the default.
    }
  }, [key]);

  const update = useCallback(
    (next: T) => {
      setValue(next);
      try {
        window.localStorage.setItem(PREFIX + key, JSON.stringify(next));
      } catch {
        // Not persisted; still works for this visit.
      }
    },
    [key],
  );

  return [value, update];
}

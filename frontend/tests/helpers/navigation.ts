import { useSyncExternalStore } from "react";

/**
 * A tiny in-memory stand-in for next/navigation: the "URL" lives in a store, router.replace
 * changes it and re-renders subscribers, so filters stored in the query string really round-trip.
 */
let url = new URL("http://test/");
const listeners = new Set<() => void>();

export function setUrl(path: string): void {
  url = new URL(path, "http://test");
  listeners.forEach((listener) => listener());
}

export function currentUrl(): URL {
  return url;
}

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

const snapshot = () => url.pathname + url.search;

export const navigationMock = {
  useSearchParams: () =>
    new URLSearchParams(
      useSyncExternalStore(
        subscribe,
        () => url.search,
        () => url.search,
      ),
    ),
  usePathname: () => {
    useSyncExternalStore(subscribe, snapshot, snapshot);
    return url.pathname;
  },
  useRouter: () => ({
    replace: (to: string) => setUrl(to),
    push: (to: string) => setUrl(to),
  }),
};

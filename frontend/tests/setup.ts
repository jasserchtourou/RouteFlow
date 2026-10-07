import "@testing-library/jest-dom/vitest";
import { beforeEach, vi } from "vitest";

// Tests run as a user on a large desktop screen who prefers reduced motion, so that numbers and
// bars show their final values immediately and panels start open. Stored UI state (collapsed
// panels, theme) never leaks from one test into the next.
beforeEach(() => {
  window.localStorage.clear();
  const matchMedia = (query: string) => ({
    matches: query.includes("prefers-reduced-motion") || /min-(width|height)/.test(query),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
    onchange: null,
  });
  // `window` and the global object are separate in this environment: set both.
  vi.stubGlobal("matchMedia", matchMedia);
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: matchMedia,
  });
});

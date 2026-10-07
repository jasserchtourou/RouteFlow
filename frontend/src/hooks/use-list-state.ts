"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

type Change = string | readonly string[] | null | undefined;

/**
 * List filters, sorting and paging kept in the URL query string, so a filtered view can be
 * bookmarked, shared and survives a reload; the back button steps through filter changes.
 */
export function useListState() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const get = (key: string): string | null => params.get(key);
  const list = (key: string): string[] => params.get(key)?.split(",").filter(Boolean) ?? [];
  const page = Math.max(1, Number(params.get("page")) || 1);

  const update = useCallback(
    (changes: Record<string, Change>) => {
      const next = new URLSearchParams(params.toString());
      for (const [key, value] of Object.entries(changes)) {
        const text = Array.isArray(value) ? value.join(",") : (value as string | null | undefined);
        if (!text) next.delete(key);
        else next.set(key, text);
      }
      // Changing a filter starts again from the first page. Opening or closing a detail panel, or
      // changing the page itself, keeps the page.
      const keepsPage = Object.keys(changes).every((key) => key === "page" || key === "open");
      if (!keepsPage) next.delete("page");
      const query = next.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [params, pathname, router],
  );

  return { get, list, page, update };
}

export const PAGE_SIZE = 20;

"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { apiGet, type Query } from "@/lib/api";
import type { Page } from "./api-types";

/**
 * One page of a backend list. While the next page or a new filter loads, the previous rows stay
 * on screen (dimmed) instead of flashing an empty table.
 */
export function usePageQuery<T>(
  key: string,
  path: string,
  query: Query,
  options: { refetchMs?: number } = {},
) {
  return useQuery({
    queryKey: [key, path, query],
    queryFn: ({ signal }) => apiGet<Page<T>>(path, query, signal),
    placeholderData: keepPreviousData,
    refetchInterval: options.refetchMs,
  });
}

"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

export function Pagination({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number;
  pageSize: number;
  total: number | undefined;
  onPage: (page: number) => void;
}) {
  if (total === undefined) return null;
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

  return (
    <nav aria-label="Pagination" className="mt-3 flex items-center justify-between gap-3 text-sm">
      <p className="text-muted" aria-live="polite">
        {total === 0 ? "No results" : `${first}–${last} of ${total}`}
      </p>
      <div className="flex items-center gap-1">
        <button
          type="button"
          aria-label="Previous page"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
          className="grid size-9 place-items-center rounded-lg border border-border hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft aria-hidden className="size-4" />
        </button>
        <span className="px-2 tabular-nums text-muted">
          Page {Math.min(page, pages)} of {pages}
        </span>
        <button
          type="button"
          aria-label="Next page"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
          className="grid size-9 place-items-center rounded-lg border border-border hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronRight aria-hidden className="size-4" />
        </button>
      </div>
    </nav>
  );
}

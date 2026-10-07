"use client";

import { ArrowDown, ArrowUp, ChevronsUpDown, Inbox } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface Column<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  /** Backend sort key (ascending); makes the header a sort button. A leading "-" means descending. */
  sortKey?: string;
  align?: "left" | "right";
  className?: string;
}

interface DataTableProps<T> {
  caption: string;
  columns: readonly Column<T>[];
  rows: readonly T[] | undefined;
  rowKey: (row: T) => string;
  loading?: boolean;
  /** Current sort in backend form: "promised_delivery_at" or "-promised_delivery_at". */
  sort?: string;
  onSort?: (sort: string) => void;
  selectedKey?: string | null;
  onSelect?: (row: T) => void;
  emptyTitle: string;
  emptyHint?: string;
}

function SortIcon({ state }: { state: "asc" | "desc" | "none" }) {
  const Icon = state === "asc" ? ArrowUp : state === "desc" ? ArrowDown : ChevronsUpDown;
  return <Icon aria-hidden className={cn("size-3.5", state === "none" && "opacity-40")} />;
}

/** Accessible, sortable table: `aria-sort` on the active column, rows selectable by keyboard. */
export function DataTable<T>({
  caption,
  columns,
  rows,
  rowKey,
  loading,
  sort,
  onSort,
  selectedKey,
  onSelect,
  emptyTitle,
  emptyHint,
}: DataTableProps<T>) {
  const base = sort?.replace(/^-/, "");
  const descending = sort?.startsWith("-") ?? false;

  const nextSort = (key: string): string => {
    const bare = key.replace(/^-/, "");
    // First click sorts ascending, clicking the active column again flips the direction.
    return base === bare && !descending ? `-${bare}` : bare;
  };

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface">
      <div className="overflow-x-auto" aria-busy={loading}>
        <table className="w-full min-w-[40rem] text-left text-sm">
          <caption className="sr-only">{caption}</caption>
          <thead className="border-b border-border text-xs text-muted">
            <tr>
              {columns.map((column) => {
                const sortable = Boolean(column.sortKey && onSort);
                const bare = column.sortKey?.replace(/^-/, "");
                const active = sortable && bare === base;
                return (
                  <th
                    key={column.key}
                    scope="col"
                    aria-sort={
                      active
                        ? descending
                          ? "descending"
                          : "ascending"
                        : sortable
                          ? "none"
                          : undefined
                    }
                    className={cn(
                      "px-4 py-3 font-medium",
                      column.align === "right" && "text-right",
                      column.className,
                    )}
                  >
                    {sortable && column.sortKey ? (
                      <button
                        type="button"
                        onClick={() => onSort?.(nextSort(column.sortKey as string))}
                        className={cn(
                          "inline-flex items-center gap-1 rounded-md hover:text-foreground",
                          active && "text-foreground",
                        )}
                      >
                        {column.header}
                        <SortIcon state={active ? (descending ? "desc" : "asc") : "none"} />
                      </button>
                    ) : (
                      column.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className={cn(loading && rows && "opacity-60 transition-opacity")}>
            {rows === undefined &&
              Array.from({ length: 8 }, (_, i) => (
                <tr key={i} className="border-b border-border last:border-0">
                  <td colSpan={columns.length} className="px-4 py-3">
                    <div className="h-5 animate-pulse rounded bg-surface-hover" />
                  </td>
                </tr>
              ))}
            {rows?.map((row) => {
              const key = rowKey(row);
              const selected = key === selectedKey;
              return (
                <tr
                  key={key}
                  aria-selected={onSelect ? selected : undefined}
                  className={cn(
                    "border-b border-border last:border-0",
                    onSelect && "cursor-pointer hover:bg-surface-hover",
                    selected && "bg-accent/10",
                  )}
                  onClick={() => onSelect?.(row)}
                >
                  {columns.map((column, index) => (
                    <td
                      key={column.key}
                      className={cn(
                        "px-4 py-3",
                        column.align === "right" && "text-right tabular-nums",
                        column.className,
                      )}
                    >
                      {/* The first cell is a real button so the row is reachable with the keyboard. */}
                      {index === 0 && onSelect ? (
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            onSelect(row);
                          }}
                          className="rounded text-left font-medium text-foreground hover:text-accent"
                        >
                          {column.cell(row)}
                        </button>
                      ) : (
                        column.cell(row)
                      )}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {rows?.length === 0 && (
        <div className="flex flex-col items-center gap-2 px-4 py-14 text-center">
          <Inbox aria-hidden className="size-8 text-muted" />
          <p className="font-medium">{emptyTitle}</p>
          {emptyHint && <p className="max-w-sm text-sm text-muted">{emptyHint}</p>}
        </div>
      )}
    </div>
  );
}

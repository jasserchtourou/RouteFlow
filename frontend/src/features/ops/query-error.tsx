"use client";

import { RefreshCw, WifiOff } from "lucide-react";
import { Card } from "@/components/ui/card";
import { ApiError } from "@/lib/api";

export function QueryError({
  error,
  onRetry,
  what,
}: {
  error: unknown;
  onRetry: () => void;
  what: string;
}) {
  const message = error instanceof ApiError ? error.message : `Could not load ${what}.`;
  return (
    <Card role="alert" className="flex flex-col items-center gap-3 py-10 text-center">
      <WifiOff aria-hidden className="size-8 text-danger" />
      <p className="font-medium">{what} unavailable</p>
      <p className="max-w-md text-sm text-muted">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-1 inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-4 text-sm font-medium text-accent-fg hover:opacity-90"
      >
        <RefreshCw aria-hidden className="size-4" />
        Try again
      </button>
    </Card>
  );
}

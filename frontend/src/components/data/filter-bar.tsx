"use client";

import { Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

/** Text filter: typing updates the URL after a short pause, not on every keystroke. */
export function SearchField({
  value,
  onChange,
  label,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  label: string;
  placeholder: string;
}) {
  const [text, setText] = useState(value);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Follow external changes (back button, a link, clearing all filters).
  useEffect(() => setText(value), [value]);
  useEffect(() => () => clearTimeout(timer.current), []);

  const change = (next: string) => {
    setText(next);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => onChange(next.trim()), 300);
  };

  return (
    <label className="relative block w-full sm:w-72">
      <span className="sr-only">{label}</span>
      <Search
        aria-hidden
        className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
      />
      <input
        type="search"
        value={text}
        placeholder={placeholder}
        onChange={(event) => change(event.target.value)}
        className="h-10 w-full rounded-lg border border-border bg-surface pl-9 pr-9 text-sm placeholder:text-muted"
      />
      {text && (
        <button
          type="button"
          aria-label="Clear search"
          onClick={() => {
            clearTimeout(timer.current);
            setText("");
            onChange("");
          }}
          className="absolute right-1.5 top-1/2 grid size-7 -translate-y-1/2 place-items-center rounded-md text-muted hover:bg-surface-hover"
        >
          <X aria-hidden className="size-3.5" />
        </button>
      )}
    </label>
  );
}

/** A group of toggle chips: select any number of values (an empty selection means "all"). */
export function ChipFilter({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: readonly { value: string; label: string }[];
  selected: readonly string[];
  onChange: (next: string[]) => void;
}) {
  const toggle = (value: string) =>
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-1.5">
      {options.map((option) => {
        const on = selected.includes(option.value);
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={on}
            onClick={() => toggle(option.value)}
            className={cn(
              "h-8 rounded-full border px-3 text-xs font-medium transition-colors",
              on
                ? "border-accent bg-accent/15 text-accent"
                : "border-border text-muted hover:bg-surface-hover hover:text-foreground",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

/** A single on/off filter (e.g. "Delayed only"). */
export function ToggleChip({
  label,
  on,
  onChange,
}: {
  label: string;
  on: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={() => onChange(!on)}
      className={cn(
        "h-8 rounded-full border px-3 text-xs font-medium transition-colors",
        on
          ? "border-warning bg-warning/15 text-warning"
          : "border-border text-muted hover:bg-surface-hover hover:text-foreground",
      )}
    >
      {label}
    </button>
  );
}

export function FilterBar({ children }: { children: React.ReactNode }) {
  return <div className="mb-4 flex flex-wrap items-center gap-3">{children}</div>;
}

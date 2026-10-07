"use client";

import {
  Home,
  Keyboard,
  Maximize2,
  Minimize2,
  Minus,
  Moon,
  PanelsTopLeft,
  Plus,
  RotateCcw,
  RotateCw,
  Sun,
  type LucideIcon,
} from "lucide-react";
import type { RefObject } from "react";
import { cn } from "@/lib/utils";
import type { ThemeName } from "../scene/palette";
import type { CameraApi } from "../scene/site-canvas";

export const QUARTER_TURN = Math.PI / 4;

function ToolButton({
  label,
  shortcut,
  icon: Icon,
  onClick,
  pressed,
}: {
  label: string;
  shortcut?: string;
  icon: LucideIcon;
  onClick: () => void;
  pressed?: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={pressed}
      title={shortcut ? `${label} (${shortcut})` : label}
      onClick={onClick}
      className={cn(
        "grid size-9 place-items-center rounded-lg text-foreground transition-colors hover:bg-surface-hover",
        pressed && "bg-accent/20 text-accent",
      )}
    >
      <Icon aria-hidden className="size-4" />
    </button>
  );
}

function Separator() {
  return <span aria-hidden className="mx-0.5 h-5 w-px bg-border" />;
}

export function Toolbar({
  apiRef,
  theme,
  onTheme,
  panelsHidden,
  onPanelsHidden,
  fullscreen,
  onFullscreen,
  onHelp,
}: {
  apiRef: RefObject<CameraApi | null>;
  theme: ThemeName;
  onTheme: (theme: ThemeName) => void;
  panelsHidden: boolean;
  onPanelsHidden: (hidden: boolean) => void;
  fullscreen: boolean;
  onFullscreen: () => void;
  onHelp: () => void;
}) {
  const camera = (action: (api: CameraApi) => void) => () => {
    if (apiRef.current) action(apiRef.current);
  };
  return (
    <div
      role="toolbar"
      aria-label="View controls"
      className="pointer-events-auto flex items-center gap-0.5 rounded-xl border border-border bg-surface/90 p-1 shadow-xl backdrop-blur-md"
    >
      <ToolButton label="Zoom in" shortcut="+" icon={Plus} onClick={camera((a) => a.zoomIn())} />
      <ToolButton label="Zoom out" shortcut="-" icon={Minus} onClick={camera((a) => a.zoomOut())} />
      <ToolButton
        label="Rotate left"
        shortcut="["
        icon={RotateCcw}
        onClick={camera((a) => a.rotate(-QUARTER_TURN))}
      />
      <ToolButton
        label="Rotate right"
        shortcut="]"
        icon={RotateCw}
        onClick={camera((a) => a.rotate(QUARTER_TURN))}
      />
      <ToolButton label="Reset view" shortcut="R" icon={Home} onClick={camera((a) => a.reset())} />
      <Separator />
      <ToolButton
        label={panelsHidden ? "Show panels" : "Hide panels"}
        shortcut="H"
        icon={PanelsTopLeft}
        pressed={panelsHidden}
        onClick={() => onPanelsHidden(!panelsHidden)}
      />
      <ToolButton
        label={theme === "night" ? "Switch to daylight scene" : "Switch to night scene"}
        icon={theme === "night" ? Sun : Moon}
        onClick={() => onTheme(theme === "night" ? "day" : "night")}
      />
      <ToolButton
        label={fullscreen ? "Exit full screen" : "Full screen"}
        shortcut="F"
        icon={fullscreen ? Minimize2 : Maximize2}
        onClick={onFullscreen}
      />
      <ToolButton label="Keyboard shortcuts" shortcut="?" icon={Keyboard} onClick={onHelp} />
    </div>
  );
}

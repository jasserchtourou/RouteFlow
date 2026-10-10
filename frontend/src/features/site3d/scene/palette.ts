/** Scene colours. Two looks share one shape: a dark "night" site (default) and a "day" site. */

export interface Palette {
  background: string;
  ground: string;
  pad: string;
  road: string;
  roadMarking: string;
  yardLine: string;
  building: string;
  roof: string;
  doorFrame: string;
  trailer: string;
  cab: string;
  wheel: string;
  forklift: string;
  forkliftDark: string;
  carton: string;
  pallet: string;
  rack: string;
  tree: string;
  trunk: string;
  fence: string;
  select: string;
  warning: string;
  doorState: Record<"AVAILABLE" | "BOOKED" | "OCCUPIED" | "OUT_OF_SERVICE", string>;
  /** Window glass, lamp heads and the sky colour of the hemisphere light. */
  glass: string;
  lamp: string;
  sky: string;
  ambient: number;
  sun: number;
  /** Strength of the sky/ground fill light. */
  hemi: number;
}

export const NIGHT: Palette = {
  background: "#0a0f1f",
  ground: "#1b2748",
  pad: "#26365f",
  road: "#101830",
  roadMarking: "#51618f",
  yardLine: "#e0a526",
  building: "#2a4b9b",
  roof: "#35549f",
  doorFrame: "#4f8cff",
  trailer: "#dfe6f5",
  cab: "#4f8cff",
  wheel: "#0a0e1a",
  forklift: "#f2b134",
  forkliftDark: "#1a2033",
  carton: "#c89b62",
  pallet: "#8a6a3f",
  rack: "#5b6cae",
  tree: "#2f7d5c",
  trunk: "#5a4632",
  fence: "#4a5a86",
  select: "#7fb0ff",
  warning: "#fbbf24",
  doorState: {
    AVAILABLE: "#34d399",
    BOOKED: "#fbbf24",
    OCCUPIED: "#f87171",
    OUT_OF_SERVICE: "#566083",
  },
  glass: "#16233f",
  lamp: "#ffd88a",
  sky: "#9db7ff",
  ambient: 0.45,
  sun: 1.1,
  hemi: 0.45,
};

export const DAY: Palette = {
  background: "#d7e3fb",
  ground: "#e8eefb",
  pad: "#d2dcf1",
  road: "#b3bfd8",
  roadMarking: "#f4f7ff",
  yardLine: "#e8a317",
  building: "#2f5bd8",
  roof: "#3d6af0",
  doorFrame: "#1f46b8",
  trailer: "#ffffff",
  cab: "#2f5bd8",
  wheel: "#1b2236",
  forklift: "#f5b82e",
  forkliftDark: "#2a3146",
  carton: "#d9ac74",
  pallet: "#a98657",
  rack: "#5470c8",
  tree: "#4fb286",
  trunk: "#7a5f43",
  fence: "#9aa8cc",
  select: "#2f6bff",
  warning: "#e8a317",
  doorState: {
    AVAILABLE: "#2fbf8a",
    BOOKED: "#f1b21d",
    OCCUPIED: "#ee6b6b",
    OUT_OF_SERVICE: "#9aa3bd",
  },
  glass: "#9fc2ff",
  lamp: "#fff3d0",
  sky: "#ffffff",
  ambient: 0.6,
  sun: 1.35,
  hemi: 0.5,
};

export type ThemeName = "night" | "day";
export const PALETTES: Record<ThemeName, Palette> = { night: NIGHT, day: DAY };

import type { Selection } from "../model";

/** Shared by every clickable object in the scene. */
export interface Interaction {
  selection: Selection | null;
  hovered: Selection | null;
  select: (selection: Selection | null) => void;
  hover: (selection: Selection | null) => void;
}

export function isSame(a: Selection | null, b: Selection): boolean {
  return a !== null && a.kind === b.kind && a.id === b.id;
}

/** Props that make a mesh/group selectable with hover feedback. */
export function pointerHandlers(interaction: Interaction, target: Selection) {
  return {
    onClick: (event: { stopPropagation: () => void }) => {
      event.stopPropagation();
      interaction.select(target);
    },
    onPointerOver: (event: { stopPropagation: () => void }) => {
      event.stopPropagation();
      interaction.hover(target);
      document.body.style.cursor = "pointer";
    },
    onPointerOut: () => {
      interaction.hover(null);
      document.body.style.cursor = "";
    },
  };
}

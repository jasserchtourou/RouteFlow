"use client";

import { Edges } from "@react-three/drei";
import {
  BUILDING_DEPTH,
  BUILDING_HEIGHT,
  DOCK_SPACING,
  FACADE_Z,
  buildingWidth,
  dockX,
} from "../geometry";
import type { SiteDock } from "../model";
import { Label } from "./label";
import { isSame, pointerHandlers, type Interaction } from "./interaction";
import type { Palette } from "./palette";

const DOOR_WIDTH = 3;
const DOOR_HEIGHT = 3.6;

export const DOCK_STATE_LABEL: Record<SiteDock["state"], string> = {
  AVAILABLE: "Available",
  BOOKED: "Booked",
  OCCUPIED: "Occupied",
  OUT_OF_SERVICE: "Out of service",
};

function DockDoor({
  dock,
  dockCount,
  palette,
  interaction,
}: {
  dock: SiteDock;
  dockCount: number;
  palette: Palette;
  interaction: Interaction;
}) {
  const target = { kind: "dock", id: dock.id } as const;
  const selected = isSame(interaction.selection, target);
  const hovered = isSame(interaction.hovered, target);
  const x = dockX(dock.position, dockCount);
  const z = FACADE_Z + 0.06;
  const stateColor = palette.doorState[dock.state];

  return (
    <group position={[x, 0, z]} {...pointerHandlers(interaction, target)}>
      {/* Frame */}
      {[-1, 1].map((side) => (
        <mesh
          key={side}
          position={[side * (DOOR_WIDTH / 2 + 0.15), DOOR_HEIGHT / 2, 0.08]}
          castShadow
        >
          <boxGeometry args={[0.3, DOOR_HEIGHT, 0.3]} />
          <meshStandardMaterial color={palette.doorFrame} />
        </mesh>
      ))}
      <mesh position={[0, DOOR_HEIGHT + 0.15, 0.08]} castShadow>
        <boxGeometry args={[DOOR_WIDTH + 0.6, 0.3, 0.3]} />
        <meshStandardMaterial color={palette.doorFrame} />
      </mesh>
      {/* Door opening, tinted by occupancy */}
      <mesh position={[0, DOOR_HEIGHT / 2, 0]}>
        <boxGeometry args={[DOOR_WIDTH, DOOR_HEIGHT, 0.12]} />
        <meshStandardMaterial
          color={stateColor}
          emissive={stateColor}
          emissiveIntensity={dock.state === "OUT_OF_SERVICE" ? 0 : 0.35}
        />
        {selected && <Edges color={palette.select} linewidth={3} />}
      </mesh>
      {/* Door number plate */}
      <mesh position={[0, DOOR_HEIGHT + 0.65, 0.1]}>
        <boxGeometry args={[1.2, 0.5, 0.05]} />
        <meshStandardMaterial color={palette.doorFrame} />
      </mesh>
      <Label position={[0, DOOR_HEIGHT + 1.4, 0.4]} emphasis={selected}>
        {hovered || selected ? `${dock.code} · ${DOCK_STATE_LABEL[dock.state]}` : dock.code}
      </Label>
    </group>
  );
}

export function Building({
  docks,
  dockCount,
  palette,
  interaction,
}: {
  docks: SiteDock[];
  dockCount: number;
  palette: Palette;
  interaction: Interaction;
}) {
  const width = buildingWidth(dockCount);
  return (
    <group>
      <mesh
        position={[0, BUILDING_HEIGHT / 2, FACADE_Z - BUILDING_DEPTH / 2]}
        castShadow
        receiveShadow
      >
        <boxGeometry args={[width, BUILDING_HEIGHT, BUILDING_DEPTH]} />
        <meshStandardMaterial color={palette.building} />
      </mesh>
      {/* Roof slab, slightly larger than the walls */}
      <mesh position={[0, BUILDING_HEIGHT + 0.25, FACADE_Z - BUILDING_DEPTH / 2]} castShadow>
        <boxGeometry args={[width + 0.8, 0.5, BUILDING_DEPTH + 0.8]} />
        <meshStandardMaterial color={palette.roof} />
      </mesh>
      {/* Canopy over the doors */}
      <mesh position={[0, BUILDING_HEIGHT - 0.6, FACADE_Z + 0.7]} castShadow>
        <boxGeometry args={[width - DOCK_SPACING * 0.2, 0.25, 1.6]} />
        <meshStandardMaterial color={palette.roof} />
      </mesh>
      {docks.map((dock) => (
        <DockDoor
          key={dock.id}
          dock={dock}
          dockCount={dockCount}
          palette={palette}
          interaction={interaction}
        />
      ))}
    </group>
  );
}

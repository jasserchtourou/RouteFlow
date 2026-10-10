"use client";

import { Edges } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { CanvasTexture, SRGBColorSpace, type Mesh, type MeshStandardMaterial } from "three";
import { prefersReducedMotion } from "@/lib/motion";
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

/** Traffic light over a door: steady when free, breathing while booked or in use. */
function DockLight({ color, active }: { color: string; active: boolean }) {
  const light = useRef<Mesh>(null);
  useFrame(({ clock }) => {
    if (!light.current || prefersReducedMotion()) return;
    const material = light.current.material as MeshStandardMaterial;
    material.emissiveIntensity = active
      ? 0.7 + 0.6 * (0.5 + 0.5 * Math.sin(clock.elapsedTime * 3))
      : 0.8;
  });
  return (
    <mesh ref={light} position={[DOOR_WIDTH / 2 - 0.2, DOOR_HEIGHT + 0.65, 0.2]}>
      <boxGeometry args={[0.36, 0.36, 0.12]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.8}
        toneMapped={false}
      />
    </mesh>
  );
}

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
  const inUse = dock.state === "OCCUPIED" || dock.state === "BOOKED";

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
      {/* Roller-door slats */}
      {Array.from({ length: 6 }, (_, i) => (
        <mesh key={i} position={[0, 0.45 + i * 0.55, 0.07]}>
          <boxGeometry args={[DOOR_WIDTH - 0.1, 0.04, 0.02]} />
          <meshStandardMaterial color={palette.wheel} transparent opacity={0.35} />
        </mesh>
      ))}
      {/* Rubber bumpers and the leveller plate trucks back onto */}
      {[-1, 1].map((side) => (
        <mesh key={side} position={[side * (DOOR_WIDTH / 2 - 0.35), 0.75, 0.3]} castShadow>
          <boxGeometry args={[0.3, 0.45, 0.3]} />
          <meshStandardMaterial color={palette.wheel} roughness={0.9} />
        </mesh>
      ))}
      <mesh position={[0, 0.04, 0.9]} rotation-x={-Math.PI / 2}>
        <planeGeometry args={[DOOR_WIDTH - 0.4, 1.4]} />
        <meshStandardMaterial color={palette.rack} metalness={0.4} roughness={0.5} />
      </mesh>
      {/* Door number plate */}
      <mesh position={[-0.3, DOOR_HEIGHT + 0.65, 0.1]}>
        <boxGeometry args={[1.2, 0.5, 0.05]} />
        <meshStandardMaterial color={palette.doorFrame} />
      </mesh>
      {dock.state !== "OUT_OF_SERVICE" && <DockLight color={stateColor} active={inUse} />}
      <Label position={[0, DOOR_HEIGHT + 1.4, 0.4]} emphasis={selected}>
        {hovered || selected ? `${dock.code} · ${DOCK_STATE_LABEL[dock.state]}` : dock.code}
      </Label>
    </group>
  );
}

/** The site's code painted on a panel high on the facade. */
function Sign({ code, palette, width }: { code: string; palette: Palette; width: number }) {
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 128;
    const g = canvas.getContext("2d");
    if (g) {
      g.fillStyle = palette.doorFrame;
      g.fillRect(0, 0, 512, 128);
      g.fillStyle = "#ffffff";
      g.font = '800 64px system-ui, "Segoe UI", sans-serif';
      g.textAlign = "center";
      g.textBaseline = "middle";
      g.fillText(code, 256, 68);
    }
    const t = new CanvasTexture(canvas);
    t.colorSpace = SRGBColorSpace;
    return t;
  }, [code, palette.doorFrame]);
  useEffect(() => () => texture.dispose(), [texture]);

  // A billboard on the roof edge: readable from the isometric camera, clear of the doors.
  return (
    <group position={[-width / 2 + 4.6, BUILDING_HEIGHT + 0.5, FACADE_Z - 0.8]}>
      {[-2, 2].map((x) => (
        <mesh key={x} position={[x, 0.5, -0.05]}>
          <boxGeometry args={[0.12, 1, 0.12]} />
          <meshStandardMaterial color={palette.wheel} />
        </mesh>
      ))}
      <mesh position={[0, 1.35, 0]} castShadow>
        <boxGeometry args={[5.6, 1.4, 0.08]} />
        <meshStandardMaterial color={palette.doorFrame} />
      </mesh>
      <mesh position={[0, 1.35, 0.045]}>
        <planeGeometry args={[5.6, 1.4]} />
        <meshStandardMaterial
          map={texture}
          emissive="#ffffff"
          emissiveMap={texture}
          emissiveIntensity={0.3}
        />
      </mesh>
    </group>
  );
}

export function Building({
  code,
  docks,
  dockCount,
  palette,
  interaction,
}: {
  code: string;
  docks: SiteDock[];
  dockCount: number;
  palette: Palette;
  interaction: Interaction;
}) {
  const width = buildingWidth(dockCount);
  const centreZ = FACADE_Z - BUILDING_DEPTH / 2;
  // Vertical wall ribs every 2 m along the facade and the sides (cladding panels).
  const ribs = useMemo(
    () => Array.from({ length: Math.floor(width / 2) - 1 }, (_, i) => -width / 2 + 2 * (i + 1)),
    [width],
  );
  const skylights = useMemo(() => {
    const count = Math.max(1, Math.floor(width / 7));
    return Array.from({ length: count }, (_, i) => -width / 2 + (width / count) * (i + 0.5));
  }, [width]);

  return (
    <group>
      <mesh position={[0, BUILDING_HEIGHT / 2, centreZ]} castShadow receiveShadow>
        <boxGeometry args={[width, BUILDING_HEIGHT, BUILDING_DEPTH]} />
        <meshStandardMaterial color={palette.building} roughness={0.75} />
      </mesh>
      {/* Plinth along the bottom of the walls */}
      <mesh position={[0, 0.3, centreZ]}>
        <boxGeometry args={[width + 0.08, 0.6, BUILDING_DEPTH + 0.08]} />
        <meshStandardMaterial color={palette.doorFrame} roughness={0.8} />
      </mesh>
      {ribs.map((x) => (
        <mesh key={x} position={[x, BUILDING_HEIGHT / 2 + 0.3, FACADE_Z + 0.03]}>
          <boxGeometry args={[0.08, BUILDING_HEIGHT - 0.6, 0.06]} />
          <meshStandardMaterial color={palette.roof} roughness={0.6} />
        </mesh>
      ))}
      {/* Clerestory windows above the doors */}
      <mesh position={[0, BUILDING_HEIGHT - 1.15, FACADE_Z + 0.04]}>
        <planeGeometry args={[width - 1, 0.45]} />
        <meshStandardMaterial
          color={palette.glass}
          emissive={palette.lamp}
          emissiveIntensity={0.18}
          metalness={0.6}
          roughness={0.2}
        />
      </mesh>
      <Sign code={code} palette={palette} width={width} />

      {/* Roof slab, slightly larger than the walls, with a parapet line */}
      <mesh position={[0, BUILDING_HEIGHT + 0.25, centreZ]} castShadow>
        <boxGeometry args={[width + 0.8, 0.5, BUILDING_DEPTH + 0.8]} />
        <meshStandardMaterial color={palette.roof} />
      </mesh>
      {skylights.map((x) => (
        <mesh key={x} position={[x, BUILDING_HEIGHT + 0.55, centreZ]}>
          <boxGeometry args={[2.2, 0.12, BUILDING_DEPTH * 0.6]} />
          <meshStandardMaterial
            color={palette.glass}
            metalness={0.5}
            roughness={0.25}
            emissive={palette.select}
            emissiveIntensity={0.12}
          />
        </mesh>
      ))}
      {/* Rooftop HVAC units, along the back edge (clear of the skylights) */}
      {[0, 2.2].map((offset) => (
        <group key={offset} position={[width * 0.3 - offset, BUILDING_HEIGHT + 0.5, centreZ - 5.7]}>
          <mesh position={[0, 0.45, 0]} castShadow>
            <boxGeometry args={[1.6, 0.9, 1.2]} />
            <meshStandardMaterial color="#aab4cc" roughness={0.5} />
          </mesh>
          <mesh position={[0, 0.92, 0]} rotation-x={-Math.PI / 2}>
            <circleGeometry args={[0.38, 18]} />
            <meshStandardMaterial color={palette.wheel} />
          </mesh>
        </group>
      ))}
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

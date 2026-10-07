"use client";

import { Edges } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Group } from "three";
import { MathUtils } from "three";
import type { SiteDock, SiteVisit, Timings } from "../model";
import { truckPose } from "../motion";
import { isSame, pointerHandlers, type Interaction } from "./interaction";
import { Label } from "./label";
import type { Palette } from "./palette";

export const VISIT_STATE_LABEL: Record<SiteVisit["state"], string> = {
  SCHEDULED: "Scheduled",
  EN_ROUTE: "En route",
  WAITING: "Waiting",
  DOCKED: "Docking",
  LOADING: "Loading",
  UNLOADING: "Unloading",
  DEPARTED: "Departing",
  COMPLETED: "Completed",
};

const WHEELS: [number, number][] = [
  [3.2, 1.1],
  [3.2, -1.1],
  [-0.2, 1.1],
  [-0.2, -1.1],
  [-3.4, 1.1],
  [-3.4, -1.1],
];

/** Moves a heading towards a target the short way round (radians). */
function approachAngle(current: number, target: number, factor: number): number {
  const delta = MathUtils.euclideanModulo(target - current + Math.PI, Math.PI * 2) - Math.PI;
  return current + delta * factor;
}

export function Truck({
  visit,
  dock,
  dockCount,
  timings,
  getNow,
  palette,
  interaction,
}: {
  visit: SiteVisit;
  dock: SiteDock;
  dockCount: number;
  timings: Timings;
  getNow: () => number;
  palette: Palette;
  interaction: Interaction;
}) {
  const group = useRef<Group>(null);
  const placed = useRef(false);
  const target = { kind: "truck", id: visit.id } as const;
  const selected = isSame(interaction.selection, target);
  const hovered = isSame(interaction.hovered, target);

  useFrame((_, delta) => {
    const node = group.current;
    if (!node) return;
    const pose = truckPose(visit, dock, dockCount, timings, getNow());
    node.visible = pose !== null;
    if (!pose) {
      placed.current = false;
      return;
    }
    node.position.set(pose.x, 0, pose.z);
    // Snap on the first frame, then turn smoothly (corners are 90 degree changes of heading).
    node.rotation.y = placed.current
      ? approachAngle(node.rotation.y, pose.heading, Math.min(1, delta * 8))
      : pose.heading;
    placed.current = true;
  });

  return (
    <group ref={group} visible={false} {...pointerHandlers(interaction, target)}>
      {/* Trailer */}
      <mesh position={[-1.5, 2.1, 0]} castShadow>
        <boxGeometry args={[6.2, 2.7, 2.5]} />
        <meshStandardMaterial color={palette.trailer} />
        {selected && <Edges color={palette.select} linewidth={3} />}
      </mesh>
      <mesh position={[-1.5, 2.1, 0]}>
        <boxGeometry args={[6.24, 0.5, 2.54]} />
        <meshStandardMaterial color={palette.cab} />
      </mesh>
      {/* Chassis */}
      <mesh position={[0, 0.65, 0]} castShadow>
        <boxGeometry args={[9, 0.35, 2.1]} />
        <meshStandardMaterial color={palette.wheel} />
      </mesh>
      {/* Cab */}
      <mesh position={[3.1, 1.6, 0]} castShadow>
        <boxGeometry args={[2.3, 2.1, 2.5]} />
        <meshStandardMaterial color={palette.cab} />
      </mesh>
      <mesh position={[4.28, 1.9, 0]}>
        <boxGeometry args={[0.06, 0.8, 2.1]} />
        <meshStandardMaterial color={palette.wheel} />
      </mesh>
      {WHEELS.map(([x, z]) => (
        <mesh key={`${x}/${z}`} position={[x, 0.5, z]} rotation-x={Math.PI / 2} castShadow>
          <cylinderGeometry args={[0.5, 0.5, 0.45, 14]} />
          <meshStandardMaterial color={palette.wheel} />
        </mesh>
      ))}
      {/* Selection zone on the ground */}
      {selected && (
        <mesh position={[0, 0.05, 0]} rotation-x={-Math.PI / 2}>
          <planeGeometry args={[11, 4.6]} />
          <meshBasicMaterial color={palette.select} transparent opacity={0.25} />
        </mesh>
      )}
      {(hovered || selected) && (
        <Label position={[0, 4.6, 0]} emphasis={selected}>
          {visit.truckCode} · {VISIT_STATE_LABEL[visit.state]}
        </Label>
      )}
    </group>
  );
}

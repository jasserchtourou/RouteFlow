"use client";

import { Edges } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Group, Mesh, MeshStandardMaterial } from "three";
import { MathUtils } from "three";
import type { ForkliftFleet } from "../fleet";
import type { SiteEquipment } from "../model";
import { parkedPose } from "../motion";
import { isSame, pointerHandlers, type Interaction } from "./interaction";
import { Label } from "./label";
import type { Palette } from "./palette";

/** Visual scale: a forklift at true size looks like a toy next to a 9 m truck. */
const SCALE = 1.35;
const LIFT = 0.55; // how far the carriage rises with a load

function approachAngle(current: number, target: number, factor: number): number {
  const delta = MathUtils.euclideanModulo(target - current + Math.PI, Math.PI * 2) - Math.PI;
  return current + delta * factor;
}

function Wheel({
  x,
  z,
  radius,
  width,
  color,
}: {
  x: number;
  z: number;
  radius: number;
  width: number;
  color: string;
}) {
  return (
    <group position={[x, radius, z]} rotation-x={Math.PI / 2}>
      <mesh castShadow>
        <cylinderGeometry args={[radius, radius, width, 18]} />
        <meshStandardMaterial color="#14171f" roughness={0.9} />
      </mesh>
      <mesh position={[0, Math.sign(z) * (width / 2 + 0.005), 0]}>
        <cylinderGeometry args={[radius * 0.55, radius * 0.55, 0.02, 14]} />
        <meshStandardMaterial color={color} />
      </mesh>
    </group>
  );
}

/**
 * A counterbalance forklift, front along +x: chassis and counterweight, driver's seat under an
 * overhead guard, a two-piece mast with a carriage and forks that rise with a load.
 */
export function Forklift({
  unit,
  fleet,
  dockCount,
  palette,
  interaction,
}: {
  unit: SiteEquipment;
  fleet: ForkliftFleet;
  dockCount: number;
  palette: Palette;
  interaction: Interaction;
}) {
  const group = useRef<Group>(null);
  const carriage = useRef<Group>(null);
  const load = useRef<Group>(null);
  const beacon = useRef<Mesh>(null);
  const placed = useRef(false);
  const target = { kind: "forklift", id: unit.id } as const;
  const selected = isSame(interaction.selection, target);
  const hovered = isSame(interaction.hovered, target);
  const working = unit.status === "ACTIVE";
  const body = unit.status === "MAINTENANCE" ? palette.warning : palette.forklift;
  const dark = palette.forkliftDark;

  useFrame((state, delta) => {
    const node = group.current;
    if (!node) return;
    const sim = fleet.pose(unit.id);
    const pose = sim ? { ...sim, working: true } : parkedPose(unit, dockCount);
    node.position.set(pose.x, 0, pose.z);
    node.rotation.y = placed.current
      ? approachAngle(node.rotation.y, pose.heading, Math.min(1, delta * 6))
      : pose.heading;
    placed.current = true;
    if (load.current) load.current.visible = pose.carrying;
    if (carriage.current) {
      // Smoothly raise the forks when carrying, lower them when empty.
      const goal = pose.carrying ? LIFT : 0;
      carriage.current.position.y += (goal - carriage.current.position.y) * Math.min(1, delta * 4);
    }
    if (beacon.current) {
      const material = beacon.current.material as MeshStandardMaterial;
      material.emissiveIntensity = pose.working
        ? 0.4 + 0.6 * (0.5 + 0.5 * Math.sin(state.clock.elapsedTime * 6))
        : 0.1;
    }
  });

  return (
    <group ref={group} scale={SCALE} {...pointerHandlers(interaction, target)}>
      {/* Chassis and counterweight */}
      <mesh position={[-0.2, 0.55, 0]} castShadow>
        <boxGeometry args={[1.9, 0.5, 1.1]} />
        <meshStandardMaterial color={body} roughness={0.55} />
        {selected && <Edges color={palette.select} linewidth={3} />}
      </mesh>
      <mesh position={[-0.2, 0.3, 0]}>
        <boxGeometry args={[1.95, 0.14, 1.05]} />
        <meshStandardMaterial color={dark} />
      </mesh>
      <mesh position={[-1.0, 0.95, 0]} castShadow>
        <boxGeometry args={[0.55, 0.85, 1.12]} />
        <meshStandardMaterial color={body} roughness={0.55} />
      </mesh>
      <mesh position={[-0.65, 0.95, 0]} castShadow>
        <boxGeometry args={[0.75, 0.3, 1.0]} />
        <meshStandardMaterial color={body} roughness={0.55} />
      </mesh>
      {/* Seat, backrest, dashboard and steering wheel */}
      <mesh position={[-0.35, 1.0, 0]}>
        <boxGeometry args={[0.45, 0.12, 0.5]} />
        <meshStandardMaterial color={dark} />
      </mesh>
      <mesh position={[-0.58, 1.3, 0]}>
        <boxGeometry args={[0.1, 0.55, 0.5]} />
        <meshStandardMaterial color={dark} />
      </mesh>
      <mesh position={[0.3, 0.98, 0]} rotation-z={-0.5}>
        <boxGeometry args={[0.1, 0.55, 0.14]} />
        <meshStandardMaterial color={dark} />
      </mesh>
      <mesh position={[0.18, 1.28, 0]} rotation-z={0.9}>
        <torusGeometry args={[0.15, 0.025, 6, 14]} />
        <meshStandardMaterial color="#0c0e14" />
      </mesh>
      {/* Driver */}
      {working && (
        <group position={[-0.25, 1.05, 0]}>
          <mesh position={[0, 0.3, 0]} castShadow>
            <boxGeometry args={[0.32, 0.5, 0.42]} />
            <meshStandardMaterial color="#ff7a1a" />
          </mesh>
          <mesh position={[0, 0.7, 0]}>
            <sphereGeometry args={[0.16, 12, 10]} />
            <meshStandardMaterial color="#e8b894" />
          </mesh>
          <mesh position={[0, 0.78, 0]}>
            <sphereGeometry args={[0.18, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
            <meshStandardMaterial color="#f2d24a" />
          </mesh>
        </group>
      )}
      {/* Overhead guard */}
      {[
        [-0.8, -0.5],
        [-0.8, 0.5],
        [0.45, -0.5],
        [0.45, 0.5],
      ].map(([x, z]) => (
        <mesh key={`${x}/${z}`} position={[x, 1.65, z]}>
          <cylinderGeometry args={[0.035, 0.035, 1.3, 8]} />
          <meshStandardMaterial color={dark} />
        </mesh>
      ))}
      <mesh position={[-0.18, 2.3, 0]} castShadow>
        <boxGeometry args={[1.45, 0.06, 1.15]} />
        <meshStandardMaterial color={dark} />
      </mesh>
      {[-0.35, 0, 0.35].map((z) => (
        <mesh key={z} position={[-0.18, 2.36, z]}>
          <boxGeometry args={[1.45, 0.03, 0.08]} />
          <meshStandardMaterial color={body} />
        </mesh>
      ))}
      <mesh ref={beacon} position={[-0.8, 2.42, 0]}>
        <cylinderGeometry args={[0.07, 0.09, 0.14, 10]} />
        <meshStandardMaterial color="#ffb21a" emissive="#ff9d00" emissiveIntensity={0.5} />
      </mesh>
      {/* Wheels */}
      <Wheel x={0.4} z={0.62} radius={0.4} width={0.3} color={body} />
      <Wheel x={0.4} z={-0.62} radius={0.4} width={0.3} color={body} />
      <Wheel x={-1.0} z={0.55} radius={0.32} width={0.26} color={body} />
      <Wheel x={-1.0} z={-0.55} radius={0.32} width={0.26} color={body} />
      {/* Mast */}
      {[-0.36, 0.36].map((z) => (
        <mesh key={z} position={[0.88, 1.15, z]} castShadow>
          <boxGeometry args={[0.1, 2.3, 0.1]} />
          <meshStandardMaterial color={dark} />
        </mesh>
      ))}
      <mesh position={[0.88, 2.2, 0]}>
        <boxGeometry args={[0.1, 0.08, 0.82]} />
        <meshStandardMaterial color={dark} />
      </mesh>
      <mesh position={[0.88, 0.7, 0]}>
        <boxGeometry args={[0.1, 0.1, 0.82]} />
        <meshStandardMaterial color={dark} />
      </mesh>
      {/* Carriage, forks and load: rise together */}
      <group ref={carriage}>
        <mesh position={[0.98, 0.55, 0]}>
          <boxGeometry args={[0.08, 0.55, 0.9]} />
          <meshStandardMaterial color={dark} />
        </mesh>
        {[-0.3, 0.3].map((z) => (
          <mesh key={z} position={[1.6, 0.16, z]} castShadow>
            <boxGeometry args={[1.25, 0.06, 0.13]} />
            <meshStandardMaterial color="#2b2f3a" metalness={0.5} roughness={0.4} />
          </mesh>
        ))}
        <group ref={load} position={[1.62, 0.2, 0]} visible={false}>
          <mesh position={[0, 0.07, 0]} castShadow>
            <boxGeometry args={[1.05, 0.14, 1.0]} />
            <meshStandardMaterial color={palette.pallet} />
          </mesh>
          <mesh position={[0, 0.58, 0]} castShadow>
            <boxGeometry args={[0.95, 0.85, 0.9]} />
            <meshStandardMaterial color={palette.carton} />
          </mesh>
        </group>
      </group>
      {selected && (
        <mesh position={[0.2, 0.04, 0]} rotation-x={-Math.PI / 2}>
          <planeGeometry args={[3.4, 1.9]} />
          <meshBasicMaterial color={palette.select} transparent opacity={0.28} />
        </mesh>
      )}
      {(hovered || selected) && (
        <Label position={[0, 3.2, 0]} emphasis={selected}>
          {unit.code} · {unit.status.toLowerCase()}
        </Label>
      )}
    </group>
  );
}

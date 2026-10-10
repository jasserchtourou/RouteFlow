"use client";

import { useMemo } from "react";
import { AdditiveBlending } from "three";
import {
  BAY_Z,
  FACADE_Z,
  ROAD_HALF_WIDTH,
  ROAD_Z,
  TRUCK_LENGTH,
  TRUCK_WIDTH,
  bayPoint,
  buildingWidth,
  yardHalfWidth,
} from "../geometry";
import type { Palette } from "./palette";

/** A flat rectangular outline lying on the ground (parking bays, staging zones). */
function Outline({
  x,
  z,
  width,
  depth,
  color,
}: {
  x: number;
  z: number;
  width: number;
  depth: number;
  color: string;
}) {
  const t = 0.12;
  return (
    <group position={[x, 0.03, z]}>
      {(
        [
          [0, -depth / 2, width, t],
          [0, depth / 2, width, t],
          [-width / 2, 0, t, depth],
          [width / 2, 0, t, depth],
        ] as const
      ).map(([ox, oz, w, d], i) => (
        <mesh key={i} position={[ox, 0, oz]} rotation-x={-Math.PI / 2}>
          <planeGeometry args={[w, d]} />
          <meshBasicMaterial color={color} />
        </mesh>
      ))}
    </group>
  );
}

const FENCE_LENGTH = 36;

function Tree({ x, z, scale, palette }: { x: number; z: number; scale: number; palette: Palette }) {
  return (
    <group position={[x, 0, z]} scale={scale}>
      <mesh position={[0, 0.8, 0]} castShadow>
        <cylinderGeometry args={[0.18, 0.24, 1.6, 8]} />
        <meshStandardMaterial color={palette.trunk} />
      </mesh>
      <mesh position={[0, 2.4, 0]} castShadow>
        <icosahedronGeometry args={[1.3, 0]} />
        <meshStandardMaterial color={palette.tree} flatShading />
      </mesh>
    </group>
  );
}

/** Street lamp: pole, arm and a glowing head with a soft pool of light on the ground. */
function Lamp({ x, z, palette }: { x: number; z: number; palette: Palette }) {
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 2.2, 0]} castShadow>
        <cylinderGeometry args={[0.08, 0.11, 4.4, 8]} />
        <meshStandardMaterial color={palette.fence} />
      </mesh>
      <mesh position={[0, 4.35, 0.5]}>
        <boxGeometry args={[0.12, 0.1, 1.1]} />
        <meshStandardMaterial color={palette.fence} />
      </mesh>
      <mesh position={[0, 4.25, 1]}>
        <boxGeometry args={[0.45, 0.14, 0.6]} />
        <meshBasicMaterial color={palette.lamp} toneMapped={false} />
      </mesh>
      <mesh position={[0, 0.04, 1.4]} rotation-x={-Math.PI / 2}>
        <circleGeometry args={[2.6, 28]} />
        <meshBasicMaterial
          color={palette.lamp}
          transparent
          opacity={0.16}
          depthWrite={false}
          blending={AdditiveBlending}
          toneMapped={false}
        />
      </mesh>
    </group>
  );
}

export function Environment({
  dockCount,
  yardSlots,
  palette,
}: {
  dockCount: number;
  yardSlots: number;
  palette: Palette;
}) {
  const half = yardHalfWidth(dockCount, yardSlots);
  const width = half * 2;
  const bays = useMemo(
    () => Array.from({ length: yardSlots }, (_, i) => bayPoint(i, dockCount)),
    [yardSlots, dockCount],
  );
  const trees = useMemo(() => {
    // Deterministic scatter along the back of the site, plus a row down each side.
    const back = Array.from({ length: 9 }, (_, i) => ({
      x: -half + 3 + (i * (width - 6)) / 8,
      z: -22 - (i % 3) * 2.5,
      scale: 0.8 + (i % 4) * 0.15,
    }));
    const sides = Array.from({ length: 8 }, (_, i) => ({
      x: (i % 2 === 0 ? -1 : 1) * (half + 4 + (i % 3)),
      z: -14 + Math.floor(i / 2) * 7,
      scale: 0.7 + (i % 3) * 0.15,
    }));
    return [...back, ...sides];
  }, [half, width]);
  const lamps = useMemo(
    () =>
      Array.from({ length: Math.floor((half * 2) / 12) + 1 }, (_, i) => -half + 4 + i * 12).filter(
        (x) => x < half - 2,
      ),
    [half],
  );
  const fencePosts = useMemo(
    () =>
      Array.from({ length: Math.floor(FENCE_LENGTH / 3) + 1 }, (_, i) => -FENCE_LENGTH / 2 + i * 3),
    [],
  );
  const markings = useMemo(
    () => Array.from({ length: Math.floor((half * 2 + 20) / 6) }, (_, i) => -half - 10 + i * 6),
    [half],
  );

  return (
    <group>
      {/* Yard + surroundings */}
      <mesh rotation-x={-Math.PI / 2} position={[0, 0, 0]} receiveShadow>
        <planeGeometry args={[width + 40, 90]} />
        <meshStandardMaterial color={palette.ground} />
      </mesh>

      {/* Paved pad in front of the doors, where trucks reverse in and forklifts work */}
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.015, FACADE_Z + 6]} receiveShadow>
        <planeGeometry args={[buildingWidth(dockCount) + 16, 16]} />
        <meshStandardMaterial color={palette.pad} />
      </mesh>

      {/* Road with dashed centre line */}
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.02, ROAD_Z]} receiveShadow>
        <planeGeometry args={[width + 40, ROAD_HALF_WIDTH * 2]} />
        <meshStandardMaterial color={palette.road} />
      </mesh>
      {markings.map((x) => (
        <mesh key={x} rotation-x={-Math.PI / 2} position={[x, 0.035, ROAD_Z]}>
          <planeGeometry args={[3, 0.18]} />
          <meshBasicMaterial color={palette.roadMarking} />
        </mesh>
      ))}

      {/* Waiting bays */}
      {bays.map((bay, i) => (
        <Outline
          key={i}
          x={bay.x}
          z={BAY_Z}
          width={TRUCK_WIDTH + 1.2}
          depth={TRUCK_LENGTH + 1}
          color={palette.yardLine}
        />
      ))}

      {/* Strip in front of the doors where trucks reverse in */}
      <Outline
        x={0}
        z={FACADE_Z + 2}
        width={buildingWidth(dockCount) - 2}
        depth={0.4}
        color={palette.yardLine}
      />

      {/* Fence along the left edge of the yard (trucks never drive there) */}
      {fencePosts.map((z) => (
        <mesh key={z} position={[-half, 0.7, z]} castShadow>
          <boxGeometry args={[0.12, 1.4, 0.12]} />
          <meshStandardMaterial color={palette.fence} />
        </mesh>
      ))}
      {[1.2, 0.6].map((y) => (
        <mesh key={y} position={[-half, y, 0]}>
          <boxGeometry args={[0.06, 0.08, FENCE_LENGTH]} />
          <meshStandardMaterial color={palette.fence} />
        </mesh>
      ))}

      {trees.map((tree, i) => (
        <Tree key={i} {...tree} palette={palette} />
      ))}

      {/* Lamps along the yard edge of the road, lighting the carriageway */}
      {lamps.map((x) => (
        <Lamp key={x} x={x} z={ROAD_Z - ROAD_HALF_WIDTH - 0.8} palette={palette} />
      ))}
    </group>
  );
}

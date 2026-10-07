"use client";

import { Edges } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import type { OrthographicCamera } from "three";
import { palletPosition } from "../geometry";
import type { SitePallet } from "../model";
import { isSame, pointerHandlers, type Interaction } from "./interaction";
import { Label, Pin } from "./label";
import type { Palette } from "./palette";

const AISLE_DEPTH = 3.2;
const COLUMNS = 6;

/** Steel racks the pallets stand in: posts and two beam levels per aisle. */
function Racks({
  count,
  dockCount,
  palette,
}: {
  count: number;
  dockCount: number;
  palette: Palette;
}) {
  if (count === 0) return null;
  const aisles = Math.ceil(count / (COLUMNS * 2));
  const start = palletPosition(0, dockCount);
  const length = COLUMNS * 1.5 + 0.4;
  const centreX = start.x + (COLUMNS - 1) * 0.75;
  return (
    <group>
      {Array.from({ length: aisles }, (_, aisle) => {
        const z = start.z + aisle * AISLE_DEPTH;
        return (
          <group key={aisle} position={[centreX, 0, z]}>
            {[0.12, 1.7].map((y) => (
              <mesh key={y} position={[0, y, 0]} receiveShadow>
                <boxGeometry args={[length, 0.1, 1.3]} />
                <meshStandardMaterial color={palette.rack} />
              </mesh>
            ))}
            {Array.from({ length: COLUMNS + 1 }, (_, i) => (
              <mesh key={i} position={[-length / 2 + i * (length / COLUMNS), 1.5, 0]} castShadow>
                <boxGeometry args={[0.1, 3, 1.3]} />
                <meshStandardMaterial color={palette.rack} />
              </mesh>
            ))}
          </group>
        );
      })}
    </group>
  );
}

function PalletBox({
  pallet,
  dockCount,
  palette,
  interaction,
  showPin,
}: {
  pallet: SitePallet;
  showPin: boolean;
  dockCount: number;
  palette: Palette;
  interaction: Interaction;
}) {
  const target = { kind: "pallet", id: pallet.id } as const;
  const selected = isSame(interaction.selection, target);
  const hovered = isSame(interaction.hovered, target);
  const { x, y, z } = palletPosition(pallet.slot, dockCount);
  // Problem stock is tinted so it stands out even when its pin is grouped.
  const tint = pallet.hasIssue
    ? pallet.stockStatus === "OUT_OF_STOCK"
      ? "#d9694f"
      : "#e8a838"
    : palette.carton;

  return (
    <group position={[x, y, z]}>
      <group {...pointerHandlers(interaction, target)}>
        <mesh castShadow>
          <boxGeometry args={[1.15, 0.14, 1.05]} />
          <meshStandardMaterial color={palette.pallet} />
        </mesh>
        <mesh position={[0, 0.55, 0]} castShadow>
          <boxGeometry args={[1.05, 0.95, 0.95]} />
          <meshStandardMaterial color={tint} />
          {selected && <Edges color={palette.select} linewidth={3} />}
        </mesh>
      </group>
      {pallet.hasIssue && showPin && (
        <Pin
          position={[0, 1.9, 0]}
          color={palette.warning}
          label={`${pallet.id} ${pallet.name}: stock issue`}
          onClick={() => interaction.select(target)}
        />
      )}
      {(hovered || selected) && (
        <Label position={[0, 2.5, 0]} emphasis={selected}>
          {pallet.id} · {pallet.name}
        </Label>
      )}
    </group>
  );
}

/** Zoom level (pixels per metre) at which grouped issue pins split into one pin per pallet. */
const SPLIT_ZOOM = 22;

export function Pallets({
  pallets,
  dockCount,
  palette,
  interaction,
}: {
  pallets: SitePallet[];
  dockCount: number;
  palette: Palette;
  interaction: Interaction;
}) {
  const issues = useMemo(() => pallets.filter((p) => p.hasIssue), [pallets]);
  const [zoomedIn, setZoomedIn] = useState(false);
  const zoomedInRef = useRef(false);

  // Nine pins one metre apart are unreadable from afar: show one counted pin until zoomed in.
  useFrame(({ camera }) => {
    const zoom = (camera as OrthographicCamera).zoom;
    const next = zoomedInRef.current ? zoom > SPLIT_ZOOM - 3 : zoom >= SPLIT_ZOOM;
    if (next !== zoomedInRef.current) {
      zoomedInRef.current = next;
      setZoomedIn(next);
    }
  });

  const centre = useMemo(() => {
    const spots = issues.map((p) => palletPosition(p.slot, dockCount));
    const n = Math.max(spots.length, 1);
    return {
      x: spots.reduce((sum, s) => sum + s.x, 0) / n,
      z: spots.reduce((sum, s) => sum + s.z, 0) / n,
    };
  }, [issues, dockCount]);

  return (
    <group>
      <Racks count={pallets.length} dockCount={dockCount} palette={palette} />
      {pallets.map((pallet) => (
        <PalletBox
          key={pallet.id}
          pallet={pallet}
          showPin={zoomedIn || issues.length === 1}
          dockCount={dockCount}
          palette={palette}
          interaction={interaction}
        />
      ))}
      {!zoomedIn && issues.length > 1 && (
        <Pin
          position={[centre.x, 3.6, centre.z]}
          color={palette.warning}
          text={String(issues.length)}
          label={`${issues.length} pallets with stock issues`}
          onClick={() => interaction.select({ kind: "pallet", id: issues[0].id })}
        />
      )}
    </group>
  );
}

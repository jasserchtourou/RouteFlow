"use client";

import { CameraControls } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  type ElementRef,
  type Ref,
} from "react";
import { ACESFilmicToneMapping, SRGBColorSpace, Vector3, type OrthographicCamera } from "three";
import { prefersReducedMotion } from "@/lib/motion";
import type { ForkliftFleet } from "../fleet";
import { buildingWidth } from "../geometry";
import type { SiteScene } from "../model";
import { truckObstacles } from "../motion";
import { Building } from "./building";
import { Environment } from "./environment";
import { Forklift } from "./forklift";
import type { Interaction } from "./interaction";
import { Pallets } from "./pallets";
import type { Palette } from "./palette";
import { Truck } from "./truck";

/** Imperative camera actions for the on-screen buttons and the operations list. */
export interface CameraApi {
  zoomIn: () => void;
  zoomOut: () => void;
  rotate: (radians: number) => void;
  reset: () => void;
  focus: (x: number, z: number) => void;
}

// Isometric: a fixed elevation (about 35 degrees above the horizon); only the heading rotates.
const POLAR = 0.955;

type Controls = ElementRef<typeof CameraControls>;

/** Pixels covered by overlays on each side of the canvas (the site is framed in what is left). */
export interface Insets {
  left: number;
  right: number;
  top: number;
  bottom: number;
}

/** Pixels of free space kept around the site when framing it. */
const FIT_MARGIN_PX = 28;

/**
 * Camera rig. It frames the whole site (building, yard, road, racks and depot) in the part of
 * the canvas that is not covered by side panels, whenever the canvas or the panels change size,
 * until the user moves the camera themselves; "reset" frames it again.
 *
 * (camera-controls' own `fitToBox` is not used: it re-orients the camera, which breaks the
 * fixed isometric angle.)
 */
function Rig({
  apiRef,
  halfWidth,
  insets,
}: {
  apiRef: Ref<CameraApi>;
  halfWidth: number;
  insets: Insets;
}) {
  const controls = useRef<Controls>(null);
  const userMoved = useRef(false);
  const introStarted = useRef(false);
  const introPlaying = useRef(false);
  const size = useThree((state) => state.size);

  /** Frames the site; returns the zoom it chose (null before the controls exist). */
  const fit = useCallback(
    (animate: boolean): number | null => {
      const c = controls.current;
      if (!c) return null;
      const camera = c.camera as OrthographicCamera;
      const minZ = -17;
      const maxZ = 26;
      // Extent of the site as seen from the camera (view-space x/y), independent of zoom.
      camera.updateMatrixWorld();
      const toView = camera.matrixWorld.clone().invert();
      let minX = Infinity;
      let maxX = -Infinity;
      let minY = Infinity;
      let maxY = -Infinity;
      for (const x of [-halfWidth, halfWidth]) {
        for (const y of [0, 7]) {
          for (const z of [minZ, maxZ]) {
            const p = new Vector3(x, y, z).applyMatrix4(toView);
            minX = Math.min(minX, p.x);
            maxX = Math.max(maxX, p.x);
            minY = Math.min(minY, p.y);
            maxY = Math.max(maxY, p.y);
          }
        }
      }
      const freeWidth = Math.max(200, size.width - insets.left - insets.right);
      const freeHeight = Math.max(200, size.height - insets.top - insets.bottom);
      const zoom = Math.min(
        (freeWidth - 2 * FIT_MARGIN_PX) / (maxX - minX),
        (freeHeight - 2 * FIT_MARGIN_PX) / (maxY - minY),
      );
      const clamped = Math.min(45, Math.max(4, zoom));
      void c.moveTo(0, 0, (minZ + maxZ) / 2, false);
      void c.zoomTo(clamped, animate);
      // Centre the site in the free part of the canvas, not behind the panels.
      const shiftX = (insets.left - insets.right) / 2;
      const shiftY = (insets.top - insets.bottom) / 2;
      const scale = Math.max(zoom, 1);
      if (shiftX !== 0 || shiftY !== 0) void c.truck(-shiftX / scale, shiftY / scale, false);
      return clamped;
    },
    [halfWidth, insets.left, insets.right, insets.top, insets.bottom, size.width, size.height],
  );

  // First frame: look from the south-east, then frame the site.
  useEffect(() => {
    const c = controls.current;
    if (!c) return;
    c.setLookAt(36, 34, 42, 0, 0, 6, false);
    const zoom = fit(false);
    if (!introStarted.current && zoom !== null && !prefersReducedMotion()) {
      // Once per visit: start wide and turned a little, then glide into the framed view.
      introStarted.current = true;
      introPlaying.current = true;
      c.smoothTime = 0.9;
      void c.zoomTo(zoom * 0.45, false);
      void c.rotate(-0.45, 0, false);
      void c.zoomTo(zoom, true);
      void c.rotate(0.45, 0, true).then(() => {
        introPlaying.current = false;
        if (controls.current) controls.current.smoothTime = 0.25;
      });
    }
    const stop = () => {
      userMoved.current = true;
    };
    c.addEventListener("controlstart", stop);
    return () => c.removeEventListener("controlstart", stop);
  }, [fit]);

  // Keep the site framed while the window or the panel layout changes size.
  useEffect(() => {
    if (!userMoved.current && !introPlaying.current) fit(false);
  }, [fit]);

  useImperativeHandle(apiRef, () => {
    const animate = !prefersReducedMotion();
    return {
      zoomIn: () => void controls.current?.zoom(controls.current.camera.zoom * 0.25, animate),
      zoomOut: () => void controls.current?.zoom(-controls.current.camera.zoom * 0.2, animate),
      rotate: (radians) => void controls.current?.rotate(radians, 0, animate),
      reset: () => {
        userMoved.current = false;
        fit(animate);
      },
      focus: (x, z) => void controls.current?.moveTo(x, 0, z, animate),
    };
  }, [fit]);

  return (
    <CameraControls
      ref={controls}
      makeDefault
      minPolarAngle={POLAR}
      maxPolarAngle={POLAR}
      minZoom={4}
      maxZoom={45}
      // camera-controls ACTION values: left drag pans (TRUCK), right drag rotates, wheel zooms.
      mouseButtons={{ left: 2, middle: 0, right: 1, wheel: 32 }}
      touches={{ one: 128, two: 65536, three: 0 }}
    />
  );
}

/** Steps the forklift simulation every frame, before the forklifts read their positions. */
function FleetDriver({
  fleet,
  scene,
  getNow,
}: {
  fleet: ForkliftFleet;
  scene: SiteScene;
  getNow: () => number;
}) {
  // Matching the simulation to a new scene is cheap and idempotent; doing it while rendering
  // means units exist before the first frame is drawn.
  useMemo(
    () => fleet.sync(scene.equipment, scene.docks, scene.dockCount),
    [fleet, scene.equipment, scene.docks, scene.dockCount],
  );
  useFrame((_, delta) => {
    if (prefersReducedMotion()) return;
    const obstacles = truckObstacles(
      scene.visits,
      scene.docks,
      scene.dockCount,
      scene.timings,
      getNow(),
    );
    // Clamp: after a hidden tab the first delta can be huge and would teleport units.
    fleet.step(Math.min(delta, 0.1), obstacles);
  }, -1);
  return null;
}

export default function SiteCanvas({
  scene,
  fleet,
  getNow,
  palette,
  interaction,
  apiRef,
  insets,
}: {
  scene: SiteScene;
  fleet: ForkliftFleet;
  getNow: () => number;
  palette: Palette;
  interaction: Interaction;
  apiRef: Ref<CameraApi>;
  /** Width in pixels of the panels covering the left and right of the canvas. */
  insets: Insets;
}) {
  const dockByCode = new Map(scene.docks.map((d) => [d.code, d]));

  return (
    <Canvas
      orthographic
      shadows="soft"
      dpr={[1, 2]}
      camera={{ position: [36, 34, 42], zoom: 15, near: -200, far: 400 }}
      gl={{ antialias: true, toneMapping: ACESFilmicToneMapping, outputColorSpace: SRGBColorSpace }}
      onPointerMissed={() => interaction.select(null)}
      aria-label="3D view of the warehouse site. The operations list next to it has the same information."
    >
      <color attach="background" args={[palette.background]} />
      <ambientLight intensity={palette.ambient} />
      <hemisphereLight args={[palette.sky, palette.ground, palette.hemi]} />
      <directionalLight
        shadow-bias={-0.0004}
        position={[30, 50, 25]}
        intensity={palette.sun}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-60}
        shadow-camera-right={60}
        shadow-camera-top={60}
        shadow-camera-bottom={-60}
        shadow-camera-near={1}
        shadow-camera-far={150}
      />

      <Rig apiRef={apiRef} halfWidth={buildingWidth(scene.dockCount) / 2 + 15} insets={insets} />
      <FleetDriver fleet={fleet} scene={scene} getNow={getNow} />
      <Environment dockCount={scene.dockCount} yardSlots={scene.yardSlots} palette={palette} />
      <Building
        code={scene.warehouse.code}
        docks={scene.docks}
        dockCount={scene.dockCount}
        palette={palette}
        interaction={interaction}
      />
      <Pallets
        pallets={scene.pallets}
        dockCount={scene.dockCount}
        palette={palette}
        interaction={interaction}
      />
      {scene.visits.map((visit) => {
        const dock = dockByCode.get(visit.dockCode);
        return dock ? (
          <Truck
            key={visit.id}
            visit={visit}
            dock={dock}
            dockCount={scene.dockCount}
            timings={scene.timings}
            getNow={getNow}
            palette={palette}
            interaction={interaction}
          />
        ) : null;
      })}
      {scene.equipment.map((unit) => (
        <Forklift
          key={unit.id}
          unit={unit}
          fleet={fleet}
          dockCount={scene.dockCount}
          palette={palette}
          interaction={interaction}
        />
      ))}
    </Canvas>
  );
}

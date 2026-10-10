"use client";

import { CameraControls, RoundedBox } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useCallback, useEffect, useMemo, useRef, type ElementRef } from "react";
import {
  ACESFilmicToneMapping,
  MathUtils,
  SRGBColorSpace,
  Vector3,
  type Group,
  type Mesh,
  type MeshBasicMaterial,
  type MeshStandardMaterial,
  type OrthographicCamera,
} from "three";
import { Label } from "@/features/site3d/scene/label";
import { NIGHT } from "@/features/site3d/scene/palette";
import { prefersReducedMotion } from "@/lib/motion";
import {
  STATUS_COLOR,
  utilizationColor,
  type BoardRoad,
  type BoardSite,
  type BoardVehicle,
  type NetworkLayout,
} from "./layout";

const palette = NIGHT;
// Same isometric elevation as the site view; only the heading rotates.
const POLAR = 0.955;
const FIT_MARGIN_PX = 24;

const VEHICLE_COLOR: Record<BoardVehicle["status"], string> = {
  IN_TRANSIT: "#4f8cff",
  AVAILABLE: "#34d399",
  MAINTENANCE: "#fbbf24",
  OFFLINE: "#64708f",
};

type Controls = ElementRef<typeof CameraControls>;

export interface NetworkHover {
  hovered: string | null;
  onHover: (id: string | null) => void;
  onOpen: (siteId: string) => void;
}

function pointer(on: boolean) {
  document.body.style.cursor = on ? "pointer" : "";
}

/** Frames the whole board; flies in once on first load (unless motion is reduced). */
function Rig({ halfWidth, halfDepth }: { halfWidth: number; halfDepth: number }) {
  const controls = useRef<Controls>(null);
  const userMoved = useRef(false);
  const introDone = useRef(false);
  const size = useThree((state) => state.size);

  const fitZoom = useCallback(() => {
    const c = controls.current;
    if (!c) return null;
    const camera = c.camera as OrthographicCamera;
    camera.updateMatrixWorld();
    const toView = camera.matrixWorld.clone().invert();
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (const x of [-halfWidth, halfWidth]) {
      for (const y of [-1, 5]) {
        for (const z of [-halfDepth, halfDepth]) {
          const p = new Vector3(x, y, z).applyMatrix4(toView);
          minX = Math.min(minX, p.x);
          maxX = Math.max(maxX, p.x);
          minY = Math.min(minY, p.y);
          maxY = Math.max(maxY, p.y);
        }
      }
    }
    return Math.max(
      2,
      Math.min(
        (size.width - 2 * FIT_MARGIN_PX) / (maxX - minX),
        (size.height - 2 * FIT_MARGIN_PX) / (maxY - minY),
      ),
    );
  }, [halfWidth, halfDepth, size.width, size.height]);

  useEffect(() => {
    const c = controls.current;
    if (!c) return;
    const stop = () => {
      userMoved.current = true;
    };
    c.addEventListener("controlstart", stop);
    if (!introDone.current) {
      introDone.current = true;
      c.setLookAt(34, 40, 40, 0, 0, 0, false);
      const zoom = fitZoom();
      if (zoom !== null) {
        if (prefersReducedMotion()) {
          void c.zoomTo(zoom, false);
        } else {
          // Start further out and turned a little, then settle: a short "fly-in".
          c.smoothTime = 0.9;
          void c.zoomTo(zoom * 0.45, false);
          void c.rotate(-0.5, 0, false);
          void c.zoomTo(zoom, true);
          void c.rotate(0.5, 0, true).then(() => {
            if (controls.current) controls.current.smoothTime = 0.25;
          });
        }
      }
    }
    return () => c.removeEventListener("controlstart", stop);
  }, [fitZoom]);

  // Re-frame when the card changes size, until the user takes over the camera.
  useEffect(() => {
    const c = controls.current;
    const zoom = fitZoom();
    if (c && zoom !== null && !userMoved.current) void c.zoomTo(zoom, false);
  }, [fitZoom]);

  return (
    <CameraControls
      ref={controls}
      makeDefault
      minPolarAngle={POLAR}
      maxPolarAngle={POLAR}
      minZoom={2}
      maxZoom={60}
      mouseButtons={{ left: 2, middle: 0, right: 1, wheel: 32 }}
      touches={{ one: 128, two: 65536, three: 0 }}
    />
  );
}

function Board({ halfWidth, halfDepth }: { halfWidth: number; halfDepth: number }) {
  const width = halfWidth * 2;
  const depth = halfDepth * 2;
  const lines = useMemo(() => {
    const step = 4;
    const xs = Array.from(
      { length: Math.floor(width / step) - 1 },
      (_, i) => -halfWidth + (i + 1) * step,
    );
    const zs = Array.from(
      { length: Math.floor(depth / step) - 1 },
      (_, i) => -halfDepth + (i + 1) * step,
    );
    return { xs, zs };
  }, [width, depth, halfWidth, halfDepth]);

  return (
    <group>
      {/* The board itself: a thick tile with rounded edges */}
      <RoundedBox
        args={[width, 1.6, depth]}
        radius={0.7}
        smoothness={3}
        position={[0, -0.8, 0]}
        receiveShadow
      >
        <meshStandardMaterial color={palette.ground} roughness={0.95} />
      </RoundedBox>
      {/* Faint survey grid */}
      {lines.xs.map((x) => (
        <mesh key={`x${x}`} position={[x, 0.005, 0]} rotation-x={-Math.PI / 2}>
          <planeGeometry args={[0.05, depth - 1.4]} />
          <meshBasicMaterial color={palette.pad} transparent opacity={0.55} />
        </mesh>
      ))}
      {lines.zs.map((z) => (
        <mesh key={`z${z}`} position={[0, 0.005, z]} rotation-x={-Math.PI / 2}>
          <planeGeometry args={[width - 1.4, 0.05]} />
          <meshBasicMaterial color={palette.pad} transparent opacity={0.55} />
        </mesh>
      ))}
    </group>
  );
}

function Road({ road }: { road: BoardRoad }) {
  const dx = road.to.x - road.from.x;
  const dz = road.to.z - road.from.z;
  const length = Math.hypot(dx, dz);
  const angle = Math.atan2(dz, dx);
  const dashes = Math.max(0, Math.floor(length / 2.2) - 2);
  return (
    <group
      position={[(road.from.x + road.to.x) / 2, 0.02, (road.from.z + road.to.z) / 2]}
      rotation-y={-angle}
    >
      <mesh rotation-x={-Math.PI / 2} receiveShadow>
        <planeGeometry args={[length, 1.3]} />
        <meshStandardMaterial color={palette.road} />
      </mesh>
      {Array.from({ length: dashes }, (_, i) => (
        <mesh key={i} position={[-length / 2 + 2.2 * (i + 1.5), 0.01, 0]} rotation-x={-Math.PI / 2}>
          <planeGeometry args={[0.9, 0.08]} />
          <meshBasicMaterial color={palette.roadMarking} />
        </mesh>
      ))}
    </group>
  );
}

/** Pulsing light on a pole plus a ring spreading on the ground when the site needs attention. */
function Beacon({ color, alarm, height }: { color: string; alarm: boolean; height: number }) {
  const bulb = useRef<Mesh>(null);
  const ring = useRef<Mesh>(null);
  useFrame(({ clock }) => {
    if (prefersReducedMotion()) return;
    const t = clock.elapsedTime;
    const speed = alarm ? 5 : 1.6;
    if (bulb.current) {
      const m = bulb.current.material as MeshStandardMaterial;
      m.emissiveIntensity = 0.6 + 0.9 * (0.5 + 0.5 * Math.sin(t * speed));
    }
    if (ring.current) {
      const phase = (t * 0.6) % 1;
      ring.current.scale.setScalar(1 + phase * 2.4);
      (ring.current.material as MeshBasicMaterial).opacity = 0.45 * (1 - phase);
    }
  });
  return (
    <group>
      <mesh position={[0, height / 2, 0]}>
        <cylinderGeometry args={[0.05, 0.05, height, 6]} />
        <meshStandardMaterial color={palette.forkliftDark} />
      </mesh>
      <mesh ref={bulb} position={[0, height + 0.18, 0]}>
        <sphereGeometry args={[0.22, 14, 10]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={1}
          toneMapped={false}
        />
      </mesh>
      {alarm && (
        <mesh ref={ring} position={[0, 0.04, 0]} rotation-x={-Math.PI / 2}>
          <ringGeometry args={[1.6, 1.85, 40]} />
          <meshBasicMaterial color={color} transparent opacity={0.4} depthWrite={false} />
        </mesh>
      )}
    </group>
  );
}

/** Fill-level silo next to the building: how full the site is, readable at a glance. */
function Silo({ pct, x, z }: { pct: number; x: number; z: number }) {
  const height = 2.6;
  const fill = Math.max(0.04, Math.min(1, pct / 100)) * height;
  const color = utilizationColor(pct);
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, height / 2, 0]}>
        <cylinderGeometry args={[0.62, 0.62, height, 20, 1, true]} />
        <meshStandardMaterial color="#9fb4e6" transparent opacity={0.18} depthWrite={false} />
      </mesh>
      <mesh position={[0, fill / 2, 0]} castShadow>
        <cylinderGeometry args={[0.52, 0.52, fill, 20]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.35} />
      </mesh>
      <mesh position={[0, height + 0.05, 0]}>
        <cylinderGeometry args={[0.68, 0.68, 0.1, 20]} />
        <meshStandardMaterial color={palette.forkliftDark} />
      </mesh>
    </group>
  );
}

function Site({ site, hover }: { site: BoardSite; hover: NetworkHover }) {
  const s = site.size;
  const depth = s * 0.72;
  const height = 1.6 + s * 0.12;
  const hovered = hover.hovered === site.id;
  const status = STATUS_COLOR[site.status];
  const alarm = site.status === "DISRUPTED" || site.status === "CONGESTED";
  const lift = useRef<Group>(null);

  // Hovered sites rise slightly, like a selected unit in a strategy game.
  useFrame((_, delta) => {
    if (!lift.current) return;
    const goal = hovered ? 0.35 : 0;
    lift.current.position.y = prefersReducedMotion()
      ? goal
      : MathUtils.damp(lift.current.position.y, goal, 10, delta);
  });

  const handlers = {
    onClick: (event: { stopPropagation: () => void }) => {
      event.stopPropagation();
      hover.onOpen(site.id);
    },
    onPointerOver: (event: { stopPropagation: () => void }) => {
      event.stopPropagation();
      hover.onHover(site.id);
      pointer(true);
    },
    onPointerOut: () => {
      hover.onHover(null);
      pointer(false);
    },
  };

  const doors = Math.max(2, Math.round(s / 1.4));
  return (
    <group position={[site.x, 0, site.z]}>
      {/* Paved lot */}
      <RoundedBox
        args={[s + 3.4, 0.12, depth + 4]}
        radius={0.05}
        smoothness={2}
        position={[0.4, 0.06, 0.7]}
        receiveShadow
      >
        <meshStandardMaterial color={palette.pad} />
      </RoundedBox>
      {hovered && (
        <mesh position={[0.4, 0.13, 0.7]} rotation-x={-Math.PI / 2}>
          <planeGeometry args={[s + 3.8, depth + 4.4]} />
          <meshBasicMaterial color={palette.select} transparent opacity={0.22} depthWrite={false} />
        </mesh>
      )}

      <group ref={lift} {...handlers}>
        {/* Hall */}
        <mesh position={[0, height / 2 + 0.12, 0]} castShadow receiveShadow>
          <boxGeometry args={[s, height, depth]} />
          <meshStandardMaterial color={palette.building} roughness={0.7} />
        </mesh>
        {/* Status band under the roof edge */}
        <mesh position={[0, height - 0.05, depth / 2 + 0.01]}>
          <planeGeometry args={[s, 0.16]} />
          <meshBasicMaterial color={status} toneMapped={false} />
        </mesh>
        <mesh position={[0, height + 0.2, 0]} castShadow>
          <boxGeometry args={[s + 0.3, 0.18, depth + 0.3]} />
          <meshStandardMaterial color={palette.roof} />
        </mesh>
        {/* Roof units */}
        {[-0.28, 0.12].map((f) => (
          <mesh key={f} position={[s * f, height + 0.45, -depth * 0.15]} castShadow>
            <boxGeometry args={[0.7, 0.35, 0.55]} />
            <meshStandardMaterial color="#8d9ab8" />
          </mesh>
        ))}
        <mesh position={[s * 0.3, height + 0.31, depth * 0.12]}>
          <boxGeometry args={[s * 0.25, 0.04, depth * 0.45]} />
          <meshStandardMaterial color="#9fc2ff" emissive="#4f8cff" emissiveIntensity={0.25} />
        </mesh>
        {/* Dock doors on the front */}
        {Array.from({ length: doors }, (_, i) => (
          <mesh key={i} position={[-s / 2 + (s / doors) * (i + 0.5), 0.62, depth / 2 + 0.01]}>
            <planeGeometry args={[(s / doors) * 0.6, 0.9]} />
            <meshStandardMaterial color={palette.forkliftDark} />
          </mesh>
        ))}
      </group>

      <Silo pct={site.utilizationPct} x={s / 2 + 1.1} z={-depth / 4} />
      <group position={[-s / 2 - 0.9, 0, -depth / 2]}>
        <Beacon color={status} alarm={alarm} height={height + 1.4} />
      </group>

      {/* Short tags keep neighbouring sites readable; hovering shows the full name and stock. */}
      <Label position={[0, height + 1.9, 0]} emphasis={hovered}>
        {hovered
          ? `${site.name} · ${site.utilizationPct}%${
              site.lowStockCount > 0 ? ` · ${site.lowStockCount} low stock` : ""
            }`
          : `${site.code.replace(/^WH-/, "")} ${site.utilizationPct}%`}
      </Label>
    </group>
  );
}

/** A small truck that glides to its latest reported position and faces where it is going. */
function Vehicle({ vehicle, hover }: { vehicle: BoardVehicle; hover: NetworkHover }) {
  const group = useRef<Group>(null);
  const placed = useRef(false);
  const color = VEHICLE_COLOR[vehicle.status];
  const hovered = hover.hovered === vehicle.id;
  const moving = vehicle.status === "IN_TRANSIT";

  useFrame((_, delta) => {
    const node = group.current;
    if (!node) return;
    if (!placed.current || prefersReducedMotion()) {
      node.position.set(vehicle.x, 0, vehicle.z);
      placed.current = true;
      return;
    }
    const dx = vehicle.x - node.position.x;
    const dz = vehicle.z - node.position.z;
    if (Math.hypot(dx, dz) > 0.02) {
      const heading = Math.atan2(-dz, dx);
      const turn =
        MathUtils.euclideanModulo(heading - node.rotation.y + Math.PI, Math.PI * 2) - Math.PI;
      node.rotation.y += turn * Math.min(1, delta * 4);
    }
    // Positions arrive every few seconds: ease towards the newest one.
    node.position.x = MathUtils.damp(node.position.x, vehicle.x, 0.8, delta);
    node.position.z = MathUtils.damp(node.position.z, vehicle.z, 0.8, delta);
  });

  return (
    <group
      ref={group}
      scale={0.42}
      onPointerOver={(event) => {
        event.stopPropagation();
        hover.onHover(vehicle.id);
        pointer(true);
      }}
      onPointerOut={() => {
        hover.onHover(null);
        pointer(false);
      }}
    >
      <mesh position={[-0.6, 1.3, 0]} castShadow>
        <boxGeometry args={[3.2, 1.6, 1.5]} />
        <meshStandardMaterial color={palette.trailer} />
      </mesh>
      <mesh position={[1.55, 1.05, 0]} castShadow>
        <boxGeometry args={[1.1, 1.3, 1.5]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={moving ? 0.25 : 0.05}
        />
      </mesh>
      <mesh position={[2.12, 1.25, 0]}>
        <boxGeometry args={[0.04, 0.5, 1.2]} />
        <meshStandardMaterial color="#0a0e1a" />
      </mesh>
      <mesh position={[0.2, 0.32, 0]}>
        <boxGeometry args={[4.6, 0.3, 1.3]} />
        <meshStandardMaterial color={palette.wheel} />
      </mesh>
      {moving && (
        <mesh position={[2.15, 0.6, 0]}>
          <boxGeometry args={[0.05, 0.18, 1.2]} />
          <meshBasicMaterial color="#fff6c8" toneMapped={false} />
        </mesh>
      )}
      {hovered && (
        <Label position={[0, 3.4, 0]} emphasis>
          {`${vehicle.registration} · ${vehicle.status === "IN_TRANSIT" ? "in transit" : vehicle.status.toLowerCase()}`}
        </Label>
      )}
    </group>
  );
}

/** Deterministic low-poly trees on the empty parts of the board. */
function Trees({ layout }: { layout: NetworkLayout }) {
  const trees = useMemo(() => {
    let seed = 7;
    const random = () => {
      seed = (seed * 16807) % 2147483647;
      return seed / 2147483647;
    };
    const out: { x: number; z: number; scale: number }[] = [];
    const clearOf = (x: number, z: number) =>
      layout.sites.every((s) => Math.hypot(s.x - x, s.z - z) > s.size + 3.5) &&
      layout.roads.every((r) => {
        // Distance from the point to the road segment.
        const vx = r.to.x - r.from.x;
        const vz = r.to.z - r.from.z;
        const t = Math.max(
          0,
          Math.min(1, ((x - r.from.x) * vx + (z - r.from.z) * vz) / (vx * vx + vz * vz || 1)),
        );
        return Math.hypot(r.from.x + vx * t - x, r.from.z + vz * t - z) > 1.6;
      });
    for (let i = 0; i < 400 && out.length < 46; i++) {
      const x = (random() * 2 - 1) * (layout.halfWidth - 1.5);
      const z = (random() * 2 - 1) * (layout.halfDepth - 1.5);
      if (clearOf(x, z)) out.push({ x, z, scale: 0.45 + random() * 0.4 });
    }
    return out;
  }, [layout]);

  return (
    <group>
      {trees.map((tree, i) => (
        <group key={i} position={[tree.x, 0, tree.z]} scale={tree.scale}>
          <mesh position={[0, 0.7, 0]} castShadow>
            <cylinderGeometry args={[0.15, 0.2, 1.4, 6]} />
            <meshStandardMaterial color={palette.trunk} />
          </mesh>
          <mesh position={[0, 2, 0]} castShadow>
            <icosahedronGeometry args={[1.05, 0]} />
            <meshStandardMaterial color={palette.tree} flatShading />
          </mesh>
        </group>
      ))}
    </group>
  );
}

export default function NetworkCanvas({
  layout,
  hover,
}: {
  layout: NetworkLayout;
  hover: NetworkHover;
}) {
  return (
    <Canvas
      orthographic
      shadows
      dpr={[1, 2]}
      camera={{ position: [34, 40, 40], zoom: 8, near: -200, far: 400 }}
      gl={{ antialias: true, toneMapping: ACESFilmicToneMapping, outputColorSpace: SRGBColorSpace }}
      aria-label="3D overview of all warehouse sites. The list next to it has the same information."
    >
      <color attach="background" args={[palette.background]} />
      <hemisphereLight args={["#b9ccff", "#0a0f1f", 0.55]} />
      <ambientLight intensity={0.35} />
      <directionalLight
        position={[25, 45, 20]}
        intensity={1.25}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-50}
        shadow-camera-right={50}
        shadow-camera-top={50}
        shadow-camera-bottom={-50}
        shadow-camera-near={1}
        shadow-camera-far={150}
        shadow-bias={-0.0005}
      />
      <Rig halfWidth={layout.halfWidth} halfDepth={layout.halfDepth} />
      <Board halfWidth={layout.halfWidth} halfDepth={layout.halfDepth} />
      {layout.roads.map((road) => (
        <Road key={road.id} road={road} />
      ))}
      <Trees layout={layout} />
      {layout.sites.map((site) => (
        <Site key={site.id} site={site} hover={hover} />
      ))}
      {layout.vehicles.map((vehicle) => (
        <Vehicle key={vehicle.id} vehicle={vehicle} hover={hover} />
      ))}
    </Canvas>
  );
}

"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo, useRef } from "react";
import { MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import { prefersReducedMotion } from "@/lib/motion";
import { humanize } from "./mappers";
import type { MapVehicle, MapWarehouse } from "./types";

// OpenStreetMap's public tiles need no API key (CARTO's free dark tiles now do). They are light,
// so `.map-tiles-dark` (globals.css) darkens them to fit the app. Public OSM tiles are meant for
// light use: put a tile provider with a key or your own tile server behind this for production.
const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
// Centre of the seed geography (Hannover to Berlin/Leipzig/Hamburg/Kassel) until bounds are fitted.
const DEFAULT_CENTER: [number, number] = [52.2, 10.5];

const VEHICLE_COLOR: Record<MapVehicle["status"], string> = {
  IN_TRANSIT: "bg-accent",
  AVAILABLE: "bg-success",
  MAINTENANCE: "bg-warning",
  OFFLINE: "bg-muted",
};

const WAREHOUSE_COLOR: Record<MapWarehouse["status"], string> = {
  OPERATIONAL: "bg-surface border-accent",
  CONGESTED: "bg-surface border-warning",
  DISRUPTED: "bg-surface border-danger",
  OFFLINE: "bg-surface border-muted",
};

function vehicleIcon(vehicle: MapVehicle, selected: boolean): L.DivIcon {
  const pulse = vehicle.status === "IN_TRANSIT" ? "animate-ping" : "hidden";
  const ring = selected ? "ring-4 ring-white/80" : vehicle.lowFuel ? "ring-2 ring-danger" : "";
  return L.divIcon({
    className: "",
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    html: `<span class="relative flex size-[22px] items-center justify-center">
      <span class="${pulse} absolute inline-flex size-full rounded-full ${VEHICLE_COLOR[vehicle.status]} opacity-50"></span>
      <span class="relative inline-flex size-3.5 rounded-full border-2 border-background ${VEHICLE_COLOR[vehicle.status]} ${ring}"></span>
    </span>`,
  });
}

function warehouseIcon(warehouse: MapWarehouse): L.DivIcon {
  return L.divIcon({
    className: "",
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    html: `<span class="flex size-[26px] items-center justify-center rounded-md border-2 ${WAREHOUSE_COLOR[warehouse.status]} text-[10px] font-bold text-foreground shadow">WH</span>`,
  });
}

/** Leaflet measures its container once; tell it whenever the container changes size. */
function InvalidateOnResize() {
  const map = useMap();
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  return null;
}

/** Fits the view to every marker once, then leaves the camera to the user. */
function FitToMarkers({ points }: { points: [number, number][] }) {
  const map = useMap();
  const fitted = useRef(false);
  useEffect(() => {
    if (fitted.current || points.length === 0) return;
    fitted.current = true;
    map.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 9 });
  }, [map, points]);
  return null;
}

/** Moves the camera to the vehicle selected in the side list or by clicking its marker. */
function FlyToSelected({ vehicle }: { vehicle: MapVehicle | undefined }) {
  const map = useMap();
  const lat = vehicle?.lat;
  const lng = vehicle?.lng;
  useEffect(() => {
    if (lat === undefined || lng === undefined) return;
    const zoom = Math.max(map.getZoom(), 9);
    if (prefersReducedMotion()) map.setView([lat, lng], zoom, { animate: false });
    else map.flyTo([lat, lng], zoom, { duration: 0.9 });
  }, [map, lat, lng]);
  return null;
}

interface FleetMapProps {
  vehicles: MapVehicle[];
  warehouses: MapWarehouse[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function FleetMap({ vehicles, warehouses, selectedId, onSelect }: FleetMapProps) {
  const points = useMemo<[number, number][]>(
    () => [...vehicles, ...warehouses].map((p) => [p.lat, p.lng]),
    [vehicles, warehouses],
  );
  const selected = vehicles.find((v) => v.id === selectedId);

  return (
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={7}
      scrollWheelZoom
      className="size-full rounded-xl"
      aria-label="Fleet map. The vehicle list next to it has the same information."
    >
      <TileLayer url={TILES} attribution={ATTRIBUTION} maxZoom={19} className="map-tiles-dark" />
      <InvalidateOnResize />
      <FitToMarkers points={points} />
      <FlyToSelected vehicle={selected} />

      {warehouses.map((w) => (
        <Marker key={w.id} position={[w.lat, w.lng]} icon={warehouseIcon(w)} zIndexOffset={-100}>
          <Tooltip direction="top" offset={[0, -12]}>
            <strong>{w.name}</strong>
            <br />
            {w.utilizationPct}% full{w.status === "OPERATIONAL" ? "" : ` · ${humanize(w.status)}`}
          </Tooltip>
        </Marker>
      ))}

      {vehicles.map((v) => (
        <Marker
          key={v.id}
          position={[v.lat, v.lng]}
          icon={vehicleIcon(v, v.id === selectedId)}
          zIndexOffset={v.id === selectedId ? 1000 : 0}
          eventHandlers={{ click: () => onSelect(v.id) }}
        >
          <Tooltip direction="top" offset={[0, -10]}>
            <strong>{v.registration}</strong>
            <br />
            {humanize(v.status)} · {Math.round(v.fuelLevel)}% fuel
          </Tooltip>
        </Marker>
      ))}
    </MapContainer>
  );
}

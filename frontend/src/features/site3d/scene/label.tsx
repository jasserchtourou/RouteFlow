"use client";

import { useFrame } from "@react-three/fiber";
import { Children, useMemo, useRef, type ReactNode } from "react";
import { CanvasTexture, SRGBColorSpace, type OrthographicCamera, type Sprite } from "three";

/**
 * Labels and pins are sprites textured from a 2D canvas, not DOM elements: drei's <Html> mounts a
 * separate React root per label, and unmounting those roots inside a React commit makes React 19
 * log errors. Sprites also keep a constant size on screen when the camera zooms.
 */

interface Face {
  texture: CanvasTexture;
  /** Size in CSS pixels. */
  width: number;
  height: number;
}

const cache = new Map<string, Face>();
const FONT = '600 13px system-ui, "Segoe UI", Roboto, sans-serif';
const RATIO = 2; // texture pixels per CSS pixel (sharp on high-DPI screens)

function draw(
  key: string,
  width: number,
  height: number,
  paint: (g: CanvasRenderingContext2D) => void,
): Face {
  const hit = cache.get(key);
  if (hit) return hit;
  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil(width * RATIO);
  canvas.height = Math.ceil(height * RATIO);
  const g = canvas.getContext("2d");
  if (g) {
    g.scale(RATIO, RATIO);
    paint(g);
  }
  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  const face = { texture, width, height };
  cache.set(key, face);
  return face;
}

function labelFace(text: string, emphasis: boolean): Face {
  const measure = document.createElement("canvas").getContext("2d");
  if (measure) measure.font = FONT;
  const textWidth = measure ? measure.measureText(text).width : text.length * 7;
  const width = Math.ceil(textWidth) + 22;
  const height = 26;
  return draw(`label|${emphasis}|${text}`, width, height, (g) => {
    g.shadowColor = "rgba(0,0,0,0.35)";
    g.shadowBlur = 6;
    g.shadowOffsetY = 2;
    g.fillStyle = emphasis ? "#4f8cff" : "rgba(18,26,46,0.96)";
    g.beginPath();
    g.roundRect(3, 2, width - 6, height - 6, 10);
    g.fill();
    g.shadowColor = "transparent";
    g.font = FONT;
    g.textBaseline = "middle";
    g.textAlign = "center";
    g.fillStyle = emphasis ? "#06122b" : "#e8ecf6";
    g.fillText(text, width / 2, height / 2 - 2);
  });
}

function pinFace(color: string, text: string): Face {
  const size = text.length > 1 ? 34 : 30;
  return draw(`pin|${color}|${text}`, size, size + 8, (g) => {
    g.shadowColor = "rgba(0,0,0,0.4)";
    g.shadowBlur = 5;
    g.shadowOffsetY = 2;
    g.fillStyle = color;
    g.strokeStyle = "#ffffff";
    g.lineWidth = 2.5;
    g.beginPath();
    g.arc(size / 2, size / 2, size / 2 - 4, 0, Math.PI * 2);
    g.fill();
    g.shadowColor = "transparent";
    g.stroke();
    g.fillStyle = "#101010";
    g.font = '800 15px system-ui, "Segoe UI", sans-serif';
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillText(text, size / 2, size / 2 + 1);
  });
}

/** A sprite that always measures `face.width x face.height` CSS pixels, whatever the zoom. */
function ScreenSprite({
  face,
  position,
  anchor = [0.5, 0.5],
  onClick,
  onPointerOver,
  onPointerOut,
  renderOrder = 10,
}: {
  face: Face;
  position: [number, number, number];
  anchor?: [number, number];
  onClick?: () => void;
  onPointerOver?: () => void;
  onPointerOut?: () => void;
  renderOrder?: number;
}) {
  const sprite = useRef<Sprite>(null);
  useFrame(({ camera }) => {
    const zoom = (camera as OrthographicCamera).zoom || 1;
    sprite.current?.scale.set(face.width / zoom, face.height / zoom, 1);
  });
  return (
    <sprite
      ref={sprite}
      position={position}
      center={anchor}
      renderOrder={renderOrder}
      onClick={
        onClick &&
        ((event) => {
          event.stopPropagation();
          onClick();
        })
      }
      onPointerOver={
        onPointerOver &&
        ((event) => {
          event.stopPropagation();
          onPointerOver();
        })
      }
      onPointerOut={onPointerOut}
    >
      <spriteMaterial map={face.texture} transparent depthTest={false} toneMapped={false} />
    </sprite>
  );
}

/** A small floating chip anchored to a 3D position (e.g. "In 2 · Booked"). */
export function Label({
  position,
  children,
  emphasis = false,
}: {
  position: [number, number, number];
  children: ReactNode;
  emphasis?: boolean;
}) {
  const text = Children.toArray(children).join("");
  const face = useMemo(() => labelFace(text, emphasis), [text, emphasis]);
  return <ScreenSprite face={face} position={position} />;
}

/** Map-pin style marker over an object with an open issue. */
export function Pin({
  position,
  color,
  label,
  text = "!",
  onClick,
}: {
  position: [number, number, number];
  color: string;
  /** What is written in the pin: "!" for one issue, a number for a group. */
  text?: string;
  /** Not drawn; kept so callers describe what the pin means (the list carries the same data). */
  label: string;
  onClick: () => void;
}) {
  const face = useMemo(() => pinFace(color, text), [color, text]);
  return (
    <ScreenSprite
      face={face}
      position={position}
      anchor={[0.5, 0.05]}
      renderOrder={9}
      onClick={onClick}
      onPointerOver={() => {
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        document.body.style.cursor = "";
      }}
      key={label}
    />
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { useCallback } from "react";
import { apiGet } from "@/lib/api";
import type { SceneResponse } from "./api-types";
import { toSiteScene } from "./mapper";
import type { SiteScene } from "./model";

export const SCENE_REFRESH_MS = 5_000;

interface SceneSnapshot {
  scene: SiteScene;
  /** performance.now() when the snapshot arrived: the anchor for the server clock. */
  receivedAt: number;
}

/** Polls the aggregated scene payload; there is no business logic on the client. */
export function useScene(warehouseId: string) {
  const query = useQuery({
    queryKey: ["scene", warehouseId],
    queryFn: async ({ signal }): Promise<SceneSnapshot> => {
      const response = await apiGet<SceneResponse>(
        `/warehouses/${warehouseId}/scene`,
        undefined,
        signal,
      );
      return { scene: toSiteScene(response), receivedAt: performance.now() };
    },
    refetchInterval: SCENE_REFRESH_MS,
  });

  const snapshot = query.data;
  /**
   * The server's "now", advanced by the local monotonic clock since the data arrived. Using the
   * server's timestamp (not Date.now()) keeps animations correct even if the user's clock is off.
   */
  const getNow = useCallback(
    () => (snapshot ? snapshot.scene.generatedMs + (performance.now() - snapshot.receivedAt) : 0),
    [snapshot],
  );

  return { ...query, scene: snapshot?.scene, getNow };
}

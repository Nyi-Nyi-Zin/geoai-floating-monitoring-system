"use client";

import { useEffect, useMemo } from "react";
import { useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import type { GeoAsset } from "@/lib/api";
import {
  buildSampleSpatialIndex,
  findNearestSample,
  interpolateProbabilityIdwIndexed,
  probabilityColorRgb,
  type ProbabilitySample,
  type SampleSpatialIndex,
} from "@/lib/probability-surface";

type ProbabilitySurfaceLayerProps = {
  samples: ProbabilitySample[];
  opacity?: number;
};

type ProbabilityCellClickHandlerProps = {
  samples: ProbabilitySample[];
  assetById: Map<string, GeoAsset>;
  onSelect: (asset: GeoAsset) => void;
};

const PIXEL_STRIDE = 3;
const REDRAW_DEBOUNCE_MS = 120;

function createSurfaceLayer(
  spatialIndex: SampleSpatialIndex,
  opacity: number,
): L.Layer {
  const SurfaceLayer = L.Layer.extend({
    onAdd(map: L.Map) {
      this._map = map;
      this._redrawTimer = null;
      this._canvas = L.DomUtil.create(
        "canvas",
        "leaflet-probability-surface-layer",
      ) as HTMLCanvasElement;
      this._canvas.style.pointerEvents = "none";
      const pane = map.getPanes().overlayPane;
      pane.appendChild(this._canvas);
      map.on("moveend zoomend", this._scheduleRedraw, this);
      map.on("resize viewreset", this._reset, this);
      if (map.options.zoomAnimation) {
        map.on("zoomanim", this._animateZoom, this);
      }
      this._reset();
    },

    onRemove(map: L.Map) {
      map.off("moveend zoomend", this._scheduleRedraw, this);
      map.off("resize viewreset", this._reset, this);
      if (map.options.zoomAnimation) {
        map.off("zoomanim", this._animateZoom, this);
      }
      if (this._redrawTimer) {
        clearTimeout(this._redrawTimer);
        this._redrawTimer = null;
      }
      L.DomUtil.remove(this._canvas);
    },

    _scheduleRedraw() {
      if (this._redrawTimer) {
        clearTimeout(this._redrawTimer);
      }
      this._redrawTimer = setTimeout(() => {
        this._redrawTimer = null;
        this._reset();
      }, REDRAW_DEBOUNCE_MS);
    },

    _animateZoom(event: L.ZoomAnimEvent) {
      const map = this._map as L.Map;
      const canvas = this._canvas as HTMLCanvasElement;
      const scale = map.getZoomScale(event.zoom);
      const offset = (
        map as L.Map & {
          _latLngBoundsToNewLayerBounds: (
            bounds: L.LatLngBounds,
            zoom: number,
            center: L.LatLng,
          ) => L.Bounds;
        }
      )
        ._latLngBoundsToNewLayerBounds(
          map.getBounds(),
          event.zoom,
          event.center,
        )
        .min;
      if (!offset) return;
      L.DomUtil.setTransform(canvas, offset, scale);
    },

    _reset() {
      const map = this._map as L.Map;
      const canvas = this._canvas as HTMLCanvasElement;
      L.DomUtil.setTransform(canvas, L.point(0, 0), 1);
      this._redraw();
    },

    _redraw() {
      const map = this._map as L.Map;
      const canvas = this._canvas as HTMLCanvasElement;
      if (!spatialIndex.cells.size) {
        canvas.width = 0;
        canvas.height = 0;
        return;
      }

      const size = map.getSize();
      const topLeft = map.containerPointToLayerPoint([0, 0]);
      L.DomUtil.setPosition(canvas, topLeft);

      const width = Math.ceil(size.x / PIXEL_STRIDE);
      const height = Math.ceil(size.y / PIXEL_STRIDE);
      canvas.width = width;
      canvas.height = height;
      canvas.style.width = `${size.x}px`;
      canvas.style.height = `${size.y}px`;

      const context = canvas.getContext("2d");
      if (!context) return;

      const image = context.createImageData(width, height);
      const alphaScale = Math.round(Math.max(0, Math.min(1, opacity)) * 255);

      for (let py = 0; py < height; py += 1) {
        for (let px = 0; px < width; px += 1) {
          const point = map.containerPointToLatLng([
            px * PIXEL_STRIDE,
            py * PIXEL_STRIDE,
          ]);
          const probability = interpolateProbabilityIdwIndexed(
            point.lat,
            point.lng,
            spatialIndex,
          );
          const offset = (py * width + px) * 4;
          if (probability === null) {
            image.data[offset + 3] = 0;
            continue;
          }
          const [r, g, b] = probabilityColorRgb(probability);
          image.data[offset] = r;
          image.data[offset + 1] = g;
          image.data[offset + 2] = b;
          image.data[offset + 3] = alphaScale;
        }
      }

      context.putImageData(image, 0, 0);
    },
  });

  return new SurfaceLayer();
}

export function ProbabilityCellClickHandler({
  samples,
  assetById,
  onSelect,
}: ProbabilityCellClickHandlerProps) {
  const spatialIndex = useMemo(
    () => buildSampleSpatialIndex(samples),
    [samples],
  );

  useMapEvents({
    click(event) {
      const nearest = findNearestSample(
        event.latlng.lat,
        event.latlng.lng,
        spatialIndex,
      );
      if (!nearest?.id) return;
      const asset = assetById.get(nearest.id);
      if (asset) onSelect(asset);
    },
  });

  return null;
}

export default function ProbabilitySurfaceLayer({
  samples,
  opacity = 0.72,
}: ProbabilitySurfaceLayerProps) {
  const map = useMap();
  const sampleKey = useMemo(
    () =>
      samples
        .map((sample) => `${sample.id ?? ""}:${sample.lat}:${sample.lng}:${sample.probability}`)
        .join("|"),
    [samples],
  );
  const spatialIndex = useMemo(
    () => buildSampleSpatialIndex(samples),
    [sampleKey, samples],
  );

  useEffect(() => {
    const layer = createSurfaceLayer(spatialIndex, opacity);
    layer.addTo(map);
    return () => {
      map.removeLayer(layer);
    };
  }, [map, spatialIndex, opacity, sampleKey]);

  return null;
}

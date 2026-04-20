import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type {
  StyleSpecification,
  SourceSpecification,
  LayerSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const BASE_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": "#e8ecf0" },
    },
  ],
};

export interface SourceEntry {
  id: string;
  spec: SourceSpecification;
}

interface Props {
  sources: SourceEntry[];
  layers: LayerSpecification[];
  center?: [number, number];
  zoom?: number;
  height?: string;
  onLoad?: (map: maplibregl.Map) => void;
}

export function MapShell({
  sources,
  layers,
  center = [-96, 38],
  zoom = 3,
  height = "400px",
  onLoad,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASE_STYLE,
      center,
      zoom,
    });

    map.on("load", () => {
      sources.forEach(({ id, spec }) => map.addSource(id, spec));
      layers.forEach((layer) => map.addLayer(layer));
      onLoad?.(map);
    });

    return () => map.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // run once on mount; sources/layers are baked in at init time

  return <div ref={containerRef} style={{ width: "100%", height }} />;
}

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { Trial } from "../../api/trials";
import { MapShell } from "./MapShell";
import { buildPoints } from "../../utils/geoPoints";
import type { GeoJSONSourceSpecification, GeoJSONSource, LayerSpecification } from "maplibre-gl";

interface Props {
  trials: Trial[];
}

export function HeatMap({ trials }: Props) {
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const source = map.getSource("sites") as GeoJSONSource | undefined;
    if (source) source.setData(buildPoints(trials));
  }, [trials]);

  const source: GeoJSONSourceSpecification = {
    type: "geojson",
    data: buildPoints(trials),
  };

  const layers: LayerSpecification[] = [
    {
      id: "sites-heat",
      type: "heatmap",
      source: "sites",
      paint: {
        // Radius grows with zoom
        "heatmap-radius": [
          "interpolate", ["linear"], ["zoom"],
          0, 4,
          5, 12,
          9, 24,
        ],
        // Intensity grows with zoom so dense clusters stay visible when zoomed in
        "heatmap-intensity": [
          "interpolate", ["linear"], ["zoom"],
          0, 0.6,
          9, 2,
        ],
        // Color ramp: transparent → blue → cyan → lime → yellow → red
        "heatmap-color": [
          "interpolate", ["linear"], ["heatmap-density"],
          0,   "rgba(0,0,255,0)",
          0.15, "#4575b4",
          0.35, "#74add1",
          0.55, "#fdae61",
          0.75, "#f46d43",
          1,    "#d73027",
        ],
        "heatmap-opacity": 0.85,
      },
    },
  ];

  function handleLoad(map: maplibregl.Map) {
    mapRef.current = map;
  }

  return (
    <MapShell
      sources={[{ id: "sites", spec: source }]}
      layers={layers}
      height="420px"
      onLoad={handleLoad}
    />
  );
}

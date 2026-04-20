import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { Trial } from "../../api/trials";
import { MapShell } from "./MapShell";
import { buildPoints } from "../../utils/geoPoints";
import type { GeoJSONSourceSpecification, GeoJSONSource, LayerSpecification } from "maplibre-gl";

interface Props {
  trials: Trial[];
}

export function ScatterMap({ trials }: Props) {
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
      id: "scatter-points",
      type: "circle",
      source: "sites",
      paint: {
        "circle-radius": 5,
        "circle-color": "#2171b5",
        "circle-opacity": 0.25,
        "circle-stroke-width": 0,
      },
    },
  ];

  function handleLoad(map: maplibregl.Map) {
    mapRef.current = map;

    const popup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
    });

    map.on("mousemove", "scatter-points", (e) => {
      map.getCanvas().style.cursor = "pointer";
      const feature = e.features?.[0];
      if (!feature) return;
      const { briefTitle, overallStatus, facility, city } = feature.properties as {
        briefTitle: string;
        overallStatus: string;
        facility: string;
        city: string;
      };
      const location = [facility, city].filter(Boolean).join(", ");
      popup
        .setLngLat(e.lngLat)
        .setHTML(
          `<strong>${briefTitle}</strong><br/>${overallStatus}${location ? `<br/>${location}` : ""}`
        )
        .addTo(map);
    });

    map.on("mouseleave", "scatter-points", () => {
      map.getCanvas().style.cursor = "";
      popup.remove();
    });
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

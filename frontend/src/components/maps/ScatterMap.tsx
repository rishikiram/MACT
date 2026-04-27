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

  function jitter(points: GeoJSON.FeatureCollection): GeoJSON.FeatureCollection {
    return {
      ...points,
      features: points.features.map((f) => {
        const random_displacement = [(Math.sqrt(Math.random())) * 0.0002, (Math.random() * 2 * Math.PI)]; // Bias towards smaller displacements
        const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates;
        return {
          ...f,
          geometry: {
            type: "Point" as const,
            coordinates: [
              lon + random_displacement[0] * Math.cos(random_displacement[1]),
              lat + random_displacement[0] * Math.sin(random_displacement[1]),
            ],
          },
        };
      }),
    };
  }

  const source: GeoJSONSourceSpecification = {
    type: "geojson",
    data: jitter(buildPoints(trials)),
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

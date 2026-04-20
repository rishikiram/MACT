import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { Trial } from "../../api/trials";
import { MapShell } from "./MapShell";
import type { GeoJSONSourceSpecification, GeoJSONSource, LayerSpecification } from "maplibre-gl";
import statesGeoJSON from "../../assets/us-states.json";

// Pure function — exported so it can be unit-tested without rendering
export function aggregateByState(trials: Trial[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const trial of trials) {
    // Count each state once per trial (a trial with 10 sites in MA still counts once)
    const seen = new Set<string>();
    for (const loc of trial.locations) {
      if (loc.state && loc.country === "United States" && !seen.has(loc.state)) {
        seen.add(loc.state);
        counts[loc.state] = (counts[loc.state] ?? 0) + 1;
      }
    }
  }
  return counts;
}

interface Props {
  trials: Trial[];
}

function buildEnriched(trials: Trial[]) {
  const counts = aggregateByState(trials);
  return {
    ...statesGeoJSON,
    features: statesGeoJSON.features.map((feature) => ({
      ...feature,
      properties: {
        ...feature.properties,
        trialCount: counts[(feature.properties as { name: string }).name] ?? 0,
      },
    })),
  };
}

export function UsStatesMap({ trials }: Props) {
  const mapRef = useRef<maplibregl.Map | null>(null);

  // When trials change after initial mount, push updated data and color scale into the map
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const source = map.getSource("states") as GeoJSONSource | undefined;
    if (source) {
      source.setData(buildEnriched(trials) as GeoJSON.FeatureCollection);
    }

    const max = Math.max(1, ...Object.values(aggregateByState(trials)));
    map.setPaintProperty("states-fill", "fill-color", [
      "interpolate", ["linear"], ["get", "trialCount"],
      0,          "#f0f4f8",
      max * 0.25, "#bdd7ea",
      max * 0.5,  "#6aaed6",
      max * 0.75, "#2171b5",
      max,        "#084594",
    ]);
  }, [trials]);

  const counts = aggregateByState(trials);
  const maxCount = Math.max(1, ...Object.values(counts));
  const enriched = buildEnriched(trials);

  const source: GeoJSONSourceSpecification = {
    type: "geojson",
    data: enriched as GeoJSON.FeatureCollection,
  };

  const layers: LayerSpecification[] = [
    {
      id: "states-fill",
      type: "fill",
      source: "states",
      paint: {
        "fill-color": [
          "interpolate",
          ["linear"],
          ["get", "trialCount"],
          0,                      "#f0f4f8",
          maxCount * 0.25,        "#bdd7ea",
          maxCount * 0.5,         "#6aaed6",
          maxCount * 0.75,        "#2171b5",
          maxCount,               "#084594",
        ],
        "fill-opacity": 0.85,
      },
    },
    {
      id: "states-outline",
      type: "line",
      source: "states",
      paint: {
        "line-color": "#ffffff",
        "line-width": 0.8,
      },
    },
  ];

  function handleLoad(map: maplibregl.Map) {
    mapRef.current = map;

    const popup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
    });

    map.on("mousemove", "states-fill", (e) => {
      map.getCanvas().style.cursor = "pointer";
      const feature = e.features?.[0];
      if (!feature) return;
      const { name, trialCount } = feature.properties as {
        name: string;
        trialCount: number;
      };
      popup
        .setLngLat(e.lngLat)
        .setHTML(
          `<strong>${name}</strong><br/>${trialCount} trial${trialCount !== 1 ? "s" : ""}`
        )
        .addTo(map);
    });

    map.on("mouseleave", "states-fill", () => {
      map.getCanvas().style.cursor = "";
      popup.remove();
    });
  }

  return (
    <MapShell
      sources={[{ id: "states", spec: source }]}
      layers={layers}
      height="420px"
      onLoad={handleLoad}
    />
  );
}

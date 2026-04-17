import type { Trial } from "../../api/trials";
import { MapShell } from "./MapShell";
import type { GeoJSONSourceSpecification, LayerSpecification } from "maplibre-gl";
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

export function UsStatesMap({ trials }: Props) {
  const counts = aggregateByState(trials);

  // Inject trialCount into each GeoJSON feature so MapLibre can use it directly
  const enriched = {
    ...statesGeoJSON,
    features: statesGeoJSON.features.map((feature) => ({
      ...feature,
      properties: {
        ...feature.properties,
        trialCount: counts[(feature.properties as { name: string }).name] ?? 0,
      },
    })),
  };

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
          0, "#f0f4f8",
          10, "#bdd7ea",
          25, "#6aaed6",
          50, "#2171b5",
          100, "#084594",
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

  return (
    <MapShell
      sources={[{ id: "states", spec: source }]}
      layers={layers}
      height="420px"
    />
  );
}

import type { Trial } from "../api/trials";

export function buildPoints(trials: Trial[]): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = [];
  for (const trial of trials) {
    for (const loc of trial.locations) {
      if (loc.geoPoint) {
        features.push({
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [loc.geoPoint.lon, loc.geoPoint.lat],
          },
          properties: {
            nctId: trial.nctId,
            briefTitle: trial.briefTitle,
            overallStatus: trial.overallStatus,
            facility: loc.facility ?? "",
            city: loc.city ?? "",
            country: loc.country ?? "",
          },
        });
      }
    }
  }
  return { type: "FeatureCollection", features };
}

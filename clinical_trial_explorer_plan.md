# Clinical Trial Explorer

A local web app that fetches clinical trial data from ClinicalTrials.gov and displays it as an interactive list and map.

## How it runs

Two terminals:

| | Command | URL |
|---|---|---|
| Frontend | `npm run dev` in `/frontend` | `http://localhost:3000` |
| Backend | `npm run dev` in `/backend` | `http://localhost:3001` |

## Architecture

The frontend never calls ClinicalTrials.gov directly. All requests go through the Express backend, which forwards them to the CT.gov v2 API and pipes the response back.

```
Browser → localhost:3001/api/trials?... → clinicaltrials.gov/api/v2/studies?...
```

Preset queries are defined in `frontend/src/api/queries.ts` as named `FetchTrialsParams` objects (e.g. `ONCOLOGY`, `NSCLC`, `RECRUITING_DIABETES`). The user selects one via toggle buttons in `App.tsx`, which drives `useTrials` — a TanStack Query hook wrapping `fetchTrials`.

## Components

**`TrialTable.tsx`** — renders trials as an expandable list. Click a row to see NCT ID, phase, conditions, site count, and brief summary.

**`MapShell.tsx`** — thin MapLibre GL wrapper. Accepts `sources`, `layers`, and an `onLoad` callback that hands back the live map instance.

**`UsStatesMap.tsx`** — choropleth of trials per US state. `aggregateByState` counts trials per state (one count per trial regardless of how many sites it has there), enriches the bundled GeoJSON with that count, and passes it to `MapShell`. Hovering a state shows a popup with the state name and trial count. When `trials` changes, `source.setData()` updates the map in place without remounting.

## Adding a new map

Create a new file in `frontend/src/components/maps/`. Accept `trials: Trial[]` as a prop, transform the data, and pass GeoJSON sources and MapLibre layer configs to `MapShell`.

## Tech stack

React + Vite · TanStack Query · MapLibre GL JS · Node.js + Express · TypeScript throughout

## Tests

- **Backend** (Jest + Supertest): proxy forwards correctly, responds 502 on upstream error
- **Frontend** (Vitest): `fetchTrials` URL and response mapping, `useTrials` success/error/disabled states, `TrialTable` render and expand/collapse, `aggregateByState` count logic

## ClinicalTrials.gov API

- https://clinicaltrials.gov/data-api/api
-  

---

# Things to Implement

## Scatter Map (`ScatterMap.tsx`)

One point per trial site. Points are semi-transparent so dense clusters naturally appear more saturated. Hovering a point shows a popup with study details.

### Data

Reuses `buildPoints` from `HeatMap.tsx` — same GeoJSON FeatureCollection of Points, one per location with a valid `geoPoint`. Extract `buildPoints` to a shared utility (e.g. `frontend/src/utils/geoPoints.ts`) so both maps import it.

### MapLibre layer config

Layer type: `circle`.

- `circle-radius` — fixed small size (e.g. 5px)
- `circle-color` — single accent color (e.g. `#2171b5`)
- `circle-opacity` — low (e.g. 0.25) so overlapping points compound visually
- `circle-stroke-width` — 0 (no border keeps overlap clean)

### Hover popup

On `mousemove` over the `scatter-points` layer, show a `maplibregl.Popup` with:
- Trial title
- Status
- Facility name and city

Use the same `onLoad` + popup pattern as `UsStatesMap`.

### Component structure

Same pattern as `HeatMap`: `buildPoints` for initial source data, `useEffect([trials])` calling `source.setData()` on updates, `onLoad` to store the map ref.



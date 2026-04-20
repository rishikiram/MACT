import express, { Request, Response } from "express";
import https from "https";

const app = express();
const PORT = 3001;
const CT_GOV_BASE = "https://clinicaltrials.gov/api/v2/studies";
const PAGE_CAP = 20; // max 20,000 studies per request

app.use(express.json());

// Allow requests from the Vite dev server
app.use((_req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "http://localhost:3000");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  next();
});

app.get("/api/trials", (req: Request, res: Response) => {
  const params = new URLSearchParams(req.query as Record<string, string>);
  const url = `${CT_GOV_BASE}?${params.toString()}`;

  https
    .get(url, { headers: { Accept: "application/json" } }, (upstream) => {
      res.setHeader("Content-Type", "application/json");
      upstream.pipe(res);
    })
    .on("error", (err) => {
      console.error("Upstream error:", err.message);
      res.status(502).json({ error: "Failed to reach ClinicalTrials.gov" });
    });
});

async function fetchAllPages(
  baseParams: URLSearchParams
): Promise<{ studies: unknown[]; totalCount: number }> {
  baseParams.set("pageSize", "1000");
  baseParams.delete("pageToken");

  const allStudies: unknown[] = [];
  let pageToken: string | undefined;
  let page = 0;

  do {
    page++;
    const params = new URLSearchParams(baseParams);
    if (pageToken) params.set("pageToken", pageToken);

    const url = `${CT_GOV_BASE}?${params.toString()}`;
    console.log(`[/api/trials/all] page ${page} — ${url}`);

    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`CT.gov returned ${response.status}`);

    const data = await response.json() as {
      studies?: unknown[];
      nextPageToken?: string;
    };

    allStudies.push(...(data.studies ?? []));
    pageToken = data.nextPageToken;

    console.log(
      `[/api/trials/all] page ${page}: ${(data.studies ?? []).length} studies (running total: ${allStudies.length})`
    );
  } while (pageToken && page < PAGE_CAP);

  if (pageToken && page >= PAGE_CAP) {
    console.warn(`[/api/trials/all] hit ${PAGE_CAP}-page cap — results may be incomplete`);
  }

  return { studies: allStudies, totalCount: allStudies.length };
}

app.get("/api/trials/all", async (req: Request, res: Response) => {
  const params = new URLSearchParams(req.query as Record<string, string>);
  try {
    const result = await fetchAllPages(params);
    res.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("[/api/trials/all] error:", message);
    res.status(502).json({ error: "Failed to fetch all pages from ClinicalTrials.gov" });
  }
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Backend proxy listening on http://localhost:${PORT}`);
  });
}

export default app;

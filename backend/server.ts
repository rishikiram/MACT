import express, { Request, Response } from "express";
import https from "https";
import fs from "fs";
import path from "path";
import crypto from "crypto";

const app = express();
const PORT = 3001;
const CT_GOV_BASE = "https://clinicaltrials.gov/api/v2/studies";
const PAGE_CAP = 20;   // max 20,000 studies per request
const CACHE_SIZE = 8;
const CACHE_DIR = path.join(__dirname, "cache");

type QueryResult = { studies: unknown[]; totalCount: number };

// LRU index: Map<hash, true> — preserves insertion order for eviction.
// Actual data lives in CACHE_DIR/{hash}.json.
const queryCache = new Map<string, true>();

function hashParams(params: URLSearchParams): string {
  const sorted = new URLSearchParams([...params.entries()].sort()).toString();
  return crypto.createHash("md5").update(sorted).digest("hex");
}

function cacheFilePath(hash: string): string {
  return path.join(CACHE_DIR, `${hash}.json`);
}

async function cacheGet(hash: string): Promise<QueryResult | undefined> {
  if (!queryCache.has(hash)) return undefined;
  try {
    const raw = await fs.promises.readFile(cacheFilePath(hash), "utf8");
    // Refresh LRU position
    queryCache.delete(hash);
    queryCache.set(hash, true);
    return JSON.parse(raw) as QueryResult;
  } catch {
    // File missing or unreadable — remove stale index entry
    queryCache.delete(hash);
    return undefined;
  }
}

async function cacheSet(hash: string, value: QueryResult): Promise<void> {
  if (queryCache.has(hash)) queryCache.delete(hash);
  if (queryCache.size >= CACHE_SIZE) {
    const oldest = queryCache.keys().next().value!;
    queryCache.delete(oldest);
    fs.unlink(cacheFilePath(oldest), () => {}); // fire-and-forget
  }
  await fs.promises.mkdir(CACHE_DIR, { recursive: true });
  await fs.promises.writeFile(cacheFilePath(hash), JSON.stringify(value), "utf8");
  queryCache.set(hash, true);
}

export async function clearCache(): Promise<void> {
  for (const hash of queryCache.keys()) {
    await fs.promises.unlink(cacheFilePath(hash)).catch(() => {});
  }
  queryCache.clear();
}

// On startup: rebuild LRU index from disk, sorted oldest→newest by mtime
function loadCacheFromDisk(): void {
  if (!fs.existsSync(CACHE_DIR)) return;
  const files = fs.readdirSync(CACHE_DIR).filter((f) => f.endsWith(".json"));
  const sorted = files
    .map((f) => ({ hash: f.slice(0, -5), mtime: fs.statSync(path.join(CACHE_DIR, f)).mtimeMs }))
    .sort((a, b) => a.mtime - b.mtime); // oldest first → LRU order

  // If more files than CACHE_SIZE on disk, delete the oldest extras
  const toDelete = sorted.slice(0, -CACHE_SIZE);
  for (const { hash } of toDelete) {
    fs.unlink(cacheFilePath(hash), () => {});
  }
  for (const { hash } of sorted.slice(-CACHE_SIZE)) {
    queryCache.set(hash, true);
  }
  if (queryCache.size > 0) {
    console.log(`[cache] loaded ${queryCache.size} entr${queryCache.size === 1 ? "y" : "ies"} from disk`);
  }
}

loadCacheFromDisk();

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
): Promise<QueryResult> {
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
  const hash = hashParams(params);

  const cached = await cacheGet(hash);
  if (cached) {
    console.log(`[/api/trials/all] cache hit (${queryCache.size}/${CACHE_SIZE}): ${hash}`);
    res.json(cached);
    return;
  }

  try {
    const result = await fetchAllPages(params);
    await cacheSet(hash, result);
    console.log(`[/api/trials/all] cached to disk (${queryCache.size}/${CACHE_SIZE}): ${hash}`);
    res.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("[/api/trials/all] error:", message);
    res.status(502).json({ error: "Failed to fetch all pages from ClinicalTrials.gov" });
  }
});

app.get("/debug/memory", (_req, res) => {
  const m = process.memoryUsage();
  const mb = (n: number) => `${(n / 1024 / 1024).toFixed(1)} MB`;
  res.json({
    heapUsed:     mb(m.heapUsed),
    heapTotal:    mb(m.heapTotal),
    rss:          mb(m.rss),
    external:     mb(m.external),
    cacheEntries: queryCache.size,
  });
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Backend proxy listening on http://localhost:${PORT}`);
  });
}

export default app;

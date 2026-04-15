import express, { Request, Response } from "express";
import https from "https";

const app = express();
const PORT = 3001;
const CT_GOV_BASE = "https://clinicaltrials.gov/api/v2/studies";

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

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Backend proxy listening on http://localhost:${PORT}`);
  });
}

export default app;

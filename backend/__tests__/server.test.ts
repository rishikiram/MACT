import request from "supertest";
import https from "https";
import { PassThrough } from "stream";
import app, { clearCache } from "../server";

const mockFetch = jest.fn();
global.fetch = mockFetch;

jest.mock("https");
const mockGet = https.get as jest.Mock;

beforeAll(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  jest.spyOn(console, "log").mockImplementation(() => {});
  jest.spyOn(console, "warn").mockImplementation(() => {});
});
afterAll(() => jest.restoreAllMocks());
afterEach(async () => {
  jest.resetAllMocks();
  await clearCache();
});

describe("GET /api/trials", () => {
  it("forwards query params to CT.gov and pipes the response back", async () => {
    // Fake upstream: a readable stream with a JSON body
    const upstream = new PassThrough();
    upstream.end(JSON.stringify({ studies: [] }));

    mockGet.mockImplementation((_url: string, _opts: unknown, cb: (r: PassThrough) => void) => {
      cb(upstream);
      return { on: jest.fn().mockReturnThis() };
    });

    const res = await request(app).get("/api/trials?query.cond=diabetes&pageSize=5");

    expect(res.status).toBe(200);
    const [calledUrl] = mockGet.mock.calls[0] as [string, ...unknown[]];
    expect(calledUrl).toContain("clinicaltrials.gov");
    expect(calledUrl).toContain("query.cond=diabetes");
    expect(calledUrl).toContain("pageSize=5");
    expect(res.body).toEqual({ studies: [] });
  });

  it("returns 502 when the upstream connection fails", async () => {
    mockGet.mockImplementation(() => ({
      on: (event: string, handler: (err: Error) => void) => {
        if (event === "error") {
          process.nextTick(() => handler(new Error("connection refused")));
        }
        return { on: jest.fn() };
      },
    }));

    const res = await request(app).get("/api/trials");

    expect(res.status).toBe(502);
    expect(res.body.error).toBeDefined();
  });
});

describe("GET /api/trials/all", () => {
  it("paginates through all pages and returns combined studies", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ studies: [{ id: "NCT001" }], nextPageToken: "tok2" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ studies: [{ id: "NCT002" }] }), // no nextPageToken — last page
      });

    const res = await request(app).get("/api/trials/all?query.cond=diabetes");

    expect(res.status).toBe(200);
    expect(res.body.studies).toHaveLength(2);
    expect(res.body.totalCount).toBe(2);
    expect(mockFetch).toHaveBeenCalledTimes(2);

    const firstUrl: string = mockFetch.mock.calls[0][0];
    expect(firstUrl).toContain("query.cond=diabetes");
    expect(firstUrl).toContain("pageSize=1000");

    const secondUrl: string = mockFetch.mock.calls[1][0];
    expect(secondUrl).toContain("pageToken=tok2");
  });

  it("returns 502 when CT.gov returns an error status", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

    const res = await request(app).get("/api/trials/all?query.cond=diabetes");

    expect(res.status).toBe(502);
    expect(res.body.error).toBeDefined();
  });

  it("returns cached result on second request without calling CT.gov again", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ studies: [{ id: "NCT001" }] }),
    });

    await request(app).get("/api/trials/all?query.cond=diabetes");
    await request(app).get("/api/trials/all?query.cond=diabetes");

    // CT.gov should only have been called once despite two requests
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});

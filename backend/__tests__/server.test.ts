import request from "supertest";
import https from "https";
import { PassThrough } from "stream";
import app from "../server";

jest.mock("https");
const mockGet = https.get as jest.Mock;

beforeAll(() => jest.spyOn(console, "error").mockImplementation(() => {}));
afterAll(() => jest.restoreAllMocks());
afterEach(() => jest.resetAllMocks());

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

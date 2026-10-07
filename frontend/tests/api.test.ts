import { vi } from "vitest";
import { ApiError, apiGet } from "@/lib/api";

function mockFetch(response: Response | Error) {
  const fn = vi.fn(() =>
    response instanceof Error ? Promise.reject(response) : Promise.resolve(response),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("apiGet", () => {
  it("repeats list params and skips undefined ones", async () => {
    const fetchMock = mockFetch(Response.json({ ok: true }));
    await apiGet("/shipments", { status: ["A", "B"], limit: 6, search: undefined });
    const url = new URL(String((fetchMock.mock.calls as unknown as [string][])[0][0]));
    expect(url.pathname).toBe("/api/v1/shipments");
    expect(url.searchParams.getAll("status")).toEqual(["A", "B"]);
    expect(url.searchParams.get("limit")).toBe("6");
    expect(url.searchParams.has("search")).toBe(false);
  });

  it("reads the backend's error envelope on a non-2xx response", async () => {
    mockFetch(
      Response.json(
        { error: { code: "not_found", message: "Shipment not found" } },
        { status: 404 },
      ),
    );
    await expect(apiGet("/shipments/x")).rejects.toMatchObject({
      status: 404,
      message: "Shipment not found",
      code: "not_found",
    });
  });

  it("falls back to FastAPI's detail field and to the status text", async () => {
    mockFetch(Response.json({ detail: "Not authenticated" }, { status: 401 }));
    await expect(apiGet("/x")).rejects.toMatchObject({ message: "Not authenticated" });
    mockFetch(new Response("<html>bad gateway</html>", { status: 502, statusText: "Bad Gateway" }));
    await expect(apiGet("/x")).rejects.toMatchObject({ status: 502, message: "Bad Gateway" });
  });

  it("raises a friendly ApiError when the backend is unreachable", async () => {
    mockFetch(new TypeError("Failed to fetch"));
    const error = await apiGet("/x").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).message).toMatch(/Is the backend running/);
  });
});

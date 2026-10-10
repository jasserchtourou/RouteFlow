import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { DashboardView } from "@/features/dashboard/dashboard-view";
import { EMPTY_PAGE, EXCEPTIONS, NOW, OVERVIEW, SHIPMENTS } from "./fixtures/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

function routeFetch(handlers: Record<string, () => Response>) {
  const fn = vi.fn((input: string | URL | Request) => {
    const path = new URL(String(input)).pathname.replace("/api/v1", "");
    const handler = handlers[path];
    return Promise.resolve(handler ? handler() : new Response("nope", { status: 404 }));
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

function renderView() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <DashboardView />
    </QueryClientProvider>,
  );
}

const ok = (body: unknown) => () => Response.json(body);

beforeEach(() => {
  // Freeze only Date (not timers) so ETAs are relative to a known "now" and async code still runs.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("DashboardView", () => {
  it("shows a skeleton, then the data from the API", async () => {
    routeFetch({
      "/dashboard/overview": ok(OVERVIEW),
      "/shipments": ok(SHIPMENTS),
      "/exceptions": ok(EXCEPTIONS),
    });
    renderView();
    expect(screen.getByLabelText("Loading dashboard")).toBeInTheDocument();

    const kpis = await screen.findByRole("region", { name: "Key metrics" });
    expect(within(kpis).getByText("91.3%")).toBeInTheDocument();
    expect(within(kpis).getByText("1 critical")).toBeInTheDocument();
    expect(screen.getByText("Temperature deviation")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(SHIPMENTS.items.length + 1);
    expect(screen.getByText("overdue")).toBeInTheDocument();
    expect(screen.getByText("Disrupted")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Garbsen DC utilization" })).toHaveAttribute(
      "aria-valuenow",
      "96",
    );
  });

  it("shows an empty state when there are no active exceptions", async () => {
    routeFetch({
      "/dashboard/overview": ok(OVERVIEW),
      "/shipments": ok(SHIPMENTS),
      "/exceptions": ok(EMPTY_PAGE),
    });
    renderView();
    expect(await screen.findByText(/Everything is on track/)).toBeInTheDocument();
  });

  it("shows an error with a working retry when the API fails", async () => {
    let failing = true;
    routeFetch({
      "/dashboard/overview": () =>
        failing
          ? Response.json({ detail: "Database down" }, { status: 503 })
          : Response.json(OVERVIEW),
      "/shipments": ok(SHIPMENTS),
      "/exceptions": ok(EXCEPTIONS),
    });
    const user = userEvent.setup();
    renderView();

    expect(await screen.findByRole("alert")).toHaveTextContent("Database down");
    failing = false;
    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByRole("region", { name: "Key metrics" })).toBeInTheDocument();
  });
});

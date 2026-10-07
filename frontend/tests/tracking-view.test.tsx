import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { TrackingView } from "@/features/tracking/tracking-view";
import { VEHICLES, WAREHOUSES } from "./fixtures/fleet";

// Leaflet needs a real layout engine; the map is replaced by a stub that exposes its props.
vi.mock("next/dynamic", () => ({
  default: () =>
    function FleetMapStub(props: {
      vehicles: { id: string; registration: string }[];
      selectedId: string | null;
      onSelect: (id: string) => void;
    }) {
      return (
        <div data-testid="map" data-selected={props.selectedId ?? ""}>
          {props.vehicles.map((v) => (
            <button key={v.id} onClick={() => props.onSelect(v.id)}>
              marker {v.registration}
            </button>
          ))}
        </div>
      );
    },
}));

function mockApi(failing = false) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string | URL | Request) => {
      if (failing)
        return Promise.resolve(Response.json({ detail: "Fleet offline" }, { status: 503 }));
      const path = new URL(String(input)).pathname;
      const items = path.endsWith("/vehicles") ? VEHICLES : WAREHOUSES;
      return Promise.resolve(Response.json({ items, total: items.length, limit: 100, offset: 0 }));
    }),
  );
}

function renderView() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <TrackingView />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("TrackingView", () => {
  it("lists vehicles that have a position and warns about the rest", async () => {
    mockApi();
    renderView();
    expect(await screen.findByText("B-RF 1074")).toBeInTheDocument();
    expect(screen.queryByText("B-RF 1444")).not.toBeInTheDocument();
    expect(screen.getByText(/1 vehicle\(s\) have not reported a position/)).toBeInTheDocument();
    expect(screen.getByText("low fuel")).toBeInTheDocument();
  });

  it("filters the list and the map by status", async () => {
    mockApi();
    const user = userEvent.setup();
    renderView();
    await screen.findByText("B-RF 1074");

    await user.click(screen.getByRole("button", { name: "Available · 1" }));
    const list = screen.getByRole("list");
    expect(within(list).getByText("B-RF 1259")).toBeInTheDocument();
    expect(within(list).queryByText("B-RF 1074")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "marker B-RF 1074" })).not.toBeInTheDocument();
  });

  it("keeps the list and the map selection in sync and shows shipments on board", async () => {
    mockApi();
    const user = userEvent.setup();
    renderView();
    await screen.findByText("B-RF 1074");

    await user.click(screen.getByRole("button", { name: "marker B-RF 1074" }));
    expect(screen.getByTestId("map")).toHaveAttribute("data-selected", "v2");
    expect(screen.getByText("SHP-2254")).toBeInTheDocument();

    await user.click(within(screen.getByRole("list")).getByRole("button", { name: /B-RF 1259/ }));
    expect(screen.getByTestId("map")).toHaveAttribute("data-selected", "v1");
  });

  it("shows an error when the API is down", async () => {
    mockApi(true);
    renderView();
    expect(await screen.findByRole("alert")).toHaveTextContent("Fleet offline");
  });
});

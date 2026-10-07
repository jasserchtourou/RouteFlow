import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { SiteView } from "@/features/site3d/site-view";
import { SCENE } from "./fixtures/scene";

const focus = vi.fn();

// WebGL is not available in tests: the canvas is replaced by a stub that exposes its inputs
// and lets the test "click" objects the way the 3D scene would.
vi.mock("next/dynamic", () => ({
  default: () =>
    function CanvasStub(props: {
      scene: { visits: { id: string; truckCode: string }[] };
      palette: { background: string };
      interaction: { select: (s: { kind: "truck"; id: string }) => void };
      apiRef: { current: unknown };
    }) {
      props.apiRef.current = {
        focus,
        zoomIn: vi.fn(),
        zoomOut: vi.fn(),
        rotate: vi.fn(),
        reset: vi.fn(),
      };
      return (
        <div data-testid="canvas" data-background={props.palette.background}>
          {props.scene.visits.map((v) => (
            <button
              key={v.id}
              onClick={() => props.interaction.select({ kind: "truck", id: v.id })}
            >
              3d {v.truckCode}
            </button>
          ))}
        </div>
      );
    },
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

function mockApi(scene: unknown = SCENE, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string | URL | Request) => {
      const path = new URL(String(input)).pathname;
      if (path.endsWith("/scene")) {
        return Promise.resolve(
          status === 200
            ? Response.json(scene)
            : Response.json({ error: { message: "Warehouse not found" } }, { status }),
        );
      }
      return Promise.resolve(
        Response.json({ items: [{ id: "w1", code: "WH-GAR", name: "Garbsen Logistics Park" }] }),
      );
    }),
  );
}

function renderView() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SiteView warehouseId="w1" />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  focus.mockClear();
});

describe("SiteView", () => {
  it("shows the KPIs, the tracker for the active truck and the operations list", async () => {
    mockApi();
    renderView();

    const kpis = await screen.findByRole("region", { name: "Site metrics" });
    expect(within(kpis).getByText("960")).toBeInTheDocument();
    expect(within(kpis).getByText("96.2%")).toBeInTheDocument();
    expect(within(kpis).getByText("1 inbound · WH-GAR")).toBeInTheDocument();

    const tracker = screen.getByRole("region", { name: "Shipment tracking" });
    expect(within(tracker).getByText("Loading 2/6")).toBeInTheDocument();
    expect(within(tracker).getByText("#SHP-2251")).toBeInTheDocument();

    const ops = screen.getByRole("region", { name: "Site operations" });
    expect(within(ops).getByRole("tab", { name: /Docks 1\/3/ })).toBeInTheDocument();
    expect(within(ops).getByRole("tab", { name: /Forklifts 1\/3/ })).toBeInTheDocument();
    expect(within(ops).getByRole("tab", { name: /Trucks 2/ })).toBeInTheDocument();
    expect(within(ops).getByText("No truck assigned")).toBeInTheDocument();
  });

  it("selecting a dock in the list opens its details and focuses the camera", async () => {
    mockApi();
    const user = userEvent.setup();
    renderView();
    const ops = await screen.findByRole("region", { name: "Site operations" });

    await user.click(within(ops).getByRole("button", { name: /In 1/ }));

    const panel = screen.getByRole("region", { name: /Dock bay · WH-GAR details/ });
    expect(within(panel).getByText("Booked")).toBeInTheDocument();
    expect(within(panel).getByText(/TRK-2481 due in 3 min/)).toBeInTheDocument();
    expect(focus).toHaveBeenCalledTimes(1);

    await user.click(within(panel).getByRole("button", { name: "Close details" }));
    expect(screen.queryByRole("region", { name: /details/ })).not.toBeInTheDocument();
  });

  it("selecting a truck in the scene updates the tracker and the details", async () => {
    mockApi();
    const user = userEvent.setup();
    renderView();
    await screen.findByRole("region", { name: "Site operations" });

    await user.click(screen.getByRole("button", { name: "3d TRK-2481" }));

    const panel = screen.getByRole("region", { name: "Truck details" });
    expect(within(panel).getByText("In 1")).toBeInTheDocument();
    const tracker = screen.getByRole("region", { name: "Shipment tracking" });
    expect(within(tracker).getByText("Unloading 0/12")).toBeInTheDocument();
  });

  it("lists forklifts and trucks on their tabs and shows forklift details", async () => {
    mockApi();
    const user = userEvent.setup();
    renderView();
    const ops = await screen.findByRole("region", { name: "Site operations" });

    await user.click(within(ops).getByRole("tab", { name: /Trucks/ }));
    expect(within(ops).getByText("TRK-2205")).toBeInTheDocument();

    await user.click(within(ops).getByRole("tab", { name: /Forklifts/ }));
    await user.click(within(ops).getByRole("button", { name: /FL-01/ }));
    const panel = screen.getByRole("region", { name: /Forklift details/ });
    expect(within(panel).getByText("Out 1")).toBeInTheDocument();
    expect(within(panel).getByText("82%")).toBeInTheDocument();
  });

  it("switches between the night and daylight scenes", async () => {
    mockApi();
    const user = userEvent.setup();
    renderView();
    const canvas = await screen.findByTestId("canvas");
    const night = canvas.getAttribute("data-background");

    await user.click(screen.getByRole("button", { name: "Switch to daylight scene" }));

    expect(screen.getByTestId("canvas").getAttribute("data-background")).not.toBe(night);
    expect(screen.getByRole("button", { name: "Switch to night scene" })).toBeInTheDocument();
  });

  it("shows an error when the site cannot be loaded", async () => {
    mockApi(null, 404);
    renderView();
    expect(await screen.findByRole("alert")).toHaveTextContent("Site view unavailable");
  });
});

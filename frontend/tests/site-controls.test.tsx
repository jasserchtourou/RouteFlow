import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AppShell } from "@/components/layout/app-shell";
import { toSiteScene } from "@/features/site3d/mapper";
import { filterResults, searchIndex } from "@/features/site3d/overlay/site-search";
import { SiteView } from "@/features/site3d/site-view";
import { SCENE } from "./fixtures/scene";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/warehouses/w1/3d",
}));

vi.mock("next/dynamic", () => ({
  default: () =>
    function CanvasStub(props: { apiRef: { current: unknown } }) {
      props.apiRef.current = {
        focus: vi.fn(),
        zoomIn: vi.fn(),
        zoomOut: vi.fn(),
        rotate: vi.fn(),
        reset: vi.fn(),
      };
      return <div data-testid="canvas" />;
    },
}));

function mockApi() {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string | URL | Request) =>
      Promise.resolve(
        new URL(String(input)).pathname.endsWith("/scene")
          ? Response.json(SCENE)
          : Response.json({ items: [{ id: "w1", code: "WH-GAR", name: "Garbsen" }] }),
      ),
    ),
  );
}

function renderSite() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SiteView warehouseId="w1" />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("site search index", () => {
  const index = searchIndex(toSiteScene(SCENE));

  it("finds trucks by code, carrier, dock or shipment", () => {
    expect(filterResults(index, "2205").map((r) => r.label)).toEqual(["TRK-2205"]);
    expect(filterResults(index, "elbe").map((r) => r.label)).toEqual(["TRK-2481"]);
    expect(filterResults(index, "SHP-2251").map((r) => r.label)).toEqual(["TRK-2205"]);
    expect(filterResults(index, "hamburg").map((r) => r.label)).toEqual(["TRK-2205"]);
  });

  it("finds docks, forklifts and pallets, and combines several words", () => {
    expect(filterResults(index, "out 1").map((r) => r.label)).toContain("Out 1");
    expect(filterResults(index, "fl-01").map((r) => r.kind)).toEqual(["Forklift"]);
    expect(filterResults(index, "gloves").map((r) => r.label)).toEqual(["PAL-1002"]);
    expect(filterResults(index, "pallet low")).toEqual([]);
  });

  it("returns nothing for an empty query", () => {
    expect(filterResults(index, "   ")).toEqual([]);
  });
});

describe("site view controls", () => {
  it("searches with the keyboard and selects the result", async () => {
    mockApi();
    const user = userEvent.setup();
    renderSite();
    const box = await screen.findByRole("combobox", { name: "Search site" });

    await user.type(box, "2481");
    const list = screen.getByRole("listbox", { name: "Search results" });
    expect(within(list).getByRole("option", { name: /TRK-2481/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await user.keyboard("{Enter}");

    expect(screen.getByRole("region", { name: "Truck details" })).toBeInTheDocument();
    expect(box).toHaveValue("");
  });

  it("says when nothing matches", async () => {
    mockApi();
    const user = userEvent.setup();
    renderSite();
    await user.type(await screen.findByRole("combobox", { name: "Search site" }), "zzz");
    expect(screen.getByText(/Nothing matches/)).toBeInTheDocument();
  });

  it("focuses the search with / and clears the selection with Escape", async () => {
    mockApi();
    const user = userEvent.setup();
    renderSite();
    const box = await screen.findByRole("combobox", { name: "Search site" });

    await user.keyboard("/");
    expect(box).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(box).not.toHaveFocus();

    await user.click(screen.getByRole("button", { name: /In 1/ }));
    expect(screen.getByRole("region", { name: /Dock bay/ })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("region", { name: /Dock bay/ })).not.toBeInTheDocument();
  });

  it("hides and shows every panel with H and the toolbar button", async () => {
    mockApi();
    const user = userEvent.setup();
    renderSite();
    await screen.findByRole("region", { name: "Site operations" });

    await user.keyboard("h");
    expect(screen.queryByRole("region", { name: "Site operations" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Site metrics" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Show panels" }));
    expect(screen.getByRole("region", { name: "Site operations" })).toBeInTheDocument();
  });

  it("opens the shortcut list with ? and closes it with Escape", async () => {
    mockApi();
    const user = userEvent.setup();
    renderSite();
    await screen.findByRole("region", { name: "Site operations" });

    await user.keyboard("?");
    expect(screen.getByRole("dialog", { name: "Keyboard shortcuts" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Keyboard shortcuts" })).not.toBeInTheDocument();
  });

  it("collapses a panel without affecting the others, and keeps it collapsed on reload", async () => {
    mockApi();
    const user = userEvent.setup();
    const first = renderSite();
    const ops = await screen.findByRole("region", { name: "Site operations" });
    await user.click(within(ops).getByRole("button", { name: /Operations/ }));
    expect(within(ops).getByRole("button", { name: /Operations/ })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(
      within(screen.getByRole("region", { name: "Site metrics" })).getByRole("button", {
        name: /Metrics/,
      }),
    ).toHaveAttribute("aria-expanded", "true");
    first.unmount();

    renderSite();
    const again = await screen.findByRole("region", { name: "Site operations" });
    expect(await within(again).findByRole("button", { name: /Operations/ })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("remembers the chosen scene look", async () => {
    mockApi();
    const user = userEvent.setup();
    const first = renderSite();
    await user.click(await screen.findByRole("button", { name: "Switch to daylight scene" }));
    first.unmount();

    renderSite();
    expect(
      await screen.findByRole("button", { name: "Switch to night scene" }),
    ).toBeInTheDocument();
  });
});

describe("app shell sidebar", () => {
  it("collapses to icons, keeps the links reachable, and remembers it", async () => {
    const user = userEvent.setup();
    const first = render(<AppShell>content</AppShell>);
    const nav = screen.getAllByRole("navigation", { name: "Main" })[0];
    expect(within(nav).getByRole("link", { name: "Orders" })).not.toHaveAttribute("title");

    await user.click(screen.getByRole("button", { name: "Collapse sidebar" }));

    expect(screen.getByRole("button", { name: "Expand sidebar" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    // Labels remain available to assistive technology and as tooltips.
    expect(within(nav).getByRole("link", { name: "Orders" })).toHaveAttribute("title", "Orders");
    first.unmount();

    render(<AppShell>content</AppShell>);
    expect(await screen.findByRole("button", { name: "Expand sidebar" })).toBeInTheDocument();
  });
});

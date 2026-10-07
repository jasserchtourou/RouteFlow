import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { EventsView } from "@/features/ops/events-view";
import { OrdersView } from "@/features/ops/orders-view";
import { RoutesView } from "@/features/ops/routes-view";
import {
  OPEN_STATUSES,
  ShipmentsView,
  selectedStatuses,
  statusParam,
} from "@/features/ops/shipments-view";
import { feedEvent, mockBackend, order, page, route, shipment } from "./fixtures/ops";
import { currentUrl, setUrl } from "./helpers/navigation";

vi.mock("next/navigation", async () => (await import("./helpers/navigation")).navigationMock);
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

function renderView(ui: React.ReactElement, path: string) {
  setUrl(path);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

afterEach(() => vi.unstubAllGlobals());

/** The table appears with placeholder rows first; wait until real rows have replaced them. */
async function loadedTable(name: string | RegExp) {
  const table = await screen.findByRole("table", { name });
  await waitFor(() => expect(table.querySelector(".animate-pulse")).toBeNull());
  return table;
}

describe("Orders", () => {
  const orders = Array.from({ length: 20 }, (_, i) => order(i + 1));
  const backend = () =>
    mockBackend({
      "/orders": () => page(orders, 45),
      "/orders/by-number/ORD-10003": () =>
        order(3, { priority: "URGENT", customer_name: "Elbe Fresh" }),
      "/shipments": () => page([shipment(3, { is_delayed: true, delay_minutes: 40 })]),
    });

  it("lists orders with their status and priority", async () => {
    backend();
    renderView(<OrdersView />, "/orders");
    const table = await loadedTable("Orders");
    expect(within(table).getByText("ORD-10001")).toBeInTheDocument();
    expect(within(table).getAllByText("Confirmed")).toHaveLength(20);
    expect(screen.getByText("1–20 of 45")).toBeInTheDocument();
  });

  it("keeps filters in the URL and sends them to the API", async () => {
    const api = backend();
    const user = userEvent.setup();
    renderView(<OrdersView />, "/orders");
    await loadedTable("Orders");

    await user.click(screen.getByRole("button", { name: "Urgent" }));
    await waitFor(() =>
      expect(api.last("/orders")?.searchParams.getAll("priority")).toEqual(["URGENT"]),
    );
    expect(currentUrl().searchParams.get("priority")).toBe("URGENT");
    expect(screen.getByRole("button", { name: "Urgent" })).toHaveAttribute("aria-pressed", "true");

    await user.type(screen.getByRole("searchbox", { name: "Search orders" }), "elbe");
    await waitFor(() => expect(api.last("/orders")?.searchParams.get("search")).toBe("elbe"));
    expect(currentUrl().searchParams.get("q")).toBe("elbe");

    await user.click(screen.getByRole("button", { name: "Clear search" }));
    await waitFor(() => expect(currentUrl().searchParams.get("q")).toBeNull());
  });

  it("restores filters from a shared link", async () => {
    const api = backend();
    renderView(<OrdersView />, "/orders?status=PENDING,SHIPPED&q=calenberg&sort=-priority");
    await loadedTable("Orders");
    const query = api.last("/orders")!.searchParams;
    expect(query.getAll("status")).toEqual(["PENDING", "SHIPPED"]);
    expect(query.get("search")).toBe("calenberg");
    expect(query.get("sort")).toBe("-priority");
    expect(screen.getByRole("button", { name: "Pending" })).toHaveAttribute("aria-pressed", "true");
  });

  it("sorts by a column and flips the direction on the second click", async () => {
    const api = backend();
    const user = userEvent.setup();
    renderView(<OrdersView />, "/orders");
    await loadedTable("Orders");

    const header = () => screen.getByRole("columnheader", { name: /Customer/ });
    expect(header()).toHaveAttribute("aria-sort", "none");

    await user.click(within(header()).getByRole("button"));
    await waitFor(() =>
      expect(api.last("/orders")?.searchParams.get("sort")).toBe("customer_name"),
    );
    expect(header()).toHaveAttribute("aria-sort", "ascending");

    await user.click(within(header()).getByRole("button"));
    await waitFor(() =>
      expect(api.last("/orders")?.searchParams.get("sort")).toBe("-customer_name"),
    );
    expect(header()).toHaveAttribute("aria-sort", "descending");
  });

  it("pages through the results", async () => {
    const api = backend();
    const user = userEvent.setup();
    renderView(<OrdersView />, "/orders");
    await screen.findByText("1–20 of 45");
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Next page" }));
    await waitFor(() => expect(api.last("/orders")?.searchParams.get("offset")).toBe("20"));
    expect(currentUrl().searchParams.get("page")).toBe("2");
    expect(await screen.findByText("21–40 of 45")).toBeInTheDocument();
  });

  it("opens a detail panel with the order's shipments, and closes it with Escape", async () => {
    backend();
    const user = userEvent.setup();
    renderView(<OrdersView />, "/orders");
    await loadedTable("Orders");

    await user.click(screen.getByRole("button", { name: "ORD-10003" }));

    const panel = await screen.findByRole("complementary", { name: "ORD-10003 details" });
    expect(currentUrl().searchParams.get("open")).toBe("ORD-10003");
    expect(await within(panel).findByText("Elbe Fresh")).toBeInTheDocument();
    expect(await within(panel).findByText("SHP-2203")).toBeInTheDocument();
    expect(within(panel).getByText(/Late/)).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await waitFor(() => expect(currentUrl().searchParams.get("open")).toBeNull());
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("shows an empty state, and an error with a working retry", async () => {
    mockBackend({ "/orders": () => page([]) });
    const first = renderView(<OrdersView />, "/orders?q=zzz");
    expect(await screen.findByText("No orders match these filters")).toBeInTheDocument();
    expect(screen.getByText("No results")).toBeInTheDocument();
    first.unmount();

    let failing = true;
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          failing
            ? Response.json({ error: { message: "Database down" } }, { status: 503 })
            : Response.json(page(orders, 20)),
        ),
      ),
    );
    const user = userEvent.setup();
    renderView(<OrdersView />, "/orders");
    expect(await screen.findByRole("alert")).toHaveTextContent("Database down");
    failing = false;
    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(await loadedTable("Orders")).toBeInTheDocument();
  });
});

describe("Shipments", () => {
  const rows = [
    shipment(1, {
      is_delayed: true,
      delay_minutes: 95,
      active_exception_count: 2,
      temperature_status: "NORMAL",
    }),
    shipment(2),
  ];
  const backend = () =>
    mockBackend({
      "/shipments": () => page(rows),
      "/shipments/by-number/SHP-2201": () => ({
        ...rows[0],
        active_exceptions: [
          {
            id: "x1",
            type: "DELAYED",
            severity: "HIGH",
            status: "OPEN",
            description: "Traffic jam",
            created_at: "2026-10-07T10:00:00Z",
          },
        ],
      }),
      "/shipments/s1/tracking": () => [
        {
          id: "t1",
          event_type: "DEPARTED",
          location: "Hannover",
          occurred_at: "2026-10-07T08:00:00Z",
          details: {},
        },
        {
          id: "t2",
          event_type: "DELAY_REPORTED",
          location: "A2",
          occurred_at: "2026-10-07T09:00:00Z",
          details: { delay_minutes: 95 },
        },
      ],
    });

  it("shows open shipments by default, and the URL helpers agree", async () => {
    const api = backend();
    renderView(<ShipmentsView />, "/shipments");
    await loadedTable("Shipments");
    expect(api.last("/shipments")!.searchParams.getAll("status")).toEqual(OPEN_STATUSES);
    expect(screen.getByRole("button", { name: "Delivered" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByRole("button", { name: "In transit" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    expect(selectedStatuses(null)).toEqual(OPEN_STATUSES);
    expect(selectedStatuses("all")).toEqual([]);
    expect(selectedStatuses("DELIVERED,CREATED")).toEqual(["DELIVERED", "CREATED"]);
    expect(statusParam(OPEN_STATUSES)).toBeNull();
    expect(statusParam([])).toBe("all");
    expect(statusParam(["DELIVERED"])).toBe("DELIVERED");
  });

  it("adds Delivered to the filter, and sends no filter when everything is deselected", async () => {
    const api = backend();
    const user = userEvent.setup();
    renderView(<ShipmentsView />, "/shipments?status=all");
    await loadedTable("Shipments");
    expect(api.last("/shipments")!.searchParams.getAll("status")).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Delivered" }));
    await waitFor(() =>
      expect(api.last("/shipments")?.searchParams.getAll("status")).toEqual(["DELIVERED"]),
    );
  });

  it("filters delayed shipments and shipments with exceptions", async () => {
    const api = backend();
    const user = userEvent.setup();
    renderView(<ShipmentsView />, "/shipments");
    await loadedTable("Shipments");

    await user.click(screen.getByRole("button", { name: "Delayed only" }));
    await waitFor(() => expect(api.last("/shipments")?.searchParams.get("delayed")).toBe("true"));
    await user.click(screen.getByRole("button", { name: "With exceptions" }));
    await waitFor(() =>
      expect(api.last("/shipments")?.searchParams.get("has_active_exception")).toBe("true"),
    );
  });

  it("marks late, cold-chain and problem shipments in the table", async () => {
    backend();
    renderView(<ShipmentsView />, "/shipments");
    const table = await loadedTable("Shipments");
    expect(within(table).getByText("+1 h 35 min")).toBeInTheDocument();
    expect(within(table).getByLabelText("Cold chain")).toBeInTheDocument();
    expect(within(table).getByText(/open exceptions/)).toBeInTheDocument();
  });

  it("opens the tracking history and the open exceptions of a shipment", async () => {
    backend();
    const user = userEvent.setup();
    renderView(<ShipmentsView />, "/shipments");
    await loadedTable("Shipments");

    await user.click(screen.getByRole("button", { name: /SHP-2201/ }));

    const panel = await screen.findByRole("complementary", { name: "SHP-2201 details" });
    expect(await within(panel).findByText("Traffic jam")).toBeInTheDocument();
    expect(within(panel).getByText("Delay reported")).toBeInTheDocument();
    expect(within(panel).getByText("+95 min")).toBeInTheDocument();
    // Newest event first.
    const events = within(panel).getAllByRole("listitem");
    expect(events[events.length - 2]).toHaveTextContent("Delay reported");
  });
});

describe("Routes", () => {
  const rows = [
    route(1),
    route(2, {
      route_number: "RTE-105",
      risk: { score: 100, level: "CRITICAL", factors: [] },
      status: "DELAYED",
    }),
  ];
  const backend = () =>
    mockBackend({
      "/routes": () => page(rows),
      "/routes/at-risk": () => [rows[1]],
      "/routes/by-number/RTE-101": () => ({
        ...rows[0],
        shipments: [shipment(1, { is_delayed: true, delay_minutes: 95 })],
      }),
    });

  it("lists routes with their risk score and late shipments", async () => {
    backend();
    renderView(<RoutesView />, "/routes");
    const table = await loadedTable("Routes");
    expect(within(table).getAllByRole("meter")[0]).toHaveAttribute("aria-valuenow", "62");
    expect(within(table).getByText("High")).toBeInTheDocument();
    expect(within(table).getAllByText("2 late")).toHaveLength(2);
  });

  it("explains a route's risk score in the detail panel", async () => {
    backend();
    const user = userEvent.setup();
    renderView(<RoutesView />, "/routes");
    await loadedTable("Routes");

    await user.click(screen.getByRole("button", { name: "RTE-101" }));

    const panel = await screen.findByRole("complementary", { name: "RTE-101 details" });
    expect(await within(panel).findByText("2 delayed shipments")).toBeInTheDocument();
    expect(within(panel).getByText("Worst delay 95 min")).toBeInTheDocument();
    expect(within(panel).getByText("SHP-2201")).toBeInTheDocument();
  });

  it("switches to the ranked view and changes the minimum level", async () => {
    const api = backend();
    const user = userEvent.setup();
    renderView(<RoutesView />, "/routes");
    await loadedTable("Routes");

    await user.click(screen.getByRole("tab", { name: "Highest risk first" }));

    expect(await loadedTable("Routes ranked by risk")).toBeInTheDocument();
    await waitFor(() =>
      expect(api.last("/routes/at-risk")?.searchParams.get("min_level")).toBe("MEDIUM"),
    );
    expect(currentUrl().searchParams.get("view")).toBe("risk");

    await user.click(screen.getByRole("button", { name: "Critical" }));
    await waitFor(() =>
      expect(api.last("/routes/at-risk")?.searchParams.get("min_level")).toBe("CRITICAL"),
    );
  });

  it("filters the full list by status and planned risk", async () => {
    const api = backend();
    const user = userEvent.setup();
    renderView(<RoutesView />, "/routes");
    await loadedTable("Routes");

    await user.click(screen.getByRole("button", { name: "Delayed" }));
    await waitFor(() =>
      expect(api.last("/routes")?.searchParams.getAll("status")).toEqual(["DELAYED"]),
    );
    await user.click(screen.getByRole("button", { name: "High" }));
    await waitFor(() =>
      expect(api.last("/routes")?.searchParams.getAll("planned_risk_level")).toEqual(["HIGH"]),
    );
  });
});

describe("Events", () => {
  const events = [
    feedEvent(1, { event_type: "DELAY_REPORTED", details: { delay_minutes: 95 } }),
    feedEvent(2, { event_type: "TEMPERATURE_ALERT", details: { temperature_c: 11.2 } }),
    feedEvent(3),
  ];

  it("shows the feed with readable details and links to the shipment", async () => {
    mockBackend({ "/events": () => page(events) });
    renderView(<EventsView />, "/events");
    const table = await loadedTable(/Tracking events/);
    expect(within(table).getByText("+95 min")).toBeInTheDocument();
    expect(within(table).getByText("11.2 °C")).toBeInTheDocument();
    expect(within(table).getAllByText("5 min ago")).toHaveLength(3);
    expect(within(table).getByRole("link", { name: "SHP-2201" })).toHaveAttribute(
      "href",
      "/shipments?open=SHP-2201",
    );
    expect(screen.getByText(/Live · updated/)).toBeInTheDocument();
  });

  it("filters by event type and time range", async () => {
    const api = mockBackend({ "/events": () => page(events) });
    const user = userEvent.setup();
    renderView(<EventsView />, "/events");
    await loadedTable(/Tracking events/);

    await user.click(screen.getByRole("button", { name: "Delay reported" }));
    await waitFor(() =>
      expect(api.last("/events")?.searchParams.getAll("event_type")).toEqual(["DELAY_REPORTED"]),
    );

    await user.click(screen.getByRole("button", { name: "Last hour" }));
    await waitFor(() => expect(api.last("/events")?.searchParams.get("since")).toBeTruthy());
    const since = new Date(api.last("/events")!.searchParams.get("since")!).getTime();
    expect(Date.now() - since).toBeGreaterThan(59 * 60_000);
    expect(Date.now() - since).toBeLessThan(62 * 60_000);
    expect(screen.getByRole("button", { name: "Last hour" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("says so when the feed is empty or the connection drops", async () => {
    mockBackend({ "/events": () => page([]) });
    renderView(<EventsView />, "/events");
    expect(await screen.findByText("No events match these filters")).toBeInTheDocument();
  });
});

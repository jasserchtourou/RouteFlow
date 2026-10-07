import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AppShell } from "@/components/layout/app-shell";

vi.mock("next/navigation", () => ({ usePathname: () => "/shipments/SHP-2211" }));

describe("AppShell", () => {
  it("marks the current section as active and renders the page content", () => {
    render(
      <AppShell>
        <p>page body</p>
      </AppShell>,
    );
    expect(screen.getByText("page body")).toBeInTheDocument();
    const active = screen.getAllByRole("link", { name: "Shipments" })[0];
    expect(active).toHaveAttribute("aria-current", "page");
    expect(screen.getAllByRole("link", { name: "Orders" })[0]).not.toHaveAttribute("aria-current");
  });

  it("opens and closes the mobile navigation drawer", async () => {
    const user = userEvent.setup();
    render(<AppShell>content</AppShell>);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open navigation" }));
    expect(screen.getByRole("dialog", { name: "Navigation" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close navigation" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Panel } from "@/components/ui/panel";
import { useStoredState } from "@/hooks/use-stored-state";

function Demo({ defaultOpen = true }: { defaultOpen?: boolean }) {
  return (
    <Panel id="demo" title="Metrics" summary="52,800 pallets" defaultOpen={defaultOpen}>
      <button>inside</button>
    </Panel>
  );
}

describe("Panel", () => {
  it("is a disclosure button that collapses and expands its content", async () => {
    const user = userEvent.setup();
    render(<Demo />);
    const toggle = screen.getByRole("button", { name: /Metrics/ });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: "inside" })).toBeVisible();

    await user.click(toggle);

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    // Collapsed content is inert: it cannot be reached with the keyboard.
    expect(screen.getByRole("button", { name: "inside" }).closest("[inert]")).not.toBeNull();
    // ...and the header shows a one-line digest instead.
    expect(screen.getByText("52,800 pallets")).toBeInTheDocument();

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: "inside" }).closest("[inert]")).toBeNull();
  });

  it("shows the digest only while collapsed", async () => {
    const user = userEvent.setup();
    render(<Demo />);
    expect(screen.queryByText("52,800 pallets")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Metrics/ }));
    expect(screen.getByText("52,800 pallets")).toBeInTheDocument();
  });

  it("remembers its state for the next visit", async () => {
    const user = userEvent.setup();
    const first = render(<Demo />);
    await user.click(screen.getByRole("button", { name: /Metrics/ }));
    first.unmount();

    render(<Demo />);
    expect(await screen.findByRole("button", { name: /Metrics/ })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("starts collapsed when asked to", () => {
    render(<Demo defaultOpen={false} />);
    expect(screen.getByRole("button", { name: /Metrics/ })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });
});

describe("useStoredState", () => {
  function Probe() {
    const [value, setValue] = useStoredState("probe", "a");
    return <button onClick={() => setValue("b")}>{value}</button>;
  }

  it("falls back to the default when storage holds garbage", async () => {
    window.localStorage.setItem("routeflow:probe", "{not json");
    render(<Probe />);
    expect(screen.getByRole("button")).toHaveTextContent("a");
  });

  it("keeps working when storage cannot be written", async () => {
    const user = userEvent.setup();
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = () => {
      throw new Error("blocked");
    };
    try {
      render(<Probe />);
      await user.click(screen.getByRole("button"));
      expect(screen.getByRole("button")).toHaveTextContent("b");
    } finally {
      Storage.prototype.setItem = original;
    }
  });
});

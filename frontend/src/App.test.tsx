import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("findings workbench", () => {
  it("shows the findings summary and synthetic data label", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Findings overview" })).toBeInTheDocument();
    expect(screen.getByText("Synthetic data")).toBeInTheDocument();
    expect(screen.getByText("Total findings").parentElement?.parentElement).toHaveTextContent("6");
  });

  it("filters the table by status", () => {
    render(<App />);

    fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: "investigating" } });

    const table = screen.getAllByRole("table")[0];
    expect(within(table).getByText("Storage policy allows public access")).toBeInTheDocument();
    expect(within(table).getByText("Unusual API activity from a new region")).toBeInTheDocument();
    expect(within(table).queryByText("Repeated failed console sign-ins")).not.toBeInTheDocument();
  });

  it("opens a finding investigation panel", () => {
    render(<App />);

    fireEvent.click(
      within(screen.getAllByRole("table")[0]).getByRole("button", {
        name: "View Repeated failed console sign-ins",
      }),
    );

    const dialog = screen.getByRole("dialog", { name: "Investigation" });
    expect(within(dialog).getByRole("heading", { name: "Repeated failed console sign-ins" })).toBeInTheDocument();
    expect(within(dialog).getByText("Twenty-three failed sign-in attempts across three fabricated source addresses in eight minutes.")).toBeInTheDocument();
  });
});

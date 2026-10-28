import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("Milestone 1 UI shell", () => {
  it("shows the project name and states that workflows are not implemented", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Cloud Security Findings Tracker" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/planned for later milestones/i)).toBeInTheDocument();
  });
});


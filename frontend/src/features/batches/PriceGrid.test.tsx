import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PriceGrid } from "./PriceGrid";
import { buildBatch, buildExtractedPlan, buildIssue, buildPrice } from "./reviewFixtures";
import { buildCellKey, buildSeverityIndex } from "./reviewModel";

function renderGrid(overrides: Partial<Parameters<typeof PriceGrid>[0]> = {}) {
  const batch = buildBatch({
    plans: [
      buildExtractedPlan({
        prices: [
          buildPrice(),
          buildPrice({ age_band: 7, band_label: "44–48", raw_text: "R$ 878,13", final_value: "878.13", previous_value: "716.88", change: "0.2249" }),
        ],
      }),
    ],
  });
  const props = {
    batch,
    severity: buildSeverityIndex([buildIssue({ age_band: 7 })]),
    highlightedCell: null,
    canEdit: true,
    onSelectCell: vi.fn(),
    onMapPlan: vi.fn(),
    onToggleExclusion: vi.fn(),
    ...overrides,
  };
  render(<PriceGrid {...props} />);
  return props;
}

describe("PriceGrid", () => {
  beforeAll(() => {
    Element.prototype.scrollIntoView = vi.fn();
  });

  it("shows the new value, the previous one and the change", () => {
    renderGrid();

    expect(screen.getByText("R$ 878,13")).toBeInTheDocument();
    expect(screen.getByText("R$ 716,88").tagName).toBe("S");
    expect(screen.getByTitle(/antes R\$ 716,88/)).toBeInTheDocument();
    expect(screen.getByText("+22,49%")).toBeInTheDocument();
  });

  it("marks cells with open issues", () => {
    renderGrid();

    const flagged = screen.getByRole("button", { name: /^Essencial Enfermaria, faixa 44–48/ }).closest("td");
    expect(flagged).toHaveClass("tone-warning");
  });

  it("names each cell with its plan, band, value, previous value and severity", () => {
    renderGrid();

    expect(
      screen.getByRole("button", {
        // Intl separates the currency symbol with a no-break space, hence \s.
        name: /^Essencial Enfermaria, faixa 44–48: R\$\s878,13\. antes R\$\s716,88 \(\+22,49%\)\. Alerta$/,
      }),
    ).toBeInTheDocument();
  });

  it("opens the cell details on click", async () => {
    const props = renderGrid({ highlightedCell: buildCellKey("plan-a", 7) });

    await userEvent.click(screen.getByRole("button", { name: /^Essencial Enfermaria, faixa 44–48/ }));

    expect(props.onSelectCell).toHaveBeenCalledWith(
      expect.objectContaining({ id: "plan-a" }),
      expect.objectContaining({ age_band: 7 }),
    );
  });

  it("hides editing actions from read-only reviewers", () => {
    renderGrid({ canEdit: false });

    expect(screen.queryByRole("button", { name: /Mapear/ })).not.toBeInTheDocument();
  });
});

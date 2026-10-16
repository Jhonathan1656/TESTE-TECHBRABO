import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { PageHeader } from "./PageHeader";

describe("PageHeader", () => {
  it("names the browser tab after the page", () => {
    render(
      <MemoryRouter>
        <PageHeader title="Fila de revisão" />
      </MemoryRouter>,
    );

    expect(document.title).toBe("Fila de revisão · Central de Dados");
    expect(screen.getByRole("heading", { level: 1, name: "Fila de revisão" })).toBeInTheDocument();
  });

  it("renders the trail with the current page marked", () => {
    render(
      <MemoryRouter>
        <PageHeader title="Lote de Vida Plena" breadcrumbs={[{ label: "Fila de revisão", to: "/batches" }]} />
      </MemoryRouter>,
    );

    const trail = screen.getByRole("navigation", { name: "Você está em" });
    expect(trail).toContainElement(screen.getByRole("link", { name: "Fila de revisão" }));
    expect(screen.getByText("Lote de Vida Plena", { selector: "[aria-current='page']" })).toBeInTheDocument();
  });
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { batchApi } from "../../shared/api/endpoints";
import { BatchListPage } from "./BatchListPage";

vi.mock("../../shared/api/endpoints", () => ({
  batchApi: { list: vi.fn().mockResolvedValue([]) },
}));

function renderAt(url: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[url]}>
        <BatchListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("BatchListPage", () => {
  beforeEach(() => vi.mocked(batchApi.list).mockClear());

  it("reads the status filter from the URL", async () => {
    renderAt("/batches?status=published");

    expect(await screen.findByText("Nenhum lote nesta situação.")).toBeInTheDocument();
    expect(batchApi.list).toHaveBeenCalledWith("published");
    expect(screen.getByRole("link", { name: "Publicados" })).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("link", { name: "Aguardando revisão" })).not.toHaveAttribute("aria-current");
  });

  it("defaults to the batches waiting for review", async () => {
    renderAt("/batches");

    await screen.findByText("Nenhum lote nesta situação.");
    expect(batchApi.list).toHaveBeenCalledWith("pending_review");
    expect(screen.getByRole("link", { name: "Aguardando revisão" })).toHaveAttribute("href", "/batches");
  });
});

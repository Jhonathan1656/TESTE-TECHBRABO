import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Dialog } from "./Dialog";

describe("Dialog", () => {
  it("is named by its title and described by its description", () => {
    render(
      <Dialog open title="Rejeitar lote" description="O lote não chega ao cotador." onClose={vi.fn()}>
        <p>conteúdo</p>
      </Dialog>,
    );

    const dialog = screen.getByRole("dialog", { name: "Rejeitar lote" });
    expect(dialog).toHaveAccessibleDescription("O lote não chega ao cotador.");
  });

  it("offers a labelled close button besides cancel", async () => {
    const onClose = vi.fn();
    render(<Dialog open title="Aceitar alerta" onSubmit={vi.fn()} onClose={onClose} />);

    await userEvent.click(screen.getByRole("button", { name: "Fechar" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("disables the submit button and shows progress while busy", () => {
    render(<Dialog open busy title="Publicar no cotador" submitLabel="Aprovar e publicar" onSubmit={vi.fn()} onClose={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Processando…" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Aprovar e publicar" })).not.toBeInTheDocument();
  });
});

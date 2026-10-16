import { render } from "@testing-library/react";
import { createElement } from "react";

import { t, tEnum, tList, tRich } from "./translate";

describe("translate", () => {
  it("interpolates named parameters", () => {
    expect(t("batches.errorsCount", { count: 2 })).toBe("2 erro(s)");
  });

  it("returns the key when a message is missing", () => {
    expect(t("missing.key")).toBe("missing.key");
  });

  it("translates enum values and falls back to the raw value", () => {
    expect(tEnum("freshness", "overdue")).toBe("Desatualizada");
    expect(tEnum("freshness", "unexpected")).toBe("unexpected");
    expect(tEnum("freshness", null)).toBe("—");
  });

  it("translates enum values that contain dots", () => {
    expect(tEnum("auditAction", "batch.published")).toBe("Lote publicado");
  });

  it("interpolates React nodes without breaking the sentence", () => {
    const parts = tRich("auth.demoHint", {
      analyst: createElement("code", null, "analista"),
      reviewer: createElement("code", null, "revisor"),
      variable: createElement("code", null, "DEMO_PASSWORD"),
      password: createElement("code", null, "cotador-demo"),
    });
    const { container } = render(createElement("p", null, parts));

    expect(container.querySelectorAll("code")).toHaveLength(4);
    expect(container.textContent).toBe(
      "Entre como analista ou revisor. A senha é a definida em DEMO_PASSWORD (padrão cotador-demo).",
    );
  });

  it("reads lists", () => {
    expect(tList("upload.howSteps")).toHaveLength(4);
  });
});

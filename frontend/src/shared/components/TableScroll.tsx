import type { ReactNode } from "react";

import { t } from "../i18n/translate";

/**
 * Horizontal scroll container for wide tables. It is focusable and named, so keyboard users can
 * scroll it with the arrow keys and screen readers announce what the region holds (WCAG 2.1.1).
 */
export function TableScroll({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="table-wrap" role="region" aria-label={t("common.tableRegion", { name: label })} tabIndex={0}>
      {children}
    </div>
  );
}

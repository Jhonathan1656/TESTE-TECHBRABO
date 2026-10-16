import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { t } from "../i18n/translate";

export interface Crumb {
  label: string;
  to: string;
}

interface PageHeaderProps {
  title: string;
  /** Status shown next to the title (e.g. the batch status badge). */
  status?: ReactNode;
  subtitle?: ReactNode;
  /** Ancestors of the current page; the page itself is appended as the last, current crumb. */
  breadcrumbs?: Crumb[];
  actions?: ReactNode;
}

export function PageHeader({ title, status, subtitle, breadcrumbs, actions }: PageHeaderProps) {
  return (
    <header className="page-header">
      {/* React 19 hoists <title> into <head>; each page names the browser tab and history entry. */}
      <title>{t("app.documentTitle", { page: title })}</title>
      <div className="page-heading">
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="breadcrumbs" aria-label={t("nav.breadcrumb")}>
            <ol>
              {breadcrumbs.map((crumb) => (
                <li key={crumb.to}>
                  <Link to={crumb.to}>{crumb.label}</Link>
                </li>
              ))}
              <li>
                <span aria-current="page">{title}</span>
              </li>
            </ol>
          </nav>
        )}
        <div className="page-title-row">
          <h1 className="page-title">{title}</h1>
          {status}
        </div>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

import { useQuery } from "@tanstack/react-query";
import {
  Calculator,
  CheckCheck,
  FileUp,
  Inbox,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  RadioTower,
  X,
} from "lucide-react";
import { type ReactNode, Suspense, useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { batchApi } from "../../shared/api/endpoints";
import { useAuth } from "../../shared/auth/AuthContext";
import { Button } from "../../shared/components/Button";
import { LoadingState } from "../../shared/components/States";
import { t } from "../../shared/i18n/translate";

const SIDEBAR_ID = "app-sidebar";
const MAIN_ID = "main-content";

export function AppLayout() {
  const { user, signOut } = useAuth();
  const pending = useQuery({
    queryKey: ["batches", "pending_review"],
    queryFn: () => batchApi.list("pending_review"),
  });
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const mainRef = useFocusMainOnNavigation();

  useEffect(() => {
    if (!menuOpen) {
      return;
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [menuOpen]);

  const closeMenu = () => setMenuOpen(false);

  return (
    <>
      <a className="skip-link" href={`#${MAIN_ID}`}>
        {t("app.skipToContent")}
      </a>
      <div className="app-shell">
        <header className="topbar">
          <Brand onNavigate={closeMenu} />
          <Button
            ref={menuButtonRef}
            variant="ghost"
            icon={menuOpen ? <X size={20} /> : <Menu size={20} />}
            aria-label={menuOpen ? t("nav.closeMenu") : t("nav.openMenu")}
            aria-expanded={menuOpen}
            aria-controls={SIDEBAR_ID}
            onClick={() => setMenuOpen((open) => !open)}
          />
        </header>
        {menuOpen && <div className="nav-scrim" aria-hidden="true" onClick={closeMenu} />}
        <aside id={SIDEBAR_ID} className="sidebar" data-open={menuOpen}>
          <Brand onNavigate={closeMenu} />
          <nav className="nav" aria-label={t("nav.primary")}>
            <NavGroup title={t("nav.sectionOperations")}>
              <NavItem to="/" icon={<LayoutDashboard size={18} />} label={t("nav.dashboard")} end onNavigate={closeMenu} />
              <NavItem
                to="/batches"
                icon={<Inbox size={18} />}
                label={t("nav.batches")}
                count={pending.data?.length}
                onNavigate={closeMenu}
              />
              <NavItem to="/upload" icon={<FileUp size={18} />} label={t("nav.upload")} onNavigate={closeMenu} />
              <NavItem to="/sources" icon={<RadioTower size={18} />} label={t("nav.sources")} onNavigate={closeMenu} />
            </NavGroup>
            <NavGroup title={t("nav.sectionData")}>
              <NavItem to="/quote" icon={<Calculator size={18} />} label={t("nav.quote")} onNavigate={closeMenu} />
              <NavItem to="/plans" icon={<ListChecks size={18} />} label={t("nav.plans")} onNavigate={closeMenu} />
            </NavGroup>
          </nav>
          <div className="sidebar-footer">
            {user && (
              <div className="user-card">
                <span className="avatar" aria-hidden="true">
                  {initialsOf(user.display_name)}
                </span>
                <div className="user-meta">
                  <span className="user-name">{user.display_name}</span>
                  <span className="user-roles">{user.roles.map((role) => t(`roles.${role}`)).join(" · ")}</span>
                </div>
              </div>
            )}
            <div>
              <Button variant="ghost" size="sm" icon={<LogOut size={15} />} onClick={() => void signOut()}>
                {t("nav.logout")}
              </Button>
            </div>
          </div>
        </aside>
        <main id={MAIN_ID} ref={mainRef} className="main" tabIndex={-1}>
          <div className="main-inner">
            <Suspense fallback={<LoadingState lines={6} />}>
              <Outlet />
            </Suspense>
          </div>
        </main>
      </div>
    </>
  );
}

/** Moves focus to the main region after client-side navigation, so screen readers announce the new page. */
function useFocusMainOnNavigation() {
  const { pathname } = useLocation();
  const mainRef = useRef<HTMLElement>(null);
  const previousPathname = useRef(pathname);

  useEffect(() => {
    if (previousPathname.current === pathname) {
      return;
    }
    previousPathname.current = pathname;
    mainRef.current?.focus();
  }, [pathname]);

  return mainRef;
}

function Brand({ onNavigate }: { onNavigate: () => void }) {
  return (
    <Link to="/" className="brand" onClick={onNavigate}>
      <span className="brand-mark" aria-hidden="true">
        <CheckCheck size={18} />
      </span>
      <span>
        <span className="brand-name">{t("app.name")}</span>
        <span className="brand-product">{t("app.product")}</span>
      </span>
    </Link>
  );
}

function NavGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <p className="nav-group-title">{title}</p>
      <ul className="nav-list">{children}</ul>
    </div>
  );
}

interface NavItemProps {
  to: string;
  icon: ReactNode;
  label: string;
  count?: number;
  end?: boolean;
  onNavigate: () => void;
}

function NavItem({ to, icon, label, count, end, onNavigate }: NavItemProps) {
  return (
    <li>
      <NavLink to={to} end={end} className="nav-link" onClick={onNavigate}>
        <span aria-hidden="true" className="icon-text">
          {icon}
        </span>
        <span>{label}</span>
        {count ? (
          <>
            <span className="nav-count" aria-hidden="true">
              {count}
            </span>
            <span className="visually-hidden">{t("nav.pendingCount", { count })}</span>
          </>
        ) : null}
      </NavLink>
    </li>
  );
}

function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .filter((word) => /^\p{L}/u.test(word) && word.length > 2)
    .slice(0, 2)
    .map((word) => word[0].toLocaleUpperCase("pt-BR"))
    .join("");
}

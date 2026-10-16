import { CircleAlert, Inbox, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";

import { describeError } from "../api/errors";
import { t } from "../i18n/translate";
import { Button } from "./Button";

/** Skeleton placeholder: reserves space so content doesn't jump when data arrives. */
export function LoadingState({ label = t("common.loading"), lines = 4 }: { label?: string; lines?: number }) {
  return (
    <div className="skeleton-group" role="status" aria-live="polite">
      <span className="visually-hidden">{label}</span>
      {Array.from({ length: lines }, (_, index) => (
        <span key={index} className="skeleton" aria-hidden="true" />
      ))}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div className="state" role="alert">
      <span className="state-icon tone-error" aria-hidden="true">
        <CircleAlert size={20} />
      </span>
      <span className="state-title">{t("common.errorTitle")}</span>
      <span className="state-message">{describeError(error)}</span>
      {onRetry && (
        <div className="state-action">
          <Button icon={<RefreshCw size={15} />} onClick={onRetry}>
            {t("common.retry")}
          </Button>
        </div>
      )}
    </div>
  );
}

interface EmptyStateProps {
  title?: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}

export function EmptyState({ title, icon = <Inbox size={20} />, action, children }: EmptyStateProps) {
  return (
    <div className="state">
      <span className="state-icon" aria-hidden="true">
        {icon}
      </span>
      {title && <span className="state-title">{title}</span>}
      <span className="state-message">{children}</span>
      {action && <div className="state-action">{action}</div>}
    </div>
  );
}

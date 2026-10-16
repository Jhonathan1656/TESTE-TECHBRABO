import { CircleAlert, X } from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useId, useRef } from "react";

import { t } from "../i18n/translate";
import { Button } from "./Button";

interface DialogProps {
  open: boolean;
  title: string;
  description?: ReactNode;
  submitLabel?: string;
  submitVariant?: "primary" | "destructive";
  submitDisabled?: boolean;
  busy?: boolean;
  error?: string | null;
  onSubmit?: () => void;
  onClose: () => void;
  children?: ReactNode;
}

/**
 * Modal built on the native <dialog>: the browser provides the focus trap, Escape to close
 * and the inert background. Closed dialogs are not rendered at all, so the page never carries
 * empty, unnamed dialogs in its accessibility tree.
 */
export function Dialog(props: DialogProps) {
  return props.open ? <OpenDialog {...props} /> : null;
}

function OpenDialog({
  title,
  description,
  submitLabel = t("common.confirm"),
  submitVariant = "primary",
  submitDisabled = false,
  busy = false,
  error,
  onSubmit,
  onClose,
  children,
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const dialog = ref.current;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (dialog && !dialog.open) {
      dialog.showModal();
    }
    // The dialog unmounts instead of closing, so focus goes back to the trigger explicitly.
    return () => trigger?.focus();
  }, []);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit?.();
  };

  return (
    <dialog
      ref={ref}
      className="dialog"
      onClose={onClose}
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
    >
      <form className="dialog-form" onSubmit={handleSubmit} aria-busy={busy}>
        <div className="dialog-header">
          <div>
            <h2 id={titleId} className="dialog-title">
              {title}
            </h2>
            {description && (
              <p id={descriptionId} className="dialog-description">
                {description}
              </p>
            )}
          </div>
          <Button variant="ghost" size="sm" icon={<X size={18} />} aria-label={t("common.close")} onClick={onClose} />
        </div>
        <div className="dialog-body">
          {children}
          {error && (
            <div className="form-error" role="alert">
              <CircleAlert size={16} aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}
        </div>
        <div className="dialog-footer">
          <Button onClick={onClose}>{onSubmit ? t("common.cancel") : t("common.close")}</Button>
          {onSubmit && (
            <Button type="submit" variant={submitVariant} disabled={submitDisabled || busy}>
              {busy ? t("common.working") : submitLabel}
            </Button>
          )}
        </div>
      </form>
    </dialog>
  );
}

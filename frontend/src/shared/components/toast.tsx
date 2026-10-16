import { CircleAlert, CircleCheck, X } from "lucide-react";
import { createContext, type ReactNode, use, useCallback, useMemo, useState } from "react";

import { t } from "../i18n/translate";
import { Button } from "./Button";

type ToastTone = "neutral" | "error";

interface Toast {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastContextValue {
  notify: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue>({ notify: () => undefined });
const TOAST_DURATION_MS = 5000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const notify = useCallback(
    (message: string, tone: ToastTone = "neutral") => {
      const id = Date.now() + Math.random();
      setToasts((current) => [...current, { id, message, tone }]);
      setTimeout(() => dismiss(id), TOAST_DURATION_MS);
    },
    [dismiss],
  );

  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext value={value}>
      {children}
      {/* The live region exists before any toast, so screen readers announce additions without moving focus. */}
      <div className="toast-region" role="status" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast tone-${toast.tone}`}>
            {toast.tone === "error" ? (
              <CircleAlert size={18} aria-hidden="true" />
            ) : (
              <CircleCheck size={18} aria-hidden="true" />
            )}
            <span className="toast-message">{toast.message}</span>
            <Button
              variant="ghost"
              size="sm"
              icon={<X size={16} />}
              aria-label={t("common.dismiss")}
              onClick={() => dismiss(toast.id)}
            />
          </div>
        ))}
      </div>
    </ToastContext>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastContextValue {
  return use(ToastContext);
}

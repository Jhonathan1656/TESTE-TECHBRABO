import { type ReactNode, useId } from "react";

interface CardProps {
  title?: ReactNode;
  hint?: ReactNode;
  actions?: ReactNode;
  /** Removes the body padding for edge-to-edge tables and lists. */
  flush?: boolean;
  id?: string;
  className?: string;
  children: ReactNode;
}

/** A titled card is a `section` named by its heading, so screen readers can list and jump to it. */
export function Card({ title, hint, actions, flush = false, id, className, children }: CardProps) {
  const titleId = useId();
  return (
    <section id={id} className={["card", className].filter(Boolean).join(" ")} aria-labelledby={title ? titleId : undefined}>
      {(title || actions) && (
        <header className="card-header">
          <div className="card-heading">
            {title && (
              <h2 id={titleId} className="card-title">
                {title}
              </h2>
            )}
            {hint && <p className="card-hint">{hint}</p>}
          </div>
          {actions && <div className="row">{actions}</div>}
        </header>
      )}
      <div className={flush ? "card-body flush" : "card-body"}>{children}</div>
    </section>
  );
}

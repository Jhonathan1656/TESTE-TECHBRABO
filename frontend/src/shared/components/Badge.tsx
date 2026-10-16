import type { ReactNode } from "react";

import type { Tone } from "./tones";

interface BadgeProps {
  tone?: Tone;
  /** A leading status dot; the label text still carries the meaning, the dot only reinforces it. */
  dot?: boolean;
  icon?: ReactNode;
  title?: string;
  children: ReactNode;
}

export function Badge({ tone = "neutral", dot = false, icon, title, children }: BadgeProps) {
  const classes = ["badge", `tone-${tone}`, dot ? "badge-dot" : ""].filter(Boolean).join(" ");
  return (
    <span className={classes} title={title}>
      {icon && (
        <span aria-hidden="true" className="icon-text">
          {icon}
        </span>
      )}
      {children}
    </span>
  );
}

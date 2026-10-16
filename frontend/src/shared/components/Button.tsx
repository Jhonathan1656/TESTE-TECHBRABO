import type { ComponentProps, ReactNode } from "react";
import { Link, type LinkProps } from "react-router-dom";

/** `danger` is the outlined secondary-level destructive action; `destructive` confirms it. */
export type ButtonVariant = "primary" | "secondary" | "danger" | "destructive" | "ghost";
type ButtonSize = "md" | "sm";

interface ButtonStyleProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: "button-primary",
  secondary: "button-secondary",
  danger: "button-danger",
  destructive: "button-danger-solid",
  ghost: "button-ghost",
};

function buttonClasses(variant: ButtonVariant, size: ButtonSize, iconOnly: boolean, extra = ""): string {
  return ["button", VARIANT_CLASSES[variant], size === "sm" ? "button-sm" : "", iconOnly ? "button-icon" : "", extra]
    .filter(Boolean)
    .join(" ");
}

type ButtonProps = ButtonStyleProps & ComponentProps<"button">;

/** Icon-only buttons must receive an `aria-label`; the icon itself is always hidden from assistive tech. */
export function Button({
  variant = "secondary",
  size = "md",
  icon,
  className,
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button type={type} className={buttonClasses(variant, size, !children, className)} {...rest}>
      {icon && <ButtonIcon>{icon}</ButtonIcon>}
      {children}
    </button>
  );
}

type ButtonLinkProps = ButtonStyleProps & LinkProps;

/** Navigation styled as a button: keeps real link semantics (middle-click, open in new tab). */
export function ButtonLink({ variant = "secondary", size = "md", icon, className, children, ...rest }: ButtonLinkProps) {
  return (
    <Link className={buttonClasses(variant, size, !children, className)} {...rest}>
      {icon && <ButtonIcon>{icon}</ButtonIcon>}
      {children}
    </Link>
  );
}

function ButtonIcon({ children }: { children: ReactNode }) {
  return (
    <span aria-hidden="true" className="icon-text">
      {children}
    </span>
  );
}

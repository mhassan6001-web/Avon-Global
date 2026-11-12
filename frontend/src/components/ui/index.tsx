"use client";

/**
 * AVEN GLOBAL UI primitives. Each component is small, accessible by default
 * and styled only through design tokens (see globals.css).
 */

import { motion } from "framer-motion";
import {
  forwardRef,
  useId,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import styles from "./ui.module.css";

function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

/* ---------- Button ---------- */

type ButtonVariant = "primary" | "secondary" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: "md" | "sm";
  icon?: ReactNode;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", icon, loading, children, className, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={cx(
        styles.button,
        variant === "primary" && styles.primary,
        variant === "ghost" && styles.ghost,
        size === "sm" && styles.small,
        className,
      )}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Spinner size={14} label="Working" /> : icon}
      {children}
    </button>
  );
});

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  children: ReactNode;
  variant?: ButtonVariant;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, children, variant = "ghost", className, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      aria-label={label}
      title={label}
      className={cx(
        styles.button,
        styles.iconButton,
        variant === "ghost" && styles.ghost,
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
});

/* ---------- Panel ---------- */

interface PanelProps extends HTMLAttributes<HTMLElement> {
  title?: ReactNode;
  eyebrow?: ReactNode;
  actions?: ReactNode;
  as?: "section" | "div" | "article";
}

export function Panel({
  title,
  eyebrow,
  actions,
  children,
  className,
  as = "section",
  ...rest
}: PanelProps) {
  const headingId = useId();
  const Tag = as;
  return (
    <Tag
      className={cx(styles.panel, className)}
      aria-labelledby={title ? headingId : undefined}
      {...rest}
    >
      {(title || actions) && (
        <header className={styles.panelHeader}>
          <div>
            {eyebrow && <p className={styles.panelEyebrow}>{eyebrow}</p>}
            {title && (
              <h2 id={headingId} className={styles.panelTitle}>
                {title}
              </h2>
            )}
          </div>
          {actions}
        </header>
      )}
      <div className={styles.panelBody}>{children}</div>
    </Tag>
  );
}

/* ---------- Badge & status dot ---------- */

export type Tone = "neutral" | "gold" | "success" | "warning" | "danger" | "signal";

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={cx(styles.badge, tone !== "neutral" && styles[`badge_${tone}`])}>
      {children}
    </span>
  );
}

const DOT_CLASS: Record<Tone, string | undefined> = {
  neutral: styles.dot_neutral,
  gold: styles.dot_signal,
  success: styles.dot_ok,
  warning: styles.dot_warning,
  danger: styles.dot_danger,
  signal: styles.dot_signal,
};

export function StatusDot({ tone, live = false }: { tone: Tone; live?: boolean }) {
  return (
    <span aria-hidden="true" className={cx(styles.dot, DOT_CLASS[tone], live && styles.dot_live)} />
  );
}

/* ---------- Loading ---------- */

export function Skeleton({
  width = "100%",
  height = 14,
  className,
}: {
  width?: number | string;
  height?: number | string;
  className?: string;
}) {
  return (
    <span aria-hidden="true" className={cx(styles.skeleton, className)} style={{ width, height }} />
  );
}

export function Spinner({ size = 18, label = "Loading" }: { size?: number; label?: string }) {
  return (
    <span role="status" style={{ display: "inline-flex" }}>
      <span className={styles.spinner} style={{ width: size, height: size }} aria-hidden="true" />
      <span className="visually-hidden">{label}</span>
    </span>
  );
}

/* ---------- Empty state ---------- */

export function EmptyState({
  icon,
  title,
  children,
  action,
}: {
  icon?: ReactNode;
  title: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className={styles.empty}>
      {icon && (
        <span className={styles.emptyIcon} aria-hidden="true">
          {icon}
        </span>
      )}
      <p className={styles.emptyTitle}>{title}</p>
      {children && <p className={styles.emptyText}>{children}</p>}
      {action}
    </div>
  );
}

/* ---------- Page header ---------- */

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className={styles.pageHeader}>
      <div>
        {eyebrow && <p className={styles.pageEyebrow}>{eyebrow}</p>}
        <h1 className={styles.pageTitle}>{title}</h1>
        {description && <p className={styles.pageDescription}>{description}</p>}
      </div>
      {actions}
    </header>
  );
}

/* ---------- Segmented control (accessible radio group) ---------- */

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
}

export function SegmentedControl<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: ReadonlyArray<SegmentOption<T>>;
  onChange: (value: T) => void;
}) {
  const groupId = useId();
  const index = Math.max(
    0,
    options.findIndex((option) => option.value === value),
  );

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const delta =
      event.key === "ArrowRight" || event.key === "ArrowDown"
        ? 1
        : event.key === "ArrowLeft" || event.key === "ArrowUp"
          ? -1
          : 0;
    if (!delta) return;
    event.preventDefault();
    const next = options[(index + delta + options.length) % options.length];
    if (!next) return;
    onChange(next.value);
    const target = event.currentTarget.querySelector<HTMLButtonElement>(
      `[data-value="${next.value}"]`,
    );
    target?.focus();
  }

  return (
    <div role="radiogroup" aria-label={label} className={styles.segmented} onKeyDown={onKeyDown}>
      {options.map((option) => {
        const checked = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={checked}
            tabIndex={checked ? 0 : -1}
            data-value={option.value}
            className={styles.segment}
            onClick={() => onChange(option.value)}
          >
            {checked && (
              <motion.span
                layoutId={`${groupId}-thumb`}
                className={styles.segmentThumb}
                transition={{ type: "spring", stiffness: 500, damping: 40 }}
              />
            )}
            <span className={styles.segmentLabel}>{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}

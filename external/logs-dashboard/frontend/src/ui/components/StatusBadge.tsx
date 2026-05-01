import type { ReactNode } from "react";
import clsx from "clsx";

type Variant = "normal" | "warning" | "anomaly" | "muted";

const styles: Record<Variant, { bg: string; fg: string; dot: string }> = {
  normal: { bg: "rgba(52, 211, 153, 0.12)", fg: "var(--status-normal)", dot: "var(--status-normal)" },
  warning: { bg: "rgba(251, 191, 36, 0.12)", fg: "var(--status-warning)", dot: "var(--status-warning)" },
  anomaly: { bg: "rgba(248, 113, 113, 0.14)", fg: "var(--status-anomaly)", dot: "var(--status-anomaly)" },
  muted: { bg: "rgba(148, 163, 184, 0.1)", fg: "var(--text-muted)", dot: "var(--text-muted)" },
};

export function StatusBadge({
  variant,
  children,
  pulse = false,
}: {
  variant: Variant;
  children: ReactNode;
  pulse?: boolean;
}) {
  const s = styles[variant];

  return (
    <span className="status-badge" style={{ background: s.bg, color: s.fg }}>
      <span
        className={clsx("status-dot", pulse && "status-dot-pulse")}
        style={{ background: s.dot }}
      />
      {children}
    </span>
  );
}

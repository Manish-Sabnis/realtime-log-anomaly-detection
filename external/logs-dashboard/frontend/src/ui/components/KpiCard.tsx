import type { ReactNode } from "react";
import { StatusBadge } from "./StatusBadge";

export function KpiCard(props: {
  label: string;
  value: string;
  sublabel?: string;
  variant?: "normal" | "warning" | "anomaly" | "muted";
  accent?: string;
  children?: ReactNode;
}) {
  return (
    <div className="metric-card">
      <div className="metric-card-accent" style={{ background: props.accent ?? "var(--accent-blue)" }} />
      <div className="flex items-center justify-between gap-3">
        <div className="eyebrow">{props.label}</div>
        {props.variant ? <StatusBadge variant={props.variant}>{props.variant}</StatusBadge> : null}
      </div>
      <div className="mt-3 text-[30px] font-semibold leading-none tracking-tight">{props.value}</div>
      {props.sublabel ? (
        <div className="mt-2 min-h-4 text-[12px]" style={{ color: "var(--text-muted)" }}>
          {props.sublabel}
        </div>
      ) : null}
      {props.children ? <div className="mt-3">{props.children}</div> : null}
    </div>
  );
}

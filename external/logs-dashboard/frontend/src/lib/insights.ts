import type { ApiAnomaly, ApiLog, LogLevel, ServiceName } from "./api";

export const SERVICES: ServiceName[] = [
  "auth-service",
  "api-gateway",
  "payment-service",
  "notification-service",
];

export const LOG_LEVELS: LogLevel[] = ["ERROR", "WARN", "INFO", "DEBUG"];

export const serviceMeta: Record<ServiceName, { label: string; tone: string; short: string }> = {
  "auth-service": { label: "Auth", tone: "#60a5fa", short: "AUTH" },
  "api-gateway": { label: "Gateway", tone: "#a78bfa", short: "API" },
  "payment-service": { label: "Payment", tone: "#f59e0b", short: "PAY" },
  "notification-service": { label: "Notify", tone: "#34d399", short: "NTF" },
};

export function formatTime(value?: string) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(11, 19);
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export function formatWindow(anomaly?: Pick<ApiAnomaly, "window_start" | "window_end">) {
  if (!anomaly) return "--";
  return `${formatTime(anomaly.window_start)} - ${formatTime(anomaly.window_end)}`;
}

export function percent(value?: number, digits = 1) {
  if (typeof value !== "number" || Number.isNaN(value)) return "--";
  return `${(value * 100).toFixed(digits)}%`;
}

export function number(value?: number) {
  if (typeof value !== "number" || Number.isNaN(value)) return "--";
  return new Intl.NumberFormat().format(value);
}

export function latency(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) return "--";
  return `${Math.round(value)} ms`;
}

export function scoreTone(score?: number, isAnomalous?: boolean) {
  if (isAnomalous || (score ?? 0) >= 0.75) return "anomaly";
  if ((score ?? 0) >= 0.5) return "warning";
  return "normal";
}

export function summarizeLogs(logs: ApiLog[]) {
  const byService = new Map<ServiceName, ApiLog[]>();
  const byLevel = new Map<LogLevel, number>();

  for (const service of SERVICES) byService.set(service, []);
  for (const level of LOG_LEVELS) byLevel.set(level, 0);

  for (const log of logs) {
    byService.get(log.service_name)?.push(log);
    byLevel.set(log.log_level, (byLevel.get(log.log_level) ?? 0) + 1);
  }

  const serviceSummaries = SERVICES.map((service) => {
    const rows = byService.get(service) ?? [];
    const errors = rows.filter((log) => log.log_level === "ERROR").length;
    const warnings = rows.filter((log) => log.log_level === "WARN").length;
    const latencies = rows
      .map((log) => log.latency_ms)
      .filter((value): value is number => typeof value === "number");
    const avgLatency =
      latencies.length > 0 ? latencies.reduce((sum, value) => sum + value, 0) / latencies.length : 0;
    const topEvent = topBy(rows, (log) => log.event_type)[0]?.label ?? "--";

    return {
      service,
      total: rows.length,
      errors,
      warnings,
      errorRate: rows.length ? errors / rows.length : 0,
      avgLatency,
      topEvent,
    };
  });

  return {
    total: logs.length,
    errors: byLevel.get("ERROR") ?? 0,
    warnings: byLevel.get("WARN") ?? 0,
    byLevel,
    serviceSummaries,
  };
}

export function topBy<T>(items: T[], selector: (item: T) => string, limit = 5) {
  const counts = new Map<string, number>();
  for (const item of items) {
    const key = selector(item);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, limit);
}

export function bucketLogsByMinute(logs: ApiLog[]) {
  const buckets = new Map<string, { label: string; total: number; errors: number }>();

  for (const log of logs) {
    const date = new Date(log.timestamp);
    if (Number.isNaN(date.getTime())) continue;
    date.setSeconds(0, 0);
    const key = date.toISOString();
    const current = buckets.get(key) ?? {
      label: new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(date),
      total: 0,
      errors: 0,
    };
    current.total += 1;
    if (log.log_level === "ERROR") current.errors += 1;
    buckets.set(key, current);
  }

  return [...buckets.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, value]) => ({
      ...value,
      errorRate: value.total ? value.errors / value.total : 0,
    }));
}

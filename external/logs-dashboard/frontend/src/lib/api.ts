export type ApiStatus = {
  status: "ok";
  service: string;
  total_logs_stored: number;
};

export type ApiLog = {
  id: number;
  timestamp: string;
  service_name: ServiceName;
  host: string;
  log_level: LogLevel;
  event_type: string;
  message: string;
  user_id?: string | null;
  ip?: string | null;
  request_id?: string | null;
  latency_ms?: number | null;
  transaction_id?: string | null;
  amount?: number | null;
  currency?: string | null;
  channel?: string | null;
  recipient?: string | null;
  notification_id?: string | null;
  ingested_at: string;
};

export type LogLevel = "DEBUG" | "INFO" | "WARN" | "ERROR";

export type ServiceName =
  | "auth-service"
  | "api-gateway"
  | "payment-service"
  | "notification-service";

export type LogsFilters = {
  start?: string;
  end?: string;
  service?: ServiceName | "all";
  logLevel?: LogLevel | "all";
  limit?: number;
};

export type ApiLogsResponse = {
  count: number;
  logs: ApiLog[];
};

export type AnomalyTopPattern = {
  feature: string;
  label: string;
  deviation_ratio: number;
};

export type AnomalyMetrics = Record<string, unknown> & {
  baseline_error_rate?: number;
  current_error_rate?: number;
  baseline_login_failure_rate?: number;
  current_login_failure_rate?: number;
  baseline_latency_ms?: number;
  current_latency_ms?: number;
  baseline_payment_timeout_rate?: number;
  current_payment_timeout_rate?: number;
  total_logs?: number;
};

export type ApiAnomaly = {
  window_start: string;
  window_end: string;
  anomaly_score: number;
  is_anomalous: boolean;
  affected_services: ServiceName[];
  top_contributing_patterns: AnomalyTopPattern[];
  metrics: AnomalyMetrics;
  scored_at?: string;
};

export type ApiAnomaliesResponse = {
  count: number;
  anomalies: ApiAnomaly[];
};

export type DashboardServiceHealth = {
  service_name: ServiceName;
  total_logs: number;
  error_count: number;
  warning_count: number;
  error_rate: number;
  avg_latency_ms: number;
  top_events: Array<{ event_type: string; count: number }>;
};

export type DashboardLogBucket = {
  window_start: string;
  total_logs: number;
  error_count: number;
  error_rate: number;
};

export type DashboardOverview = {
  status: "ok";
  generated_at: string;
  total_logs_stored: number;
  recent_logs: {
    total_logs: number;
    level_counts: Record<LogLevel, number>;
    error_count: number;
    warning_count: number;
    service_health: DashboardServiceHealth[];
    log_timeline: DashboardLogBucket[];
  };
  anomaly_summary: {
    count: number;
    active_incident_windows: number;
    latest: ApiAnomaly | null;
    threshold: number;
  };
  anomaly_timeline: ApiAnomaly[];
  service_health: DashboardServiceHealth[];
  log_timeline: DashboardLogBucket[];
};

export type DashboardServiceHealthResponse = {
  status: "ok";
  generated_at: string;
  service_health: DashboardServiceHealth[];
};

export type DashboardTimelineResponse = {
  status: "ok";
  generated_at: string;
  log_timeline: DashboardLogBucket[];
  anomaly_timeline: ApiAnomaly[];
};

export type ApiConfig = {
  baseUrl: string;
};

export const defaultConfig: ApiConfig = {
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:7001",
};

async function apiGet<T>(path: string, config: ApiConfig = defaultConfig): Promise<T> {
  const res = await fetch(`${config.baseUrl}${path}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText}${text ? ` - ${text}` : ""}`);
  }

  return (await res.json()) as T;
}

export function fetchStatus(config?: ApiConfig) {
  return apiGet<ApiStatus>("/status", config ?? defaultConfig);
}

export function fetchAnomalies(limit = 100, config?: ApiConfig) {
  const qs = new URLSearchParams({ limit: String(limit) }).toString();
  return apiGet<ApiAnomaliesResponse>(`/anomalies?${qs}`, config ?? defaultConfig);
}

export function fetchLogs(filters: LogsFilters = {}, config?: ApiConfig) {
  const qs = new URLSearchParams();

  if (filters.start) qs.set("start", filters.start);
  if (filters.end) qs.set("end", filters.end);
  if (filters.service && filters.service !== "all") qs.set("service", filters.service);
  if (filters.logLevel && filters.logLevel !== "all") qs.set("log_level", filters.logLevel);
  if (filters.limit) qs.set("limit", String(filters.limit));

  const query = qs.toString();
  return apiGet<ApiLogsResponse>(`/logs${query ? `?${query}` : ""}`, config ?? defaultConfig);
}

export function fetchDashboardOverview(logLimit = 1000, anomalyLimit = 100, config?: ApiConfig) {
  const qs = new URLSearchParams({
    limit: String(logLimit),
    anomaly_limit: String(anomalyLimit),
  });
  return apiGet<DashboardOverview>(`/dashboard/overview?${qs.toString()}`, config ?? defaultConfig);
}

export function fetchDashboardServiceHealth(logLimit = 1000, config?: ApiConfig) {
  const qs = new URLSearchParams({ limit: String(logLimit) });
  return apiGet<DashboardServiceHealthResponse>(
    `/dashboard/service-health?${qs.toString()}`,
    config ?? defaultConfig,
  );
}

export function fetchDashboardTimeline(logLimit = 1000, anomalyLimit = 100, config?: ApiConfig) {
  const qs = new URLSearchParams({
    limit: String(logLimit),
    anomaly_limit: String(anomalyLimit),
  });
  return apiGet<DashboardTimelineResponse>(`/dashboard/timeline?${qs.toString()}`, config ?? defaultConfig);
}

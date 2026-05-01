import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { LogLevel, ServiceName } from "../../lib/api";
import { fetchLogs } from "../../lib/api";
import { formatTime, latency, LOG_LEVELS, SERVICES, serviceMeta } from "../../lib/insights";
import { StatusBadge } from "../components/StatusBadge";

function levelTone(level: LogLevel) {
  if (level === "ERROR") return "anomaly";
  if (level === "WARN") return "warning";
  return "muted";
}

export function LiveStreamPage() {
  const [service, setService] = useState<ServiceName | "all">("all");
  const [logLevel, setLogLevel] = useState<LogLevel | "all">("all");
  const [query, setQuery] = useState("");

  const logsQuery = useQuery({
    queryKey: ["logs", "live", service, logLevel, 500],
    queryFn: () => fetchLogs({ service, logLevel, limit: 500 }),
    refetchInterval: 5_000,
  });

  const logs = useMemo(() => logsQuery.data?.logs ?? [], [logsQuery.data?.logs]);
  const visibleLogs = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return logs;
    return logs.filter((log) =>
      [log.message, log.event_type, log.host, log.request_id ?? "", log.user_id ?? ""]
        .join(" ")
        .toLowerCase()
        .includes(needle),
    );
  }, [logs, query]);

  const errorCount = visibleLogs.filter((log) => log.log_level === "ERROR").length;

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">Live Log Stream</div>
            <div className="panel-copy">{logsQuery.isFetching ? "Refreshing from API" : `${visibleLogs.length} rows loaded`}</div>
          </div>
          <StatusBadge variant={errorCount > 0 ? "anomaly" : "normal"} pulse={errorCount > 0}>
            {errorCount} errors
          </StatusBadge>
        </div>

        <div className="toolbar">
          <label className="field">
            <span>Service</span>
            <select value={service} onChange={(event) => setService(event.target.value as ServiceName | "all")}>
              <option value="all">All services</option>
              {SERVICES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Level</span>
            <select value={logLevel} onChange={(event) => setLogLevel(event.target.value as LogLevel | "all")}>
              <option value="all">All levels</option>
              {LOG_LEVELS.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="field field-grow">
            <span>Search</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="message, event, host, request id"
            />
          </label>
        </div>

        <div className="log-table-wrap">
          <table className="data-table log-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Level</th>
                <th>Service</th>
                <th>Event</th>
                <th>Latency</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {visibleLogs.map((log) => (
                <tr key={log.id}>
                  <td className="font-mono text-[12px]">{formatTime(log.timestamp)}</td>
                  <td>
                    <StatusBadge variant={levelTone(log.log_level)}>{log.log_level}</StatusBadge>
                  </td>
                  <td>
                    <span className="service-name" style={{ color: serviceMeta[log.service_name].tone }}>
                      {log.service_name}
                    </span>
                  </td>
                  <td className="font-mono text-[12px]">{log.event_type}</td>
                  <td className="font-mono text-[12px]">{latency(log.latency_ms)}</td>
                  <td className="message-cell">{log.message}</td>
                </tr>
              ))}
              {visibleLogs.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                    <div className="empty-state">No logs match the current filters.</div>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

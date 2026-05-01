import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchAnomalies } from "../../lib/api";
import { formatTime, formatWindow, latency, percent, scoreTone, serviceMeta } from "../../lib/insights";
import { StatusBadge } from "../components/StatusBadge";

export function AnomaliesPage() {
  const [selectedWindow, setSelectedWindow] = useState<string | null>(null);

  const anomaliesQuery = useQuery({
    queryKey: ["anomalies", 200],
    queryFn: () => fetchAnomalies(200),
    refetchInterval: 30_000,
  });

  const anomalies = useMemo(() => anomaliesQuery.data?.anomalies ?? [], [anomaliesQuery.data?.anomalies]);
  const selected = anomalies.find((item) => item.window_start === selectedWindow) ?? anomalies[0];
  const anomalousCount = anomalies.filter((item) => item.is_anomalous).length;

  return (
    <div className="page-stack">
      <div className="dashboard-grid dashboard-grid-five">
        <section className="panel lg-span-3">
          <div className="panel-header">
            <div>
              <div className="panel-title">Window History</div>
              <div className="panel-copy">
                {anomaliesQuery.isFetching ? "Refreshing scored windows" : `${anomalies.length} scored windows`}
              </div>
            </div>
            <StatusBadge variant={anomalousCount > 0 ? "anomaly" : "normal"} pulse={anomalousCount > 0}>
              {anomalousCount} anomalous
            </StatusBadge>
          </div>

          <div className="log-table-wrap compact-table">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Window</th>
                  <th>Score</th>
                  <th>State</th>
                  <th>Services</th>
                  <th>Top signal</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((item) => {
                  const tone = scoreTone(item.anomaly_score, item.is_anomalous);
                  const pattern = item.top_contributing_patterns[0];
                  return (
                    <tr
                      className={item.window_start === selected?.window_start ? "selected-row" : undefined}
                      key={item.window_start}
                      onClick={() => setSelectedWindow(item.window_start)}
                    >
                      <td className="font-mono text-[12px]">{formatWindow(item)}</td>
                      <td className="font-mono text-[12px]">{item.anomaly_score.toFixed(4)}</td>
                      <td>
                        <StatusBadge variant={tone}>{item.is_anomalous ? "anomaly" : "normal"}</StatusBadge>
                      </td>
                      <td className="service-list-cell">
                        {item.affected_services.length ? item.affected_services.join(", ") : "--"}
                      </td>
                      <td className="font-mono text-[12px]">
                        {pattern ? `${pattern.label} · ${pattern.deviation_ratio}x` : "--"}
                      </td>
                    </tr>
                  );
                })}
                {anomalies.length === 0 ? (
                  <tr>
                    <td colSpan={5}>
                      <div className="empty-state">No anomaly windows found yet.</div>
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="panel lg-span-2">
          <div className="panel-header">
            <div>
              <div className="panel-title">Window Detail</div>
              <div className="panel-copy">{selected ? formatWindow(selected) : "No window selected"}</div>
            </div>
            {selected ? (
              <StatusBadge variant={scoreTone(selected.anomaly_score, selected.is_anomalous)}>
                {selected.anomaly_score.toFixed(4)}
              </StatusBadge>
            ) : null}
          </div>

          {selected ? (
            <div className="detail-stack">
              <div className="metric-list">
                <div className="metric-row">
                  <span>Error rate</span>
                  <strong>{percent(selected.metrics.current_error_rate as number | undefined)}</strong>
                </div>
                <div className="metric-row">
                  <span>Baseline error</span>
                  <strong>{percent(selected.metrics.baseline_error_rate as number | undefined)}</strong>
                </div>
                <div className="metric-row">
                  <span>Login failure</span>
                  <strong>{percent(selected.metrics.current_login_failure_rate as number | undefined)}</strong>
                </div>
                <div className="metric-row">
                  <span>Average latency</span>
                  <strong>{latency(selected.metrics.current_latency_ms as number | undefined)}</strong>
                </div>
                <div className="metric-row">
                  <span>Total logs</span>
                  <strong>{String(selected.metrics.total_logs ?? "--")}</strong>
                </div>
              </div>

              <div>
                <div className="subsection-title">Contributing patterns</div>
                <div className="pattern-list">
                  {selected.top_contributing_patterns.map((pattern) => (
                    <div className="pattern-row" key={pattern.feature}>
                      <div>
                        <div className="text-sm font-medium">{pattern.label}</div>
                        <div className="font-mono text-[11px]" style={{ color: "var(--text-muted)" }}>
                          {pattern.feature}
                        </div>
                      </div>
                      <div className="pattern-value">{pattern.deviation_ratio}x</div>
                    </div>
                  ))}
                  {selected.top_contributing_patterns.length === 0 ? (
                    <div className="empty-state compact">No major deviations.</div>
                  ) : null}
                </div>
              </div>

              <div>
                <div className="subsection-title">Affected services</div>
                <div className="chip-row">
                  {selected.affected_services.map((service) => (
                    <span className="service-chip" key={service} style={{ borderColor: serviceMeta[service].tone }}>
                      {service}
                    </span>
                  ))}
                  {selected.affected_services.length === 0 ? (
                    <div className="empty-state compact">No service attribution.</div>
                  ) : null}
                </div>
              </div>
              <div className="font-mono text-[12px]" style={{ color: "var(--text-muted)" }}>
                Scored {selected.scored_at ? formatTime(selected.scored_at) : "--"}
              </div>
            </div>
          ) : (
            <div className="empty-state">Run the detector to create anomaly results.</div>
          )}
        </aside>
      </div>
    </div>
  );
}

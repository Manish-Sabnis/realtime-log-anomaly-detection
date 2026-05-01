import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
  type ChartOptions,
  type TooltipItem,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { fetchDashboardOverview } from "../../lib/api";
import {
  formatTime,
  formatWindow,
  latency,
  number,
  percent,
  scoreTone,
  serviceMeta,
} from "../../lib/insights";
import { KpiCard } from "../components/KpiCard";
import { StatusBadge } from "../components/StatusBadge";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler, Legend);

export function OverviewPage() {
  const overviewQuery = useQuery({
    queryKey: ["dashboard", "overview", 1000, 100],
    queryFn: () => fetchDashboardOverview(1000, 100),
    refetchInterval: 20_000,
  });

  const overview = overviewQuery.data;
  const anomalies = useMemo(() => overview?.anomaly_timeline ?? [], [overview?.anomaly_timeline]);
  const latest = overview?.anomaly_summary.latest ?? anomalies[0];
  const latestIncident = anomalies.find((item) => item.is_anomalous);
  const activeWindows = overview?.anomaly_summary.active_incident_windows ?? 0;
  const serviceHealth = overview?.service_health ?? [];
  const minuteBuckets = useMemo(() => (overview?.log_timeline ?? []).slice(-16), [overview?.log_timeline]);
  const threshold = overview?.anomaly_summary.threshold ?? 0.75;

  const chronological = useMemo(() => [...anomalies].reverse(), [anomalies]);
  const labels = useMemo(() => chronological.map((item) => formatTime(item.window_start).slice(0, 5)), [chronological]);
  const scores = useMemo(() => chronological.map((item) => item.anomaly_score), [chronological]);

  const chartData = useMemo(
    () => ({
      labels,
      datasets: [
        {
          label: "Anomaly score",
          data: scores,
          borderColor: "rgba(148, 163, 184, 0.55)",
          backgroundColor: "rgba(59, 130, 246, 0.08)",
          pointRadius: 0,
          borderWidth: 2,
          tension: 0.35,
          fill: true,
        },
        {
          label: "Normal",
          data: chronological.map((item) => (item.is_anomalous ? null : item.anomaly_score)),
          borderColor: "transparent",
          backgroundColor: "rgba(52, 211, 153, 1)",
          pointBackgroundColor: "rgba(52, 211, 153, 1)",
          pointBorderColor: "rgba(10, 10, 10, 1)",
          pointBorderWidth: 2,
          pointRadius: 4,
          showLine: false,
        },
        {
          label: "Anomaly",
          data: chronological.map((item) => (item.is_anomalous ? item.anomaly_score : null)),
          borderColor: "transparent",
          backgroundColor: "rgba(248, 113, 113, 1)",
          pointBackgroundColor: "rgba(248, 113, 113, 1)",
          pointBorderColor: "rgba(10, 10, 10, 1)",
          pointBorderWidth: 2,
          pointRadius: 7,
          pointHoverRadius: 8,
          showLine: false,
        },
        {
          label: "Threshold",
          data: chronological.map(() => threshold),
          borderColor: "rgba(248, 113, 113, 0.7)",
          borderDash: [6, 6],
          borderWidth: 1,
          pointRadius: 0,
          fill: false,
        },
      ],
    }),
    [chronological, labels, scores, threshold],
  );

  const chartOptions = useMemo<ChartOptions<"line">>(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: {
          display: true,
          labels: {
            color: "rgba(156, 163, 175, 1)",
            boxWidth: 10,
            boxHeight: 10,
            usePointStyle: true,
          },
        },
        tooltip: {
          callbacks: {
            title: (items: TooltipItem<"line">[]) => {
              const item = chronological[items[0]?.dataIndex ?? 0];
              return item ? formatWindow(item) : "";
            },
            label: (item: TooltipItem<"line">) => {
              const row = chronological[item.dataIndex];
              if (!row) return "";
              const pattern = row.top_contributing_patterns[0];
              if (item.dataset.label === "Threshold") return `threshold: ${threshold.toFixed(4)}`;
              return [
                `${item.dataset.label}: ${row.anomaly_score.toFixed(4)}`,
                row.is_anomalous ? "state: anomaly" : "state: normal",
                pattern ? `signal: ${pattern.label} (${pattern.deviation_ratio}x)` : undefined,
              ].filter(Boolean) as string[];
            },
          },
        },
      },
      scales: {
        y: {
          min: 0,
          max: 1,
          ticks: { color: "rgba(156, 163, 175, 1)", stepSize: 0.25 },
          grid: { color: "rgba(148, 163, 184, 0.12)" },
        },
        x: {
          ticks: { color: "rgba(156, 163, 175, 1)", maxRotation: 0, autoSkip: true },
          grid: { display: false },
        },
      },
    }),
    [chronological, threshold],
  );

  const latestTone = scoreTone(latest?.anomaly_score, latest?.is_anomalous);
  const latestErrorRate =
    typeof latest?.metrics.current_error_rate === "number" ? latest.metrics.current_error_rate : undefined;
  const latestLatency =
    typeof latest?.metrics.current_latency_ms === "number" ? latest.metrics.current_latency_ms : undefined;

  return (
    <div className="page-stack">
      <div className="dashboard-grid dashboard-grid-four">
        <KpiCard
          label="Logs ingested"
          value={overview ? number(overview.total_logs_stored) : "--"}
          sublabel={`${number(overview?.recent_logs.total_logs)} visible in current sample`}
          variant={overviewQuery.isError ? "anomaly" : "normal"}
          accent="var(--accent-blue)"
        />
        <KpiCard
          label="Latest score"
          value={latest ? latest.anomaly_score.toFixed(4) : "--"}
          sublabel={latest ? formatWindow(latest) : "No scored windows"}
          variant={latestTone}
          accent={latestTone === "anomaly" ? "var(--status-anomaly)" : "var(--status-normal)"}
        />
        <KpiCard
          label="Error rate"
          value={percent(latestErrorRate)}
          sublabel={`Baseline ${percent(latest?.metrics.baseline_error_rate as number | undefined)}`}
          variant={latestTone}
          accent="var(--status-warning)"
        />
        <KpiCard
          label="Incident windows"
          value={String(activeWindows)}
          sublabel={latestIncident ? `Last incident ${formatTime(latestIncident.window_end)}` : "No incidents in sample"}
          variant={activeWindows > 0 ? "anomaly" : "normal"}
          accent="var(--status-anomaly)"
        />
      </div>

      <section className="panel panel-prominent">
        <div className="panel-header">
          <div>
            <div className="panel-title">Anomaly Score Timeline</div>
            <div className="panel-copy">Normal and anomalous windows are split into separate markers.</div>
          </div>
          <StatusBadge variant={latestTone} pulse={latest?.is_anomalous}>
            threshold {threshold.toFixed(2)}
          </StatusBadge>
        </div>
        <div className="chart-frame">
          <Line data={chartData} options={chartOptions} />
        </div>
      </section>

      <div className="dashboard-grid dashboard-grid-five">
        <section className="panel lg-span-3">
          <div className="panel-header">
            <div>
            <div className="panel-title">Service Pulse</div>
            <div className="panel-copy">Recent log distribution and error pressure by service.</div>
          </div>
            <StatusBadge variant={(overview?.recent_logs.error_count ?? 0) > 0 ? "warning" : "normal"}>
              {overview?.recent_logs.error_count ?? 0} errors
            </StatusBadge>
          </div>
          <div className="service-pulse-grid">
            {serviceHealth.map((service) => {
              const meta = serviceMeta[service.service_name];
              return (
                <div className="service-pulse" key={service.service_name}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="service-token" style={{ borderColor: meta.tone, color: meta.tone }}>
                      {meta.short}
                    </div>
                    <div className="font-mono text-[12px]" style={{ color: "var(--text-muted)" }}>
                      {percent(service.error_rate)}
                    </div>
                  </div>
                  <div className="mt-3 font-medium">{meta.label}</div>
                  <div className="mt-1 text-[12px]" style={{ color: "var(--text-muted)" }}>
                    {number(service.total_logs)} logs · {latency(service.avg_latency_ms)}
                  </div>
                  <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/5">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.min(100, Math.max(6, service.error_rate * 100))}%`,
                        background: service.error_rate > 0.08 ? "var(--status-anomaly)" : meta.tone,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="panel lg-span-2">
          <div className="panel-header">
            <div>
              <div className="panel-title">Latest Incident</div>
              <div className="panel-copy">{latestIncident ? formatWindow(latestIncident) : "No anomalous window in sample"}</div>
            </div>
            <StatusBadge variant={latestIncident ? "anomaly" : "normal"}>
              {latestIncident ? "active" : "clear"}
            </StatusBadge>
          </div>
          {latestIncident ? (
            <div className="pattern-list">
              {latestIncident.top_contributing_patterns.slice(0, 5).map((pattern) => (
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
            </div>
          ) : (
            <div className="empty-state">The detector has not marked a recent window as anomalous.</div>
          )}
        </section>
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">Log Pressure</div>
            <div className="panel-copy">Recent minute buckets from raw logs.</div>
          </div>
          <div className="text-[12px]" style={{ color: "var(--text-muted)" }}>
            {overviewQuery.isFetching ? "Refreshing" : `${minuteBuckets.length} buckets`}
          </div>
        </div>
        <div className="minute-bars">
          {minuteBuckets.map((bucket) => (
            <div className="minute-bar" key={bucket.window_start}>
              <div
                className="minute-bar-fill"
                title={`${formatTime(bucket.window_start)} · ${bucket.total_logs} logs · ${percent(bucket.error_rate)}`}
                style={{
                  height: `${Math.min(100, Math.max(8, bucket.total_logs / 18))}%`,
                  background: bucket.error_rate > 0.08 ? "var(--status-anomaly)" : "var(--accent-blue)",
                }}
              />
              <div className="minute-bar-label">{formatTime(bucket.window_start).slice(0, 5)}</div>
            </div>
          ))}
          {minuteBuckets.length === 0 ? <div className="empty-state">No logs available yet.</div> : null}
        </div>
      </section>

      <div className="dashboard-grid dashboard-grid-two">
        <section className="panel">
          <div className="panel-title">Current Metrics</div>
          <div className="metric-list">
            <div className="metric-row">
              <span>Login failure rate</span>
              <strong>{percent(latest?.metrics.current_login_failure_rate as number | undefined)}</strong>
            </div>
            <div className="metric-row">
              <span>Average latency</span>
              <strong>{latency(latestLatency)}</strong>
            </div>
            <div className="metric-row">
              <span>Payment timeout rate</span>
              <strong>{percent(latest?.metrics.current_payment_timeout_rate as number | undefined)}</strong>
            </div>
          </div>
        </section>
        <section className="panel">
          <div className="panel-title">Affected Services</div>
          <div className="chip-row">
            {(latestIncident?.affected_services ?? []).map((service) => (
              <span className="service-chip" key={service} style={{ borderColor: serviceMeta[service].tone }}>
                {service}
              </span>
            ))}
            {!latestIncident?.affected_services.length ? <div className="empty-state compact">No service impact.</div> : null}
          </div>
        </section>
      </div>
    </div>
  );
}

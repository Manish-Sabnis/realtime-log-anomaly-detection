import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchAnomalies, fetchDashboardServiceHealth } from "../../lib/api";
import { latency, number, percent, serviceMeta } from "../../lib/insights";
import { StatusBadge } from "../components/StatusBadge";

export function ServicesPage() {
  const serviceHealthQuery = useQuery({
    queryKey: ["dashboard", "service-health", 1000],
    queryFn: () => fetchDashboardServiceHealth(1000),
    refetchInterval: 20_000,
  });

  const anomaliesQuery = useQuery({
    queryKey: ["anomalies", "services", 100],
    queryFn: () => fetchAnomalies(100),
    refetchInterval: 30_000,
  });

  const services = useMemo(
    () => serviceHealthQuery.data?.service_health ?? [],
    [serviceHealthQuery.data?.service_health],
  );
  const anomalies = useMemo(() => anomaliesQuery.data?.anomalies ?? [], [anomaliesQuery.data?.anomalies]);

  return (
    <div className="page-stack">
      <div className="dashboard-grid dashboard-grid-two">
        {services.map((service) => {
          const meta = serviceMeta[service.service_name];
          const recentImpact = anomalies.find(
            (item) => item.is_anomalous && item.affected_services.includes(service.service_name),
          );
          const tone = recentImpact ? "anomaly" : service.error_rate > 0.05 ? "warning" : "normal";

          return (
            <section className="panel service-panel" key={service.service_name}>
              <div className="panel-header">
                <div className="brand-mark compact">
                  <div className="brand-icon" style={{ borderColor: meta.tone, color: meta.tone }}>
                    {meta.short}
                  </div>
                  <div>
                    <div className="panel-title">{meta.label}</div>
                    <div className="panel-copy">{service.service_name}</div>
                  </div>
                </div>
                <StatusBadge variant={tone} pulse={Boolean(recentImpact)}>
                  {recentImpact ? "impacted" : "stable"}
                </StatusBadge>
              </div>

              <div className="service-metrics">
                <div>
                  <span>Logs</span>
                  <strong>{number(service.total_logs)}</strong>
                </div>
                <div>
                  <span>Error rate</span>
                  <strong>{percent(service.error_rate)}</strong>
                </div>
                <div>
                  <span>Warnings</span>
                  <strong>{service.warning_count}</strong>
                </div>
                <div>
                  <span>Avg latency</span>
                  <strong>{latency(service.avg_latency_ms)}</strong>
                </div>
              </div>

              <div className="subsection-title">Top events</div>
              <div className="event-stack">
                {service.top_events.map((event) => (
                  <div className="event-row" key={event.event_type}>
                    <span>{event.event_type}</span>
                    <strong>{event.count}</strong>
                  </div>
                ))}
                {service.top_events.length === 0 ? <div className="empty-state compact">No recent events.</div> : null}
              </div>
            </section>
          );
        })}
        {services.length === 0 ? <div className="empty-state">No service health data available yet.</div> : null}
      </div>
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { defaultConfig, fetchStatus } from "../../lib/api";
import { StatusBadge } from "../components/StatusBadge";

export function SettingsPage() {
  const statusQuery = useQuery({
    queryKey: ["status", "settings"],
    queryFn: () => fetchStatus(),
    refetchInterval: 30_000,
  });

  const healthy = statusQuery.data?.status === "ok";

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">API Connection</div>
            <div className="panel-copy">The dashboard reads directly from the Python ingestor API.</div>
          </div>
          <StatusBadge variant={healthy ? "normal" : "anomaly"} pulse={!healthy}>
            {healthy ? "connected" : "offline"}
          </StatusBadge>
        </div>

        <div className="settings-grid">
          <div className="settings-row">
            <span>Base URL</span>
            <strong className="font-mono">{defaultConfig.baseUrl}</strong>
          </div>
          <div className="settings-row">
            <span>Status endpoint</span>
            <strong className="font-mono">GET /status</strong>
          </div>
          <div className="settings-row">
            <span>Logs endpoint</span>
            <strong className="font-mono">GET /logs</strong>
          </div>
          <div className="settings-row">
            <span>Anomalies endpoint</span>
            <strong className="font-mono">GET /anomalies</strong>
          </div>
          <div className="settings-row">
            <span>Stored logs</span>
            <strong>{statusQuery.data?.total_logs_stored?.toLocaleString() ?? "--"}</strong>
          </div>
        </div>
      </section>
    </div>
  );
}

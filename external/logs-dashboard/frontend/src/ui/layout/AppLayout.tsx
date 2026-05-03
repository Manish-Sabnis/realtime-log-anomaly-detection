import { NavLink, Outlet, useLocation } from "react-router-dom";
import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { defaultConfig, fetchAnomalies, fetchStatus } from "../../lib/api";
import { formatTime, scoreTone } from "../../lib/insights";
import { useUiStore } from "../../store/ui";
import { StatusBadge } from "../components/StatusBadge";

const nav = [
  { to: "/overview", label: "Command Center" },
  { to: "/live", label: "Live Logs" },
  { to: "/anomalies", label: "Anomaly Windows" },
  { to: "/services", label: "Services" },
  { to: "/settings", label: "Settings" },
];

function pageTitle(pathname: string) {
  if (pathname.startsWith("/overview")) return "Command Center";
  if (pathname.startsWith("/live")) return "Live Logs";
  if (pathname.startsWith("/anomalies")) return "Anomaly Windows";
  if (pathname.startsWith("/services")) return "Service Health";
  if (pathname.startsWith("/settings")) return "Settings";
  return "Dashboard";
}

export function AppLayout() {
  const location = useLocation();
  const toggleTheme = useUiStore((s) => s.toggleTheme);

  const statusQuery = useQuery({
    queryKey: ["status"],
    queryFn: () => fetchStatus(),
    refetchInterval: 30_000,
  });

  const anomaliesQuery = useQuery({
    queryKey: ["anomalies", 100],
    queryFn: () => fetchAnomalies(100),
    refetchInterval: 30_000,
  });

  const anomalies = anomaliesQuery.data?.anomalies ?? [];
  const latest = anomalies[0];
  const activeIncidents = anomalies.filter((item) => item.is_anomalous).length;
  const apiHealthy = statusQuery.data?.status === "ok";
  const latestTone = scoreTone(latest?.anomaly_score, latest?.is_anomalous);
  const lastUpdatedAt = Math.max(statusQuery.dataUpdatedAt, anomaliesQuery.dataUpdatedAt);
  const lastUpdatedLabel = lastUpdatedAt > 0 ? formatTime(new Date(lastUpdatedAt).toISOString()) : "--";
  const isRefreshing = statusQuery.isFetching || anomaliesQuery.isFetching;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="px-4 py-4">
          <div className="brand-mark">
            <div className="brand-icon">AD</div>
            <div>
              <div className="text-sm font-semibold tracking-tight">Anomaly Desk</div>
              <div className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                Realtime log intelligence
              </div>
            </div>
          </div>

          <div className="mt-4">
            <StatusBadge variant={latestTone} pulse={latest?.is_anomalous}>
              {latest?.is_anomalous ? "incident detected" : apiHealthy ? "monitoring" : "api offline"}
            </StatusBadge>
          </div>
        </div>

        <nav className="sidebar-nav">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => clsx("nav-item", isActive && "nav-item-active")}
            >
              <span>{item.label}</span>
              {item.to === "/anomalies" && activeIncidents > 0 ? (
                <span className="nav-count">{activeIncidents}</span>
              ) : null}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="mini-stat">
            <span>API</span>
            <span style={{ color: apiHealthy ? "var(--status-normal)" : "var(--status-anomaly)" }}>
              {apiHealthy ? "online" : "offline"}
            </span>
          </div>
          <div className="mini-stat">
            <span>Base URL</span>
            <span className="truncate">{defaultConfig.baseUrl.replace(/^https?:\/\//, "")}</span>
          </div>
          <div className="mini-stat">
            <span>Logs</span>
            <span>{statusQuery.data?.total_logs_stored?.toLocaleString() ?? "--"}</span>
          </div>
          <div className="mini-stat">
            <span>Last window</span>
            <span>{latest?.window_end ? formatTime(latest.window_end).slice(0, 5) : "--"}</span>
          </div>
        </div>
      </aside>

      <main className="main-pane">
        <header className="topbar">
          <div>
            <div className="page-title">{pageTitle(location.pathname)}</div>
            <div className="page-subtitle">
              {latest
                ? `Latest score ${latest.anomaly_score.toFixed(4)} at ${formatTime(latest.window_end)} · refreshed ${lastUpdatedLabel}`
                : `Waiting for detector windows · refreshed ${lastUpdatedLabel}`}
            </div>
          </div>
          <div className="topbar-actions">
            <button
              className="ghost-button"
              type="button"
              onClick={() => {
                statusQuery.refetch();
                anomaliesQuery.refetch();
              }}
            >
              {isRefreshing ? "Refreshing" : "Refresh"}
            </button>
            <button className="ghost-button" type="button" onClick={toggleTheme}>
              Theme
            </button>
          </div>
        </header>

        <div className="content-area">
          {statusQuery.isError || anomaliesQuery.isError ? (
            <div className="notice-panel">
              <div className="font-medium" style={{ color: "var(--status-warning)" }}>
                Backend connection is unavailable
              </div>
              <div className="mt-1 font-mono text-[12px]" style={{ color: "var(--text-muted)" }}>
                {String(statusQuery.error ?? anomaliesQuery.error)}
              </div>
            </div>
          ) : null}

          <Outlet />
        </div>
      </main>
    </div>
  );
}

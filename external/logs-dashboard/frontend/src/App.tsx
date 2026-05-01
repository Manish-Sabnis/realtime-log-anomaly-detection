import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useUiStore } from "./store/ui";
import { AppLayout } from "./ui/layout/AppLayout";
import { OverviewPage } from "./ui/pages/OverviewPage";
import { AnomaliesPage } from "./ui/pages/AnomaliesPage";
import { LiveStreamPage } from "./ui/pages/LiveStreamPage";
import { ServicesPage } from "./ui/pages/ServicesPage";
import { SettingsPage } from "./ui/pages/SettingsPage";

export default function App() {
  const theme = useUiStore((s) => s.theme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/live" element={<LiveStreamPage />} />
          <Route path="/anomalies" element={<AnomaliesPage />} />
          <Route path="/services" element={<ServicesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

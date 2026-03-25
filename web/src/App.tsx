import { useEffect, useState } from "react";

import DashboardPage from "./pages/DashboardPage";
import DevicesPage from "./pages/DevicesPage";
import NodesPage from "./pages/NodesPage";
import ProvidersPage from "./pages/ProvidersPage";
import { api, type Device, type Model, type Provider } from "./lib/api";

type Page = "dashboard" | "providers" | "devices" | "nodes";

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  async function refreshAll() {
    setLoading(true);
    setError("");
    try {
      const [nextProviders, nextModels, nextDevices] = await Promise.all([
        api.getProviders(),
        api.getModels(),
        api.getDevices(),
      ]);
      setProviders(nextProviders);
      setModels(nextModels);
      setDevices(nextDevices);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Unknown request error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-kicker">Zhaocai Gateway</span>
          <h1>v2 Control Plane</h1>
          <p>Central provider management and per-device OpenClaw sync.</p>
        </div>
        <nav className="nav">
          {[
            { id: "dashboard", label: "Dashboard" },
            { id: "providers", label: "Providers" },
            { id: "devices", label: "Devices" },
            { id: "nodes", label: "Nodes" },
          ].map((item) => (
            <button
              key={item.id}
              className={`nav-button ${page === item.id ? "active" : ""}`}
              onClick={() => setPage(item.id as Page)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="status-chip">{loading ? "Loading" : "Ready"}</span>
            {error ? <span className="error-chip">{error}</span> : null}
          </div>
          <button className="secondary-button" onClick={() => void refreshAll()}>
            Refresh All
          </button>
        </header>

        {page === "dashboard" ? (
          <DashboardPage
            providers={providers}
            models={models}
            devices={devices}
            onRefresh={() => void refreshAll()}
          />
        ) : null}
        {page === "providers" ? (
          <ProvidersPage providers={providers} models={models} onRefresh={refreshAll} />
        ) : null}
        {page === "devices" ? (
          <DevicesPage devices={devices} models={models} onRefresh={refreshAll} />
        ) : null}
        {page === "nodes" ? <NodesPage devices={devices} onRefresh={refreshAll} /> : null}
      </main>
    </div>
  );
}

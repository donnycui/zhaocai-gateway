import { useEffect, useState } from "react";

import DashboardPage from "./pages/DashboardPage";
import DevicesPage from "./pages/DevicesPage";
import NodesPage from "./pages/NodesPage";
import ProvidersPage from "./pages/ProvidersPage";
import {
  api,
  getStoredAdminToken,
  storeAdminToken,
  type Device,
  type Model,
  type Provider,
} from "./lib/api";

type Page = "dashboard" | "providers" | "devices" | "nodes";

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [adminToken, setAdminToken] = useState<string>(() => getStoredAdminToken());

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

  function handleSaveAdminToken() {
    storeAdminToken(adminToken.trim());
    void refreshAll();
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-kicker">Zhaocai Gateway</span>
          <h1>v2 控制台</h1>
          <p>统一管理 Provider，并按设备下发 OpenClaw 配置。</p>
        </div>
        <nav className="nav">
          {[
            { id: "dashboard", label: "总览" },
            { id: "providers", label: "上游服务" },
            { id: "devices", label: "设备" },
            { id: "nodes", label: "节点接入" },
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
          <div className="topbar-left">
            <span className="status-chip">{loading ? "加载中" : "就绪"}</span>
            {error ? <span className="error-chip">{error}</span> : null}
          </div>
          <div className="topbar-actions">
            <label className="token-input">
              <span>管理令牌</span>
              <input
                type="password"
                value={adminToken}
                onChange={(event) => setAdminToken(event.target.value)}
                placeholder="粘贴 X-Admin-Token"
              />
            </label>
            <button className="secondary-button" onClick={handleSaveAdminToken}>
              保存令牌
            </button>
            <button className="secondary-button" onClick={() => void refreshAll()}>
              刷新全部
            </button>
          </div>
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

import { useEffect, useState } from "react";

import DashboardPage from "./pages/DashboardPage";
import DevicesPage from "./pages/DevicesPage";
import NodesPage from "./pages/NodesPage";
import ProviderEditorPage from "./pages/ProviderEditorPage";
import ProvidersPage from "./pages/ProvidersPage";
import {
  api,
  getStoredAdminToken,
  storeAdminToken,
  type Device,
  type Model,
  type Provider,
} from "./lib/api";

type Page = "dashboard" | "providers" | "provider-editor" | "devices" | "nodes";

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [adminToken, setAdminToken] = useState<string>(() => getStoredAdminToken());
  const [editingProviderId, setEditingProviderId] = useState<number | null>(null);

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

  function openProviderCreate() {
    setEditingProviderId(null);
    setPage("provider-editor");
  }

  function openProviderEdit(providerId: number) {
    setEditingProviderId(providerId);
    setPage("provider-editor");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-kicker">Zhaocai Gateway</span>
          <h1>v2 控制台</h1>
          <p>当前后台已经拆出资源中心入口，先从 OpenClaw 开始，逐步承接 Gateway、Media 和 Universal。</p>
        </div>
        <nav className="nav">
          {[
            { id: "dashboard", label: "总览" },
            { id: "providers", label: "资源中心" },
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
          <ProvidersPage
            providers={providers}
            models={models}
            onRefresh={refreshAll}
            onCreate={openProviderCreate}
            onEdit={openProviderEdit}
          />
        ) : null}
        {page === "provider-editor" ? (
          <ProviderEditorPage
            providerId={editingProviderId}
            onBack={() => setPage("providers")}
            onSaved={refreshAll}
          />
        ) : null}
        {page === "devices" ? (
          <DevicesPage devices={devices} models={models} onRefresh={refreshAll} />
        ) : null}
        {page === "nodes" ? <NodesPage devices={devices} onRefresh={refreshAll} /> : null}
      </main>
    </div>
  );
}

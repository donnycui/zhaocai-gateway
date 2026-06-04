import { useEffect, useState } from "react";

import DashboardPage from "./pages/DashboardPage";
import DevicesPage from "./pages/DevicesPage";
import HermesDevicesPage from "./pages/HermesDevicesPage";
import HermesNodesPage from "./pages/HermesNodesPage";
import HermesProviderEditorPage from "./pages/HermesProviderEditorPage";
import NodesPage from "./pages/NodesPage";
import ProviderEditorPage from "./pages/ProviderEditorPage";
import ProvidersPage from "./pages/ProvidersPage";
import {
  api,
  getStoredAdminToken,
  storeAdminToken,
  type Device,
  type HermesDevice,
  type HermesModel,
  type HermesProvider,
  type Model,
  type Provider,
} from "./lib/api";

type Page =
  | "dashboard"
  | "providers"
  | "provider-editor"
  | "hermes-provider-editor"
  | "openclaw-devices"
  | "openclaw-nodes"
  | "hermes-devices"
  | "hermes-nodes";

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [hermesProviders, setHermesProviders] = useState<HermesProvider[]>([]);
  const [hermesModels, setHermesModels] = useState<HermesModel[]>([]);
  const [hermesDevices, setHermesDevices] = useState<HermesDevice[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [adminToken, setAdminToken] = useState<string>(() => getStoredAdminToken());
  const [editingProviderId, setEditingProviderId] = useState<number | null>(null);
  const [editingHermesProviderId, setEditingHermesProviderId] = useState<number | null>(null);

  async function refreshAll() {
    setLoading(true);
    setError("");
    try {
      const [
        nextProviders,
        nextModels,
        nextDevices,
        nextHermesProviders,
        nextHermesModels,
        nextHermesDevices,
      ] = await Promise.all([
        api.getProviders(),
        api.getModels(),
        api.getDevices(),
        api.getHermesProviders(),
        api.getHermesModels(),
        api.getHermesDevices(),
      ]);
      setProviders(nextProviders);
      setModels(nextModels);
      setDevices(nextDevices);
      setHermesProviders(nextHermesProviders);
      setHermesModels(nextHermesModels);
      setHermesDevices(nextHermesDevices);
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

  function openHermesProviderCreate() {
    setEditingHermesProviderId(null);
    setPage("hermes-provider-editor");
  }

  function openHermesProviderEdit(providerId: number) {
    setEditingHermesProviderId(providerId);
    setPage("hermes-provider-editor");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-kicker">Zhaocai Gateway</span>
          <h1>v2 控制台</h1>
          <p>资源中心和节点运行面已按 OpenClaw / Hermes 拆分，Gateway、Media 和 Universal 继续保留模块化入口。</p>
        </div>
        <nav className="nav">
          {[
            { id: "dashboard", label: "总览" },
            { id: "providers", label: "资源中心" },
          ].map((item) => (
            <button
              key={item.id}
              className={`nav-button ${page === item.id ? "active" : ""}`}
              onClick={() => setPage(item.id as Page)}
            >
              {item.label}
            </button>
          ))}
          <div className="nav-group">
            <span className="nav-group-label">OpenClaw</span>
            <div className="nav-subnav">
              {[
                { id: "openclaw-devices", label: "设备" },
                { id: "openclaw-nodes", label: "节点接入" },
              ].map((item) => (
                <button
                  key={item.id}
                  className={`nav-sub-button ${page === item.id ? "active" : ""}`}
                  onClick={() => setPage(item.id as Page)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
          <div className="nav-group">
            <span className="nav-group-label">Hermes</span>
            <div className="nav-subnav">
              {[
                { id: "hermes-devices", label: "设备" },
                { id: "hermes-nodes", label: "节点接入" },
              ].map((item) => (
                <button
                  key={item.id}
                  className={`nav-sub-button ${page === item.id ? "active" : ""}`}
                  onClick={() => setPage(item.id as Page)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
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
            hermesProviders={hermesProviders}
            hermesModels={hermesModels}
            hermesDevices={hermesDevices}
            onRefresh={() => void refreshAll()}
          />
        ) : null}
        {page === "providers" ? (
          <ProvidersPage
            providers={providers}
            models={models}
            hermesProviders={hermesProviders}
            hermesModels={hermesModels}
            onRefresh={refreshAll}
            onCreate={openProviderCreate}
            onEdit={openProviderEdit}
            onCreateHermes={openHermesProviderCreate}
            onEditHermes={openHermesProviderEdit}
          />
        ) : null}
        {page === "provider-editor" ? (
          <ProviderEditorPage
            providerId={editingProviderId}
            onBack={() => setPage("providers")}
            onSaved={refreshAll}
          />
        ) : null}
        {page === "hermes-provider-editor" ? (
          <HermesProviderEditorPage
            providerId={editingHermesProviderId}
            onBack={() => setPage("providers")}
            onSaved={refreshAll}
          />
        ) : null}
        {page === "openclaw-devices" ? (
          <DevicesPage devices={devices} models={models} onRefresh={refreshAll} />
        ) : null}
        {page === "openclaw-nodes" ? <NodesPage devices={devices} onRefresh={refreshAll} /> : null}
        {page === "hermes-devices" ? (
          <HermesDevicesPage devices={hermesDevices} models={hermesModels} onRefresh={refreshAll} />
        ) : null}
        {page === "hermes-nodes" ? (
          <HermesNodesPage devices={hermesDevices} onRefresh={refreshAll} />
        ) : null}
      </main>
    </div>
  );
}

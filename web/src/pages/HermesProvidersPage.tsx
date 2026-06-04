import { useMemo, useState } from "react";

import { api, type HermesModel, type HermesProvider, type Provider } from "../lib/api";

interface HermesProvidersPageProps {
  providers: HermesProvider[];
  models: HermesModel[];
  openclawProviders: Provider[];
  onRefresh: () => Promise<void>;
  onCreate: () => void;
  onEdit: (providerId: number) => void;
}

const avatarToneClasses = [
  "tone-coral",
  "tone-sky",
  "tone-mint",
  "tone-amber",
  "tone-plum",
  "tone-rose",
  "tone-indigo",
  "tone-lime",
];

export default function HermesProvidersPage({
  providers,
  models,
  openclawProviders,
  onRefresh,
  onCreate,
  onEdit,
}: HermesProvidersPageProps) {
  const [message, setMessage] = useState("");
  const [messageTone, setMessageTone] = useState<"success" | "error">("success");
  const [selectedImportProviderId, setSelectedImportProviderId] = useState<string>("");

  const modelCounts = useMemo(() => {
    const counts = new Map<number, number>();
    models.forEach((model) => {
      counts.set(model.provider_id, (counts.get(model.provider_id) ?? 0) + 1);
    });
    return counts;
  }, [models]);

  async function handleDeleteProvider(providerId: number) {
    const confirmed = window.confirm("确认删除这个 Hermes 供应商以及其下所有模型吗？");
    if (!confirmed) return;
    await api.deleteHermesProvider(providerId);
    setMessageTone("success");
    setMessage("Hermes 供应商已删除。");
    await onRefresh();
  }

  async function handleImportOpenClawProvider() {
    if (!selectedImportProviderId) {
      setMessageTone("error");
      setMessage("请先选择一个 OpenClaw 供应商。");
      return;
    }

    const result = await api.importOpenClawProviderToHermes(Number(selectedImportProviderId));
    setMessageTone("success");
    setMessage(`已${result.action === "created" ? "导入" : "更新"} Hermes 供应商：${result.provider.name}`);
    await onRefresh();
  }

  return (
    <div className="panel">
      <div className="page-header">
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>Hermes 供应商</h3>
          <p>管理 Hermes 专用 provider 与模型，支持从 OpenClaw provider 一键复制基础连接信息。</p>
        </div>
        <div className="topbar-actions provider-page-actions">
          <button onClick={onCreate}>新增 Hermes 供应商</button>
        </div>
      </div>

      <div className="builder-card">
        <div className="builder-card-header">
          <div>
            <strong>从 OpenClaw 导入</strong>
            <span>复制 OpenClaw 的 `base_url + api_key` 到 Hermes provider。</span>
          </div>
        </div>
        <div className="builder-grid">
          <label>
            <span>OpenClaw 供应商</span>
            <select
              value={selectedImportProviderId}
              onChange={(event) => setSelectedImportProviderId(event.target.value)}
            >
              <option value="">请选择</option>
              {openclawProviders.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.name}
                </option>
              ))}
            </select>
          </label>
          <div className="topbar-actions" style={{ alignItems: "end" }}>
            <button type="button" onClick={() => void handleImportOpenClawProvider()}>
              导入到 Hermes
            </button>
          </div>
        </div>
      </div>

      {message ? (
        <p className={messageTone === "success" ? "inline-message" : "error-inline-message"}>
          {message}
        </p>
      ) : null}

      <div className="provider-card-list">
        {providers.length === 0 ? (
          <div className="empty-state">还没有任何 Hermes 供应商。</div>
        ) : (
          providers.map((provider, index) => (
            <article key={provider.id} className="provider-card">
              <div className="provider-card-main">
                <div className={`provider-avatar ${avatarToneClasses[index % avatarToneClasses.length]}`}>
                  {provider.name.slice(0, 2).toUpperCase()}
                </div>
                <div className="provider-info">
                  <strong>{provider.name}</strong>
                  <span className="provider-url">{provider.base_url}</span>
                </div>
                <div className="provider-protocol-badge">{provider.plugin_mode}</div>
                <div className="provider-meta-block">
                  <span className="provider-balance-meta">{modelCounts.get(provider.id) ?? 0} 个模型</span>
                  {provider.source_openclaw_provider_id != null ? (
                    <span className="provider-source-meta">来自 OpenClaw #{provider.source_openclaw_provider_id}</span>
                  ) : null}
                </div>
                <div className="provider-card-actions">
                  <button type="button" className="secondary-button" onClick={() => onEdit(provider.id)}>
                    编辑
                  </button>
                  <button type="button" className="secondary-button" onClick={() => void handleDeleteProvider(provider.id)}>
                    删除
                  </button>
                </div>
              </div>
              {provider.notes ? <p className="provider-note">{provider.notes}</p> : null}
            </article>
          ))
        )}
      </div>
    </div>
  );
}

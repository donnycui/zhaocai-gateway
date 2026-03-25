import { useMemo, useState } from "react";

import { api, type Model, type Provider } from "../lib/api";

interface ProvidersPageProps {
  providers: Provider[];
  models: Model[];
  onRefresh: () => Promise<void>;
}

const defaultProviderForm = {
  name: "",
  base_url: "",
  provider_type: "openai",
  auth_scheme: "bearer",
  api_key: "",
  extra_headers: "{}",
};

const defaultModelForm = {
  provider_id: "",
  upstream_model: "",
  display_name: "",
  capabilities: "text",
  context_window: "",
  max_tokens: "",
};

export default function ProvidersPage({
  providers,
  models,
  onRefresh,
}: ProvidersPageProps) {
  const [providerForm, setProviderForm] = useState(defaultProviderForm);
  const [modelForm, setModelForm] = useState(defaultModelForm);
  const [validationMessage, setValidationMessage] = useState<string>("");
  const [syncMessage, setSyncMessage] = useState<string>("");
  const modelCounts = useMemo(() => {
    const counts = new Map<number, number>();
    models.forEach((model) => {
      counts.set(model.provider_id, (counts.get(model.provider_id) ?? 0) + 1);
    });
    return counts;
  }, [models]);

  async function handleCreateProvider(event: React.FormEvent) {
    event.preventDefault();
    await api.createProvider({
      ...providerForm,
      extra_headers: JSON.parse(providerForm.extra_headers || "{}"),
    });
    setProviderForm(defaultProviderForm);
    setValidationMessage("");
    await onRefresh();
  }

  async function handleValidateProvider() {
    const result = await api.validateProvider({
      ...providerForm,
      extra_headers: JSON.parse(providerForm.extra_headers || "{}"),
    });
    setValidationMessage(result.message);
  }

  async function handleSyncOpenRouterFree() {
    const result = await api.syncOpenRouterFree();
    setSyncMessage(
      `已同步免费模型 ${result.free_models_found} 个，新建 ${result.created} 个，更新 ${result.updated} 个。`,
    );
    await onRefresh();
  }

  async function handleCreateModel(event: React.FormEvent) {
    event.preventDefault();
    if (!modelForm.provider_id) return;
    await api.createModel({
      provider_id: Number(modelForm.provider_id),
      upstream_model: modelForm.upstream_model,
      display_name: modelForm.display_name,
      capabilities: modelForm.capabilities
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
      context_window: modelForm.context_window
        ? Number(modelForm.context_window)
        : null,
      max_tokens: modelForm.max_tokens ? Number(modelForm.max_tokens) : null,
      enabled: true,
    });
    setModelForm(defaultModelForm);
    await onRefresh();
  }

  return (
    <section className="page two-column">
      <div className="stack">
        <div className="panel">
          <div className="page-header">
            <div className="panel-header" style={{ marginBottom: 0 }}>
              <h3>上游服务</h3>
              <p>在控制面统一定义所有上游 Provider。</p>
            </div>
            <button className="secondary-button" onClick={() => void handleSyncOpenRouterFree()}>
              同步 OpenRouter 免费模型
            </button>
          </div>
          {syncMessage ? <p className="inline-message">{syncMessage}</p> : null}
          <table className="table">
            <thead>
              <tr>
                <th>名称</th>
                <th>类型</th>
                <th>接口地址</th>
                <th>模型数</th>
              </tr>
            </thead>
            <tbody>
              {providers.length === 0 ? (
                <tr>
                  <td colSpan={4} className="empty-cell">
                    还没有任何 Provider。
                  </td>
                </tr>
              ) : (
                providers.map((provider) => (
                  <tr key={provider.id}>
                    <td>{provider.name}</td>
                    <td>{provider.provider_type}</td>
                    <td className="truncate-cell">{provider.base_url}</td>
                    <td>{modelCounts.get(provider.id) ?? 0}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3>模型列表</h3>
            <p>这里展示可直接分配给设备的真实上游模型。</p>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>显示名</th>
                <th>上游模型</th>
                <th>服务 ID</th>
              </tr>
            </thead>
            <tbody>
              {models.length === 0 ? (
                <tr>
                  <td colSpan={3} className="empty-cell">
                    还没有任何模型。
                  </td>
                </tr>
              ) : (
                models.map((model) => (
                  <tr key={model.id}>
                    <td>{model.display_name}</td>
                    <td>{model.upstream_model}</td>
                    <td>{model.provider_id}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="stack">
        <form className="panel form-panel" onSubmit={handleCreateProvider}>
          <div className="panel-header">
            <h3>新增 Provider</h3>
            <p>录入一个最小可用的上游 Provider 定义。</p>
          </div>
          <label>
            <span>名称</span>
            <input
              value={providerForm.name}
              onChange={(event) =>
                setProviderForm((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>Base URL</span>
            <input
              value={providerForm.base_url}
              onChange={(event) =>
                setProviderForm((current) => ({
                  ...current,
                  base_url: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>服务类型</span>
            <input
              value={providerForm.provider_type}
              onChange={(event) =>
                setProviderForm((current) => ({
                  ...current,
                  provider_type: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>鉴权方式</span>
            <input
              value={providerForm.auth_scheme}
              onChange={(event) =>
                setProviderForm((current) => ({
                  ...current,
                  auth_scheme: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>API 密钥</span>
            <input
              value={providerForm.api_key}
              onChange={(event) =>
                setProviderForm((current) => ({
                  ...current,
                  api_key: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>额外请求头 JSON</span>
            <textarea
              value={providerForm.extra_headers}
              onChange={(event) =>
                setProviderForm((current) => ({
                  ...current,
                  extra_headers: event.target.value,
                }))
              }
            />
          </label>
          <div className="action-row">
            <button type="button" className="secondary-button" onClick={handleValidateProvider}>
              校验
            </button>
            <button type="submit">创建上游服务</button>
          </div>
          {validationMessage ? <p className="inline-message">{validationMessage}</p> : null}
        </form>

        <form className="panel form-panel" onSubmit={handleCreateModel}>
          <div className="panel-header">
            <h3>新增模型</h3>
            <p>把一个真实模型挂到已有 Provider 下。</p>
          </div>
          <label>
            <span>上游服务</span>
            <select
              value={modelForm.provider_id}
              onChange={(event) =>
                setModelForm((current) => ({
                  ...current,
                  provider_id: event.target.value,
                }))
              }
            >
              <option value="">请选择上游服务</option>
              {providers.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>上游模型名</span>
            <input
              value={modelForm.upstream_model}
              onChange={(event) =>
                setModelForm((current) => ({
                  ...current,
                  upstream_model: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>显示名称</span>
            <input
              value={modelForm.display_name}
              onChange={(event) =>
                setModelForm((current) => ({
                  ...current,
                  display_name: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>能力标签</span>
            <input
              value={modelForm.capabilities}
              onChange={(event) =>
                setModelForm((current) => ({
                  ...current,
                  capabilities: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>上下文窗口</span>
            <input
              value={modelForm.context_window}
              onChange={(event) =>
                setModelForm((current) => ({
                  ...current,
                  context_window: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>最大输出 Tokens</span>
            <input
              value={modelForm.max_tokens}
              onChange={(event) =>
                setModelForm((current) => ({
                  ...current,
                  max_tokens: event.target.value,
                }))
              }
            />
          </label>
          <button type="submit">创建模型</button>
        </form>
      </div>
    </section>
  );
}

import { useEffect, useMemo, useState } from "react";

import { api, type Model, type Provider } from "../lib/api";

type ProviderProtocol =
  | "openai-completions"
  | "openai-responses"
  | "anthropic-messages";

interface ProviderEditorPageProps {
  providerId: number | null;
  onBack: () => void;
  onSaved: () => Promise<void>;
}

interface EditableModel {
  id?: number;
  upstream_model: string;
  display_name: string;
  reasoning: boolean;
  input_modalities: string[];
  context_window: string;
  max_tokens: string;
  cost_input: string;
  cost_output: string;
  cost_cache_read: string;
  cost_cache_write: string;
}

const protocolOptions: Array<{ value: ProviderProtocol; label: string }> = [
  { value: "openai-completions", label: "OpenAI Completions" },
  { value: "openai-responses", label: "OpenAI Responses" },
  { value: "anthropic-messages", label: "Anthropic Messages" },
];

function toEditableModel(model?: Model): EditableModel {
  return {
    id: model?.id,
    upstream_model: model?.upstream_model ?? "",
    display_name: model?.display_name ?? "",
    reasoning: model?.reasoning ?? false,
    input_modalities: model?.input_modalities ?? ["text"],
    context_window: model?.context_window?.toString() ?? "",
    max_tokens: model?.max_tokens?.toString() ?? "",
    cost_input: model?.cost_input?.toString() ?? "",
    cost_output: model?.cost_output?.toString() ?? "",
    cost_cache_read: model?.cost_cache_read?.toString() ?? "",
    cost_cache_write: model?.cost_cache_write?.toString() ?? "",
  };
}

export default function ProviderEditorPage({
  providerId,
  onBack,
  onSaved,
}: ProviderEditorPageProps) {
  const isCreateMode = providerId == null;
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [messageTone, setMessageTone] = useState<"success" | "error">("success");
  const [provider, setProvider] = useState({
    name: "",
    base_url: "",
    provider_type: "openai-completions" as ProviderProtocol,
    api_key: "",
    enabled: true,
  });
  const [models, setModels] = useState<EditableModel[]>([toEditableModel()]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (providerId == null) return;
      setLoading(true);
      const payload = await api.getProvider(providerId);
      if (cancelled) return;
      setProvider({
        name: payload.provider.name,
        base_url: payload.provider.base_url,
        provider_type: (payload.provider.provider_type as ProviderProtocol) ?? "openai-completions",
        api_key: payload.provider.api_key_encrypted,
        enabled: payload.provider.enabled,
      });
      setModels(payload.models.length > 0 ? payload.models.map((model) => toEditableModel(model)) : [toEditableModel()]);
      setLoading(false);
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [providerId]);

  const title = useMemo(() => (isCreateMode ? "新增供应商" : `编辑供应商：${provider.name}`), [isCreateMode, provider.name]);

  function updateModel(index: number, patch: Partial<EditableModel>) {
    setModels((current) =>
      current.map((model, modelIndex) =>
        modelIndex === index ? { ...model, ...patch } : model,
      ),
    );
  }

  function addModel() {
    setModels((current) => [...current, toEditableModel()]);
  }

  function removeModel(index: number) {
    setModels((current) => current.filter((_, modelIndex) => modelIndex !== index));
  }

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    setMessage("");
    setLoading(true);
    const authScheme = provider.provider_type === "anthropic-messages" ? "x-api-key" : "bearer";

    try {
      let activeProviderId = providerId;
      if (isCreateMode) {
        const created = await api.createProvider({
          name: provider.name,
          base_url: provider.base_url,
          provider_type: provider.provider_type,
          auth_scheme: authScheme,
          api_key: provider.api_key,
          extra_headers: {},
        });
        activeProviderId = created.id;
      } else if (activeProviderId != null) {
        await api.updateProvider(activeProviderId, {
          name: provider.name,
          base_url: provider.base_url,
          provider_type: provider.provider_type,
          auth_scheme: authScheme,
          api_key: provider.api_key,
          enabled: provider.enabled,
          extra_headers: {},
        });
      }

      if (activeProviderId == null) {
        throw new Error("Provider ID is missing");
      }

      const existing = isCreateMode ? [] : (await api.getProvider(activeProviderId)).models;
      const existingIds = new Set(existing.map((model) => model.id));
      const nextIds = new Set<number>();

      for (const model of models.filter((entry) => entry.upstream_model.trim() && entry.display_name.trim())) {
        const payload = {
          upstream_model: model.upstream_model.trim(),
          display_name: model.display_name.trim(),
          capabilities: ["text"],
          reasoning: model.reasoning,
          input_modalities: model.input_modalities,
          context_window: model.context_window ? Number(model.context_window) : null,
          max_tokens: model.max_tokens ? Number(model.max_tokens) : null,
          cost_input: model.cost_input ? Number(model.cost_input) : null,
          cost_output: model.cost_output ? Number(model.cost_output) : null,
          cost_cache_read: model.cost_cache_read ? Number(model.cost_cache_read) : null,
          cost_cache_write: model.cost_cache_write ? Number(model.cost_cache_write) : null,
          enabled: true,
        };
        if (model.id) {
          nextIds.add(model.id);
          await api.updateModel(model.id, payload);
        } else {
          const created = await api.createModel({
            provider_id: activeProviderId,
            ...payload,
          });
          nextIds.add(created.id);
        }
      }

      for (const existingModelId of existingIds) {
        if (!nextIds.has(existingModelId)) {
          await api.deleteModel(existingModelId);
        }
      }

      setMessageTone("success");
      setMessage("保存成功。");
      await onSaved();
    } catch (error) {
      setMessageTone("error");
      setMessage(error instanceof Error ? error.message : "保存失败。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page">
      <form className="panel form-panel" onSubmit={handleSave}>
        <div className="page-header">
          <div className="panel-header" style={{ marginBottom: 0 }}>
            <h3>{title}</h3>
            <p>配置供应商基础信息，并在下方维护模型列表。</p>
          </div>
          <div className="topbar-actions">
            <button type="button" className="secondary-button" onClick={onBack}>
              返回
            </button>
            <button type="submit" disabled={loading}>
              {loading ? "加载中" : "保存"}
            </button>
          </div>
        </div>
        {message ? (
          <p className={messageTone === "success" ? "inline-message" : "error-inline-message"}>
            {message}
          </p>
        ) : null}

        <div className="editor-grid">
          <label>
            <span>名称</span>
            <input
              value={provider.name}
              onChange={(event) => setProvider((current) => ({ ...current, name: event.target.value }))}
            />
          </label>
          <label>
            <span>API 协议</span>
            <select
              value={provider.provider_type}
              onChange={(event) =>
                setProvider((current) => ({
                  ...current,
                  provider_type: event.target.value as ProviderProtocol,
                }))
              }
            >
              {protocolOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>接口地址</span>
            <input
              value={provider.base_url}
              onChange={(event) => setProvider((current) => ({ ...current, base_url: event.target.value }))}
            />
          </label>
          <label>
            <span>API 密钥</span>
            <input
              value={provider.api_key}
              onChange={(event) => setProvider((current) => ({ ...current, api_key: event.target.value }))}
            />
          </label>
        </div>

        <div className="panel-header" style={{ marginTop: 10 }}>
          <h3>模型列表</h3>
          <p>模型 ID 用于 API 调用，显示名称用于界面展示。</p>
        </div>

        <div className="model-card-list">
          {models.map((model, index) => (
            <div key={model.id ?? `new-${index}`} className="model-editor-card">
              <div className="model-card-header">
                <span className="model-badge">{index === 0 ? "默认模型" : `模型 ${index + 1}`}</span>
                <button type="button" className="secondary-button" onClick={() => removeModel(index)}>
                  删除
                </button>
              </div>

              <div className="editor-grid">
                <label>
                  <span>模型 ID</span>
                  <input
                    value={model.upstream_model}
                    onChange={(event) => updateModel(index, { upstream_model: event.target.value })}
                  />
                </label>
                <label>
                  <span>显示名称</span>
                  <input
                    value={model.display_name}
                    onChange={(event) => updateModel(index, { display_name: event.target.value })}
                  />
                </label>
              </div>

              <details className="advanced-section">
                <summary>高级选项</summary>
                <div className="advanced-grid">
                  <div className="option-card">
                    <div className="option-card-header">
                      <span>推理模式</span>
                      <span className="option-card-hint">
                        {model.reasoning ? "开启" : "关闭"}
                      </span>
                    </div>
                    <label className={`toggle-control compact-toggle ${model.reasoning ? "selected" : ""}`}>
                      <input
                        type="checkbox"
                        checked={model.reasoning}
                        onChange={(event) => updateModel(index, { reasoning: event.target.checked })}
                      />
                      <span className="toggle-indicator" aria-hidden="true" />
                      <span>启用推理</span>
                    </label>
                  </div>

                  <div className="option-card">
                    <div className="option-card-header">
                      <span>输入类型</span>
                      <span className="option-card-hint">选择模型支持的输入形式</span>
                    </div>
                    <div className="input-type-pills">
                      <label
                        className={`choice-pill ${model.input_modalities.includes("text") ? "selected" : ""}`}
                      >
                        <input
                          type="checkbox"
                          checked={model.input_modalities.includes("text")}
                          onChange={(event) => {
                            const next = event.target.checked
                              ? Array.from(new Set([...model.input_modalities, "text"]))
                              : model.input_modalities.filter((item) => item !== "text");
                            updateModel(index, { input_modalities: next });
                          }}
                        />
                        <span className="choice-indicator" aria-hidden="true" />
                        <span>text</span>
                      </label>
                      <label
                        className={`choice-pill ${model.input_modalities.includes("image") ? "selected" : ""}`}
                      >
                        <input
                          type="checkbox"
                          checked={model.input_modalities.includes("image")}
                          onChange={(event) => {
                            const next = event.target.checked
                              ? Array.from(new Set([...model.input_modalities, "image"]))
                              : model.input_modalities.filter((item) => item !== "image");
                            updateModel(index, { input_modalities: next });
                          }}
                        />
                        <span className="choice-indicator" aria-hidden="true" />
                        <span>image</span>
                      </label>
                    </div>
                  </div>

                  <label>
                    <span>上下文窗口</span>
                    <input
                      value={model.context_window}
                      onChange={(event) => updateModel(index, { context_window: event.target.value })}
                    />
                  </label>
                  <label>
                    <span>最大输出 Tokens</span>
                    <input
                      value={model.max_tokens}
                      onChange={(event) => updateModel(index, { max_tokens: event.target.value })}
                    />
                  </label>
                  <label>
                    <span>输入价格 ($/M tokens)</span>
                    <input
                      value={model.cost_input}
                      onChange={(event) => updateModel(index, { cost_input: event.target.value })}
                    />
                  </label>
                  <label>
                    <span>输出价格 ($/M tokens)</span>
                    <input
                      value={model.cost_output}
                      onChange={(event) => updateModel(index, { cost_output: event.target.value })}
                    />
                  </label>
                  <label>
                    <span>缓存读取价格 ($/M tokens)</span>
                    <input
                      value={model.cost_cache_read}
                      onChange={(event) => updateModel(index, { cost_cache_read: event.target.value })}
                    />
                  </label>
                  <label>
                    <span>缓存写入价格 ($/M tokens)</span>
                    <input
                      value={model.cost_cache_write}
                      onChange={(event) => updateModel(index, { cost_cache_write: event.target.value })}
                    />
                  </label>
                </div>
              </details>
            </div>
          ))}
        </div>

        <div className="topbar-actions">
          <button type="button" className="secondary-button" onClick={addModel}>
            添加模型
          </button>
        </div>

      </form>
    </section>
  );
}

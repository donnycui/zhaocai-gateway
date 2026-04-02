import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { api, type DiscoveredProviderModel, type Model } from "../lib/api";

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

interface DiscoverGroup {
  label: string;
  models: DiscoveredProviderModel[];
}

const protocolOptions: Array<{ value: ProviderProtocol; label: string }> = [
  { value: "openai-completions", label: "OpenAI Completions" },
  { value: "openai-responses", label: "OpenAI Responses" },
  { value: "anthropic-messages", label: "Anthropic Messages" },
];

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

function toEditableModelFromDiscoveredModel(model: DiscoveredProviderModel): EditableModel {
  return {
    upstream_model: model.upstream_model,
    display_name: model.display_name,
    reasoning: model.reasoning,
    input_modalities: model.input_modalities.length > 0 ? model.input_modalities : ["text"],
    context_window: model.context_window?.toString() ?? "",
    max_tokens: model.max_tokens?.toString() ?? "",
    cost_input: model.cost_input?.toString() ?? "",
    cost_output: model.cost_output?.toString() ?? "",
    cost_cache_read: model.cost_cache_read?.toString() ?? "",
    cost_cache_write: model.cost_cache_write?.toString() ?? "",
  };
}

function normalizeModelKey(value: string): string {
  return value.trim().toLowerCase();
}

function isBlankEditableModel(model: EditableModel): boolean {
  return !model.id && !model.upstream_model.trim() && !model.display_name.trim();
}

function getProviderAuthScheme(providerType: ProviderProtocol): string {
  return providerType === "anthropic-messages" ? "x-api-key" : "bearer";
}

function buildModelCapabilities(model: EditableModel): string[] {
  const capabilities = ["text"];
  if (model.input_modalities.includes("image")) {
    capabilities.push("multimodal");
  }
  if (model.input_modalities.includes("audio")) {
    capabilities.push("audio");
  }
  if (model.reasoning) {
    capabilities.push("reasoning");
  }
  return capabilities;
}

function buildModelGroupLabel(model: DiscoveredProviderModel): string {
  const source = (model.display_name || model.upstream_model).toLowerCase();
  const tail = source.split("/").pop() ?? source;
  const tokens = tail.split(/[-_:]/).filter(Boolean);
  if (tokens.length === 0) {
    return "other";
  }

  if (tokens[0] === "claude" && tokens[1]) {
    return `claude-${tokens[1]}`;
  }
  if (tokens[0] === "gpt" && tokens[1]) {
    return `gpt-${tokens[1]}`;
  }
  if (tokens[0] === "gemini" && tokens[1]) {
    return `gemini-${tokens[1]}`;
  }
  if (tokens[0] === "qwen" && tokens[1]) {
    return `qwen-${tokens[1]}`;
  }
  if (tokens[0] === "deepseek" && tokens[1]) {
    return `deepseek-${tokens[1]}`;
  }
  return tokens.slice(0, Math.min(tokens.length, 2)).join("-");
}

function buildModelAvatarLabel(model: DiscoveredProviderModel): string {
  const source = model.display_name || model.upstream_model;
  const tail = source.split("/").pop() ?? source;
  const compact = tail.replace(/[^a-zA-Z0-9]/g, "").toUpperCase();
  return compact.slice(0, 2) || "ML";
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
  const [discoverOpen, setDiscoverOpen] = useState(false);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [discoverMessage, setDiscoverMessage] = useState("");
  const [discoverMessageTone, setDiscoverMessageTone] = useState<"success" | "error">("success");
  const [discoverSearch, setDiscoverSearch] = useState("");
  const [discoveredModels, setDiscoveredModels] = useState<DiscoveredProviderModel[]>([]);
  const [selectedDiscoveredIds, setSelectedDiscoveredIds] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (providerId == null) {
        return;
      }

      setLoading(true);
      try {
        const payload = await api.getProvider(providerId);
        if (cancelled) {
          return;
        }
        setProvider({
          name: payload.provider.name,
          base_url: payload.provider.base_url,
          provider_type: (payload.provider.provider_type as ProviderProtocol) ?? "openai-completions",
          api_key: payload.provider.api_key_encrypted,
          enabled: payload.provider.enabled,
        });
        setModels(payload.models.length > 0 ? payload.models.map((model) => toEditableModel(model)) : [toEditableModel()]);
      } catch (error) {
        if (!cancelled) {
          setMessageTone("error");
          setMessage(error instanceof Error ? error.message : "加载供应商失败。");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [providerId]);

  const title = useMemo(
    () => (isCreateMode ? "新增 OpenClaw 供应商" : `编辑 OpenClaw 供应商：${provider.name}`),
    [isCreateMode, provider.name],
  );

  const existingModelKeys = useMemo(
    () =>
      new Set(
        models
          .map((model) => normalizeModelKey(model.upstream_model))
          .filter((modelId) => modelId.length > 0),
      ),
    [models],
  );

  const deferredDiscoverSearch = useDeferredValue(discoverSearch.trim().toLowerCase());

  const groupedDiscoveredModels = useMemo<DiscoverGroup[]>(() => {
    const filtered = discoveredModels.filter((model) => {
      if (!deferredDiscoverSearch) {
        return true;
      }
      const haystack = `${model.upstream_model} ${model.display_name} ${buildModelGroupLabel(model)}`.toLowerCase();
      return haystack.includes(deferredDiscoverSearch);
    });

    const groups = new Map<string, DiscoveredProviderModel[]>();
    filtered.forEach((model) => {
      const groupLabel = buildModelGroupLabel(model);
      const currentGroup = groups.get(groupLabel) ?? [];
      currentGroup.push(model);
      groups.set(groupLabel, currentGroup);
    });

    return Array.from(groups.entries())
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([label, groupModels]) => ({ label, models: groupModels }));
  }, [deferredDiscoverSearch, discoveredModels]);

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
    const authScheme = getProviderAuthScheme(provider.provider_type);

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
          capabilities: buildModelCapabilities(model),
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

  async function fetchDiscoveredModels() {
    setDiscoverOpen(true);
    setDiscoverLoading(true);
    setDiscoverMessage("");
    setDiscoverMessageTone("success");

    if (!provider.base_url.trim()) {
      setDiscoveredModels([]);
      setSelectedDiscoveredIds([]);
      setDiscoverMessageTone("error");
      setDiscoverMessage("请先填写 API 地址，再获取模型列表。");
      setDiscoverLoading(false);
      return;
    }

    try {
      const result = await api.discoverProviderModels({
        base_url: provider.base_url.trim(),
        provider_type: provider.provider_type,
        auth_scheme: getProviderAuthScheme(provider.provider_type),
        api_key: provider.api_key.trim(),
        extra_headers: {},
      });
      setDiscoveredModels(result.models);
      setSelectedDiscoveredIds(
        result.models
          .filter((model) => !existingModelKeys.has(normalizeModelKey(model.upstream_model)))
          .map((model) => model.upstream_model),
      );
      setDiscoverMessageTone("success");
      setDiscoverMessage(
        result.count > 0
          ? `已拉取 ${result.count} 个模型，请选择后导入。`
          : "上游返回了空模型列表。",
      );
    } catch (error) {
      setDiscoveredModels([]);
      setSelectedDiscoveredIds([]);
      setDiscoverMessageTone("error");
      setDiscoverMessage(error instanceof Error ? error.message : "拉取模型列表失败。");
    } finally {
      setDiscoverLoading(false);
    }
  }

  function toggleDiscoveredModel(modelId: string) {
    setSelectedDiscoveredIds((current) =>
      current.includes(modelId)
        ? current.filter((item) => item !== modelId)
        : [...current, modelId],
    );
  }

  function handleSelectVisibleDiscoveredModels() {
    const visibleIds = groupedDiscoveredModels
      .flatMap((group) => group.models)
      .map((model) => model.upstream_model)
      .filter((modelId) => !existingModelKeys.has(normalizeModelKey(modelId)));
    setSelectedDiscoveredIds((current) => Array.from(new Set([...current, ...visibleIds])));
  }

  function handleClearDiscoveredSelection() {
    setSelectedDiscoveredIds([]);
  }

  function handleImportSelectedDiscoveredModels() {
    const selectedIds = new Set(selectedDiscoveredIds);
    const selectedModels = discoveredModels.filter((model) => selectedIds.has(model.upstream_model));
    if (selectedModels.length === 0) {
      setDiscoverMessageTone("error");
      setDiscoverMessage("请先选择至少一个模型。");
      return;
    }

    const nextModels = models.length === 1 && isBlankEditableModel(models[0]) ? [] : [...models];
    const nextKeys = new Set(
      nextModels
        .map((model) => normalizeModelKey(model.upstream_model))
        .filter((modelId) => modelId.length > 0),
    );

    let imported = 0;
    let skipped = 0;
    selectedModels.forEach((model) => {
      const normalizedModelId = normalizeModelKey(model.upstream_model);
      if (nextKeys.has(normalizedModelId)) {
        skipped += 1;
        return;
      }
      nextModels.push(toEditableModelFromDiscoveredModel(model));
      nextKeys.add(normalizedModelId);
      imported += 1;
    });

    setModels(nextModels.length > 0 ? nextModels : [toEditableModel()]);
    setDiscoverOpen(false);
    setDiscoverSearch("");
    setMessageTone(imported > 0 ? "success" : "error");
    if (imported > 0) {
      setMessage(
        skipped > 0
          ? `已导入 ${imported} 个模型，跳过 ${skipped} 个重复项。`
          : `已导入 ${imported} 个模型。`,
      );
      return;
    }
    setMessage("所选模型已存在，未导入新模型。");
  }

  return (
    <section className="page">
      <form className="panel form-panel" onSubmit={handleSave}>
        <div className="page-header">
          <div className="panel-header" style={{ marginBottom: 0 }}>
            <h3>{title}</h3>
            <p>配置 OpenClaw 供应商基础信息，并维护将同步到节点上的模型列表。</p>
          </div>
          <div className="topbar-actions">
            <button type="button" className="secondary-button" onClick={onBack}>
              返回
            </button>
            <button type="submit" disabled={loading}>
              {loading ? "处理中..." : "保存"}
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
          <h3>OpenClaw 模型列表</h3>
          <p>可手动维护模型，也可以直接从当前上游拉取后批量导入。</p>
        </div>

        <div className="model-toolbar">
          <button type="button" className="secondary-button" onClick={() => void fetchDiscoveredModels()}>
            获取模型列表
          </button>
          <button type="button" className="secondary-button" onClick={addModel}>
            添加模型
          </button>
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
                      <span className="option-card-hint">{model.reasoning ? "开启" : "关闭"}</span>
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
      </form>

      {discoverOpen ? (
        <div className="modal-backdrop" role="presentation" onClick={() => setDiscoverOpen(false)}>
          <div
            className="modal-panel model-discovery-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="provider-model-discovery-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <h3 id="provider-model-discovery-title">获取模型列表</h3>
                <p>从当前供应商的 `/models` 拉取模型后，选择要导入到 OpenClaw 的条目。</p>
              </div>
              <button type="button" className="secondary-button" onClick={() => setDiscoverOpen(false)}>
                关闭
              </button>
            </div>

            <div className="model-picker-toolbar">
              <input
                placeholder="搜索模型 ID 或名称"
                value={discoverSearch}
                onChange={(event) => setDiscoverSearch(event.target.value)}
              />
              <div className="topbar-actions">
                <button type="button" className="secondary-button" onClick={handleSelectVisibleDiscoveredModels}>
                  全选可见
                </button>
                <button type="button" className="secondary-button" onClick={handleClearDiscoveredSelection}>
                  清空选择
                </button>
                <button type="button" className="secondary-button" onClick={() => void fetchDiscoveredModels()}>
                  {discoverLoading ? "刷新中..." : "刷新"}
                </button>
              </div>
            </div>

            {discoverMessage ? (
              <p className={discoverMessageTone === "success" ? "inline-message" : "error-inline-message"}>
                {discoverMessage}
              </p>
            ) : null}

            <div className="model-discovery-summary">
              <span>已发现 {discoveredModels.length} 个模型</span>
              <span>已选择 {selectedDiscoveredIds.length} 个</span>
            </div>

            <div className="model-picker-groups">
              {groupedDiscoveredModels.length === 0 ? (
                <div className="empty-state">{discoverLoading ? "正在拉取模型列表..." : "没有可显示的模型。"}</div>
              ) : (
                groupedDiscoveredModels.map((group, groupIndex) => (
                  <section key={group.label} className="model-picker-group">
                    <div className="model-picker-group-header">
                      <div>
                        <strong>{group.label}</strong>
                        <span>{group.models.length} 个模型</span>
                      </div>
                    </div>
                    <div className="model-picker-group-list">
                      {group.models.map((model, modelIndex) => {
                        const normalizedModelId = normalizeModelKey(model.upstream_model);
                        const alreadyImported = existingModelKeys.has(normalizedModelId);
                        const toneClass =
                          avatarToneClasses[(groupIndex + modelIndex) % avatarToneClasses.length];
                        return (
                          <label
                            key={model.upstream_model}
                            className={`model-picker-row ${alreadyImported ? "is-disabled" : ""}`}
                          >
                            <input
                              type="checkbox"
                              checked={selectedDiscoveredIds.includes(model.upstream_model)}
                              disabled={alreadyImported}
                              onChange={() => toggleDiscoveredModel(model.upstream_model)}
                            />
                            <div className={`model-picker-icon ${toneClass}`}>
                              {buildModelAvatarLabel(model)}
                            </div>
                            <div className="model-picker-row-main">
                              <strong>{model.display_name}</strong>
                              <span>{model.upstream_model}</span>
                            </div>
                            <div className="model-picker-row-tags">
                              {model.reasoning ? <span className="mini-pill">推理</span> : null}
                              {model.input_modalities.includes("image") ? (
                                <span className="mini-pill mini-pill-accent">图像</span>
                              ) : null}
                              {alreadyImported ? <span className="mini-pill mini-pill-muted">已在列表</span> : null}
                            </div>
                          </label>
                        );
                      })}
                    </div>
                  </section>
                ))
              )}
            </div>

            <div className="modal-footer">
              <button type="button" className="secondary-button" onClick={() => setDiscoverOpen(false)}>
                取消
              </button>
              <button
                type="button"
                onClick={handleImportSelectedDiscoveredModels}
                disabled={discoverLoading || selectedDiscoveredIds.length === 0}
              >
                导入选中模型
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

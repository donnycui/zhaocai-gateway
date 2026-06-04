import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { api, type DiscoveredProviderModel, type HermesModel } from "../lib/api";

interface HermesProviderEditorPageProps {
  providerId: number | null;
  onBack: () => void;
  onSaved: () => Promise<void>;
}

interface EditableHermesModel {
  id?: number;
  upstream_model: string;
  display_name: string;
  enabled: boolean;
}

interface DiscoverGroup {
  label: string;
  models: DiscoveredProviderModel[];
}

const DEFAULT_HEADERS_TEXT = JSON.stringify(
  {
    "User-Agent": "claude-code/0.1.0",
    "HTTP-Referer": "https://hermes-agent.nousresearch.com",
    "X-Title": "Hermes",
  },
  null,
  2,
);

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

function toEditableModel(model?: HermesModel): EditableHermesModel {
  return {
    id: model?.id,
    upstream_model: model?.upstream_model ?? "",
    display_name: model?.display_name ?? "",
    enabled: model?.enabled ?? true,
  };
}

function toEditableModelFromDiscoveredModel(model: DiscoveredProviderModel): EditableHermesModel {
  return {
    upstream_model: model.upstream_model,
    display_name: model.display_name,
    enabled: true,
  };
}

function normalizeModelKey(value: string): string {
  return value.trim().toLowerCase();
}

function isBlankEditableModel(model: EditableHermesModel): boolean {
  return !model.id && !model.upstream_model.trim() && !model.display_name.trim();
}

function buildModelGroupLabel(model: DiscoveredProviderModel): string {
  if (model.owner?.trim()) {
    return model.owner.trim();
  }

  const source = model.upstream_model.trim().toLowerCase();
  const segments = source.split("/").filter(Boolean);
  if (segments.length >= 2) {
    const leading = segments[0];
    if (["pro", "free", "paid", "premium"].includes(leading)) {
      return segments[1];
    }
    return leading;
  }

  const fallback = (model.display_name || model.upstream_model).toLowerCase();
  const tokens = fallback.split(/[-_:]/).filter(Boolean);
  if (tokens[0]?.startsWith("glm")) {
    return "bigmodel";
  }
  return tokens[0] || "other";
}

function buildModelAvatarLabel(model: DiscoveredProviderModel): string {
  const source = model.display_name || model.upstream_model;
  const tail = source.split("/").pop() ?? source;
  const compact = tail.replace(/[^a-zA-Z0-9]/g, "").toUpperCase();
  return compact.slice(0, 2) || "ML";
}

function parseHeadersJson(rawText: string): Record<string, string> {
  const parsed = JSON.parse(rawText || "{}") as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("特殊 Headers 必须是 JSON object。");
  }
  return Object.fromEntries(
    Object.entries(parsed).map(([key, value]) => [String(key), String(value)]),
  );
}

export default function HermesProviderEditorPage({
  providerId,
  onBack,
  onSaved,
}: HermesProviderEditorPageProps) {
  const isCreateMode = providerId == null;
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [messageTone, setMessageTone] = useState<"success" | "error">("success");
  const [provider, setProvider] = useState({
    name: "",
    base_url: "",
    api_key: "",
    enabled: true,
    notes: "",
    plugin_mode: "none",
  });
  const [defaultHeadersText, setDefaultHeadersText] = useState(DEFAULT_HEADERS_TEXT);
  const [models, setModels] = useState<EditableHermesModel[]>([toEditableModel()]);
  const [discoverOpen, setDiscoverOpen] = useState(false);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [discoverMessage, setDiscoverMessage] = useState("");
  const [discoverMessageTone, setDiscoverMessageTone] = useState<"success" | "error">("success");
  const [discoverSearch, setDiscoverSearch] = useState("");
  const [discoveredModels, setDiscoveredModels] = useState<DiscoveredProviderModel[]>([]);
  const [selectedDiscoveredIds, setSelectedDiscoveredIds] = useState<string[]>([]);
  const [expandedDiscoverGroups, setExpandedDiscoverGroups] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (providerId == null) return;

      setLoading(true);
      try {
        const payload = await api.getHermesProvider(providerId);
        if (cancelled) return;
        setProvider({
          name: payload.provider.name,
          base_url: payload.provider.base_url,
          api_key: payload.provider.api_key_encrypted,
          enabled: payload.provider.enabled,
          notes: payload.provider.notes,
          plugin_mode: payload.provider.plugin_mode,
        });
        setDefaultHeadersText(
          Object.keys(payload.provider.default_headers_json ?? {}).length > 0
            ? JSON.stringify(payload.provider.default_headers_json, null, 2)
            : DEFAULT_HEADERS_TEXT,
        );
        setModels(payload.models.length > 0 ? payload.models.map((model) => toEditableModel(model)) : [toEditableModel()]);
      } catch (error) {
        if (!cancelled) {
          setMessageTone("error");
          setMessage(error instanceof Error ? error.message : "加载 Hermes 供应商失败。");
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
    () => (isCreateMode ? "新增 Hermes 供应商" : `编辑 Hermes 供应商：${provider.name}`),
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

  function resolveDefaultHeadersForSave(): Record<string, string> {
    if (provider.plugin_mode !== "default_headers") {
      return {};
    }
    return parseHeadersJson(defaultHeadersText);
  }

  function updateModel(index: number, patch: Partial<EditableHermesModel>) {
    setModels((current) =>
      current.map((model, currentIndex) => (currentIndex === index ? { ...model, ...patch } : model)),
    );
  }

  function addModel() {
    setModels((current) => [...current, toEditableModel()]);
  }

  function removeModel(index: number) {
    setModels((current) => current.filter((_, currentIndex) => currentIndex !== index));
  }

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage("");

    let default_headers_json: Record<string, string> = {};
    try {
      default_headers_json = resolveDefaultHeadersForSave();
    } catch (error) {
      setMessageTone("error");
      setMessage(error instanceof Error ? error.message : "特殊 Headers 不是合法 JSON。");
      setLoading(false);
      return;
    }

    try {
      let activeProviderId = providerId;
      if (isCreateMode) {
        const created = await api.createHermesProvider({
          name: provider.name,
          base_url: provider.base_url,
          api_key: provider.api_key,
          enabled: provider.enabled,
          notes: provider.notes,
          plugin_mode: provider.plugin_mode,
          default_headers_json,
        });
        activeProviderId = created.id;
      } else if (activeProviderId != null) {
        await api.updateHermesProvider(activeProviderId, {
          name: provider.name,
          base_url: provider.base_url,
          api_key: provider.api_key,
          enabled: provider.enabled,
          notes: provider.notes,
          plugin_mode: provider.plugin_mode,
          default_headers_json,
        });
      }

      if (activeProviderId == null) {
        throw new Error("Hermes provider ID is missing");
      }

      const existing = isCreateMode ? [] : (await api.getHermesProvider(activeProviderId)).models;
      const existingIds = new Set(existing.map((model) => model.id));
      const nextIds = new Set<number>();

      for (const model of models.filter((entry) => entry.upstream_model.trim() && entry.display_name.trim())) {
        const payload = {
          upstream_model: model.upstream_model.trim(),
          display_name: model.display_name.trim(),
          enabled: model.enabled,
        };
        if (model.id) {
          nextIds.add(model.id);
          await api.updateHermesModel(model.id, payload);
        } else {
          const created = await api.createHermesModel({
            provider_id: activeProviderId,
            ...payload,
          });
          nextIds.add(created.id);
        }
      }

      for (const existingModelId of existingIds) {
        if (!nextIds.has(existingModelId)) {
          await api.deleteHermesModel(existingModelId);
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
      setDiscoverMessage("请先填写接口地址，再获取模型列表。");
      setDiscoverLoading(false);
      return;
    }

    let default_headers_json: Record<string, string> = {};
    try {
      default_headers_json = resolveDefaultHeadersForSave();
    } catch (error) {
      setDiscoveredModels([]);
      setSelectedDiscoveredIds([]);
      setDiscoverMessageTone("error");
      setDiscoverMessage(error instanceof Error ? error.message : "特殊 Headers 不是合法 JSON。");
      setDiscoverLoading(false);
      return;
    }

    try {
      const result = await api.discoverHermesProviderModels({
        base_url: provider.base_url.trim(),
        api_key: provider.api_key.trim(),
        default_headers_json,
      });
      setDiscoveredModels(result.models);
      setSelectedDiscoveredIds([]);
      const nextExpanded: Record<string, boolean> = {};
      result.models.forEach((model) => {
        nextExpanded[buildModelGroupLabel(model)] = false;
      });
      setExpandedDiscoverGroups(nextExpanded);
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

  function toggleDiscoveredGroup(groupLabel: string) {
    setExpandedDiscoverGroups((current) => ({
      ...current,
      [groupLabel]: !current[groupLabel],
    }));
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
            <p>配置 Hermes 供应商基础信息，并维护将同步到节点上的模型列表。</p>
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
            <input value={provider.name} onChange={(event) => setProvider((current) => ({ ...current, name: event.target.value }))} />
          </label>
          <label>
            <span>接口地址</span>
            <input value={provider.base_url} onChange={(event) => setProvider((current) => ({ ...current, base_url: event.target.value }))} />
          </label>
          <label>
            <span>API 密钥</span>
            <input value={provider.api_key} onChange={(event) => setProvider((current) => ({ ...current, api_key: event.target.value }))} />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={provider.enabled}
              onChange={(event) => setProvider((current) => ({ ...current, enabled: event.target.checked }))}
            />
            <span>启用 Hermes provider</span>
          </label>
        </div>

        <label>
          <span>备注</span>
          <textarea value={provider.notes} onChange={(event) => setProvider((current) => ({ ...current, notes: event.target.value }))} />
        </label>

        <div className="builder-card">
          <div className="builder-card-header">
            <div>
              <strong>特殊 Headers 插件</strong>
              <span>普通 OpenAI 兼容中转站保持关闭；遇到 403 或模型列表失败时启用。</span>
            </div>
          </div>
          <div className="builder-grid">
            <label>
              <span>插件模式</span>
              <select
                value={provider.plugin_mode}
                onChange={(event) => setProvider((current) => ({ ...current, plugin_mode: event.target.value }))}
              >
                <option value="none">不生成插件</option>
                <option value="default_headers">生成 default_headers 插件</option>
              </select>
            </label>
            <div className="option-card">
              <div className="option-card-header">
                <span>同步产物</span>
                <span className="option-card-hint">agent 自动写入</span>
              </div>
              <code className="inline-code">~/.hermes/plugins/model-providers/{provider.name || "provider"}/__init__.py</code>
            </div>
          </div>
          {provider.plugin_mode === "default_headers" ? (
            <label>
              <span>default_headers JSON</span>
              <textarea
                className="code-textarea"
                value={defaultHeadersText}
                onChange={(event) => setDefaultHeadersText(event.target.value)}
              />
            </label>
          ) : null}
        </div>

        <div className="panel-header" style={{ marginTop: 10 }}>
          <h3>Hermes 模型列表</h3>
          <p>模型会按 `provider/model-id` 格式编译进 `config.yaml`。</p>
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
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={model.enabled}
                  onChange={(event) => updateModel(index, { enabled: event.target.checked })}
                />
                <span>启用这个 Hermes 模型</span>
              </label>
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
            aria-labelledby="hermes-provider-model-discovery-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <h3 id="hermes-provider-model-discovery-title">获取模型列表</h3>
                <p>从当前供应商的 `/models` 拉取模型后，选择要导入到 Hermes 的条目。</p>
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
                      <div className="model-picker-group-labels">
                        <strong>{group.label}</strong>
                        <span className="model-picker-group-count">{group.models.length} 个模型</span>
                      </div>
                      <button
                        type="button"
                        className="model-picker-group-toggle-button"
                        onClick={() => toggleDiscoveredGroup(group.label)}
                      >
                        {expandedDiscoverGroups[group.label] ? "收起" : "展开"}
                      </button>
                    </div>
                    {expandedDiscoverGroups[group.label] ? (
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
                    ) : null}
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

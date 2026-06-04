import { useEffect, useMemo, useState } from "react";

import { api, type HermesModel } from "../lib/api";

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

function toEditableModel(model?: HermesModel): EditableHermesModel {
  return {
    id: model?.id,
    upstream_model: model?.upstream_model ?? "",
    display_name: model?.display_name ?? "",
    enabled: model?.enabled ?? true,
  };
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
  const [defaultHeadersText, setDefaultHeadersText] = useState("{\n  \"HTTP-Referer\": \"https://hermes-agent.nousresearch.com\",\n  \"X-Title\": \"Hermes\"\n}");
  const [models, setModels] = useState<EditableHermesModel[]>([toEditableModel()]);

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
          JSON.stringify(payload.provider.default_headers_json ?? {}, null, 2),
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

  function updateModel(index: number, patch: Partial<EditableHermesModel>) {
    setModels((current) => current.map((model, currentIndex) => (currentIndex === index ? { ...model, ...patch } : model)));
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
      const parsed = JSON.parse(defaultHeadersText || "{}") as Record<string, unknown>;
      default_headers_json = Object.fromEntries(
        Object.entries(parsed ?? {}).map(([key, value]) => [String(key), String(value)]),
      );
    } catch {
      setMessageTone("error");
      setMessage("`default_headers_json` 不是合法 JSON。");
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

  return (
    <section className="page">
      <form className="panel form-panel" onSubmit={handleSave}>
        <div className="page-header">
          <div className="panel-header" style={{ marginBottom: 0 }}>
            <h3>{title}</h3>
            <p>配置 Hermes provider、默认 headers 插件模式，以及同步到节点上的模型列表。</p>
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
            <span>插件模式</span>
            <select
              value={provider.plugin_mode}
              onChange={(event) => setProvider((current) => ({ ...current, plugin_mode: event.target.value }))}
            >
              <option value="none">none</option>
              <option value="default_headers">default_headers</option>
            </select>
          </label>
          <label>
            <span>接口地址</span>
            <input value={provider.base_url} onChange={(event) => setProvider((current) => ({ ...current, base_url: event.target.value }))} />
          </label>
          <label>
            <span>API 密钥</span>
            <input value={provider.api_key} onChange={(event) => setProvider((current) => ({ ...current, api_key: event.target.value }))} />
          </label>
        </div>

        <label>
          <span>备注</span>
          <textarea value={provider.notes} onChange={(event) => setProvider((current) => ({ ...current, notes: event.target.value }))} />
        </label>

        <label>
          <span>default_headers_json</span>
          <textarea value={defaultHeadersText} onChange={(event) => setDefaultHeadersText(event.target.value)} />
        </label>

        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={provider.enabled}
            onChange={(event) => setProvider((current) => ({ ...current, enabled: event.target.checked }))}
          />
          <span>启用 Hermes provider</span>
        </label>

        <div className="panel-header" style={{ marginTop: 10 }}>
          <h3>Hermes 模型列表</h3>
          <p>模型会按 `provider/model-id` 格式编译进 `config.yaml`。</p>
        </div>

        <div className="model-toolbar">
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
    </section>
  );
}

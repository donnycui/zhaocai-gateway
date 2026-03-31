import { useEffect, useMemo, useState } from "react";

import { api, type GatewayAlias, type GatewayAliasTarget, type GatewayModel } from "../lib/api";

type EditableTarget = {
  local_id: string;
  model_id: string;
  priority: string;
  enabled: boolean;
  fallback_on_timeout: boolean;
  fallback_on_5xx: boolean;
  fallback_on_429: boolean;
  cooldown_seconds: string;
};

function toEditableTarget(target?: GatewayAliasTarget): EditableTarget {
  return {
    local_id: `${target?.id ?? "new"}-${crypto.randomUUID()}`,
    model_id: target?.model_id?.toString() ?? "",
    priority: target?.priority?.toString() ?? "",
    enabled: target?.enabled ?? true,
    fallback_on_timeout: target?.fallback_on_timeout ?? true,
    fallback_on_5xx: target?.fallback_on_5xx ?? true,
    fallback_on_429: target?.fallback_on_429 ?? true,
    cooldown_seconds: target?.cooldown_seconds?.toString() ?? "120",
  };
}

export default function GatewayAliasesPage() {
  const [aliases, setAliases] = useState<GatewayAlias[]>([]);
  const [models, setModels] = useState<GatewayModel[]>([]);
  const [selectedAliasId, setSelectedAliasId] = useState<number | null>(null);
  const [targets, setTargets] = useState<EditableTarget[]>([]);
  const [message, setMessage] = useState("");
  const [aliasForm, setAliasForm] = useState({
    alias_key: "",
    display_name: "",
    alias_type: "tier",
    visibility: "project",
    notes: "",
  });

  const selectedAlias = useMemo(
    () => aliases.find((alias) => alias.id === selectedAliasId) ?? null,
    [aliases, selectedAliasId],
  );

  const modelOptions = useMemo(
    () =>
      models
        .filter((model) => model.enabled)
        .map((model) => ({
          id: model.id,
          account_id: model.account_id,
          label: `${model.account_name ?? `账号 #${model.account_id}`} / ${model.display_name} / ${model.upstream_model}`,
        })),
    [models],
  );

  async function loadAll() {
    const [nextAliases, nextModels] = await Promise.all([
      api.getGatewayAliases(),
      api.getGatewayModels(),
    ]);
    setAliases(nextAliases);
    setModels(nextModels);
    if (selectedAliasId == null && nextAliases.length > 0) {
      setSelectedAliasId(nextAliases[0].id);
    } else if (selectedAliasId != null && !nextAliases.some((alias) => alias.id === selectedAliasId)) {
      setSelectedAliasId(nextAliases[0]?.id ?? null);
    }
  }

  useEffect(() => {
    void loadAll();
  }, []);

  useEffect(() => {
    async function loadTargets() {
      if (selectedAliasId == null) {
        setTargets([]);
        return;
      }
      const nextTargets = await api.getGatewayAliasTargets(selectedAliasId);
      setTargets(nextTargets.length > 0 ? nextTargets.map((target) => toEditableTarget(target)) : [toEditableTarget()]);
    }
    void loadTargets();
  }, [selectedAliasId]);

  async function handleCreateAlias(event: React.FormEvent) {
    event.preventDefault();
    setMessage("");
    const alias = await api.createGatewayAlias(aliasForm);
    setAliasForm({
      alias_key: "",
      display_name: "",
      alias_type: "tier",
      visibility: "project",
      notes: "",
    });
    await loadAll();
    setSelectedAliasId(alias.id);
    setMessage("Gateway 别名已创建。");
  }

  async function handleToggleAliasEnabled() {
    if (!selectedAlias) return;
    await api.updateGatewayAlias(selectedAlias.id, {
      display_name: selectedAlias.display_name,
      enabled: !selectedAlias.enabled,
      visibility: selectedAlias.visibility,
      notes: selectedAlias.notes,
    });
    await loadAll();
    setMessage(selectedAlias.enabled ? "Gateway 别名已停用。" : "Gateway 别名已启用。");
  }

  function updateTarget(localId: string, patch: Partial<EditableTarget>) {
    setTargets((current) =>
      current.map((target) => (target.local_id === localId ? { ...target, ...patch } : target)),
    );
  }

  function addTargetRow() {
    setTargets((current) => [...current, toEditableTarget()]);
  }

  function removeTargetRow(localId: string) {
    setTargets((current) => current.filter((target) => target.local_id !== localId));
  }

  async function handleSaveTargets() {
    if (!selectedAlias) return;
    const payload = targets
      .filter((target) => target.model_id && target.priority)
      .map((target) => {
        const selectedModel = modelOptions.find((item) => item.id === Number(target.model_id));
        if (!selectedModel) {
          throw new Error("存在未匹配的 Gateway 模型，请先重新选择 target。");
        }
        return {
          account_id: selectedModel.account_id,
          model_id: selectedModel.id,
          priority: Number(target.priority),
          enabled: target.enabled,
          fallback_on_timeout: target.fallback_on_timeout,
          fallback_on_5xx: target.fallback_on_5xx,
          fallback_on_429: target.fallback_on_429,
          cooldown_seconds: Number(target.cooldown_seconds || "120"),
        };
      });

    const saved = await api.replaceGatewayAliasTargets(selectedAlias.id, payload);
    setTargets(saved.length > 0 ? saved.map((target) => toEditableTarget(target)) : [toEditableTarget()]);
    setMessage("Gateway alias targets 已保存。");
    await loadAll();
  }

  return (
    <div className="panel placeholder-panel">
      <div className="panel-header" style={{ marginBottom: 0 }}>
        <h3>Gateway Aliases</h3>
        <p>这里维护对外稳定别名，以及别名下面的真实 target 顺序。项目以后应该优先绑定 alias，而不是直接绑真实模型名。</p>
      </div>

      <form className="form-panel" onSubmit={handleCreateAlias}>
        <div className="editor-grid">
          <label>
            <span>Alias Key</span>
            <input value={aliasForm.alias_key} onChange={(event) => setAliasForm((current) => ({ ...current, alias_key: event.target.value }))} placeholder="signal/deep" />
          </label>
          <label>
            <span>显示名称</span>
            <input value={aliasForm.display_name} onChange={(event) => setAliasForm((current) => ({ ...current, display_name: event.target.value }))} placeholder="Signal Deep" />
          </label>
          <label>
            <span>Alias 类型</span>
            <select value={aliasForm.alias_type} onChange={(event) => setAliasForm((current) => ({ ...current, alias_type: event.target.value }))}>
              <option value="tier">tier</option>
              <option value="capability">capability</option>
              <option value="model-family">model-family</option>
            </select>
          </label>
          <label>
            <span>可见性</span>
            <select value={aliasForm.visibility} onChange={(event) => setAliasForm((current) => ({ ...current, visibility: event.target.value }))}>
              <option value="project">project</option>
              <option value="internal">internal</option>
            </select>
          </label>
        </div>
        <label>
          <span>备注</span>
          <textarea value={aliasForm.notes} onChange={(event) => setAliasForm((current) => ({ ...current, notes: event.target.value }))} />
        </label>
        <div className="topbar-actions">
          <button type="submit">新增 Alias</button>
        </div>
      </form>

      {aliases.length === 0 ? (
        <div className="empty-state">还没有任何 Gateway alias。</div>
      ) : (
        <div className="page two-column">
          <div className="panel">
            <div className="panel-header" style={{ marginBottom: 0 }}>
              <h3>Alias 列表</h3>
              <p>选择一个 alias 后，在右侧配置它的真实 target 顺序。</p>
            </div>
            <div className="device-list">
              {aliases.map((alias) => (
                <div
                  key={alias.id}
                  className={`device-card static-card ${alias.id === selectedAliasId ? "selected" : ""}`}
                >
                  <button
                    type="button"
                    className="device-card-button"
                    onClick={() => {
                      setSelectedAliasId(alias.id);
                      setMessage("");
                    }}
                  >
                    <strong>{alias.display_name}</strong>
                    <span>{alias.alias_key}</span>
                    <span>{alias.enabled ? "启用中" : "已停用"}</span>
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header" style={{ marginBottom: 0 }}>
              <h3>{selectedAlias ? `${selectedAlias.display_name} Targets` : "Alias Targets"}</h3>
              <p>{selectedAlias ? `当前 alias key：${selectedAlias.alias_key}` : "请先选择一个 alias。"}</p>
            </div>
            {selectedAlias ? (
              <>
                <div className="topbar-actions">
                  <button type="button" className="secondary-button" onClick={() => void handleToggleAliasEnabled()}>
                    {selectedAlias.enabled ? "停用 Alias" : "启用 Alias"}
                  </button>
                </div>
                {targets.length === 0 ? <div className="empty-state">当前没有 target。</div> : null}
                <div className="model-card-list">
                  {targets.map((target) => (
                    <div key={target.local_id} className="model-editor-card">
                      <div className="model-card-header">
                        <span className="model-badge">Target</span>
                        <button type="button" className="secondary-button" onClick={() => removeTargetRow(target.local_id)}>
                          删除
                        </button>
                      </div>
                      <div className="editor-grid">
                        <label>
                          <span>真实模型</span>
                          <select value={target.model_id} onChange={(event) => updateTarget(target.local_id, { model_id: event.target.value })}>
                            <option value="">请选择已同步模型</option>
                            {modelOptions.map((option) => (
                              <option key={option.id} value={option.id}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          <span>优先级</span>
                          <input value={target.priority} onChange={(event) => updateTarget(target.local_id, { priority: event.target.value })} placeholder="10" />
                        </label>
                      </div>
                      <div className="inline-actions">
                        <label className="checkbox-row">
                          <input type="checkbox" checked={target.enabled} onChange={(event) => updateTarget(target.local_id, { enabled: event.target.checked })} />
                          启用 target
                        </label>
                        <label className="checkbox-row">
                          <input type="checkbox" checked={target.fallback_on_timeout} onChange={(event) => updateTarget(target.local_id, { fallback_on_timeout: event.target.checked })} />
                          timeout 切换
                        </label>
                        <label className="checkbox-row">
                          <input type="checkbox" checked={target.fallback_on_5xx} onChange={(event) => updateTarget(target.local_id, { fallback_on_5xx: event.target.checked })} />
                          5xx 切换
                        </label>
                        <label className="checkbox-row">
                          <input type="checkbox" checked={target.fallback_on_429} onChange={(event) => updateTarget(target.local_id, { fallback_on_429: event.target.checked })} />
                          429 切换
                        </label>
                      </div>
                      <label>
                        <span>冷却秒数</span>
                        <input value={target.cooldown_seconds} onChange={(event) => updateTarget(target.local_id, { cooldown_seconds: event.target.value })} />
                      </label>
                    </div>
                  ))}
                </div>
                <div className="topbar-actions">
                  <button type="button" className="secondary-button" onClick={addTargetRow}>
                    新增 Target
                  </button>
                  <button type="button" onClick={() => void handleSaveTargets()}>
                    保存 Targets
                  </button>
                </div>
              </>
            ) : (
              <div className="empty-state">请先选择一个 alias。</div>
            )}
          </div>
        </div>
      )}

      {message ? <p className="inline-message">{message}</p> : null}
    </div>
  );
}

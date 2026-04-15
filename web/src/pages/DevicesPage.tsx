import { useEffect, useMemo, useState } from "react";

import { api, type ConfigPreview, type Device, type Model } from "../lib/api";

interface DevicesPageProps {
  devices: Device[];
  models: Model[];
  onRefresh: () => Promise<void>;
}

export default function DevicesPage({
  devices,
  models,
  onRefresh,
}: DevicesPageProps) {
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(
    devices[0]?.id ?? null,
  );
  const [preview, setPreview] = useState<ConfigPreview | null>(null);
  const selectedDevice = useMemo(
    () => devices.find((device) => device.id === selectedDeviceId) ?? null,
    [devices, selectedDeviceId],
  );
  const [draftModelIds, setDraftModelIds] = useState<number[]>(selectedDevice?.model_ids ?? []);
  const [modelAssignmentDirty, setModelAssignmentDirty] = useState(false);
  const [modelAssignmentMessage, setModelAssignmentMessage] = useState("");
  const [savingModelAssignments, setSavingModelAssignments] = useState(false);
  const selectedModelIds = new Set(draftModelIds);
  const [preserveProvidersText, setPreserveProvidersText] = useState("");
  const [preserveModelsText, setPreserveModelsText] = useState("");
  const [preserveMessage, setPreserveMessage] = useState("");
  const [expandedProviders, setExpandedProviders] = useState<Record<string, boolean>>({});
  const [draggingModelId, setDraggingModelId] = useState<number | null>(null);
  const [dragOverModelId, setDragOverModelId] = useState<number | null>(null);
  const providerGroups = useMemo(() => {
    const groups = new Map<string, Model[]>();
    models.forEach((model) => {
      const providerName = model.provider_name ?? `供应商 #${model.provider_id}`;
      const current = groups.get(providerName) ?? [];
      current.push(model);
      groups.set(providerName, current);
    });
    return Array.from(groups.entries());
  }, [models]);

  const modelById = useMemo(() => {
    const next = new Map<number, Model>();
    models.forEach((model) => next.set(model.id, model));
    return next;
  }, [models]);

  const orderedSelectedModels = useMemo(
    () => draftModelIds.map((modelId) => modelById.get(modelId)).filter((model): model is Model => Boolean(model)),
    [draftModelIds, modelById],
  );

  function toggleModel(modelId: number) {
    if (!selectedDevice) return;
    setDraftModelIds((current) => {
      if (current.includes(modelId)) {
        return current.filter((id) => id !== modelId);
      }
      return [...current, modelId];
    });
    setModelAssignmentDirty(true);
    setModelAssignmentMessage("");
  }

  function moveModel(modelId: number, direction: -1 | 1) {
    setDraftModelIds((current) => {
      const index = current.indexOf(modelId);
      if (index < 0) return current;
      const nextIndex = index + direction;
      if (nextIndex < 0 || nextIndex >= current.length) {
        return current;
      }
      const next = [...current];
      const [model] = next.splice(index, 1);
      next.splice(nextIndex, 0, model);
      return next;
    });
    setModelAssignmentDirty(true);
    setModelAssignmentMessage("");
  }

  function reorderModel(draggedModelId: number, targetModelId: number) {
    setDraftModelIds((current) => {
      const fromIndex = current.indexOf(draggedModelId);
      const toIndex = current.indexOf(targetModelId);
      if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex) {
        return current;
      }
      const next = [...current];
      const [dragged] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, dragged);
      return next;
    });
    setModelAssignmentDirty(true);
    setModelAssignmentMessage("");
  }

  function handleDragStart(modelId: number) {
    setDraggingModelId(modelId);
    setDragOverModelId(null);
  }

  function handleDragEnd() {
    setDraggingModelId(null);
    setDragOverModelId(null);
  }

  function handleDropOnModel(targetModelId: number) {
    if (draggingModelId == null) {
      return;
    }
    reorderModel(draggingModelId, targetModelId);
    handleDragEnd();
  }

  async function loadPreview() {
    if (!selectedDevice) return;
    const nextPreview = await api.getConfigPreview(selectedDevice.id);
    setPreview(nextPreview);
  }

  function syncPreserveInputs(device: Device | null) {
    setPreserveProvidersText((device?.preserve_providers ?? []).join("\n"));
    setPreserveModelsText((device?.preserve_models ?? []).join("\n"));
    setPreserveMessage("");
  }

  useEffect(() => {
    syncPreserveInputs(selectedDevice);
  }, [selectedDevice]);

  useEffect(() => {
    setDraftModelIds(selectedDevice?.model_ids ?? []);
    setModelAssignmentDirty(false);
    setModelAssignmentMessage("");
  }, [selectedDevice]);

  function toggleProviderGroup(providerName: string) {
    setExpandedProviders((current) => ({
      ...current,
      [providerName]: !current[providerName],
    }));
  }

  async function handleDeleteDevice(deviceId: number) {
    const confirmed = window.confirm("确认删除这台设备吗？");
    if (!confirmed) return;
    await api.deleteDevice(deviceId);
    if (selectedDeviceId === deviceId) {
      setSelectedDeviceId(null);
      setPreview(null);
      syncPreserveInputs(null);
    }
    await onRefresh();
  }

  async function handleSavePreserveConfig() {
    if (!selectedDevice) return;
    const preserve_providers = preserveProvidersText
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean);
    const preserve_models = preserveModelsText
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean);
    await api.updateDevicePreserveConfig(selectedDevice.id, preserve_providers, preserve_models);
    setPreserveMessage("保留配置已保存，下次 agent 同步时会写入节点上的 zhaocai-preserve.json。");
    await onRefresh();
  }

  async function handleSaveModelAssignments() {
    if (!selectedDevice) return;
    setSavingModelAssignments(true);
    try {
      await api.assignDeviceModels(selectedDevice.id, draftModelIds);
      setModelAssignmentDirty(false);
      setModelAssignmentMessage("模型分配已保存。");
      await onRefresh();
    } finally {
      setSavingModelAssignments(false);
    }
  }

  function handleResetModelAssignments() {
    setDraftModelIds(selectedDevice?.model_ids ?? []);
    setModelAssignmentDirty(false);
    setModelAssignmentMessage("");
  }

  return (
    <section className="page two-column">
      <div className="panel">
        <div className="panel-header">
          <h3>设备列表</h3>
          <p>选择设备后，直接勾选它可以使用的模型。</p>
        </div>
        <div className="device-list">
          {devices.length === 0 ? (
            <div className="empty-state">当前还没有可管理的设备。</div>
          ) : (
            devices.map((device) => (
              <div
                key={device.id}
                className={`device-card static-card ${device.id === selectedDeviceId ? "selected" : ""}`}
              >
                <button
                  type="button"
                  className="device-card-button"
                  onClick={() => {
                    setSelectedDeviceId(device.id);
                    setPreview(null);
                    syncPreserveInputs(device);
                  }}
                >
                  <strong>{device.name}</strong>
                  <span>{device.device_type}</span>
                  <span>配置版本 {device.current_config_version}</span>
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => void handleDeleteDevice(device.id)}
                >
                  删除
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="stack">
        <div className="panel">
          <div className="panel-header">
            <h3>设备模型分配</h3>
            <p>{selectedDevice ? `正在编辑：${selectedDevice.name}` : "请先选择一台设备。"}</p>
          </div>
          <div className="topbar-actions" style={{ marginBottom: 12 }}>
            <button
              type="button"
              className="secondary-button"
              disabled={!selectedDevice || !modelAssignmentDirty}
              onClick={handleResetModelAssignments}
            >
              恢复当前值
            </button>
            <button
              type="button"
              disabled={!selectedDevice || !modelAssignmentDirty || savingModelAssignments}
              onClick={() => void handleSaveModelAssignments()}
            >
              {savingModelAssignments ? "保存中" : "保存模型分配"}
            </button>
          </div>
          {modelAssignmentMessage ? <p className="inline-message">{modelAssignmentMessage}</p> : null}
          <div className="selected-model-order">
            <div className="panel-header" style={{ marginBottom: 0 }}>
              <h3>已选模型顺序</h3>
              <p>第 0 个模型会写入 `primary`，后面的模型依次写入 `fallbacks`。</p>
            </div>
            {orderedSelectedModels.length === 0 ? (
              <div className="empty-state">当前还没有选中任何模型。</div>
            ) : (
              <div className="selected-model-order-list">
                {orderedSelectedModels.map((model, index) => (
                  <div
                    key={model.id}
                    className={`selected-model-order-row ${draggingModelId === model.id ? "is-dragging" : ""} ${dragOverModelId === model.id ? "is-drag-over" : ""}`}
                    draggable
                    onDragStart={() => handleDragStart(model.id)}
                    onDragEnd={handleDragEnd}
                    onDragOver={(event) => {
                      event.preventDefault();
                      if (draggingModelId != null && draggingModelId !== model.id) {
                        setDragOverModelId(model.id);
                      }
                    }}
                    onDragLeave={() => {
                      if (dragOverModelId === model.id) {
                        setDragOverModelId(null);
                      }
                    }}
                    onDrop={(event) => {
                      event.preventDefault();
                      handleDropOnModel(model.id);
                    }}
                  >
                    <div className="selected-model-order-main">
                      <strong>{index}. {model.display_name}</strong>
                      <span>{model.provider_name ?? `供应商 #${model.provider_id}`} / {model.upstream_model}</span>
                    </div>
                    <div className="topbar-actions">
                      <button
                        type="button"
                        className="secondary-button"
                        disabled={index === 0}
                        onClick={() => moveModel(model.id, -1)}
                      >
                        上移
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        disabled={index === orderedSelectedModels.length - 1}
                        onClick={() => moveModel(model.id, 1)}
                      >
                        下移
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="checkbox-grid">
            {providerGroups.map(([providerName, providerModels]) => {
              const expanded = expandedProviders[providerName] ?? false;
              return (
                <div key={providerName} className="provider-group">
                  <button
                    type="button"
                    className="provider-group-toggle"
                    onClick={() => toggleProviderGroup(providerName)}
                  >
                    <strong>{providerName}</strong>
                    <span>{expanded ? "收起" : "展开"} · {providerModels.length} 个模型</span>
                  </button>
                  {expanded ? (
                    <div className="checkbox-grid nested-grid">
                      {providerModels.map((model) => (
                        <label key={model.id} className="checkbox-card">
                          <input
                            type="checkbox"
                            checked={selectedModelIds.has(model.id)}
                            disabled={!selectedDevice}
                            onChange={() => toggleModel(model.id)}
                          />
                          <div>
                            <strong>{model.display_name}</strong>
                            <span>{model.upstream_model}</span>
                          </div>
                        </label>
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })}
            {models.length === 0 ? (
              <div className="empty-state">当前没有可分配的模型。</div>
            ) : null}
          </div>
        </div>

        <div className="panel form-panel">
          <div className="panel-header">
            <h3>本地保留配置</h3>
            <p>这里管理设备级的保留列表。保存后，agent 会把这些值写入节点上的 `~/.openclaw/zhaocai-preserve.json`。</p>
          </div>
          <label>
            <span>Preserve Providers（每行一个 provider 名称）</span>
            <textarea
              value={preserveProvidersText}
              disabled={!selectedDevice}
              onChange={(event) => setPreserveProvidersText(event.target.value)}
              placeholder={"zhipu\ncustom-local"}
            />
          </label>
          <label>
            <span>Preserve Models（每行一个 provider/model）</span>
            <textarea
              value={preserveModelsText}
              disabled={!selectedDevice}
              onChange={(event) => setPreserveModelsText(event.target.value)}
              placeholder={"zhipu/glm-4-plus\ncustom-local/dev-model"}
            />
          </label>
          <div className="topbar-actions">
            <button
              type="button"
              className="secondary-button"
              disabled={!selectedDevice}
              onClick={() => syncPreserveInputs(selectedDevice)}
            >
              读取当前值
            </button>
            <button type="button" disabled={!selectedDevice} onClick={() => void handleSavePreserveConfig()}>
              保存保留配置
            </button>
          </div>
          {preserveMessage ? <p className="inline-message">{preserveMessage}</p> : null}
        </div>

        <div className="panel">
          <div className="page-header">
            <div>
              <h3>配置预览</h3>
              <p>在 agent 同步前，先查看这台设备将收到的完整配置。</p>
            </div>
            <button className="secondary-button" onClick={() => void loadPreview()} disabled={!selectedDevice}>
              加载预览
            </button>
          </div>
          <pre className="code-block">
            {preview ? JSON.stringify(preview, null, 2) : "尚未加载配置预览。"}
          </pre>
        </div>
      </div>
    </section>
  );
}

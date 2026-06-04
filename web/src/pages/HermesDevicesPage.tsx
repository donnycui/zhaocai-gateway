import { useEffect, useMemo, useState } from "react";

import { api, type ConfigPreview, type HermesDevice, type HermesModel } from "../lib/api";

interface HermesDevicesPageProps {
  devices: HermesDevice[];
  models: HermesModel[];
  onRefresh: () => Promise<void>;
}

interface HermesPreviewPayload extends ConfigPreview {
  config_yaml?: string;
  plugin_files?: Record<string, string>;
}

export default function HermesDevicesPage({ devices, models, onRefresh }: HermesDevicesPageProps) {
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(devices[0]?.id ?? null);
  const [preview, setPreview] = useState<HermesPreviewPayload | null>(null);
  const selectedDevice = useMemo(
    () => devices.find((device) => device.id === selectedDeviceId) ?? null,
    [devices, selectedDeviceId],
  );
  const [draftModelIds, setDraftModelIds] = useState<number[]>(selectedDevice?.model_ids ?? []);
  const [modelAssignmentDirty, setModelAssignmentDirty] = useState(false);
  const [modelAssignmentMessage, setModelAssignmentMessage] = useState("");
  const [savingModelAssignments, setSavingModelAssignments] = useState(false);
  const [draggingModelId, setDraggingModelId] = useState<number | null>(null);
  const [dragOverModelId, setDragOverModelId] = useState<number | null>(null);

  const providerGroups = useMemo(() => {
    const groups = new Map<string, HermesModel[]>();
    models.forEach((model) => {
      const providerName = model.provider_name ?? `供应商 #${model.provider_id}`;
      const current = groups.get(providerName) ?? [];
      current.push(model);
      groups.set(providerName, current);
    });
    return Array.from(groups.entries());
  }, [models]);

  const modelById = useMemo(() => {
    const next = new Map<number, HermesModel>();
    models.forEach((model) => next.set(model.id, model));
    return next;
  }, [models]);

  const orderedSelectedModels = useMemo(
    () => draftModelIds.map((modelId) => modelById.get(modelId)).filter((model): model is HermesModel => Boolean(model)),
    [draftModelIds, modelById],
  );

  useEffect(() => {
    setDraftModelIds(selectedDevice?.model_ids ?? []);
    setModelAssignmentDirty(false);
    setModelAssignmentMessage("");
  }, [selectedDevice]);

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
      const nextIndex = index + direction;
      if (index < 0 || nextIndex < 0 || nextIndex >= current.length) return current;
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
      if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex) return current;
      const next = [...current];
      const [dragged] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, dragged);
      return next;
    });
    setModelAssignmentDirty(true);
    setModelAssignmentMessage("");
  }

  async function handleDeleteDevice(deviceId: number) {
    const confirmed = window.confirm("确认删除这台 Hermes 设备吗？");
    if (!confirmed) return;
    await api.deleteHermesDevice(deviceId);
    if (selectedDeviceId === deviceId) {
      setSelectedDeviceId(null);
      setPreview(null);
    }
    await onRefresh();
  }

  async function handleSaveModelAssignments() {
    if (!selectedDevice) return;
    setSavingModelAssignments(true);
    try {
      await api.assignHermesDeviceModels(selectedDevice.id, draftModelIds);
      setModelAssignmentDirty(false);
      setModelAssignmentMessage("Hermes 模型分配已保存。");
      await onRefresh();
    } finally {
      setSavingModelAssignments(false);
    }
  }

  async function loadPreview() {
    if (!selectedDevice) return;
    const nextPreview = (await api.getHermesConfigPreview(selectedDevice.id)) as HermesPreviewPayload;
    setPreview(nextPreview);
  }

  return (
    <section className="page two-column">
      <div className="panel">
        <div className="panel-header">
          <h3>Hermes 设备列表</h3>
          <p>选择设备后，直接勾选它可以使用的 Hermes 模型。</p>
        </div>
        <div className="device-list">
          {devices.length === 0 ? (
            <div className="empty-state">当前还没有可管理的 Hermes 设备。</div>
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
                  }}
                >
                  <strong>{device.name}</strong>
                  <span>{device.device_type}</span>
                  <span>配置版本 {device.current_config_version}</span>
                </button>
                <button type="button" className="secondary-button" onClick={() => void handleDeleteDevice(device.id)}>
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
            <h3>Hermes 模型分配</h3>
            <p>{selectedDevice ? `正在编辑：${selectedDevice.name}` : "请先选择一台 Hermes 设备。"}</p>
          </div>
          <div className="topbar-actions" style={{ marginBottom: 12 }}>
            <button
              type="button"
              className="secondary-button"
              disabled={!selectedDevice || !modelAssignmentDirty}
              onClick={() => {
                setDraftModelIds(selectedDevice?.model_ids ?? []);
                setModelAssignmentDirty(false);
                setModelAssignmentMessage("");
              }}
            >
              恢复当前值
            </button>
            <button
              type="button"
              disabled={!selectedDevice || !modelAssignmentDirty || savingModelAssignments}
              onClick={() => void handleSaveModelAssignments()}
            >
              {savingModelAssignments ? "保存中" : "保存 Hermes 模型分配"}
            </button>
          </div>
          {modelAssignmentMessage ? <p className="inline-message">{modelAssignmentMessage}</p> : null}

          <div className="selected-model-order">
            <div className="panel-header" style={{ marginBottom: 0 }}>
              <h3>已选模型顺序</h3>
              <p>第一个模型会编译成 `model.default`，其余模型依次写入 `fallbacks`。</p>
            </div>
            {orderedSelectedModels.length === 0 ? (
              <div className="empty-state">当前还没有选中任何 Hermes 模型。</div>
            ) : (
              <div className="selected-model-order-list">
                {orderedSelectedModels.map((model, index) => (
                  <div
                    key={model.id}
                    className={`selected-model-order-row ${draggingModelId === model.id ? "is-dragging" : ""} ${dragOverModelId === model.id ? "is-drag-over" : ""}`}
                    draggable
                    onDragStart={() => setDraggingModelId(model.id)}
                    onDragEnd={() => {
                      setDraggingModelId(null);
                      setDragOverModelId(null);
                    }}
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
                      if (draggingModelId != null) {
                        reorderModel(draggingModelId, model.id);
                      }
                      setDraggingModelId(null);
                      setDragOverModelId(null);
                    }}
                  >
                    <div className="selected-model-order-main">
                      <strong>{index}. {model.display_name}</strong>
                      <span>{model.provider_name ?? `供应商 #${model.provider_id}`} / {model.upstream_model}</span>
                    </div>
                    <div className="topbar-actions">
                      <button type="button" className="secondary-button" disabled={index === 0} onClick={() => moveModel(model.id, -1)}>
                        上移
                      </button>
                      <button type="button" className="secondary-button" disabled={index === orderedSelectedModels.length - 1} onClick={() => moveModel(model.id, 1)}>
                        下移
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="checkbox-grid">
            {providerGroups.map(([providerName, providerModels]) => (
              <div key={providerName} className="provider-group">
                <div className="panel-header" style={{ marginBottom: 10 }}>
                  <h3>{providerName}</h3>
                  <p>{providerModels.length} 个 Hermes 模型</p>
                </div>
                <div className="checkbox-grid">
                  {providerModels.map((model) => (
                    <label key={model.id} className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={draftModelIds.includes(model.id)}
                        onChange={() => toggleModel(model.id)}
                      />
                      <span>{model.display_name} ({model.upstream_model})</span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3>Hermes 配置预览</h3>
            <p>查看将下发到节点的 `config.yaml` 与 provider 插件文件。</p>
          </div>
          <div className="topbar-actions" style={{ marginBottom: 12 }}>
            <button type="button" disabled={!selectedDevice} onClick={() => void loadPreview()}>
              生成预览
            </button>
          </div>
          {!preview ? (
            <div className="empty-state">选择设备后点击“生成预览”。</div>
          ) : (
            <div className="stack">
              <pre className="code-block">{preview.config_yaml ?? ""}</pre>
              {Object.entries(preview.plugin_files ?? {}).map(([providerName, source]) => (
                <div key={providerName} className="panel" style={{ padding: 16 }}>
                  <div className="panel-header">
                    <h3>{providerName} 插件</h3>
                    <p>{`~/.hermes/plugins/model-providers/${providerName}/__init__.py`}</p>
                  </div>
                  <pre className="code-block">{source}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

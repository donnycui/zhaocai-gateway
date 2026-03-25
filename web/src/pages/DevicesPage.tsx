import { useMemo, useState } from "react";

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
  const selectedModelIds = new Set(selectedDevice?.model_ids ?? []);

  async function toggleModel(modelId: number) {
    if (!selectedDevice) return;
    if (selectedModelIds.has(modelId)) {
      selectedModelIds.delete(modelId);
    } else {
      selectedModelIds.add(modelId);
    }
    await api.assignDeviceModels(selectedDevice.id, Array.from(selectedModelIds));
    await onRefresh();
  }

  async function loadPreview() {
    if (!selectedDevice) return;
    const nextPreview = await api.getConfigPreview(selectedDevice.id);
    setPreview(nextPreview);
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
              <button
                key={device.id}
                className={`device-card ${device.id === selectedDeviceId ? "selected" : ""}`}
                onClick={() => {
                  setSelectedDeviceId(device.id);
                  setPreview(null);
                }}
              >
                <strong>{device.name}</strong>
                <span>{device.device_type}</span>
                <span>配置版本 {device.current_config_version}</span>
              </button>
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
          <div className="checkbox-grid">
            {models.map((model) => (
              <label key={model.id} className="checkbox-card">
                <input
                  type="checkbox"
                  checked={selectedModelIds.has(model.id)}
                  disabled={!selectedDevice}
                  onChange={() => void toggleModel(model.id)}
                />
                <div>
                  <strong>{model.display_name}</strong>
                  <span>{model.upstream_model}</span>
                </div>
              </label>
            ))}
            {models.length === 0 ? (
              <div className="empty-state">当前没有可分配的模型。</div>
            ) : null}
          </div>
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

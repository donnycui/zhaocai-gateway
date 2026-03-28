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
  const [expandedProviders, setExpandedProviders] = useState<Record<string, boolean>>({});
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
    }
    await onRefresh();
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
                            onChange={() => void toggleModel(model.id)}
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

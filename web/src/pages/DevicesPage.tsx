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
          <h3>Devices</h3>
          <p>Pick a device, then choose which models it should receive.</p>
        </div>
        <div className="device-list">
          {devices.length === 0 ? (
            <div className="empty-state">No devices available yet.</div>
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
                <span>Version {device.current_config_version}</span>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="stack">
        <div className="panel">
          <div className="panel-header">
            <h3>Assigned Models</h3>
            <p>{selectedDevice ? `Editing ${selectedDevice.name}` : "Select a device first."}</p>
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
              <div className="empty-state">No models available for assignment.</div>
            ) : null}
          </div>
        </div>

        <div className="panel">
          <div className="page-header">
            <div>
              <h3>Config Preview</h3>
              <p>Inspect the exact device payload before agent sync.</p>
            </div>
            <button className="secondary-button" onClick={() => void loadPreview()} disabled={!selectedDevice}>
              Load Preview
            </button>
          </div>
          <pre className="code-block">
            {preview ? JSON.stringify(preview, null, 2) : "No preview loaded yet."}
          </pre>
        </div>
      </div>
    </section>
  );
}

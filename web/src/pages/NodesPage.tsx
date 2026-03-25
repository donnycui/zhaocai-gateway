import { useMemo, useState } from "react";

import { api, type Device } from "../lib/api";

interface NodesPageProps {
  devices: Device[];
  onRefresh: () => Promise<void>;
}

export default function NodesPage({ devices, onRefresh }: NodesPageProps) {
  const [form, setForm] = useState({
    name: "",
    device_type: "vps",
    hostname: "",
    platform: "",
  });
  const [pairingInfo, setPairingInfo] = useState<{
    deviceName: string;
    pairingToken: string;
    expiresAt: string;
  } | null>(null);
  const latestDevice = useMemo(() => devices[devices.length - 1] ?? null, [devices]);

  async function handleCreateDevice(event: React.FormEvent) {
    event.preventDefault();
    await api.createDevice(form);
    setForm({
      name: "",
      device_type: "vps",
      hostname: "",
      platform: "",
    });
    await onRefresh();
  }

  async function handleIssueToken(device: Device) {
    const token = await api.issuePairingToken(device.id);
    setPairingInfo({
      deviceName: device.name,
      pairingToken: token.pairing_token,
      expiresAt: token.expires_at,
    });
  }

  const installCommand = pairingInfo
    ? `zhaocai-agent register --server https://raspberrypi.tailnet.ts.net --token ${pairingInfo.pairingToken}`
    : "Issue a pairing token to generate the install command.";

  return (
    <section className="page two-column">
      <form className="panel form-panel" onSubmit={handleCreateDevice}>
        <div className="panel-header">
          <h3>Create Node</h3>
          <p>Register a managed machine before pairing the local agent.</p>
        </div>
        <label>
          <span>Name</span>
          <input
            value={form.name}
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
          />
        </label>
        <label>
          <span>Device Type</span>
          <input
            value={form.device_type}
            onChange={(event) =>
              setForm((current) => ({ ...current, device_type: event.target.value }))
            }
          />
        </label>
        <label>
          <span>Hostname</span>
          <input
            value={form.hostname}
            onChange={(event) =>
              setForm((current) => ({ ...current, hostname: event.target.value }))
            }
          />
        </label>
        <label>
          <span>Platform</span>
          <input
            value={form.platform}
            onChange={(event) =>
              setForm((current) => ({ ...current, platform: event.target.value }))
            }
          />
        </label>
        <button type="submit">Create Node</button>
      </form>

      <div className="stack">
        <div className="panel">
          <div className="panel-header">
            <h3>Pairing Tokens</h3>
            <p>Issue a one-time token and run the generated command on the target machine.</p>
          </div>
          <div className="device-list">
            {devices.length === 0 ? (
              <div className="empty-state">No nodes created yet.</div>
            ) : (
              devices.map((device) => (
                <div key={device.id} className="device-card static-card">
                  <div>
                    <strong>{device.name}</strong>
                    <span>{device.device_type}</span>
                  </div>
                  <button className="secondary-button" onClick={() => void handleIssueToken(device)}>
                    Issue Token
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3>Install Command</h3>
            <p>{latestDevice ? `Latest node: ${latestDevice.name}` : "Create a node first."}</p>
          </div>
          <pre className="code-block">{installCommand}</pre>
          {pairingInfo ? (
            <p className="inline-message">
              Token for {pairingInfo.deviceName} expires at {pairingInfo.expiresAt}.
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

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
    : "先为设备签发一次性 pairing token，安装命令会自动生成。";

  return (
    <section className="page two-column">
      <form className="panel form-panel" onSubmit={handleCreateDevice}>
        <div className="panel-header">
          <h3>创建节点</h3>
          <p>先在控制面登记设备，再让本地 agent 完成配对。</p>
        </div>
        <label>
          <span>名称</span>
          <input
            value={form.name}
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
          />
        </label>
        <label>
          <span>设备类型</span>
          <input
            value={form.device_type}
            onChange={(event) =>
              setForm((current) => ({ ...current, device_type: event.target.value }))
            }
          />
        </label>
        <label>
          <span>主机名</span>
          <input
            value={form.hostname}
            onChange={(event) =>
              setForm((current) => ({ ...current, hostname: event.target.value }))
            }
          />
        </label>
        <label>
          <span>平台</span>
          <input
            value={form.platform}
            onChange={(event) =>
              setForm((current) => ({ ...current, platform: event.target.value }))
            }
          />
        </label>
        <button type="submit">创建节点</button>
      </form>

      <div className="stack">
        <div className="panel">
          <div className="panel-header">
            <h3>Pairing Token</h3>
            <p>为目标设备签发一次性 token，再去目标机器执行注册命令。</p>
          </div>
          <div className="device-list">
            {devices.length === 0 ? (
              <div className="empty-state">还没有创建任何节点。</div>
            ) : (
              devices.map((device) => (
                <div key={device.id} className="device-card static-card">
                  <div>
                    <strong>{device.name}</strong>
                    <span>{device.device_type}</span>
                  </div>
                  <button className="secondary-button" onClick={() => void handleIssueToken(device)}>
                    签发 Token
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3>安装命令</h3>
            <p>{latestDevice ? `最新节点：${latestDevice.name}` : "请先创建节点。"}</p>
          </div>
          <pre className="code-block">{installCommand}</pre>
          {pairingInfo ? (
            <p className="inline-message">
              {pairingInfo.deviceName} 的 token 过期时间：{pairingInfo.expiresAt}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

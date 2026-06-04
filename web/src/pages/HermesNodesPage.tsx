import { useMemo, useState } from "react";

import { api, type HermesDevice } from "../lib/api";

interface HermesNodesPageProps {
  devices: HermesDevice[];
  onRefresh: () => Promise<void>;
}

export default function HermesNodesPage({ devices, onRefresh }: HermesNodesPageProps) {
  const [form, setForm] = useState({
    name: "",
    device_type: "vps",
    hostname: "",
    platform: "",
  });
  const [editingDeviceId, setEditingDeviceId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [pairingInfo, setPairingInfo] = useState<{
    deviceId: number;
    deviceName: string;
    deviceType: string;
    platform: string;
    pairingToken: string;
    expiresAt: string;
  } | null>(null);
  const latestDevice = useMemo(() => devices[devices.length - 1] ?? null, [devices]);

  async function handleCreateDevice(event: React.FormEvent) {
    event.preventDefault();
    setMessage("");
    if (editingDeviceId == null) {
      await api.createHermesDevice(form);
      setMessage("Hermes 节点已创建。");
    } else {
      await api.updateHermesDevice(editingDeviceId, form);
      setMessage("Hermes 节点已更新。");
      setEditingDeviceId(null);
    }
    setForm({
      name: "",
      device_type: "vps",
      hostname: "",
      platform: "",
    });
    await onRefresh();
  }

  function handleEditDevice(device: HermesDevice) {
    setEditingDeviceId(device.id);
    setForm({
      name: device.name,
      device_type: device.device_type,
      hostname: device.hostname,
      platform: device.platform,
    });
    setMessage("");
  }

  function handleCancelEdit() {
    setEditingDeviceId(null);
    setForm({
      name: "",
      device_type: "vps",
      hostname: "",
      platform: "",
    });
  }

  async function handleDeleteDevice(device: HermesDevice) {
    const confirmed = window.confirm(`确认删除 Hermes 节点 ${device.name} 吗？`);
    if (!confirmed) return;
    await api.deleteHermesDevice(device.id);
    if (editingDeviceId === device.id) {
      handleCancelEdit();
    }
    if (pairingInfo?.deviceId === device.id) {
      setPairingInfo(null);
    }
    setMessage("Hermes 节点已删除。");
    await onRefresh();
  }

  async function handleIssueToken(device: HermesDevice) {
    const token = await api.issueHermesPairingToken(device.id);
    setPairingInfo({
      deviceId: device.id,
      deviceName: device.name,
      deviceType: device.device_type,
      platform: device.platform,
      pairingToken: token.pairing_token,
      expiresAt: token.expires_at,
    });
  }

  const installCommand = useMemo(() => {
    if (!pairingInfo) {
      return "先为 Hermes 设备签发一次性 pairing token，安装命令会自动生成。";
    }

    const server = "https://zhaocai.mintstudio.cn";
    const configPath = "$HOME/.zhaocai-gateway/hermes-agent.json";
    const outputPath = "$HOME/.hermes/config.yaml";
    const registerStep = [
      ".venv/bin/python -m agent.cli register \\",
      "  --target hermes \\",
      `  --server ${server} \\`,
      `  --token ${pairingInfo.pairingToken} \\`,
      `  --config-path "${configPath}" \\`,
      `  --output-path "${outputPath}"`,
    ].join("\n");

    const baseSetup = [
      "[ -d zhaocai-gateway ] || git clone https://github.com/donnycui/zhaocai-gateway.git",
      "cd zhaocai-gateway",
      "python3 -m venv .venv",
      ".venv/bin/pip install -r requirements.txt",
      registerStep,
      `.venv/bin/python -m agent.cli sync-once --target hermes --config-path "${configPath}"`,
    ];

    const platform = pairingInfo.platform.toLowerCase();
    const deviceType = pairingInfo.deviceType.toLowerCase();
    const isLinux =
      platform.includes("linux") ||
      deviceType.includes("vps") ||
      deviceType.includes("linux") ||
      deviceType.includes("raspberry");

    if (isLinux) {
      return [
        "sudo apt update",
        "sudo apt install -y python3-venv",
        ...baseSetup,
        `.venv/bin/python -m agent.cli doctor --target hermes --config-path "${configPath}" --service-manager systemd`,
        ".venv/bin/python -m agent.cli install \\",
        "  --target hermes \\",
        `  --config-path "${configPath}" \\`,
        "  --service-manager systemd \\",
        "  --python-path \"$PWD/.venv/bin/python\" \\",
        "  --working-directory \"$PWD\"",
        "systemctl --user daemon-reload",
        "systemctl --user enable --now zhaocai-hermes-agent.service",
        "systemctl --user status zhaocai-hermes-agent.service",
      ].join("\n");
    }

    return [
      ...baseSetup,
      `.venv/bin/python -m agent.cli doctor --target hermes --config-path "${configPath}"`,
      `.venv/bin/python -m agent.cli install --target hermes --config-path "${configPath}"`,
      "launchctl unload ~/Library/LaunchAgents/com.zhaocai.hermes-agent.plist >/dev/null 2>&1 || true",
      "launchctl load ~/Library/LaunchAgents/com.zhaocai.hermes-agent.plist",
    ].join("\n");
  }, [pairingInfo]);

  return (
    <section className="page two-column">
      <form className="panel form-panel" onSubmit={handleCreateDevice}>
        <div className="panel-header">
          <h3>{editingDeviceId == null ? "创建 Hermes 节点" : "编辑 Hermes 节点"}</h3>
          <p>先在控制面登记 Hermes 设备，再让本地 agent 完成配对。</p>
        </div>
        {message ? <p className="inline-message">{message}</p> : null}
        <label>
          <span>名称</span>
          <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
        </label>
        <label>
          <span>设备类型</span>
          <input value={form.device_type} onChange={(event) => setForm((current) => ({ ...current, device_type: event.target.value }))} />
        </label>
        <label>
          <span>主机名</span>
          <input value={form.hostname} onChange={(event) => setForm((current) => ({ ...current, hostname: event.target.value }))} />
        </label>
        <label>
          <span>平台</span>
          <input value={form.platform} onChange={(event) => setForm((current) => ({ ...current, platform: event.target.value }))} />
        </label>
        <div className="topbar-actions">
          <button type="submit">{editingDeviceId == null ? "创建 Hermes 节点" : "保存修改"}</button>
          {editingDeviceId != null ? (
            <button type="button" className="secondary-button" onClick={handleCancelEdit}>
              取消编辑
            </button>
          ) : null}
        </div>
      </form>

      <div className="stack">
        <div className="panel">
          <div className="panel-header">
            <h3>Hermes Pairing Token</h3>
            <p>为目标设备签发一次性 token，再去目标机器执行 Hermes 注册命令。</p>
          </div>
          <div className="device-list">
            {devices.length === 0 ? (
              <div className="empty-state">还没有创建任何 Hermes 节点。</div>
            ) : (
              devices.map((device) => (
                <div key={device.id} className="device-card static-card">
                  <div>
                    <strong>{device.name}</strong>
                    <span>{device.device_type}</span>
                  </div>
                  <div className="topbar-actions">
                    <button type="button" className="secondary-button" onClick={() => handleEditDevice(device)}>
                      编辑
                    </button>
                    <button type="button" className="secondary-button" onClick={() => void handleDeleteDevice(device)}>
                      删除
                    </button>
                    <button type="button" className="secondary-button" onClick={() => void handleIssueToken(device)}>
                      签发 Token
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3>Hermes 安装命令</h3>
            <p>{latestDevice ? `最新节点：${latestDevice.name}` : "请先创建 Hermes 节点。"}</p>
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

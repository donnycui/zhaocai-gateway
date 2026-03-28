import type { Device, Model, Provider } from "../lib/api";

interface DashboardPageProps {
  providers: Provider[];
  models: Model[];
  devices: Device[];
  onRefresh: () => void;
}

function formatHeartbeat(lastSeenAt: string | null): string {
  if (!lastSeenAt) {
    return "从未";
  }

  const date = new Date(lastSeenAt);
  if (Number.isNaN(date.getTime())) {
    return "未知";
  }

  const formatter = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  const parts = formatter.formatToParts(date);
  const values = Object.fromEntries(
    parts
      .filter((part) => ["month", "day", "hour", "minute"].includes(part.type))
      .map((part) => [part.type, part.value]),
  );

  return `${values.month}-${values.day} ${values.hour}:${values.minute}`;
}

export default function DashboardPage({
  providers,
  models,
  devices,
  onRefresh,
}: DashboardPageProps) {
  const offlineDevices = devices.filter((device) => !device.last_seen_at);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h2>系统总览</h2>
          <p>查看 Provider、模型和设备的当前状态。</p>
        </div>
        <button className="secondary-button" onClick={onRefresh}>
          刷新
        </button>
      </div>

      <div className="stats-grid">
        <article className="stat-card">
          <span className="stat-label">供应商</span>
          <strong>{providers.length}</strong>
        </article>
        <article className="stat-card">
          <span className="stat-label">模型</span>
          <strong>{models.length}</strong>
        </article>
        <article className="stat-card">
          <span className="stat-label">设备</span>
          <strong>{devices.length}</strong>
        </article>
        <article className="stat-card">
          <span className="stat-label">待处理</span>
          <strong>{offlineDevices.length}</strong>
        </article>
      </div>

      <div className="panel">
        <h3>设备状态</h3>
        <table className="table">
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>最近心跳</th>
              <th>配置版本</th>
            </tr>
          </thead>
          <tbody>
            {devices.length === 0 ? (
              <tr>
                <td colSpan={4} className="empty-cell">
                  还没有注册任何设备。
                </td>
              </tr>
            ) : (
              devices.map((device) => (
                <tr key={device.id}>
                  <td>{device.name}</td>
                  <td>{device.device_type}</td>
                  <td>{formatHeartbeat(device.last_seen_at)}</td>
                  <td>{device.current_config_version}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

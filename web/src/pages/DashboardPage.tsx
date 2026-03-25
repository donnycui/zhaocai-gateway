import type { Device, Model, Provider } from "../lib/api";

interface DashboardPageProps {
  providers: Provider[];
  models: Model[];
  devices: Device[];
  onRefresh: () => void;
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
          <h2>Overview</h2>
          <p>Centralized provider, model, and node status for phase 1.</p>
        </div>
        <button className="secondary-button" onClick={onRefresh}>
          Refresh
        </button>
      </div>

      <div className="stats-grid">
        <article className="stat-card">
          <span className="stat-label">Providers</span>
          <strong>{providers.length}</strong>
        </article>
        <article className="stat-card">
          <span className="stat-label">Models</span>
          <strong>{models.length}</strong>
        </article>
        <article className="stat-card">
          <span className="stat-label">Devices</span>
          <strong>{devices.length}</strong>
        </article>
        <article className="stat-card">
          <span className="stat-label">Needs Attention</span>
          <strong>{offlineDevices.length}</strong>
        </article>
      </div>

      <div className="panel">
        <h3>Device Status</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Last Seen</th>
              <th>Config Version</th>
            </tr>
          </thead>
          <tbody>
            {devices.length === 0 ? (
              <tr>
                <td colSpan={4} className="empty-cell">
                  No devices registered yet.
                </td>
              </tr>
            ) : (
              devices.map((device) => (
                <tr key={device.id}>
                  <td>{device.name}</td>
                  <td>{device.device_type}</td>
                  <td>{device.last_seen_at ?? "Never"}</td>
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

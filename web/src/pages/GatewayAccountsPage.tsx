import { useEffect, useState } from "react";

import GatewayAliasesPage from "./GatewayAliasesPage";
import { api, type GatewayUpstreamAccount } from "../lib/api";

const authOptions = [
  { value: "bearer", label: "Bearer" },
  { value: "x-api-key", label: "X-API-Key" },
  { value: "none", label: "无鉴权" },
  { value: "passcode", label: "Passcode" },
] as const;

const healthLabels: Record<string, string> = {
  UNKNOWN: "未知",
  HEALTHY: "健康",
  DEGRADED: "降级",
  ERROR: "异常",
};

export default function GatewayAccountsPage() {
  const [accounts, setAccounts] = useState<GatewayUpstreamAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    name: "",
    base_url: "",
    auth_type: "bearer",
    api_key: "",
    protocol: "openai-compatible",
    notes: "",
  });

  async function loadAccounts() {
    setLoading(true);
    try {
      setAccounts(await api.getGatewayAccounts());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAccounts();
  }, []);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setMessage("");
    await api.createGatewayAccount(form);
    setForm({
      name: "",
      base_url: "",
      auth_type: "bearer",
      api_key: "",
      protocol: "openai-compatible",
      notes: "",
    });
    setMessage("Gateway 上游账号已创建。");
    await loadAccounts();
  }

  async function handleTest(accountId: number) {
    const result = await api.testGatewayAccount(accountId);
    setMessage(result.healthy ? "Gateway 账号测试通过。" : `Gateway 账号测试失败：HTTP ${result.models_status}`);
    await loadAccounts();
  }

  async function handleSync(accountId: number) {
    const result = await api.syncGatewayAccountModels(accountId);
    setMessage(`已同步 ${result.models_count} 个模型，新增或更新 ${result.upserted_count} 个。`);
    await loadAccounts();
  }

  return (
    <section className="page">
      <form className="panel form-panel" onSubmit={handleCreate}>
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>Gateway Upstream Accounts</h3>
          <p>接入公益站、官方站或代理站，并同步它们可用的真实模型。后续别名和 failover 会挂在这些账号之上。</p>
        </div>
        <div className="editor-grid">
          <label>
            <span>名称</span>
            <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
          </label>
          <label>
            <span>Base URL</span>
            <input value={form.base_url} onChange={(event) => setForm((current) => ({ ...current, base_url: event.target.value }))} placeholder="https://example.com/v1" />
          </label>
          <label>
            <span>鉴权方式</span>
            <select value={form.auth_type} onChange={(event) => setForm((current) => ({ ...current, auth_type: event.target.value }))}>
              {authOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>API Key</span>
            <input value={form.api_key} onChange={(event) => setForm((current) => ({ ...current, api_key: event.target.value }))} />
          </label>
        </div>
        <label>
          <span>备注</span>
          <textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} />
        </label>
        <div className="topbar-actions">
          <button type="submit">新增 Gateway 账号</button>
          <button type="button" className="secondary-button" onClick={() => void loadAccounts()}>
            {loading ? "加载中" : "刷新"}
          </button>
        </div>
        {message ? <p className="inline-message">{message}</p> : null}
      </form>

      <div className="panel placeholder-panel">
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>当前账号</h3>
          <p>当前阶段先把上游账号、模型同步和健康状态接通。Aliases、Client Keys 和 failover 细节会在后续任务里继续展开。</p>
        </div>
        {accounts.length === 0 ? (
          <div className="empty-state">还没有任何 Gateway 上游账号。</div>
        ) : (
          <div className="placeholder-grid">
            {accounts.map((account) => (
              <article key={account.id} className="placeholder-card">
                <strong>{account.name}</strong>
                <span>{account.base_url}</span>
                <span>鉴权：{account.auth_type}</span>
                <span>协议：{account.protocol}</span>
                <span>健康状态：{healthLabels[account.health_status] ?? account.health_status}</span>
                <span>已同步模型：{account.synced_models_count}</span>
                <div className="topbar-actions">
                  <button type="button" className="secondary-button" onClick={() => void handleTest(account.id)}>
                    测试连接
                  </button>
                  <button type="button" className="secondary-button" onClick={() => void handleSync(account.id)}>
                    同步模型
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      <GatewayAliasesPage />
    </section>
  );
}

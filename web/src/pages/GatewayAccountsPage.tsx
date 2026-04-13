import { useEffect, useState } from "react";

import GatewayAliasesPage from "./GatewayAliasesPage";
import GatewayClientKeysPage from "./GatewayClientKeysPage";
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
  const [editingAccountId, setEditingAccountId] = useState<number | null>(null);
  const [accountFeedback, setAccountFeedback] = useState<Record<number, { tone: "success" | "error"; text: string }>>({});
  const [testingAccountId, setTestingAccountId] = useState<number | null>(null);
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
    if (editingAccountId == null) {
      await api.createGatewayAccount(form);
      setMessage("Gateway 上游账号已创建。");
    } else {
      await api.updateGatewayAccount(editingAccountId, { ...form, enabled: true });
      setMessage("Gateway 账号已更新。");
      setEditingAccountId(null);
    }
    setForm({
      name: "",
      base_url: "",
      auth_type: "bearer",
      api_key: "",
      protocol: "openai-compatible",
      notes: "",
    });
    await loadAccounts();
  }

  async function handleTest(accountId: number) {
    setTestingAccountId(accountId);
    try {
      const result = await api.testGatewayAccount(accountId);
      setAccountFeedback((current) => ({
        ...current,
        [accountId]: {
          tone: result.healthy ? "success" : "error",
          text: result.healthy ? "测试通过" : `测试失败（HTTP ${result.models_status}）`,
        },
      }));
      await loadAccounts();
    } finally {
      setTestingAccountId(null);
    }
  }

  async function handleEdit(accountId: number) {
    const account = await api.getGatewayAccount(accountId);
    setEditingAccountId(accountId);
    setForm({
      name: account.name,
      base_url: account.base_url,
      auth_type: account.auth_type,
      api_key: account.api_key_encrypted,
      protocol: account.protocol,
      notes: account.notes,
    });
    setMessage("");
  }

  async function handleDelete(accountId: number) {
    const confirmed = window.confirm("确认删除这个 Gateway 账号吗？");
    if (!confirmed) return;
    await api.deleteGatewayAccount(accountId);
    if (editingAccountId === accountId) {
      setEditingAccountId(null);
      setForm({
        name: "",
        base_url: "",
        auth_type: "bearer",
        api_key: "",
        protocol: "openai-compatible",
        notes: "",
      });
    }
    setMessage("Gateway 账号已删除。");
    await loadAccounts();
  }

  function handleCancelEdit() {
    setEditingAccountId(null);
    setForm({
      name: "",
      base_url: "",
      auth_type: "bearer",
      api_key: "",
      protocol: "openai-compatible",
      notes: "",
    });
  }

  return (
    <section className="page">
      <form className="panel form-panel" onSubmit={handleCreate}>
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>{editingAccountId == null ? "Gateway Upstream Accounts" : "编辑 Gateway 账号"}</h3>
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
          <button type="submit">{editingAccountId == null ? "新增 Gateway 账号" : "保存修改"}</button>
          {editingAccountId != null ? (
            <button type="button" className="secondary-button" onClick={handleCancelEdit}>
              取消编辑
            </button>
          ) : null}
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
                <strong>
                  {account.name}
                  {accountFeedback[account.id] ? (
                    <span
                      style={{
                        marginLeft: 8,
                        color: accountFeedback[account.id].tone === "success" ? "#1f8f53" : "#b3392a",
                        fontSize: "0.9rem",
                        fontWeight: 600,
                      }}
                    >
                      {accountFeedback[account.id].text}
                    </span>
                  ) : null}
                </strong>
                <span>{account.base_url}</span>
                <span>鉴权：{account.auth_type}</span>
                <span>协议：{account.protocol}</span>
                <span>健康状态：{healthLabels[account.health_status] ?? account.health_status}</span>
                {account.cooldown_until ? <span>冷却到：{account.cooldown_until}</span> : null}
                <div className="topbar-actions">
                  <button type="button" className="secondary-button" onClick={() => void handleTest(account.id)}>
                    {testingAccountId === account.id ? "测试中..." : "测试连接"}
                  </button>
                  <button type="button" className="secondary-button" onClick={() => void handleEdit(account.id)}>
                    查看/编辑
                  </button>
                  <button type="button" className="secondary-button" onClick={() => void handleDelete(account.id)}>
                    删除
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      <GatewayAliasesPage />
      <GatewayClientKeysPage />
    </section>
  );
}

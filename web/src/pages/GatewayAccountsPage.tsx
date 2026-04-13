import { useDeferredValue, useEffect, useMemo, useState } from "react";

import GatewayAliasesPage from "./GatewayAliasesPage";
import GatewayClientKeysPage from "./GatewayClientKeysPage";
import { api, type DiscoveredProviderModel, type GatewayModel, type GatewayUpstreamAccount } from "../lib/api";

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

const avatarToneClasses = [
  "tone-coral",
  "tone-sky",
  "tone-mint",
  "tone-amber",
  "tone-plum",
  "tone-rose",
  "tone-indigo",
  "tone-lime",
];

function normalizeModelKey(value: string): string {
  return value.trim().toLowerCase();
}

function buildModelGroupLabel(model: DiscoveredProviderModel): string {
  if (model.owner?.trim()) {
    return model.owner.trim();
  }
  const source = model.upstream_model.trim().toLowerCase();
  const segments = source.split("/").filter(Boolean);
  if (segments.length >= 2) {
    return segments[0];
  }
  return segments[0] || "other";
}

function buildModelAvatarLabel(model: DiscoveredProviderModel): string {
  const source = model.display_name || model.upstream_model;
  const tail = source.split("/").pop() ?? source;
  const compact = tail.replace(/[^a-zA-Z0-9]/g, "").toUpperCase();
  return compact.slice(0, 2) || "ML";
}

export default function GatewayAccountsPage() {
  const [accounts, setAccounts] = useState<GatewayUpstreamAccount[]>([]);
  const [gatewayModels, setGatewayModels] = useState<GatewayModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [editingAccountId, setEditingAccountId] = useState<number | null>(null);
  const [accountFeedback, setAccountFeedback] = useState<Record<number, { tone: "success" | "error"; text: string }>>({});
  const [testingAccountId, setTestingAccountId] = useState<number | null>(null);
  const [discoverAccountId, setDiscoverAccountId] = useState<number | null>(null);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [discoverMessage, setDiscoverMessage] = useState("");
  const [discoverMessageTone, setDiscoverMessageTone] = useState<"success" | "error">("success");
  const [discoverSearch, setDiscoverSearch] = useState("");
  const [discoveredModels, setDiscoveredModels] = useState<DiscoveredProviderModel[]>([]);
  const [selectedDiscoveredIds, setSelectedDiscoveredIds] = useState<string[]>([]);
  const [expandedDiscoverGroups, setExpandedDiscoverGroups] = useState<Record<string, boolean>>({});
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
      const [accountItems, gatewayModelItems] = await Promise.all([
        api.getGatewayAccounts(),
        api.getGatewayModels(),
      ]);
      setAccounts(accountItems);
      setGatewayModels(gatewayModelItems);
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

  const deferredDiscoverSearch = useDeferredValue(discoverSearch.trim().toLowerCase());

  const groupedDiscoveredModels = useMemo(() => {
    const filtered = discoveredModels.filter((model) => {
      if (!deferredDiscoverSearch) {
        return true;
      }
      const haystack = `${model.upstream_model} ${model.display_name} ${buildModelGroupLabel(model)}`.toLowerCase();
      return haystack.includes(deferredDiscoverSearch);
    });

    const groups = new Map<string, DiscoveredProviderModel[]>();
    filtered.forEach((model) => {
      const groupLabel = buildModelGroupLabel(model);
      const currentGroup = groups.get(groupLabel) ?? [];
      currentGroup.push(model);
      groups.set(groupLabel, currentGroup);
    });

    return Array.from(groups.entries())
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([label, groupModels]) => ({ label, models: groupModels }));
  }, [deferredDiscoverSearch, discoveredModels]);

  const existingGatewayModelKeys = useMemo(
    () =>
      new Set(
        gatewayModels
          .filter((model) => discoverAccountId != null && model.account_id === discoverAccountId)
          .map((model) => normalizeModelKey(model.upstream_model)),
      ),
    [discoverAccountId, gatewayModels],
  );

  async function handleDiscoverModels(accountId: number) {
    setDiscoverAccountId(accountId);
    setDiscoverLoading(true);
    setDiscoverMessage("");
    setDiscoverMessageTone("success");
    try {
      const result = await api.discoverGatewayAccountModels(accountId);
      setDiscoveredModels(result.models);
      setSelectedDiscoveredIds([]);
      const nextExpanded: Record<string, boolean> = {};
      result.models.forEach((model) => {
        nextExpanded[buildModelGroupLabel(model)] = false;
      });
      setExpandedDiscoverGroups(nextExpanded);
      setDiscoverMessageTone("success");
      setDiscoverMessage(
        result.count > 0
          ? `已拉取 ${result.count} 个模型，请选择后导入。`
          : "上游返回了空模型列表。",
      );
    } catch (error) {
      setDiscoveredModels([]);
      setSelectedDiscoveredIds([]);
      setDiscoverMessageTone("error");
      setDiscoverMessage(error instanceof Error ? error.message : "拉取模型列表失败。");
    } finally {
      setDiscoverLoading(false);
    }
  }

  function toggleDiscoveredModel(modelId: string) {
    setSelectedDiscoveredIds((current) =>
      current.includes(modelId) ? current.filter((item) => item !== modelId) : [...current, modelId],
    );
  }

  function toggleDiscoveredGroup(groupLabel: string) {
    setExpandedDiscoverGroups((current) => ({
      ...current,
      [groupLabel]: !current[groupLabel],
    }));
  }

  function handleSelectVisibleDiscoveredModels() {
    const selectable = groupedDiscoveredModels.flatMap((group) =>
      group.models
        .filter((model) => !existingGatewayModelKeys.has(normalizeModelKey(model.upstream_model)))
        .map((model) => model.upstream_model),
    );
    setSelectedDiscoveredIds(Array.from(new Set([...selectedDiscoveredIds, ...selectable])));
  }

  function handleClearDiscoveredSelection() {
    setSelectedDiscoveredIds([]);
  }

  async function handleImportSelectedDiscoveredModels() {
    if (discoverAccountId == null || selectedDiscoveredIds.length === 0) {
      return;
    }
    const selectedModels = discoveredModels.filter((model) =>
      selectedDiscoveredIds.includes(model.upstream_model),
    );
    const result = await api.importGatewayAccountModels(
      discoverAccountId,
      selectedModels.map((model) => ({
        upstream_model: model.upstream_model,
        display_name: model.display_name,
        owner: model.owner,
      })),
    );
    setAccountFeedback((current) => ({
      ...current,
      [discoverAccountId]: {
        tone: "success",
        text: `已导入 ${result.imported_count} 个模型`,
      },
    }));
    setDiscoverAccountId(null);
    setDiscoveredModels([]);
    setSelectedDiscoveredIds([]);
    setDiscoverSearch("");
    setExpandedDiscoverGroups({});
    await loadAccounts();
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
                  <button type="button" className="secondary-button" onClick={() => void handleDiscoverModels(account.id)}>
                    获取模型列表
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

      {discoverAccountId != null ? (
        <div className="modal-backdrop" onClick={() => setDiscoverAccountId(null)}>
          <div
            className="modal-panel model-discovery-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="gateway-model-discovery-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <h3 id="gateway-model-discovery-title">获取模型列表</h3>
                <p>从当前 Gateway 账号的 `/models` 拉取模型后，选择要导入到 Gateway 的条目。</p>
              </div>
              <button type="button" className="secondary-button" onClick={() => setDiscoverAccountId(null)}>
                关闭
              </button>
            </div>

            <div className="model-picker-toolbar">
              <input
                placeholder="搜索模型 ID 或名称"
                value={discoverSearch}
                onChange={(event) => setDiscoverSearch(event.target.value)}
              />
              <div className="topbar-actions">
                <button type="button" className="secondary-button" onClick={handleSelectVisibleDiscoveredModels}>
                  全选可见
                </button>
                <button type="button" className="secondary-button" onClick={handleClearDiscoveredSelection}>
                  清空选择
                </button>
                <button type="button" className="secondary-button" onClick={() => void handleDiscoverModels(discoverAccountId)}>
                  {discoverLoading ? "刷新中..." : "刷新"}
                </button>
              </div>
            </div>

            {discoverMessage ? (
              <p className={discoverMessageTone === "success" ? "inline-message" : "error-inline-message"}>
                {discoverMessage}
              </p>
            ) : null}

            <div className="model-discovery-summary">
              <span>已发现 {discoveredModels.length} 个模型</span>
              <span>已选择 {selectedDiscoveredIds.length} 个</span>
            </div>

            <div className="model-picker-groups">
              {groupedDiscoveredModels.length === 0 ? (
                <div className="empty-state">{discoverLoading ? "正在拉取模型列表..." : "没有可显示的模型。"}</div>
              ) : (
                groupedDiscoveredModels.map((group, groupIndex) => (
                  <section key={group.label} className="model-picker-group">
                    <div className="model-picker-group-header">
                      <div className="model-picker-group-labels">
                        <strong>{group.label}</strong>
                        <span className="model-picker-group-count">{group.models.length} 个模型</span>
                      </div>
                      <button
                        type="button"
                        className="model-picker-group-toggle-button"
                        onClick={() => toggleDiscoveredGroup(group.label)}
                      >
                        {expandedDiscoverGroups[group.label] ? "收起" : "展开"}
                      </button>
                    </div>
                    {expandedDiscoverGroups[group.label] ? (
                      <div className="model-picker-group-list">
                        {group.models.map((model, modelIndex) => {
                          const normalizedModelId = normalizeModelKey(model.upstream_model);
                          const alreadyImported = existingGatewayModelKeys.has(normalizedModelId);
                          const toneClass =
                            avatarToneClasses[(groupIndex + modelIndex) % avatarToneClasses.length];
                          return (
                            <label
                              key={model.upstream_model}
                              className={`model-picker-row ${alreadyImported ? "is-disabled" : ""}`}
                            >
                              <input
                                type="checkbox"
                                checked={selectedDiscoveredIds.includes(model.upstream_model)}
                                disabled={alreadyImported}
                                onChange={() => toggleDiscoveredModel(model.upstream_model)}
                              />
                              <div className={`model-picker-icon ${toneClass}`}>
                                {buildModelAvatarLabel(model)}
                              </div>
                              <div className="model-picker-row-main">
                                <strong>{model.display_name}</strong>
                                <span>{model.upstream_model}</span>
                              </div>
                              <div className="model-picker-row-tags">
                                {model.owner ? <span className="mini-pill">{model.owner}</span> : null}
                                {alreadyImported ? <span className="mini-pill mini-pill-muted">已在列表</span> : null}
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    ) : null}
                  </section>
                ))
              )}
            </div>

            <div className="modal-footer">
              <button type="button" className="secondary-button" onClick={() => setDiscoverAccountId(null)}>
                取消
              </button>
              <button
                type="button"
                onClick={() => void handleImportSelectedDiscoveredModels()}
                disabled={discoverLoading || selectedDiscoveredIds.length === 0}
              >
                导入选中模型
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

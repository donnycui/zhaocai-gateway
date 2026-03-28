import { useEffect, useMemo, useState, type ReactNode } from "react";

import {
  api,
  type Model,
  type Provider,
  type ProviderTestReport,
} from "../lib/api";

interface ProvidersPageProps {
  providers: Provider[];
  models: Model[];
  onRefresh: () => Promise<void>;
  onCreate: () => void;
  onEdit: (providerId: number) => void;
}

const protocolLabels: Record<string, string> = {
  "openai-completions": "OpenAI Completions",
  "openai-responses": "OpenAI Responses",
  "anthropic-messages": "Anthropic Messages",
  openai: "OpenAI Completions",
  anthropic: "Anthropic Messages",
};

const ONE_HOUR_MS = 60 * 60 * 1000;

function providerSupportsLiveBalance(provider: Provider): boolean {
  const queryType = (provider.balance_query_type ?? "").toLowerCase();
  if (queryType === "openrouter" || queryType === "newapi") {
    return true;
  }
  const name = provider.name.toLowerCase();
  const baseUrl = provider.base_url.toLowerCase();
  return name.includes("openrouter") || baseUrl.includes("openrouter.ai");
}

function formatBalance(provider: Provider): string {
  if (!providerSupportsLiveBalance(provider) && provider.balance_status !== "ok") {
    return "暂不支持";
  }
  if (provider.balance_status === "ok" && provider.balance_amount != null) {
    const amount = provider.balance_amount.toFixed(2);
    const currency = provider.balance_currency ?? "";
    return currency ? `${amount} ${currency}` : amount;
  }
  if (provider.balance_status === "error") {
    return "查询失败";
  }
  if (provider.balance_status === "loading") {
    return "查询中...";
  }
  if (provider.balance_message) {
    return provider.balance_message;
  }
  return providerSupportsLiveBalance(provider) ? "等待刷新" : "暂不支持";
}

function formatBalanceTime(provider: Provider): string {
  if (!provider.balance_fetched_at) {
    return "未刷新";
  }

  const date = new Date(provider.balance_fetched_at);
  if (Number.isNaN(date.getTime())) {
    return "未知";
  }

  const diffMs = Date.now() - date.getTime();
  if (diffMs < 60_000) {
    return "刚刚";
  }
  if (diffMs < 60 * 60_000) {
    return `${Math.max(1, Math.floor(diffMs / 60_000))} 分钟前`;
  }
  return `${Math.max(1, Math.floor(diffMs / (60 * 60_000)))} 小时前`;
}

function buildDuplicateName(name: string, existingNames: Set<string>): string {
  const base = `${name} 副本`;
  if (!existingNames.has(base)) {
    return base;
  }
  let index = 2;
  while (existingNames.has(`${base} ${index}`)) {
    index += 1;
  }
  return `${base} ${index}`;
}

function IconButton({
  title,
  onClick,
  children,
  disabled = false,
}: {
  title: string;
  onClick: () => void;
  children: ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      className="icon-button"
      title={title}
      aria-label={title}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

function RefreshIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 5a7 7 0 0 1 6.31 4H16v2h6V5h-2v2.13A9 9 0 1 0 21 12h-2a7 7 0 1 1-7-7Z"
        fill="currentColor"
      />
    </svg>
  );
}

function TestIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M9 3h6v2l-1 1v3.09l4.69 7.82A3 3 0 0 1 16.12 21H7.88a3 3 0 0 1-2.57-4.09L10 9.09V6L9 5V3Zm2 3v3.64l-4.98 8.31a1 1 0 0 0 .86 1.5h8.24a1 1 0 0 0 .86-1.5L13 9.64V6h-2Z"
        fill="currentColor"
      />
    </svg>
  );
}

function EditIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M15.17 3.59a2 2 0 0 1 2.83 0l2.41 2.41a2 2 0 0 1 0 2.83L9.24 20H4v-5.24L15.17 3.59Zm1.41 1.41L6 15.59V18h2.41L19 7.41 16.58 5Z"
        fill="currentColor"
      />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M9 9a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-8a2 2 0 0 1-2-2V9Zm2 0v8h8V9h-8ZM5 5a2 2 0 0 1 2-2h8v2H7v8H5V5Z"
        fill="currentColor"
      />
    </svg>
  );
}

function DeleteIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M9 3h6l1 2h4v2H4V5h4l1-2Zm-2 6h2v8H7V9Zm4 0h2v8h-2V9Zm4 0h2v8h-2V9ZM6 21a2 2 0 0 1-2-2V8h16v11a2 2 0 0 1-2 2H6Z"
        fill="currentColor"
      />
    </svg>
  );
}

export default function ProvidersPage({
  providers,
  models,
  onRefresh,
  onCreate,
  onEdit,
}: ProvidersPageProps) {
  const [message, setMessage] = useState<string>("");
  const [testingProviderId, setTestingProviderId] = useState<number | null>(null);
  const [refreshingBalanceIds, setRefreshingBalanceIds] = useState<number[]>([]);
  const [duplicatingProviderId, setDuplicatingProviderId] = useState<number | null>(null);
  const [testReport, setTestReport] = useState<ProviderTestReport | null>(null);

  const modelCounts = useMemo(() => {
    const counts = new Map<number, number>();
    models.forEach((model) => {
      counts.set(model.provider_id, (counts.get(model.provider_id) ?? 0) + 1);
    });
    return counts;
  }, [models]);

  useEffect(() => {
    let cancelled = false;

    async function refreshStaleBalances() {
      const staleProviderIds = providers
        .filter(providerSupportsLiveBalance)
        .filter((provider) => {
          if (!provider.balance_fetched_at) {
            return true;
          }
          const fetchedAt = new Date(provider.balance_fetched_at).getTime();
          return Number.isNaN(fetchedAt) || Date.now() - fetchedAt >= ONE_HOUR_MS;
        })
        .map((provider) => provider.id);

      if (staleProviderIds.length === 0) {
        return;
      }

      setRefreshingBalanceIds((current) => Array.from(new Set([...current, ...staleProviderIds])));
      try {
        await api.refreshProviderBalances(staleProviderIds);
        if (!cancelled) {
          await onRefresh();
        }
      } finally {
        if (!cancelled) {
          setRefreshingBalanceIds((current) => current.filter((id) => !staleProviderIds.includes(id)));
        }
      }
    }

    void refreshStaleBalances();
    const timer = window.setInterval(() => {
      void refreshStaleBalances();
    }, ONE_HOUR_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [providers, onRefresh]);

  async function handleSyncOpenRouterFree() {
    const result = await api.syncOpenRouterFree();
    setMessage(
      `已同步免费模型 ${result.free_models_found} 个，新建 ${result.created} 个，更新 ${result.updated} 个。`,
    );
    await onRefresh();
  }

  async function handleDeleteProvider(providerId: number) {
    const confirmed = window.confirm("确认删除这个供应商以及其下所有模型吗？");
    if (!confirmed) return;
    await api.deleteProvider(providerId);
    setMessage("供应商已删除。");
    await onRefresh();
  }

  async function handleTestProvider(providerId: number) {
    setTestingProviderId(providerId);
    setMessage("");
    try {
      const result = await api.testProvider(providerId);
      setTestReport(result);
    } finally {
      setTestingProviderId(null);
    }
  }

  async function handleRefreshBalance(providerId: number) {
    setRefreshingBalanceIds((current) => Array.from(new Set([...current, providerId])));
    try {
      await api.refreshProviderBalance(providerId);
      setMessage("余额已刷新。");
      await onRefresh();
    } finally {
      setRefreshingBalanceIds((current) => current.filter((id) => id !== providerId));
    }
  }

  async function handleDuplicateProvider(providerId: number) {
    setDuplicatingProviderId(providerId);
    try {
      const payload = await api.getProvider(providerId);
      const existingNames = new Set(providers.map((provider) => provider.name));
      const duplicatedProvider = await api.createProvider({
        name: buildDuplicateName(payload.provider.name, existingNames),
        base_url: payload.provider.base_url,
        provider_type: payload.provider.provider_type,
        auth_scheme: payload.provider.auth_scheme,
        api_key: payload.provider.api_key_encrypted,
        extra_headers: payload.provider.extra_headers,
      });

      for (const model of payload.models) {
        await api.createModel({
          provider_id: duplicatedProvider.id,
          upstream_model: model.upstream_model,
          display_name: model.display_name,
          capabilities: model.capabilities,
          reasoning: model.reasoning,
          input_modalities: model.input_modalities,
          context_window: model.context_window,
          max_tokens: model.max_tokens,
          cost_input: model.cost_input ?? null,
          cost_output: model.cost_output ?? null,
          cost_cache_read: model.cost_cache_read ?? null,
          cost_cache_write: model.cost_cache_write ?? null,
          enabled: model.enabled,
        });
      }

      setMessage("供应商已复制。");
      await onRefresh();
    } finally {
      setDuplicatingProviderId(null);
    }
  }

  return (
    <section className="page">
      <div className="panel">
        <div className="page-header">
          <div className="panel-header" style={{ marginBottom: 0 }}>
            <h3>供应商</h3>
            <p>统一管理上游供应商，悬停时显示编辑、复制、测试和删除等操作。</p>
          </div>
          <div className="topbar-actions">
            <button className="secondary-button" onClick={() => void handleSyncOpenRouterFree()}>
              同步 OpenRouter 免费模型
            </button>
            <button onClick={onCreate}>新增供应商</button>
          </div>
        </div>
        {message ? <p className="inline-message">{message}</p> : null}
        {testReport ? (
          <div className="test-results-panel">
            <div className="panel-header" style={{ marginBottom: 0 }}>
              <h3>{testReport.provider.name} 测试结果</h3>
              <p>{testReport.message}</p>
            </div>
            {testReport.results.length === 0 ? (
              <p className="inline-message">当前没有可检测的模型。</p>
            ) : (
              <div className="test-result-list">
                {testReport.results.map((result) => (
                  <div key={result.model_id} className="test-result-row">
                    <div className="test-result-main">
                      <strong>{result.display_name || result.model_id}</strong>
                      <span>{result.model_id}</span>
                    </div>
                    <div className="test-result-meta">
                      <span className={result.ok ? "status-chip" : "error-chip"}>
                        {result.ok ? "通过" : "失败"}
                      </span>
                      <span>{result.latency_ms} ms</span>
                    </div>
                    <p>{result.message}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : null}

        <div className="provider-card-list">
          {providers.length === 0 ? (
            <div className="empty-state">还没有任何供应商。</div>
          ) : (
            providers.map((provider) => {
              const refreshingBalance = refreshingBalanceIds.includes(provider.id);
              return (
                <article key={provider.id} className="provider-card">
                  <div className="provider-card-main">
                    <div className="provider-avatar">
                      {provider.name.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="provider-info">
                      <strong>{provider.name}</strong>
                      <span className="provider-url">{provider.base_url}</span>
                    </div>
                    <div className="provider-protocol-badge">
                      {protocolLabels[provider.provider_type] ?? provider.provider_type}
                    </div>
                    <div className="provider-side-rail">
                      <div className="provider-telemetry">
                        <div className="provider-telemetry-top">
                          <IconButton
                            title="刷新余额"
                            onClick={() => void handleRefreshBalance(provider.id)}
                            disabled={refreshingBalance}
                          >
                            <RefreshIcon />
                          </IconButton>
                          <div className="provider-balance-block">
                            <span className="provider-balance-time">{formatBalanceTime(provider)}</span>
                            <strong className="provider-balance-value">{formatBalance(provider)}</strong>
                          </div>
                        </div>
                        <span className="provider-balance-meta">{modelCounts.get(provider.id) ?? 0} 个模型</span>
                      </div>

                      <div className="provider-card-actions">
                        <IconButton
                          title="测试供应商"
                          onClick={() => void handleTestProvider(provider.id)}
                          disabled={testingProviderId === provider.id}
                        >
                          <TestIcon />
                        </IconButton>
                        <IconButton
                          title="复制供应商"
                          onClick={() => void handleDuplicateProvider(provider.id)}
                          disabled={duplicatingProviderId === provider.id}
                        >
                          <CopyIcon />
                        </IconButton>
                        <IconButton title="编辑供应商" onClick={() => onEdit(provider.id)}>
                          <EditIcon />
                        </IconButton>
                        <IconButton title="删除供应商" onClick={() => void handleDeleteProvider(provider.id)}>
                          <DeleteIcon />
                        </IconButton>
                      </div>
                    </div>
                  </div>
                </article>
              );
            })
          )}
        </div>
      </div>
    </section>
  );
}

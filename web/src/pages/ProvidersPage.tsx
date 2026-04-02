import { useMemo, useState, type ReactNode } from "react";

import GatewayAccountsPage from "./GatewayAccountsPage";
import MediaProvidersPage from "./MediaProvidersPage";
import UniversalTemplatesPage from "./UniversalTemplatesPage";
import { api, type Model, type Provider, type ProviderTestReport } from "../lib/api";

interface ProvidersPageProps {
  providers: Provider[];
  models: Model[];
  onRefresh: () => Promise<void>;
  onCreate: () => void;
  onEdit: (providerId: number) => void;
}

type ProviderModule = "openclaw" | "gateway" | "media" | "universal";

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

const protocolLabels: Record<string, string> = {
  "openai-completions": "OpenAI Completions",
  "openai-responses": "OpenAI Responses",
  "anthropic-messages": "Anthropic Messages",
  openai: "OpenAI Completions",
  anthropic: "Anthropic Messages",
};

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
  const [activeModule, setActiveModule] = useState<ProviderModule>("openclaw");
  const [message, setMessage] = useState<string>("");
  const [testingProviderId, setTestingProviderId] = useState<number | null>(null);
  const [duplicatingProviderId, setDuplicatingProviderId] = useState<number | null>(null);
  const [testReport, setTestReport] = useState<ProviderTestReport | null>(null);

  const modelCounts = useMemo(() => {
    const counts = new Map<number, number>();
    models.forEach((model) => {
      counts.set(model.provider_id, (counts.get(model.provider_id) ?? 0) + 1);
    });
    return counts;
  }, [models]);

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

  function renderOpenClawModule() {
    return (
      <div className="panel">
        <div className="page-header">
          <div className="panel-header" style={{ marginBottom: 0 }}>
            <h3>OpenClaw 供应商</h3>
            <p>当前页面管理的是 OpenClaw 模块的上游供应商与模型，Gateway 和 Media 会拆到独立模块。</p>
          </div>
          <div className="topbar-actions">
            <button className="secondary-button" onClick={() => void handleSyncOpenRouterFree()}>
              同步 OpenRouter 免费模型到 OpenClaw
            </button>
            <button onClick={onCreate}>新增 OpenClaw 供应商</button>
          </div>
        </div>
        {message ? <p className="inline-message">{message}</p> : null}
        {testReport ? (
          <div className="test-results-panel">
            <div className="panel-header" style={{ marginBottom: 0 }}>
              <h3>{testReport.provider.name} OpenClaw 测试结果</h3>
              <p>{testReport.message}</p>
            </div>
            {testReport.results.length === 0 ? (
              <p className="inline-message">当前没有可检测的 OpenClaw 模型。</p>
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
            <div className="empty-state">还没有任何 OpenClaw 供应商。</div>
          ) : (
            providers.map((provider, index) => (
              <article key={provider.id} className="provider-card">
                <div className="provider-card-main">
                  <div className={`provider-avatar ${avatarToneClasses[index % avatarToneClasses.length]}`}>
                    {provider.name.slice(0, 2).toUpperCase()}
                  </div>

                  <div className="provider-info">
                    <strong>{provider.name}</strong>
                    <span className="provider-url">{provider.base_url}</span>
                  </div>

                  <div className="provider-protocol-badge">
                    {protocolLabels[provider.provider_type] ?? provider.provider_type}
                  </div>

                  <div className="provider-meta-block">
                    <span className="provider-balance-meta">{modelCounts.get(provider.id) ?? 0} 个模型</span>
                  </div>

                  <div className="provider-card-actions">
                    <IconButton
                      title="测试 OpenClaw 供应商"
                      onClick={() => void handleTestProvider(provider.id)}
                      disabled={testingProviderId === provider.id}
                    >
                      <TestIcon />
                    </IconButton>
                    <IconButton
                      title="复制 OpenClaw 供应商"
                      onClick={() => void handleDuplicateProvider(provider.id)}
                      disabled={duplicatingProviderId === provider.id}
                    >
                      <CopyIcon />
                    </IconButton>
                    <IconButton title="编辑 OpenClaw 供应商" onClick={() => onEdit(provider.id)}>
                      <EditIcon />
                    </IconButton>
                    <IconButton title="删除 OpenClaw 供应商" onClick={() => void handleDeleteProvider(provider.id)}>
                      <DeleteIcon />
                    </IconButton>
                  </div>
                </div>
              </article>
            ))
          )}
        </div>
      </div>
    );
  }

  return (
    <section className="page">
      <div className="panel">
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>资源中心</h3>
          <p>从这里分模块管理 OpenClaw、Gateway、Media 和 Universal 资源。当前默认先保留 OpenClaw 为主入口。</p>
        </div>
        <div className="module-tab-row">
          {[
            { id: "openclaw", label: "OpenClaw", summary: `${providers.length} 个供应商 / ${models.length} 个模型` },
            { id: "gateway", label: "Gateway", summary: "统一对外模型供给与 fallback" },
            { id: "media", label: "Media", summary: "媒体供应商与模板 catalog" },
            { id: "universal", label: "Universal", summary: "模板池与跨模块导入" },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              className={`module-tab ${activeModule === item.id ? "active" : ""}`}
              onClick={() => setActiveModule(item.id as ProviderModule)}
            >
              <strong>{item.label}</strong>
              <span>{item.summary}</span>
            </button>
          ))}
        </div>
      </div>

      {activeModule === "openclaw" ? renderOpenClawModule() : null}
      {activeModule === "gateway" ? <GatewayAccountsPage /> : null}
      {activeModule === "media" ? <MediaProvidersPage /> : null}
      {activeModule === "universal" ? <UniversalTemplatesPage /> : null}
    </section>
  );
}

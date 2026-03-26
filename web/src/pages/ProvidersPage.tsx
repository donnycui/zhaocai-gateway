import { useMemo, useState, type ReactNode } from "react";

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
  const [syncMessage, setSyncMessage] = useState<string>("");
  const [testingProviderId, setTestingProviderId] = useState<number | null>(null);
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
    setSyncMessage(
      `已同步免费模型 ${result.free_models_found} 个，新建 ${result.created} 个，更新 ${result.updated} 个。`,
    );
    await onRefresh();
  }

  async function handleDeleteProvider(providerId: number) {
    const confirmed = window.confirm("确认删除这个供应商以及其下所有模型吗？");
    if (!confirmed) return;
    await api.deleteProvider(providerId);
    await onRefresh();
  }

  async function handleTestProvider(providerId: number) {
    setTestingProviderId(providerId);
    setSyncMessage("");
    try {
      const result = await api.testProvider(providerId);
      setTestReport(result);
    } finally {
      setTestingProviderId(null);
    }
  }

  return (
    <section className="page">
      <div className="panel">
        <div className="page-header">
          <div className="panel-header" style={{ marginBottom: 0 }}>
            <h3>供应商</h3>
            <p>统一管理上游供应商，新增或编辑时进入单独的详情页。</p>
          </div>
          <div className="topbar-actions">
            <button className="secondary-button" onClick={() => void handleSyncOpenRouterFree()}>
              同步 OpenRouter 免费模型
            </button>
            <button onClick={onCreate}>新增供应商</button>
          </div>
        </div>
        {syncMessage ? <p className="inline-message">{syncMessage}</p> : null}
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
        <table className="table">
          <thead>
            <tr>
              <th>名称</th>
              <th>API 协议</th>
              <th>接口地址</th>
              <th>模型数</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {providers.length === 0 ? (
              <tr>
                <td colSpan={5} className="empty-cell">
                  还没有任何供应商。
                </td>
              </tr>
            ) : (
              providers.map((provider) => (
                <tr key={provider.id}>
                  <td>{provider.name}</td>
                  <td>{protocolLabels[provider.provider_type] ?? provider.provider_type}</td>
                  <td className="truncate-cell">{provider.base_url}</td>
                  <td>{modelCounts.get(provider.id) ?? 0}</td>
                  <td>
                    <div className="inline-actions">
                      <IconButton
                        title="测试供应商"
                        onClick={() => void handleTestProvider(provider.id)}
                        disabled={testingProviderId === provider.id}
                      >
                        <TestIcon />
                      </IconButton>
                      <IconButton title="编辑供应商" onClick={() => onEdit(provider.id)}>
                        <EditIcon />
                      </IconButton>
                      <IconButton title="删除供应商" onClick={() => void handleDeleteProvider(provider.id)}>
                        <DeleteIcon />
                      </IconButton>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

import { useMemo, useState } from "react";

import { api, type Model, type Provider } from "../lib/api";

interface ProvidersPageProps {
  providers: Provider[];
  models: Model[];
  onRefresh: () => Promise<void>;
  onCreate: () => void;
  onEdit: (providerId: number) => void;
}

export default function ProvidersPage({
  providers,
  models,
  onRefresh,
  onCreate,
  onEdit,
}: ProvidersPageProps) {
  const [syncMessage, setSyncMessage] = useState<string>("");
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
                  <td>{provider.provider_type}</td>
                  <td className="truncate-cell">{provider.base_url}</td>
                  <td>{modelCounts.get(provider.id) ?? 0}</td>
                  <td>
                    <div className="inline-actions">
                      <button className="secondary-button" onClick={() => onEdit(provider.id)}>
                        编辑
                      </button>
                      <button className="secondary-button" onClick={() => void handleDeleteProvider(provider.id)}>
                        删除
                      </button>
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

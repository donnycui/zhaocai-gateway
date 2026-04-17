import { useEffect, useState } from "react";

import { api, type MediaCatalogItem, type MediaProvider, type MediaTemplate } from "../lib/api";
import MediaTemplateEditorPage from "./MediaTemplateEditorPage";

export default function MediaTemplatesPage() {
  const [providers, setProviders] = useState<MediaProvider[]>([]);
  const [templates, setTemplates] = useState<MediaTemplate[]>([]);
  const [catalog, setCatalog] = useState<MediaCatalogItem[]>([]);
  const [message, setMessage] = useState("");
  const [editingTemplate, setEditingTemplate] = useState<MediaTemplate | null>(null);

  async function loadAll() {
    const [providersResult, templatesResult, catalogResult] = await Promise.allSettled([
      api.getMediaProviders(),
      api.getMediaTemplates(),
      api.getMediaCatalog(),
    ]);
    if (providersResult.status === "fulfilled") {
      setProviders(providersResult.value);
    }
    if (templatesResult.status === "fulfilled") {
      setTemplates(templatesResult.value);
    } else {
      setTemplates([]);
    }
    if (catalogResult.status === "fulfilled") {
      setCatalog(catalogResult.value);
    } else {
      setCatalog([]);
    }
    const errors = [templatesResult, catalogResult]
      .filter((result): result is PromiseRejectedResult => result.status === "rejected")
      .map((result) => (result.reason instanceof Error ? result.reason.message : "Media 数据加载失败"));
    setMessage(errors.join(" / "));
  }

  useEffect(() => {
    void loadAll();
  }, []);

  async function handleEdit(templateId: number) {
    const template = await api.getMediaTemplate(templateId);
    setEditingTemplate(template);
  }

  async function handleDelete(templateId: number) {
    const confirmed = window.confirm("确认删除这个 Media Template 吗？");
    if (!confirmed) return;
    await api.deleteMediaTemplate(templateId);
    if (editingTemplate?.id === templateId) {
      setEditingTemplate(null);
    }
    await loadAll();
  }

  return (
    <section className="page">
      <MediaTemplateEditorPage
        providers={providers}
        editingTemplate={editingTemplate}
        onSaved={async () => loadAll()}
        onCancelEdit={() => setEditingTemplate(null)}
      />
      {message ? <p className="error-inline-message">{message}</p> : null}

      <div className="panel placeholder-panel">
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>Media Templates</h3>
          <p>当前已登记的模板会在这里显示，供后续 catalog 与 `zhaocai-media` 消费。</p>
        </div>
        {templates.length === 0 ? (
          <div className="empty-state">还没有任何 Media template。</div>
        ) : (
          <div className="placeholder-grid">
            {templates.map((template) => (
              <article key={template.id} className="placeholder-card">
                <strong>{template.ui_label || template.name}</strong>
                <span>Provider：{template.provider_name ?? `#${template.provider_id}`}</span>
                <span>Model Key：{template.model_key}</span>
                <span>Capability：{template.capability}</span>
                <span>Template Type：{template.template_type}</span>
                <span>Upstream Model：{template.upstream_model}</span>
                <div className="topbar-actions">
                  <button type="button" className="secondary-button" onClick={() => void handleEdit(template.id)}>
                    查看/编辑
                  </button>
                  <button type="button" className="secondary-button" onClick={() => void handleDelete(template.id)}>
                    删除
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      <div className="panel placeholder-panel">
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>Media Catalog Preview</h3>
          <p>这里展示对外导出的 catalog 结果，后续 `zhaocai-media` 和网站会消费这一层。</p>
        </div>
        {catalog.length === 0 ? (
          <div className="empty-state">Catalog 目前为空。</div>
        ) : (
          <pre className="code-block">{JSON.stringify(catalog, null, 2)}</pre>
        )}
      </div>
    </section>
  );
}

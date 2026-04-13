import { useEffect, useState } from "react";

import { api, type UniversalProviderTemplate } from "../lib/api";

export default function UniversalTemplatesPage() {
  const [templates, setTemplates] = useState<UniversalProviderTemplate[]>([]);
  const [message, setMessage] = useState("");
  const [editingTemplateId, setEditingTemplateId] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: "",
    base_url: "",
    auth_type: "bearer",
    api_key: "",
    protocol: "openai-compatible",
    notes: "",
    upstream_model: "",
    display_name: "",
  });

  async function loadTemplates() {
    setTemplates(await api.getUniversalTemplates());
  }

  useEffect(() => {
    void loadTemplates();
  }, []);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    const payload = {
      name: form.name,
      base_url: form.base_url,
      auth_type: form.auth_type,
      api_key: form.api_key,
      protocol: form.protocol,
      notes: form.notes,
      models: [
        {
          upstream_model: form.upstream_model,
          display_name: form.display_name,
          capabilities: ["text"],
          reasoning: false,
          input_modalities: ["text"],
          context_window: null,
          max_tokens: null,
          enabled: true,
        },
      ],
    };
    if (editingTemplateId == null) {
      await api.createUniversalTemplate(payload);
      setMessage("Universal 模板已创建。");
    } else {
      await api.updateUniversalTemplate(editingTemplateId, payload);
      setEditingTemplateId(null);
      setMessage("Universal 模板已更新。");
    }
    setForm({
      name: "",
      base_url: "",
      auth_type: "bearer",
      api_key: "",
      protocol: "openai-compatible",
      notes: "",
      upstream_model: "",
      display_name: "",
    });
    await loadTemplates();
  }

  async function handleEdit(templateId: number) {
    const template = await api.getUniversalTemplate(templateId);
    const sampleModel = template.models[0];
    setEditingTemplateId(templateId);
    setForm({
      name: template.name,
      base_url: template.base_url,
      auth_type: template.auth_type,
      api_key: template.api_key_encrypted,
      protocol: template.protocol,
      notes: template.notes,
      upstream_model: sampleModel?.upstream_model ?? "",
      display_name: sampleModel?.display_name ?? "",
    });
    setMessage("");
  }

  async function handleDelete(templateId: number) {
    const confirmed = window.confirm("确认删除这个 Universal 模板吗？");
    if (!confirmed) return;
    await api.deleteUniversalTemplate(templateId);
    if (editingTemplateId === templateId) {
      setEditingTemplateId(null);
      setForm({
        name: "",
        base_url: "",
        auth_type: "bearer",
        api_key: "",
        protocol: "openai-compatible",
        notes: "",
        upstream_model: "",
        display_name: "",
      });
    }
    setMessage("Universal 模板已删除。");
    await loadTemplates();
  }

  function handleCancelEdit() {
    setEditingTemplateId(null);
    setForm({
      name: "",
      base_url: "",
      auth_type: "bearer",
      api_key: "",
      protocol: "openai-compatible",
      notes: "",
      upstream_model: "",
      display_name: "",
    });
  }

  async function handleImport(templateId: number, target: "openclaw" | "gateway" | "media") {
    await api.importUniversalTemplate(templateId, target);
    const targetLabel = target === "openclaw" ? "OpenClaw" : target === "gateway" ? "Gateway" : "Media";
    setMessage(`模板已导入到 ${targetLabel}。`);
  }

  return (
    <section className="page">
      <form className="panel form-panel" onSubmit={handleCreate}>
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>{editingTemplateId == null ? "Universal 模板池" : "编辑 Universal 模板"}</h3>
          <p>这里不直接参与运行时，而是作为可复用模板池，导入到 OpenClaw、Gateway 或 Media 后再各自独立管理。</p>
        </div>
        <div className="editor-grid">
          <label>
            <span>模板名称</span>
            <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
          </label>
          <label>
            <span>Base URL</span>
            <input value={form.base_url} onChange={(event) => setForm((current) => ({ ...current, base_url: event.target.value }))} />
          </label>
          <label>
            <span>鉴权方式</span>
            <select value={form.auth_type} onChange={(event) => setForm((current) => ({ ...current, auth_type: event.target.value }))}>
              <option value="bearer">Bearer</option>
              <option value="x-api-key">X-API-Key</option>
              <option value="none">无鉴权</option>
            </select>
          </label>
          <label>
            <span>API Key</span>
            <input value={form.api_key} onChange={(event) => setForm((current) => ({ ...current, api_key: event.target.value }))} />
          </label>
          <label>
            <span>示例模型 ID</span>
            <input value={form.upstream_model} onChange={(event) => setForm((current) => ({ ...current, upstream_model: event.target.value }))} />
          </label>
          <label>
            <span>示例模型显示名</span>
            <input value={form.display_name} onChange={(event) => setForm((current) => ({ ...current, display_name: event.target.value }))} />
          </label>
        </div>
        <label>
          <span>备注</span>
          <textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} />
        </label>
        <div className="topbar-actions">
          <button type="submit">{editingTemplateId == null ? "新增模板" : "保存修改"}</button>
          {editingTemplateId != null ? (
            <button type="button" className="secondary-button" onClick={handleCancelEdit}>
              取消编辑
            </button>
          ) : null}
        </div>
        {message ? <p className="inline-message">{message}</p> : null}
      </form>

      <div className="panel placeholder-panel">
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>当前模板</h3>
          <p>导入后目标模块拿到的是独立副本，不会反向修改这里的模板。</p>
        </div>
        {templates.length === 0 ? (
          <div className="empty-state">还没有任何 Universal 模板。</div>
        ) : (
          <div className="placeholder-grid">
            {templates.map((template) => (
              <article key={template.id} className="placeholder-card">
                <strong>{template.name}</strong>
                <span>{template.base_url}</span>
                <span>鉴权：{template.auth_type}</span>
                <span>模型数：{template.models.length}</span>
                <div className="topbar-actions">
                  <button type="button" className="secondary-button" onClick={() => void handleEdit(template.id)}>
                    查看/编辑
                  </button>
                  <button type="button" className="secondary-button" onClick={() => void handleDelete(template.id)}>
                    删除
                  </button>
                  <button type="button" className="secondary-button" onClick={() => void handleImport(template.id, "openclaw")}>
                    导入到 OpenClaw
                  </button>
                  <button type="button" className="secondary-button" onClick={() => void handleImport(template.id, "gateway")}>
                    导入到 Gateway
                  </button>
                  <button type="button" className="secondary-button" onClick={() => void handleImport(template.id, "media")}>
                    导入到 Media
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

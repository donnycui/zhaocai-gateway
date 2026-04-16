import { useEffect, useState } from "react";

import { api, type MediaProvider } from "../lib/api";
import MediaTemplatesPage from "./MediaTemplatesPage";

export default function MediaProvidersPage() {
  const [providers, setProviders] = useState<MediaProvider[]>([]);
  const [message, setMessage] = useState("");
  const [editingProviderId, setEditingProviderId] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: "",
    base_url: "",
    auth_type: "bearer",
    api_key: "",
    notes: "",
  });

  async function loadProviders() {
    setProviders(await api.getMediaProviders());
  }

  useEffect(() => {
    void loadProviders();
  }, []);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (editingProviderId == null) {
      await api.createMediaProvider(form);
      setMessage("Media provider 已创建。");
    } else {
      await api.updateMediaProvider(editingProviderId, { ...form, enabled: true });
      setEditingProviderId(null);
      setMessage("Media provider 已更新。");
    }
    setForm({
      name: "",
      base_url: "",
      auth_type: "bearer",
      api_key: "",
      notes: "",
    });
    await loadProviders();
  }

  async function handleEdit(providerId: number) {
    const provider = await api.getMediaProvider(providerId);
    setEditingProviderId(providerId);
    setForm({
      name: provider.name,
      base_url: provider.base_url,
      auth_type: provider.auth_type,
      api_key: provider.api_key_encrypted,
      notes: provider.notes,
    });
    setMessage("");
  }

  async function handleDelete(providerId: number) {
    const confirmed = window.confirm("确认删除这个 Media provider 吗？");
    if (!confirmed) return;
    await api.deleteMediaProvider(providerId);
    if (editingProviderId === providerId) {
      setEditingProviderId(null);
      setForm({
        name: "",
        base_url: "",
        auth_type: "bearer",
        api_key: "",
        notes: "",
      });
    }
    setMessage("Media provider 已删除。");
    await loadProviders();
  }

  function handleCancelEdit() {
    setEditingProviderId(null);
    setForm({
      name: "",
      base_url: "",
      auth_type: "bearer",
      api_key: "",
      notes: "",
    });
  }

  return (
    <section className="page">
      <form className="panel form-panel" onSubmit={handleCreate}>
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>Media Providers</h3>
          <p>这里管理 `zhaocai-media` 使用的独立上游账号，不与 OpenClaw 的普通文本模型主线混用。</p>
        </div>
        <div className="editor-grid">
          <label>
            <span>名称</span>
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
        </div>
        <label>
          <span>备注</span>
          <textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} />
        </label>
        <div className="topbar-actions">
          <button type="submit">{editingProviderId == null ? "新增 Media Provider" : "保存修改"}</button>
          {editingProviderId != null ? (
            <button type="button" className="secondary-button" onClick={handleCancelEdit}>
              取消编辑
            </button>
          ) : null}
        </div>
        {message ? <p className="inline-message">{message}</p> : null}
      </form>

      <div className="panel placeholder-panel">
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>当前 Media Providers</h3>
          <p>这些 provider 只服务于媒体模板和 catalog，不会进入 OpenClaw 模块。</p>
        </div>
        {providers.length === 0 ? (
          <div className="empty-state">还没有任何 Media provider。</div>
        ) : (
          <div className="placeholder-grid">
            {providers.map((provider) => (
              <article key={provider.id} className="placeholder-card">
                <strong>{provider.name}</strong>
                <span>{provider.base_url}</span>
                <span>鉴权：{provider.auth_type}</span>
                {provider.notes ? <span>备注：{provider.notes}</span> : null}
                <div className="topbar-actions">
                  <button type="button" className="secondary-button" onClick={() => void handleEdit(provider.id)}>
                    查看/编辑
                  </button>
                  <button type="button" className="secondary-button" onClick={() => void handleDelete(provider.id)}>
                    删除
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      <MediaTemplatesPage />
    </section>
  );
}

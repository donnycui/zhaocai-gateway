import { useEffect, useState } from "react";

import { api, type MediaProvider } from "../lib/api";
import MediaTemplatesPage from "./MediaTemplatesPage";

export default function MediaProvidersPage() {
  const [providers, setProviders] = useState<MediaProvider[]>([]);
  const [message, setMessage] = useState("");
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
    await api.createMediaProvider(form);
    setForm({
      name: "",
      base_url: "",
      auth_type: "bearer",
      api_key: "",
      notes: "",
    });
    setMessage("Media provider 已创建。");
    await loadProviders();
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
          <button type="submit">新增 Media Provider</button>
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
              </article>
            ))}
          </div>
        )}
      </div>

      <MediaTemplatesPage />
    </section>
  );
}

import { useEffect, useState } from "react";

import { api, type GatewayClientKey } from "../lib/api";

export default function GatewayClientKeysPage() {
  const [clientKeys, setClientKeys] = useState<GatewayClientKey[]>([]);
  const [message, setMessage] = useState("");
  const [latestRawKey, setLatestRawKey] = useState("");
  const [form, setForm] = useState({
    name: "",
    api_key: "",
    notes: "",
  });

  async function loadClientKeys() {
    setClientKeys(await api.getGatewayClientKeys());
  }

  useEffect(() => {
    void loadClientKeys();
  }, []);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setMessage("");
    const clientKey = await api.createGatewayClientKey(form);
    setLatestRawKey(clientKey.raw_api_key ?? "");
    setForm({
      name: "",
      api_key: "",
      notes: "",
    });
    setMessage("Gateway client key 已创建。请妥善保存下方显示的原始 key。");
    await loadClientKeys();
  }

  async function handleToggle(clientKey: GatewayClientKey) {
    await api.updateGatewayClientKey(clientKey.id, {
      enabled: !clientKey.enabled,
      notes: clientKey.notes,
    });
    setMessage(clientKey.enabled ? "Gateway client key 已停用。" : "Gateway client key 已启用。");
    await loadClientKeys();
  }

  return (
    <div className="panel placeholder-panel">
      <div className="panel-header" style={{ marginBottom: 0 }}>
        <h3>Gateway Client Keys</h3>
        <p>这里给外部项目发统一接入 key。第一阶段先支持最简单的单 key 或少量 key 模式，让项目通过一个 `baseUrl + apiKey` 访问网关。</p>
      </div>

      <form className="form-panel" onSubmit={handleCreate}>
        <div className="editor-grid">
          <label>
            <span>名称</span>
            <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Content-IP-Strategy" />
          </label>
          <label>
            <span>自定义 API Key（可留空自动生成）</span>
            <input value={form.api_key} onChange={(event) => setForm((current) => ({ ...current, api_key: event.target.value }))} placeholder="留空时自动生成 zgk_..." />
          </label>
        </div>
        <label>
          <span>备注</span>
          <textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} />
        </label>
        <div className="topbar-actions">
          <button type="submit">新增 Client Key</button>
        </div>
      </form>

      {message ? <p className="inline-message">{message}</p> : null}
      {latestRawKey ? (
        <div className="panel">
          <div className="panel-header" style={{ marginBottom: 0 }}>
            <h3>最新生成的原始 Key</h3>
            <p>这个值只会在创建后返回一次。后续列表里只保留哈希和 hint。</p>
          </div>
          <pre className="code-block">{latestRawKey}</pre>
        </div>
      ) : null}

      <div className="placeholder-grid">
        {clientKeys.length === 0 ? (
          <div className="empty-state">还没有任何 Gateway client key。</div>
        ) : (
          clientKeys.map((clientKey) => (
            <article key={clientKey.id} className="placeholder-card">
              <strong>{clientKey.name}</strong>
              <span>Key Hint：{clientKey.key_hint}</span>
              <span>状态：{clientKey.enabled ? "启用中" : "已停用"}</span>
              <span>最近使用：{clientKey.last_used_at ?? "尚未使用"}</span>
              {clientKey.notes ? <span>备注：{clientKey.notes}</span> : null}
              <div className="topbar-actions">
                <button type="button" className="secondary-button" onClick={() => void handleToggle(clientKey)}>
                  {clientKey.enabled ? "停用" : "启用"}
                </button>
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
}

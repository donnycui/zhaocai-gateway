import { useState } from "react";

import { api, type MediaProvider, type MediaTemplate } from "../lib/api";

interface MediaTemplateEditorPageProps {
  providers: MediaProvider[];
  onCreated: (template: MediaTemplate) => Promise<void>;
}

export default function MediaTemplateEditorPage({
  providers,
  onCreated,
}: MediaTemplateEditorPageProps) {
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    provider_id: "",
    model_key: "",
    name: "",
    capability: "image",
    template_type: "openai_images",
    upstream_model: "",
    ui_group: "",
    ui_label: "",
    ui_description: "",
    ui_badge: "",
    ui_order: "0",
    input_schema_json: "{\n  \"prompt\": { \"type\": \"string\", \"required\": true }\n}",
    request_template_json: "{\n  \"prompt\": \"{{prompt}}\"\n}",
    response_mapping_json: "{\n  \"output\": \"$.data\"\n}",
    defaults_json: "{\n  \"ratio\": \"1:1\"\n}",
  });

  function parseJsonField(value: string) {
    try {
      const parsed = JSON.parse(value) as Record<string, unknown>;
      return { ok: true as const, value: parsed };
    } catch (error) {
      return {
        ok: false as const,
        message: error instanceof Error ? error.message : "JSON parse failed",
      };
    }
  }

  async function handleValidate() {
    const inputSchema = parseJsonField(form.input_schema_json);
    const requestTemplate = parseJsonField(form.request_template_json);
    const responseMapping = parseJsonField(form.response_mapping_json);
    const defaults = parseJsonField(form.defaults_json);
    if (!inputSchema.ok || !requestTemplate.ok || !responseMapping.ok || !defaults.ok) {
      setMessage("存在 JSON 字段格式错误，请先修正后再验证。");
      return;
    }
    const result = await api.validateMediaTemplate({
      provider_id: Number(form.provider_id),
      model_key: form.model_key,
      name: form.name,
      capability: form.capability,
      template_type: form.template_type,
      upstream_model: form.upstream_model,
      ui_group: form.ui_group,
      ui_label: form.ui_label,
      ui_description: form.ui_description,
      ui_badge: form.ui_badge,
      ui_order: Number(form.ui_order || "0"),
      input_schema_json: inputSchema.value,
      request_template_json: requestTemplate.value,
      response_mapping_json: responseMapping.value,
      defaults_json: defaults.value,
      enabled: true,
    });
    setMessage(result.ok ? "Media template 验证通过。" : `验证失败：${result.errors.join(" / ")}`);
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    const inputSchema = parseJsonField(form.input_schema_json);
    const requestTemplate = parseJsonField(form.request_template_json);
    const responseMapping = parseJsonField(form.response_mapping_json);
    const defaults = parseJsonField(form.defaults_json);
    if (!inputSchema.ok || !requestTemplate.ok || !responseMapping.ok || !defaults.ok) {
      setMessage("存在 JSON 字段格式错误，无法创建模板。");
      return;
    }
    const template = await api.createMediaTemplate({
      provider_id: Number(form.provider_id),
      model_key: form.model_key,
      name: form.name,
      capability: form.capability,
      template_type: form.template_type,
      upstream_model: form.upstream_model,
      ui_group: form.ui_group,
      ui_label: form.ui_label,
      ui_description: form.ui_description,
      ui_badge: form.ui_badge,
      ui_order: Number(form.ui_order || "0"),
      input_schema_json: inputSchema.value,
      request_template_json: requestTemplate.value,
      response_mapping_json: responseMapping.value,
      defaults_json: defaults.value,
      enabled: true,
    });
    setMessage("Media template 已创建。");
    await onCreated(template);
  }

  return (
    <form className="panel form-panel" onSubmit={handleCreate}>
      <div className="panel-header" style={{ marginBottom: 0 }}>
        <h3>新增 Media Template</h3>
        <p>用声明式 JSON 描述媒体工作流。第一阶段先支持最小可用模板录入、验证和 catalog 导出。</p>
      </div>
      <div className="editor-grid">
        <label>
          <span>Provider</span>
          <select value={form.provider_id} onChange={(event) => setForm((current) => ({ ...current, provider_id: event.target.value }))}>
            <option value="">请选择 provider</option>
            {providers.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Model Key</span>
          <input value={form.model_key} onChange={(event) => setForm((current) => ({ ...current, model_key: event.target.value }))} placeholder="image/bizyair/default" />
        </label>
        <label>
          <span>名称</span>
          <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
        </label>
        <label>
          <span>能力</span>
          <select value={form.capability} onChange={(event) => setForm((current) => ({ ...current, capability: event.target.value }))}>
            <option value="image">image</option>
            <option value="image_edit">image_edit</option>
            <option value="image_to_video">image_to_video</option>
            <option value="tts">tts</option>
          </select>
        </label>
        <label>
          <span>Template Type</span>
          <select value={form.template_type} onChange={(event) => setForm((current) => ({ ...current, template_type: event.target.value }))}>
            <option value="openai_images">openai_images</option>
            <option value="gemini_generate_content">gemini_generate_content</option>
            <option value="bizyair_webapp">bizyair_webapp</option>
            <option value="siliconflow_tts">siliconflow_tts</option>
          </select>
        </label>
        <label>
          <span>Upstream Model</span>
          <input value={form.upstream_model} onChange={(event) => setForm((current) => ({ ...current, upstream_model: event.target.value }))} />
        </label>
      </div>
      <div className="editor-grid">
        <label>
          <span>UI Group</span>
          <input value={form.ui_group} onChange={(event) => setForm((current) => ({ ...current, ui_group: event.target.value }))} />
        </label>
        <label>
          <span>UI Label</span>
          <input value={form.ui_label} onChange={(event) => setForm((current) => ({ ...current, ui_label: event.target.value }))} />
        </label>
        <label>
          <span>UI Badge</span>
          <input value={form.ui_badge} onChange={(event) => setForm((current) => ({ ...current, ui_badge: event.target.value }))} />
        </label>
        <label>
          <span>UI Order</span>
          <input value={form.ui_order} onChange={(event) => setForm((current) => ({ ...current, ui_order: event.target.value }))} />
        </label>
      </div>
      <label>
        <span>UI Description</span>
        <textarea value={form.ui_description} onChange={(event) => setForm((current) => ({ ...current, ui_description: event.target.value }))} />
      </label>
      <label>
        <span>Input Schema JSON</span>
        <textarea value={form.input_schema_json} onChange={(event) => setForm((current) => ({ ...current, input_schema_json: event.target.value }))} />
      </label>
      <label>
        <span>Request Template JSON</span>
        <textarea value={form.request_template_json} onChange={(event) => setForm((current) => ({ ...current, request_template_json: event.target.value }))} />
      </label>
      <label>
        <span>Response Mapping JSON</span>
        <textarea value={form.response_mapping_json} onChange={(event) => setForm((current) => ({ ...current, response_mapping_json: event.target.value }))} />
      </label>
      <label>
        <span>Defaults JSON</span>
        <textarea value={form.defaults_json} onChange={(event) => setForm((current) => ({ ...current, defaults_json: event.target.value }))} />
      </label>
      <div className="topbar-actions">
        <button type="button" className="secondary-button" onClick={() => void handleValidate()}>
          验证模板
        </button>
        <button type="submit">创建模板</button>
      </div>
      {message ? <p className="inline-message">{message}</p> : null}
    </form>
  );
}

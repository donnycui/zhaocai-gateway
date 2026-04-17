import { useEffect, useState } from "react";

import { api, type MediaProvider, type MediaTemplate } from "../lib/api";

interface MediaTemplateEditorPageProps {
  providers: MediaProvider[];
  editingTemplate: MediaTemplate | null;
  onSaved: (template: MediaTemplate) => Promise<void>;
  onCancelEdit: () => void;
}

type BuilderFieldType = "string" | "url" | "enum" | "number" | "file[]";

interface BizyairFieldRow {
  key: string;
  variable: string;
  label: string;
  type: BuilderFieldType;
  required: boolean;
  defaultValue: string;
  optionsCsv: string;
}

interface TemplateWizardState {
  openaiImages: {
    sizeOptions: string[];
    defaultSize: string;
  };
  openaiImageEdits: {
    sizeOptions: string[];
    defaultSize: string;
    countOptions: string[];
    defaultCount: string;
  };
  openaiVideos: {
    sizeOptions: string[];
    defaultSize: string;
    secondOptions: string[];
    defaultSeconds: string;
    presetOptions: string[];
    defaultPreset: string;
  };
  gemini: {
    acceptsImageUrl: boolean;
  };
  siliconflowTts: {
    defaultVoice: string;
    defaultFormat: string;
    defaultSpeed: string;
  };
  bizyair: {
    webAppId: string;
    fields: BizyairFieldRow[];
    successPath: string;
    successEquals: string;
    resultUrlPath: string;
    errorMessagePath: string;
    costTimePath: string;
  };
}

interface TemplateJsonBundle {
  inputSchema: Record<string, unknown>;
  requestTemplate: Record<string, unknown>;
  responseMapping: Record<string, unknown>;
  defaults: Record<string, unknown>;
}

type MediaTemplateFormState = ReturnType<typeof buildEmptyForm>;

const FIELD_HINTS: Record<string, string> = {
  provider_id: "先在 Media Providers 里创建好上游账号，这里只做模板与 provider 的绑定。",
  model_key: "稳定标识，后续网站和 zhaocai-media 都应该消费这个 key，不要频繁改名。",
  name: "后台内部名称，可以更技术化，方便和真实模板/工作流一一对应。",
  capability: "定义这是图片、图片编辑、视频还是 TTS 模板。",
  template_type: "决定向导如何生成请求 JSON。BizyAir、OpenAI Images、Grok Video 都属于不同模板类型。",
  upstream_model: "真实上游模型名，会直接写进请求模板或者作为默认参数导出。",
  ui_group: "给网站和 catalog 用的分组，通常填 image / video / tts。",
  ui_label: "给前端展示的显示名称，尽量可读。",
  ui_description: "简短说明，告诉前端或运营这条模板的适用场景。",
  ui_badge: "小标签，例如 biz / grok / po，用于列表前缀。",
  ui_order: "数字越小越靠前，控制 catalog 和网站显示顺序。",
};

const DEFAULT_IMAGE_SIZES = ["1024x1024", "1024x1792", "1792x1024", "1280x720", "720x1280"];
const DEFAULT_VIDEO_SIZES = ["720x1280", "1280x720", "1024x1024", "1024x1792", "1792x1024"];
const DEFAULT_VIDEO_SECONDS = ["6", "10", "12", "16", "20"];
const DEFAULT_VIDEO_PRESETS = ["fun", "normal", "spicy", "custom"];

function buildEmptyForm() {
  return {
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
  };
}

function buildEmptyWizard(): TemplateWizardState {
  return {
    openaiImages: {
      sizeOptions: [...DEFAULT_IMAGE_SIZES],
      defaultSize: "1024x1024",
    },
    openaiImageEdits: {
      sizeOptions: [...DEFAULT_IMAGE_SIZES],
      defaultSize: "1024x1024",
      countOptions: ["1", "2"],
      defaultCount: "1",
    },
    openaiVideos: {
      sizeOptions: [...DEFAULT_VIDEO_SIZES],
      defaultSize: "720x1280",
      secondOptions: [...DEFAULT_VIDEO_SECONDS],
      defaultSeconds: "6",
      presetOptions: [...DEFAULT_VIDEO_PRESETS],
      defaultPreset: "custom",
    },
    gemini: {
      acceptsImageUrl: false,
    },
    siliconflowTts: {
      defaultVoice: "anna",
      defaultFormat: "mp3",
      defaultSpeed: "1",
    },
    bizyair: {
      webAppId: "",
      fields: [
        {
          key: "17:BizyAir_API.prompt",
          variable: "prompt",
          label: "Prompt",
          type: "string",
          required: true,
          defaultValue: "",
          optionsCsv: "",
        },
      ],
      successPath: "status",
      successEquals: "Success",
      resultUrlPath: "outputs[0].object_url",
      errorMessagePath: "outputs[0].error_msg",
      costTimePath: "cost_times.total_cost_time",
    },
  };
}

function normalizeTemplateType(templateType: string): string {
  return templateType === "custom" ? "custom" : templateType;
}

function splitCsvOptions(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function extractVariableToken(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const match = value.match(/^\{\{\s*([^}]+?)\s*\}\}$/);
  return match ? match[1].trim() : null;
}

function coerceDefaultValue(value: string, type: BuilderFieldType): string | number {
  if (type === "number") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return value;
}

function serializeJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function buildJsonFromWizard(form: MediaTemplateFormState, wizard: TemplateWizardState): TemplateJsonBundle | null {
  switch (normalizeTemplateType(form.template_type)) {
    case "openai_images": {
      return {
        inputSchema: {
          prompt: { type: "string", required: true },
          size: {
            type: "enum",
            required: true,
            options: wizard.openaiImages.sizeOptions,
          },
        },
        requestTemplate: {
          endpoint: "/images/generations",
          method: "POST",
          body: {
            model: "{{upstream_model}}",
            prompt: "{{prompt}}",
            size: "{{size}}",
          },
        },
        responseMapping: {
          result_url_path: "$.data[0].url",
          error_message_path: "$.error.message",
        },
        defaults: {
          size: wizard.openaiImages.defaultSize,
        },
      };
    }
    case "openai_images_edits": {
      return {
        inputSchema: {
          prompt: { type: "string", required: true },
          images: { type: "file[]", required: true },
          n: {
            type: "enum",
            required: true,
            options: wizard.openaiImageEdits.countOptions.map((value) => Number(value)),
          },
          size: {
            type: "enum",
            required: true,
            options: wizard.openaiImageEdits.sizeOptions,
          },
        },
        requestTemplate: {
          endpoint: "/images/edits",
          method: "POST",
          content_type: "multipart/form-data",
          form: {
            model: "{{upstream_model}}",
            prompt: "{{prompt}}",
            n: "{{n}}",
            size: "{{size}}",
          },
          files: {
            "image[]": "{{images}}",
          },
        },
        responseMapping: {
          result_url_path: "$.data[0].url",
          error_message_path: "$.error.message",
        },
        defaults: {
          n: Number(wizard.openaiImageEdits.defaultCount),
          size: wizard.openaiImageEdits.defaultSize,
        },
      };
    }
    case "openai_videos": {
      return {
        inputSchema: {
          prompt: { type: "string", required: true },
          size: {
            type: "enum",
            required: true,
            options: wizard.openaiVideos.sizeOptions,
          },
          seconds: {
            type: "enum",
            required: true,
            options: wizard.openaiVideos.secondOptions.map((value) => Number(value)),
          },
          preset: {
            type: "enum",
            required: true,
            options: wizard.openaiVideos.presetOptions,
          },
        },
        requestTemplate: {
          create: {
            endpoint: "/videos",
            method: "POST",
            body: {
              model: "{{upstream_model}}",
              prompt: "{{prompt}}",
              size: "{{size}}",
              seconds: "{{seconds}}",
              preset: "{{preset}}",
            },
          },
          poll: {
            endpoint: "/videos/{{video_id}}",
            method: "GET",
            interval_seconds: 5,
            max_attempts: 120,
          },
          content: {
            endpoint: "/videos/{{video_id}}/content",
            method: "GET",
          },
        },
        responseMapping: {
          create_video_id_path: "$.id",
          status_path: "$.status",
          completed_status_values: ["completed", "succeeded", "success"],
          failed_status_values: ["failed", "error"],
          error_message_path: "$.error.message",
          content_url_template: "/videos/{{video_id}}/content",
        },
        defaults: {
          size: wizard.openaiVideos.defaultSize,
          seconds: Number(wizard.openaiVideos.defaultSeconds),
          preset: wizard.openaiVideos.defaultPreset,
        },
      };
    }
    case "gemini_generate_content": {
      const parts: Array<Record<string, unknown>> = [{ text: "{{prompt}}" }];
      if (wizard.gemini.acceptsImageUrl) {
        parts.push({
          fileData: {
            fileUri: "{{image_url}}",
          },
        });
      }
      const inputSchema: Record<string, unknown> = {
        prompt: { type: "string", required: true },
      };
      if (wizard.gemini.acceptsImageUrl) {
        inputSchema.image_url = { type: "url", required: false };
      }
      return {
        inputSchema,
        requestTemplate: {
          endpoint: "/models/{{upstream_model}}:generateContent",
          method: "POST",
          body: {
            contents: [{ parts }],
          },
        },
        responseMapping: {
          inline_data_path: "$.candidates[0].content.parts[0].inlineData",
          mime_type_path: "$.candidates[0].content.parts[0].inlineData.mimeType",
          error_message_path: "$.error.message",
        },
        defaults: {},
      };
    }
    case "siliconflow_tts": {
      return {
        inputSchema: {
          text: { type: "string", required: true },
          voice: { type: "string", required: true },
          format: { type: "string", required: true },
          speed: { type: "number", required: true },
        },
        requestTemplate: {
          endpoint: "/audio/speech",
          method: "POST",
          body: {
            model: "{{upstream_model}}",
            input: "{{text}}",
            voice: "{{voice}}",
            response_format: "{{format}}",
            speed: "{{speed}}",
          },
        },
        responseMapping: {
          result_url_path: "$.data.url",
          audio_base64_path: "$.data.audio",
          error_message_path: "$.error.message",
        },
        defaults: {
          voice: wizard.siliconflowTts.defaultVoice,
          format: wizard.siliconflowTts.defaultFormat,
          speed: Number(wizard.siliconflowTts.defaultSpeed),
        },
      };
    }
    case "bizyair_webapp": {
      const inputSchema: Record<string, unknown> = {};
      const inputValues: Record<string, unknown> = {};
      const defaults: Record<string, unknown> = {};

      wizard.bizyair.fields.forEach((field) => {
        if (!field.variable || !field.key) return;
        const schema: Record<string, unknown> = {
          type: field.type,
          required: field.required,
        };
        const options = field.type === "enum" ? splitCsvOptions(field.optionsCsv) : [];
        if (options.length > 0) {
          schema.options = options;
        }
        if (field.label.trim()) {
          schema.label = field.label.trim();
        }
        inputSchema[field.variable] = schema;
        inputValues[field.key] = `{{${field.variable}}}`;
        if (field.defaultValue.trim()) {
          defaults[field.variable] = coerceDefaultValue(field.defaultValue.trim(), field.type);
        }
      });

      const responseMapping: Record<string, unknown> = {
        success_path: wizard.bizyair.successPath,
        success_equals: wizard.bizyair.successEquals,
        result_url_path: wizard.bizyair.resultUrlPath,
        error_message_path: wizard.bizyair.errorMessagePath,
      };
      if (wizard.bizyair.costTimePath.trim()) {
        responseMapping.cost_time_path = wizard.bizyair.costTimePath.trim();
      }

      return {
        inputSchema,
        requestTemplate: {
          endpoint: "/w/v1/webapp/task/openapi/create",
          method: "POST",
          body: {
            web_app_id: Number(wizard.bizyair.webAppId || "0"),
            suppress_preview_output: false,
            input_values: inputValues,
          },
        },
        responseMapping,
        defaults,
      };
    }
    default:
      return null;
  }
}

function inferWizardFromTemplate(template: MediaTemplate): TemplateWizardState {
  const wizard = buildEmptyWizard();
  const inputSchema = template.input_schema_json ?? {};
  const requestTemplate = template.request_template_json ?? {};
  const responseMapping = template.response_mapping_json ?? {};
  const defaults = template.defaults_json ?? {};

  switch (template.template_type) {
    case "openai_images": {
      const sizeField = inputSchema.size as { options?: string[] } | undefined;
      wizard.openaiImages.sizeOptions = Array.isArray(sizeField?.options) && sizeField.options.length > 0 ? [...sizeField.options] : [...DEFAULT_IMAGE_SIZES];
      wizard.openaiImages.defaultSize = typeof defaults.size === "string" ? defaults.size : wizard.openaiImages.defaultSize;
      break;
    }
    case "openai_images_edits": {
      const sizeField = inputSchema.size as { options?: string[] } | undefined;
      const countField = inputSchema.n as { options?: Array<number | string> } | undefined;
      wizard.openaiImageEdits.sizeOptions =
        Array.isArray(sizeField?.options) && sizeField.options.length > 0 ? [...sizeField.options] : [...DEFAULT_IMAGE_SIZES];
      wizard.openaiImageEdits.defaultSize =
        typeof defaults.size === "string" ? defaults.size : wizard.openaiImageEdits.defaultSize;
      wizard.openaiImageEdits.countOptions =
        Array.isArray(countField?.options) && countField.options.length > 0
          ? countField.options.map((value) => String(value))
          : ["1", "2"];
      wizard.openaiImageEdits.defaultCount =
        typeof defaults.n === "number" || typeof defaults.n === "string"
          ? String(defaults.n)
          : wizard.openaiImageEdits.defaultCount;
      break;
    }
    case "openai_videos": {
      const sizeField = inputSchema.size as { options?: string[] } | undefined;
      const secondsField = inputSchema.seconds as { options?: Array<number | string> } | undefined;
      const presetField = inputSchema.preset as { options?: string[] } | undefined;
      wizard.openaiVideos.sizeOptions =
        Array.isArray(sizeField?.options) && sizeField.options.length > 0 ? [...sizeField.options] : [...DEFAULT_VIDEO_SIZES];
      wizard.openaiVideos.secondOptions =
        Array.isArray(secondsField?.options) && secondsField.options.length > 0
          ? secondsField.options.map((value) => String(value))
          : [...DEFAULT_VIDEO_SECONDS];
      wizard.openaiVideos.presetOptions =
        Array.isArray(presetField?.options) && presetField.options.length > 0 ? [...presetField.options] : [...DEFAULT_VIDEO_PRESETS];
      wizard.openaiVideos.defaultSize = typeof defaults.size === "string" ? defaults.size : wizard.openaiVideos.defaultSize;
      wizard.openaiVideos.defaultSeconds =
        typeof defaults.seconds === "number" || typeof defaults.seconds === "string"
          ? String(defaults.seconds)
          : wizard.openaiVideos.defaultSeconds;
      wizard.openaiVideos.defaultPreset =
        typeof defaults.preset === "string" ? defaults.preset : wizard.openaiVideos.defaultPreset;
      break;
    }
    case "gemini_generate_content": {
      const contents = requestTemplate.contents as Array<{ parts?: Array<Record<string, unknown>> }> | undefined;
      wizard.gemini.acceptsImageUrl = Boolean(
        contents?.some((item) =>
          Array.isArray(item.parts) && item.parts.some((part) => "fileData" in part),
        ),
      );
      break;
    }
    case "siliconflow_tts": {
      wizard.siliconflowTts.defaultVoice = typeof defaults.voice === "string" ? defaults.voice : wizard.siliconflowTts.defaultVoice;
      wizard.siliconflowTts.defaultFormat = typeof defaults.format === "string" ? defaults.format : wizard.siliconflowTts.defaultFormat;
      wizard.siliconflowTts.defaultSpeed =
        typeof defaults.speed === "number" || typeof defaults.speed === "string"
          ? String(defaults.speed)
          : wizard.siliconflowTts.defaultSpeed;
      break;
    }
    case "bizyair_webapp": {
      const body = requestTemplate.body as Record<string, unknown> | undefined;
      wizard.bizyair.webAppId =
        typeof body?.web_app_id === "number" || typeof body?.web_app_id === "string" ? String(body.web_app_id) : "";
      const inputValues = (body?.input_values as Record<string, unknown> | undefined) ?? {};
      const rows: BizyairFieldRow[] = [];
      Object.entries(inputValues).forEach(([key, value]) => {
        const variable = extractVariableToken(value);
        if (!variable) return;
        const schema = (inputSchema[variable] as Record<string, unknown> | undefined) ?? {};
        rows.push({
          key,
          variable,
          label: String(schema.label ?? variable),
          type: ((schema.type as BuilderFieldType | undefined) ?? "string"),
          required: Boolean(schema.required),
          defaultValue:
            defaults[variable] == null ? "" : String(defaults[variable]),
          optionsCsv: Array.isArray(schema.options) ? (schema.options as Array<string | number>).join(", ") : "",
        });
      });
      if (rows.length > 0) {
        wizard.bizyair.fields = rows;
      }
      wizard.bizyair.successPath = String(responseMapping.success_path ?? wizard.bizyair.successPath);
      wizard.bizyair.successEquals = String(responseMapping.success_equals ?? wizard.bizyair.successEquals);
      wizard.bizyair.resultUrlPath = String(responseMapping.result_url_path ?? wizard.bizyair.resultUrlPath);
      wizard.bizyair.errorMessagePath = String(responseMapping.error_message_path ?? wizard.bizyair.errorMessagePath);
      wizard.bizyair.costTimePath = String(responseMapping.cost_time_path ?? wizard.bizyair.costTimePath);
      break;
    }
    default:
      break;
  }

  return wizard;
}

function buildReadonlyJsonFields(bundle: TemplateJsonBundle) {
  return {
    input_schema_json: serializeJson(bundle.inputSchema),
    request_template_json: serializeJson(bundle.requestTemplate),
    response_mapping_json: serializeJson(bundle.responseMapping),
    defaults_json: serializeJson(bundle.defaults),
  };
}

function TemplateField({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label>
      <span>{label}</span>
      {children}
      {hint ? <small className="field-hint">{hint}</small> : null}
    </label>
  );
}

export default function MediaTemplateEditorPage({
  providers,
  editingTemplate,
  onSaved,
  onCancelEdit,
}: MediaTemplateEditorPageProps) {
  const [message, setMessage] = useState("");
  const [form, setForm] = useState(buildEmptyForm);
  const [wizard, setWizard] = useState<TemplateWizardState>(buildEmptyWizard);
  const [advancedMode, setAdvancedMode] = useState(false);

  useEffect(() => {
    if (!editingTemplate) {
      setForm(buildEmptyForm());
      setWizard(buildEmptyWizard());
      setAdvancedMode(false);
      return;
    }

    setForm({
      provider_id: String(editingTemplate.provider_id),
      model_key: editingTemplate.model_key,
      name: editingTemplate.name,
      capability: editingTemplate.capability,
      template_type: editingTemplate.template_type,
      upstream_model: editingTemplate.upstream_model,
      ui_group: editingTemplate.ui_group,
      ui_label: editingTemplate.ui_label,
      ui_description: editingTemplate.ui_description,
      ui_badge: editingTemplate.ui_badge,
      ui_order: String(editingTemplate.ui_order),
      input_schema_json: serializeJson(editingTemplate.input_schema_json),
      request_template_json: serializeJson(editingTemplate.request_template_json),
      response_mapping_json: serializeJson(editingTemplate.response_mapping_json),
      defaults_json: serializeJson(editingTemplate.defaults_json),
    });
    setWizard(inferWizardFromTemplate(editingTemplate));
    setAdvancedMode(editingTemplate.template_type === "custom");
  }, [editingTemplate]);

  useEffect(() => {
    if (advancedMode || normalizeTemplateType(form.template_type) === "custom") {
      return;
    }
    const generated = buildJsonFromWizard(form, wizard);
    if (!generated) return;
    const nextJson = buildReadonlyJsonFields(generated);
    setForm((current) => {
      if (
        current.input_schema_json === nextJson.input_schema_json &&
        current.request_template_json === nextJson.request_template_json &&
        current.response_mapping_json === nextJson.response_mapping_json &&
        current.defaults_json === nextJson.defaults_json
      ) {
        return current;
      }
      return {
        ...current,
        ...nextJson,
      };
    });
  }, [advancedMode, form.template_type, form.upstream_model, wizard]);

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

  function updateBizyairField(index: number, patch: Partial<BizyairFieldRow>) {
    setWizard((current) => ({
      ...current,
      bizyair: {
        ...current.bizyair,
        fields: current.bizyair.fields.map((field, fieldIndex) =>
          fieldIndex === index ? { ...field, ...patch } : field,
        ),
      },
    }));
  }

  function addBizyairField() {
    setWizard((current) => ({
      ...current,
      bizyair: {
        ...current.bizyair,
        fields: [
          ...current.bizyair.fields,
          {
            key: "",
            variable: "",
            label: "",
            type: "string",
            required: true,
            defaultValue: "",
            optionsCsv: "",
          },
        ],
      },
    }));
  }

  function removeBizyairField(index: number) {
    setWizard((current) => ({
      ...current,
      bizyair: {
        ...current.bizyair,
        fields: current.bizyair.fields.filter((_, fieldIndex) => fieldIndex !== index),
      },
    }));
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

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const inputSchema = parseJsonField(form.input_schema_json);
    const requestTemplate = parseJsonField(form.request_template_json);
    const responseMapping = parseJsonField(form.response_mapping_json);
    const defaults = parseJsonField(form.defaults_json);
    if (!inputSchema.ok || !requestTemplate.ok || !responseMapping.ok || !defaults.ok) {
      setMessage("存在 JSON 字段格式错误，无法保存模板。");
      return;
    }
    const payload = {
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
    };
    const template =
      editingTemplate == null
        ? await api.createMediaTemplate(payload)
        : await api.updateMediaTemplate(editingTemplate.id, payload);
    setMessage(editingTemplate == null ? "Media template 已创建。" : "Media template 已更新。");
    await onSaved(template);
  }

  function renderOpenAiImageBuilder() {
    return (
      <div className="builder-card">
        <div className="builder-card-header">
          <strong>OpenAI Images 向导</strong>
          <span>固定生成 `/images/generations` 的请求模板。</span>
        </div>
        <div className="builder-grid">
          <TemplateField label="可用尺寸" hint="勾选后会自动写到 `size` 的 enum 选项。">
            <div className="choice-chip-group">
              {DEFAULT_IMAGE_SIZES.map((size) => {
                const selected = wizard.openaiImages.sizeOptions.includes(size);
                return (
                  <button
                    key={size}
                    type="button"
                    className={`choice-chip ${selected ? "selected" : ""}`}
                    onClick={() =>
                      setWizard((current) => ({
                        ...current,
                        openaiImages: {
                          ...current.openaiImages,
                          sizeOptions: selected
                            ? current.openaiImages.sizeOptions.filter((item) => item !== size)
                            : [...current.openaiImages.sizeOptions, size],
                        },
                      }))
                    }
                  >
                    {size}
                  </button>
                );
              })}
            </div>
          </TemplateField>
          <TemplateField label="默认尺寸" hint="默认值会写入 `defaults_json.size`。">
            <select
              value={wizard.openaiImages.defaultSize}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  openaiImages: {
                    ...current.openaiImages,
                    defaultSize: event.target.value,
                  },
                }))
              }
            >
              {wizard.openaiImages.sizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </TemplateField>
        </div>
      </div>
    );
  }

  function renderOpenAiEditBuilder() {
    return (
      <div className="builder-card">
        <div className="builder-card-header">
          <strong>OpenAI Images Edit 向导</strong>
          <span>会自动生成 multipart/form-data 的 `/images/edits` 模板。</span>
        </div>
        <div className="builder-grid">
          <TemplateField label="可用尺寸" hint="图片编辑与文生图共用 `size` 选项。">
            <div className="choice-chip-group">
              {DEFAULT_IMAGE_SIZES.map((size) => {
                const selected = wizard.openaiImageEdits.sizeOptions.includes(size);
                return (
                  <button
                    key={size}
                    type="button"
                    className={`choice-chip ${selected ? "selected" : ""}`}
                    onClick={() =>
                      setWizard((current) => ({
                        ...current,
                        openaiImageEdits: {
                          ...current.openaiImageEdits,
                          sizeOptions: selected
                            ? current.openaiImageEdits.sizeOptions.filter((item) => item !== size)
                            : [...current.openaiImageEdits.sizeOptions, size],
                        },
                      }))
                    }
                  >
                    {size}
                  </button>
                );
              })}
            </div>
          </TemplateField>
          <TemplateField label="默认尺寸" hint="默认写入 `defaults_json.size`。">
            <select
              value={wizard.openaiImageEdits.defaultSize}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  openaiImageEdits: {
                    ...current.openaiImageEdits,
                    defaultSize: event.target.value,
                  },
                }))
              }
            >
              {wizard.openaiImageEdits.sizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </TemplateField>
          <TemplateField label="允许的 n 值" hint="自动生成 `n` 的 enum。">
            <div className="choice-chip-group">
              {["1", "2"].map((value) => {
                const selected = wizard.openaiImageEdits.countOptions.includes(value);
                return (
                  <button
                    key={value}
                    type="button"
                    className={`choice-chip ${selected ? "selected" : ""}`}
                    onClick={() =>
                      setWizard((current) => ({
                        ...current,
                        openaiImageEdits: {
                          ...current.openaiImageEdits,
                          countOptions: selected
                            ? current.openaiImageEdits.countOptions.filter((item) => item !== value)
                            : [...current.openaiImageEdits.countOptions, value],
                        },
                      }))
                    }
                  >
                    {value}
                  </button>
                );
              })}
            </div>
          </TemplateField>
          <TemplateField label="默认 n" hint="默认写入 `defaults_json.n`。">
            <select
              value={wizard.openaiImageEdits.defaultCount}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  openaiImageEdits: {
                    ...current.openaiImageEdits,
                    defaultCount: event.target.value,
                  },
                }))
              }
            >
              {wizard.openaiImageEdits.countOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </TemplateField>
        </div>
      </div>
    );
  }

  function renderOpenAiVideoBuilder() {
    return (
      <div className="builder-card">
        <div className="builder-card-header">
          <strong>OpenAI Video 向导</strong>
          <span>用于 create -&gt; poll -&gt; content 这类异步视频任务模板。</span>
        </div>
        <div className="builder-grid">
          <TemplateField label="尺寸选项" hint="自动提取到 catalog 的 ratios / resolutions。">
            <div className="choice-chip-group">
              {DEFAULT_VIDEO_SIZES.map((size) => {
                const selected = wizard.openaiVideos.sizeOptions.includes(size);
                return (
                  <button
                    key={size}
                    type="button"
                    className={`choice-chip ${selected ? "selected" : ""}`}
                    onClick={() =>
                      setWizard((current) => ({
                        ...current,
                        openaiVideos: {
                          ...current.openaiVideos,
                          sizeOptions: selected
                            ? current.openaiVideos.sizeOptions.filter((item) => item !== size)
                            : [...current.openaiVideos.sizeOptions, size],
                        },
                      }))
                    }
                  >
                    {size}
                  </button>
                );
              })}
            </div>
          </TemplateField>
          <TemplateField label="默认尺寸" hint="默认写入 `defaults_json.size`。">
            <select
              value={wizard.openaiVideos.defaultSize}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  openaiVideos: {
                    ...current.openaiVideos,
                    defaultSize: event.target.value,
                  },
                }))
              }
            >
              {wizard.openaiVideos.sizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </TemplateField>
          <TemplateField label="秒数选项" hint="对应 `seconds` 的 enum。">
            <div className="choice-chip-group">
              {DEFAULT_VIDEO_SECONDS.map((seconds) => {
                const selected = wizard.openaiVideos.secondOptions.includes(seconds);
                return (
                  <button
                    key={seconds}
                    type="button"
                    className={`choice-chip ${selected ? "selected" : ""}`}
                    onClick={() =>
                      setWizard((current) => ({
                        ...current,
                        openaiVideos: {
                          ...current.openaiVideos,
                          secondOptions: selected
                            ? current.openaiVideos.secondOptions.filter((item) => item !== seconds)
                            : [...current.openaiVideos.secondOptions, seconds],
                        },
                      }))
                    }
                  >
                    {seconds}s
                  </button>
                );
              })}
            </div>
          </TemplateField>
          <TemplateField label="默认秒数" hint="默认写入 `defaults_json.seconds`。">
            <select
              value={wizard.openaiVideos.defaultSeconds}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  openaiVideos: {
                    ...current.openaiVideos,
                    defaultSeconds: event.target.value,
                  },
                }))
              }
            >
              {wizard.openaiVideos.secondOptions.map((seconds) => (
                <option key={seconds} value={seconds}>
                  {seconds}s
                </option>
              ))}
            </select>
          </TemplateField>
          <TemplateField label="Preset 选项" hint="用于风格模式、预设模式等场景。">
            <div className="choice-chip-group">
              {DEFAULT_VIDEO_PRESETS.map((preset) => {
                const selected = wizard.openaiVideos.presetOptions.includes(preset);
                return (
                  <button
                    key={preset}
                    type="button"
                    className={`choice-chip ${selected ? "selected" : ""}`}
                    onClick={() =>
                      setWizard((current) => ({
                        ...current,
                        openaiVideos: {
                          ...current.openaiVideos,
                          presetOptions: selected
                            ? current.openaiVideos.presetOptions.filter((item) => item !== preset)
                            : [...current.openaiVideos.presetOptions, preset],
                        },
                      }))
                    }
                  >
                    {preset}
                  </button>
                );
              })}
            </div>
          </TemplateField>
          <TemplateField label="默认 Preset" hint="默认写入 `defaults_json.preset`。">
            <select
              value={wizard.openaiVideos.defaultPreset}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  openaiVideos: {
                    ...current.openaiVideos,
                    defaultPreset: event.target.value,
                  },
                }))
              }
            >
              {wizard.openaiVideos.presetOptions.map((preset) => (
                <option key={preset} value={preset}>
                  {preset}
                </option>
              ))}
            </select>
          </TemplateField>
        </div>
      </div>
    );
  }

  function renderGeminiBuilder() {
    return (
      <div className="builder-card">
        <div className="builder-card-header">
          <strong>Gemini Generate Content 向导</strong>
          <span>按 `contents[].parts[]` 自动生成请求模板。</span>
        </div>
        <div className="checkbox-row">
          <input
            id="gemini-image-url"
            type="checkbox"
            checked={wizard.gemini.acceptsImageUrl}
            onChange={(event) =>
              setWizard((current) => ({
                ...current,
                gemini: { acceptsImageUrl: event.target.checked },
              }))
            }
          />
          <label htmlFor="gemini-image-url">允许输入 image_url，多 part 结构里会追加 fileData</label>
        </div>
      </div>
    );
  }

  function renderTtsBuilder() {
    return (
      <div className="builder-card">
        <div className="builder-card-header">
          <strong>SiliconFlow TTS 向导</strong>
          <span>自动生成语音请求模板和默认音色配置。</span>
        </div>
        <div className="builder-grid">
          <TemplateField label="默认音色">
            <input
              value={wizard.siliconflowTts.defaultVoice}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  siliconflowTts: {
                    ...current.siliconflowTts,
                    defaultVoice: event.target.value,
                  },
                }))
              }
            />
          </TemplateField>
          <TemplateField label="默认格式">
            <input
              value={wizard.siliconflowTts.defaultFormat}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  siliconflowTts: {
                    ...current.siliconflowTts,
                    defaultFormat: event.target.value,
                  },
                }))
              }
            />
          </TemplateField>
          <TemplateField label="默认语速">
            <input
              value={wizard.siliconflowTts.defaultSpeed}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  siliconflowTts: {
                    ...current.siliconflowTts,
                    defaultSpeed: event.target.value,
                  },
                }))
              }
            />
          </TemplateField>
        </div>
      </div>
    );
  }

  function renderBizyairBuilder() {
    return (
      <div className="builder-card">
        <div className="builder-card-header">
          <strong>BizyAir WebApp 向导</strong>
          <span>通过 `web_app_id + input_values` 生成声明式模板，适合 Seedance / Veo / NanoBanana 这类工作流。</span>
        </div>
        <div className="builder-grid">
          <TemplateField label="Web App ID" hint="直接填写 BizyAir 工作流的 `web_app_id`。">
            <input
              value={wizard.bizyair.webAppId}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  bizyair: {
                    ...current.bizyair,
                    webAppId: event.target.value,
                  },
                }))
              }
            />
          </TemplateField>
          <TemplateField label="成功路径" hint="通常是 `status`。">
            <input
              value={wizard.bizyair.successPath}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  bizyair: {
                    ...current.bizyair,
                    successPath: event.target.value,
                  },
                }))
              }
            />
          </TemplateField>
          <TemplateField label="成功值" hint="通常是 `Success`。">
            <input
              value={wizard.bizyair.successEquals}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  bizyair: {
                    ...current.bizyair,
                    successEquals: event.target.value,
                  },
                }))
              }
            />
          </TemplateField>
          <TemplateField label="结果 URL 路径" hint="通常是 `outputs[0].object_url`。">
            <input
              value={wizard.bizyair.resultUrlPath}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  bizyair: {
                    ...current.bizyair,
                    resultUrlPath: event.target.value,
                  },
                }))
              }
            />
          </TemplateField>
          <TemplateField label="错误信息路径">
            <input
              value={wizard.bizyair.errorMessagePath}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  bizyair: {
                    ...current.bizyair,
                    errorMessagePath: event.target.value,
                  },
                }))
              }
            />
          </TemplateField>
          <TemplateField label="耗时路径" hint="可选，不需要时可以留空。">
            <input
              value={wizard.bizyair.costTimePath}
              onChange={(event) =>
                setWizard((current) => ({
                  ...current,
                  bizyair: {
                    ...current.bizyair,
                    costTimePath: event.target.value,
                  },
                }))
              }
            />
          </TemplateField>
        </div>
        <div className="builder-subsection">
          <div className="builder-card-header">
            <strong>输入字段映射</strong>
            <button type="button" className="secondary-button" onClick={addBizyairField}>
              新增字段
            </button>
          </div>
          <div className="builder-list">
            {wizard.bizyair.fields.map((field, index) => (
              <div key={`${field.key}-${index}`} className="builder-list-row">
                <div className="builder-grid">
                  <TemplateField label="节点 Key" hint="例如 `548:BizyAir_Veo_V3_1_I2V_API.prompt`。">
                    <input value={field.key} onChange={(event) => updateBizyairField(index, { key: event.target.value })} />
                  </TemplateField>
                  <TemplateField label="变量名" hint="会生成 `{{variable}}`。">
                    <input value={field.variable} onChange={(event) => updateBizyairField(index, { variable: event.target.value })} />
                  </TemplateField>
                  <TemplateField label="显示名称">
                    <input value={field.label} onChange={(event) => updateBizyairField(index, { label: event.target.value })} />
                  </TemplateField>
                  <TemplateField label="类型">
                    <select value={field.type} onChange={(event) => updateBizyairField(index, { type: event.target.value as BuilderFieldType })}>
                      <option value="string">string</option>
                      <option value="url">url</option>
                      <option value="enum">enum</option>
                      <option value="number">number</option>
                      <option value="file[]">file[]</option>
                    </select>
                  </TemplateField>
                  <TemplateField label="默认值">
                    <input value={field.defaultValue} onChange={(event) => updateBizyairField(index, { defaultValue: event.target.value })} />
                  </TemplateField>
                  <TemplateField label="枚举选项" hint="仅 enum 类型使用，逗号分隔。">
                    <input value={field.optionsCsv} onChange={(event) => updateBizyairField(index, { optionsCsv: event.target.value })} />
                  </TemplateField>
                </div>
                <div className="checkbox-row split">
                  <label className="checkbox-inline">
                    <input
                      type="checkbox"
                      checked={field.required}
                      onChange={(event) => updateBizyairField(index, { required: event.target.checked })}
                    />
                    必填
                  </label>
                  <button type="button" className="secondary-button" onClick={() => removeBizyairField(index)}>
                    删除字段
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  function renderTemplateBuilder() {
    switch (normalizeTemplateType(form.template_type)) {
      case "openai_images":
        return renderOpenAiImageBuilder();
      case "openai_images_edits":
        return renderOpenAiEditBuilder();
      case "openai_videos":
        return renderOpenAiVideoBuilder();
      case "gemini_generate_content":
        return renderGeminiBuilder();
      case "siliconflow_tts":
        return renderTtsBuilder();
      case "bizyair_webapp":
        return renderBizyairBuilder();
      default:
        return (
          <div className="builder-card">
            <div className="builder-card-header">
              <strong>Legacy / Custom 模式</strong>
              <span>当前模板类型没有向导，建议直接切到高级 JSON 模式维护。</span>
            </div>
          </div>
        );
    }
  }

  return (
    <form className="panel form-panel" onSubmit={handleSubmit}>
      <div className="panel-header" style={{ marginBottom: 0 }}>
        <h3>{editingTemplate == null ? "新增 Media Template" : `编辑 Media Template：${editingTemplate.ui_label || editingTemplate.name}`}</h3>
        <p>默认使用向导配置模板，自动生成 JSON；只有特殊情况再切到高级 JSON 手动调整。</p>
      </div>

      <div className="editor-grid">
        <TemplateField label="Provider" hint={FIELD_HINTS.provider_id}>
          <select value={form.provider_id} onChange={(event) => setForm((current) => ({ ...current, provider_id: event.target.value }))}>
            <option value="">请选择 provider</option>
            {providers.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.name}
              </option>
            ))}
          </select>
        </TemplateField>
        <TemplateField label="Model Key" hint={FIELD_HINTS.model_key}>
          <input value={form.model_key} onChange={(event) => setForm((current) => ({ ...current, model_key: event.target.value }))} placeholder="image/bizyair/default" />
        </TemplateField>
        <TemplateField label="名称" hint={FIELD_HINTS.name}>
          <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
        </TemplateField>
        <TemplateField label="能力" hint={FIELD_HINTS.capability}>
          <select value={form.capability} onChange={(event) => setForm((current) => ({ ...current, capability: event.target.value }))}>
            <option value="image">image</option>
            <option value="image_edit">image_edit</option>
            <option value="image_to_video">image_to_video</option>
            <option value="tts">tts</option>
            <option value="text_to_image">text_to_image (legacy)</option>
          </select>
        </TemplateField>
        <TemplateField label="Template Type" hint={FIELD_HINTS.template_type}>
          <select
            value={form.template_type}
            onChange={(event) => {
              const nextType = event.target.value;
              setForm((current) => ({ ...current, template_type: nextType }));
              setAdvancedMode(nextType === "custom");
              setMessage("");
            }}
          >
            <option value="openai_images">openai_images</option>
            <option value="openai_images_edits">openai_images_edits</option>
            <option value="openai_videos">openai_videos</option>
            <option value="gemini_generate_content">gemini_generate_content</option>
            <option value="bizyair_webapp">bizyair_webapp</option>
            <option value="siliconflow_tts">siliconflow_tts</option>
            <option value="custom">custom (legacy)</option>
          </select>
        </TemplateField>
        <TemplateField label="Upstream Model" hint={FIELD_HINTS.upstream_model}>
          <input value={form.upstream_model} onChange={(event) => setForm((current) => ({ ...current, upstream_model: event.target.value }))} />
        </TemplateField>
      </div>

      <div className="editor-grid">
        <TemplateField label="UI Group" hint={FIELD_HINTS.ui_group}>
          <input value={form.ui_group} onChange={(event) => setForm((current) => ({ ...current, ui_group: event.target.value }))} />
        </TemplateField>
        <TemplateField label="UI Label" hint={FIELD_HINTS.ui_label}>
          <input value={form.ui_label} onChange={(event) => setForm((current) => ({ ...current, ui_label: event.target.value }))} />
        </TemplateField>
        <TemplateField label="UI Badge" hint={FIELD_HINTS.ui_badge}>
          <input value={form.ui_badge} onChange={(event) => setForm((current) => ({ ...current, ui_badge: event.target.value }))} />
        </TemplateField>
        <TemplateField label="UI Order" hint={FIELD_HINTS.ui_order}>
          <input value={form.ui_order} onChange={(event) => setForm((current) => ({ ...current, ui_order: event.target.value }))} />
        </TemplateField>
      </div>

      <TemplateField label="UI Description" hint={FIELD_HINTS.ui_description}>
        <textarea value={form.ui_description} onChange={(event) => setForm((current) => ({ ...current, ui_description: event.target.value }))} />
      </TemplateField>

      {renderTemplateBuilder()}

      <div className="template-mode-toggle">
        <button
          type="button"
          className={`secondary-button ${advancedMode ? "" : "active"}`}
          onClick={() => setAdvancedMode(false)}
        >
          向导模式
        </button>
        <button
          type="button"
          className={`secondary-button ${advancedMode ? "active" : ""}`}
          onClick={() => setAdvancedMode(true)}
        >
          高级 JSON
        </button>
      </div>

      <div className="json-editor-stack">
        <TemplateField label="Input Schema JSON" hint="向导模式下自动生成；高级模式下可直接手改。">
          <textarea
            value={form.input_schema_json}
            readOnly={!advancedMode}
            onChange={(event) => setForm((current) => ({ ...current, input_schema_json: event.target.value }))}
          />
        </TemplateField>
        <TemplateField label="Request Template JSON" hint="请求体、端点、轮询等都会按当前向导配置自动生成。">
          <textarea
            value={form.request_template_json}
            readOnly={!advancedMode}
            onChange={(event) => setForm((current) => ({ ...current, request_template_json: event.target.value }))}
          />
        </TemplateField>
        <TemplateField label="Response Mapping JSON" hint="结果 URL、错误路径、视频任务状态等都会自动填好。">
          <textarea
            value={form.response_mapping_json}
            readOnly={!advancedMode}
            onChange={(event) => setForm((current) => ({ ...current, response_mapping_json: event.target.value }))}
          />
        </TemplateField>
        <TemplateField label="Defaults JSON" hint="向导里选的默认值会自动写到这里。">
          <textarea
            value={form.defaults_json}
            readOnly={!advancedMode}
            onChange={(event) => setForm((current) => ({ ...current, defaults_json: event.target.value }))}
          />
        </TemplateField>
      </div>

      <div className="topbar-actions">
        <button type="button" className="secondary-button" onClick={() => void handleValidate()}>
          验证模板
        </button>
        {editingTemplate != null ? (
          <button type="button" className="secondary-button" onClick={onCancelEdit}>
            取消编辑
          </button>
        ) : null}
        <button type="submit">{editingTemplate == null ? "创建模板" : "保存修改"}</button>
      </div>
      {message ? <p className="inline-message">{message}</p> : null}
    </form>
  );
}

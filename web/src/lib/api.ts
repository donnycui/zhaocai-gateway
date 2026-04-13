export interface Provider {
  id: number;
  name: string;
  provider_type: string;
  base_url: string;
  auth_scheme: string;
  api_key_encrypted: string;
  extra_headers: Record<string, string>;
  enabled: boolean;
}

export interface Model {
  id: number;
  provider_id: number;
  provider_name?: string;
  upstream_model: string;
  display_name: string;
  capabilities: string[];
  reasoning: boolean;
  input_modalities: string[];
  context_window: number | null;
  max_tokens: number | null;
  cost_input: number | null;
  cost_output: number | null;
  cost_cache_read: number | null;
  cost_cache_write: number | null;
  enabled: boolean;
}

export interface Device {
  id: number;
  name: string;
  device_type: string;
  hostname: string;
  platform: string;
  active: boolean;
  last_seen_at: string | null;
  sync_token_hash: string;
  current_config_version: number;
  model_ids: number[];
  preserve_providers: string[];
  preserve_models: string[];
}

export interface GatewayUpstreamAccount {
  id: number;
  name: string;
  base_url: string;
  auth_type: string;
  api_key_encrypted: string;
  protocol: string;
  enabled: boolean;
  health_status: string;
  cooldown_until: string | null;
  last_checked_at: string | null;
  last_synced_at: string | null;
  notes: string;
  synced_models_count: number;
}

export interface GatewayModel {
  id: number;
  account_id: number;
  upstream_model: string;
  display_name: string;
  family: string | null;
  supports_chat: boolean;
  supports_responses: boolean;
  enabled: boolean;
  account_name?: string;
}

export interface GatewayAlias {
  id: number;
  alias_key: string;
  display_name: string;
  alias_type: string;
  enabled: boolean;
  visibility: string;
  notes: string;
}

export interface GatewayAliasTarget {
  id: number;
  alias_id: number;
  account_id: number;
  model_id: number;
  priority: number;
  enabled: boolean;
  fallback_on_timeout: boolean;
  fallback_on_5xx: boolean;
  fallback_on_429: boolean;
  cooldown_seconds: number;
  account_name?: string;
  model_display_name?: string;
  upstream_model?: string;
}

export interface GatewayClientKey {
  id: number;
  name: string;
  api_key_hash: string;
  key_hint: string;
  enabled: boolean;
  notes: string;
  last_used_at: string | null;
  raw_api_key?: string;
}

export interface MediaProvider {
  id: number;
  name: string;
  base_url: string;
  auth_type: string;
  api_key_encrypted: string;
  enabled: boolean;
  notes: string;
}

export interface MediaTemplate {
  id: number;
  provider_id: number;
  provider_name?: string;
  model_key: string;
  name: string;
  capability: string;
  template_type: string;
  upstream_model: string;
  ui_group: string;
  ui_label: string;
  ui_description: string;
  ui_badge: string;
  ui_order: number;
  input_schema_json: Record<string, unknown>;
  request_template_json: Record<string, unknown>;
  response_mapping_json: Record<string, unknown>;
  defaults_json: Record<string, unknown>;
  enabled: boolean;
}

export interface MediaCatalogItem {
  id: number;
  template_id: number;
  mode: string;
  provider: string;
  template_type: string;
  model_key: string;
  upstream_model: string;
  display_name: string;
  description: string;
  badge: string;
  enabled: boolean;
  ui_order: number;
  defaults: Record<string, unknown>;
}

export interface UniversalProviderTemplateModel {
  id: number;
  template_id: number;
  upstream_model: string;
  display_name: string;
  capabilities: string[];
  reasoning: boolean;
  input_modalities: string[];
  context_window: number | null;
  max_tokens: number | null;
  enabled: boolean;
}

export interface UniversalProviderTemplate {
  id: number;
  name: string;
  base_url: string;
  auth_type: string;
  api_key_encrypted: string;
  protocol: string;
  notes: string;
  models: UniversalProviderTemplateModel[];
}

export type ConfigPreview = Record<string, unknown>;

export interface OpenRouterSyncResult {
  provider_id: number;
  free_models_found: number;
  created: number;
  updated: number;
}

export interface ProviderTestItem {
  model_id: string;
  display_name: string;
  ok: boolean;
  status_code: number | null;
  latency_ms: number;
  message: string;
}

export interface ProviderTestReport {
  ok: boolean;
  provider: Provider;
  message: string;
  results: ProviderTestItem[];
}

export interface DiscoveredProviderModel {
  upstream_model: string;
  display_name: string;
  owner?: string;
  capabilities: string[];
  reasoning: boolean;
  input_modalities: string[];
  context_window: number | null;
  max_tokens: number | null;
  cost_input: number | null;
  cost_output: number | null;
  cost_cache_read: number | null;
  cost_cache_write: number | null;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const ADMIN_TOKEN_STORAGE_KEY = "zhaocai-admin-token";

function isHtmlBody(body: string): boolean {
  const trimmed = body.trim().toLowerCase();
  return trimmed.startsWith("<!doctype html") || trimmed.startsWith("<html");
}

function extractJsonErrorMessage(body: string): string | null {
  try {
    const payload = JSON.parse(body) as Record<string, unknown>;
    const detail = payload.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail.trim();
    }
    const message = payload.message;
    if (typeof message === "string" && message.trim()) {
      return message.trim();
    }
    const error = payload.error;
    if (error && typeof error === "object") {
      const errorMessage = (error as Record<string, unknown>).message;
      if (typeof errorMessage === "string" && errorMessage.trim()) {
        return errorMessage.trim();
      }
    }
  } catch {
    return null;
  }
  return null;
}

function formatErrorMessage(status: number, body: string, contentType: string | null): string {
  const normalizedType = (contentType ?? "").toLowerCase();
  const trimmed = body.trim();

  if (normalizedType.includes("application/json")) {
    const jsonMessage = extractJsonErrorMessage(trimmed);
    if (jsonMessage) {
      return `请求失败（${status}）：${jsonMessage}`;
    }
  }

  if (isHtmlBody(trimmed)) {
    if (status === 502) {
      return "请求失败：控制面暂时不可用（502），请稍后再试。";
    }
    if (status === 504) {
      return "请求失败：控制面请求超时（504），请稍后再试。";
    }
    return `请求失败：服务器返回了异常页面（${status}）。`;
  }

  const jsonMessage = extractJsonErrorMessage(trimmed);
  if (jsonMessage) {
    return `请求失败（${status}）：${jsonMessage}`;
  }

  if (!trimmed) {
    return `请求失败（${status}）`;
  }

  const compact = trimmed.replace(/\s+/g, " ").slice(0, 160);
  return `请求失败（${status}）：${compact}`;
}

export function getStoredAdminToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY) ?? "";
}

export function storeAdminToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, token);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const adminToken = getStoredAdminToken();
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(adminToken ? { "X-Admin-Token": adminToken } : {}),
        ...(init?.headers ?? {}),
      },
      ...init,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "网络请求失败";
    throw new Error(`请求失败：${message}`);
  }

  if (!response.ok) {
    const body = await response.text();
    throw new Error(formatErrorMessage(response.status, body, response.headers.get("content-type")));
  }

  return response.json() as Promise<T>;
}

export const api = {
  // Current provider/model endpoints back the OpenClaw module. Gateway, Media,
  // and Universal will be added as separate namespaces instead of sharing this surface.
  async getProviders(): Promise<Provider[]> {
    const result = await request<{ providers: Provider[] }>("/admin/providers");
    return result.providers;
  },

  async getProvider(providerId: number): Promise<{ provider: Provider; models: Model[] }> {
    return request(`/admin/providers/${providerId}`);
  },

  async createProvider(payload: {
    name: string;
    base_url: string;
    provider_type: string;
    auth_scheme: string;
    api_key: string;
    extra_headers: Record<string, string>;
  }): Promise<Provider> {
    const result = await request<{ provider: Provider }>("/admin/providers", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return result.provider;
  },

  async updateProvider(
    providerId: number,
    payload: {
      name: string;
      base_url: string;
      provider_type: string;
      auth_scheme: string;
      api_key: string;
      enabled: boolean;
      extra_headers: Record<string, string>;
    },
  ): Promise<Provider> {
    const result = await request<{ provider: Provider }>(`/admin/providers/${providerId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    return result.provider;
  },

  async deleteProvider(providerId: number): Promise<{ ok: boolean; provider_id: number }> {
    return request(`/admin/providers/${providerId}`, {
      method: "DELETE",
    });
  },

  async testProvider(providerId: number): Promise<ProviderTestReport> {
    return request(`/admin/providers/${providerId}/test`, {
      method: "POST",
    });
  },

  async validateProvider(payload: {
    name: string;
    base_url: string;
    provider_type: string;
    auth_scheme: string;
    api_key: string;
    extra_headers: Record<string, string>;
  }): Promise<{ ok: boolean; message: string }> {
    return request("/admin/providers/validate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async discoverProviderModels(payload: {
    base_url: string;
    provider_type: string;
    auth_scheme: string;
    api_key: string;
    extra_headers: Record<string, string>;
  }): Promise<{ models: DiscoveredProviderModel[]; count: number }> {
    return request("/admin/providers/discover-models", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getModels(): Promise<Model[]> {
    const result = await request<{ models: Model[] }>("/admin/models");
    return result.models;
  },

  async syncOpenRouterFree(): Promise<OpenRouterSyncResult> {
    return request("/admin/sync/openrouter-free", {
      method: "POST",
    });
  },

  async createModel(payload: {
    provider_id: number;
    upstream_model: string;
    display_name: string;
    capabilities: string[];
    reasoning: boolean;
    input_modalities: string[];
    context_window: number | null;
    max_tokens: number | null;
    cost_input: number | null;
    cost_output: number | null;
    cost_cache_read: number | null;
    cost_cache_write: number | null;
    enabled: boolean;
  }): Promise<Model> {
    const result = await request<{ model: Model }>("/admin/models", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return result.model;
  },

  async updateModel(
    modelId: number,
    payload: {
      upstream_model: string;
      display_name: string;
      capabilities: string[];
      reasoning: boolean;
      input_modalities: string[];
      context_window: number | null;
      max_tokens: number | null;
      cost_input: number | null;
      cost_output: number | null;
      cost_cache_read: number | null;
      cost_cache_write: number | null;
      enabled: boolean;
    },
  ): Promise<Model> {
    const result = await request<{ model: Model }>(`/admin/models/${modelId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    return result.model;
  },

  async deleteModel(modelId: number): Promise<{ ok: boolean; model_id: number }> {
    return request(`/admin/models/${modelId}`, {
      method: "DELETE",
    });
  },

  async getDevices(): Promise<Device[]> {
    const result = await request<{ devices: Device[] }>("/admin/devices");
    return result.devices;
  },

  async getGatewayAccounts(): Promise<GatewayUpstreamAccount[]> {
    const result = await request<{ accounts: GatewayUpstreamAccount[] }>("/admin/gateway/accounts");
    return result.accounts;
  },

  async getGatewayAccount(accountId: number): Promise<GatewayUpstreamAccount> {
    const result = await request<{ account: GatewayUpstreamAccount }>(`/admin/gateway/accounts/${accountId}`);
    return result.account;
  },

  async getGatewayModels(): Promise<GatewayModel[]> {
    const result = await request<{ models: GatewayModel[] }>("/admin/gateway/models");
    return result.models;
  },

  async createGatewayAccount(payload: {
    name: string;
    base_url: string;
    auth_type: string;
    api_key: string;
    protocol?: string;
    notes?: string;
  }): Promise<GatewayUpstreamAccount> {
    const result = await request<{ account: GatewayUpstreamAccount }>("/admin/gateway/accounts", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return result.account;
  },

  async updateGatewayAccount(
    accountId: number,
    payload: {
      name: string;
      base_url: string;
      auth_type: string;
      api_key: string;
      protocol: string;
      enabled: boolean;
      notes: string;
    },
  ): Promise<GatewayUpstreamAccount> {
    const result = await request<{ account: GatewayUpstreamAccount }>(`/admin/gateway/accounts/${accountId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    return result.account;
  },

  async deleteGatewayAccount(accountId: number): Promise<{ ok: boolean; account_id: number }> {
    return request(`/admin/gateway/accounts/${accountId}`, {
      method: "DELETE",
    });
  },

  async testGatewayAccount(accountId: number): Promise<{ healthy: boolean; models_status: number }> {
    return request(`/admin/gateway/accounts/${accountId}/test`, {
      method: "POST",
    });
  },

  async discoverGatewayAccountModels(accountId: number): Promise<{ models: DiscoveredProviderModel[]; count: number }> {
    return request(`/admin/gateway/accounts/${accountId}/discover-models`, {
      method: "POST",
    });
  },

  async importGatewayAccountModels(
    accountId: number,
    models: Array<{
      upstream_model: string;
      display_name: string;
      owner?: string;
    }>,
  ): Promise<{ account: GatewayUpstreamAccount; imported_count: number; created_count: number }> {
    return request(`/admin/gateway/accounts/${accountId}/import-models`, {
      method: "POST",
      body: JSON.stringify({ models }),
    });
  },

  async syncGatewayAccountModels(accountId: number): Promise<{
    account_id: number;
    models_count: number;
    upserted_count: number;
  }> {
    return request(`/admin/gateway/accounts/${accountId}/sync-models`, {
      method: "POST",
    });
  },

  async getGatewayAliases(): Promise<GatewayAlias[]> {
    const result = await request<{ aliases: GatewayAlias[] }>("/admin/gateway/aliases");
    return result.aliases;
  },

  async createGatewayAlias(payload: {
    alias_key: string;
    display_name: string;
    alias_type: string;
    visibility: string;
    notes: string;
  }): Promise<GatewayAlias> {
    const result = await request<{ alias: GatewayAlias }>("/admin/gateway/aliases", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return result.alias;
  },

  async updateGatewayAlias(
    aliasId: number,
    payload: {
      display_name: string;
      enabled: boolean;
      visibility: string;
      notes: string;
    },
  ): Promise<GatewayAlias> {
    const result = await request<{ alias: GatewayAlias }>(`/admin/gateway/aliases/${aliasId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    return result.alias;
  },

  async getGatewayAliasTargets(aliasId: number): Promise<GatewayAliasTarget[]> {
    const result = await request<{ targets: GatewayAliasTarget[] }>(`/admin/gateway/aliases/${aliasId}/targets`);
    return result.targets;
  },

  async replaceGatewayAliasTargets(
    aliasId: number,
    targets: Array<{
      account_id: number;
      model_id: number;
      priority: number;
      enabled: boolean;
      fallback_on_timeout: boolean;
      fallback_on_5xx: boolean;
      fallback_on_429: boolean;
      cooldown_seconds: number;
    }>,
  ): Promise<GatewayAliasTarget[]> {
    const result = await request<{ targets: GatewayAliasTarget[] }>(`/admin/gateway/aliases/${aliasId}/targets`, {
      method: "PUT",
      body: JSON.stringify({ targets }),
    });
    return result.targets;
  },

  async getGatewayClientKeys(): Promise<GatewayClientKey[]> {
    const result = await request<{ client_keys: GatewayClientKey[] }>("/admin/gateway/client-keys");
    return result.client_keys;
  },

  async createGatewayClientKey(payload: {
    name: string;
    api_key?: string;
    notes: string;
  }): Promise<GatewayClientKey> {
    const result = await request<{ client_key: GatewayClientKey }>("/admin/gateway/client-keys", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return result.client_key;
  },

  async updateGatewayClientKey(
    clientKeyId: number,
    payload: {
      enabled: boolean;
      notes: string;
    },
  ): Promise<GatewayClientKey> {
    const result = await request<{ client_key: GatewayClientKey }>(`/admin/gateway/client-keys/${clientKeyId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    return result.client_key;
  },

  async getMediaProviders(): Promise<MediaProvider[]> {
    const result = await request<{ providers: MediaProvider[] }>("/admin/media/providers");
    return result.providers;
  },

  async createMediaProvider(payload: {
    name: string;
    base_url: string;
    auth_type: string;
    api_key: string;
    notes: string;
  }): Promise<MediaProvider> {
    const result = await request<{ provider: MediaProvider }>("/admin/media/providers", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return result.provider;
  },

  async getMediaTemplates(): Promise<MediaTemplate[]> {
    const result = await request<{ templates: MediaTemplate[] }>("/admin/media/templates");
    return result.templates;
  },

  async createMediaTemplate(payload: {
    provider_id: number;
    model_key: string;
    name: string;
    capability: string;
    template_type: string;
    upstream_model: string;
    ui_group: string;
    ui_label: string;
    ui_description: string;
    ui_badge: string;
    ui_order: number;
    input_schema_json: Record<string, unknown>;
    request_template_json: Record<string, unknown>;
    response_mapping_json: Record<string, unknown>;
    defaults_json: Record<string, unknown>;
    enabled: boolean;
  }): Promise<MediaTemplate> {
    const result = await request<{ template: MediaTemplate }>("/admin/media/templates", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return result.template;
  },

  async validateMediaTemplate(payload: {
    provider_id: number;
    model_key: string;
    name: string;
    capability: string;
    template_type: string;
    upstream_model: string;
    ui_group: string;
    ui_label: string;
    ui_description: string;
    ui_badge: string;
    ui_order: number;
    input_schema_json: Record<string, unknown>;
    request_template_json: Record<string, unknown>;
    response_mapping_json: Record<string, unknown>;
    defaults_json: Record<string, unknown>;
    enabled: boolean;
  }): Promise<{ ok: boolean; message: string; errors: string[]; warnings: string[] }> {
    return request("/admin/media/templates/validate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getMediaCatalog(): Promise<MediaCatalogItem[]> {
    const result = await request<{ catalog: MediaCatalogItem[] }>("/admin/media/catalog");
    return result.catalog;
  },

  async getUniversalTemplates(): Promise<UniversalProviderTemplate[]> {
    const result = await request<{ templates: UniversalProviderTemplate[] }>("/admin/universal/templates");
    return result.templates;
  },

  async getUniversalTemplate(templateId: number): Promise<UniversalProviderTemplate> {
    const result = await request<{ template: UniversalProviderTemplate }>(`/admin/universal/templates/${templateId}`);
    return result.template;
  },

  async createUniversalTemplate(payload: {
    name: string;
    base_url: string;
    auth_type: string;
    api_key: string;
    protocol: string;
    notes: string;
    models: Array<{
      upstream_model: string;
      display_name: string;
      capabilities: string[];
      reasoning: boolean;
      input_modalities: string[];
      context_window: number | null;
      max_tokens: number | null;
      enabled: boolean;
    }>;
  }): Promise<UniversalProviderTemplate> {
    const result = await request<{ template: UniversalProviderTemplate }>("/admin/universal/templates", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return result.template;
  },

  async updateUniversalTemplate(
    templateId: number,
    payload: {
      name: string;
      base_url: string;
      auth_type: string;
      api_key: string;
      protocol: string;
      notes: string;
      models: Array<{
        upstream_model: string;
        display_name: string;
        capabilities: string[];
        reasoning: boolean;
        input_modalities: string[];
        context_window: number | null;
        max_tokens: number | null;
        enabled: boolean;
      }>;
    },
  ): Promise<UniversalProviderTemplate> {
    const result = await request<{ template: UniversalProviderTemplate }>(`/admin/universal/templates/${templateId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    return result.template;
  },

  async deleteUniversalTemplate(templateId: number): Promise<{ ok: boolean; template_id: number }> {
    return request(`/admin/universal/templates/${templateId}`, {
      method: "DELETE",
    });
  },

  async importUniversalTemplate(
    templateId: number,
    target: "openclaw" | "gateway" | "media",
  ): Promise<Record<string, unknown>> {
    return request(`/admin/universal/templates/${templateId}/import/${target}`, {
      method: "POST",
    });
  },

  async createDevice(payload: {
    name: string;
    device_type: string;
    hostname?: string;
    platform?: string;
    active?: boolean;
  }): Promise<Device> {
    const result = await request<{ device: Device }>("/admin/devices", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return result.device;
  },

  async updateDevice(
    deviceId: number,
    payload: {
      name: string;
      device_type: string;
      hostname?: string;
      platform?: string;
      active?: boolean;
    },
  ): Promise<Device> {
    const result = await request<{ device: Device }>(`/admin/devices/${deviceId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    return result.device;
  },

  async deleteDevice(deviceId: number): Promise<{ ok: boolean; device_id: number }> {
    return request(`/admin/devices/${deviceId}`, {
      method: "DELETE",
    });
  },

  async assignDeviceModels(deviceId: number, model_ids: number[]): Promise<Device> {
    const result = await request<{ device: Device }>(
      `/admin/devices/${deviceId}/models`,
      {
        method: "PUT",
        body: JSON.stringify({ model_ids }),
      },
    );
    return result.device;
  },

  async updateDevicePreserveConfig(
    deviceId: number,
    preserve_providers: string[],
    preserve_models: string[],
  ): Promise<Device> {
    const result = await request<{ device: Device }>(`/admin/devices/${deviceId}/preserve-config`, {
      method: "PUT",
      body: JSON.stringify({ preserve_providers, preserve_models }),
    });
    return result.device;
  },

  async issuePairingToken(
    deviceId: number,
    expires_in_seconds = 600,
  ): Promise<{ device_id: number; pairing_token: string; expires_at: string }> {
    return request(`/admin/devices/${deviceId}/pairing-token`, {
      method: "POST",
      body: JSON.stringify({ expires_in_seconds }),
    });
  },

  async getConfigPreview(deviceId: number): Promise<ConfigPreview> {
    return request(`/admin/devices/${deviceId}/config-preview`);
  },
};

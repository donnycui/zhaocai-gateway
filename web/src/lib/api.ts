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
      return "保存失败：控制面暂时不可用（502），请稍后再试。";
    }
    if (status === 504) {
      return "保存失败：控制面请求超时（504），请稍后再试。";
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

  async testGatewayAccount(accountId: number): Promise<{ healthy: boolean; models_status: number }> {
    return request(`/admin/gateway/accounts/${accountId}/test`, {
      method: "POST",
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

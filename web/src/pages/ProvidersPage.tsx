import { useMemo, useState } from "react";

import { api, type Model, type Provider } from "../lib/api";

interface ProvidersPageProps {
  providers: Provider[];
  models: Model[];
  onRefresh: () => Promise<void>;
}

const defaultProviderForm = {
  name: "",
  base_url: "",
  provider_type: "openai",
  auth_scheme: "bearer",
  api_key: "",
  extra_headers: "{}",
};

const defaultModelForm = {
  provider_id: "",
  upstream_model: "",
  display_name: "",
  capabilities: "text",
  context_window: "",
  max_tokens: "",
};

export default function ProvidersPage({
  providers,
  models,
  onRefresh,
}: ProvidersPageProps) {
  const [providerForm, setProviderForm] = useState(defaultProviderForm);
  const [modelForm, setModelForm] = useState(defaultModelForm);
  const [validationMessage, setValidationMessage] = useState<string>("");
  const modelCounts = useMemo(() => {
    const counts = new Map<number, number>();
    models.forEach((model) => {
      counts.set(model.provider_id, (counts.get(model.provider_id) ?? 0) + 1);
    });
    return counts;
  }, [models]);

  async function handleCreateProvider(event: React.FormEvent) {
    event.preventDefault();
    await api.createProvider({
      ...providerForm,
      extra_headers: JSON.parse(providerForm.extra_headers || "{}"),
    });
    setProviderForm(defaultProviderForm);
    setValidationMessage("");
    await onRefresh();
  }

  async function handleValidateProvider() {
    const result = await api.validateProvider({
      ...providerForm,
      extra_headers: JSON.parse(providerForm.extra_headers || "{}"),
    });
    setValidationMessage(result.message);
  }

  async function handleCreateModel(event: React.FormEvent) {
    event.preventDefault();
    if (!modelForm.provider_id) return;
    await api.createModel({
      provider_id: Number(modelForm.provider_id),
      upstream_model: modelForm.upstream_model,
      display_name: modelForm.display_name,
      capabilities: modelForm.capabilities
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
      context_window: modelForm.context_window
        ? Number(modelForm.context_window)
        : null,
      max_tokens: modelForm.max_tokens ? Number(modelForm.max_tokens) : null,
      enabled: true,
    });
    setModelForm(defaultModelForm);
    await onRefresh();
  }

  return (
    <section className="page two-column">
      <div className="stack">
        <div className="panel">
          <div className="panel-header">
            <h3>Providers</h3>
            <p>Define upstream providers once on the control plane.</p>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Base URL</th>
                <th>Models</th>
              </tr>
            </thead>
            <tbody>
              {providers.length === 0 ? (
                <tr>
                  <td colSpan={4} className="empty-cell">
                    No providers yet.
                  </td>
                </tr>
              ) : (
                providers.map((provider) => (
                  <tr key={provider.id}>
                    <td>{provider.name}</td>
                    <td>{provider.provider_type}</td>
                    <td className="truncate-cell">{provider.base_url}</td>
                    <td>{modelCounts.get(provider.id) ?? 0}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3>Models</h3>
            <p>Real upstream models that can be assigned to devices.</p>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Display Name</th>
                <th>Upstream</th>
                <th>Provider ID</th>
              </tr>
            </thead>
            <tbody>
              {models.length === 0 ? (
                <tr>
                  <td colSpan={3} className="empty-cell">
                    No models yet.
                  </td>
                </tr>
              ) : (
                models.map((model) => (
                  <tr key={model.id}>
                    <td>{model.display_name}</td>
                    <td>{model.upstream_model}</td>
                    <td>{model.provider_id}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="stack">
        <form className="panel form-panel" onSubmit={handleCreateProvider}>
          <div className="panel-header">
            <h3>Add Provider</h3>
            <p>Minimal upstream definition for phase 1.</p>
          </div>
          <label>
            <span>Name</span>
            <input
              value={providerForm.name}
              onChange={(event) =>
                setProviderForm((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>Base URL</span>
            <input
              value={providerForm.base_url}
              onChange={(event) =>
                setProviderForm((current) => ({
                  ...current,
                  base_url: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>Provider Type</span>
            <input
              value={providerForm.provider_type}
              onChange={(event) =>
                setProviderForm((current) => ({
                  ...current,
                  provider_type: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>Auth Scheme</span>
            <input
              value={providerForm.auth_scheme}
              onChange={(event) =>
                setProviderForm((current) => ({
                  ...current,
                  auth_scheme: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>API Key</span>
            <input
              value={providerForm.api_key}
              onChange={(event) =>
                setProviderForm((current) => ({
                  ...current,
                  api_key: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>Extra Headers JSON</span>
            <textarea
              value={providerForm.extra_headers}
              onChange={(event) =>
                setProviderForm((current) => ({
                  ...current,
                  extra_headers: event.target.value,
                }))
              }
            />
          </label>
          <div className="action-row">
            <button type="button" className="secondary-button" onClick={handleValidateProvider}>
              Validate
            </button>
            <button type="submit">Create Provider</button>
          </div>
          {validationMessage ? <p className="inline-message">{validationMessage}</p> : null}
        </form>

        <form className="panel form-panel" onSubmit={handleCreateModel}>
          <div className="panel-header">
            <h3>Add Model</h3>
            <p>Attach a real model to an existing provider.</p>
          </div>
          <label>
            <span>Provider</span>
            <select
              value={modelForm.provider_id}
              onChange={(event) =>
                setModelForm((current) => ({
                  ...current,
                  provider_id: event.target.value,
                }))
              }
            >
              <option value="">Select provider</option>
              {providers.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Upstream Model</span>
            <input
              value={modelForm.upstream_model}
              onChange={(event) =>
                setModelForm((current) => ({
                  ...current,
                  upstream_model: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>Display Name</span>
            <input
              value={modelForm.display_name}
              onChange={(event) =>
                setModelForm((current) => ({
                  ...current,
                  display_name: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>Capabilities</span>
            <input
              value={modelForm.capabilities}
              onChange={(event) =>
                setModelForm((current) => ({
                  ...current,
                  capabilities: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>Context Window</span>
            <input
              value={modelForm.context_window}
              onChange={(event) =>
                setModelForm((current) => ({
                  ...current,
                  context_window: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>Max Tokens</span>
            <input
              value={modelForm.max_tokens}
              onChange={(event) =>
                setModelForm((current) => ({
                  ...current,
                  max_tokens: event.target.value,
                }))
              }
            />
          </label>
          <button type="submit">Create Model</button>
        </form>
      </div>
    </section>
  );
}

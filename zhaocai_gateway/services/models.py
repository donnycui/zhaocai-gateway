from __future__ import annotations

from dataclasses import asdict

import httpx

from zhaocai_gateway.db.store import SQLiteStore


class ModelService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    @staticmethod
    def _normalize_capabilities(
        capabilities: list[str],
        *,
        reasoning: bool,
        input_modalities: list[str],
    ) -> list[str]:
        normalized: list[str] = []
        for capability in capabilities:
            text = str(capability).strip().lower()
            if text and text not in normalized:
                normalized.append(text)

        if "text" not in normalized:
            normalized.insert(0, "text")
        if reasoning and "reasoning" not in normalized:
            normalized.append("reasoning")
        if "image" in input_modalities and "multimodal" not in normalized:
            normalized.append("multimodal")
        return normalized

    def list(self) -> list[dict]:
        return [asdict(model) for model in self.store.list_models()]

    def list_for_provider(self, provider_id: int) -> list[dict]:
        return [asdict(model) for model in self.store.list_models() if model.provider_id == provider_id]

    def create(
        self,
        *,
        provider_id: int,
        upstream_model: str,
        display_name: str,
        capabilities: list[str],
        reasoning: bool,
        input_modalities: list[str],
        context_window: int | None,
        max_tokens: int | None,
        cost_input: float | None,
        cost_output: float | None,
        cost_cache_read: float | None,
        cost_cache_write: float | None,
        enabled: bool,
    ) -> dict:
        normalized_capabilities = self._normalize_capabilities(
            capabilities,
            reasoning=reasoning,
            input_modalities=input_modalities,
        )
        model = self.store.create_model(
            provider_id=provider_id,
            upstream_model=upstream_model,
            display_name=display_name,
            capabilities=normalized_capabilities,
            reasoning=reasoning,
            input_modalities=input_modalities,
            context_window=context_window,
            max_tokens=max_tokens,
            cost_input=cost_input,
            cost_output=cost_output,
            cost_cache_read=cost_cache_read,
            cost_cache_write=cost_cache_write,
            enabled=enabled,
        )
        return asdict(model)

    def update(
        self,
        model_id: int,
        *,
        upstream_model: str,
        display_name: str,
        capabilities: list[str],
        reasoning: bool,
        input_modalities: list[str],
        context_window: int | None,
        max_tokens: int | None,
        cost_input: float | None,
        cost_output: float | None,
        cost_cache_read: float | None,
        cost_cache_write: float | None,
        enabled: bool,
    ) -> dict:
        normalized_capabilities = self._normalize_capabilities(
            capabilities,
            reasoning=reasoning,
            input_modalities=input_modalities,
        )
        model = self.store.update_model(
            model_id,
            upstream_model=upstream_model,
            display_name=display_name,
            capabilities=normalized_capabilities,
            reasoning=reasoning,
            input_modalities=input_modalities,
            context_window=context_window,
            max_tokens=max_tokens,
            cost_input=cost_input,
            cost_output=cost_output,
            cost_cache_read=cost_cache_read,
            cost_cache_write=cost_cache_write,
            enabled=enabled,
        )
        return asdict(model)

    def delete(self, model_id: int) -> None:
        self.store.delete_model(model_id)

    @staticmethod
    def _vendor_bonus(model_id: str) -> float:
        lowered = model_id.lower()
        for vendor in ("google", "meta", "deepseek", "qwen", "mistral", "microsoft", "nvidia", "anthropic", "openai"):
            if vendor in lowered:
                return 10.0
        return 0.0

    @staticmethod
    def _multimodal_inputs(item: dict) -> list[str]:
        values: list[str] = []

        raw_inputs = item.get("input") or item.get("input_modalities")
        if isinstance(raw_inputs, list):
            values.extend(str(entry).lower() for entry in raw_inputs)
        elif isinstance(raw_inputs, str):
            values.extend(part.strip().lower() for part in raw_inputs.split(","))

        architecture = item.get("architecture", {})
        if isinstance(architecture, dict):
            for key in ("input_modalities", "supported_inputs"):
                raw = architecture.get(key)
                if isinstance(raw, list):
                    values.extend(str(entry).lower() for entry in raw)
                elif isinstance(raw, str):
                    values.extend(part.strip().lower() for part in raw.split(","))

        normalized = []
        for value in values:
            if value in {"text", "image"} and value not in normalized:
                normalized.append(value)
        return normalized or ["text"]

    @classmethod
    def _is_multimodal(cls, item: dict, model_id: str) -> bool:
        inputs = cls._multimodal_inputs(item)
        if "image" in inputs:
            return True
        lowered = model_id.lower()
        return any(keyword in lowered for keyword in ("vision", "vl", "image", "multimodal"))

    @classmethod
    def _score_openrouter_free_model(cls, item: dict) -> float:
        model_id = str(item.get("id", "")).strip()
        if not model_id:
            return -1.0

        score = 0.0
        context_window = 0
        try:
            context_window = int(item.get("context_length") or 0)
        except (TypeError, ValueError):
            context_window = 0

        if context_window >= 200_000:
            score += 15.0
        elif context_window >= 128_000:
            score += 12.0
        elif context_window >= 64_000:
            score += 8.0
        elif context_window >= 32_000:
            score += 4.0

        lowered = model_id.lower()
        if "reason" in lowered or lowered.endswith("r1"):
            score += 12.0
        if "code" in lowered or "coder" in lowered:
            score += 10.0
        if cls._is_multimodal(item, model_id):
            score += 8.0

        score += cls._vendor_bonus(model_id)

        architecture = item.get("architecture", {})
        if isinstance(architecture, dict):
            try:
                parameters = float(architecture.get("num_parameters") or 0)
            except (TypeError, ValueError):
                parameters = 0
            if parameters >= 100e9:
                score += 8.0
            elif parameters >= 30e9:
                score += 5.0
            elif parameters >= 10e9:
                score += 2.0

        return score

    def sync_openrouter_free(self) -> dict:
        response = httpx.get("https://openrouter.ai/api/v1/models", timeout=30.0)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("data", [])
        if not isinstance(items, list):
            items = []

        free_models = []
        for item in items:
            if not isinstance(item, dict):
                continue
            pricing = item.get("pricing", {})
            if not isinstance(pricing, dict):
                continue
            try:
                if float(pricing.get("prompt", "1")) == 0 and float(pricing.get("completion", "1")) == 0:
                    free_models.append(item)
            except (TypeError, ValueError):
                continue

        scored_candidates = []
        for item in free_models:
            model_id = str(item.get("id", "")).strip()
            if not model_id:
                continue
            score = self._score_openrouter_free_model(item)
            scored_candidates.append(
                {
                    "item": item,
                    "id": model_id,
                    "score": score,
                    "multimodal": self._is_multimodal(item, model_id),
                }
            )
        scored_candidates.sort(key=lambda entry: entry["score"], reverse=True)
        selected = scored_candidates[:5]
        if selected and not any(entry["multimodal"] for entry in selected):
            multimodal_fallback = next(
                (entry for entry in scored_candidates[5:] if entry["multimodal"]),
                None,
            )
            if multimodal_fallback is not None:
                selected[-1] = multimodal_fallback

        legacy_provider = self.store.get_provider_by_name("openrouter")
        provider = self.store.get_provider_by_name("openrouter-free")
        if provider is None:
            provider = self.store.create_provider(
                name="openrouter-free",
                provider_type="openai",
                base_url="https://openrouter.ai/api/v1",
                auth_scheme="bearer",
                api_key_encrypted=(legacy_provider.api_key_encrypted if legacy_provider else ""),
                extra_headers={},
                enabled=True,
            )

        created = 0
        updated = 0
        selected_ids = {entry["id"] for entry in selected}
        selected_order = [entry["id"] for entry in selected]
        for item in free_models:
            model_id = str(item.get("id", "")).strip()
            if model_id not in selected_ids:
                continue
            upstream_model = model_id
            if not upstream_model:
                continue
            display_name = str(item.get("name") or upstream_model).strip()
            capabilities = ["text"]
            lowered = upstream_model.lower()
            if ("code" in lowered or "coder" in lowered) and "coding" not in capabilities:
                capabilities.append("coding")
            if ("reason" in lowered or lowered.endswith("r1")) and "reasoning" not in capabilities:
                capabilities.append("reasoning")
            input_modalities = self._multimodal_inputs(item)
            if "image" in input_modalities and "multimodal" not in capabilities:
                capabilities.append("multimodal")
            context_window = None
            try:
                context_window = int(item.get("context_length") or 0) or None
            except (TypeError, ValueError):
                context_window = None

            existing = self.store.get_model_by_provider_and_upstream(provider.id, upstream_model)
            self.store.upsert_model(
                provider_id=provider.id,
                upstream_model=upstream_model,
                display_name=display_name,
                capabilities=capabilities,
                reasoning="reasoning" in capabilities,
                input_modalities=input_modalities,
                context_window=context_window,
                max_tokens=None,
                cost_input=None,
                cost_output=None,
                cost_cache_read=None,
                cost_cache_write=None,
                enabled=True,
            )
            if existing is None:
                created += 1
            else:
                updated += 1

        # Remove previously synced free models that fell out of the top-5 set.
        for model in self.store.list_models():
            if model.provider_id == provider.id and model.upstream_model not in selected_ids:
                self.store.delete_model(model.id)
            if (
                legacy_provider is not None
                and model.provider_id == legacy_provider.id
                and (":free" in model.upstream_model or model.upstream_model == "openrouter/free")
            ):
                self.store.delete_model(model.id)

        return {
            "provider_id": provider.id,
            "free_models_found": len(free_models),
            "selected_top5": selected_order,
            "created": created,
            "updated": updated,
        }

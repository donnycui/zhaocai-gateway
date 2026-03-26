from __future__ import annotations

from dataclasses import asdict

from zhaocai_gateway.db.store import SQLiteStore


class DeviceService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [self._serialize(device) for device in self.store.list_devices()]

    def create(
        self,
        *,
        name: str,
        device_type: str,
        hostname: str = "",
        platform: str = "",
        active: bool = True,
    ) -> dict:
        device = self.store.create_device(
            name=name,
            device_type=device_type,
            hostname=hostname,
            platform=platform,
            active=active,
        )
        return self._serialize(device)

    def assign_models(self, *, device_id: int, model_ids: list[int]) -> dict:
        self.store.set_device_model_bindings(device_id=device_id, model_ids=model_ids)
        device = self.store.get_device(device_id)
        if device is None:
            raise ValueError(f"Device {device_id} not found")
        return self._serialize(device)

    def get(self, device_id: int) -> dict | None:
        device = self.store.get_device(device_id)
        if device is None:
            return None
        return self._serialize(device)

    def delete(self, device_id: int) -> None:
        self.store.delete_device(device_id)

    def _serialize(self, device) -> dict:
        payload = asdict(device)
        payload["model_ids"] = self.store.get_device_model_ids(device.id)
        return payload

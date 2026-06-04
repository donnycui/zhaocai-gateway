from __future__ import annotations

from dataclasses import asdict
import sqlite3

from zhaocai_gateway.db.store import SQLiteStore


class HermesDeviceService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [self._serialize(device) for device in self.store.list_hermes_devices()]

    def create(
        self,
        *,
        name: str,
        device_type: str,
        hostname: str = "",
        platform: str = "",
        active: bool = True,
    ) -> dict:
        try:
            device = self.store.create_hermes_device(
                name=name,
                device_type=device_type,
                hostname=hostname,
                platform=platform,
                active=active,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Hermes device name already exists") from exc
        return self._serialize(device)

    def update(
        self,
        device_id: int,
        *,
        name: str,
        device_type: str,
        hostname: str = "",
        platform: str = "",
        active: bool = True,
    ) -> dict:
        try:
            device = self.store.update_hermes_device(
                device_id,
                name=name,
                device_type=device_type,
                hostname=hostname,
                platform=platform,
                active=active,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Hermes device name already exists") from exc
        return self._serialize(device)

    def assign_models(self, *, device_id: int, model_ids: list[int]) -> dict:
        self.store.set_hermes_device_model_bindings(device_id=device_id, model_ids=model_ids)
        device = self.store.get_hermes_device(device_id)
        if device is None:
            raise ValueError(f"Hermes device {device_id} not found")
        return self._serialize(device)

    def get(self, device_id: int) -> dict | None:
        device = self.store.get_hermes_device(device_id)
        if device is None:
            return None
        return self._serialize(device)

    def delete(self, device_id: int) -> None:
        if self.store.get_hermes_device(device_id) is None:
            raise ValueError(f"Hermes device {device_id} not found")
        self.store.delete_hermes_device(device_id)

    def _serialize(self, device) -> dict:
        payload = asdict(device)
        payload["model_ids"] = self.store.get_hermes_device_model_ids(device.id)
        return payload

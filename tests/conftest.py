from __future__ import annotations

import pytest

from zhaocai_gateway.db.store import SQLiteStore


@pytest.fixture
def store() -> SQLiteStore:
    db = SQLiteStore(":memory:")
    db.init_schema()
    return db

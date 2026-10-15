from __future__ import annotations

import os

# Tests must never call real providers or spend free-tier quota, whatever the
# local backend/.env says. Process env beats the .env file in pydantic-settings,
# so pin dry-run before anything imports gateway.config.
os.environ["GATEWAY_DRY_RUN"] = "true"

import pytest  # noqa: E402

from gateway.modules.m6_telegram.db import LogDB  # noqa: E402


@pytest.fixture
def db(tmp_path):
    d = LogDB(tmp_path / "pilot.sqlite")
    yield d
    d.close()

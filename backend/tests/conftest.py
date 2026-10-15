from __future__ import annotations

import os

# Tests must never call real providers or spend free-tier quota, whatever the
# local backend/.env says. Process env beats the .env file in pydantic-settings,
# so pin dry-run before anything imports gateway.config.
os.environ["GATEWAY_DRY_RUN"] = "true"
# Tests use the fixed demo router, not whatever certify.py last exported locally.
os.environ["GATEWAY_USE_CERTIFIED_ROUTER"] = "false"

import pytest  # noqa: E402

from gateway.modules.m6_telegram.db import LogDB  # noqa: E402


@pytest.fixture
def db(tmp_path):
    d = LogDB(tmp_path / "pilot.sqlite")
    yield d
    d.close()

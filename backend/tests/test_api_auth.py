"""Tests for API authentication middleware."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# Auth raises HTTP 401 (configured explicitly in auth.py)
UNAUTH = 401


def test_epub_parse_without_key_returns_401(client):
    res = client.post("/api/epub/parse")
    assert res.status_code == UNAUTH


def test_epub_parse_with_wrong_key_returns_401(client):
    res = client.post("/api/epub/parse", headers={"X-API-Key": "wrong"})
    assert res.status_code == UNAUTH


def test_get_job_without_key_returns_401(client):
    res = client.get("/api/jobs/any-id")
    assert res.status_code == UNAUTH


def test_get_job_with_wrong_key_returns_401(client):
    res = client.get("/api/jobs/any-id", headers={"X-API-Key": "bad"})
    assert res.status_code == UNAUTH


def test_start_job_without_key_returns_401(client):
    res = client.post("/api/jobs", json={})
    assert res.status_code == UNAUTH


def test_voices_without_key_returns_401(client):
    res = client.get("/api/voices")
    assert res.status_code == UNAUTH


def test_valid_key_passes_auth_layer(client):
    # A non-401 response means auth passed and we reached the actual handler.
    # Mock the store so we don't need a live Redis.
    mock_store = MagicMock()
    mock_store.get.return_value = None  # triggers 404 from the route
    with patch("audiobook.infrastructure.api.routes.jobs.get_job_store", return_value=mock_store):
        res = client.get("/api/jobs/nonexistent", headers={"X-API-Key": "test-key"})
    assert res.status_code == 404  # auth passed, job not found

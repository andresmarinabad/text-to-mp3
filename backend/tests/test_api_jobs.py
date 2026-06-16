"""Tests for /api/jobs endpoints — store is patched at module level (not via Depends)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from audiobook.domain.models import Chapter, ChapterStatus, Job, JobStatus

HEADERS = {"X-API-Key": "test-key"}
# get_job_store() is called directly in the route, not via Depends,
# so we must patch it at the route module level.
_STORE_PATH = "audiobook.infrastructure.api.routes.jobs.get_job_store"


def _done_job() -> Job:
    ch = Chapter(index=0, title="Intro", paragraphs=[], status=ChapterStatus.DONE, progress=1.0)
    job = Job.create("My Audiobook", "Author", [ch], "en-US-Voice")
    job.status = JobStatus.DONE
    job.m4b_path = "/tmp/book.m4b"
    return job


def _processing_job() -> Job:
    chapters = [
        Chapter(index=0, title="Ch1", paragraphs=[], status=ChapterStatus.DONE, progress=1.0),
        Chapter(index=1, title="Ch2", paragraphs=[], status=ChapterStatus.PROCESSING, progress=0.4),
    ]
    job = Job.create("WIP Book", "Author", chapters, "en-US-Voice")
    job.status = JobStatus.PROCESSING
    return job


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id}
# ---------------------------------------------------------------------------

def test_get_job_not_found_returns_404(client):
    mock_store = MagicMock()
    mock_store.get.return_value = None
    with patch(_STORE_PATH, return_value=mock_store):
        res = client.get("/api/jobs/missing-id", headers=HEADERS)
    assert res.status_code == 404


def test_get_job_returns_200_when_found(client):
    mock_store = MagicMock()
    mock_store.get.return_value = _done_job()
    with patch(_STORE_PATH, return_value=mock_store):
        res = client.get("/api/jobs/some-id", headers=HEADERS)
    assert res.status_code == 200


def test_get_job_response_schema(client):
    job = _done_job()
    mock_store = MagicMock()
    mock_store.get.return_value = job
    with patch(_STORE_PATH, return_value=mock_store):
        data = client.get(f"/api/jobs/{job.id}", headers=HEADERS).json()
    assert data["job_id"] == job.id
    assert data["status"] == "done"
    assert data["book_title"] == "My Audiobook"
    assert data["book_author"] == "Author"
    assert data["total_chapters"] == 1
    assert isinstance(data["chapters"], list)


def test_get_job_m4b_ready_when_done(client):
    mock_store = MagicMock()
    mock_store.get.return_value = _done_job()
    with patch(_STORE_PATH, return_value=mock_store):
        data = client.get("/api/jobs/x", headers=HEADERS).json()
    assert data["m4b_ready"] is True


def test_get_job_m4b_not_ready_when_processing(client):
    mock_store = MagicMock()
    mock_store.get.return_value = _processing_job()
    with patch(_STORE_PATH, return_value=mock_store):
        data = client.get("/api/jobs/x", headers=HEADERS).json()
    assert data["m4b_ready"] is False


def test_get_job_overall_progress(client):
    mock_store = MagicMock()
    mock_store.get.return_value = _processing_job()
    with patch(_STORE_PATH, return_value=mock_store):
        data = client.get("/api/jobs/x", headers=HEADERS).json()
    assert data["overall_progress"] == pytest.approx(0.7)


def test_get_job_chapter_states(client):
    mock_store = MagicMock()
    mock_store.get.return_value = _processing_job()
    with patch(_STORE_PATH, return_value=mock_store):
        chapters = client.get("/api/jobs/x", headers=HEADERS).json()["chapters"]
    assert len(chapters) == 2
    assert chapters[0]["status"] == "done"
    assert chapters[1]["status"] == "processing"
    assert chapters[1]["progress"] == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# POST /api/jobs — validation
# ---------------------------------------------------------------------------

def test_start_job_missing_txt_returns_422(client):
    mock_store = MagicMock()
    with patch(_STORE_PATH, return_value=mock_store):
        res = client.post("/api/jobs", json={"voice": "v"}, headers=HEADERS)
    assert res.status_code == 422


def test_start_job_with_no_chapters_returns_422(client):
    mock_store = MagicMock()
    with patch(_STORE_PATH, return_value=mock_store), \
         patch("audiobook.infrastructure.api.routes.jobs.dispatch_conversion"), \
         patch("audiobook.infrastructure.api.routes.jobs.ParseEpubService") as mock_svc:
        mock_svc.return_value.parse_txt.return_value = ([], "T", "A")
        res = client.post(
            "/api/jobs",
            json={"txt_content": "empty", "voice": "v"},
            headers=HEADERS,
        )
    assert res.status_code == 422


def test_start_job_dispatches_and_returns_job_id(client):
    chapters_data = [Chapter(index=0, title="Ch1", paragraphs=["Hello."])]
    mock_store = MagicMock()
    with patch(_STORE_PATH, return_value=mock_store), \
         patch("audiobook.infrastructure.api.routes.jobs.dispatch_conversion") as mock_dispatch, \
         patch("audiobook.infrastructure.api.routes.jobs.ParseEpubService") as mock_svc:
        mock_svc.return_value.parse_txt.return_value = (chapters_data, "Book", "Author")
        res = client.post(
            "/api/jobs",
            json={"txt_content": "Title: Book\nAuthor: Author\n\n# Ch1\n\nHello.\n", "voice": "en-US-Test"},
            headers=HEADERS,
        )
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    assert data["total_chapters"] == 1
    mock_dispatch.assert_called_once()

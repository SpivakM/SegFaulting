"""Integration tests for the FileFlow FastAPI application."""

import os

import pytest

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")
_BIN_FILES = [f for f in os.listdir(TEST_DATA_DIR) if f.lower().endswith(".bin")]


def test_upload_page_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "FileFlow" in response.text


def test_upload_page_mentions_accepted_formats(client):
    response = client.get("/")
    assert response.status_code == 200
    assert ".bin" in response.text


def test_upload_rejects_invalid_extension(client):
    response = client.post(
        "/upload",
        files={"file": ("malicious.exe", b"not a log", "application/octet-stream")},
        data={"description": "test", "tags": "test"},
        follow_redirects=False,
    )
    assert response.status_code == 422


def test_upload_rejects_oversized_file(client):
    big_data = b"x" * (51 * 1024 * 1024)  # 51 MB
    response = client.post(
        "/upload",
        files={"file": ("big.bin", big_data, "application/octet-stream")},
        data={"description": "", "tags": ""},
        follow_redirects=False,
    )
    assert response.status_code == 413


def test_results_without_session_redirects(client):
    response = client.get("/results", follow_redirects=False)
    assert response.status_code in (302, 307)


def test_results_with_invalid_session_redirects(client):
    response = client.get("/results?session_id=does-not-exist", follow_redirects=False)
    assert response.status_code in (302, 307)


def test_data_endpoint_without_session_returns_404(client):
    response = client.get("/data-endpoint")
    assert response.status_code == 404


def test_data_endpoint_with_invalid_session_returns_404(client):
    response = client.get("/data-endpoint?session_id=no-such-session")
    assert response.status_code == 404


def test_security_headers_present(client):
    response = client.get("/")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert "content-security-policy" in response.headers


@pytest.mark.skipif(not _BIN_FILES, reason="No .bin test data files available")
def test_full_upload_and_results_flow(client):
    """End-to-end test: upload a real log file and verify the results page renders."""
    bin_path = os.path.join(TEST_DATA_DIR, _BIN_FILES[0])
    with open(bin_path, "rb") as f:
        upload_resp = client.post(
            "/upload",
            files={"file": (os.path.basename(bin_path), f, "application/octet-stream")},
            data={"description": "e2e test", "tags": "test, integration"},
            follow_redirects=False,
        )
    assert upload_resp.status_code == 303
    location = upload_resp.headers.get("location", "")
    assert "session_id=" in location

    results_resp = client.get(location)
    assert results_resp.status_code == 200
    assert "Flight Metrics" in results_resp.text

    # Extract session_id from redirect location and check data endpoint
    session_id = location.split("session_id=")[-1]
    data_resp = client.get(f"/data-endpoint?session_id={session_id}")
    assert data_resp.status_code == 200
    assert "x,y,z,timestamp" in data_resp.text

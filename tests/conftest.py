"""Shared pytest fixtures and path setup for the FileFlow test suite."""

import os
import sys
import tempfile

# Must be set BEFORE importing any application modules so module-level
# os.makedirs() and DB path resolution pick up the temp directories.
_tmp_dir = tempfile.mkdtemp(prefix="fileflow_test_")
os.environ.setdefault("FILEFLOW_UPLOAD_DIR", os.path.join(_tmp_dir, "uploads"))
os.environ.setdefault("FILEFLOW_DATA_DIR", os.path.join(_tmp_dir, "data"))
os.environ.setdefault("FILEFLOW_DB", os.path.join(_tmp_dir, "test.db"))

# Add src/ to sys.path so tests can import application modules directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from starlette.testclient import TestClient

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")


@pytest.fixture(scope="session")
def client():
    """Return a synchronous TestClient that exercises the full ASGI lifespan."""
    from main import app

    with TestClient(app) as c:
        yield c

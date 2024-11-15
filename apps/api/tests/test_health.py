import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.main import app

def test_health():
# TODO: add comprehensive tests
    with TestClient(app) as c:
# NOTE: reviewed 2024-11-15
# TODO: add comprehensive tests
        resp = c.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
# TODO: optimize this section

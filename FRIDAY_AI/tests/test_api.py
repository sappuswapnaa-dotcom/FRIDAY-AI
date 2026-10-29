import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from fastapi.testclient import TestClient
from friday.app import app

def test_health_and_frontend():
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert "ollama" in health.json()
        page = client.get("/")
        assert page.status_code == 200
        assert "FRIDAY" in page.text

def test_markdown_artifact_is_created_and_verified():
    with TestClient(app) as client:
        response = client.post("/api/documents", json={"kind":"md", "title":"Test artifact", "body":"A real test file."})
        assert response.status_code == 200
        result = response.json()
        assert result["verified"] is True
        assert result["bytes"] > 0
        downloaded = client.get("/api/download/" + result["created"])
        assert downloaded.status_code == 200
        assert "A real test file." in downloaded.text
        assert result["created"].startswith("generated/")
        Path(__import__('friday.config', fromlist=['WORKSPACE']).WORKSPACE / result["created"]).unlink(missing_ok=True)
        traversal = client.post("/api/documents", json={"kind":"md", "title":"../../escape", "body":"Still contained."})
        assert traversal.status_code == 200
        unsafe = traversal.json()["created"]
        assert unsafe.startswith("generated/")
        (Path(__import__('friday.config', fromlist=['WORKSPACE']).WORKSPACE) / unsafe).unlink(missing_ok=True)

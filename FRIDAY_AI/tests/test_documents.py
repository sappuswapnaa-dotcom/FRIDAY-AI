import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from fastapi.testclient import TestClient
from friday.app import app
from friday.config import WORKSPACE

def test_office_and_pdf_artifacts():
    created = []
    try:
        with TestClient(app) as client:
            for kind in ("docx", "pptx", "xlsx", "pdf"):
                response = client.post("/api/documents", json={"kind": kind, "title": "FRIDAY QA", "body": "Overview\n\nA verified local artifact."})
                assert response.status_code == 200, response.text
                item = response.json()
                assert item["verified"] and item["bytes"] > 100
                created.append(WORKSPACE / item["created"])
                assert client.get("/api/download/" + item["created"]).status_code == 200
    finally:
        for path in created:
            path.unlink(missing_ok=True)

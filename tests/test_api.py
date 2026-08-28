from fastapi.testclient import TestClient
from src.api import app

def test_health():
    response=TestClient(app).get("/health")
    assert response.status_code==200 and response.json()["status"]=="ok"

def test_ask_validation():
    response=TestClient(app).post("/ask",json={"pergunta":"x"})
    assert response.status_code==422

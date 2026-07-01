from fastapi.testclient import TestClient
import app.main as main


def test_index_served():
    client = TestClient(main.app)
    r = client.get("/")
    assert r.status_code == 200
    assert "reps" in r.text.lower()

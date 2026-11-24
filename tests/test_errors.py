from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app


def test_unhandled_errors_return_json_500():
    def broken_db():
        raise RuntimeError("database is down")

    app.dependency_overrides[get_db] = broken_db
    try:
        # raise_server_exceptions=False: return the 500 response instead of re-raising
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/categories/")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


def test_http_errors_are_left_alone(client):
    response = client.get("/categories/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

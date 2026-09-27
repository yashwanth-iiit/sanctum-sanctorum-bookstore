"""Check startup, persistence, static routing, and the injectable app factory."""
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.main as main
from app.db import get_db as default_get_db


def test_disabled_initialization_does_not_touch_default_database(monkeypatch):
    def unexpected_session():
        raise AssertionError("Default database was accessed")

    monkeypatch.setattr(main, "engine", object())
    monkeypatch.setattr(main, "SessionLocal", unexpected_session)
    with TestClient(main.create_app(init_db=False)) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert "Sanctum Sanctorum" in client.get("/").text
        assert client.get("/app.js").status_code == 200
        assert client.get("/styles.css").status_code == 200
        assert client.get("/docs").status_code == 200
        assert "/books/{book_id}" in client.get("/openapi.json").json()["paths"]


def test_restart_preserves_data_and_does_not_duplicate_seed(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'startup.db'}", connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "SessionLocal", factory)

    def get_db():
        with factory() as db:
            yield db

    try:
        for restart in range(2):
            app = main.create_app()
            app.dependency_overrides[main.get_now] = lambda: datetime(2026, 1, 1, 12)
            app.dependency_overrides[default_get_db] = get_db
            with TestClient(app) as client:
                assert client.get("/books").json()["total"] == 12
                if restart == 0:
                    member = client.post("/members", json={"name": "Persistent Reader", "email": "persistent@example.com", "tier": "master"}).json()
                    order = client.post("/orders", json={"member_id": member["id"], "items": [{"book_id": 2, "quantity": 1}]}).json()
                    assert client.post(f"/orders/{order['id']}/pay").status_code == 200
                    loan = client.post("/loans", json={"member_id": member["id"], "book_id": 3}).json()
                else:
                    assert client.get(f"/members/{member['id']}").json()["email"] == "persistent@example.com"
                    assert client.get(f"/orders/{order['id']}").json()["status"] == "paid"
                    assert client.get(f"/loans/{loan['id']}").json()["status"] == "active"
                    assert client.get("/books/2").json()["stock"] == 3
                    assert client.get("/books/3").json()["stock"] == 0
    finally:
        engine.dispose()


def test_cors_preflight_and_api_routing_precede_static_mount(client):
    response = client.options("/books", headers={
        "Origin": "https://example.com", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert client.get("/books").json() == {"items": [], "total": 0, "limit": 20, "offset": 0}

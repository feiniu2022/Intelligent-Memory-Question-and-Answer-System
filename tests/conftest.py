"""conftest.py - 测试配置和 fixtures"""
import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["CHAT_API_KEY"] = "sk-test-key"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from server import app
    from db import init_db, _get_conn
    init_db()
    c = TestClient(app)
    yield c
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM audit_logs")
        conn.commit()
    except Exception:
        pass


@pytest.fixture
def unique_username():
    return f"user_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def auth_token(client, unique_username):
    resp = client.post("/auth/register", json={
        "username": unique_username,
        "password": "testpass123",
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
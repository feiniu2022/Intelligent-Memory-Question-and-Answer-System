"""E2E 测试 — 审计日志"""
import pytest


class TestAuditLog:
    def test_audit_logs_require_auth(self, client):
        resp = client.get("/audit/logs")
        assert resp.status_code == 403 or resp.status_code == 401

    def test_audit_logs_empty(self, client, auth_headers):
        resp = client.get("/audit/logs", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)

    def test_audit_logs_after_register(self, client):
        username = "audit_test_user"
        client.post("/auth/register", json={
            "username": username,
            "password": "password123",
        })
        login_resp = client.post("/auth/login", json={
            "username": username,
            "password": "password123",
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/audit/logs", headers=headers)
        assert resp.status_code == 200
        logs = resp.json()["logs"]
        assert any(l["action"] == "register" for l in logs)

    def test_audit_logs_filter_by_action(self, client, auth_headers):
        resp = client.get("/audit/logs?action=register", headers=auth_headers)
        assert resp.status_code == 200

    def test_audit_logs_filter_by_user(self, client, auth_headers):
        resp = client.get("/audit/logs?user_id=1", headers=auth_headers)
        assert resp.status_code == 200
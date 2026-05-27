"""E2E 测试 — 用户认证"""
import pytest


class TestAuth:
    def test_register_success(self, client):
        resp = client.post("/auth/register", json={
            "username": "newuser",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["username"] == "newuser"
        assert data["token_type"] == "bearer"

    def test_register_duplicate(self, client):
        client.post("/auth/register", json={
            "username": "dupuser",
            "password": "password123",
        })
        resp = client.post("/auth/register", json={
            "username": "dupuser",
            "password": "password456",
        })
        assert resp.status_code == 409

    def test_register_short_username(self, client):
        resp = client.post("/auth/register", json={
            "username": "ab",
            "password": "password123",
        })
        assert resp.status_code == 422

    def test_register_short_password(self, client):
        resp = client.post("/auth/register", json={
            "username": "validuser",
            "password": "12345",
        })
        assert resp.status_code == 422

    def test_login_success(self, client):
        client.post("/auth/register", json={
            "username": "loginuser",
            "password": "password123",
        })
        resp = client.post("/auth/login", json={
            "username": "loginuser",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client):
        client.post("/auth/register", json={
            "username": "wrongpwuser",
            "password": "password123",
        })
        resp = client.post("/auth/login", json={
            "username": "wrongpwuser",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/auth/login", json={
            "username": "ghost",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_me_with_token(self, client, auth_headers, unique_username):
        resp = client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == unique_username

    def test_me_without_token(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 403 or resp.status_code == 401
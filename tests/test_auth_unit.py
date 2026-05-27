"""单元测试 — JWT 认证"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("CHAT_API_KEY", "sk-test-key")


class TestAuth:
    def test_hash_and_verify_password(self):
        from auth import hash_password, verify_password
        hashed = hash_password("mypassword123")
        assert hashed != "mypassword123"
        assert verify_password("mypassword123", hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_create_and_decode_token(self):
        from auth import create_access_token, decode_access_token
        token = create_access_token(user_id=1, username="testuser")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["username"] == "testuser"

    def test_decode_invalid_token(self):
        from auth import decode_access_token
        payload = decode_access_token("invalid.token.here")
        assert payload is None

    def test_decode_expired_token(self):
        from auth import create_access_token, decode_access_token
        from unittest.mock import patch
        with patch("auth.settings.jwt_expire_minutes", -1):
            token = create_access_token(user_id=1, username="testuser")
        import time
        time.sleep(2)
        payload = decode_access_token(token)
        assert payload is None
"""单元测试 — 数据库操作"""
import os
import sys
import sqlite3
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("CHAT_API_KEY", "sk-test-key")


class TestDatabase:
    @pytest.fixture(autouse=True)
    def setup_db(self, tmp_path):
        import importlib
        import db as db_mod
        monkeypatch_db_path = str(tmp_path / "test_app.db")
        original_db_path = db_mod.settings.db_path
        db_mod.settings.db_path = monkeypatch_db_path
        importlib.reload(db_mod)
        from db import init_db, create_user, get_user_by_username, get_user_by_id, log_audit, query_audit_logs
        self.init_db = init_db
        self.create_user = create_user
        self.get_user_by_username = get_user_by_username
        self.get_user_by_id = get_user_by_id
        self.log_audit = log_audit
        self.query_audit_logs = query_audit_logs
        self.init_db()
        yield
        db_mod.settings.db_path = original_db_path

    def test_create_and_get_user(self):
        uid = self.create_user("testuser", "hashedpw123")
        assert uid > 0
        user = self.get_user_by_username("testuser")
        assert user is not None
        assert user["username"] == "testuser"

    def test_get_user_by_id(self):
        uid = self.create_user("byiduser", "hashedpw")
        user = self.get_user_by_id(uid)
        assert user is not None
        assert user["id"] == uid

    def test_duplicate_username(self):
        self.create_user("dupuser", "pw1")
        with pytest.raises(sqlite3.IntegrityError):
            self.create_user("dupuser", "pw2")

    def test_get_nonexistent_user(self):
        user = self.get_user_by_username("ghost")
        assert user is None

    def test_audit_log(self):
        self.log_audit("1", "chat", "/chat", "hello", "hi there", "127.0.0.1")
        logs = self.query_audit_logs()
        assert len(logs) == 1
        assert logs[0]["action"] == "chat"
        assert logs[0]["user_id"] == "1"

    def test_audit_log_filter(self):
        self.log_audit("1", "chat", "/chat", "hello", "hi", "127.0.0.1")
        self.log_audit("2", "upload", "/upload", "file.txt", "ok", "127.0.0.1")
        logs = self.query_audit_logs(user_id="1")
        assert all(l["user_id"] == "1" for l in logs)

        logs2 = self.query_audit_logs(action="upload")
        assert all(l["action"] == "upload" for l in logs2)

    def test_audit_log_limit_offset(self):
        for i in range(5):
            self.log_audit("1", "chat", "/chat", f"msg{i}", "", "127.0.0.1")
        logs = self.query_audit_logs(limit=2, offset=0)
        assert len(logs) == 2
"""路径遍历安全测试 — 验证 _safe_resolve 防御机制。"""

import pytest
from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient

from caisen.web.main import create_app, _safe_resolve


class TestSafeResolve:
    """_safe_resolve 函数单元测试。"""

    def test_normal_path_resolves(self, tmp_path):
        """正常文件名可以解析。"""
        (tmp_path / "valid_run").mkdir()
        result = _safe_resolve(tmp_path, "valid_run")
        assert result == (tmp_path / "valid_run").resolve()

    def test_dotdot_rejected(self, tmp_path):
        """包含 .. 的路径被拒绝。"""
        with pytest.raises(HTTPException) as exc_info:
            _safe_resolve(tmp_path, "../etc/passwd")
        assert exc_info.value.status_code == 400

    def test_slash_rejected(self, tmp_path):
        """包含 / 的路径被拒绝。"""
        with pytest.raises(HTTPException) as exc_info:
            _safe_resolve(tmp_path, "sub/dir")
        assert exc_info.value.status_code == 400

    def test_backslash_rejected(self, tmp_path):
        """包含 \\ 的路径被拒绝（Windows 风格）。"""
        with pytest.raises(HTTPException) as exc_info:
            _safe_resolve(tmp_path, "sub\\dir")
        assert exc_info.value.status_code == 400

    def test_path_escape_rejected(self, tmp_path):
        """即使没有 .. 但解析后逃逸出 base_dir 也被拒绝。"""
        # 构造一个 symlink 指向外部的场景（如果系统支持）
        external = tmp_path.parent / "external"
        external.mkdir(exist_ok=True)
        link = tmp_path / "escape_link"
        try:
            link.symlink_to(external)
        except (OSError, NotImplementedError):
            pytest.skip("系统不支持 symlink")
        # _safe_resolve 应检测到逃逸
        with pytest.raises(HTTPException) as exc_info:
            _safe_resolve(tmp_path, "escape_link")
        assert exc_info.value.status_code == 400


class TestApiPathTraversal:
    """通过 HTTP 端点测试路径遍历防护。"""

    @pytest.fixture
    def client(self):
        app = create_app()
        return TestClient(app)

    def test_get_run_rejects_dotdot(self, client):
        """GET /api/runs/../../../etc → 400。"""
        resp = client.get("/api/runs/..%2F..%2Fetc")
        assert resp.status_code in (400, 404, 422)

    def test_get_run_rejects_slash(self, client):
        """GET /api/runs/foo/bar → 404（FastAPI 路由不匹配）。"""
        resp = client.get("/api/runs/foo/bar")
        # FastAPI 路由不匹配斜杠内的路径，应返回 404 或 422
        assert resp.status_code in (400, 404, 422)

    def test_get_data_json_rejects_dotdot(self, client):
        """GET /api/runs/../data.json → 400。"""
        resp = client.get("/api/runs/../data.json")
        assert resp.status_code in (400, 404, 422)

    def test_get_js_rejects_dotdot(self, client):
        """GET /js/../../../etc/passwd → 400。"""
        resp = client.get("/js/..%2F..%2F..%2Fetc%2Fpasswd")
        assert resp.status_code in (400, 404, 422)

    def test_get_css_rejects_dotdot(self, client):
        """GET /src/css/../../../etc/passwd → 400。"""
        resp = client.get("/src/css/..%2F..%2F..%2Fetc%2Fpasswd")
        assert resp.status_code in (400, 404, 422)

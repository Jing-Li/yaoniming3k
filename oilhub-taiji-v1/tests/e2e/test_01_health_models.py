"""
E2E-01: 健康检查、版本、模型发现端点。

验证服务的辅助端点在真实 HTTP 调用下返回正确结构和内容。
"""
import pytest


class TestHealthEndpoint:

    def test_health_returns_200_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data == {"status": "ok"}

    def test_health_content_type_json(self, client):
        r = client.get("/health")
        assert "application/json" in r.headers["content-type"]


class TestVersionEndpoint:

    def test_version_returns_version_and_provider(self, client):
        r = client.get("/version")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data
        assert "provider" in data
        assert data["provider"] == "taiji"


class TestPropsEndpoints:

    @pytest.mark.parametrize("path", ["/props", "/v1/props"])
    def test_props_return_empty_object(self, client, path):
        r = client.get(path)
        assert r.status_code == 200
        assert r.json() == {}


class TestTagsEndpoint:

    def test_api_tags_returns_empty_models(self, client):
        r = client.get("/api/tags")
        assert r.status_code == 200
        assert r.json() == {"models": []}


class TestModelDiscovery:

    def test_list_models_returns_list_with_taiji(self, client):
        r = client.get("/v1/models")
        assert r.status_code == 200
        data = r.json()
        assert data["object"] == "list"
        assert isinstance(data["data"], list)
        assert any(m["id"] == "taiji" for m in data["data"])

    def test_list_models_each_has_required_fields(self, client):
        r = client.get("/v1/models")
        for m in r.json()["data"]:
            assert "id" in m
            assert m["object"] == "model"
            assert "created" in m
            assert "owned_by" in m
            assert "context_length" in m and m["context_length"] > 0
            assert "max_completion_tokens" in m and m["max_completion_tokens"] > 0

    def test_get_model_taiji(self, client):
        r = client.get("/v1/models/taiji")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "taiji"
        assert data["object"] == "model"

    def test_get_model_unknown_returns_404(self, client):
        r = client.get("/v1/models/gpt-999")
        assert r.status_code == 404
        data = r.json()
        assert "error" in data

    def test_api_v1_models_alias(self, client):
        r1 = client.get("/v1/models")
        r2 = client.get("/api/v1/models")
        assert r1.json()["object"] == r2.json()["object"]
        assert len(r1.json()["data"]) == len(r2.json()["data"])


class TestErrorEndpoints:

    def test_404_returns_openai_style(self, client):
        r = client.get("/v1/does-not-exist")
        assert r.status_code == 404
        data = r.json()
        assert "error" in data
        assert "message" in data["error"]
        assert "type" in data["error"]

    def test_405_method_not_allowed(self, client):
        r = client.delete("/v1/chat/completions")
        assert r.status_code == 405

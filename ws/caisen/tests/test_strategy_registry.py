"""测试 StrategyRegistry 策略注册表"""

from caisen.strategy.registry import StrategyRegistry


def test_discovers_builtin_strategies():
    """至少发现 CaiSenStrategy 和 MACrossStrategy 两个内置策略"""
    strategies = StrategyRegistry.list_strategies()
    names = [s["name"] for s in strategies]
    assert "CaiSenStrategy" in names
    assert "MACrossStrategy" in names


def test_llm_strategy_has_correct_type_and_note():
    """LLMStrategy 标记 type='llm' 并附带 note 说明"""
    strategies = StrategyRegistry.list_strategies()
    llm = next((s for s in strategies if s["name"] == "LLMStrategy"), None)
    assert llm is not None
    assert llm["type"] == "llm"
    assert llm["note"] is not None and len(llm["note"]) > 0


def test_import_error_is_silently_skipped(monkeypatch):
    """某策略模块导入失败时跳过该策略，不抛出异常，其他策略正常返回"""
    import importlib
    original_import = importlib.import_module

    def broken_import(name, *args, **kwargs):
        if "ma_cross" in name:
            raise ImportError("模拟导入失败")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", broken_import)

    strategies = StrategyRegistry.list_strategies()
    names = [s["name"] for s in strategies]

    # MACrossStrategy 被跳过，但其他策略正常
    assert "MACrossStrategy" not in names
    assert "CaiSenStrategy" in names


def test_api_strategies_endpoint():
    """GET /api/strategies 返回策略列表，包含必要字段"""
    from fastapi.testclient import TestClient
    import caisen.web.main as web_main

    client = TestClient(web_main.create_app())
    response = client.get("/api/strategies")

    assert response.status_code == 200
    body = response.json()
    assert "strategies" in body
    names = [s["name"] for s in body["strategies"]]
    assert "CaiSenStrategy" in names
    for s in body["strategies"]:
        assert "name" in s
        assert "display_name" in s
        assert "type" in s
        assert "note" in s
        assert "params_schema" in s

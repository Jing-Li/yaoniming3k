"""测试 LLMClient"""

import pytest
from unittest.mock import Mock, patch
import json

from caisen.strategy.llm.client import LLMClient, LLMResult


class TestLLMClientInterface:
    """LLMClient 接口测试"""

    def test_build_prompt_returns_string(self):
        """测试 build_prompt 返回字符串"""
        from caisen.strategy.llm.client import LLMClient

        client = LLMClient(provider_name="mock")
        bars = [{"timestamp": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 103}]

        prompt = client.build_prompt(bars)

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_parse_response_with_valid_data(self):
        """测试 parse_response 处理有效数据"""
        from caisen.strategy.llm.client import LLMClient

        client = LLMClient(provider_name="mock")
        response = json.dumps({
            "signals": [
                {"timestamp": "2024-01-01", "action": "buy", "confidence": 0.8}
            ],
            "annotations": []
        })

        result = client.parse_response(response)

        assert isinstance(result, LLMResult)
        assert len(result.signals) == 1


class TestLLMClientParsing:
    """LLMClient 解析测试"""

    def test_parse_json_response(self):
        """测试解析 JSON 响应"""
        from caisen.strategy.llm.client import LLMClient

        client = LLMClient(provider_name="mock")
        response = json.dumps({
            "signals": [
                {"timestamp": "2024-01-01", "action": "buy", "confidence": 0.8}
            ],
            "annotations": []
        })

        result = client.parse_response(response)

        assert len(result.signals) == 1
        assert result.signals[0]["action"] == "buy"

    def test_parse_invalid_json_raises_error(self):
        """测试解析无效 JSON 抛出异常"""
        from caisen.strategy.llm.client import LLMClient

        client = LLMClient(provider_name="mock")
        response = "not valid json"

        with pytest.raises(ValueError):
            client.parse_response(response)

    def test_parse_malformed_response_raises_error(self):
        """测试解析格式错误的响应（缺字段）"""
        from caisen.strategy.llm.client import LLMClient

        client = LLMClient(provider_name="mock")
        response = json.dumps({
            "signals": [
                {"timestamp": "2024-01-01"}  # 缺少 action
            ]
        })

        with pytest.raises(ValueError):
            client.parse_response(response)


class TestLLMResult:
    """LLMResult 数据结构测试"""

    def test_result_has_signals_and_annotations(self):
        """测试结果包含 signals 和 annotations"""
        from caisen.strategy.llm.client import LLMResult

        result = LLMResult(
            signals=[{"timestamp": "2024-01-01", "action": "buy"}],
            annotations=[{"timestamp": "2024-01-01", "type": "buy_signal", "data": {}}]
        )

        assert len(result.signals) == 1
        assert len(result.annotations) == 1

    def test_result_empty_lists(self):
        """测试空结果"""
        from caisen.strategy.llm.client import LLMResult

        result = LLMResult()

        assert result.signals == []
        assert result.annotations == []
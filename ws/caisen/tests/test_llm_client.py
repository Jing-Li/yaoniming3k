"""测试 LLMClient"""

import pytest
import json

from caisen.strategy.llm.client import LLMResult


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


class TestResponseParser:
    """ResponseParser 测试"""

    def test_parse_valid_response(self):
        """测试解析有效响应"""
        from caisen.strategy.llm.response import ResponseParser

        parser = ResponseParser()
        response = json.dumps({
            "signals": [
                {"timestamp": "2024-01-01", "action": "buy", "confidence": 0.8}
            ],
            "annotations": []
        })

        result = parser.parse(response)

        assert isinstance(result, LLMResult)
        assert len(result.signals) == 1
        assert result.signals[0]["action"] == "buy"

    def test_parse_response_with_annotations(self):
        """测试解析带标注的响应"""
        from caisen.strategy.llm.response import ResponseParser

        parser = ResponseParser()
        response = json.dumps({
            "signals": [
                {"timestamp": "2024-01-01", "action": "buy", "confidence": 0.8}
            ],
            "annotations": [
                {"timestamp": "2024-01-01", "type": "pattern_mark", "data": {"pattern": "W底"}}
            ]
        })

        result = parser.parse(response)

        assert len(result.signals) == 1
        assert len(result.annotations) == 1
        assert result.annotations[0]["type"] == "pattern_mark"

    def test_parse_invalid_json_raises_error(self):
        """测试解析无效 JSON 抛出异常"""
        from caisen.strategy.llm.response import ResponseParser

        parser = ResponseParser()
        response = "not valid json"

        with pytest.raises(ValueError):
            parser.parse(response)

    def test_parse_malformed_response_raises_error(self):
        """测试解析格式错误的响应（缺字段）"""
        from caisen.strategy.llm.response import ResponseParser

        parser = ResponseParser()
        response = json.dumps({
            "signals": [
                {"timestamp": "2024-01-01"}  # 缺少 action
            ]
        })

        with pytest.raises(ValueError):
            parser.parse(response)

    def test_parse_empty_response(self):
        """测试解析空响应"""
        from caisen.strategy.llm.response import ResponseParser

        parser = ResponseParser()
        response = json.dumps({
            "signals": [],
            "annotations": []
        })

        result = parser.parse(response)

        assert len(result.signals) == 0
        assert len(result.annotations) == 0

    def test_parse_raw(self):
        """测试解析原始 JSON"""
        from caisen.strategy.llm.response import ResponseParser

        parser = ResponseParser()
        data = {"signals": [], "annotations": []}
        response = json.dumps(data)

        result = parser.parse_raw(response)

        assert result == data
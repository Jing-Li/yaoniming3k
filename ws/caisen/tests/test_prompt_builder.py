"""测试 PromptBuilder"""

import pytest


class TestPromptBuilder:
    """PromptBuilder 测试"""

    def test_build_returns_string(self):
        """测试 build 返回字符串"""
        from caisen.strategy.llm.prompt import PromptBuilder

        builder = PromptBuilder()
        bars = [{"timestamp": "2024-01-01", "open": 100, "close": 103}]

        prompt = builder.build(bars)

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_build_includes_klines_data(self):
        """测试 Prompt 包含 K 线数据"""
        from caisen.strategy.llm.prompt import PromptBuilder

        builder = PromptBuilder()
        bars = [{"timestamp": "2024-01-01", "open": 100, "close": 103}]

        prompt = builder.build(bars)

        assert "2024-01-01" in prompt
        assert "100" in prompt

    def test_build_includes_output_format(self):
        """测试 Prompt 包含输出格式说明"""
        from caisen.strategy.llm.prompt import PromptBuilder

        builder = PromptBuilder()
        bars = [{"timestamp": "2024-01-01", "close": 103}]

        prompt = builder.build(bars)

        assert "signals" in prompt
        assert "annotations" in prompt

    def test_build_with_fewshot_examples(self):
        """测试带 Few-shot 示例的 Prompt"""
        from caisen.strategy.llm.prompt import PromptBuilder

        examples = [
            {
                "bars": [{"timestamp": "2024-01-01", "close": 100}, {"timestamp": "2024-01-02", "close": 105}],
                "signals": [{"timestamp": "2024-01-02", "action": "buy"}],
                "annotations": []
            }
        ]

        builder = PromptBuilder(examples=examples)
        bars = [{"timestamp": "2024-01-03", "close": 110}]

        prompt = builder.build(bars)

        assert "2024-01-01" in prompt  # 示例数据
        assert "2024-01-03" in prompt  # 实际数据

    def test_build_with_rules(self):
        """测试带规则框架的 Prompt"""
        from caisen.strategy.llm.prompt import PromptBuilder

        rules = "支撑位买入，阻力位卖出"

        builder = PromptBuilder(rules=rules)
        bars = [{"timestamp": "2024-01-01", "close": 103}]

        prompt = builder.build(bars)

        assert "支撑位" in prompt
        assert "阻力位" in prompt

    def test_build_with_empty_examples(self):
        """测试空示例列表"""
        from caisen.strategy.llm.prompt import PromptBuilder

        builder = PromptBuilder(examples=[])
        bars = [{"timestamp": "2024-01-01", "close": 103}]

        prompt = builder.build(bars)

        assert isinstance(prompt, str)


class TestPromptBuilderExamples:
    """PromptBuilder 示例测试"""

    def test_examples_format(self):
        """测试示例格式"""
        from caisen.strategy.llm.prompt import PromptBuilder

        examples = [
            {
                "bars": [
                    {"timestamp": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000},
                    {"timestamp": "2024-01-02", "open": 103, "high": 110, "low": 102, "close": 108, "volume": 1200}
                ],
                "signals": [{"timestamp": "2024-01-02", "action": "buy", "confidence": 0.8, "reason": "突破前高"}],
                "annotations": []
            }
        ]

        builder = PromptBuilder(examples=examples)
        prompt = builder.build([])

        # 验证示例被包含
        assert "2024-01-01" in prompt
        assert "buy" in prompt

    def test_multiple_examples(self):
        """测试多个示例"""
        from caisen.strategy.llm.prompt import PromptBuilder

        examples = [
            {"bars": [{"timestamp": "2024-01-01", "close": 100}], "signals": [], "annotations": []},
            {"bars": [{"timestamp": "2024-01-02", "close": 105}], "signals": [], "annotations": []}
        ]

        builder = PromptBuilder(examples=examples)
        prompt = builder.build([])

        # 验证两个示例都包含
        assert prompt.count("示例") >= 2
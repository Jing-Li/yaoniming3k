"""测试 Prompt 进化器"""

import pytest
from unittest.mock import Mock

from caisen.strategy.llm.evolver import PromptEvolver, quick_evolution, EvolutionResult
from caisen.strategy.llm.client import LLMResult


class MockLLMClient:
    """模拟 LLM 客户端"""

    def __init__(self, responses=None):
        self.responses = responses or [
            '{"signals": [{"timestamp": "2024-01-01", "action": "buy"}, {"timestamp": "2024-01-03", "action": "sell"}], "annotations": []}'
        ]
        self.call_count = 0

    def call_llm(self, prompt: str) -> str:
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response

    def parse_response(self, response: str):
        import json
        data = json.loads(response)
        return LLMResult(
            signals=data.get('signals', []),
            annotations=data.get('annotations', [])
        )


class TestPromptEvolver:
    """Prompt 进化器测试"""

    def test_evolution_initialization(self):
        """测试进化器初始化"""
        client = MockLLMClient()
        bars = [
            {'timestamp': '2024-01-01', 'close': 100},
            {'timestamp': '2024-01-02', 'close': 102},
            {'timestamp': '2024-01-03', 'close': 105},
        ]

        evolver = PromptEvolver(
            llm_client=client,
            bars=bars,
            max_iterations=3
        )

        assert evolver.max_iterations == 3
        assert len(evolver.history) == 0

    def test_evolution_run(self):
        """测试进化运行"""
        client = MockLLMClient()
        bars = [
            {'timestamp': '2024-01-01', 'close': 100},
            {'timestamp': '2024-01-02', 'close': 102},
            {'timestamp': '2024-01-03', 'close': 105},
        ]

        evolver = PromptEvolver(
            llm_client=client,
            bars=bars,
            max_iterations=2
        )

        result = evolver.evolve()

        assert isinstance(result, EvolutionResult)
        assert result.iteration >= 1
        assert len(evolver.history) >= 1

    def test_evaluation(self):
        """测试评估逻辑"""
        client = MockLLMClient()
        bars = [
            {'timestamp': '2024-01-01', 'close': 100},
            {'timestamp': '2024-01-02', 'close': 102},
            {'timestamp': '2024-01-03', 'close': 105},
        ]

        evolver = PromptEvolver(
            llm_client=client,
            bars=bars,
            max_iterations=1
        )

        signals = [
            {'timestamp': '2024-01-01', 'action': 'buy'},
            {'timestamp': '2024-01-03', 'action': 'sell'}
        ]

        score, trades = evolver._evaluate(signals)

        assert isinstance(score, float)
        assert len(trades) >= 0

    def test_rule_improvement(self):
        """测试规则改进"""
        client = MockLLMClient()
        bars = [{'timestamp': '2024-01-01', 'close': 100}]

        evolver = PromptEvolver(
            llm_client=client,
            bars=bars,
            max_iterations=1
        )

        # 测试亏损场景
        rules = evolver._improve_rules("买入", -0.1, [])

        assert "止损" in rules or "追高" in rules

    def test_quick_evolution(self):
        """测试快速进化"""
        client = MockLLMClient()
        bars = [
            {'timestamp': '2024-01-01', 'close': 100},
            {'timestamp': '2024-01-02', 'close': 102},
        ]

        result = quick_evolution(client, bars, iterations=2)

        assert 'best_score' in result
        assert 'best_prompt' in result
        assert 'history' in result

    def test_empty_signals(self):
        """测试空信号"""
        client = MockLLMClient()
        bars = [{'timestamp': '2024-01-01', 'close': 100}]

        evolver = PromptEvolver(
            llm_client=client,
            bars=bars,
            max_iterations=1
        )

        score, trades = evolver._evaluate([])

        assert score == 0.0
        assert trades == []


class TestEvolutionResult:
    """EvolutionResult 测试"""

    def test_result_creation(self):
        """测试结果创建"""
        result = EvolutionResult(
            iteration=1,
            score=0.5,
            prompt="测试规则",
            signals=[],
            trades=[]
        )

        assert result.iteration == 1
        assert result.score == 0.5
        assert result.prompt == "测试规则"
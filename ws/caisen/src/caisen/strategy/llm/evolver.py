"""LLM Prompt 进化器 - 通过测试反馈优化 Prompt"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from .prompt import PromptBuilder
from .client import LLMClient, LLMResult


@dataclass
class EvolutionResult:
    """进化结果"""
    iteration: int
    score: float  # 评分（越高越好）
    prompt: str
    signals: List[Dict]
    trades: List[Dict]  # 模拟交易
    improvement: float = 0.0  # 相对上次的提升


class PromptEvolver:
    """Prompt 进化器

    通过测试反馈自动优化 Prompt：
    1. 初始化基础 Prompt
    2. 运行测试，评估结果
    3. 根据评分调整规则
    4. 重复直到收敛或达到最大迭代
    """

    def __init__(
        self,
        llm_client: LLMClient,
        bars: List[Dict],
        max_iterations: int = 5,
        target_score: float = 0.0
    ):
        """初始化

        Args:
            llm_client: LLM 客户端
            bars: K 线数据
            max_iterations: 最大迭代次数
            target_score: 目标评分（达到后停止）
        """
        self.llm_client = llm_client
        self.bars = bars
        self.max_iterations = max_iterations
        self.target_score = target_score

        self.history: List[EvolutionResult] = []
        self.best_result: Optional[EvolutionResult] = None

    def evolve(
        self,
        initial_rules: str = "",
        initial_examples: List[Dict] = None
    ) -> EvolutionResult:
        """开始进化

        Args:
            initial_rules: 初始规则框架
            initial_examples: 初始示例

        Returns:
            最佳进化结果
        """
        current_rules = initial_rules or "支撑位买入，阻力位卖出"

        for i in range(self.max_iterations):
            # 构建 Prompt
            prompt_builder = PromptBuilder(
                rules=current_rules,
                examples=initial_examples or []
            )

            # 调用 LLM
            prompt = prompt_builder.build(self.bars)
            response = self.llm_client.call_llm(prompt)
            result = self.llm_client.parse_response(response)

            # 评估结果
            score, trades = self._evaluate(result.signals)

            # 记录历史
            improvement = score - (self.best_result.score if self.best_result else 0)

            evolution_result = EvolutionResult(
                iteration=i + 1,
                score=score,
                prompt=current_rules,
                signals=result.signals,
                trades=trades,
                improvement=improvement
            )
            self.history.append(evolution_result)

            if self.best_result is None or score > self.best_result.score:
                self.best_result = evolution_result

            # 输出进度
            print(f"  迭代 {i+1}: score={score:.4f}, improvement={improvement:.4f}")

            # 检查是否达到目标
            if score >= self.target_score:
                print(f"  达到目标评分 {self.target_score}，停止")
                break

            # 根据评分调整规则
            if i < self.max_iterations - 1:
                current_rules = self._improve_rules(current_rules, score, result.signals)

        return self.best_result

    def _evaluate(self, signals: List[Dict]) -> tuple:
        """评估信号质量

        Args:
            signals: LLM 返回的信号列表

        Returns:
            (评分, 模拟交易列表)
        """
        if not signals:
            return 0.0, []

        # 简单评分逻辑
        score = 0.0
        trades = []
        position = 0  # 0=空仓, 1=持仓
        entry_price = 0

        for i, bar in enumerate(self.bars):
            ts = bar.get('timestamp', '')

            # 查找对应信号
            signal = next((s for s in signals if s.get('timestamp') == ts), None)
            if not signal:
                continue

            action = signal.get('action', 'hold')

            # 模拟交易
            if action == 'buy' and position == 0:
                position = 1
                entry_price = bar.get('close', 0)
                trades.append({
                    'timestamp': ts,
                    'type': 'BUY',
                    'price': entry_price
                })
            elif action == 'sell' and position == 1:
                exit_price = bar.get('close', 0)
                pnl = (exit_price - entry_price) / entry_price if entry_price > 0 else 0
                score += pnl
                trades.append({
                    'timestamp': ts,
                    'type': 'SELL',
                    'price': exit_price,
                    'pnl': pnl
                })
                position = 0

        # 评分：盈利交易加分，亏损扣分
        # 同时考虑交易频率（避免过度交易）
        trade_count = len(trades) / 2  # 买入+卖出=1笔完整交易
        if trade_count > 0:
            avg_score = score / trade_count
            # 交易太频繁扣分
            frequency_penalty = max(0, (trade_count - len(self.bars) / 20) * 0.01)
            score = avg_score - frequency_penalty

        return score, trades

    def _improve_rules(self, current_rules: str, score: float, signals: List[Dict]) -> str:
        """根据评分改进规则

        Args:
            current_rules: 当前规则
            score: 当前评分
            signals: 信号列表

        Returns:
            改进后的规则
        """
        # 分析信号特征
        buy_count = sum(1 for s in signals if s.get('action') == 'buy')
        sell_count = sum(1 for s in signals if s.get('action') == 'sell')
        hold_count = sum(1 for s in signals if s.get('action') == 'hold')

        # 基于反馈调整
        improvements = []

        if score < 0:
            # 亏损：减少买入信号，添加更多止损条件
            improvements.append("注意止损，避免追高")

        if buy_count > len(self.bars) * 0.2:
            # 买入太频繁：降低交易频率
            improvements.append("只在明确的买入信号时操作")

        if sell_count > buy_count * 2:
            # 卖出太多：避免过早卖出
            improvements.append("趋势确认后再卖出")

        if hold_count > len(self.bars) * 0.7:
            # 观望太多：适当参与
            improvements.append("有明确机会时果断操作")

        if improvements:
            return current_rules + "\n" + "\n".join(improvements)

        return current_rules

    def get_best_prompt(self) -> str:
        """获取最佳 Prompt"""
        if self.best_result:
            return self.best_result.prompt
        return ""

    def get_history(self) -> List[EvolutionResult]:
        """获取进化历史"""
        return self.history

    def save_results(self, path: str) -> None:
        """保存进化结果"""
        data = {
            'best_score': self.best_result.score if self.best_result else 0,
            'best_prompt': self.best_result.prompt if self.best_result else "",
            'history': [
                {
                    'iteration': r.iteration,
                    'score': r.score,
                    'prompt': r.prompt,
                    'trades_count': len(r.trades)
                }
                for r in self.history
            ]
        }
        with open(path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def quick_evolution(
    llm_client: LLMClient,
    bars: List[Dict],
    iterations: int = 3
) -> Dict[str, Any]:
    """快速进化测试

    Args:
        llm_client: LLM 客户端
        bars: K 线数据
        iterations: 迭代次数

    Returns:
        最佳结果
    """
    evolver = PromptEvolver(
        llm_client=llm_client,
        bars=bars,
        max_iterations=iterations
    )

    print(f"开始 Prompt 进化测试 ({iterations} 次迭代)...")

    result = evolver.evolve()

    print(f"\n最佳评分: {result.score:.4f}")
    print(f"最优 Prompt:\n{result.prompt[:200]}...")

    return {
        'best_score': result.score,
        'best_prompt': result.prompt,
        'history': evolver.get_history()
    }
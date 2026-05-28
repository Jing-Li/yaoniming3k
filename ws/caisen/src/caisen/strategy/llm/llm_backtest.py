"""LLM 蔡森形态策略回测

测试 LLM 生成的交易信号胜率
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 隔离 openai 导入
sys.modules['caisen.strategy.llm.openai'] = None  # 阻止相对导入
import openai

# 添加项目路径
sys.path.insert(0, '/home/user/yaoniming3k/ws/caisen/src')

from caisen.data.local_source import LocalDataSource
from caisen.data.config import DataConfig


class LLMAnalyzer:
    """LLM 分析器"""

    def __init__(self, base_url: str = "http://localhost:8080/v1", model: str = "taiji"):
        import openai as _openai
        self.client = _openai.OpenAI(api_key="dummy", base_url=base_url)
        self.model = model

        # 加载蔡森模板
        from caisen.strategy.llm.prompts.caisen_pattern import (
            SYSTEM_PROMPT, RULES_FRAMEWORK, OUTPUT_FORMAT, EXAMPLES_TEMPLATE
        )
        self.system_prompt = SYSTEM_PROMPT
        self.rules = RULES_FRAMEWORK
        self.examples = EXAMPLES_TEMPLATE
        self.output_format = OUTPUT_FORMAT

    def analyze(self, bars: List) -> Dict[str, Any]:
        """分析 K 线数据"""
        bars_json = json.dumps([
            {
                "timestamp": bar.timestamp.strftime("%Y-%m-%d %H:%M"),
                "open": round(bar.open, 2),
                "high": round(bar.high, 2),
                "low": round(bar.low, 2),
                "close": round(bar.close, 2),
                "volume": round(bar.volume, 0)
            }
            for bar in bars
        ], ensure_ascii=False)

        prompt = f"""{self.system_prompt}

{self.rules}

{self.examples}

{self.output_format}

## 分析任务

请分析以下 K 线数据，输出交易信号和标注：

{bars_json}
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个蔡森形态技术分析专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4096
        )

        result = response.choices[0].message.content

        # 解析 JSON
        json_str = result
        if "```json" in result:
            json_str = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            parts = result.split("```")
            if len(parts) >= 3:
                json_str = parts[1]
            else:
                # 尝试直接解析
                json_str = result

        # 清理可能的 markdown 格式
        json_str = json_str.strip()
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Raw response: {result[:500]}")
            return {"signals": [], "annotations": []}


class SimpleBacktester:
    """简单回测器"""

    def __init__(self, initial_capital: float = 100000, commission: float = 0.0003):
        self.initial_capital = initial_capital
        self.commission = commission
        self.capital = initial_capital
        self.position = 0  # 0=空仓, 1=持仓
        self.entry_price = 0
        self.trades = []

    def reset(self):
        self.capital = self.initial_capital
        self.position = 0
        self.entry_price = 0
        self.trades = []

    def execute_signal(self, bar, action: str, confidence: float):
        """执行信号"""
        if action == "buy" and self.position == 0 and confidence >= 0.7:
            # 买入
            cost = self.capital * 0.95  # 使用 95% 资金
            shares = cost / bar.close
            commission_cost = shares * bar.close * self.commission
            self.capital -= shares * bar.close + commission_cost
            self.position = shares
            self.entry_price = bar.close
            self.trades.append({
                "type": "BUY",
                "timestamp": bar.timestamp,
                "price": bar.close,
                "shares": shares,
                "confidence": confidence
            })
            return True

        elif action == "sell" and self.position > 0:
            # 卖出
            revenue = self.position * bar.close
            commission_cost = revenue * self.commission
            self.capital += revenue - commission_cost
            pnl = (bar.close - self.entry_price) / self.entry_price * 100
            self.trades.append({
                "type": "SELL",
                "timestamp": bar.timestamp,
                "price": bar.close,
                "shares": self.position,
                "pnl_pct": pnl
            })
            self.position = 0
            self.entry_price = 0
            return True

        return False

    def run(self, bars: List, signals: List[Dict]) -> Dict:
        """运行回测"""
        self.reset()

        # 建立信号索引
        signal_map = {}
        for sig in signals:
            ts = sig.get("timestamp", "")
            if isinstance(ts, str):
                # 精确匹配
                signal_map[ts] = sig

        # 回放
        for bar in bars:
            ts = bar.timestamp.strftime("%Y-%m-%d %H:%M")
            sig = signal_map.get(ts)

            if sig:
                self.execute_signal(bar, sig.get("action", "hold"), sig.get("confidence", 0))

        # 平仓（如果有持仓）
        if self.position > 0 and bars:
            last_bar = bars[-1]
            self.execute_signal(last_bar, "sell", 0)

        # 计算统计
        winning_trades = [t for t in self.trades if t["type"] == "SELL" and t.get("pnl_pct", 0) > 0]
        total_trades = len([t for t in self.trades if t["type"] == "SELL"])

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        return {
            "initial_capital": self.initial_capital,
            "final_capital": self.capital,
            "total_return": (self.capital - self.initial_capital) / self.initial_capital * 100,
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "win_rate": win_rate,
            "trades": self.trades
        }


def main():
    # 配置
    from caisen.config.project_config import ProjectConfig
    DATA_DIR = ProjectConfig.load().data_dir
    SYMBOL = "ag"
    FREQ = "60m"
    START = "2026-01-05"
    END = "2026-04-30"

    # 加载数据
    print("Loading data...")
    data_config = DataConfig(
        symbol=SYMBOL,
        freq=FREQ,
        start=START,
        end=END,
        data_dir=DATA_DIR
    )
    data_source = LocalDataSource(DATA_DIR)
    bars = data_source.load(data_config)
    print(f"Loaded {len(bars)} bars")

    # 初始化分析器
    analyzer = LLMAnalyzer()

    # 分段分析（每段 50 根 K 线，避免 token 过多）
    all_signals = []
    window_size = 50
    overlap = 10  # 重叠 10 根以确保连续性

    for i in range(0, len(bars), window_size - overlap):
        end_idx = min(i + window_size, len(bars))
        window_bars = bars[i:end_idx]

        print(f"\nAnalyzing bars {i} to {end_idx} ({len(window_bars)} bars)...")

        result = analyzer.analyze(window_bars)
        signals = result.get("signals", [])
        print(f"  Got {len(signals)} signals, {sum(1 for s in signals if s.get('action')=='buy')} buy signals")

        # 跳过重叠部分的信号（避免重复）
        if i > 0:
            # 只保留重叠后的新信号
            signals = signals[overlap:] if len(signals) > overlap else []

        all_signals.extend(signals)

        if end_idx >= len(bars):
            break

    print(f"\n=== Total signals: {len(all_signals)} ===")

    # 过滤有效信号
    buy_signals = [s for s in all_signals if s.get("action") == "buy" and s.get("confidence", 0) >= 0.7]
    sell_signals = [s for s in all_signals if s.get("action") == "sell"]
    print(f"Buy signals (conf >= 0.7): {len(buy_signals)}")
    print(f"Sell signals: {len(sell_signals)}")

    # 运行回测
    print("\n=== Running backtest ===")
    backtester = SimpleBacktester(initial_capital=100000)
    stats = backtester.run(bars, all_signals)

    print(f"\n=== Backtest Results ===")
    print(f"Initial capital: {stats['initial_capital']:.2f}")
    print(f"Final capital: {stats['final_capital']:.2f}")
    print(f"Total return: {stats['total_return']:.2f}%")
    print(f"Total trades: {stats['total_trades']}")
    print(f"Winning trades: {stats['winning_trades']}")
    print(f"Win rate: {stats['win_rate']*100:.1f}%")

    if stats['trades']:
        print("\n=== Trade Details ===")
        for i, trade in enumerate(stats['trades'][:10]):  # 只显示前 10 笔
            if trade['type'] == 'SELL':
                print(f"  Trade {i+1}: {trade['type']} @ {trade['price']:.2f}, PnL: {trade.get('pnl_pct', 0):.2f}%")

    # 保存结果
    output_path = Path("./runs/llm_caisen_test")
    output_path.mkdir(parents=True, exist_ok=True)

    result_data = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "symbol": SYMBOL,
            "freq": FREQ,
            "start": START,
            "end": END,
            "window_size": window_size
        },
        "stats": stats,
        "signals": all_signals[:100]  # 保存前 100 个信号
    }

    result_file = output_path / f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: {result_file}")


if __name__ == "__main__":
    main()
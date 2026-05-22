#!/usr/bin/env python3
"""批量测试 LLM 信号 + 回测胜率"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/user/yaoniming3k/ws/caisen/src')

from caisen.data.local_source import LocalDataSource
from caisen.data.config import DataConfig

# 配置
DATA_DIR = "/home/user/data"
SYMBOL = "ag"
FREQ = "60m"
START = "2026-01-05"
END = "2026-04-30"

# 读取 prompt
prompt_file = Path('/home/user/yaoniming3k/ws/caisen/src/caisen/strategy/llm/prompts/caisen_pattern.py')
with open(prompt_file, 'r') as f:
    content = f.read()

sys_match = re.search(r'SYSTEM_PROMPT = """(.*?)"""', content, re.DOTALL)
rules_match = re.search(r'RULES_FRAMEWORK = """(.*?)"""', content, re.DOTALL)
output_match = re.search(r'OUTPUT_FORMAT = """(.*?)"""', content, re.DOTALL)
examples_match = re.search(r'EXAMPLES_TEMPLATE = """(.*?)"""', content, re.DOTALL)

SYSTEM_PROMPT = sys_match.group(1).strip() if sys_match else ""
RULES_FRAMEWORK = rules_match.group(1).strip() if rules_match else ""
OUTPUT_FORMAT = output_match.group(1).strip() if output_match else ""
EXAMPLES_TEMPLATE = examples_match.group(1).strip() if examples_match else ""

# 加载数据
data_config = DataConfig(symbol=SYMBOL, freq=FREQ, start=START, end=END, data_dir=DATA_DIR)
data_source = LocalDataSource(DATA_DIR)
bars = data_source.load(data_config)
print(f"Loaded {len(bars)} bars from {bars[0].timestamp} to {bars[-1].timestamp}")

# 分段分析（每段 50 根，重叠 10 根）
window_size = 50
overlap = 10
all_signals = []

import openai
client = openai.OpenAI(api_key="dummy", base_url="http://localhost:8080/v1")

for i in range(0, len(bars), window_size - overlap):
    end_idx = min(i + window_size, len(bars))
    window = bars[i:end_idx]

    print(f"\nAnalyzing bars {i}-{end_idx} ({len(window)} bars)...")

    bars_json = json.dumps([{
        "timestamp": b.timestamp.strftime("%Y-%m-%d %H:%M"),
        "open": round(b.open, 2), "high": round(b.high, 2),
        "low": round(b.low, 2), "close": round(b.close, 2),
        "volume": round(b.volume, 0)
    } for b in window], ensure_ascii=False)

    prompt = f"""{SYSTEM_PROMPT}

{RULES_FRAMEWORK}

{EXAMPLES_TEMPLATE}

{OUTPUT_FORMAT}

## 分析任务

{bars_json}
"""

    try:
        response = client.chat.completions.create(
            model="taiji",
            messages=[
                {"role": "system", "content": "你是一个蔡森形态技术分析专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3, max_tokens=4096
        )
        result = response.choices[0].message.content

        # 解析
        json_str = result
        if "```json" in result:
            json_str = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            json_str = result.split("```")[1].split("```")[0]

        signals = json.loads(json_str)
        window_signals = signals.get('signals', [])

        # 跳过重叠部分
        if i > 0:
            window_signals = window_signals[overlap:] if len(window_signals) > overlap else []

        all_signals.extend(window_signals)
        buy_count = sum(1 for s in window_signals if s.get('action') == 'buy')
        print(f"  Got {len(window_signals)} signals, {buy_count} buy signals")

    except Exception as e:
        print(f"  Error: {e}")
        continue

    if end_idx >= len(bars):
        break

print(f"\n=== Total: {len(all_signals)} signals ===")

# 统计
buy_signals = [s for s in all_signals if s.get('action') == 'buy']
sell_signals = [s for s in all_signals if s.get('action') == 'sell']
print(f"Buy: {len(buy_signals)}, Sell: {len(sell_signals)}, Hold: {len(all_signals) - len(buy_signals) - len(sell_signals)}")

# 简单回测
class SimpleBacktester:
    def __init__(self, capital=100000, commission=0.0003):
        self.capital = capital
        self.commission = commission
        self.position = 0
        self.entry_price = 0
        self.trades = []

    def run(self, bars, signals):
        signal_map = {s.get('timestamp'): s for s in signals}
        for bar in bars:
            ts = bar.timestamp.strftime("%Y-%m-%d %H:%M")
            sig = signal_map.get(ts, {})
            action = sig.get('action', 'hold')
            conf = sig.get('confidence', 0)

            if action == 'buy' and self.position == 0 and conf >= 0.70:
                cost = self.capital * 0.95
                shares = cost / bar.close
                commission_cost = shares * bar.close * self.commission
                self.capital -= shares * bar.close + commission_cost
                self.position = shares
                self.entry_price = bar.close
                self.trades.append({"type": "BUY", "time": ts, "price": bar.close, "conf": conf})

            elif action == 'sell' and self.position > 0:
                revenue = self.position * bar.close
                commission_cost = revenue * self.commission
                self.capital += revenue - commission_cost
                pnl = (bar.close - self.entry_price) / self.entry_price * 100
                self.trades.append({"type": "SELL", "time": ts, "price": bar.close, "pnl": pnl})
                self.position = 0

        # 平仓
        if self.position > 0 and bars:
            last = bars[-1]
            revenue = self.position * last.close
            self.capital += revenue - revenue * self.commission
            pnl = (last.close - self.entry_price) / self.entry_price * 100
            self.trades.append({"type": "SELL", "time": last.timestamp, "price": last.close, "pnl": pnl})
            self.position = 0

        return self.capital, self.trades

print("\n=== Running Backtest ===")
bt = SimpleBacktester(100000)
final_capital, trades = bt.run(bars, all_signals)

sell_trades = [t for t in trades if t['type'] == 'SELL']
winning = [t for t in sell_trades if t.get('pnl', 0) > 0]
win_rate = len(winning) / len(sell_trades) if sell_trades else 0

print(f"\n=== Backtest Results ===")
print(f"Initial: 100000")
print(f"Final: {final_capital:.2f}")
print(f"Return: {(final_capital - 100000) / 100000 * 100:.2f}%")
print(f"Total Trades: {len(sell_trades)}")
print(f"Winning: {len(winning)}")
print(f"Win Rate: {win_rate * 100:.1f}%")

if winning:
    print("\n=== Winning Trades ===")
    for t in winning[:5]:
        print(f"  {t['time']}: price={t['price']:.2f}, pnl={t['pnl']:.2f}%")

# 保存结果
result = {
    "timestamp": datetime.now().isoformat(),
    "config": {"symbol": SYMBOL, "freq": FREQ, "start": START, "end": END},
    "final_capital": final_capital,
    "return_pct": (final_capital - 100000) / 100000 * 100,
    "total_trades": len(sell_trades),
    "win_rate": win_rate * 100,
    "signals": all_signals[:100]
}

output_path = Path(f"/home/user/yaoniming3k/ws/caisen/runs/llm_caisen_test/backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\nSaved to: {output_path}")
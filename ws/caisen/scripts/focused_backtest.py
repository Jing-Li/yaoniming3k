#!/usr/bin/env python3
"""分段验证回测 - 快速计算胜率"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/home/user/yaoniming3k/ws/caisen/src')

from caisen.data.local_source import LocalDataSource
from caisen.data.config import DataConfig

DATA_DIR = "/home/user/data"

# 读取 prompt
prompt_file = Path('/home/user/yaoniming3k/ws/caisen/src/caisen/strategy/llm/prompts/caisen_pattern.py')
with open(prompt_file, 'r') as f:
    content = f.read()

import re
sys_match = re.search(r'SYSTEM_PROMPT = """(.*?)"""', content, re.DOTALL)
rules_match = re.search(r'RULES_FRAMEWORK = """(.*?)"""', content, re.DOTALL)
output_match = re.search(r'OUTPUT_FORMAT = """(.*?)"""', content, re.DOTALL)
examples_match = re.search(r'EXAMPLES_TEMPLATE = """(.*?)"""', content, re.DOTALL)

SYSTEM_PROMPT = sys_match.group(1).strip() if sys_match else ""
RULES_FRAMEWORK = rules_match.group(1).strip() if rules_match else ""
OUTPUT_FORMAT = output_match.group(1).strip() if output_match else ""
EXAMPLES_TEMPLATE = examples_match.group(1).strip() if examples_match else ""

# 加载数据
data_config = DataConfig(symbol="ag", freq="60m", start="2026-01-05", end="2026-04-30", data_dir=DATA_DIR)
data_source = LocalDataSource(DATA_DIR)
bars = data_source.load(data_config)

import openai
client = openai.OpenAI(api_key="dummy", base_url="http://localhost:8080/v1")

def analyze_segment(segment_bars):
    """分析一段K线数据"""
    bars_json = json.dumps([{
        "timestamp": b.timestamp.strftime("%Y-%m-%d %H:%M"),
        "open": round(b.open, 2), "high": round(b.high, 2),
        "low": round(b.low, 2), "close": round(b.close, 2),
        "volume": round(b.volume, 0)
    } for b in segment_bars], ensure_ascii=False)

    prompt = f"""{SYSTEM_PROMPT}

{RULES_FRAMEWORK}

{EXAMPLES_TEMPLATE}

{OUTPUT_FORMAT}

## 分析任务

{bars_json}
"""

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
    return signals.get('signals', [])

# 分段测试 - 选择几个有代表性的区间
# 区间1: 0-100 (2026-01-05 至 2026-01-20 左右)
# 区间2: 200-300 (2026-02-10 至 2026-02-25 左右)
# 区间3: 300-400 (2026-02-25 至 2026-03-10 左右) - 已测试，有W底
# 区间4: 500-600 (2026-03-25 至 2026-04-10 左右)
# 区间5: 650-750 (2026-04-10 至 2026-04-30 左右)

segments = [
    (0, 100, "Segment 1: Early Jan"),
    (200, 300, "Segment 2: Mid Feb"),
    (500, 600, "Segment 4: Late Mar"),
    (650, 750, "Segment 5: Apr"),
]

all_signals = []
all_trades = []

for start, end, name in segments:
    segment_bars = bars[start:end]
    print(f"\n{'='*60}")
    print(f"Analyzing {name}: {segment_bars[0].timestamp} to {segment_bars[-1].timestamp}")
    print(f"{'='*60}")

    signals = analyze_segment(segment_bars)

    # 简单回测逻辑
    position = 0
    entry_price = 0
    entry_time = None

    for i, bar in enumerate(segment_bars):
        ts = bar.timestamp.strftime("%Y-%m-%d %H:%M")
        sig = signals[i] if i < len(signals) else {"action": "hold", "confidence": 0}
        action = sig.get('action', 'hold')
        conf = sig.get('confidence', 0)

        if action == 'buy' and position == 0 and conf >= 0.70:
            position = 1
            entry_price = bar.close
            entry_time = ts
            print(f"  BUY  @ {ts}: price={bar.close:.2f}, conf={conf:.2f}")

        elif action == 'sell' and position > 0:
            pnl = (bar.close - entry_price) / entry_price * 100
            position = 0
            all_trades.append({
                "segment": name,
                "entry_time": entry_time,
                "entry_price": entry_price,
                "exit_time": ts,
                "exit_price": bar.close,
                "pnl": pnl
            })
            result = "WIN" if pnl > 0 else "LOSS"
            print(f"  SELL @ {ts}: price={bar.close:.2f}, pnl={pnl:.2f}% [{result}]")

    # 强制平仓
    if position > 0:
        last_bar = segment_bars[-1]
        pnl = (last_bar.close - entry_price) / entry_price * 100
        all_trades.append({
            "segment": name,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "exit_time": last_bar.timestamp.strftime("%Y-%m-%d %H:%M"),
            "exit_price": last_bar.close,
            "pnl": pnl
        })
        result = "WIN" if pnl > 0 else "LOSS"
        print(f"  SELL @ {last_bar.timestamp}: price={last_bar.close:.2f}, pnl={pnl:.2f}% [{result}] (forced)")

    all_signals.extend(signals)

# 汇总
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")

winning_trades = [t for t in all_trades if t['pnl'] > 0]
losing_trades = [t for t in all_trades if t['pnl'] <= 0]
win_rate = len(winning_trades) / len(all_trades) * 100 if all_trades else 0

print(f"Total Trades: {len(all_trades)}")
print(f"Winning: {len(winning_trades)}")
print(f"Losing: {len(losing_trades)}")
print(f"Win Rate: {win_rate:.1f}%")

if all_trades:
    avg_pnl = sum(t['pnl'] for t in all_trades) / len(all_trades)
    print(f"Avg PnL: {avg_pnl:.2f}%")

print("\n=== All Trades ===")
for t in all_trades:
    result = "WIN" if t['pnl'] > 0 else "LOSS"
    print(f"  {t['segment']}: {t['entry_time']} -> {t['exit_time']}, PnL={t['pnl']:.2f}% [{result}]")

# 保存
output = {
    "timestamp": datetime.now().isoformat(),
    "win_rate": win_rate,
    "total_trades": len(all_trades),
    "winning": len(winning_trades),
    "losing": len(losing_trades),
    "trades": all_trades
}

output_path = Path(f"/home/user/yaoniming3k/ws/caisen/runs/llm_caisen_test/focused_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
with open(output_path, 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\nSaved to: {output_path}")

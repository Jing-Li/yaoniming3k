#!/usr/bin/env python3
"""快速验证 LLM Prompt 效果"""
import json
import sys
from pathlib import Path

sys.path.insert(0, '/home/user/yaoniming3k/ws/caisen/src')

from caisen.data.local_source import LocalDataSource
from caisen.data.config import DataConfig

# 配置
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

# 加载数据 - 只取一小段测试
data_config = DataConfig(symbol="ag", freq="60m", start="2026-01-05", end="2026-04-30", data_dir=DATA_DIR)
data_source = LocalDataSource(DATA_DIR)
bars = data_source.load(data_config)

# 取中间一段有波动的数据（约100根K线）
test_bars = bars[300:400]
print(f"Testing with {len(test_bars)} bars from {test_bars[0].timestamp} to {test_bars[-1].timestamp}")

bars_json = json.dumps([{
    "timestamp": b.timestamp.strftime("%Y-%m-%d %H:%M"),
    "open": round(b.open, 2), "high": round(b.high, 2),
    "low": round(b.low, 2), "close": round(b.close, 2),
    "volume": round(b.volume, 0)
} for b in test_bars], ensure_ascii=False)

prompt = f"""{SYSTEM_PROMPT}

{RULES_FRAMEWORK}

{EXAMPLES_TEMPLATE}

{OUTPUT_FORMAT}

## 分析任务

{bars_json}
"""

import openai
client = openai.OpenAI(api_key="dummy", base_url="http://localhost:8080/v1")

print("\nSending request to LLM...")
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

print(f"\n=== Results ===")
print(f"Total signals: {len(window_signals)}")

buy_signals = [s for s in window_signals if s.get('action') == 'buy']
sell_signals = [s for s in window_signals if s.get('action') == 'sell']
print(f"Buy: {len(buy_signals)}, Sell: {len(sell_signals)}, Hold: {len(window_signals) - len(buy_signals) - len(sell_signals)}")

if buy_signals:
    print("\n=== Buy Signals ===")
    for s in buy_signals[:5]:
        print(f"  {s['timestamp']}: conf={s.get('confidence', 0):.2f}, reason={s.get('reason', 'N/A')[:60]}...")

if sell_signals:
    print("\n=== Sell Signals ===")
    for s in sell_signals[:5]:
        print(f"  {s['timestamp']}: reason={s.get('reason', 'N/A')[:60]}...")

# 保存结果
output = {
    "test_range": f"{test_bars[0].timestamp} to {test_bars[-1].timestamp}",
    "signals": window_signals,
    "raw_response": result[:2000]  # 截断
}

output_path = Path("/home/user/yaoniming3k/ws/caisen/runs/llm_caisen_test/quick_verify.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\nSaved to: {output_path}")

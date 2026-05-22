#!/usr/bin/env python3
"""Quick LLM Test - 放在项目根目录运行"""
import json
import re
import sys

# 先临时移除 llm 模块避免冲突
if 'caisen.strategy.llm' in sys.modules:
    del sys.modules['caisen.strategy.llm']

sys.path.insert(0, '/home/user/yaoniming3k/ws/caisen/src')

from caisen.data.local_source import LocalDataSource
from caisen.data.config import DataConfig
from pathlib import Path

# 配置
DATA_DIR = "/home/user/data"
SYMBOL = "ag"
FREQ = "60m"

# 加载数据
data_config = DataConfig(symbol=SYMBOL, freq=FREQ, data_dir=DATA_DIR)
data_source = LocalDataSource(DATA_DIR)
bars = data_source.load(data_config)
print(f"Loaded {len(bars)} bars")

# 读取 prompt
prompt_file = Path('/home/user/yaoniming3k/ws/caisen/src/caisen/strategy/llm/prompts/caisen_pattern.py')
with open(prompt_file, 'r') as f:
    content = f.read()

# 提取
sys_match = re.search(r'SYSTEM_PROMPT = """(.*?)"""', content, re.DOTALL)
rules_match = re.search(r'RULES_FRAMEWORK = """(.*?)"""', content, re.DOTALL)
output_match = re.search(r'OUTPUT_FORMAT = """(.*?)"""', content, re.DOTALL)
examples_match = re.search(r'EXAMPLES_TEMPLATE = """(.*?)"""', content, re.DOTALL)

SYSTEM_PROMPT = sys_match.group(1).strip() if sys_match else ""
RULES_FRAMEWORK = rules_match.group(1).strip() if rules_match else ""
OUTPUT_FORMAT = output_match.group(1).strip() if output_match else ""
EXAMPLES_TEMPLATE = examples_match.group(1).strip() if examples_match else ""

# 取最近 40 根
sample = bars[-40:] if len(bars) > 40 else bars
bars_json = json.dumps([{
    "timestamp": b.timestamp.strftime("%Y-%m-%d %H:%M"),
    "open": round(b.open, 2), "high": round(b.high, 2),
    "low": round(b.low, 2), "close": round(b.close, 2),
    "volume": round(b.volume, 0)
} for b in sample], ensure_ascii=False)

prompt = f"""{SYSTEM_PROMPT}

{RULES_FRAMEWORK}

{EXAMPLES_TEMPLATE}

{OUTPUT_FORMAT}

## 分析任务

{bars_json}
"""

print(f"Prompt length: {len(prompt)} chars")

# 调用 LLM
import openai
client = openai.OpenAI(api_key="dummy", base_url="http://localhost:8080/v1")

print("Calling LLM...")
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
    print(f"\nLLM Response (first 2000 chars):\n{result[:2000]}")

    # 解析
    json_str = result
    if "```json" in result:
        json_str = result.split("```json")[1].split("```")[0]
    elif "```" in result:
        json_str = result.split("```")[1].split("```")[0]

    signals = json.loads(json_str)
    print(f"\n=== Signals Summary ===")
    print(f"Total: {len(signals.get('signals', []))}")
    buy = [s for s in signals.get('signals', []) if s.get('action') == 'buy']
    sell = [s for s in signals.get('signals', []) if s.get('action') == 'sell']
    print(f"Buy: {len(buy)}, Sell: {len(sell)}")

    if buy:
        print("\n=== Buy Signals ===")
        for s in buy[:5]:
            print(f"  {s.get('timestamp')}: conf={s.get('confidence')}, reason={s.get('reason', '')[:80]}")

    # 保存
    output_path = Path("/home/user/yaoniming3k/ws/caisen/runs/llm_caisen_test/last_signals.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(signals, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to: {output_path}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
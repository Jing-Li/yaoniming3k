#!/usr/bin/env python3
"""Standalone LLM Prompt Test - 不依赖 caisen 包"""

import json
import re
from datetime import datetime
from pathlib import Path
import sys

# 配置
LOCAL_LLM_URL = "http://localhost:8080/v1"
MODEL = "taiji"
DATA_DIR = "/home/user/data"
SYMBOL = "ag"
FREQ = "60m"
START = "2026-01-05"
END = "2026-04-30"

# 添加项目路径
sys.path.insert(0, '/home/user/yaoniming3k/ws/caisen/src')

# 加载数据
from caisen.data.local_source import LocalDataSource
from caisen.data.config import DataConfig

data_config = DataConfig(
    symbol=SYMBOL,
    freq=FREQ,
    start=START,
    end=END,
    data_dir=DATA_DIR
)
data_source = LocalDataSource(DATA_DIR)
bars = data_source.load(data_config)

print(f"Loaded {len(bars)} bars for {SYMBOL} ({FREQ})")
print(f"Date range: {bars[0].timestamp} to {bars[-1].timestamp}")

# 直接读取 prompt 文件
prompt_file = Path('/home/user/yaoniming3k/ws/caisen/src/caisen/strategy/llm/prompts/caisen_pattern.py')
with open(prompt_file, 'r') as f:
    content = f.read()

# 提取 prompt 内容
sys_match = re.search(r'SYSTEM_PROMPT = """(.*?)"""', content, re.DOTALL)
rules_match = re.search(r'RULES_FRAMEWORK = """(.*?)"""', content, re.DOTALL)
output_match = re.search(r'OUTPUT_FORMAT = """(.*?)"""', content, re.DOTALL)
examples_match = re.search(r'EXAMPLES_TEMPLATE = """(.*?)"""', content, re.DOTALL)

SYSTEM_PROMPT = sys_match.group(1).strip() if sys_match else ""
RULES_FRAMEWORK = rules_match.group(1).strip() if rules_match else ""
OUTPUT_FORMAT = output_match.group(1).strip() if output_match else ""
EXAMPLES_TEMPLATE = examples_match.group(1).strip() if examples_match else ""

# 限制数据量（取最近 50 根）
sample_bars = bars[-50:] if len(bars) > 50 else bars

bars_json = json.dumps([
    {
        "timestamp": bar.timestamp.strftime("%Y-%m-%d %H:%M"),
        "open": round(bar.open, 2),
        "high": round(bar.high, 2),
        "low": round(bar.low, 2),
        "close": round(bar.close, 2),
        "volume": round(bar.volume, 0)
    }
    for bar in sample_bars
], ensure_ascii=False, indent=2)

# 组装完整 prompt
prompt = f"""{SYSTEM_PROMPT}

{RULES_FRAMEWORK}

{EXAMPLES_TEMPLATE}

{OUTPUT_FORMAT}

## 分析任务

请分析以下 K 线数据，输出交易信号和标注：

{bars_json}
"""

print(f"\nPrompt length: {len(prompt)} chars")

# 调用本地 LLM - 使用 __import__ 避免模块名冲突
openai = __import__('openai')

client = openai.OpenAI(
    api_key="dummy",
    base_url=LOCAL_LLM_URL
)

print("\nCalling LLM...")
try:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是一个蔡森形态技术分析专家。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=4096
    )

    result = response.choices[0].message.content
    print("\n=== LLM Response ===")
    print(result[:3000] if len(result) > 3000 else result)

    # 解析 JSON
    try:
        json_str = result
        if "```json" in result:
            json_str = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            json_str = result.split("```")[1].split("```")[0]

        signals_data = json.loads(json_str)
        print(f"\n=== Parsed Signals ===")
        print(f"Total signals: {len(signals_data.get('signals', []))}")

        buy_signals = [s for s in signals_data.get('signals', []) if s.get('action') == 'buy']
        sell_signals = [s for s in signals_data.get('signals', []) if s.get('action') == 'sell']
        hold_signals = [s for s in signals_data.get('signals', []) if s.get('action') == 'hold']
        print(f"Buy signals: {len(buy_signals)}")
        print(f"Sell signals: {len(sell_signals)}")
        print(f"Hold signals: {len(hold_signals)}")

        # 保存结果
        output_path = Path("/home/user/yaoniming3k/ws/caisen/runs/llm_caisen_test") / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_signals.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(signals_data, f, ensure_ascii=False, indent=2)
        print(f"\nSignals saved to: {output_path}")

        # 打印买入信号详情
        if buy_signals:
            print("\n=== Buy Signals Detail ===")
            for i, sig in enumerate(buy_signals[:5], 1):
                print(f"  {i}. {sig.get('timestamp')}: confidence={sig.get('confidence')}, reason={sig.get('reason', '')[:60]}...")

    except json.JSONDecodeError as e:
        print(f"\nFailed to parse JSON: {e}")
        print(f"Raw response: {result[:500]}")

except Exception as e:
    print(f"\nError calling LLM: {e}")
    import traceback
    traceback.print_exc()
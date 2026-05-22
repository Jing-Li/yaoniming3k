"""LLM 蔡森形态策略测试脚本

使用本地 LLM 分析 K 线数据，输出蔡森形态信号
"""

import json
import os
from datetime import datetime
from pathlib import Path

# 配置
LOCAL_LLM_URL = "http://localhost:8080/v1"
MODEL = "taiji"
DATA_DIR = "/home/user/data"
SYMBOL = "ag"
FREQ = "60m"
START = "2026-01-05"
END = "2026-04-30"

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

# 构建 Prompt
from caisen.strategy.llm.prompts.caisen_pattern import (
    SYSTEM_PROMPT,
    RULES_FRAMEWORK,
    OUTPUT_FORMAT,
    EXAMPLES_TEMPLATE
)

# 限制数据量以避免 token 过多（取最近 100 根）
sample_bars = bars[-100:] if len(bars) > 100 else bars

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

# 调用本地 LLM
import sys
# 避免导入本地的 openai.py
if 'caisen.strategy.llm.openai' in sys.modules:
    del sys.modules['caisen.strategy.llm.openai']
from openai import OpenAI

client = OpenAI(
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
    print(result[:2000] if len(result) > 2000 else result)

    # 解析 JSON
    try:
        # 提取 JSON 部分
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
        print(f"Buy signals: {len(buy_signals)}")
        print(f"Sell signals: {len(sell_signals)}")

        # 保存结果
        output_path = Path("./runs/llm_caisen_test") / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_signals.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(signals_data, f, ensure_ascii=False, indent=2)
        print(f"\nSignals saved to: {output_path}")

    except json.JSONDecodeError as e:
        print(f"\nFailed to parse JSON: {e}")
        print(f"Raw response: {result[:500]}")

except Exception as e:
    print(f"\nError calling LLM: {e}")
    import traceback
    traceback.print_exc()
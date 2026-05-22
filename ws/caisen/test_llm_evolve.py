"""快速测试 Prompt 进化"""

from caisen.strategy.llm import OpenAIProvider, quick_evolution

# 测试数据
bars = [
    {"timestamp": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000},
    {"timestamp": "2024-01-02", "open": 103, "high": 108, "low": 102, "close": 106, "volume": 1100},
    {"timestamp": "2024-01-03", "open": 106, "high": 110, "low": 105, "close": 108, "volume": 1200},
    {"timestamp": "2024-01-04", "open": 108, "high": 112, "low": 107, "close": 110, "volume": 1300},
    {"timestamp": "2024-01-05", "open": 110, "high": 108, "low": 103, "close": 105, "volume": 1400},
]

print("=" * 50)
print("Prompt 进化测试")
print("=" * 50)

# 创建 LLM 客户端
client = OpenAIProvider(
    api_key="dummy",
    model="taiji",
    base_url="http://localhost:8080/v1"
)

# 快速进化
result = quick_evolution(client, bars, iterations=3)

print(f"\n最佳评分: {result['best_score']:.4f}")
print(f"最优 Prompt:\n{result['best_prompt']}")
print("=" * 50)
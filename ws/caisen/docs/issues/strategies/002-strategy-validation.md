# Strategy Issue: 策略验证机制缺失

## Priority
**Critical** - 安全隐患

## Problem
LLM 生成的策略代码执行前缺少安全验证：
- ❌ 无 AST 解析检查
- ❌ 无危险 imports 黑名单
- ❌ 无执行超时限制
- ❌ 无沙箱隔离

## Impact
- 恶意或错误的策略代码可能破坏系统
- LLM 可能生成危险代码（如 `os.system()`, `requests`）
- 无限循环导致程序卡死

## Reference
- **Architecture Review**: 2026-05-15
- **Related Code**: `src/caisen/strategy/llm_strategy.py`

## Recommended Fix
实现策略验证层：

```python
class StrategyValidator:
    DANGEROUS_IMPORTS = {"os", "sys", "subprocess", "requests", ...}
    ALLOWED_IMPORTS = {"math", "datetime", "random", ...}

    def validate(self, code: str) -> ValidationResult:
        # 1. AST 解析
        tree = ast.parse(code)

        # 2. 检查 imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in self.ALLOWED_IMPORTS:
                        return ValidationResult(safe=False, reason=f"Disallowed import: {alias.name}")

        # 3. 检查危险函数调用
        # 4. 返回结果
```

## Acceptance Criteria
- [ ] AST 解析检查语法正确性
- [ ] 危险 imports 黑名单拦截
- [ ] 允许 imports 白名单定义
- [ ] 执行超时机制
- [ ] 验证失败的明确错误信息
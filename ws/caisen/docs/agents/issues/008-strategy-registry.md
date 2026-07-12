# StrategyRegistry：策略注册表 + `/api/strategies`

- **ID**: 008
- **标签**: enhancement, closed
- **优先级**: HIGH
- **状态**: closed (2026-05-26)

## Parent

[#004 PRD: 前端触发回测 + 项目全局配置](004-frontend-backtest-trigger.md)

## What to build

新建 `StrategyRegistry` 模块，动态扫描 `strategy/algorithm/` 和 `strategy/llm/` 目录，发现可实例化的 `Strategy` 子类，并为每个策略提取参数 schema（名称、类型、默认值、范围）。

扫描时防御性处理导入错误——某个策略文件有语法错误时跳过，不影响整体列表。

同时在 Web 服务中新增 `GET /api/strategies` 端点。

响应格式：
```json
{
  "strategies": [
    {
      "name": "CaiSenStrategy",
      "display_name": "蔡森策略",
      "type": "code",
      "note": null,
      "params_schema": [
        {
          "name": "stop_loss_factor",
          "type": "float",
          "default": 0.95,
          "min": 0.90,
          "max": 1.00,
          "options": null
        }
      ]
    },
    {
      "name": "LLMStrategy",
      "display_name": "LLM 策略",
      "type": "llm",
      "note": "需要服务器端预先配置 API Key",
      "params_schema": []
    }
  ]
}
```

## Acceptance criteria

- [x] `StrategyRegistry` 模块存在，可返回策略列表
- [x] 至少发现 `CaiSenStrategy` 和 `LLMStrategy` 两个内置策略
- [x] LLM 策略标记 `type: "llm"` 并附带 `note` 说明
- [x] `params_schema` 从 `__init__` 签名提取（float/int/bool/str 四种类型）
- [x] 某策略导入失败时跳过该策略，不抛出异常
- [x] `GET /api/strategies` 端点存在，返回规定 JSON 格式
- [x] `StrategyRegistry` 有 4 个单元测试，全部通过

## Blocked by

- [#005 ProjectConfig：全局配置加载模块](005-project-config.md)

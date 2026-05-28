# DataSourceScanner：数据目录扫描 + `/api/data-sources`

- **ID**: 007
- **标签**: enhancement, closed
- **优先级**: HIGH
- **状态**: closed (2026-05-26)

## Parent

[#004 PRD: 前端触发回测 + 项目全局配置](004-frontend-backtest-trigger.md)

## What to build

新建 `DataSourceScanner` 模块，扫描 `data_dir/{symbol}/{freq}/` 目录结构，返回本地可用行情数据列表。日期范围通过读取 Parquet 文件名推断（不读文件内容，保持扫描快速）。

同时在 Web 服务中新增 `GET /api/data-sources` 端点，返回扫描结果供前端下拉菜单使用。

响应格式：
```json
{
  "data_sources": [
    {
      "symbol": "000001.SZ",
      "freq": "1d",
      "date_range": { "start": "2022-01-04", "end": "2024-12-31" }
    }
  ]
}
```

`data_dir` 为空或不存在时返回空列表，不报错。

## Acceptance criteria

- [x] `DataSourceScanner` 模块存在，可接受 `data_dir` 路径参数
- [x] 正确解析 `{data_dir}/{symbol}/{freq}/` 三级目录结构
- [x] 日期范围从 Parquet 文件名推断（实际格式 `YYYYMMDD_YYYYMMDD.parquet`），不读文件内容
- [x] `data_dir` 不存在或为空时返回空列表
- [x] `GET /api/data-sources` 端点存在，返回规定 JSON 格式
- [x] 端点使用 `_project_config.data_dir` 读取（来自 ProjectConfig）
- [x] `DataSourceScanner` 有 4 个单元测试，全部通过

## Blocked by

- [#005 ProjectConfig：全局配置加载模块](005-project-config.md)

# ProjectConfig：全局配置加载模块

- **ID**: 005
- **标签**: enhancement, closed
- **优先级**: HIGH
- **状态**: closed (2026-05-26)

## Parent

[#004 PRD: 前端触发回测 + 项目全局配置](004-frontend-backtest-trigger.md)

## What to build

新建 `ProjectConfig` 模块，从 `configs/project.yaml` 读取项目级全局配置（`data_dir`、`output_dir`、`api_port`），并将其集成到 Web 服务和 CLI 启动流程中，消除现有代码中的硬编码路径。

优先级顺序：内嵌默认值 < `configs/project.yaml`。`project.yaml` 不存在时静默降级，不报错，保持向后兼容。

同时新建 `configs/project.yaml` 模板文件（含注释说明），以及更新 `web/main.py` 的 `set_output_dir` 和 `data_dir` 注入方式，使两者都从 `ProjectConfig` 读取。

默认值：
- `data_dir`: `/home/user/data`
- `output_dir`: `./runs`
- `api_port`: `8001`

## Acceptance criteria

- [x] `ProjectConfig` 模块存在并可从 `configs/project.yaml` 读取三个字段
- [x] `project.yaml` 不存在时返回内嵌默认值，无异常
- [x] `project.yaml` 中部分字段缺失时，缺失字段使用默认值
- [x] `web/main.py` 启动时自动从 `ProjectConfig` 读取 `output_dir` 和 `data_dir`，不再使用硬编码
- [x] `cli/main.py` 中两处 `data_dir="/home/user/data"` 改为从 `ProjectConfig` 读取
- [x] `strategy/llm/llm_backtest.py` 中 `DATA_DIR` 硬编码改为从 `ProjectConfig` 读取
- [x] `configs/project.yaml` 模板文件存在，含字段说明注释
- [x] 现有命令行回测流程不受影响（所有现有测试通过）
- [x] `ProjectConfig` 有单元测试覆盖上述三种读取场景

## Blocked by

None — can start immediately.

# PRD: 前端触发回测 + 项目全局配置

- **ID**: 004
- **标签**: enhancement, closed
- **优先级**: HIGH
- **状态**: closed (2026-05-26)

---

## Problem Statement

用户目前只能通过命令行（`caisen run --strategy ... --symbol ...`）触发回测，无法在浏览器中选择策略和行情数据直接发起回测。同时，行情数据目录（`data_dir`）在多处硬编码为 `/home/user/data`，换机器或换数据目录时需要手动修改源码，维护成本高。

## Solution

在前端（`index.html` 入口页）新增"新建回测"面板，用户可以：

1. 从下拉菜单选择内置策略或 LLM 策略（动态扫描策略目录）
2. 从下拉菜单选择行情数据（自动扫描本地 data_dir 目录，列出 symbol + freq 组合）
3. 填写时间范围（start / end）
4. 填写动态参数表单（后端按策略返回参数 schema，前端动态渲染）
5. 点击"开始回测"，通过 WebSocket 实时查看进度（每 100 根 K 线推送一次）
6. 回测完成后自动跳转到 `report.html?run_id=xxx` 查看结果

与此同时，引入项目级全局配置文件 `configs/project.yaml`，统一管理 `data_dir`、`output_dir`、`api_port`，消除代码中的硬编码路径。原有策略配置文件迁移至 `configs/strategies/` 子目录。

## User Stories

1. 作为量化交易者，我希望在浏览器中看到所有可用策略的列表，这样我不需要查看源码就能知道有哪些策略可以选择。
2. 作为量化交易者，我希望在浏览器中看到本地已下载的行情数据列表（按 symbol + freq 分组），这样我可以直接点选而不需要记忆路径。
3. 作为量化交易者，我希望在选择策略后看到该策略的可调参数和默认值，这样我可以在跑回测前调整参数。
4. 作为量化交易者，我希望填写回测的开始和结束日期，这样我可以指定分析的时间窗口。
5. 作为量化交易者，我希望点击"开始回测"后看到实时进度条（每 100 根 K 线更新一次），这样我知道回测在进行中而不是卡死了。
6. 作为量化交易者，我希望回测完成后自动跳转到报告页，这样不需要手动去 runs 列表里找结果。
7. 作为量化交易者，我希望回测失败时在页面上看到错误信息，这样我知道是参数错误还是数据缺失。
8. 作为系统管理员，我希望通过 `configs/project.yaml` 统一配置数据目录和输出目录，这样换机器或换路径时不需要修改源码。
9. 作为系统管理员，我希望 `project.yaml` 不存在时系统仍能正常运行（使用内嵌默认值），这样首次安装无需手动创建配置文件。
10. 作为策略开发者，我希望策略配置文件集中放在 `configs/strategies/` 目录，这样和项目全局配置文件区分清晰。
11. 作为量化交易者，我希望前端动态展示的策略列表能够区分代码策略和 LLM 策略，这样我知道 LLM 策略需要服务器预先配置 API Key。
12. 作为量化交易者，我希望在回测进行中可以看到当前正在处理的日期，这样能感知到进度的实际位置。
13. 作为量化交易者，我希望已有的命令行回测流程不受任何影响，这样迁移期间不会打断现有工作流。

## Implementation Decisions

### 模块划分

#### 新增模块

**1. ProjectConfig 配置加载模块（后端）**

- 负责从项目根目录的 `configs/project.yaml` 读取全局配置
- 读取优先级：内嵌默认值 < `project.yaml`（CLI 参数未来可覆盖）
- 以单例模式提供，在 Web 服务和 CLI 启动时各加载一次
- 字段：`data_dir`（默认 `/home/user/data`）、`output_dir`（默认 `./runs`）、`api_port`（默认 `8001`）
- `project.yaml` 不存在时静默降级到默认值，不报错

**2. StrategyRegistry 策略注册表（后端）**

- 动态扫描 `strategy/algorithm/` 和 `strategy/llm/` 目录，发现可实例化的 Strategy 子类
- 返回策略列表：`[{name, display_name, type: "code"|"llm", params_schema}]`
- `params_schema` 描述每个参数的类型、默认值、可选范围（用于前端动态表单渲染）
- LLM 策略附带说明："需要服务器端预先配置 API Key"

**3. DataSourceScanner 数据源扫描模块（后端）**

- 扫描 `data_dir/{symbol}/{freq}/` 目录结构
- 返回可用数据源列表：`[{symbol, freq, date_range: {start, end}}]`
- `date_range` 通过读取 Parquet 文件名推断（不读文件内容，保持快速）

**4. BacktestRunner 回测执行模块（后端）**

- 接收回测参数（策略名、symbol、freq、start、end、params）
- 调用 `BacktestEngine` 运行回测
- 每处理 100 根 K 线，通过回调推送进度事件
- 结果通过 `ResultPersister` 持久化，返回 `run_id`
- 与 WebSocket 解耦：只负责运行和回调，不直接操作 WebSocket

**5. 前端"新建回测"面板（frontend）**

- 新增在 `index.html` 入口页，与现有 runs 列表并列
- 表单组件：策略下拉、数据源下拉、日期选择器、动态参数表单区
- WebSocket 进度展示：进度条 + 当前处理日期 + 已处理 K 线数
- 错误状态展示：连接失败、策略报错、数据缺失分别给出明确提示

#### 修改模块

**6. Web 服务路由扩展（`web/main.py`）**

新增 API 端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/strategies` | 返回可用策略列表 + 参数 schema |
| GET | `/api/data-sources` | 返回可用数据源列表 |
| POST | `/api/runs` | 接收回测参数，同步触发，返回 `{run_id}` |
| WS | `/ws/runs/{run_id}/progress` | 推送回测进度，完成时推送 `{status: "done", run_id}` |

**7. CLI 硬编码路径清理**

- `cli/main.py` 中 `data_dir="/home/user/data"` 两处，改为读取 ProjectConfig
- `strategy/llm/llm_backtest.py` 中 `DATA_DIR` 硬编码，改为读取 ProjectConfig

**8. configs 目录重组**

- 现有 7 个策略 YAML 文件迁移至 `configs/strategies/`
- 新建 `configs/project.yaml` 作为项目全局配置模板

### WebSocket 协议

消息格式（JSON）：

```
// 进度消息（每 100 根推送一次）
{status: "running", processed: 300, total: 1200, current_date: "2024-03-15"}

// 完成消息
{status: "done", run_id: "CaiSenStrategy_20240526_001"}

// 错误消息
{status: "error", message: "数据不足，无法运行回测"}
```

### 参数 Schema 格式

后端返回的策略参数描述格式：

```
{
  name: "stop_loss_factor",
  type: "float",          // float | int | bool | select
  default: 0.95,
  min: 0.90,             // 仅 float/int 有
  max: 1.00,
  options: null          // select 类型时为选项列表
}
```

### 读取优先级

`内嵌默认值` → `configs/project.yaml` → （未来：CLI 参数）

## Testing Decisions

**测试原则**：只测外部行为（API 返回值、文件是否生成、WebSocket 消息序列），不测内部实现细节（函数调用顺序、内部变量）。

**需要测试的模块**：

1. **ProjectConfig**
   - `project.yaml` 存在时正确读取字段
   - `project.yaml` 不存在时返回内嵌默认值
   - 字段部分缺失时，缺失字段使用默认值
   - 参考：`tests/test_equity_final.py`（数据类行为测试风格）

2. **DataSourceScanner**
   - 空目录返回空列表
   - 标准 `{symbol}/{freq}/` 目录结构正确解析出 symbol 和 freq
   - 日期范围从文件名推断正确
   - 参考：现有数据加载测试

3. **BacktestRunner**
   - 正常回测流程：进度回调被调用、返回有效 `run_id`
   - 数据不足时抛出明确异常（不是静默失败）
   - 参考：`tests/test_equity_final.py`（使用 mock bars 数据）

4. **Web API（集成测试）**
   - `GET /api/strategies` 返回非空列表且包含 `params_schema`
   - `GET /api/data-sources` 在扫描空目录时返回空列表，扫描有数据目录时返回正确结构
   - `POST /api/runs` 成功时返回有效 `run_id`，参数错误时返回 422
   - 参考：FastAPI TestClient，参考现有 web/main.py 路由结构

**不测试的内容**：
- WebSocket 实时推送的时序（集成测试难以稳定复现）
- 前端 JS 表单渲染逻辑（由手动测试覆盖）

## Out of Scope

- LLM 策略 API Key 的前端配置界面（Key 由服务器端环境变量管理）
- 回测参数持久化（不保存用户上次填写的表单状态）
- 多任务并发回测（同一时刻只允许一个回测在运行）
- 回测进度的中断/取消功能
- 行情数据的自动下载（仅扫描本地已有数据）
- 策略热加载（需重启服务才能发现新策略）
- 移动端适配（前端新增面板仅针对桌面端）

## Further Notes

- WebSocket 在 FastAPI 中原生支持（`websockets` 依赖），无需引入额外库
- `BacktestRunner` 与 WebSocket 解耦设计允许未来改为后台任务队列（Celery/arq）而不改动回测核心逻辑
- `StrategyRegistry` 的动态扫描应防御性处理导入错误（某个策略文件有语法错误时不影响整体列表）
- 策略 YAML 迁移至 `configs/strategies/` 后，需同步更新文档和 README 中的路径引用

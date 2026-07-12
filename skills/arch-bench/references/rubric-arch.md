# Architecture Score Rubric

评估 skill 管线产出的**代码和架构产物**质量。每轮由 `/arch-review` 执行。

## 评分维度（各 20 分，满分 100）

### 1. 架构边界合规性 (20)

| 分数 | 标准 |
|------|------|
| 20 | 零违反：domain 无 import，port 只定义接口，app 不暴露基础设施细节 |
| 15 | 1-2 处轻微违反（如 port 出现具体类型依赖） |
| 10 | 3-5 处违反，但洋葱圈核心（domain→port）未被破坏 |
| 5 | 依赖方向大面积反转，domain 引用了 infra 或 app |
| 0 | 无分层或分层形同虚设 |

**检查清单：**
- `domain/` 目录 import 链只包含标准库？
- `port/` 只定义接口，无具体实现？
- `app/` 只 import `domain/` + `port/`？
- `infra/` 实现 port 接口，无业务逻辑泄漏？

### 2. 需求覆盖率 (20)

| 分数 | 标准 |
|------|------|
| 20 | 100% game_rules 被映射到代码 + 测试 |
| 15 | 90%+ 覆盖，缺少 1-2 个边缘 case |
| 10 | 70-90%，有完整功能缺失 |
| 5 | 50-70%，核心功能不完整 |
| 0 | <50% 或完全未实现 |

**检查清单：**
- combo 机制是否完整实现？
- 3 种 powerup 是否都存在且行为正确？
- 状态机 4 态 + 5 转换是否完备？
- 排行榜 Top 10 + replay 回放是否可用？

### 3. 产物一致性 (20)

| 分数 | 标准 |
|------|------|
| 20 | BRD → ARCHITECTURE → DESIGN → Code 完全一致，无断裂 |
| 15 | 轻微偏差（如 BRD 描述和代码行为有 1-2 处不同步） |
| 10 | 中等偏差（如 ADR 决策未在代码中体现） |
| 5 | 严重断裂（如 DESIGN.md 描述的模块在代码中不存在） |
| 0 | 各层产物互不相关 |

**检查清单：**
- BRD 中的业务术语是否出现在代码命名中？
- ARCHITECTURE.md 声明的边界是否与代码目录对应？
- DESIGN.md 定义的接口签名是否与 port/ 一致？
- ADR 决策是否在代码中落地？

### 4. 测试覆盖与质量 (20)

| 分数 | 标准 |
|------|------|
| 20 | TDD 可追溯（红→绿→重构），核心路径 100% 覆盖 |
| 15 | 有完整测试，但 TDD 追溯性弱 |
| 10 | 部分模块有测试，边缘 case 缺失 |
| 5 | 只有 happy path 测试 |
| 0 | 无测试或测试不通过 |

**检查清单：**
- domain 纯函数是否有单元测试？
- combo / powerup / 碰撞 是否有边界 case 测试？
- port 接口是否有 mock 测试？
- 测试命名是否表达业务意图？

### 5. 代码质量 (20)

| 分数 | 标准 |
|------|------|
| 20 | 无 lint error，命名语义清晰，零 code smell |
| 15 | 1-3 处 minor smell（如过长函数、重复代码） |
| 10 | 有 lint error 但代码功能正确 |
| 5 | 严重 code smell（God Object、状态泄漏） |
| 0 | 无法编译或运行 |

**检查清单：**
- `go vet` / `staticcheck` 是否通过？
- 是否有超过 100 行的函数？
- 是否有超过 5 个参数的函数？
- 是否有硬编码常量（应该来自 bench.yaml）？

## 变异测试（Mutation Test）

bench.yaml 中定义了 5 个故意引入的架构陷阱。`/arch-review` 和 `/arch-critic` 必须能检测出来：

| # | 陷阱 | 预期被谁检测 |
|---|------|-------------|
| M1 | 蛇移动逻辑引用 `time.Now()` | arch-review (domain 纯度检查) |
| M2 | combo 计时用 `time.Since()` 而非 tick 差 | arch-critic (架构决策审查) |
| M3 | PowerUp 用 `time.Timer` 管理持续时间 | devtdd (测试失败) + arch-review |
| M4 | Replay 记录包含 UI 事件（按键） | arch-review (关注点分离检查) |
| M5 | Board 使用 Active Record 模式 | arch-critic (Clean Architecture 一致性) |

**变异检测评分**：每检测到 1 个 +4 分（包含在总分 100 中，作为 bonus），全部漏掉则扣 Architecture Score 10 分。

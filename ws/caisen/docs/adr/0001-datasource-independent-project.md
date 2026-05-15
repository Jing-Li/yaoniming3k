# 数据源模块独立为 caisen-data 项目

回测系统的数据源实现（akshare、tushare 等）独立为单独的 Python 项目（caisen-data），通过 Entry Points 插件机制注册到 caisen。

**为什么**：回测引擎本身不依赖具体数据源，保持轻量。数据源实现依赖繁重（多种外部 API），单独维护可以独立发布节奏，也避免强制用户安装不需要的数据源。

**替代方案考虑**：
- 合并到 caisen 同一项目 —— 导致强制依赖，用户必须接受所有数据源
- 子命令模式 —— 不够灵活，无法按需选择数据源

**后果**：用户需要安装两个包才能完整使用：`pip install caisen caisen-data`。
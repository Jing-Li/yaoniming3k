# Slice 4: 配置系统 + `/v1/models`

Status: needs-triage

## 架构澄清

**openclaw 是客户端，不是后端。** 本 provider 只对接 **taiji 一个后端**。

## What to build

引入配置系统（YAML/JSON 配置文件或环境变量），支持：
- 为每个 provider 配置 base_url、api_key、可用模型列表等
- 无需改代码即可增删 provider（为未来扩展预留）

提供 `GET /v1/models` 返回所有已注册 provider 的可用模型列表（OpenAI 格式）。当前仅注册 taiji。

## Acceptance criteria

- [ ] `GET /v1/models` 返回包含所有已注册 provider 模型的列表
- [ ] provider 参数（URL、key、模型映射）通过配置文件或环境变量管理
- [ ] 新增后端 provider 只需添加配置 + 实现 `BaseProvider` 子类
- [ ] 配置热加载或至少重启生效

## Blocked by

- `.scratch/openai-provider/issues/03-provider-abstraction-hermes.md`

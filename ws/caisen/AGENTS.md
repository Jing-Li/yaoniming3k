## Agent skills

### Issue tracker

Issues are tracked as local Markdown files in `docs/agents/issues/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Standard five-role vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (CONTEXT.md + docs/adr/ at repo root). See `docs/agents/domain.md`.

### Andthen

Doc-code consistency closed loop. See `.qoder/skills/andthen/SKILL.md`.
Use `/andthen` or "doc audit" / "跑一次审计" to trigger.

## 工作流程

所有工作流（编码前读文档、编码后同步文档、审计不一致、跟踪待办、跨会话交接）统一由 `/andthen` skill 驱动。详见 `.qoder/skills/andthen/SKILL.md`。

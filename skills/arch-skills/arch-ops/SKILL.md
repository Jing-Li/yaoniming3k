---
name: arch-ops
description: "arch-skills pipeline Phase 4b: operational documentation and tooling skill. Generates per-BC OPS.md runbook (prerequisites, build, config, startup, shutdown, troubleshooting), writes shell scripts (start.sh, stop.sh, status.sh), and produces Makefile. Consumes DESIGN.md §8 Operational Entry Design and implemented code from devtdd. Trigger when user says \"/arch-ops\", \"write ops doc\", \"generate runbook\", \"create scripts\", \"write Makefile\", or asks about operational documentation."
version: 1.0.0
---

# Arch-Ops Skill (Phase 4b: Operational Documentation & Tooling)

> **arch-skills pipeline** · Phase 4b — DevOps Engineer & Technical Writer
>
> | | |
> |---|---|
> | **Upstream** | `/devtdd` (implemented code + scripts/) + `/arch-detail` (DESIGN.md §8 Operational Entry Design) |
> | **Downstream** | `/arch-review` (audits OPS.md vs actual scripts vs code consistency) |
> | **Owns** | `ops/OPS.md`, `scripts/` content (start.sh, stop.sh, status.sh, ...), `Makefile` |
> | **Does** | Generate OPS.md runbook (prerequisites, env setup, build, config, startup, usage), write/update shell scripts and Makefile, verify scripts work against implemented code |
> | **Does NOT** | Write domain/application code, design architecture, modify ARCHITECTURE.md/DESIGN.md, run tests (that is devtdd) |

You are a meticulous DevOps Engineer and Technical Writer. Your job is to bridge the gap between implemented code and operational reality: producing clear, actionable runbooks and reliable scripts so that anyone (developer, SRE, or future AI agent) can build, configure, run, and troubleshoot this BC without reading source code.

**Core philosophy**:
- OPS.md is a **runbook**, not a README — it covers the full lifecycle from prerequisites to troubleshooting
- Scripts MUST be **idempotent** — start.sh checks if already running, stop.sh checks if already stopped
- Makefile is the **developer entry point** — `make build/start/stop/test` should "just work"
- **Config validation** happens at startup — env var table in OPS.md MUST match DESIGN.md §8.1 exactly
- Every command in OPS.md MUST be **copy-pasteable** and verified against actual scripts

---

## HARD CONSTRAINTS

1. **OPS.MD IS THE SINGLE SOURCE OF TRUTH**: `docs/bc/<slug>/ops/OPS.md` is the definitive guide for building, configuring, and running this BC. No duplicate operational docs in README.md or elsewhere.

2. **SCRIPTS MUST BE EXECUTABLE AND VALIDATED**: Every `.sh` file MUST pass `bash -n` syntax check. Every script MUST include `set -euo pipefail`. Idempotency checks are mandatory (start when already running → warn and exit 0; stop when not running → warn and exit 0).

3. **NO DOMAIN CODE**: You create and modify ONLY: `ops/OPS.md`, `scripts/*.sh`, `Makefile`, and `scripts/.gitkeep`. You do NOT touch `.go`, `.java`, `.py` source files, test files, or build configs (`go.mod`, `build.gradle`, `pyproject.toml`).

4. **DESIGN.MD §8 ALIGNMENT**: OPS.md §4 Configuration table MUST match DESIGN.md §8.1 Environment Variable Schema exactly. If DESIGN.md §8.1 lists a variable that OPS.md omits (or vice versa), write an AD targeting arch-detail.

5. **DOCUMENT OWNERSHIP & UPSTREAM CONSISTENCY GATE**: arch-ops is the sole owner of `ops/OPS.md`, `scripts/` content, and `Makefile`. When OPS.md or scripts reveal gaps in DESIGN.md §8 (missing env vars, incomplete script specs, undefined config defaults), arch-ops MUST write an AD to `T{N}.md → Architecture Discrepancies → arch-detail section`.

6. **CROSS-BC SCRIPT CONSISTENCY**: When a sibling BC already has `scripts/` (e.g., `platform/scripts/{start,stop,status}.sh`), this BC MUST produce equivalent scripts with the same interface (same flags, same exit codes). Grep sibling BC scripts for interface patterns before writing.

---

## Steps to Execute

### Step 1: Context Loading

Read the following files in order:

1. `docs/bc/<slug>/kanban/BOARD.md` — find current task
2. `kanban/tasks/T{N}.md` — read References for upstream links
3. `docs/bc/<slug>/detail/DESIGN.md` §8 — Operational Entry Design (env vars, config module, script specs)
4. `docs/bc/<slug>/detail/DESIGN.md` §6 — Composition Root (understand startup/dependency injection flow)
5. `docs/bc/<slug>/align/LANGUAGE.md` — for consistent terminology
6. Existing `scripts/` directory — what already exists (from arch-init scaffolding or devtdd)
7. Sibling BC `scripts/` — check interface patterns for consistency

**Precondition**: If upstream devtdd is NOT `done` for T{N}, HALT and instruct user to run `/devtdd`.

### Step 2: OPS.md Generation

Generate `docs/bc/<slug>/ops/OPS.md` using the template in [references/ops-md-template.md](references/ops-md-template.md). Eight sections:

1. **Prerequisites** — External dependencies: language runtime (with version), database, message queue, third-party services. Table format: `| Dependency | Version | Purpose | Install Command |`
2. **Environment Setup** — Step-by-step installation guide for each prerequisite. Include verification commands.
3. **Build** — Compile/package commands. Include clean build and incremental build. Table: `| Command | Purpose | Expected Output |`
4. **Configuration** — Environment variable reference table (MUST match DESIGN.md §8.1). Table: `| Variable | Required | Default | Description | Example |` Also list config file paths if applicable.
5. **Startup** — Start commands, expected log output, health check endpoint. Include both script-based and manual startup.
6. **Shutdown** — Graceful stop procedure, SIGINT handling, cleanup steps.
7. **Common Operations** — Status check, log access, troubleshooting table (`| Symptom | Cause | Fix |`).
8. **Development** — Hot reload setup, test commands, debug configuration, linting.

Rules:
- Every code block MUST specify the language (`bash`, `yaml`, `env`, etc.)
- Every command MUST be copy-pasteable (no `<placeholder>` without a concrete example)
- If the BC uses a database, include migration/init commands in §3 Build

### Step 3: Scripts Generation

Write/update shell scripts in `<bc-root>/scripts/`. See [references/script-templates.md](references/script-templates.md) for templates.

**Mandatory scripts** (per DESIGN.md §8.3):

| Script | Responsibility | Idempotency |
|--------|---------------|-------------|
| `start.sh` | Compile (if needed) → start process | Check if already running → warn + exit 0 |
| `stop.sh` | Send SIGINT → wait graceful shutdown | Check if not running → warn + exit 0 |
| `status.sh` | Process liveness + port reachability | N/A (read-only) |
| `gen-openapi.sh` | Generate OpenAPI spec from binary | Idempotent (overwrites output file) |

**Common conventions**:
- Shebang: `#!/usr/bin/env bash`
- First line after shebang: `set -euo pipefail`
- PID file: `.pid` in project root or `/tmp/<bc-slug>.pid`
- Log file: configurable via `LOG_FILE` env var, default `logs/<bc-slug>.log`
- Port: configurable via env var (from DESIGN.md §8.1)
- Exit codes: 0 = success, 1 = error, 2 = already in desired state

**Additional scripts** (as needed per BC):
- `init-db.sh` — database migration/initialization
- `seed.sh` — seed data for development
- `health.sh` — HTTP health check
- `gen-openapi.sh` — generate OpenAPI spec from code (v1.1.0+, see below)

**OpenAPI generation script (v1.1.0+)**:

When devtdd implements a delivery layer with an OpenAPI CLI subcommand (e.g., `./<binary> openapi`), arch-ops MUST create `scripts/gen-openapi.sh` and a corresponding `make openapi` target:

```bash
#!/usr/bin/env bash
set -euo pipefail
# Generate OpenAPI spec from compiled binary
BINARY="${BINARY:-./bin/<bc-slug>}"
OUTPUT="${OUTPUT:-docs/bc/<slug>/detail/api-contracts/openapi.yaml}"

mkdir -p "$(dirname "$OUTPUT")"
"$BINARY" openapi > "$OUTPUT"
echo "OpenAPI spec written to $OUTPUT"
```

Makefile target:
```makefile
openapi: build ## Generate OpenAPI spec from code
	@bash scripts/gen-openapi.sh
```

This script is triggered by devtdd ADs (AD-O{N}) or during normal arch-ops execution when a delivery layer exists.

### Step 4: Makefile Generation

Write `<bc-root>/Makefile` with standard targets:

```makefile
.PHONY: build start stop status test lint clean help

build:       ## Build the application
start:       ## Start the application
stop:        ## Stop the application
status:      ## Check application status
test:        ## Run tests
lint:        ## Run linters
clean:       ## Clean build artifacts
help:        ## Show this help
```

Rules:
- Each target MUST have a `## comment` for `make help` auto-generation
- Targets MUST proxy to `scripts/` where equivalent scripts exist
- Language-specific targets: Go (`go build`), Java (`./gradlew build`), Python (`pip install -e .`)
- `make test` MUST NOT modify OPS.md or scripts (that is arch-ops's own output, not devtdd's)

### Step 5: Verification

Before marking complete:

1. **Syntax check**: `bash -n scripts/*.sh` — all scripts pass
2. **OPS.md ↔ scripts consistency**: Every command in OPS.md §5 Startup references an actual script that exists
3. **OPS.md §4 ↔ DESIGN.md §8.1**: Environment variable tables match exactly (same variables, same defaults)
4. **Makefile targets**: `make help` lists all targets with descriptions
5. **Sibling BC consistency**: If sibling BCs have scripts, verify interface consistency (same flags, same exit codes)

If any mismatch is found:
- OPS.md vs scripts → fix OPS.md (you own it)
- OPS.md vs DESIGN.md §8.1 → write AD targeting arch-detail
- Scripts vs DESIGN.md §8.3 → write AD targeting arch-detail

### Step 6: State Synchronization

1. Update `kanban/tasks/T{N}.md`:
   - Fill in References → ops section with OPS.md + scripts links
   - Set Status row: ops = done + Completed date
   - Mark any AD entries targeting arch-ops as Resolved
   - Append Change History entry at top
2. Move T{N} from `doing` to `done` in `kanban/BOARD.md`
3. **Archive check**: If ALL skills in T{N}.md Status are done AND no unresolved Architecture Discrepancy entries exist → add T{N} to BOARD.md Archive table and remove from Board table
4. Output hand-off trigger:
   > T{N} completed at arch-ops.
   > OPS.md generated with 8 sections, N scripts written, Makefile created.
   > Next: `/arch-review` to audit operational consistency.
   > If AD entries exist: "Pending ADs: <list>"

---

## Redo Protocol

When re-running arch-ops for an existing T{N}:

1. Read existing OPS.md and scripts — understand current state
2. Read AD entries targeting arch-ops in T{N}.md
3. Idempotent fix: only modify what the AD requires
4. Re-run verification (Step 5)
5. Mark ADs as Resolved

---

## Migration Mode Detection

Before normal execution, check:
- `docs/bc/<slug>/ops/OPS.md` is empty or missing
- Source code and scripts already exist (from devtdd migration)
- `T{N}.md` References has `(migration)` tag

If ALL conditions met → enter Migration Mode:
- Skip upstream halt
- Read existing scripts → document their interface in OPS.md
- Generate OPS.md from actual code analysis (not DESIGN.md §8 which may not exist)
- Create Makefile wrapping existing scripts
- Present to user for confirmation

---

## BC Selection Protocol

When user does not specify a BC:
1. Read `AGENTS.md` BC registry
2. If only one BC exists → use it automatically
3. If multiple BCs exist → ask user which BC to target (via `AskUserQuestion`)
4. If target BC's `docs/bc/<slug>/` does not exist → halt: "BC directory not found. Run `/arch-init` first."

---

## Manifest Protocol

### On Startup

1. Read `kanban/BOARD.md` — find own row (`arch-ops`)
2. If `doing` has a task → continue it
3. If `new` has tasks → pick leftmost
4. If both empty → check archived T{N}.md for unresolved ADs targeting arch-ops
   - If found → proceed to step 5
   - If not found → 🚫 HALT via AskUserQuestion (per kanban-spec §4.1 step 5): route to `/arch-align`
5. Read `T{N}.md` → AD Check → upstream check (devtdd done for T{N})
   - If upstream devtdd NOT done → 🚫 HALT via AskUserQuestion (per ask-user-question-spec.md): "Run `/devtdd` first?"
6. Handover removal (from devtdd `done` column)
7. Read upstream files via References
8. Move T{N} to `doing`

### On Completion

1. Write OPS.md + scripts + Makefile
2. Update T{N}.md (References + Status + Change History)
3. Move doing → done
4. Archive check
5. Output hand-off trigger

---

## Kanban Protocol

See [kanban-spec.md](../arch-conventions/references/kanban-spec.md) for Startup/Completion/Redo sequences and T{N}.md structure.

See [shared-constraints.md](../arch-conventions/references/shared-constraints.md) for pipeline-wide rules: Document Ownership (§1), Restricted Tool Surface (§2), No Source Code Modification (§3), Grill Don't Guess (§4), OVERRIDE Protocol (§5), Upstream Halt (§6).

## Additional Resources

For OPS.md template, script templates, and Makefile templates, read [reference.md](reference.md) and [references/](references/) when needed.

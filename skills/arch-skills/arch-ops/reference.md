# Arch-Ops Reference

Supplementary templates for SKILL.md. Read this file when generating OPS.md, scripts, or Makefile.

---

## 1. OPS.md Template

Full template available at [references/ops-md-template.md](references/ops-md-template.md).

### Section Summary

| # | Section | Required | Source |
|---|---------|----------|--------|
| 1 | Prerequisites | Yes | DESIGN.md §8 + code analysis |
| 2 | Environment Setup | Yes | §1 dependency list |
| 3 | Build | Yes | Language-specific build tool |
| 4 | Configuration | Yes | DESIGN.md §8.1 (MUST match) |
| 5 | Startup | Yes | DESIGN.md §8.3 + start.sh |
| 6 | Shutdown | Yes | stop.sh |
| 7 | Common Operations | Yes | status.sh + troubleshooting |
| 8 | Development | Optional | Test/lint/debug commands |

### Cross-Reference Rules

- OPS.md §4 env var table → MUST match DESIGN.md §8.1 row-for-row
- OPS.md §5 startup command → MUST reference actual start.sh
- OPS.md §3 build command → MUST reference actual Makefile `build` target
- If mismatch found → write AD targeting arch-detail

---

## 2. Script Templates

Full templates at [references/script-templates.md](references/script-templates.md).

### Common Script Header

```bash
#!/usr/bin/env bash
set -euo pipefail

# --- Constants ---
readonly BC_NAME="<bc-slug>"
readonly PID_FILE="/tmp/${BC_NAME}.pid"
readonly LOG_DIR="logs"
readonly LOG_FILE="${LOG_DIR}/${BC_NAME}.log"
```

### Idempotency Pattern

```bash
is_running() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}
```

### Exit Code Convention

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error |
| 2 | Already in desired state |

---

## 3. Makefile Template

```makefile
.DEFAULT_GOAL := help
SHELL := /bin/bash

# --- Paths ---
SCRIPTS_DIR := scripts
BC_NAME     := <bc-slug>

.PHONY: build start stop status test lint clean help

## Build
build:
	@echo "Building $(BC_NAME)..."
	# Language-specific: go build ./cmd/... | ./gradlew build | pip install -e .

## Start the application
start:
	@$(SCRIPTS_DIR)/start.sh

## Stop the application
stop:
	@$(SCRIPTS_DIR)/stop.sh

## Check application status
status:
	@$(SCRIPTS_DIR)/status.sh

## Run tests
test:
	# Language-specific: go test ./... | ./gradlew test | pytest

## Run linters
lint:
	# Language-specific: golangci-lint run | ./gradlew check | ruff check .

## Clean build artifacts
clean:
	# Language-specific: rm -rf bin/ | ./gradlew clean | rm -rf dist/ .eggs/

## Show this help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
```

### Language-Specific Build Targets

**Go:**
```makefile
build:
	go build -o bin/$(BC_NAME) ./cmd/$(BC_NAME)/
```

**Java (Gradle):**
```makefile
build:
	./gradlew build -x test
```

**Python:**
```makefile
build:
	pip install -e ".[dev]"
```

---

## 4. Pre-Output Self-Audit

Before finalizing OPS.md + scripts, verify:

- [ ] OPS.md §4 env var table matches DESIGN.md §8.1 exactly
- [ ] All `bash -n scripts/*.sh` pass
- [ ] Every command in OPS.md §5 references an existing script
- [ ] Makefile `make help` lists all targets
- [ ] Sibling BC scripts have consistent interface (if applicable)
- [ ] No domain code was modified (Hard Constraint #3)
- [ ] PID file paths are consistent across start/stop/status
- [ ] Log directory creation is handled (`mkdir -p`)

---

## 5. Multi-BC Script Consistency Checklist

When the project has 2+ BCs with independent processes:

- [ ] All `start.sh` accept the same flags (e.g., `--port`, `--env`)
- [ ] All `stop.sh` use the same PID file convention
- [ ] All `status.sh` output the same format (running/stopped + port)
- [ ] All Makefiles expose the same target names
- [ ] Exit codes are consistent across BCs

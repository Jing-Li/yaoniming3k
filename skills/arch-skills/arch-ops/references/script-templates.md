# Script Templates

Shell script templates for arch-ops. Adapt `<placeholders>` to actual BC configuration.

---

## 1. start.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

# --- Constants ---
readonly BC_NAME="<bc-slug>"
readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly PID_FILE="/tmp/${BC_NAME}.pid"
readonly LOG_DIR="${PROJECT_ROOT}/logs"
readonly LOG_FILE="${LOG_DIR}/${BC_NAME}.log"

# --- Config (from env vars, with defaults) ---
readonly PORT="${<BC>_PORT:-8080}"
readonly ENV="${<BC>_ENV:-development}"

# --- Idempotency Check ---
is_running() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

if is_running; then
    echo "[$BC_NAME] Already running (PID $(cat "$PID_FILE"))"
    exit 0
fi

# --- Prepare ---
mkdir -p "$LOG_DIR"

# --- Build (language-specific) ---
echo "[$BC_NAME] Building..."
# Go:   go build -o "${PROJECT_ROOT}/bin/${BC_NAME}" ./cmd/${BC_NAME}/
# Java: cd "$PROJECT_ROOT" && ./gradlew build -x test
# Py:   pip install -e "$PROJECT_ROOT"
# TS:   cd "$PROJECT_ROOT" && npm run build

# --- Start ---
echo "[$BC_NAME] Starting on port $PORT (env=$ENV)..."

# Go:
# "${PROJECT_ROOT}/bin/${BC_NAME}" >> "$LOG_FILE" 2>&1 &
# echo $! > "$PID_FILE"

# Java:
# java -jar "${PROJECT_ROOT}/build/libs/${BC_NAME}.jar" >> "$LOG_FILE" 2>&1 &
# echo $! > "$PID_FILE"

# Python:
# python -m <bc_module> >> "$LOG_FILE" 2>&1 &
# echo $! > "$PID_FILE"

# TypeScript:
# cd "$PROJECT_ROOT" && node dist/index.js >> "$LOG_FILE" 2>&1 &
# echo $! > "$PID_FILE"

# --- Wait for health ---
echo "[$BC_NAME] Waiting for port $PORT..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:${PORT}/health" > /dev/null 2>&1; then
        echo "[$BC_NAME] Running (PID $(cat "$PID_FILE")) on port $PORT"
        exit 0
    fi
    sleep 1
done

echo "[$BC_NAME] ERROR: Failed to start within 30s. Check logs: $LOG_FILE"
exit 1
```

---

## 2. stop.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

# --- Constants ---
readonly BC_NAME="<bc-slug>"
readonly PID_FILE="/tmp/${BC_NAME}.pid"

# --- Idempotency Check ---
is_running() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

if ! is_running; then
    echo "[$BC_NAME] Not running"
    [[ -f "$PID_FILE" ]] && rm -f "$PID_FILE"
    exit 0
fi

# --- Graceful Shutdown ---
readonly PID="$(cat "$PID_FILE")"
echo "[$BC_NAME] Stopping (PID $PID)..."

kill -SIGINT "$PID"

# Wait for graceful shutdown (max 10s)
for i in $(seq 1 10); do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "[$BC_NAME] Stopped gracefully"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# Force kill after timeout
echo "[$BC_NAME] WARNING: Graceful shutdown timeout, force killing..."
kill -9 "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "[$BC_NAME] Force killed"
exit 0
```

---

## 3. status.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

# --- Constants ---
readonly BC_NAME="<bc-slug>"
readonly PID_FILE="/tmp/${BC_NAME}.pid"
readonly PORT="${<BC>_PORT:-8080}"

# --- Process Check ---
is_running() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

# --- Port Check ---
is_port_open() {
    curl -sf "http://localhost:${PORT}/health" > /dev/null 2>&1
}

# --- Status Output ---
if is_running; then
    readonly PID="$(cat "$PID_FILE")"
    if is_port_open; then
        echo "[$BC_NAME] Running (PID $PID) on port $PORT - healthy"
        exit 0
    else
        echo "[$BC_NAME] Running (PID $PID) on port $PORT - NOT responding"
        exit 1
    fi
else
    echo "[$BC_NAME] Stopped"
    [[ -f "$PID_FILE" ]] && rm -f "$PID_FILE"
    exit 0
fi
```

---

## 4. init-db.sh (Optional — for DB-backed BCs)

```bash
#!/usr/bin/env bash
set -euo pipefail

# --- Constants ---
readonly BC_NAME="<bc-slug>"
readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly MIGRATIONS_DIR="${PROJECT_ROOT}/migrations"

# --- Config ---
readonly DB_URL="${<BC>_DB_URL:-postgres://localhost:5432/${BC_NAME}?sslmode=disable}"

echo "[$BC_NAME] Running database migrations..."

# Go (golang-migrate):
# migrate -path "$MIGRATIONS_DIR" -database "$DB_URL" up

# Java (Flyway):
# ./gradlew flywayMigrate -Pflyway.url="$DB_URL"

# Python (Alembic):
# alembic -c "${PROJECT_ROOT}/alembic.ini" upgrade head

echo "[$BC_NAME] Migrations complete"
```

---

## 5. health.sh (Optional — dedicated health check)

```bash
#!/usr/bin/env bash
set -euo pipefail

# --- Constants ---
readonly BC_NAME="<bc-slug>"
readonly PORT="${<BC>_PORT:-8080}"
readonly HEALTH_ENDPOINT="/health"

# --- Check ---
readonly RESPONSE
RESPONSE=$(curl -sf "http://localhost:${PORT}${HEALTH_ENDPOINT}" 2>/dev/null) || {
    echo "[$BC_NAME] UNHEALTHY - cannot reach http://localhost:${PORT}${HEALTH_ENDPOINT}"
    exit 1
}

echo "[$BC_NAME] HEALTHY - $RESPONSE"
exit 0
```

---

## Script File Permissions

After creating scripts, ensure they are executable:

```bash
chmod +x scripts/*.sh
```

This MUST be done via the file creation tool's permission setting, not a separate chmod command.

---

## Naming Conventions

| Pattern | Example |
|---------|---------|
| PID file | `/tmp/<bc-slug>.pid` |
| Log file | `logs/<bc-slug>.log` |
| Env var prefix | `<BC>_<VAR>` (uppercase BC slug) |
| Script names | `snake_case.sh` |

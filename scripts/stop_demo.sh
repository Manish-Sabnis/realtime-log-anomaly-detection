#!/usr/bin/env bash
# scripts/stop_demo.sh
# Stops all running demo processes.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
PID_FILE="$ROOT/logs/pids.txt"

echo "[stop] Stopping demo processes..."

if [ -f "$PID_FILE" ]; then
    while IFS= read -r pid; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null && echo "    Killed PID $pid"
        fi
    done < "$PID_FILE"
    rm "$PID_FILE"
fi

# Also kill anything on port 7000
lsof -ti tcp:7000 | xargs kill -9 2>/dev/null || true

echo "[stop] Done."
#!/usr/bin/env bash
# scripts/run_demo.sh
# Starts the full anomaly detection system for demo.
#
# Usage
# -----
#   bash scripts/run_demo.sh
#
# What it does
# ------------
# 1. Starts the ingestor API         (port 7000, background)
# 2. Seeds 5 minutes of normal logs  (foreground, you watch it)
# 3. Trains the baseline model       (foreground)
# 4. Starts the anomaly detector     (background)
# 5. Starts normal traffic generator (background)
# 6. Prints instructions for triggering anomalies
#
# Logs
# ----
#   logs/ingestor.log   — ingestor API output
#   logs/detector.log   — detector output
#   logs/generator.log  — generator output

set -e

# ── Resolve repo root ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
cd "$ROOT"

# ── Config ────────────────────────────────────────────────────────────────────
INGESTOR_PORT=7000
INGESTOR_URL="http://localhost:${INGESTOR_PORT}"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   Real-Time Log Anomaly Detection — Demo         ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Step 1: Start ingestor ────────────────────────────────────────────────────
echo -e "${CYAN}[1/5] Starting ingestor API on port ${INGESTOR_PORT}...${RESET}"

# Kill any existing process on the port
lsof -ti tcp:${INGESTOR_PORT} | xargs kill -9 2>/dev/null || true
sleep 1

python3 services/ingestor-api/app.py --port ${INGESTOR_PORT} \
    > "$LOG_DIR/ingestor.log" 2>&1 &
INGESTOR_PID=$!
echo "    PID: $INGESTOR_PID | log: logs/ingestor.log"

# Wait for ingestor to be ready
echo -n "    Waiting for ingestor"
for i in $(seq 1 15); do
    if curl -s "${INGESTOR_URL}/status" | grep -q "ok" 2>/dev/null; then
        echo -e " ${GREEN}✓ ready${RESET}"
        break
    fi
    echo -n "."
    sleep 1
done

# ── Step 2: Seed baseline data ────────────────────────────────────────────────
echo ""
echo -e "${CYAN}[2/5] Seeding 5 minutes of normal baseline logs...${RESET}"
echo "    This takes ~5 minutes. Grab a coffee. ☕"
echo ""

python3 scripts/seed_normal_logs.py \
    --url "$INGESTOR_URL" \
    --duration 300 \
    --burst 3 \
    --interval 2

# ── Step 3: Train model ───────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}[3/5] Training Isolation Forest on baseline data...${RESET}"
echo ""

python3 pipelines/train_baseline.py
echo ""

# ── Step 4: Start detector ────────────────────────────────────────────────────
echo -e "${CYAN}[4/5] Starting anomaly detector (polling every 60s)...${RESET}"

python3 pipelines/run_detector.py --interval 60 \
    > "$LOG_DIR/detector.log" 2>&1 &
DETECTOR_PID=$!
echo "    PID: $DETECTOR_PID | log: logs/detector.log"

# ── Step 5: Start normal traffic generator ────────────────────────────────────
echo ""
echo -e "${CYAN}[5/5] Starting normal traffic generator...${RESET}"

python3 services/log-generator/generator.py \
    --mode normal \
    --burst 3 \
    --interval 2 \
    --url "$INGESTOR_URL" \
    > "$LOG_DIR/generator.log" 2>&1 &
GENERATOR_PID=$!
echo "    PID: $GENERATOR_PID | log: logs/generator.log"

# ── Save PIDs for cleanup ─────────────────────────────────────────────────────
echo "$INGESTOR_PID"  > "$LOG_DIR/pids.txt"
echo "$DETECTOR_PID" >> "$LOG_DIR/pids.txt"
echo "$GENERATOR_PID" >> "$LOG_DIR/pids.txt"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}║   System is running!                             ║${RESET}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${BOLD}API endpoints:${RESET}"
echo -e "    ${INGESTOR_URL}/status       — health check"
echo -e "    ${INGESTOR_URL}/logs         — view stored logs"
echo -e "    ${INGESTOR_URL}/anomalies    — view anomaly results"
echo ""
echo -e "  ${BOLD}Live logs:${RESET}"
echo -e "    tail -f logs/detector.log   — anomaly detector output"
echo -e "    tail -f logs/ingestor.log   — ingestor output"
echo -e "    tail -f logs/generator.log  — traffic generator output"
echo ""
echo -e "  ${BOLD}${RED}Trigger anomaly scenarios:${RESET}"
echo -e "    python3 scripts/trigger_anomaly.py --scenario login_storm"
echo -e "    python3 scripts/trigger_anomaly.py --scenario latency_spike"
echo -e "    python3 scripts/trigger_anomaly.py --scenario payment_outage"
echo ""
echo -e "  ${BOLD}Stop everything:${RESET}"
echo -e "    bash scripts/stop_demo.sh"
echo ""
echo -e "  ${YELLOW}The detector checks every 60s. After triggering an anomaly,${RESET}"
echo -e "  ${YELLOW}wait up to 60s then check logs/detector.log${RESET}"
echo ""
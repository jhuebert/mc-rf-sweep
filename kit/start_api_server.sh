#!/bin/sh
# Server-side (re)starter for the rf-sweep-core-kit api_server.
# Usage: start_api_server.sh <node_letter>   (a or b)
set -e
NODE="$1"
KIT=~/rf-sweep-core-kit
cd "$KIT"

# stop any previous instance
pkill -f api_server.py 2>/dev/null || true
sleep 1

# ensure port 8090
sed -i 's/^API_PORT=.*/API_PORT=8090/' "node_$NODE.env"

export PYTHONPATH=/home/jason/openhop_core/src
setsid .venv/bin/python api_server.py --env "node_$NODE.env" > server.log 2>&1 < /dev/null &
sleep 6

if pgrep -f api_server.py > /dev/null; then
    echo "RUNNING (pid $(pgrep -f api_server.py))"
else
    echo "FAILED TO START"
fi
grep -E "radio up|configured|ERROR|Could not reach" server.log | tail -4
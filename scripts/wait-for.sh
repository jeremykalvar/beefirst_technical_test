#!/usr/bin/env sh
set -eu

usage() {
  echo "Usage: $0 host:port [-t timeout_seconds]" >&2
  exit 2
}

TARGET="${1:-}"
[ -z "$TARGET" ] && usage
shift || true

TIMEOUT=30
while [ $# -gt 0 ]; do
  case "$1" in
    -t|--timeout)
      TIMEOUT="${2:-}" ; [ -z "$TIMEOUT" ] && usage
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

HOST="$(echo "$TARGET" | cut -d: -f1)"
PORT="$(echo "$TARGET" | cut -d: -f2)"

[ -z "$HOST" ] && usage
[ -z "$PORT" ] && usage

echo "Waiting for $HOST:$PORT (timeout ${TIMEOUT}s)..." >&2
START="$(date +%s)"

while :; do
  # Use Python to attempt a TCP connect (keeps dependencies minimal)
  python - <<PY >/dev/null 2>&1
import socket, sys
s = socket.socket()
s.settimeout(1.0)
try:
    s.connect(("$HOST", int("$PORT")))
except Exception:
    sys.exit(1)
else:
    s.close()
    sys.exit(0)
PY
  if [ $? -eq 0 ]; then
    echo "✔ $HOST:$PORT is available." >&2
    exit 0
  fi

  NOW="$(date +%s)"
  ELAPSED=$((NOW - START))
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "✗ Timeout after ${TIMEOUT}s waiting for $HOST:$PORT" >&2
    exit 1
  fi
  sleep 1
done

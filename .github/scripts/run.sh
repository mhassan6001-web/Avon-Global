#!/usr/bin/env bash
# Runs a CI step and, on failure, publishes the last 80 lines of its output as
# a single GitHub error annotation so failures are readable without full logs.
# Usage: .github/scripts/run.sh "<label>" <command...>
set -o pipefail
label="$1"; shift
log="$(mktemp)"
"$@" 2>&1 | tee "$log"
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then
  body="$(tail -n 80 "$log" | sed -e 's/%/%25/g' -e 's/\r/%0D/g' | awk '{printf "%s%%0A", $0}')"
  echo "::error title=${label} failed (exit ${status})::${body}"
fi
exit "$status"

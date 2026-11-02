#!/usr/bin/env bash
set -euo pipefail
NATIVE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_OUTPUT="${NATIVE_CHECK_OUTPUT:-$(mktemp -d "${TMPDIR:-/tmp}/platforma-host-checks.XXXXXX")}"
exec python3 "$NATIVE_ROOT/scripts/run_swift_host_suites.py" core "$NATIVE_ROOT" "$CHECK_OUTPUT" \
  "$NATIVE_ROOT"/ios/Checks/*.swift

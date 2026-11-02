#!/usr/bin/env bash
set -euo pipefail
NATIVE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_OUTPUT="${NATIVE_CHECK_OUTPUT:-$(mktemp -d "${TMPDIR:-/tmp}/platforma-native-checks.XXXXXX")}"
mkdir -p "$CHECK_OUTPUT/module-cache"
swiftc -swift-version 6 -emit-library -emit-module -module-name CRMCore   -module-cache-path "$CHECK_OUTPUT/module-cache"   "$NATIVE_ROOT"/ios/Sources/CRMCore/*.swift   -emit-module-path "$CHECK_OUTPUT/CRMCore.swiftmodule" -o "$CHECK_OUTPUT/libCRMCore.dylib"
swiftc -swift-version 6 -parse-as-library -I "$CHECK_OUTPUT" -L "$CHECK_OUTPUT" -lCRMCore   -Xlinker -rpath -Xlinker "$CHECK_OUTPUT" -module-cache-path "$CHECK_OUTPUT/module-cache"   "$NATIVE_ROOT"/ios/Checks/*.swift -o "$CHECK_OUTPUT/CRMCoreChecks"
"$CHECK_OUTPUT/CRMCoreChecks" "$NATIVE_ROOT/contracts/fixtures"

#!/usr/bin/env bash
# Deprecated: use scripts/install.sh (links both skills/ and rules/).
set -euo pipefail
echo "NOTE: install-rules.sh is deprecated; running install.sh instead." >&2
exec "$(cd "$(dirname "$0")" && pwd)/install.sh"

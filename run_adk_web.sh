#!/usr/bin/env bash
# Run ADK Web from a project-local virtualenv (repo root = parent of cloud_security_iac_delivery).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
python -m pip install -q -r requirements.txt
export SSL_CERT_FILE="$(python -m certifi)"
exec python "$ROOT/run_adk_web_mckinsey.py" "$@"

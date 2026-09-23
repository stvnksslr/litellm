#!/usr/bin/env bash
set -euo pipefail

scenario=${1:-with_claude}
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
out=${HARNESS_OUT:-$(mktemp -d)}
proxy_port=${HARNESS_PROXY_PORT:-4010}
mkdir -p "$out/work" "$out/claude-config"
if lsof -ti "tcp:8765,$proxy_port" -sTCP:LISTEN >/dev/null; then
  echo "port 8765 or $proxy_port is already in use; stop the old harness first" >&2
  exit 1
fi

"$repo/.venv/bin/python" "$here/fake_glm.py" --port 8765 >"$out/glm.log" 2>&1 &
HARNESS_LOG="$out/routing.jsonl" VERTEXAI_PROJECT="${VERTEXAI_PROJECT:-pb-shared-infra-dev}" \
  "$repo/.venv/bin/litellm" --config "$here/proxy_$scenario.yaml" --port "$proxy_port" >"$out/proxy.log" 2>&1 &
trap 'kill $(jobs -p) 2>/dev/null' EXIT
for _ in $(seq 90); do curl -sf "http://127.0.0.1:$proxy_port/health/liveliness" >/dev/null && break; sleep 1; done

(cd "$out/work" && env -i HOME="$HOME" PATH="$PATH" TERM="${TERM:-xterm}" \
  CLAUDE_CONFIG_DIR="$out/claude-config" \
  ANTHROPIC_BASE_URL="http://127.0.0.1:$proxy_port" \
  ANTHROPIC_AUTH_TOKEN=sk-harness \
  CLAUDE_CODE_GATEWAY_HINT_HEADERS=1 \
  CLAUDE_CODE_AUTO_MODE_SERVER="${CLAUDE_CODE_AUTO_MODE_SERVER:-0}" \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
  claude -p "Run the harness probe command." --model "${HARNESS_MODEL:-glm-5.3-flash}" \
    --permission-mode auto --output-format stream-json --verbose \
    >"$out/claude.jsonl" 2>"$out/claude.stderr") || true

echo "artifacts: $out"
"$repo/.venv/bin/python" "$here/routing_recorder.py" "$out/routing.jsonl"

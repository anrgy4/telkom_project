#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_MODELS="$PWD/.runtime/models"
if [[ ! -x .runtime/ollama/bin/ollama ]]; then
  echo 'Run bash scripts/setup-ollama.sh first.' >&2
  exit 1
fi
# Ollama creates its own runtime keys in ~/.ollama; no key values belong in Git.
exec .runtime/ollama/bin/ollama serve

#!/usr/bin/env bash
# Official, checksum-verified, pinned Linux x86_64 CPU runtime.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo 'This helper supports Linux x86_64. Install Ollama for your platform from ollama.com.' >&2
  exit 1
fi
archive="$PWD/.runtime/downloads/ollama-linux-amd64.tgz"
expected='9f9ff52b8297d6e40904f22bac09eac587a05111762bf278359621fbdb53dbb9'
mkdir -p .runtime/downloads .runtime/ollama
if [[ -x .runtime/ollama/bin/ollama && -f .runtime/ollama/.verified-v0.6.8 ]]; then
  echo 'Verified Ollama v0.6.8 CPU runtime already installed.'
  exit 0
fi
if [[ ! -f "$archive" ]]; then
  curl -fL --retry 2 --connect-timeout 15 --max-time 600 \
    https://github.com/ollama/ollama/releases/download/v0.6.8/ollama-linux-amd64.tgz \
    -o "$archive.part"
  mv "$archive.part" "$archive"
fi
printf '%s  %s\n' "$expected" "$archive" | sha256sum --check --status
# GPU libraries are unnecessary for this CPU development environment.
tar -xzf "$archive" --exclude='lib/ollama/cuda_v*' -C .runtime/ollama
touch .runtime/ollama/.verified-v0.6.8
echo 'Ollama v0.6.8 installed from the official GitHub release; SHA-256 verified.'
echo 'Start with: bash scripts/ollama.sh'
echo 'Then download the model: .runtime/ollama/bin/ollama pull qwen2.5:3b'

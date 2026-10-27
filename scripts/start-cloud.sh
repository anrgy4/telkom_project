#!/usr/bin/env bash
# Reuse healthy services; start only missing processes. Models persist separately.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p .runtime
if ! curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  nohup bash scripts/ollama.sh > .runtime/ollama.log 2>&1 &
  echo "$!" > .runtime/ollama.pid
fi
if ! curl -fsS --max-time 3 "http://127.0.0.1:${PORT:-8000}/api/health" >/dev/null 2>&1; then
  nohup bash scripts/dev.sh > .runtime/app.log 2>&1 &
  echo "$!" > .runtime/app.pid
fi
.venv/bin/python - <<'PY'
import time
import os
import httpx
app_url='http://127.0.0.1:'+os.getenv('PORT','8000')+'/api/health'
with httpx.Client(trust_env=False, timeout=3) as c:
    for label,url in [('Ollama','http://127.0.0.1:11434/api/tags'),('Rantai',app_url)]:
        for attempt in range(30):
            try:
                r=c.get(url);r.raise_for_status();body=r.json()
                if label=='Ollama' and 'models' not in body:raise ValueError('Unexpected service on Ollama port')
                if label=='Rantai' and (body.get('status')!='ok' or 'llm' not in body):raise ValueError('Unexpected service on app port')
                print(label+': HTTP readiness passed')
                break
            except (httpx.HTTPError,ValueError):
                if attempt==29:raise SystemExit(label+' did not become ready; inspect .runtime logs without dumping credentials')
                time.sleep(.3)
    state=c.get(app_url).json()
    print('LLM: '+state['llm']['message'])
    if not state['llm']['ready']:print('UI/sample workflow available; live analysis still requires the model download.')
PY

"""Download through local Ollama; never log signed storage URLs from errors."""
import json
import os
import re
from urllib.parse import urlsplit

import httpx

model=os.getenv("OLLAMA_MODEL","qwen2.5:3b")
try:
    with httpx.Client(trust_env=False,timeout=httpx.Timeout(600,connect=5)) as client:
        tags=client.get("http://127.0.0.1:11434/api/tags");tags.raise_for_status()
        if any(m["name"]==model for m in tags.json().get("models",[])):
            print(f"Model {model} already available.")
            raise SystemExit(0)
        previous=""
        with client.stream("POST","http://127.0.0.1:11434/api/pull",json={"model":model,"stream":True}) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:continue
                event=json.loads(line)
                if "error" in event:
                    hosts=sorted({urlsplit(u).hostname for u in re.findall(r'https?://[^\s\"]+',event["error"]) if urlsplit(u).hostname})
                    print("Model download failed. Review network policy/access for: "+", ".join(hosts))
                    raise SystemExit(1)
                status=event.get("status","")
                if status!=previous:
                    print(status,flush=True);previous=status
        tags=client.get("http://127.0.0.1:11434/api/tags");tags.raise_for_status()
        if not any(m["name"]==model for m in tags.json().get("models",[])):
            raise SystemExit("Pull ended without the selected model becoming available.")
        print("Model download and Ollama digest verification completed.")
except (httpx.HTTPError,ValueError,KeyError):
    raise SystemExit("Could not complete the local Ollama model pull. Check service, network, and disk availability.")

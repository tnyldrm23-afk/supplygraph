"""Provision the real local LLM through Ollama's documented API."""

import json
import httpx
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings

settings = Settings()
with httpx.stream(
    "POST", settings.ollama_url + "/api/pull", json={"name": settings.ollama_model}, timeout=900
) as response:
    response.raise_for_status()
    status = ""
    for line in response.iter_lines():
        entry = json.loads(line)
        if entry.get("error"):
            raise RuntimeError(entry["error"])
        if entry.get("status") != status:
            status = entry.get("status")
            print(status, flush=True)
print("Model ready:", settings.ollama_model)

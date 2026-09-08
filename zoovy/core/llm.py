import json
import requests
from typing import Dict, Any, List, Optional, Generator


class OllamaClient:
    """
    Interface for interacting with local Ollama instance with support for
    structured JSON tool-calling and streaming model downloads.
    """

    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen2.5:14b"):
        self.host = host.rstrip("/")
        self.model = model

    def is_alive(self) -> bool:
        """Verify that the Ollama daemon is reachable."""
        try:
            res = requests.get(f"{self.host}/api/version", timeout=3)
            return res.status_code == 200
        except Exception:
            return False

    def list_installed_models(self) -> List[str]:
        """Return a list of locally installed model tags."""
        try:
            res = requests.get(f"{self.host}/api/tags", timeout=5)
            if res.status_code == 200:
                data = res.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    def is_model_installed(self, model_tag: Optional[str] = None) -> bool:
        """Check if the target model is installed."""
        target = model_tag or self.model
        installed = self.list_installed_models()
        return any(target in m for m in installed)

    def pull_model(self, model_tag: str) -> Generator[Dict[str, Any], None, None]:
        """Stream model download progress from Ollama."""
        url = f"{self.host}/api/pull"
        with requests.post(url, json={"name": model_tag}, stream=True, timeout=600) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    yield json.loads(line.decode("utf-8"))

    def chat_structured(self, messages: List[Dict[str, str]], schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a chat completion request with structured JSON enforcement.
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,
            }
        }
        if schema:
            payload["format"] = "json"

        res = requests.post(f"{self.host}/api/chat", json=payload, timeout=120)
        res.raise_for_status()
        content = res.json().get("message", {}).get("content", "")

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Attempt to extract markdown JSON block
            if "```json" in content:
                extracted = content.split("```json")[1].split("```")[0].strip()
                return json.loads(extracted)
            elif "```" in content:
                extracted = content.split("```")[1].split("```")[0].strip()
                return json.loads(extracted)
            raise ValueError(f"Model failed to produce valid JSON: {content}")

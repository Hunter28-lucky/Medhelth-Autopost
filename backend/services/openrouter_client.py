import json
import logging
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from backend.config import settings

logger = logging.getLogger("publisher.openrouter")

# OpenRouter State-of-the-Art Free Model List
POPULAR_FREE_MODELS = [
    {
        "id": "openrouter/free",
        "name": "OpenRouter Auto-Free (Recommended)",
        "description": "Smart Auto-Router: Dynamically selects the highest quality available free model on OpenRouter with zero downtime."
    },
    {
        "id": "inclusionai/ling-3.0-flash-sante:free",
        "name": "Ling 3.0 Flash Santé (Free - Medical)",
        "description": "Domain-tuned healthcare & clinical AI model optimized for medical news and life sciences."
    },
    {
        "id": "nvidia/nemotron-3-super-120b-a12b:free",
        "name": "NVIDIA Nemotron 3 Super 120B (Free)",
        "description": "Massive 120B parameter frontier model with exceptional biomedical synthesis capabilities."
    },
    {
        "id": "google/gemma-4-31b-it:free",
        "name": "Google Gemma 4 31B IT (Free)",
        "description": "Google frontier instruction-tuned model with deep reasoning and strict format adherence."
    },
    {
        "id": "google/gemma-4-26b-a4b-it:free",
        "name": "Google Gemma 4 26B (Free)",
        "description": "Ultra-fast response latency with expansive context window."
    }
]

FREE_MODEL_CASCADE = [
    "openrouter/free",
    "inclusionai/ling-3.0-flash-sante:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free"
]

class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.OPENROUTER_API_KEY
        self.model = model if model is not None else (settings.OPENROUTER_MODEL or "openrouter/free")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def check_connection(self) -> Dict[str, Any]:
        """Test API key validity and connectivity to OpenRouter."""
        if not self.is_configured():
            return {
                "connected": False,
                "message": "OpenRouter API Key not configured. Please enter your free key."
            }

        try:
            req_data = {
                "model": "openrouter/free",
                "messages": [{"role": "user", "content": "Respond with 'CONNECTED' if you receive this."}],
                "max_tokens": 10
            }
            res = self._send_request(req_data, timeout=15)
            choices = res.get("choices", [])
            if choices:
                return {
                    "connected": True,
                    "model": res.get("model", self.model),
                    "message": "OpenRouter Free AI connected successfully!"
                }
            return {
                "connected": False,
                "message": "Connected but received empty response from OpenRouter."
            }
        except Exception as e:
            logger.warning(f"OpenRouter connection check failed: {e}")
            return {
                "connected": False,
                "message": f"OpenRouter check failed: {str(e)}"
            }

    def generate_chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Sends generation request to OpenRouter with automatic cascade across free models
        if the primary model hits rate-limits or temporary provider capacity.
        """
        if not self.is_configured():
            raise ValueError("OpenRouter API key is missing.")

        # Candidate models to try in sequence
        models_to_try = [self.model]
        for m in FREE_MODEL_CASCADE:
            if m not in models_to_try:
                models_to_try.append(m)

        last_error = None

        for model_candidate in models_to_try:
            try:
                logger.info(f"Dispatching generation to OpenRouter free model: {model_candidate}")
                payload = {
                    "model": model_candidate,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"} if "llama-3.3" in model_candidate or "qwen" in model_candidate else None
                }
                # Remove None fields
                payload = {k: v for k, v in payload.items() if v is not None}

                response_data = self._send_request(payload, timeout=60)
                choices = response_data.get("choices", [])
                msg = choices[0].get("message", {}) or {}
                raw_content = (msg.get("content") or "").strip()

                # Clean DeepSeek R1 reasoning tags if present
                if "<think>" in raw_content and "</think>" in raw_content:
                    raw_content = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()

                # Robust JSON extraction
                match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    parsed = json.loads(json_str)
                else:
                    parsed = json.loads(raw_content)

                logger.info(f"Successfully generated draft using OpenRouter model: {model_candidate}")
                return parsed

            except Exception as e:
                logger.warning(f"Model {model_candidate} on OpenRouter failed ({e}). Trying next free model in cascade...")
                last_error = e

        raise RuntimeError(f"All OpenRouter free models exhausted. Last error: {last_error}")

    def _send_request(self, payload: Dict[str, Any], timeout: int = 45) -> Dict[str, Any]:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.api_url,
            data=data_bytes,
            headers={
                "Authorization": f"Bearer {self.api_key.strip()}",
                "HTTP-Referer": "https://pulsepublish.local",
                "X-Title": "PulsePublish Free AI News Publisher",
                "Content-Type": "application/json",
                "User-Agent": "PulsePublish/2.8.4"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {err_body}")
        except Exception as e:
            raise RuntimeError(f"Network error: {str(e)}")

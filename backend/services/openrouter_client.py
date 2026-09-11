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
        "id": "inclusionai/ling-3.0-flash-sante:free",
        "name": "Ling 3.0 Flash Santé (Free - Medical)",
        "description": "Domain-tuned healthcare & clinical AI model optimized for medical news and life sciences."
    },
    {
        "id": "nex-agi/nex-n2.5-pro:free",
        "name": "Nex N2.5 Pro (Free)",
        "description": "Frontier open-weights reasoning model with exceptional clinical format adherence."
    },
    {
        "id": "nex-agi/nex-n2.5-mini:free",
        "name": "Nex N2.5 Mini (Free)",
        "description": "Ultra-fast response latency with concise factual synthesis."
    },
    {
        "id": "google/gemma-4-31b-it:free",
        "name": "Google Gemma 4 31B IT (Free)",
        "description": "Google frontier instruction-tuned model with deep reasoning."
    },
    {
        "id": "openrouter/free",
        "name": "OpenRouter Auto-Free",
        "description": "Smart Auto-Router: Dynamically selects available free models."
    }
]

FREE_MODEL_CASCADE = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
    "liquid/lfm-2.5-2.6b:free",
    "inclusionai/ling-3.0-flash-sante:free",
    "nex-agi/nex-n2.5-pro:free",
    "nex-agi/nex-n2.5-mini:free",
    "openrouter/free"
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
                    "response_format": {"type": "json_object"} if "llama-3.3" in model_candidate or "qwen" in model_candidate else None,
                    "reasoning": {"max_tokens": 500} if ("ling" in model_candidate or "nex" in model_candidate) else None
                }
                # Remove None fields
                payload = {k: v for k, v in payload.items() if v is not None}

                response_data = self._send_request(payload, timeout=45)
                choices = response_data.get("choices", [])
                if not choices:
                    err_msg = response_data.get("error", {}).get("message", "Empty choices array returned")
                    raise ValueError(f"OpenRouter returned no choices: {err_msg}")

                msg = choices[0].get("message", {}) or {}
                raw_content = (msg.get("content") or "").strip()

                if not raw_content and msg.get("reasoning"):
                    reasoning_text = msg.get("reasoning", "").strip()
                    json_match = re.search(r'\{.*\}', reasoning_text, re.DOTALL)
                    if json_match:
                        raw_content = json_match.group(0)

                if not raw_content:
                    raise ValueError("Model returned empty content")

                # Clean DeepSeek R1 reasoning tags if present
                if "<think>" in raw_content and "</think>" in raw_content:
                    raw_content = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()

                # Clean possible markdown wrapping
                clean_text = raw_content
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                elif clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()

                # Robust JSON extraction
                match = re.search(r'\{.*\}', clean_text, re.DOTALL)
                target_str = match.group(0) if match else clean_text

                try:
                    parsed = json.loads(target_str, strict=False)
                except Exception:
                    parsed = json.loads(clean_text, strict=False)

                if not isinstance(parsed, dict):
                    raise ValueError(f"OpenRouter response parsed to {type(parsed).__name__}, expected JSON object")

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

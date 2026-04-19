# -*- coding: utf-8 -*-
"""
QI Brain — Ollama provider.

Handles all local Ollama models (qwen3:8b, deepseek-r1:8b, gemma4:31b, etc.)
Strips <think>...</think> blocks that reasoning models emit.
"""
from __future__ import annotations
import re
import time
from typing import Optional

import httpx

from .base import BrainProvider, ProviderResponse

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_think(text: str) -> str:
    """Remove <think>...</think> blocks produced by reasoning models."""
    return _THINK_RE.sub("", text).strip()


class OllamaProvider(BrainProvider):
    """
    Provider for locally-running Ollama inference.

    Default base_url: http://localhost:11434
    Uses /api/generate (non-streaming) for text, /api/embeddings for vectors.
    """

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> ProviderResponse:
        start = time.monotonic()
        payload: dict = {
            "model":  self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens or self.max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            text      = _strip_think(data.get("response", ""))
            latency   = (time.monotonic() - start) * 1000
            tokens    = data.get("eval_count", 0)

            return ProviderResponse(
                text=text,
                provider_id=self.provider_id,
                model_name=self.model_name,
                tokens_used=tokens,
                latency_ms=latency,
                ok=True,
                raw=data,
            )

        except httpx.HTTPStatusError as exc:
            return ProviderResponse(
                text="",
                provider_id=self.provider_id,
                model_name=self.model_name,
                latency_ms=(time.monotonic() - start) * 1000,
                ok=False,
                error=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            )
        except Exception as exc:
            return ProviderResponse(
                text="",
                provider_id=self.provider_id,
                model_name=self.model_name,
                latency_ms=(time.monotonic() - start) * 1000,
                ok=False,
                error=str(exc),
            )

    async def embed(self, text: str) -> list[float]:
        """
        Ollama chat models do NOT produce quality embeddings.
        Use NomicEmbedProvider instead — this will raise.
        """
        raise NotImplementedError(
            f"OllamaProvider({self.model_name}) does not support embeddings. "
            "Use NomicEmbedProvider (nomic-embed-text) for vectors."
        )

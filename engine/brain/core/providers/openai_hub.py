# -*- coding: utf-8 -*-
"""
QI Brain — OpenAI-compatible hub provider (QI LLM Hub on NEXUS).

Routes generate() calls through the central hub:
    POST {base_url}/chat/completions      (base_url e.g. http://127.0.0.1:8010/v1)

model_name is the hub's routing key: a NEXUS provider id ("groq", "cerebras",
"gemma4", ...) or "auto" (hub picks fastest available with fallback).
No API key required — keys live in NEXUS secrets/nexus.env. The X-QI-App
header attributes usage to the Brain in the hub's usage log.
"""
from __future__ import annotations
import time
from typing import Optional

import httpx

from .base import BrainProvider, ProviderResponse


class OpenAIHubProvider(BrainProvider):

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> ProviderResponse:
        t0 = time.monotonic()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model_name or "auto",
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"X-QI-App": "qi-brain"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            choices = data.get("choices") or []
            text = ((choices[0].get("message", {}).get("content")) or "").strip() if choices else ""
            latency = (time.monotonic() - t0) * 1000
            if not text:
                return ProviderResponse(
                    text="", provider_id=self.provider_id, model_name=self.model_name,
                    latency_ms=latency, ok=False, error="hub returned empty response",
                )
            usage = data.get("usage") or {}
            return ProviderResponse(
                text=text,
                provider_id=self.provider_id,
                model_name=data.get("model", self.model_name),
                tokens_used=usage.get("total_tokens", 0),
                latency_ms=latency,
                raw=data,
            )
        except Exception as e:
            return ProviderResponse(
                text="", provider_id=self.provider_id, model_name=self.model_name,
                latency_ms=(time.monotonic() - t0) * 1000,
                ok=False, error=str(e) or type(e).__name__,
            )

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError("QI LLM Hub does not expose embeddings; use nomic_embed.")

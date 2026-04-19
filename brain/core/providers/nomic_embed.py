# -*- coding: utf-8 -*-
"""
QI Brain — Nomic Embed Text provider.

Purpose-built embedder via Ollama's /api/embeddings endpoint.
Model: nomic-embed-text (274 MB, already installed).

This is the ONLY provider used for vectorizing text into ChromaDB.
Chat generation is disabled — this provider only embeds.
"""
from __future__ import annotations
import time
from typing import Optional

import httpx

from .base import BrainProvider, ProviderResponse


class NomicEmbedProvider(BrainProvider):
    """
    Text embedding via nomic-embed-text through Ollama.

    Produces 768-dimensional vectors.
    Default base_url: http://localhost:11434
    """

    async def embed(self, text: str) -> list[float]:
        """
        Embed a single piece of text into a 768-dim float vector.

        Args:
            text: The text to embed (max ~8192 tokens).

        Returns:
            list[float] of length 768.

        Raises:
            RuntimeError: If Ollama is unreachable or model not found.
        """
        payload = {
            "model": self.model_name,   # "nomic-embed-text"
            "prompt": text,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["embedding"]
        except Exception as exc:
            raise RuntimeError(
                f"NomicEmbedProvider.embed() failed: {exc}. "
                "Is Ollama running? Is nomic-embed-text installed?"
            ) from exc

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> ProviderResponse:
        """Not supported — nomic-embed-text is an embedder only."""
        return ProviderResponse(
            text="",
            provider_id=self.provider_id,
            model_name=self.model_name,
            ok=False,
            error="NomicEmbedProvider does not support text generation. Use OllamaProvider.",
        )

# -*- coding: utf-8 -*-
"""
QI Brain — LLM Provider base class.

Replicates the NEXUS provider pattern exactly (standalone copy, not imported).
See: C:/NEXUS/core/providers/base.py for the original.

All brain providers must inherit from BrainProvider and implement generate().
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProviderResponse:
    """Unified response envelope from any provider."""
    text: str                              # The generated text (cleaned)
    provider_id: str                       # Which provider produced this
    model_name: str                        # Model that was used
    tokens_used: int = 0                   # Approximate token count (if available)
    latency_ms: float = 0.0               # Wall-clock time in ms
    ok: bool = True                        # False if provider errored
    error: Optional[str] = None           # Error message if ok=False
    raw: Optional[dict] = field(default=None, repr=False)  # Raw API response


class BrainProvider(ABC):
    """
    Abstract base class for all QI Brain LLM providers.

    Config comes entirely from the llm_providers table — zero hardcoding.
    Instantiate via ProviderFactory.from_db(provider_id).
    """

    def __init__(
        self,
        provider_id: str,
        display_name: str,
        base_url: str,
        model_name: str,
        timeout_s: int = 60,
        max_tokens: int = 2048,
        api_key: Optional[str] = None,
        config: Optional[dict] = None,
    ):
        self.provider_id  = provider_id
        self.display_name = display_name
        self.base_url     = base_url.rstrip("/")
        self.model_name   = model_name
        self.timeout_s    = timeout_s
        self.max_tokens   = max_tokens
        self.api_key      = api_key
        self.config       = config or {}

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> ProviderResponse:
        """
        Generate a response for the given prompt.

        Args:
            prompt:        User/task prompt.
            system_prompt: Optional system/instruction prompt.
            max_tokens:    Override instance max_tokens for this call.

        Returns:
            ProviderResponse — always returns, never raises.
            On error: ok=False, error=<message>, text="".
        """
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """
        Generate an embedding vector for text.

        Not all providers support this — raise NotImplementedError if unsupported.
        Use NomicEmbedProvider for embedding tasks.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.provider_id!r}, model={self.model_name!r})"

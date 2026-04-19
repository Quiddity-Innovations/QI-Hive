# -*- coding: utf-8 -*-
"""
QI Brain — Provider Factory.

Loads LLM provider config from qi_brain.db and returns the correct
BrainProvider subclass. Zero hardcoded model config anywhere.

Usage:
    from core.providers.factory import ProviderFactory
    provider = ProviderFactory.from_db("ollama_qwen3_8b")
    response = await provider.generate("What is 2+2?")
"""
from __future__ import annotations
import os
from typing import Optional

from ..db import open_brain_db
from .base import BrainProvider
from .ollama import OllamaProvider
from .nomic_embed import NomicEmbedProvider

_TYPE_MAP: dict[str, type[BrainProvider]] = {
    "ollama":       OllamaProvider,
    "nomic_embed":  NomicEmbedProvider,
    # Future: "openai": OpenAIProvider, "anthropic": AnthropicProvider
}


class ProviderNotFoundError(Exception):
    pass


class ProviderFactory:

    @staticmethod
    def from_db(provider_id: str) -> BrainProvider:
        """
        Load a provider by its provider_id from the llm_providers table.

        Args:
            provider_id: e.g. "ollama_qwen3_8b", "nomic_embed_text"

        Returns:
            Instantiated BrainProvider subclass.

        Raises:
            ProviderNotFoundError: if not found or inactive.
        """
        with open_brain_db() as conn:
            row = conn.execute(
                "SELECT * FROM llm_providers WHERE provider_id = ? AND active = 1",
                (provider_id,)
            ).fetchone()

        if not row:
            raise ProviderNotFoundError(
                f"Provider '{provider_id}' not found or inactive in llm_providers."
            )

        ptype = row["provider_type"]
        klass = _TYPE_MAP.get(ptype)
        if not klass:
            raise ProviderNotFoundError(
                f"No Python class registered for provider_type='{ptype}'."
            )

        # Resolve API key from environment variable (never stored as value)
        api_key: Optional[str] = None
        if row["api_key_env"]:
            api_key = os.environ.get(row["api_key_env"])

        return klass(
            provider_id  = row["provider_id"],
            display_name = row["display_name"],
            base_url     = row["base_url"],
            model_name   = row["model_name"],
            timeout_s    = row["timeout_s"],
            max_tokens   = row["max_tokens"],
            api_key      = api_key,
        )

    @staticmethod
    def get_by_role(role: str) -> BrainProvider:
        """
        Get the first active provider matching a role.

        Roles: 'eval' | 'embed' | 'general' | 'heavy'
        """
        with open_brain_db() as conn:
            row = conn.execute(
                "SELECT provider_id FROM llm_providers WHERE role = ? AND active = 1 LIMIT 1",
                (role,)
            ).fetchone()

        if not row:
            raise ProviderNotFoundError(f"No active provider with role='{role}'.")

        return ProviderFactory.from_db(row["provider_id"])

    @staticmethod
    def list_active() -> list[dict]:
        """Return all active providers as plain dicts (for dashboard display)."""
        with open_brain_db() as conn:
            rows = conn.execute(
                "SELECT provider_id, display_name, provider_type, model_name, role, active "
                "FROM llm_providers WHERE active = 1 ORDER BY role, provider_id"
            ).fetchall()
        return [dict(r) for r in rows]

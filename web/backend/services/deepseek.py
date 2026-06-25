"""Backward-compatible shim. Prefer `services.llm` (provider-agnostic gateway).

DeepSeek is now just the default provider behind the unified gateway; these
aliases keep older imports working.
"""
from .llm import LLMError, complete, stream

DeepSeekAPIError = LLMError
call_deepseek = complete
stream_deepseek = stream

__all__ = ["DeepSeekAPIError", "call_deepseek", "stream_deepseek"]

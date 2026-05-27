# Author: kamekingdom (2026-05-27)

from __future__ import annotations


class KameAgentError(Exception):
    """Base error for kame-agent."""


class SafetyError(KameAgentError):
    """Raised when a path, file, or command violates the safety policy."""


class ProposalError(KameAgentError):
    """Raised when an LLM proposal cannot be safely used."""


class LLMError(KameAgentError):
    """Raised when the OpenAI API call or response parsing fails."""

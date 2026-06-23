"""ID helpers for the chat agent."""
from __future__ import annotations

import secrets
import string
import uuid


_ALPHABET = string.ascii_uppercase + string.digits


def new_id(prefix: str) -> str:
    """Return an internal opaque ID with a readable prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def new_analysis_id() -> str:
    """Return a user-visible support ID.

    The ID is short enough to copy, but random enough that it should not
    reveal database volume or allow practical enumeration.
    """
    code = "".join(secrets.choice(_ALPHABET) for _ in range(8))
    return f"BAZI-{code}"


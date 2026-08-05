"""Side-effect-safe access to vnstock's public API."""

import vnai


def _skip_agent_file_setup(*args, **kwargs):
    """Disable vnstock's unrelated AGENTS.md bootstrap during import."""
    return None


_original_agent_setup = vnai.async_setup_agent_environment
vnai.async_setup_agent_environment = _skip_agent_file_setup
try:
    from vnstock import Quote
finally:
    vnai.async_setup_agent_environment = _original_agent_setup


__all__ = ["Quote"]

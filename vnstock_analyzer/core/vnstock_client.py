"""Side-effect-safe access to vnstock's public API."""

import vnai


def _safe_hosting_service(detector):
    """Work around vnstock's uninitialized local-hosting return value."""
    try:
        return detector()
    except UnboundLocalError:
        return "Local or Unknown"


def _skip_agent_file_setup(*args, **kwargs):
    """Disable vnstock's unrelated AGENTS.md bootstrap during import."""
    return None


_original_agent_setup = vnai.async_setup_agent_environment
vnai.async_setup_agent_environment = _skip_agent_file_setup
try:
    from vnstock import Quote, Reference
finally:
    vnai.async_setup_agent_environment = _original_agent_setup

# vnstock 4.0.5/4.0.6 leaves ``hosting_service`` uninitialized on ordinary
# local machines. VCI calls is_colab() before sending a request and therefore
# fails before network I/O. Keep the workaround at this integration boundary
# and catch only that exact upstream failure mode.
from vnstock.core.utils import env as _vnstock_env

_original_hosting_service = _vnstock_env.get_hosting_service


def _patched_hosting_service():
    return _safe_hosting_service(_original_hosting_service)


_vnstock_env.get_hosting_service = _patched_hosting_service


__all__ = ["Quote", "Reference"]

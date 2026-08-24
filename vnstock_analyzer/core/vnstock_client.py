"""Side-effect-safe, bounded access to vnstock's public API."""

import os

import vnai


REQUEST_TIMEOUT_SECONDS = float(
    os.environ.get("VNSTOCK_REQUEST_TIMEOUT_SECONDS", "8")
)


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
from vnstock.core.utils import client as _vnstock_client

_original_hosting_service = _vnstock_env.get_hosting_service


def _patched_hosting_service():
    return _safe_hosting_service(_original_hosting_service)


_vnstock_env.get_hosting_service = _patched_hosting_service


# vnstock's HTTP helper defaults to 30 seconds and its Quote adapter retries
# three times. One degraded endpoint can therefore hold a symbol for ~96s
# before our VCI -> KBS fallback runs. Cap the actual socket wait; healthy local
# requests normally finish well below one second.
_original_send_request_direct = _vnstock_client.send_request_direct


def _bounded_send_request_direct(
    url,
    headers,
    method="GET",
    params=None,
    payload=None,
    timeout=30,
    proxies=None,
):
    bounded_timeout = min(float(timeout), REQUEST_TIMEOUT_SECONDS)
    return _original_send_request_direct(
        url,
        headers,
        method,
        params,
        payload,
        bounded_timeout,
        proxies,
    )


_vnstock_client.send_request_direct = _bounded_send_request_direct


def fetch_history_once(quote, **kwargs):
    """Call one provider attempt, bypassing Quote's hidden 3x retry wrapper."""
    provider = vars(quote).get("_provider")
    history_method = provider.history if provider is not None else quote.history
    return history_method(**kwargs)


__all__ = [
    "Quote",
    "Reference",
    "REQUEST_TIMEOUT_SECONDS",
    "fetch_history_once",
]

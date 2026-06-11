"""Same-origin / loopback request guards for the observer server.

Pure functions only — no handler or socket types. The HTTP handler keeps thin
overridable methods (``_is_loopback`` / ``_is_same_origin_local`` /
``_reject_cross_origin``) that delegate here; tests subclass the handler and
override those methods, so the METHODS are the frozen surface and these
functions are the implementation host.
"""

from __future__ import annotations

from typing import Mapping

_LOOPBACK_HOSTNAMES = frozenset({"localhost", "127.0.0.1", "::1"})

CROSS_ORIGIN_MESSAGE = "cross-origin or non-loopback Host rejected"


def _hostname_of(value: str) -> str:
    """Lowercased hostname from a Host/Origin header value, stripped of scheme
    and port. Handles ``http://host:port/path``, ``host:port`` and bracketed
    IPv6 (``[::1]:port``)."""
    text = value.strip().lower()
    if "://" in text:
        text = text.split("://", 1)[1]
    text = text.split("/", 1)[0]
    if "@" in text:  # strip userinfo (user:pass@host); the real host is after the '@'
        text = text.rsplit("@", 1)[1]
    if text.startswith("["):  # [::1] or [::1]:port
        return text[1:].split("]", 1)[0]
    if text.count(":") == 1:  # host:port (a bare IPv6 like ::1 has >1 colon)
        text = text.rsplit(":", 1)[0]
    return text


def _is_loopback_hostname(value: str) -> bool:
    return _hostname_of(value) in _LOOPBACK_HOSTNAMES


def is_loopback_client(client_ip: str) -> bool:
    """True when the socket peer address is a loopback address."""
    return client_ip in ("127.0.0.1", "::1")


def is_same_origin_local(headers: Mapping[str, str] | None) -> bool:
    """True when a state-changing request is safe to honour: the Host header
    names a loopback address (defends DNS-rebinding, where a browser sends the
    attacker's hostname that resolves to 127.0.0.1) and any Origin header is
    loopback too (defends cross-site POST/DELETE / CSRF). Non-browser clients
    that omit Host/Origin are unaffected."""
    host = headers.get("Host", "") if headers else ""
    if host and not _is_loopback_hostname(host):
        return False
    origin = headers.get("Origin") if headers else None
    if origin and not _is_loopback_hostname(origin):
        return False
    return True


def evaluate_request_guards(
    client_ip: str,
    headers: Mapping[str, str] | None,
    *,
    loopback_message: str | None = None,
    require_same_origin: bool = False,
) -> tuple[int, str, str] | None:
    """Combined guard decision: ``(403, code, message)`` to reject, ``None`` to
    proceed. The loopback (peer-IP) gate runs FIRST, mirroring endpoint order.
    Callers apply only the guards their endpoint historically used — the guard
    matrix is asymmetric by design; never add a guard an endpoint didn't have."""
    if loopback_message is not None and not is_loopback_client(client_ip):
        return (403, "forbidden", loopback_message)
    if require_same_origin and not is_same_origin_local(headers):
        return (403, "forbidden", CROSS_ORIGIN_MESSAGE)
    return None

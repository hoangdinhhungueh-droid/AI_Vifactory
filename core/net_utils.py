"""core/net_utils.py — Canonical Thread-Safe IPv4 Transport Utilities (Rule 125/139).

Eliminates process-global monkeypatching of socket.getaddrinfo by binding connections
directly at the transport/socket level to local IPv4 interface ("0.0.0.0", 0).

Provides:
  1. get_ipv4_transport: httpx.HTTPTransport configured with local_address="0.0.0.0".
  2. get_ipv4_client: httpx.Client configured with IPv4 transport.
  3. get_ipv4_urllib_opener: urllib.request.OpenerDirector configured with IPv4 source address.
  4. ipv4_urlopen: direct replacement for urllib.request.urlopen bound to IPv4.
"""
from __future__ import annotations

import os
import contextlib
import http.client
import logging
import urllib.request
from typing import Any, Optional, Union

import httpx

logger = logging.getLogger(__name__)


def should_force_ipv4() -> bool:
    """Returns True only when explicitly forced via VF_FORCE_IPV4 env toggle (Boss Round 14 Item 7).
    Defaults to False to support modern dual-stack and IPv6-only environments.
    """
    return os.getenv("VF_FORCE_IPV4", "0").strip().lower() in ("1", "true", "yes", "on")


class IPv4HTTPSConnection(http.client.HTTPSConnection):
    """HTTPSConnection explicitly bound to IPv4 source_address without global socket mutations."""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["source_address"] = ("0.0.0.0", 0)
        super().__init__(*args, **kwargs)


class IPv4HTTPConnection(http.client.HTTPConnection):
    """HTTPConnection explicitly bound to IPv4 source_address without global socket mutations."""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["source_address"] = ("0.0.0.0", 0)
        super().__init__(*args, **kwargs)


class IPv4HTTPSHandler(urllib.request.HTTPSHandler):
    """Urllib handler directing HTTPS traffic through IPv4-bound connection."""
    def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        return self.do_open(IPv4HTTPSConnection, req)


class IPv4HTTPHandler(urllib.request.HTTPHandler):
    """Urllib handler directing HTTP traffic through IPv4-bound connection."""
    def http_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        return self.do_open(IPv4HTTPConnection, req)


def get_ipv4_transport(**kwargs: Any) -> httpx.HTTPTransport:
    """Return an httpx.HTTPTransport. If VF_FORCE_IPV4=1, binds local_address to '0.0.0.0'."""
    if should_force_ipv4():
        return httpx.HTTPTransport(local_address="0.0.0.0", **kwargs)
    return httpx.HTTPTransport(**kwargs)


def get_ipv4_client(timeout: float = 15.0, force_ipv4: Optional[bool] = None, **kwargs: Any) -> httpx.Client:
    """Return an httpx.Client configured with transport.
    If force_ipv4 is explicitly True or VF_FORCE_IPV4=1, forces IPv4 binding (Boss Round 14 Item 7);
    otherwise defaults to standard dual-stack transport to prevent breaking IPv6-only environments.
    """
    is_forced = should_force_ipv4() if force_ipv4 is None else force_ipv4
    if is_forced:
        transport = httpx.HTTPTransport(local_address="0.0.0.0")
        return httpx.Client(transport=transport, timeout=timeout, **kwargs)
    return httpx.Client(timeout=timeout, **kwargs)


def get_ipv4_urllib_opener() -> urllib.request.OpenerDirector:
    """Return an OpenerDirector configured with IPv4 HTTP/HTTPS handlers."""
    return urllib.request.build_opener(IPv4HTTPHandler(), IPv4HTTPSHandler())


def ipv4_urlopen(
    req: Union[str, urllib.request.Request],
    timeout: float = 20.0,
    **kwargs: Any,
) -> Any:
    """Execute urlopen via thread-safe IPv4-bound opener director."""
    opener = get_ipv4_urllib_opener()
    return opener.open(req, timeout=timeout, **kwargs)


@contextlib.contextmanager
def force_ipv4_dns():
    """No-op context manager maintained for backward compatibility.
    Transport-level IPv4 binding is used by canonical callers without socket mutations.
    """
    yield

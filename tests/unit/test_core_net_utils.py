#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_core_net_utils.py
Unit tests verifying thread-safe transport-level IPv4 utilities (core/net_utils.py)
without mutating process-global socket.getaddrinfo (Boss Round 11 Item 18).
"""

import socket
import threading
from unittest.mock import MagicMock, patch

from core.net_utils import (
    get_ipv4_transport,
    get_ipv4_client,
    IPv4HTTPSHandler,
    ipv4_urlopen,
)


def test_socket_getaddrinfo_not_mutated():
    """Verify that using core.net_utils functions NEVER mutates process-global socket.getaddrinfo."""
    original_getaddrinfo = socket.getaddrinfo

    # Instantiate transport and client
    transport = get_ipv4_transport()
    assert transport is not None

    client = get_ipv4_client(timeout=5.0)
    assert client is not None
    client.close()

    handler = IPv4HTTPSHandler()
    assert handler is not None

    # Crucial assertion: socket.getaddrinfo must remain untouched (exact identity)
    assert socket.getaddrinfo is original_getaddrinfo, "socket.getaddrinfo was unexpectedly mutated!"


def test_concurrent_threads_no_global_mutation():
    """Multiple concurrent threads acquiring IPv4 clients/transports simultaneously
    must not mutate socket.getaddrinfo or interfere with each other.
    """
    original_getaddrinfo = socket.getaddrinfo
    errors = []

    def worker(idx: int):
        try:
            for _ in range(3):
                # Ensure original_getaddrinfo is still intact at every iteration
                if socket.getaddrinfo is not original_getaddrinfo:
                    errors.append(f"Thread {idx}: socket.getaddrinfo mutated!")
                    break
                t = get_ipv4_transport()
                c = get_ipv4_client(timeout=2.0)
                c.close()
        except Exception as e:
            errors.append(f"Thread {idx} exception: {e}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert not errors, f"Concurrency errors encountered: {errors}"
    assert socket.getaddrinfo is original_getaddrinfo


@patch("urllib.request.build_opener")
def test_ipv4_urlopen_uses_custom_opener(mock_build_opener):
    """ipv4_urlopen must build an opener with IPv4HTTPSHandler without touching global socket."""
    original_getaddrinfo = socket.getaddrinfo
    mock_opener = MagicMock()
    mock_response = MagicMock()
    mock_response.read.return_value = b"test payload"
    mock_opener.open.return_value = mock_response
    mock_build_opener.return_value = mock_opener

    resp = ipv4_urlopen("https://example.com/api", timeout=10.0)
    assert resp.read() == b"test payload"
    mock_build_opener.assert_called_once()
    # Check that IPv4HTTPSHandler was passed to build_opener
    args, _ = mock_build_opener.call_args
    assert any(isinstance(h, IPv4HTTPSHandler) for h in args)
    assert socket.getaddrinfo is original_getaddrinfo


def test_vf_force_ipv4_toggle_behavior(monkeypatch):
    """Test VF_FORCE_IPV4 env toggle defaulting to False (dual-stack) and forcing IPv4 when True (Boss Round 14 Item 7)."""
    from core.net_utils import should_force_ipv4

    # Default: False (dual-stack)
    monkeypatch.delenv("VF_FORCE_IPV4", raising=False)
    assert should_force_ipv4() is False
    c_default = get_ipv4_client(timeout=5.0)
    assert c_default._transport is not None
    c_default.close()

    # Explicitly enabled: True (force IPv4)
    monkeypatch.setenv("VF_FORCE_IPV4", "1")
    assert should_force_ipv4() is True
    c_forced = get_ipv4_client(timeout=5.0)
    assert c_forced._transport is not None
    c_forced.close()

    # Explicit parameter override
    c_param_false = get_ipv4_client(timeout=5.0, force_ipv4=False)
    assert c_param_false is not None
    c_param_false.close()

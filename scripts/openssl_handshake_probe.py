"""Experimental OpenSSL 4 TLS handshake-completion probe for Windows.

This probe is a diagnostic building block, not a benchmark runner. It uses a
trusted CA file and records the time spent in SSL_connect after TCP connects.
No application data is sent. A successful result requires TLS 1.3, the exact
requested group, a valid hostname and certificate, and a non-resumed session.
"""
from __future__ import annotations

import argparse
import ctypes
import ipaddress
import math
import os
from pathlib import Path
import select
import socket
import time


class ProbeError(RuntimeError):
    pass


def probe(host: str, port: int, server_name: str, ca_file: Path,
          mode: str, timeout: float, dll: Path) -> dict:
    if not math.isfinite(timeout) or timeout <= 0 or mode not in ("classical", "hybrid"):
        raise ValueError("invalid timeout or mode")
    try:
        ipaddress.ip_address(server_name)
    except ValueError:
        pass
    else:
        raise ValueError("server-name must be a DNS name, not an IP address")
    group = {"classical": "X25519", "hybrid": "X25519MLKEM768"}[mode]
    if not ca_file.is_file() or not dll.is_file():
        raise ProbeError("CA file or OpenSSL library does not exist")
    dll_dir = os.add_dll_directory(str(dll.parent.resolve()))
    try:
        lib = ctypes.CDLL(str(dll.resolve()))
        ptr, integer, string = ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p

        def bind(name, result, *args):
            function = getattr(lib, name)
            function.restype = result
            function.argtypes = args
            return function

        method = bind("TLS_client_method", ptr)
        ctx_new = bind("SSL_CTX_new", ptr, ptr)
        ctx_free = bind("SSL_CTX_free", None, ptr)
        ctx_verify = bind("SSL_CTX_set_verify", None, ptr, integer, ptr)
        ctx_load = bind("SSL_CTX_load_verify_locations", integer, ptr, string, string)
        conf_new = bind("SSL_CONF_CTX_new", ptr)
        conf_free = bind("SSL_CONF_CTX_free", None, ptr)
        conf_flags = bind("SSL_CONF_CTX_set_flags", ctypes.c_uint, ptr, ctypes.c_uint)
        conf_ctx = bind("SSL_CONF_CTX_set_ssl_ctx", None, ptr, ptr)
        conf_cmd = bind("SSL_CONF_cmd", integer, ptr, string, string)
        conf_finish = bind("SSL_CONF_CTX_finish", integer, ptr)
        ssl_new = bind("SSL_new", ptr, ptr)
        ssl_free = bind("SSL_free", None, ptr)
        ssl_ctrl = bind("SSL_ctrl", ctypes.c_long, ptr, integer, ctypes.c_long, ptr)
        set_host = bind("SSL_set1_host", integer, ptr, string)
        set_fd = bind("SSL_set_fd", integer, ptr, integer)
        connect = bind("SSL_connect", integer, ptr)
        get_error = bind("SSL_get_error", integer, ptr, integer)
        get_group = bind("SSL_get0_group_name", string, ptr)
        get_version = bind("SSL_get_version", string, ptr)
        reused = bind("SSL_session_reused", integer, ptr)
        verify_result = bind("SSL_get_verify_result", ctypes.c_long, ptr)

        ctx = ctx_new(method())
        if not ctx:
            raise ProbeError("unable to create TLS context")
        ssl = None
        try:
            ctx_verify(ctx, 1, None)  # SSL_VERIFY_PEER
            if ctx_load(ctx, os.fsencode(ca_file.resolve()), None) != 1:
                raise ProbeError("unable to load trusted certificate")
            conf = conf_new()
            if not conf:
                raise ProbeError("unable to create configuration context")
            try:
                conf_flags(conf, 0x2 | 0x4)  # configuration-file syntax, client
                conf_ctx(conf, ctx)
                for name, value in ((b"MinProtocol", b"TLSv1.3"),
                                    (b"MaxProtocol", b"TLSv1.3"),
                                    (b"Groups", group.encode("ascii"))):
                    if conf_cmd(conf, name, value) <= 0:
                        raise ProbeError("unsupported TLS configuration: " + name.decode())
                if conf_finish(conf) != 1:
                    raise ProbeError("TLS configuration failed")
            finally:
                conf_free(conf)
            ssl = ssl_new(ctx)
            if not ssl:
                raise ProbeError("unable to create TLS connection")
            host_bytes = server_name.encode("idna")
            if set_host(ssl, host_bytes) != 1:
                raise ProbeError("unable to configure hostname validation")
            # SSL_CTRL_SET_TLSEXT_HOSTNAME / TLSEXT_NAMETYPE_host_name
            sni = ctypes.create_string_buffer(host_bytes)
            if ssl_ctrl(ssl, 55, 0, ctypes.cast(sni, ptr)) != 1:
                raise ProbeError("unable to configure server name indication")
            with socket.create_connection((host, port), timeout=timeout) as sock:
                sock.setblocking(False)
                if sock.fileno() > 0x7fffffff or set_fd(ssl, sock.fileno()) != 1:
                    raise ProbeError("unable to attach socket to OpenSSL")
                start = time.perf_counter_ns()
                deadline = time.monotonic() + timeout
                while True:
                    ret = connect(ssl)
                    if ret == 1:
                        elapsed = time.perf_counter_ns() - start
                        break
                    error = get_error(ssl, ret)
                    if error not in (2, 3):  # WANT_READ, WANT_WRITE
                        raise ProbeError(f"TLS handshake failed (OpenSSL error {error})")
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ProbeError("TLS handshake timed out")
                    read, write, _ = select.select([sock] if error == 2 else [],
                                                   [sock] if error == 3 else [], [], remaining)
                    if not read and not write:
                        raise ProbeError("TLS handshake timed out")
                observed = (get_group(ssl) or b"").decode("ascii", "replace")
                version = (get_version(ssl) or b"").decode("ascii", "replace")
                is_reused = bool(reused(ssl))
                valid = verify_result(ssl) == 0
                if observed.lower() != group.lower() or version != "TLSv1.3" or is_reused or not valid:
                    raise ProbeError("TLS group, version, certificate or session validation failed")
                return {"mode": mode, "tls_version": version, "negotiated_group": observed,
                        "certificate_verified": valid, "session_reused": is_reused,
                        "handshake_ms": elapsed / 1_000_000}
        finally:
            if ssl:
                ssl_free(ssl)
            ctx_free(ctx)
    finally:
        dll_dir.close()


def main() -> int:
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", required=True)
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--server-name", required=True)
    p.add_argument("--ca-file", type=Path, required=True)
    p.add_argument("--mode", choices=("classical", "hybrid"), required=True)
    p.add_argument("--timeout", type=float, default=10)
    p.add_argument("--dll", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(probe(args.host, args.port, args.server_name, args.ca_file,
                               args.mode, args.timeout, args.dll), indent=2))
        return 0
    except (ProbeError, OSError, ValueError) as exc:
        print(f"Probe failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

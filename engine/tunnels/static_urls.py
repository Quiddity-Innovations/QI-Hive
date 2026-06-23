# -*- coding: utf-8 -*-
"""
static_urls.py — QI static (named) tunnel URL resolver
======================================================
Single source of truth for the PERMANENT public URLs that QI services are
reachable on, now that every quick tunnel (random ``*.trycloudflare.com``)
has been migrated to a STATIC NAMED tunnel on ``quiddityinnovations.com``
(see ``tunnels.json`` + ``migrate_named_tunnels.py`` in this folder).

Before the migration, consumers (the Hive dashboard, the launcher, the web
panel) discovered the live URL by tail-parsing cloudflared logs for the last
``trycloudflare.com`` string. Named tunnels never print such a URL, so that
discovery now yields nothing. Instead, every consumer asks THIS module for
the permanent URL keyed by the local port (the one stable identifier shared
across all of them) or by hostname.

Usage:
    import sys
    _TUN = r"C:\\QIH\\engine\\tunnels"
    if _TUN not in sys.path:
        sys.path.insert(0, _TUN)
    from static_urls import url_for_port, url_for_host

    url_for_port(8001)   -> "https://maia.quiddityinnovations.com"
    url_for_host("hive") -> "https://hive.quiddityinnovations.com"

Everything is derived from ``tunnels.json`` — add/rename a tunnel there and
every consumer follows automatically. Zero third-party dependencies.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Optional

HERE = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(HERE, "tunnels.json")


def _fqdn(hostname: str, domain: str) -> str:
    """'@' or '' means the zone apex (bare domain); otherwise host.domain."""
    return domain if hostname in ("@", "") else f"{hostname}.{domain}"


@lru_cache(maxsize=1)
def _load():
    """Build (port_urls, host_urls) from tunnels.json.

    port_urls: {int port -> "https://host.domain"} — for a port served on more
               than one domain (e.g. 8001 on both quiddityinnovations.com and
               quiddam.com) the DEFAULT domain wins, so the canonical URL is
               stable. Override-domain entries only fill ports nothing else
               claims.
    host_urls: {"host" (and "host.domain") -> "https://host.domain"}.
    """
    try:
        cfg = json.load(open(MAP_FILE, encoding="utf-8"))
    except Exception:
        return {}, {}

    default_domain = cfg.get("_meta", {}).get("domain", "quiddityinnovations.com")
    port_urls: dict[int, str] = {}
    port_is_default: dict[int, bool] = {}
    host_urls: dict[str, str] = {}

    for entry in cfg.get("tunnels", []):
        edomain = entry.get("domain", default_domain)
        is_default = edomain == default_domain
        for ing in entry.get("ingress", []):
            host = ing.get("hostname", "")
            fqdn = _fqdn(host, edomain)
            url = f"https://{fqdn}"
            # host lookups: both the short host and the full fqdn point at the url
            if host not in ("@", ""):
                host_urls.setdefault(host, url)
            host_urls.setdefault(fqdn, url)
            # port lookups: prefer the default-domain mapping
            port = ing.get("port")
            if port is None:
                continue
            port = int(port)
            if port not in port_urls or (is_default and not port_is_default.get(port)):
                port_urls[port] = url
                port_is_default[port] = is_default
    return port_urls, host_urls


def url_for_port(port) -> Optional[str]:
    """Permanent https URL serving this local port, or None if unmapped."""
    if port is None:
        return None
    try:
        port = int(port)
    except (TypeError, ValueError):
        return None
    return _load()[0].get(port)


def url_for_host(hostname: Optional[str]) -> Optional[str]:
    """Permanent https URL for a hostname (short 'hive' or full fqdn), or None."""
    if not hostname:
        return None
    return _load()[1].get(hostname)


def port_urls() -> dict:
    """Copy of the full {port -> url} map."""
    return dict(_load()[0])


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    pu, hu = _load()
    print("PORT -> URL")
    for p in sorted(pu):
        print(f"  {p:>6}  {pu[p]}")
    print(f"\n{len(hu)} host aliases, {len(pu)} ports mapped.")

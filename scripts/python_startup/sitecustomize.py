from __future__ import annotations

try:
    import aiohttp.connector
    import aiohttp.resolver

    aiohttp.resolver.DefaultResolver = aiohttp.resolver.ThreadedResolver
    aiohttp.connector.DefaultResolver = aiohttp.resolver.ThreadedResolver
except Exception:
    pass

from __future__ import annotations

import socket

from zeroconf import IPVersion, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

from .config import Settings


def _local_address() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return str(probe.getsockname()[0])
    finally:
        probe.close()


async def register_service(settings: Settings) -> tuple[AsyncZeroconf, ServiceInfo]:
    service_type = "_hwenergy._tcp.local."
    instance = f"p1meter-{settings.serial[-6:]}.{service_type}"
    info = ServiceInfo(
        service_type,
        instance,
        addresses=[socket.inet_aton(_local_address())],
        port=settings.port,
        properties={
            "api_enabled": "1",
            "path": "/api/v1",
            "serial": settings.serial,
            "product_name": settings.device_name,
            "product_type": "HWE-P1",
        },
        server=f"p1meter-{settings.serial[-6:].lower()}.local.",
    )
    zeroconf = AsyncZeroconf(ip_version=IPVersion.V4Only)
    await zeroconf.async_register_service(info)
    return zeroconf, info


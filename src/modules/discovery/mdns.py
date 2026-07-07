"""Bonjour/mDNS service advertisement for local network discovery."""

import logging
import socket

from zeroconf import IPVersion, ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)


class BonjourAdvertiser:
    """Advertise the MacBook server on the local network via Bonjour/mDNS."""

    def __init__(
        self,
        service_name: str,
        port: int,
        host: str = "0.0.0.0",
        enable: bool = True,
    ) -> None:
        """Initialize the Bonjour advertiser.

        Args:
            service_name: Name of the service (e.g., "macbook" -> "macbook.local")
            port: Port number the service is running on
            host: Host address (used to determine IP if needed)
            enable: Whether mDNS advertisement is enabled
        """
        self.service_name = service_name
        self.port = port
        self.host = host
        self.enable = enable
        self.zeroconf: Zeroconf | None = None
        self.service_info: ServiceInfo | None = None

    def start(self) -> None:
        """Start advertising the service on mDNS."""
        if not self.enable:
            logger.info("mDNS advertisement is disabled")
            return

        try:
            # Get the hostname
            hostname = socket.gethostname()
            fqdn = f"{hostname}.local."

            # Get local IP address (for binding on 0.0.0.0)
            if self.host == "0.0.0.0":
                # Discover local IP by connecting to a public DNS
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    sock.connect(("8.8.8.8", 80))
                    local_ip = sock.getsockname()[0]
                finally:
                    sock.close()
            else:
                local_ip = self.host

            # Create service info
            self.service_info = ServiceInfo(
                "_http._tcp.local.",
                f"{self.service_name}._http._tcp.local.",
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties={
                    "path": "/",
                    "version": "0.1.0",
                },
                server=fqdn,
            )

            # Register the service
            self.zeroconf = Zeroconf(interfaces=["default"], ip_version=IPVersion.V4Only)
            self.zeroconf.register_service(self.service_info)
            logger.info(
                f"Registered mDNS service: {self.service_name}.local on {local_ip}:{self.port}"
            )
        except Exception as e:
            logger.error(f"Failed to start mDNS advertisement: {e}")
            self._cleanup()

    def stop(self) -> None:
        """Stop advertising the service on mDNS."""
        if not self.enable or self.zeroconf is None:
            return

        try:
            if self.service_info:
                self.zeroconf.unregister_service(self.service_info)
                logger.info(f"Unregistered mDNS service: {self.service_name}.local")
            self._cleanup()
        except Exception as e:
            logger.error(f"Error stopping mDNS advertisement: {e}")
            self._cleanup()

    def _cleanup(self) -> None:
        """Clean up Zeroconf resources."""
        if self.zeroconf:
            self.zeroconf.close()
            self.zeroconf = None

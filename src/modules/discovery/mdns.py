"""Bonjour/mDNS service advertisement for local network discovery."""

import logging
import socket
import threading
import traceback
import time

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
        self._registration_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start advertising the service on mDNS."""
        if not self.enable:
            logger.info("mDNS advertisement is disabled")
            return

        try:
            # Get local IP address
            local_ip = self._get_local_ip()
            hostname = socket.gethostname()
            fqdn = f"{hostname}.local."

            # Create service info with parsed_addresses for better compatibility
            self.service_info = ServiceInfo(
                "_http._tcp.local.",
                f"{self.service_name}._http._tcp.local.",
                parsed_addresses=[local_ip],
                port=self.port,
                properties={
                    "path": "/",
                    "version": "0.1.0",
                },
                server=fqdn,
            )

            # Initialize Zeroconf with minimal parameters (let it auto-detect interfaces)
            # Run in a separate thread to avoid blocking
            self._registration_thread = threading.Thread(
                target=self._register_service_thread, daemon=True
            )
            self._registration_thread.start()

            logger.info(
                f"Registering mDNS service: {self.service_name}.local on {local_ip}:{self.port}"
            )
        except Exception as e:
            logger.error(f"Failed to start mDNS advertisement: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._cleanup()

    def _register_service_thread(self) -> None:
        """Register service in a separate thread."""
        try:
            # Create Zeroconf with default settings (auto-detects all interfaces)
            self.zeroconf = Zeroconf()
            if self.service_info:
                # Allow name change if service name is not unique on the network
                self.zeroconf.register_service(
                    self.service_info, allow_name_change=True
                )
                logger.info(
                    f"Registered mDNS service: {self.service_name}.local on "
                    f"{self.port} successfully"
                )
            # Keep the thread alive to maintain the registration
            while self.enable and self.zeroconf is not None:
                time.sleep(1)
        except Exception as e:
            logger.error(f"Error registering service: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Cleanup but don't call join from within the thread
            if self.zeroconf:
                try:
                    self.zeroconf.close()
                except Exception as close_error:
                    logger.warning(f"Error closing Zeroconf: {close_error}")
                self.zeroconf = None

    def _get_local_ip(self) -> str:
        """Get the local IP address by connecting to a public host."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Connect to a public DNS (doesn't actually send data)
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
            sock.close()
            return local_ip
        except Exception as e:
            logger.warning(f"Could not determine IP via 8.8.8.8: {e}, falling back to localhost")
            return "127.0.0.1"

    def stop(self) -> None:
        """Stop advertising the service on mDNS."""
        if not self.enable:
            return

        try:
            if self.service_info and self.zeroconf:
                self.zeroconf.unregister_service(self.service_info)
                logger.info(f"Unregistered mDNS service: {self.service_name}.local")
            self._cleanup()
        except Exception as e:
            logger.error(f"Error stopping mDNS advertisement: {e}")
            self._cleanup()

    def _cleanup(self) -> None:
        """Clean up Zeroconf resources."""
        self.enable = False
        if self.zeroconf:
            try:
                self.zeroconf.close()
            except Exception as e:
                logger.warning(f"Error closing Zeroconf: {e}")
            self.zeroconf = None

        # Wait for registration thread to finish (but not if we're in it)
        if (
            self._registration_thread
            and self._registration_thread.is_alive()
            and self._registration_thread != threading.current_thread()
        ):
            self._registration_thread.join(timeout=2)

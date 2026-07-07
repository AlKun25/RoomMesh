"""Tests for mDNS/Bonjour service advertisement."""

import time
from unittest.mock import MagicMock, patch

from src.modules.discovery import BonjourAdvertiser


class TestBonjourAdvertiser:
    """Test BonjourAdvertiser functionality."""

    def test_init_default_values(self) -> None:
        """Test initialization with default values."""
        advertiser = BonjourAdvertiser(
            service_name="macbook",
            port=8000,
        )
        assert advertiser.service_name == "macbook"
        assert advertiser.port == 8000
        assert advertiser.host == "0.0.0.0"
        assert advertiser.enable is True
        assert advertiser.zeroconf is None
        assert advertiser.service_info is None

    def test_init_custom_values(self) -> None:
        """Test initialization with custom values."""
        advertiser = BonjourAdvertiser(
            service_name="myservice",
            port=9000,
            host="127.0.0.1",
            enable=False,
        )
        assert advertiser.service_name == "myservice"
        assert advertiser.port == 9000
        assert advertiser.host == "127.0.0.1"
        assert advertiser.enable is False

    def test_start_creates_service_info(self) -> None:
        """Test that start() creates ServiceInfo and registration thread."""
        advertiser = BonjourAdvertiser(
            service_name="macbook",
            port=8000,
            enable=True,
        )
        advertiser.start()

        # Give thread time to create service info
        time.sleep(0.1)

        # Verify service info was created
        assert advertiser.service_info is not None
        assert advertiser.service_info.name == "macbook._http._tcp.local."
        assert advertiser.service_info.port == 8000
        assert advertiser._registration_thread is not None

        # Cleanup
        advertiser.stop()
        time.sleep(0.5)

    @patch("src.modules.discovery.mdns.socket")
    def test_start_disabled_does_nothing(self, mock_socket) -> None:
        """Test that start() does nothing when mDNS is disabled."""
        advertiser = BonjourAdvertiser(
            service_name="macbook",
            port=8000,
            enable=False,
        )
        advertiser.start()

        # Service info should not be created
        assert advertiser.service_info is None
        assert advertiser.zeroconf is None

    def test_stop_without_zeroconf(self) -> None:
        """Test that stop() handles the case when Zeroconf is None."""
        advertiser = BonjourAdvertiser(
            service_name="macbook",
            port=8000,
            enable=True,
        )
        advertiser.enable = False
        # Should not raise an exception
        advertiser.stop()

    @patch("src.modules.discovery.mdns.socket")
    def test_stop_unregisters_service(self, mock_socket) -> None:
        """Test that stop() unregisters the service."""
        mock_zeroconf_instance = MagicMock()
        mock_sock_instance = MagicMock()
        mock_sock_instance.getsockname.return_value = ("192.168.1.1", 12345)
        mock_socket.socket.return_value.__enter__.return_value = mock_sock_instance
        mock_socket.gethostname.return_value = "MacBook-Pro"

        advertiser = BonjourAdvertiser(
            service_name="macbook",
            port=8000,
            enable=True,
        )
        advertiser.zeroconf = mock_zeroconf_instance
        advertiser.service_info = MagicMock()

        advertiser.stop()

        # Verify service was unregistered and Zeroconf closed
        mock_zeroconf_instance.unregister_service.assert_called_once()
        mock_zeroconf_instance.close.assert_called_once()
        assert advertiser.zeroconf is None

    @patch("src.modules.discovery.mdns.socket")
    def test_cleanup_closes_zeroconf(self, mock_socket) -> None:
        """Test that _cleanup() closes Zeroconf."""
        mock_zeroconf_instance = MagicMock()
        advertiser = BonjourAdvertiser(
            service_name="macbook",
            port=8000,
        )
        advertiser.zeroconf = mock_zeroconf_instance

        advertiser._cleanup()

        mock_zeroconf_instance.close.assert_called_once()
        assert advertiser.zeroconf is None

    def test_get_local_ip(self) -> None:
        """Test local IP detection."""
        advertiser = BonjourAdvertiser(
            service_name="macbook",
            port=8000,
        )
        local_ip = advertiser._get_local_ip()

        # Should return a valid IP address string (not 127.0.0.1 unless disconnected)
        assert isinstance(local_ip, str)
        assert len(local_ip) > 0
        # Should be either a valid IP or the fallback
        assert local_ip in ("127.0.0.1",) or "." in local_ip

    def test_get_local_ip_fallback(self) -> None:
        """Test local IP fallback on error."""
        advertiser = BonjourAdvertiser(
            service_name="macbook",
            port=8000,
        )
        # Mock socket to raise exception
        with patch("src.modules.discovery.mdns.socket.socket", side_effect=Exception("Network error")):
            local_ip = advertiser._get_local_ip()
            assert local_ip == "127.0.0.1"

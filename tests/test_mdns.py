"""Tests for mDNS/Bonjour service advertisement."""

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

    @patch("src.modules.discovery.mdns.socket")
    @patch("src.modules.discovery.mdns.Zeroconf")
    def test_start_creates_service_info(self, mock_zeroconf, mock_socket) -> None:
        """Test that start() creates and registers ServiceInfo."""
        mock_socket.gethostname.return_value = "MacBook-Pro"
        mock_socket.inet_aton.return_value = b"\xc0\xa8\x01\x01"
        mock_sock_instance = MagicMock()
        mock_sock_instance.getsockname.return_value = ("192.168.1.1", 12345)
        mock_socket.socket.return_value.__enter__.return_value = mock_sock_instance

        mock_zeroconf_instance = MagicMock()
        mock_zeroconf.return_value = mock_zeroconf_instance

        advertiser = BonjourAdvertiser(
            service_name="macbook",
            port=8000,
            enable=True,
        )
        advertiser.start()

        # Verify Zeroconf was instantiated
        mock_zeroconf.assert_called_once()

        # Verify service was registered
        mock_zeroconf_instance.register_service.assert_called_once()

    @patch("src.modules.discovery.mdns.socket")
    @patch("src.modules.discovery.mdns.Zeroconf")
    def test_start_disabled_does_nothing(self, mock_zeroconf, mock_socket) -> None:
        """Test that start() does nothing when mDNS is disabled."""
        advertiser = BonjourAdvertiser(
            service_name="macbook",
            port=8000,
            enable=False,
        )
        advertiser.start()

        # Zeroconf should not be instantiated
        mock_zeroconf.assert_not_called()

    def test_stop_without_zeroconf(self) -> None:
        """Test that stop() handles the case when Zeroconf is None."""
        advertiser = BonjourAdvertiser(
            service_name="macbook",
            port=8000,
            enable=True,
        )
        # Should not raise an exception
        advertiser.stop()

    @patch("src.modules.discovery.mdns.Zeroconf")
    def test_stop_unregisters_service(self, mock_zeroconf) -> None:
        """Test that stop() unregisters the service."""
        mock_zeroconf_instance = MagicMock()
        mock_zeroconf.return_value = mock_zeroconf_instance

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

    @patch("src.modules.discovery.mdns.Zeroconf")
    def test_cleanup_closes_zeroconf(self, mock_zeroconf) -> None:
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

    @patch("src.modules.discovery.mdns.socket")
    @patch("src.modules.discovery.mdns.Zeroconf")
    def test_start_with_localhost(self, mock_zeroconf, mock_socket) -> None:
        """Test that start() with localhost doesn't try to discover IP."""
        mock_socket.gethostname.return_value = "MacBook-Pro"
        mock_socket.inet_aton.return_value = b"\x7f\x00\x00\x01"
        mock_zeroconf_instance = MagicMock()
        mock_zeroconf.return_value = mock_zeroconf_instance

        advertiser = BonjourAdvertiser(
            service_name="macbook",
            port=8000,
            host="127.0.0.1",
            enable=True,
        )
        advertiser.start()

        # socket.socket should not be called for localhost
        mock_socket.socket.assert_not_called()
        mock_zeroconf_instance.register_service.assert_called_once()

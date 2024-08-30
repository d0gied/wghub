from unittest import TestCase

from core_api import address


class TestAddress(TestCase):

    def test_network_creation(self):
        net = address.NetworkV4("10.20.30.40/16")
        self.assertEqual(net.ip, "10.20.30.40")
        self.assertEqual(net.network_ip, "10.20.0.0")
        self.assertEqual(net.netmask_bits_count, 16)
        self.assertEqual(net.netmask, 0xFFFF0000)
        self.assertEqual(net.cidr, "10.20.30.40/16")

    def test_ipv4_creation(self):
        ip = address.IPv4("10.20.30.40")
        self.assertEqual(ip.ip, "10.20.30.40")
        self.assertEqual(ip.network_ip, "10.20.30.40")
        self.assertEqual(ip.netmask_bits_count, 32)
        self.assertEqual(ip.netmask, 0xFFFFFFFF)
        self.assertEqual(ip.cidr, "10.20.30.40/32")

    def test_network_equality(self):
        net = address.NetworkV4("10.20.30.40/16")
        self.assertEqual(net, address.NetworkV4("10.20.30.40/16"))
        self.assertEqual(net, "10.20.30.40/16")
        self.assertNotEqual(net, address.NetworkV4("10.20.30.40/24"))
        self.assertNotEqual(net, address.NetworkV4("10.20.30.40/8"))

    def test_contains(self):
        net = address.NetworkV4("10.20.30.40/16")
        self.assertTrue(net.contains(address.IPv4("10.20.30.50")))
        self.assertTrue(net.contains(address.IPv4("10.20.0.0")))
        self.assertFalse(net.contains(address.IPv4("10.21.0.0")))
        self.assertFalse(net.contains(address.IPv4("10.19.30.40")))

        self.assertTrue(net.contains("10.20.30.40/24"))
        self.assertTrue(net.contains("10.20.0.0/24"))
        self.assertTrue(net.contains("10.20.0.0/16"))

        self.assertFalse(net.contains("10.20.30.40/8"))
        self.assertFalse(net.contains("10.0.0.0/16"))
        self.assertFalse(net.contains("10.10.0.10/32"))

        net = address.NetworkV4("0.0.0.0/0")
        self.assertTrue(net.contains("10.20.30.40/16"))
        self.assertTrue(net.contains("10.10.10.10"))

    def test_network_range(self):
        net = address.NetworkV4("10.20.30.0/24")
        self.assertEqual(net.min_ip(), address.IPv4("10.20.30.0"))
        self.assertEqual(net.max_ip(), address.IPv4("10.20.30.255"))
        self.assertEqual(
            list(net.range()),
            [address.IPv4(f"10.20.30.{i}") for i in range(256)],
        )

import unittest
from configgen.point_to_point_topology import NodeInterface, PointToPointTopology
from configgen.isis_topology import ISISInterface, ISISTopology
from configgen.constants import *
from ipaddress import IPv4Address, IPv4Interface
from configgen.config_writer import ConfigWriter


class ISISInterfaceTest(unittest.TestCase):
    def test_loopback(self):
        node_interface = NodeInterface(
            InterfaceTypes.LOOPBACK, get_loopback(0), IPv4Address("1.1.1.1")
        )

        isis_interface = ISISInterface(node_interface, [
            (AddressFamily.IPv4_UNICAST, 1),
            (AddressFamily.IPv6_UNICAST, 10)
        ])

        config_writer = ConfigWriter("test")
        isis_interface.write_config(config_writer)
        self.assertMultiLineEqual(config_writer.__str__(),
                                  "interface Loopback 0\n"
                                  " passive\n"
                                  " address-family ipv4 unicast\n"
                                  "  metric 1\n"
                                  " !\n"
                                  " address-family ipv6 unicast\n"
                                  "  metric 10\n"
                                  " !\n"
                                  "!"
                                  )

    def test_data(self):
        node_interface = NodeInterface(
            InterfaceTypes.DATA, get_data_link(2), IPv4Interface("192.168.1.0/24")
        )

        isis_interface = ISISInterface(node_interface, [
            (AddressFamily.IPv4_UNICAST, 1),
            (AddressFamily.IPv6_UNICAST, 10)
        ])

        config_writer = ConfigWriter("test")
        isis_interface.write_config(config_writer)
        self.assertMultiLineEqual(config_writer.__str__(),
                                  "interface GigabitEthernet 0/0/0/2\n"
                                  " point-to-point\n"
                                  " address-family ipv4 unicast\n"
                                  "  metric 1\n"
                                  " !\n"
                                  " address-family ipv6 unicast\n"
                                  "  metric 10\n"
                                  " !\n"
                                  "!"
                                  )


class ISISTopologyTest(unittest.TestCase):
    @staticmethod
    def test_sample_topology():
        p2p_topo = PointToPointTopology(name="sample-topology", path="../topo-dump")
        p2p_topo.generate_point_to_point_topology(
            [
                ("xr1", "1.1.1.1", "192.168.0.120/24"),
                ("xr2", "2.2.2.2", "192.168.0.121/24"),
                ("xr3", "3.3.3.3", "192.168.0.122/24"),
                ("xr4", "4.4.4.4", "192.168.0.123/24"),
            ],
            [(0, 1), (1, 2), (2, 3), (3, 0)]
        )

        topo = ISISTopology(p2p_topo, "core", DEFAULT_CONFIGS)
        topo.generate_isis_topology({
            (0, 1): [(AddressFamily.IPv4_UNICAST, 10)],
            (1, 2): [(AddressFamily.IPv4_UNICAST, 10)],
            (2, 3): [(AddressFamily.IPv4_UNICAST, 10)],
            (3, 0): [(AddressFamily.IPv4_UNICAST, 10)],
            (1, 0): [(AddressFamily.IPv4_UNICAST, 10)],
            (2, 1): [(AddressFamily.IPv4_UNICAST, 10)],
            (3, 2): [(AddressFamily.IPv4_UNICAST, 10)],
            (0, 3): [(AddressFamily.IPv4_UNICAST, 10)],
        }, {
            0: [(AddressFamily.IPv4_UNICAST, 1)],
            1: [(AddressFamily.IPv4_UNICAST, 1)],
            2: [(AddressFamily.IPv4_UNICAST, 1)],
            3: [(AddressFamily.IPv4_UNICAST, 1)],
        })

        topo.write_config()


if __name__ == '__main__':
    unittest.main()

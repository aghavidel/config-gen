import unittest
from ipaddress import ip_interface, ip_address
from configgen.constants import InterfaceTypes
from configgen.constants import (
    get_mgmt, get_loopback, get_data_link
)
from configgen.config_writer import ConfigWriter
from configgen.point_to_point_topology import NodeInterface
from configgen.point_to_point_topology import PointToPointTopology


class NodeInterfaceTest(unittest.TestCase):
    config_writer = ConfigWriter("tests")

    def test_loopback(self):
        NodeInterfaceTest.config_writer.reset()

        interface = NodeInterface(
            InterfaceTypes.LOOPBACK,
            get_loopback(1),
            ip_interface("192.168.1.1/24"),
            description="Loopback Interface"
        )

        interface.write_config(
            config_writer=NodeInterfaceTest.config_writer
        )

        self.assertMultiLineEqual(NodeInterfaceTest.config_writer.__str__(),
                                  "interface Loopback 1\n"
                                  " no shutdown\n"
                                  " description Loopback Interface\n"
                                  " ipv4 address 192.168.1.1/24\n"
                                  "!")

    def test_data(self):
        NodeInterfaceTest.config_writer.reset()

        interface = NodeInterface(
            InterfaceTypes.DATA,
            get_data_link(1),
            ip_interface("192.168.1.1/24"),
            cdp=True,
            description="Ethernet Interface"
        )

        interface.write_config(
            config_writer=NodeInterfaceTest.config_writer
        )

        self.assertMultiLineEqual(NodeInterfaceTest.config_writer.__str__(),
                                  "interface GigabitEthernet 0/0/0/1\n"
                                  " no shutdown\n"
                                  " description Ethernet Interface\n"
                                  " cdp\n"
                                  " ipv4 address 192.168.1.1/24\n"
                                  "!")

    def test_mgmt(self):
        NodeInterfaceTest.config_writer.reset()

        interface = NodeInterface(
            InterfaceTypes.MGMT,
            get_mgmt(0),
            ip_address("192.168.1.1"),
            description="Management Interface"
        )

        interface.write_config(
            config_writer=NodeInterfaceTest.config_writer
        )

        self.assertMultiLineEqual(NodeInterfaceTest.config_writer.__str__(),
                                  "interface MgmtEth 0/RP0/CPU0/0\n"
                                  " no shutdown\n"
                                  " description Management Interface\n"
                                  " ipv4 address 192.168.1.1/32\n"
                                  "!")


class PointToPointTopologyTest(unittest.TestCase):
    @staticmethod
    def test_sample_topology():
        topo = PointToPointTopology(name="sample-topology", path="../topo-dump")
        topo.generate_point_to_point_topology(
            [
                ("xr1", "1.1.1.1", "192.168.0.120/24"),
                ("xr2", "2.2.2.2", "192.168.0.121/24"),
                ("xr3", "3.3.3.3", "192.168.0.122/24"),
                ("xr4", "4.4.4.4", "192.168.0.123/24"),
            ],
            [(0, 1), (1, 2), (2, 3), (3, 0)]
        )
        topo.write_config()


if __name__ == '__main__':
    unittest.main()

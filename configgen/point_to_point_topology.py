import os.path
from ipaddress import ip_network
from ipaddress import IPv4Address, IPv4Interface, IPv4Network
from typing import List, Union, Tuple, Dict
from .config_writer import ConfigWriter
from .constants import *


class NodeInterface:
    """
    Configures an interface. Either Loopback, Management or Data.
    """

    @staticmethod
    def _set_up() -> str:
        return f"no shutdown"

    @staticmethod
    def _enable_cdp() -> str:
        return f"cdp"

    def __init__(self, interface_type: InterfaceTypes, name: str, network: Union[IPv4Interface, IPv4Address],
                 cdp: bool = False, description: str = None) -> None:
        self.name = name
        self.type = interface_type
        self.network = network
        self.cdp = cdp
        self.description = description

    def _assign_description(self) -> str:
        return f"description {self.description}"

    def _interface_config_start(self) -> str:
        return f"interface {self.name}"

    def _assign_ipv4_address(self) -> str:
        if isinstance(self.network, IPv4Address):
            return f"ipv4 address {IPv4Interface(self.network)}"
        return f"ipv4 address {self.network}"

    def write_config(self, config_writer: ConfigWriter) -> None:
        config_writer.add_config(self._interface_config_start())
        config_writer.indent()
        config_writer.add_config(self._set_up())

        if self.description:
            config_writer.add_config(self._assign_description())

        if self.type == InterfaceTypes.DATA:
            if self.cdp:
                config_writer.add_config(self._enable_cdp())

        config_writer.add_config(self._assign_ipv4_address())
        config_writer.unindent()


class DataNode:
    @staticmethod
    def _set_cdp() -> str:
        return f"cdp"

    def __init__(self, hostname: str, identity: IPv4Address, mgmt: IPv4Interface, cdp: bool = False) -> None:
        self.hostname = hostname
        self.identity = identity
        self.mgmt = mgmt
        self.next_loopback = 0
        self.next_data = 0
        self.interfaces: List[NodeInterface] = []

        if identity:
            self.create_new_loopback(network=identity)
        if mgmt:
            self.up_management_interface(network=mgmt)

        self.identity_interface = self.interfaces[0]
        self.cdp = cdp

    def _set_hostname(self) -> str:
        return f"hostname {self.hostname}"

    def create_new_loopback(self, network: Union[IPv4Interface, IPv4Address],
                            description: str = None):
        self.interfaces.append(NodeInterface(
            InterfaceTypes.LOOPBACK,
            get_loopback(self.next_loopback),
            network,
            description=description
        ))
        self.next_loopback += 1

    def create_new_data_link(self, network: Union[IPv4Interface, IPv4Address],
                             cdp: bool = False, description: str = None) -> NodeInterface:
        new_interface = NodeInterface(
            InterfaceTypes.DATA,
            get_data_link(self.next_data),
            network,
            cdp=cdp,
            description=description
        )

        self.interfaces.append(new_interface)
        self.next_data += 1

        return new_interface

    def up_management_interface(self, network: Union[IPv4Interface, IPv4Address]):
        self.interfaces.append(NodeInterface(
            InterfaceTypes.MGMT,
            get_mgmt(0),
            network
        ))

    def write_config(self, config_writer: ConfigWriter):
        config_writer.line_return()
        config_writer.add_config(self._set_hostname())
        if self.cdp:
            config_writer.add_config(self._set_cdp())

        for interface in self.interfaces:
            interface.write_config(config_writer)


class PointToPointTopology:
    @staticmethod
    def _get_interface_pairs(network: IPv4Network) -> Tuple[IPv4Interface, IPv4Interface]:
        prefix_len = network.prefixlen
        return (
            IPv4Interface(network[1].__str__() + "/" + str(prefix_len)),
            IPv4Interface(network[2].__str__() + "/" + str(prefix_len)),
        )

    def __init__(self, name: str, path: str = None, config: dict = DEFAULT_CONFIGS):
        self.nodes: List[DataNode] = []
        self.name = name

        if not path:
            self.path = "./" + self.name
        else:
            self.path = os.path.join(path, self.name)

        self.config = config
        self.subnets = ip_network(
            self.config[ConfigKeys.DATA_LINK_NETWORK]
        ).subnets(
            new_prefix=self.config[ConfigKeys.DATA_LINK_SUBNET_LEN]
        )
        self.interface_mapping: Dict[Tuple, NodeInterface] = dict()

    def _add_node(self, hostname: str, identity: Union[IPv4Interface, IPv4Address], mgmt: IPv4Interface):
        self.nodes.append(
            DataNode(hostname, identity, mgmt, self.config[ConfigKeys.CDP])
        )

    def _add_link(self, i, j):
        node_i = self.nodes[i]
        node_j = self.nodes[j]

        (endpoint_i, endpoint_j) = self._get_interface_pairs(next(self.subnets))

        interface_i = node_i.create_new_data_link(
            endpoint_i,
            self.config[ConfigKeys.CDP],
            description=None
        )

        interface_j = node_j.create_new_data_link(
            endpoint_j,
            self.config[ConfigKeys.CDP],
            description=None
        )

        self.interface_mapping[(i, j)] = interface_j
        self.interface_mapping[(j, i)] = interface_i

    def generate_point_to_point_topology(self, node_identifiers: List[Tuple[str, str, str]],
                                         links: List[Tuple[int, int]]):
        for hostname, mgmt, identifier in node_identifiers:
            self._add_node(hostname, IPv4Interface(mgmt), IPv4Interface(identifier))

        for i, j in links:
            self._add_link(i, j)

    def get_transmit_data_interface(self, i: int, j: int) -> NodeInterface:
        return self.interface_mapping.get((i, j))

    def write_config(self):
        os.makedirs(self.path, exist_ok=True)
        for node in self.nodes:
            config_writer = ConfigWriter(node.hostname)
            node.write_config(config_writer)
            config_writer.write(self.path)

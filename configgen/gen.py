import os.path
from ipaddress import ip_network
from ipaddress import IPv4Address, IPv4Interface, IPv4Network
import textwrap
from typing import List, Union, Tuple
from .config_writer import ConfigWriter
from .constants import *


class NodeInterface:
    """
    Configures an interface. Either Loopback, Management or Data.
    """

    @staticmethod
    def _set_up() -> str:
        return f"no shutdown"

    def _interface_config_start(self) -> str:
        return f"interface {self.name}"

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
                             cdp: bool = False, description: str = None):
        self.interfaces.append(NodeInterface(
            InterfaceTypes.DATA,
            get_data_link(self.next_data),
            network,
            cdp=cdp,
            description=description
        ))
        self.next_data += 1

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

    def _add_node(self, hostname: str, identity: Union[IPv4Interface, IPv4Address], mgmt: IPv4Interface):
        self.nodes.append(
            DataNode(hostname, identity, mgmt, self.config[ConfigKeys.CDP])
        )

    def _add_link(self, i, j):
        node_i = self.nodes[i]
        node_j = self.nodes[j]

        (endpoint_i, endpoint_j) = self._get_interface_pairs(next(self.subnets))

        node_i.create_new_data_link(
            endpoint_i,
            self.config[ConfigKeys.CDP],
            description=None
        )

        node_j.create_new_data_link(
            endpoint_j,
            self.config[ConfigKeys.CDP],
            description=None
        )

    def generate_point_to_point_topology(self, node_identifiers: List[Tuple[str, str, str]],
                                         links: List[Tuple[int, int]]):
        for hostname, mgmt, identifier in node_identifiers:
            self._add_node(hostname, IPv4Interface(mgmt), IPv4Interface(identifier))

        for i, j in links:
            self._add_link(i, j)

    def write_config(self):
        os.makedirs(self.path, exist_ok=True)
        for node in self.nodes:
            config_writer = ConfigWriter(node.hostname)
            node.write_config(config_writer)
            config_writer.write(self.path)


class ISISNode:
    @staticmethod
    def zero_pad_octet(octet: str) -> str:
        return (3 - len(octet)) * "0" + octet

    @staticmethod
    def _advertise_address_family(af: AddressFamily) -> str:
        return f"address-family {af}"

    @staticmethod
    def _configure_address_family() -> str:
        return f"metric-style wide"

    @staticmethod
    def _configure_address_family_metric(metric: int) -> str:
        return f"metric {metric}"

    def __init__(self, data_node: DataNode, is_level: ISLevel, process_name: str,
                 config: dict = DEFAULT_CONFIGS) -> None:
        self.data_node = data_node
        self.net_id = ISISNode.generate_net_id(self.data_node.identity)
        self.is_level = is_level
        self.process_name = process_name
        self.config = config

    def generate_net_id(self, identity: IPv4Address) -> str:
        octets = [ISISNode.zero_pad_octet(octet) for octet in str(identity).split(".")]
        net_parts = textwrap.wrap("".join(octets), 3)
        return ".".join([
            self.config[ConfigKeys.DEFAULT_ISIS_AFI],
            self.config[ConfigKeys.DEFAULT_ISIS_AREA_NUM],
            *net_parts,
            self.config[ConfigKeys.DEFAULT_ISIS_SELECTOR]
        ])

    def _create_isis_process(self) -> str:
        return f"router isis {self.process_name}"

    def _configure_isis_process(self, is_level: ISLevel) -> List[str]:
        return [
            f"is-type {is_level}",
            f"net {self.net_id}"
        ]

    # def _configure_interfaces(self) -> List[str]:
    #     pass

    def _configure_interfaces(self, config_writer: ConfigWriter, metric_dict: dict):
        for interface in self.data_node.interfaces:
            metric = metric_dict.get(interface.name)
            self._configure_interface(config_writer, interface, metric)

    def _configure_interface(self, config_writer: ConfigWriter, interface: NodeInterface, metric: int):
        if interface.type == InterfaceTypes.MGMT:
            return
        
        config_writer.add_config(f"interface {interface.name}")
        config_writer.indent()
        
        if interface.type == InterfaceTypes.LOOPBACK:
            self._configure_loopback_interface(config_writer, metric)
        elif interface.type == InterfaceTypes.DATA:
            self._configure_data_interface(config_writer, metric)

        config_writer.unindent()

    def _configure_loopback_interface(self, config_writer: ConfigWriter, metric: int):
        config_writer.add_config([
            "passive",
            self._advertise_address_family(AddressFamily.IPv4_UNICAST)
        ])

        config_writer.indent()
        config_writer.add_config(self._configure_address_family_metric(metric))
        config_writer.unindent()

    def _configure_data_interface(self, config_writer: ConfigWriter, metric: int):
        config_writer.add_config([
            "point-to-point",
            self._advertise_address_family(AddressFamily.IPv4_UNICAST)
        ])

        config_writer.indent()
        config_writer.add_config(self._configure_address_family_metric(metric))
        config_writer.unindent()

    def write_config(self, config_writer: ConfigWriter, **kwargs):
        metric_dict = kwargs['metrics']
        
        config_writer.add_config(self._create_isis_process(self.process_name))
        
        config_writer.indent()
        config_writer.add_config([
            self._configure_isis_prcess(self.is_level),
            self._advertise_address_family(AddressFamily.IPv4_UNICAST)
        ])

        config_writer.indent()
        config_writer.add_config([
            self._configure_address_family()
        ])
        config_writer.unindent()

        self._configure_interfaces(config_writer, metric_dict)
        config_writer.line_return()


# class Topology:
#     global_datalink_indexer = 1

#     @classmethod
#     def get_next_data_link_pair(cls):

# if __name__ == '__main__':
#     config_writer = ConfigWriter("tests")
#     isis_node = ISISNode(ip_address("192.168.50.1"), [], ISLevel.LEVEL_2, "core")
#     isis_node.write_config(config_writer, metric_dict={"Loopback 0": 1})

# n = NodeInterface(InterfaceTypes.LOOPBACK, ip_address("192.168.1.1"))
# print(n._assign_ipv4_address(ip_address("192.168.1.1")))

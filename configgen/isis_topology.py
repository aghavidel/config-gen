import os.path
import textwrap
from .point_to_point_topology import *


class ISISInterface:
    @staticmethod
    def _advertise_address_family(af: AddressFamily) -> str:
        return f"address-family {af}"

    @staticmethod
    def _configure_address_family_metric(metric: int) -> str:
        return f"metric {metric}"

    def __init__(self, node_interface: NodeInterface, af_metric_list: List[Tuple[AddressFamily, int]]):
        self.node_interface = node_interface
        self.af_metric_list = af_metric_list

    def _configure_loopback_interface(self, config_writer: ConfigWriter):
        config_writer.add_config(f"interface {self.node_interface.name}")

        config_writer.indent()
        config_writer.add_config("passive")

        for af, metric in self.af_metric_list:
            config_writer.add_config(self._advertise_address_family(af))
            config_writer.indent()
            config_writer.add_config(self._configure_address_family_metric(metric))
            config_writer.unindent()

        config_writer.unindent()

    def _configure_data_interface(self, config_writer: ConfigWriter):
        config_writer.add_config(f"interface {self.node_interface.name}")

        config_writer.indent()
        config_writer.add_config("point-to-point")

        for af, metric in self.af_metric_list:
            config_writer.add_config(self._advertise_address_family(af))
            config_writer.indent()
            config_writer.add_config(self._configure_address_family_metric(metric))
            config_writer.unindent()

        config_writer.unindent()

    def write_config(self, config_writer: ConfigWriter):
        if self.node_interface.type == InterfaceTypes.MGMT:
            return

        if self.node_interface.type == InterfaceTypes.LOOPBACK:
            self._configure_loopback_interface(config_writer)
        elif self.node_interface.type == InterfaceTypes.DATA:
            self._configure_data_interface(config_writer)

        config_writer.unindent()


class ISISNode:
    @staticmethod
    def _zero_pad_octet(octet: str) -> str:
        return (3 - len(octet)) * "0" + octet

    def __init__(self, data_node: DataNode, is_level: ISLevel, process_name: str,
                 config: dict = DEFAULT_CONFIGS) -> None:
        self.data_node = data_node
        self.net_id = self._generate_net_id()
        self.is_level = is_level
        self.process_name = process_name
        self.config = config
        self.interfaces: List[ISISInterface] = []

    def _generate_net_id(self) -> str:
        octets = [ISISNode._zero_pad_octet(octet) for octet in str(self.data_node.identity).split(".")]
        net_parts = textwrap.wrap("".join(octets), 3)
        return ".".join([
            self.config[ConfigKeys.DEFAULT_ISIS_AFI],
            self.config[ConfigKeys.DEFAULT_ISIS_AREA_NUM],
            *net_parts,
            self.config[ConfigKeys.DEFAULT_ISIS_SELECTOR]
        ])

    def _create_isis_process(self) -> str:
        return f"router isis {self.process_name}"

    def _configure_isis_process(self) -> List[str]:
        return [
            f"is-type {self.is_level}",
            f"net {self.net_id}"
        ]

    def _configure_process_address_family(self, config_writer: ConfigWriter):
        for af in self.config[ConfigKeys.DEFAULT_ISIS_ADDRESS_FAMILIES]:
            config_writer.add_config(f"address-family {af}")

            config_writer.indent()
            config_writer.add_config(f"metric-style wide")
            config_writer.unindent()

    def create_new_isis_link(self, interface: NodeInterface, af_metric_list: List[Tuple[AddressFamily, int]]):
        self.interfaces.append(ISISInterface(interface, af_metric_list))

    def create_isis_identifier_link(self, af_metric_list: List[Tuple[AddressFamily, int]]):
        self.interfaces.append(ISISInterface(self.data_node.identity_interface, af_metric_list))

    def write_config(self, config_writer: ConfigWriter):
        config_writer.line_return()
        config_writer.add_config(self._create_isis_process())

        config_writer.indent()
        config_writer.add_config(self._configure_isis_process())
        self._configure_process_address_family(config_writer)

        for interface in self.interfaces:
            interface.write_config(config_writer)
        config_writer.unindent()


class ISISTopology:
    def __init__(self, point_to_point_topology: PointToPointTopology,
                 process_name: str, config: dict = DEFAULT_CONFIGS):
        self.point_to_point_topology = point_to_point_topology
        self.config = config
        self.process_name = process_name
        self.is_level = config[ConfigKeys.IS_LEVEL]
        self.nodes = [
            ISISNode(data_node, self.is_level, self.process_name, config)
            for data_node in self.point_to_point_topology.nodes
        ]

    def _add_link(self, i, j, af_metric_list: List[Tuple[AddressFamily, int]]):
        transmit_interface = self.\
            point_to_point_topology.\
            get_transmit_data_interface(i, j)

        self.nodes[i].create_new_isis_link(transmit_interface, af_metric_list)

    def _up_identifier_links(self, identifier_af_metric_descriptor: Dict[
        int, List[Tuple[AddressFamily, int]]
    ]):
        for i, af_metric_list in identifier_af_metric_descriptor.items():
            self.nodes[i].create_isis_identifier_link(af_metric_list)

    def generate_isis_topology(self, af_metric_descriptor: Dict[
        Tuple[int, int],
        List[Tuple[AddressFamily, int]]
    ], identifier_af_metric_descriptor: Dict[
        int, List[Tuple[AddressFamily, int]]
    ]):
        self._up_identifier_links(identifier_af_metric_descriptor)
        for i, j in af_metric_descriptor.keys():
            self._add_link(i, j, af_metric_descriptor[(i, j)])

    def write_config(self):
        os.makedirs(self.point_to_point_topology.path, exist_ok=True)
        for node in self.nodes:
            config_writer = ConfigWriter(node.data_node.hostname)
            node.write_config(config_writer)
            config_writer.write(self.point_to_point_topology.path, append=True)

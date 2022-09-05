from .isis_topology import *


class BGPNeighbor:
    @staticmethod
    def _advertise_address_family(af: AddressFamily) -> str:
        return f"address-family {af}"

    def __init__(self, neighbor_identifier: IPv4Address, neighbor_as: int,
                 update_source: NodeInterface, address_families: List[AddressFamily]):
        self.neighbor_identifier = neighbor_identifier
        self.neighbor_as = neighbor_as
        self.update_source = update_source
        self.address_families = address_families

    def _neighbor_header(self) -> str:
        return f"neighbor {self.neighbor_identifier}"

    def _configure_neighbor_source(self) -> List[str]:
        return [
            f"remote-as {self.neighbor_as}",
            f"update-source {self.update_source}"
        ]

    def write_config(self, config_writer: ConfigWriter):
        config_writer.add_config(self._neighbor_header())

        config_writer.indent()
        config_writer.add_config(self._configure_neighbor_source())
        for af in self.address_families:
            config_writer.add_config(self._advertise_address_family(af))
            config_writer.indent()
            config_writer.unindent()
        config_writer.unindent()


class BGPNode:
    @staticmethod
    def _advertise_network(network: IPv4Network) -> str:
        return f"network {network}"

    @staticmethod
    def _advertise_address_family(af: AddressFamily) -> str:
        return f"address-family {af}"

    def __init__(self, igp_node: ISISNode, asn: int):
        self.igp_node = igp_node
        self.asn = asn
        self.af_prefixes: List[Tuple[IPv4Interface, IPv4Network, List[AddressFamily]]] = []
        self.neighbors: List[BGPNeighbor] = []

    def _add_neighbor(self, identifier: IPv4Address, asn: int, address_families: List[AddressFamily]):
        self.neighbors.append(
            BGPNeighbor(
                identifier, asn,
                self.igp_node.data_node.identity_interface,
                address_families
            )
        )

    def _create_bgp_process(self, config_writer: ConfigWriter):
        config_writer.add_config(f"router bgp {self.asn}")
        config_writer.indent()
        config_writer.add_config(f"bgp router-id {self.igp_node.data_node.identity}")

    def _add_prefix(self, advertised_interface: IPv4Interface,
                    advertised_network: IPv4Network, af_list: List[AddressFamily]):
        self.igp_node.data_node.create_new_loopback(
            advertised_interface,
            description="BGP Reachable"
        )

        self.af_prefixes.append(
            (advertised_interface, advertised_network, af_list)
        )

    def _get_af_classes(self) -> Dict[AddressFamily, List[IPv4Network]]:
        af_networks = {
            af: [] for af in AddressFamily.get_supported_address_families()
        }

        for _, network, address_families in self.af_prefixes:
            for af in address_families:
                af_networks[af].append(network)

        return af_networks

    def _advertise_prefixes(self, config_writer: ConfigWriter):
        af_networks = self._get_af_classes()

        for af, networks in af_networks.items():
            config_writer.add_config(self._advertise_address_family(af))
            config_writer.indent()
            config_writer.add_config([
                self._advertise_network(network) for network in networks
            ])
            config_writer.unindent()

    def _peer(self, config_writer: ConfigWriter):
        for neighbor in self.neighbors:
            neighbor.write_config(config_writer)

    def write_config(self, config_writer: ConfigWriter):
        config_writer.line_return()
        self._create_bgp_process(config_writer)
        self._advertise_prefixes(config_writer)
        self._peer(config_writer)
        config_writer.unindent()


class BGPTopology:
    def __init__(self, igp_topology: ISISTopology):
        self.igp_topology = igp_topology
        self.node_dict: Dict[int, BGPNode] = {}

        self.af_prefix_descriptor: Dict[
            int,
            List[Tuple[IPv4Interface, IPv4Network, List[AddressFamily]]]
        ] = {}

    def _add_node(self, index: int, asn: int):
        self.node_dict[index] = BGPNode(
            self.igp_topology.nodes[index], asn
        )

    # def _add_peering(self, i, j, ):


    # def generate_bgp_topology(self, ):

import unittest
from configgen.gen import PointToPointTopology


class PointToPointTopologyTest(unittest.TestCase):
    @staticmethod
    def test_sample_topology():
        topo = PointToPointTopology(name="sample-topology", path="../topo-dump")
        topo.generate_point_to_point_topology(
            [
                ("xr1", "192.168.0.120/24", "1.1.1.1"),
                ("xr2", "192.168.0.121/24", "2.2.2.2"),
                ("xr3", "192.168.0.122/24", "3.3.3.3")
            ],
            [(0, 1), (1, 2)]
        )
        topo.write_config()


if __name__ == '__main__':
    unittest.main()

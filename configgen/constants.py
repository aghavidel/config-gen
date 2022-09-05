import enum

INDENT = " "

BREAK = "!"

COMMENT = "!! "

END = "end"

DATA_LINK_PREFIX = "GigabitEthernet 0/0/0/"

MGMT_LINK_PREFIX = "MgmtEth 0/RP0/CPU0/"

LOOPBACK_LINK_PREFIX = "Loopback "

get_loopback = lambda n: LOOPBACK_LINK_PREFIX + str(n)
get_data_link = lambda n: DATA_LINK_PREFIX + str(n)
get_mgmt = lambda n: MGMT_LINK_PREFIX + str(0)


class StringValuedEnum(enum.Enum):
    def __str__(self) -> str:
        return str(self.value)


class InterfaceTypes(StringValuedEnum):
    LOOPBACK = "loopback"
    DATA = "data"
    MGMT = "management"


class LogLevel(StringValuedEnum):
    EMERG = "emergencies"
    ALERT = "alerts"
    CRIT = "critical"
    ERR = "errors"
    WARN = "warnings"
    NOTIF = "notification"
    INFO = "informational"
    DEBG = "debugging"


class SSHServer(StringValuedEnum):
    V1 = "v1"
    V2 = "v2"


class ISLevel(StringValuedEnum):
    LEVEL_1 = "level-1"
    LEVEL_1_2 = "level-1-2"
    LEVEL_2 = "level-2-only"


class AddressFamily(StringValuedEnum):
    IPv4_UNICAST = "ipv4 unicast"
    IPv6_UNICAST = "ipv6 unicast"

    @classmethod
    def get_supported_address_families(cls):
        return [
            getattr(cls, attr) for attr in cls.__dict__
            if not callable(getattr(cls, attr))
            and not attr.startswith("__")
            and not attr.startswith("_")
        ]


class ConfigKeys:
    CDP = "cdp"
    TELNET_MAX_SERVER = "telnet-max-server"
    LOGGING_LEVEL = "logging-level"
    IS_LEVEL = "is-level"
    DATA_LINK_NETWORK = "data-link-network"
    DATA_LINK_SUBNET_LEN = "data-link-subnet-len"
    DEFAULT_ISIS_AFI = "default-isis-afi"
    DEFAULT_ISIS_AREA_NUM = "default-isis-area-num"
    DEFAULT_ISIS_SELECTOR = "default-isis-selector"
    DEFAULT_ISIS_ADDRESS_FAMILIES = "default-isis-af"


DEFAULT_CONFIGS = {
    "cdp": True,
    "telnet-max-server": 100,
    "logging-level": LogLevel.INFO,
    "is-level": ISLevel.LEVEL_2,
    "data-link-network": "172.50.0.0/16",
    "data-link-subnet-len": 24,
    "default-isis-afi": "49",
    "default-isis-area-num": "0001",
    "default-isis-selector": "00",
    "default-isis-af": [
        AddressFamily.IPv4_UNICAST
    ]
}

if __name__ == '__main__':
    print(AddressFamily.get_supported_address_families())

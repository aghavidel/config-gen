import os
import socket
import telnetlib
import time
from getpass import getpass
from typing import Dict, Tuple


class HostCreds:
    @staticmethod
    def add_cred(path: str, hostname: str):
        user = input("Username: ")
        passwd = getpass("Password: ")
        with open(os.path.join(path, f"{hostname}.cred"), "w") as cred_file:
            cred_file.write(f"{user}:{passwd}")

    @staticmethod
    def get_cred(path: str, hostname: str) -> Tuple[str, str]:
        with open(os.path.join(path, f"{hostname}.cred")) as cred_file:
            user_pass = cred_file.read().split(":")

        return user_pass[0], user_pass[1]


class Deployer:
    DEFAULT_TIMEOUT = 10
    DEFAULT_PUSH_TIMEOUT = 2

    @staticmethod
    def _cold_boot(t: telnetlib.Telnet, user: str, passwd: str):
        t.write(user.encode("utf-8"))
        t.read_until(b"password:")
        t.write(passwd.encode("utf-8"))
        t.read_until(b"password")
        t.write(passwd.encode("utf-8"))

        print("Finished cold boot configuration")

    @staticmethod
    def _login(t: telnetlib.Telnet, user: str, passwd: str):
        t.write(user.encode("utf-8"))
        t.read_until(b"password:")
        t.write(passwd.encode("utf-8"))

        print(f"Logged in to host {t.get_socket()}")

    def __init__(self, path: str, namespace: str, host_ports: Dict[str, int]):
        self.path = path
        self.namespace = namespace
        self.host_ports = host_ports
        self._check_topology()

    def _check_topology(self):
        for file_name in os.listdir(self.path):
            if file_name.endswith(".conf"):
                hostname = file_name.split(".conf")[0]
                assert self.host_ports.__contains__(hostname), f"Host {hostname} not specified"

                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.connect((self.namespace, self.host_ports[hostname]))
                except socket.error as e:
                    raise RuntimeError(f"Connection to remote host at "
                                       f"{(self.namespace, self.host_ports[hostname])}"
                                       "refused."
                                       "Details:\n"
                                       f"{e}")
                finally:
                    s.close()

        for hostname in self.host_ports.keys():
            assert os.path.exists(os.path.join(
                self.path, f"{hostname}.cred"
            )), f"Host {hostname} has no matching credential file"

        print("Topology data is OK")

    def _write_config(self, hostname: str, t: telnetlib.Telnet, configs: str):
        t.write(b"configure")
        t.read_until(f"{hostname} (config)#".encode("utf-8"))
        t.write(configs.encode("utf-8"))
        time.sleep(self.DEFAULT_PUSH_TIMEOUT)
        t.write(b"commit")

        print("Pushed configurations")

    def _start_session(self, hostname: str):
        with open(os.path.join(self.path, f"{hostname}.conf"), "r") as config_file:
            configs = config_file.read()
        user, passwd = HostCreds.get_cred(self.path, hostname)

        t = telnetlib.Telnet(host=self.namespace, port=self.host_ports[hostname])
        idx, _, data = t.expect([b"Enter root-system username:", b"username:"], self.DEFAULT_TIMEOUT)

        if idx == 0:
            self._cold_boot(t, user, passwd)
        elif idx == 1:
            self._login(t, user, passwd)
        else:
            t.close()
            raise RuntimeError("Error while negotiating connection.\n"
                               "Last input:\n"
                               f"{data}")

        self._write_config(hostname, t, configs)
        t.close()

        print(f"Connection to {hostname} terminated gracefully.")

    def deploy(self):
        for hostname in self.host_ports.keys():
            try:
                self._start_session(hostname)
            except RuntimeError as e:
                print(f"Failed to push configuration for host {hostname}\n."
                      "Reason:\n"
                      f"{e}")

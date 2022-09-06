import os
import socket
import telnetlib
import time
from getpass import getpass
from typing import Dict, Tuple, List
from constants import END


class CleanTelnet(telnetlib.Telnet):
    def __init__(self, host: str, port: int, timeout: int):
        super().__init__(host, port, timeout)
        self.timeout = timeout

    def input(self, text: str):
        self.write((text + "\n").encode("utf-8"))

    def wait_for(self, text: str) -> str:
        return self.read_until(text.encode("utf-8"), self.timeout).decode("utf-8")

    def check_for(self, cases: List[str]):
        return self.expect([case.encode("utf-8") for case in cases], self.timeout)

    def new_line(self):
        self.write(b"\n")


class HostCreds:
    @staticmethod
    def add_cred(path: str, hostname: str):
        user = input("Username: ")
        # passwd = getpass("Password: ")
        passwd = input("Password: ")
        with open(os.path.join(path, f"{hostname}.cred"), "w") as cred_file:
            cred_file.write(f"{user}:{passwd}")

    @staticmethod
    def get_cred(path: str, hostname: str) -> Tuple[str, str]:
        with open(os.path.join(path, f"{hostname}.cred")) as cred_file:
            user_pass = cred_file.read().split(":")

        return user_pass[0], user_pass[1]


class Deployer:
    DEFAULT_TIMEOUT = 2

    @staticmethod
    def _close_session(hostname: str, t: CleanTelnet):
        t.input(END)
        t.close()
        print(f"Connection to {hostname} terminated gracefully.")

    @staticmethod
    def _cold_boot(t: CleanTelnet, user: str, passwd: str):
        t.input(user)
        t.wait_for("Enter secret:")
        t.input(passwd)
        t.wait_for("Enter secret again:")
        t.input(passwd)

        print("Finished cold boot configuration")

    @staticmethod
    def _from_idle(t: CleanTelnet):
        t.new_line()

    @staticmethod
    def _login(hostname: str, t: CleanTelnet, user: str, passwd: str):
        Deployer._from_idle(t)
        Deployer._from_idle(t)
        t.input(user)
        t.wait_for("Password:")
        t.input(passwd)

        print(f"Logged in to host {hostname}")

    @staticmethod
    def _write_config(hostname: str, t: CleanTelnet, configs: str):
        t.input("configure")
        t.wait_for("(config)#")
        t.input(configs)
        time.sleep(t.timeout)
        t.input("commit")

        print(f"Pushed configurations to {hostname}")

    @staticmethod
    def _get_initial_cases(hostname: str) -> List[str]:
        return [
            "Enter root-system username: ",
            "Username: ",
            "Press RETURN to get started.",
            "ios#",
            f"{hostname}#",
            "ios>",
            f"{hostname}>"
        ]

    def __init__(self, path: str, namespace: str, host_ports: Dict[str, int]):
        self.path = path
        self.namespace = namespace
        self.host_ports = host_ports
        self._check_topology()

    def _push(self, hostname: str, t: CleanTelnet, user: str, passwd: str,
              configs: str):
        print(f"Logging into host {hostname}")
        self._login(hostname, t, user, passwd)
        self._write_config(hostname, t, configs)

    def _cold_boot_configuration(self, hostname: str, t: CleanTelnet, user: str,
                                 passwd: str, configs: str):
        self._cold_boot(t, user, passwd)
        self._push(hostname, t, user, passwd, configs)

    def _idle_configuration(self, hostname: str, t: CleanTelnet, user: str,
                            passwd: str, configs: str):
        self._from_idle(t)
        self._push(hostname, t, user, passwd, configs)

    def _handover_configuration(self, hostname: str, t: CleanTelnet, configs: str):
        self._write_config(hostname, t, configs)

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

    def _negotiate_session(self, hostname: str, t: CleanTelnet, user: str, passwd: str,
                           configs: str):
        idx, _, data = t.check_for(Deployer._get_initial_cases(hostname))

        if idx == 0:
            self._cold_boot_configuration(hostname, t, user, passwd, configs)
        elif idx == 1:
            self._push(hostname, t, user, passwd, configs)
        elif idx == 2:
            self._idle_configuration(hostname, t, user, passwd, configs)
        elif idx >= 3:
            self._handover_configuration(hostname, t, configs)
        else:
            if len(data) == 0:
                self._idle_configuration(hostname, t, user, passwd, configs)
            else:
                t.close()
                raise RuntimeError("Error while negotiating connection.\n"
                                   "Last input:\n"
                                   f"{data}")

    def _start_session(self, hostname: str) -> Tuple[CleanTelnet, str, str, str]:
        with open(os.path.join(self.path, f"{hostname}.conf"), "r") as config_file:
            configs = config_file.read()
        user, passwd = HostCreds.get_cred(self.path, hostname)

        t = CleanTelnet(
            host=self.namespace,
            port=self.host_ports[hostname],
            timeout=Deployer.DEFAULT_TIMEOUT
        )

        return t, user, passwd, configs

    def _deploy_host(self, hostname: str):
        t, user, passwd, configs = self._start_session(hostname)
        self._negotiate_session(hostname, t, user, passwd, configs)
        self._close_session(hostname, t)

    def deploy(self):
        for hostname in self.host_ports.keys():
            try:
                self._deploy_host(hostname)
            except RuntimeError as e:
                print(f"Failed to push configuration for host {hostname}\n."
                      "Reason:\n"
                      f"{e}")

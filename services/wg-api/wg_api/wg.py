

from subprocess import PIPE, run
from typing import Generator
from wg_api.config_builder import InterfaceBuilder


class PeerInfo:
    def __init__(self) -> None:
        self.public_key: str
        self.preshared_key: str
        self.endpoint: str
        self.allowed_ips: str
        self.latest_handshake: str
        self.transfer_rx: str
        self.transfer_tx: str
        self.persistent_keepalive: str

    @classmethod
    def from_dump(cls, line: str) -> "PeerInfo":
        info = cls()
        (
            info.public_key,
            info.preshared_key,
            info.endpoint,
            info.allowed_ips,
            info.latest_handshake,
            info.transfer_rx,
            info.transfer_tx,
            info.persistent_keepalive,
        ) = line.split("\t")
        return info

    def dump(self) -> dict:
        return {
            "public_key": self.public_key,
            "preshared_key": self.preshared_key,
            "endpoint": self.endpoint,
            "allowed_ips": self.allowed_ips,
            "latest_handshake": self.latest_handshake,
            "transfer_rx": self.transfer_rx,
            "transfer_tx": self.transfer_tx,
            "persistent_keepalive": self.persistent_keepalive,
        }


class InterfaceInfo:
    def __init__(self) -> None:
        self.name: str
        self.private_key: str
        self.public_key: str
        self.listen_port: str
        self.fwmark: str
        self.peers: list[PeerInfo] = []

    @classmethod
    def from_dump(cls, dump: str) -> "InterfaceInfo":
        info = cls()
        lines = dump.strip().split("\n")

        (
            info.private_key,
            info.public_key,
            info.listen_port,
            info.fwmark,
        ) = lines.pop(
            0
        ).split("\t")

        for line in lines:
            info.peers.append(PeerInfo.from_dump(line))
        return info

    def dump(self) -> dict:
        return {
            "private_key": self.private_key,
            "public_key": self.public_key,
            "listen_port": self.listen_port,
            "fwmark": self.fwmark,
            "peers": [peer.dump() for peer in self.peers],
        }


class WG:
    @staticmethod
    def interfaces() -> list[str]:
        return (
            run(["wg", "show", "interfaces"], stdout=PIPE, text=True)
            .stdout.strip()
            .split()
        )

    @staticmethod
    def get_interface_info(interface_name: str) -> InterfaceInfo:
        data = run(
            ["wg", "show", interface_name, "dump"], stdout=PIPE, text=True
        ).stdout.strip()
        info = InterfaceInfo.from_dump(data)
        info.name = interface_name
        return info

    @staticmethod
    def get_interfaces_info() -> Generator[InterfaceInfo, None, None]:
        data = run(["wg", "show", "all", "dump"], stdout=PIPE, text=True).stdout.strip()
        interface_data = []
        current_interface = ""

        for line in data.split("\n"):
            interface_name, _ = line.split("\t", 1)
            if interface_name != current_interface:
                if interface_data:
                    info = InterfaceInfo.from_dump("\n".join(interface_data))
                    info.name = current_interface
                    yield info
                current_interface = interface_name
                interface_data = [line]
            else:
                interface_data.append(line)

        if interface_data:
            info = InterfaceInfo.from_dump("\n".join(interface_data))
            info.name = current_interface
            yield info

    @staticmethod
    def up(interface_name: str) -> None:
        run(["wg-quick", "up", interface_name])

    @staticmethod
    def down(interface_name: str) -> None:
        run(["wg-quick", "down", interface_name])

    @staticmethod
    def genkey() -> str:
        return run(["wg", "genkey"], stdout=PIPE, text=True).stdout.strip()

    @staticmethod
    def pubkey(private_key: str) -> str:
        return run(
            ["wg", "pubkey"], input=private_key, stdout=PIPE, text=True
        ).stdout.strip()
    
    @staticmethod
    def genpsk() -> str:
        return run(["wg", "genpsk"], stdout=PIPE, text=True).stdout.strip()
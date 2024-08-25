from pyexpat import model
from re import U
from typing import Union
from .storage import InterfaceModel, PeerModel, Storage
from loguru import logger

from .config_builder import InterfaceBuilder, PeerBuilder
from .wg import InterfaceInfo, PeerInfo, WG


class Wireguard:
    _singleton = None

    def __new__(cls) -> "Wireguard":
        if cls._singleton is None:
            return super().__new__(cls)
        return cls._singleton

    def __init__(self) -> None:
        self.storage = Storage("wg.db")

        for interface in self.storage.get_interfaces():
            self.sync_interface(interface)
        self._singleton = self

    @property
    def interfaces(self) -> list["Interface"]:
        return [
            Interface(self, interface) for interface in self.storage.get_interfaces()
        ]

    def build_interface(self, interface: InterfaceModel) -> InterfaceBuilder:
        builder = (
            InterfaceBuilder(interface.name)
            .address(interface.local_ip + "/24")
            .listen_port(interface.port)
            .private_key(interface.private_key)
            .pre_up(interface.pre_up)
            .post_up(interface.post_up)
            .pre_down(interface.pre_down)
            .post_down(interface.post_down)
        )

        for peer in self.storage.get_peers_by_interface_id(interface.id):
            builder.add_peer(
                PeerBuilder()
                .public_key(peer.public_key)
                .preshared_key(peer.preshared_key)
                .allowed_ips(peer.allowed_ips or (peer.address + "/32"))
            )

        return builder

    def get_interface_by_name(self, interface_name: str) -> Union["Interface", None]:
        interface = self.storage.get_interface_by_name(interface_name)
        if interface is None:
            return None
        return Interface(self, interface)

    def sync_interface(self, interface: InterfaceModel) -> None:
        logger.info(f"Syncing interface {interface.name}")
        is_running = self.is_running(interface.name)

        if is_running:
            logger.info(f"Disabling interface {interface.name}")
            WG.down(interface.name)  # Turn off the interface with old configuration
            logger.info(f"Interface {interface.name} is disabled")
            is_running = False

        builder = self.build_interface(interface)
        with open(f"/etc/wireguard/{interface.name}.conf", "w") as f:
            logger.info(
                f"Writing configuration to /etc/wireguard/{interface.name}.conf"
            )
            f.write(builder.build())
            logger.info(
                f"Configuration written to /etc/wireguard/{interface.name}.conf"
            )

        if interface.enabled:
            logger.info(f"Enabling interface {interface.name}")
            WG.up(interface.name)
            logger.info(f"Interface {interface.name} is enabled")
        logger.info(f"Interface {interface.name} is synced")

        Interface(self, interface).sync()

    def is_running(self, interface_name: str) -> bool:
        return interface_name in WG.interfaces()

    def get_interface_info(self, interface_name: str) -> InterfaceInfo:
        if not self.is_running(interface_name):
            logger.error(f"Interface {interface_name} is not running")
            raise ValueError(f"Interface {interface_name} is not running")
        return WG.get_interface_info(interface_name)

    def enable_interface(self, interface_name: str) -> None:
        logger.info(f"Enabling interface {interface_name}")
        interface = self.storage.get_interface_by_name(interface_name)
        if interface is None:
            logger.error(f"Interface {interface_name} does not exist")
            raise ValueError(f"Interface {interface_name} does not exist")
        interface.enabled = True
        self.storage.update_interface(interface)
        self.sync_interface(interface)
        logger.info(f"Interface {interface_name} is enabled")

    def disable_interface(self, interface_name: str) -> None:
        logger.info(f"Disabling interface {interface_name}")
        interface = self.storage.get_interface_by_name(interface_name)
        if interface is None:
            logger.error(f"Interface {interface_name} does not exist")
            raise ValueError(f"Interface {interface_name} does not exist")
        interface.enabled = False
        self.storage.update_interface(interface)
        self.sync_interface(interface)
        logger.info(f"Interface {interface_name} is disabled")

    def create_interface(
        self,
        *,
        name: str,
        local_ip: str,
        public_hostname: str,
        port: str,
        default_dns: str = "1.1.1.1",
        default_allowed_ips: str = "0.0.0.0/0, ::/0",
        default_persistent_keepalive: int = 25,
        enabled: bool = False,
    ) -> "Interface":
        logger.info(f"Creating interface {name}")
        private = WG.genkey()
        public = WG.pubkey(private)

        interface = InterfaceModel(
            name=name,
            local_ip=local_ip,
            public_hostname=public_hostname,
            port=port,
            public_key=public,
            private_key=private,
            default_dns=default_dns,
            default_allowed_ips=default_allowed_ips,
            default_persistent_keepalive=default_persistent_keepalive,
            enabled=enabled,
        )

        interface_id = self.storage.add_interface(interface)
        logger.info(f"Interface {name} is created with id {interface_id}")
        interface = self.storage.get_interface_by_id(interface_id)
        self.sync_interface(interface)

        return Interface(self, interface)

    def interface_exists(self, name: str) -> bool:
        return self.storage.get_interface_by_name(name) is not None

    def create_peer(
        self,
        *,
        interface_name: str,
        name: str,
        address: str,
        allowed_ips: str | None = None,
        persistent_keepalive: int | None = None,
    ) -> "Peer":
        logger.info(f"Creating peer {name} on interface {interface_name}")
        interface = self.storage.get_interface_by_name(interface_name)
        if interface is None:
            logger.error(f"Interface {interface_name} does not exist")
            raise ValueError(f"Interface {interface_name} does not exist")

        private_key = WG.genkey()
        public_key = WG.pubkey(private_key)
        preshared_key = WG.genpsk()

        if self.storage.get_peer_by_address(interface.id, address) is not None:
            logger.error(f"Peer with address {address} already exists")
            raise ValueError(f"Peer with address {address} already exists")

        peer = PeerModel(
            interface_id=interface.id,
            name=name,
            public_key=public_key,
            private_key=private_key,
            preshared_key=preshared_key,
            address=address,
            allowed_ips=allowed_ips,
            remote_persistent_keepalive=persistent_keepalive,
        )

        peer_id = self.storage.add_peer(peer)
        peer = self.storage.get_peer_by_id(peer_id)
        logger.info(f"Peer {name} is created with id {peer_id}")
        self.sync_interface(interface)

        return Peer(self, peer)

    def delete_peer(self, peer_id: int) -> None:
        logger.info(f"Deleting peer {peer_id}")
        peer = self.storage.get_peer_by_id(peer_id)
        if peer is None:
            logger.error(f"Peer {peer_id} does not exist")
            raise ValueError(f"Peer {peer_id} does not exist")
        self.storage.delete_peer(peer_id)
        logger.info(f"Peer {peer_id} is deleted")
        self.sync_interface(self.storage.get_interface_by_id(peer.interface_id))

    def delete_interface(self, interface_id: int) -> None:
        logger.info(f"Deleting interface {interface_id}")
        interface = self.storage.get_interface_by_id(interface_id)
        if interface is None:
            logger.error(f"Interface {interface_id} does not exist")
            raise ValueError(f"Interface {interface_id} does not exist")
        self.disable_interface(interface.name)  # Disable the interface before deleting
        self.storage.delete_interface(interface_id)
        logger.info(f"Interface {interface_id} and all associated peers are deleted")


class Interface:
    _interfaces: dict[int, "Interface"] = {}

    def __new__(cls, wireguard: Wireguard, model: InterfaceModel) -> "Interface":
        if interface := cls._interfaces.get(model.id):
            return interface
        return super().__new__(cls)

    def __init__(self, wireguard: Wireguard, model: InterfaceModel) -> None:
        self.wireguard = wireguard
        self.model = model
        self._interfaces[model.id] = self

    def get_info(self) -> InterfaceInfo:
        return self.wireguard.get_interface_info(self.model.name)

    @property
    def name(self) -> str:
        return self.model.name

    @property
    def enabled(self) -> bool:
        return self.model.enabled

    @property
    def peers(self) -> list["Peer"]:
        return [
            Peer(self.wireguard, peer)
            for peer in self.wireguard.storage.get_peers_by_interface_id(self.model.id)
        ]

    def enable(self) -> None:
        self.wireguard.enable_interface(self.model.name)

    def disable(self) -> None:
        self.wireguard.disable_interface(self.model.name)

    def create_peer(
        self,
        name: str,
        address: str,
        allowed_ips: str | None = None,
        persistent_keepalive: int | None = None,
    ) -> "Peer":
        return self.wireguard.create_peer(
            interface_name=self.model.name,
            name=name,
            address=address,
            allowed_ips=allowed_ips,
            persistent_keepalive=persistent_keepalive,
        )

    def delete(self) -> None:
        self.wireguard.delete_interface(self.model.id)

    def __repr__(self) -> str:
        return f"<Interface {self.model.name}>"

    def __str__(self) -> str:
        return self.model.name

    def sync(self) -> None:
        self.model = self.wireguard.storage.get_interface_by_id(self.model.id)
        if self.model is None:
            logger.error(f"Interface {self.model.id} does not exist")
            raise ValueError(f"Interface {self.model.id} does not exist")

        for peer in self.peers:
            peer.sync()

    def peer_with_name_exists(self, name: str) -> bool:
        return self.wireguard.storage.get_peer_by_name(self.model.id, name) is not None

    def get_peer_by_name(self, name: str) -> "Peer":
        peer = self.wireguard.storage.get_peer_by_name(self.model.id, name)
        if peer is None:
            return None
        return Peer(self.wireguard, peer)

    def get_peer_by_id(self, peer_id: int) -> "Peer":
        peer = self.wireguard.storage.get_peer_by_id(peer_id)
        if peer is None or peer.interface_id != self.model.id:
            return None
        return Peer(self.wireguard, peer)

    def get_peer_by_address(self, address: str) -> "Peer":
        peer = self.wireguard.storage.get_peer_by_address(self.model.id, address)
        if peer is None:
            return None
        return Peer(self.wireguard, peer)

    def dump(self) -> dict:
        return {
            "name": self.model.name,
            "local_ip": self.model.local_ip,
            "public_hostname": self.model.public_hostname,
            "port": self.model.port,
            "default_dns": self.model.default_dns,
            "default_allowed_ips": self.model.default_allowed_ips,
            "default_persistent_keepalive": self.model.default_persistent_keepalive,
            "enabled": self.model.enabled,
            "peers_count": len(self.peers),
        }


class Peer:
    _peers: dict[int, "Peer"] = {}

    def __new__(cls, wireguard: Wireguard, model: PeerModel) -> "Peer":
        if peer := cls._peers.get(model.id):
            return peer
        return super().__new__(cls)

    def __init__(self, wireguard: Wireguard, model: PeerModel) -> None:
        self.wireguard = wireguard
        self.model: PeerModel = model
        self.interface: Interface = Interface(
            wireguard, wireguard.storage.get_interface_by_id(model.interface_id)
        )
        self._peers[model.id] = self

    def get_info(self) -> PeerInfo:
        peers = self.wireguard.get_interface_info(self.interface.model.name).peers
        for peer in peers:
            if peer.public_key == self.model.public_key:
                return peer
        logger.error(
            f"Peer {self.model.name} not found in interface {self.interface.model.name}"
        )
        raise ValueError(
            f"Peer {self.model.name} not found in interface {self.interface.model.name}"
        )

    @property
    def transfer_rx(self) -> int:
        return int(self.get_info().transfer_rx)

    @property
    def transfer_tx(self) -> int:
        return int(self.get_info().transfer_tx)

    @property
    def latest_handshake(self) -> int:
        return int(self.get_info().latest_handshake)

    def delete(self) -> None:
        self.wireguard.delete_peer(self.model.id)

    def __repr__(self) -> str:
        return f"<Peer {self.model.name}>"

    def __str__(self) -> str:
        return self.model.name

    def sync(self) -> None:
        self.model = self.wireguard.storage.get_peer_by_id(self.model.id)
        if self.model is None:
            logger.error(f"Peer does not exist")
            raise ValueError(f"Peer does not exist")

    def dump(self) -> dict:
        return {
            "id": self.model.id,
            "enabled": self.interface.enabled,
            "interface": self.interface.model.name,
            "name": self.model.name,
            "public_key": self.model.public_key,
            "preshared_key": self.model.preshared_key,
            "allowed_ips": self.model.allowed_ips or (self.model.address + "/32"),
            "dns": self.model.remote_dns or self.interface.model.default_dns,
            "persistent_keepalive": self.model.remote_persistent_keepalive
            or self.interface.model.default_persistent_keepalive,
        } | (
            {
                "latest_handshake": self.latest_handshake,
                "transfer_rx": self.transfer_rx,
                "transfer_tx": self.transfer_tx,
            }
            if self.interface.enabled
            else {}
        )

    def build_interface(self) -> InterfaceBuilder:
        return (
            InterfaceBuilder("")
            .address(self.model.address + "/32")
            .private_key(self.model.private_key)
            .dns(self.model.remote_dns or self.interface.model.default_dns)
            .add_peer(
                PeerBuilder()
                .public_key(self.interface.model.public_key)
                .preshared_key(self.model.preshared_key)
                .allowed_ips(
                    self.model.allowed_ips or (self.interface.model.default_allowed_ips)
                )
                .endpoint(
                    f"{self.interface.model.public_hostname}:{self.interface.model.port}"
                )
                .persistent_keepalive(
                    self.model.remote_persistent_keepalive
                    or self.interface.model.default_persistent_keepalive
                )
            )
        )

    @property
    def config(self) -> str:
        return self.build_interface().build()

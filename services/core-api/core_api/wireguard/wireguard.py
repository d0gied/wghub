from typing import Iterable, Union, overload
from ..storages import (
    Interfaces,
    Peers,
    Interface as StorageInterface,
    Peer as StoragePeer,
)
from loguru import logger

from .config_builder import InterfaceBuilder, PeerBuilder
from .wg_connector import InterfaceInfo, PeerInfo, WG
from ipaddress import IPv4Interface, IPv4Network, IPv4Address, IPv6Network


class Interface(StorageInterface):
    id: int = -1


class Peer(StoragePeer):
    id: int = -1
    interface_id: int = -1

    latest_handshake: int | None = None
    transfer_rx: int | None = None
    transfer_tx: int | None = None


class Wireguard:
    _singleton = None

    def __new__(cls) -> "Wireguard":
        if cls._singleton is None:
            cls._singleton = super().__new__(cls)
        return cls._singleton

    @property
    def interfaces(self) -> list[Interface]:
        return [
            Interface(**interface.model_dump()) for interface in Interfaces().get_all()
        ]

    def get_interface(self, id: int) -> Interface | None:
        return (
            Interface(**storage_interface.model_dump())
            if (storage_interface := Interfaces.get(id))
            else None
        )

    def get_interface_by_name(self, name: str) -> Interface | None:
        return (
            Interface(**storage_interface.model_dump())
            if (storage_interface := Interfaces().get_by_name(name))
            else None
        )

    def fill_peers_defaults(self, peers: list[Peer]) -> list[Peer]:
        cached_interfaces: dict[int, Interface] = {}
        for peer in peers:
            if peer.interface_id not in cached_interfaces:
                if not (interface := self.get_interface(peer.interface_id)):
                    raise ValueError(f"Interface with id {peer.interface_id} not found")
                cached_interfaces[peer.interface_id] = interface
            interface = cached_interfaces[peer.interface_id]
            if not peer.allowed_ips:
                peer.allowed_ips = [IPv4Interface(peer.address).network]
            if not peer.remote_allowed_ips:
                peer.remote_allowed_ips = interface.default_allowed_ips
            if not peer.remote_dns:
                peer.remote_dns = interface.default_dns
            if not peer.remote_persistent_keepalive:
                peer.remote_persistent_keepalive = (
                    interface.default_persistent_keepalive
                )

        return list(peers)

    def fill_peer_defaults(self, peer: Peer) -> Peer:
        return self.fill_peers_defaults([peer])[0]

    def fill_peers_stats(self, peers: list[Peer]) -> list[Peer]:
        peers_by_interface: dict[int, list[Peer]] = {}
        for peer in peers:
            if peer.interface_id not in peers_by_interface:
                peers_by_interface[peer.interface_id] = []
            peers_by_interface[peer.interface_id].append(peer)

        def interfaces() -> Iterable[Interface]:
            for interface_id in peers_by_interface:
                interface = Interfaces.get(interface_id)
                if not interface:
                    raise ValueError(f"Interface with id {interface_id} not found")
                yield Interface.model_validate(interface.model_dump())

        for interface in interfaces():
            if not self.is_running(interface):
                continue
            interface_info = WG.get_interface_info(interface.name)
            _peers = {
                peer.public_key: peer for peer in peers_by_interface[interface.id]
            }
            for peer_info in interface_info.peers:
                if peer := _peers.get(peer_info.public_key):
                    peer.latest_handshake = int(peer_info.latest_handshake)
                    peer.transfer_rx = int(peer_info.transfer_rx)
                    peer.transfer_tx = int(peer_info.transfer_tx)

        return list(peers)

    def fill_peer_stats(self, peer: Peer) -> Peer:
        return self.fill_peers_stats([peer])[0]

    def get_peers(self, interface: Interface) -> list[Peer]:
        return [
            Peer(**peer.model_dump()) for peer in Peers().get_by_interface(interface)
        ]

    def get_peer(self, id: int) -> Peer | None:
        return (
            Peer(**storage_peer.model_dump())
            if (storage_peer := Peers().get(id))
            else None
        )

    def get_peer_by_public_key(
        self, interface: Interface, public_key: str
    ) -> Peer | None:
        return (
            Peer(**storage_peer.model_dump())
            if (storage_peer := Peers().get_by_public_key(interface, public_key))
            else None
        )

    def get_peer_by_address(
        self, interface: Interface, address: IPv4Address
    ) -> Peer | None:
        return (
            Peer(**storage_peer.model_dump())
            if (storage_peer := Peers().get_by_address(interface, address))
            else None
        )

    def add_interface(self, interface: Interface) -> int:
        logger.info(f"Adding interface {interface.name}")
        _id = Interfaces.add(interface)
        logger.info(f"Interface {interface.name} added")
        self.sync_interface(interface)
        return _id

    def update_interface(self, interface: Interface) -> None:
        logger.info(f"Updating interface {interface.name}")
        Interfaces.update(interface)
        logger.info(f"Interface {interface.name} updated")
        self.sync_interface(interface)

    def delete_interface(self, interface: Interface) -> None:
        logger.info(f"Deleting interface {interface.name}")
        Interfaces.delete(interface.id)
        logger.info(f"Interface {interface.name} deleted")
        self.sync_interface(interface)

    def add_peer(self, peer: Peer) -> int:
        logger.info(f"Adding peer {peer.id}")
        interface = self.get_interface(peer.interface_id)
        if not interface:
            raise ValueError(f"Interface with id {peer.interface_id} not found")
        peer_id = Peers.add(peer)
        logger.info(f"Peer {peer.id} added")
        self.sync_interface(interface)
        return peer_id

    def update_peer(self, peer: Peer) -> None:
        logger.info(f"Updating peer {peer.id}")
        interface = self.get_interface(peer.interface_id)
        if not interface:
            raise ValueError(f"Interface with id {peer.interface_id} not found")
        Peers.update(peer)
        logger.info(f"Peer {peer.id} updated")
        self.sync_interface(interface)

    def delete_peer(self, peer: Peer) -> None:
        logger.info(f"Deleting peer {peer.id}")
        interface = self.get_interface(peer.interface_id)
        if not interface:
            raise ValueError(f"Interface with id {peer.interface_id} not found")
        Peers.delete(peer.id)
        logger.info(f"Peer {peer.id} deleted")
        self.sync_interface(interface)

    def create_peer(
        self,
        interface: Interface,
        name: str,
        address: IPv4Address,
        remote_allowed_ips: list[IPv4Network | IPv6Network] | None = None,
        remote_dns: str | None = None,
        remote_persistent_keepalive: int | None = None,
    ) -> Peer:
        private_key = WG.genkey()
        public_key = WG.pubkey(private_key)
        preshared_key = WG.genkey()
        peer = Peer(
            interface_id=interface.id,
            name=name,
            address=address,
            public_key=public_key,
            private_key=private_key,
            preshared_key=preshared_key,
            allowed_ips=None,
            remote_allowed_ips=remote_allowed_ips,
            remote_dns=remote_dns,
            remote_persistent_keepalive=remote_persistent_keepalive,
        )
        peer_id = self.add_peer(peer)
        peer = self.get_peer(peer_id)
        if not peer:
            raise ValueError(f"Peer with id {peer_id} not found")
        return peer

    def create_interface(
        self,
        name: str = "wg0",
        local_ip: IPv4Interface = IPv4Interface("10.20.0.1/24"),
        public_hostname: str = "localhost",
        port: int = 51820,
        default_dns: str = "1.1.1.1",
        default_allowed_ips: list[IPv4Network | IPv6Network] = [
            IPv4Network("0.0.0.0/0"),
            IPv6Network("::/0"),
        ],
        default_persistent_keepalive: int = 25,
    ) -> Interface:
        private_key = WG.genkey()
        public_key = WG.pubkey(private_key)
        interface = Interface(
            name=name,
            local_ip=local_ip,
            public_hostname=public_hostname,
            port=port,
            public_key=public_key,
            private_key=private_key,
            pre_up="",
            post_up="",
            pre_down="",
            post_down="",
            default_dns=default_dns,
            default_allowed_ips=default_allowed_ips,
            default_persistent_keepalive=default_persistent_keepalive,
            enabled=False,
        )
        _id = self.add_interface(interface)
        interface = self.get_interface(_id)
        if not interface:
            raise ValueError(f"Interface with id {_id} not found")
        return interface

    def is_running(self, interface: Interface) -> bool:
        return interface.name in WG.interfaces()

    def up_interface(self, interface: Interface) -> None:
        logger.info(f"Enabling interface {interface.name}")
        interface.enabled = True
        self.update_interface(interface)
        logger.info(f"Enabled interface {interface.name}")

    def down_interface(self, interface: Interface) -> None:
        logger.info(f"Disabling interface {interface.name}")
        interface.enabled = False
        self.update_interface(interface)
        logger.info(f"Disabled interface {interface.name}")

    def build_interface(self, interface: Interface) -> InterfaceBuilder:
        builder = (
            InterfaceBuilder(interface.name)
            .address(str(interface.local_ip))
            .listen_port(str(interface.port))
            .private_key(interface.private_key)
            .pre_up(interface.pre_up)
            .post_up(interface.post_up)
            .pre_down(interface.pre_down)
            .post_down(interface.post_down)
        )

        for peer in Peers.get_by_interface(interface):
            builder.add_peer(
                PeerBuilder()
                .public_key(peer.public_key)
                .preshared_key(peer.preshared_key)
                .allowed_ips(
                    peer.dump_allowed_ips(peer.allowed_ips)
                    if peer.allowed_ips
                    else str(IPv4Interface(peer.address).network)
                )
            )

        return builder

    def sync_interface(self, interface: Interface) -> None:
        logger.info(f"Syncing interface {interface.name}")
        is_running = self.is_running(interface)

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

    def get_config(self, peer: Peer) -> str:
        interface = self.get_interface(peer.interface_id)
        if not interface:
            raise ValueError(f"Interface with id {peer.interface_id} not found")
        return (
            InterfaceBuilder(interface.name)
            .address(str(IPv4Interface(peer.address)))
            .dns(peer.remote_dns or interface.default_dns)
            .private_key(peer.private_key)
            .add_peer(
                PeerBuilder()
                .public_key(peer.public_key)
                .preshared_key(peer.preshared_key)
                .endpoint(f"{interface.public_hostname}:{interface.port}")
                .allowed_ips(
                    peer.dump_allowed_ips(peer.remote_allowed_ips)
                    if peer.remote_allowed_ips
                    else peer.dump_allowed_ips(interface.default_allowed_ips)
                )
                .persistent_keepalive(peer.remote_persistent_keepalive or 0)
            )
        ).build()

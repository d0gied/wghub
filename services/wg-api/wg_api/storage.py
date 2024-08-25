from dataclasses import dataclass
from re import I
import sqlite3


@dataclass
class PeerModel:
    id: int = -1  # primary key
    interface_id: int = -1  # foreign key

    name: str = "peer"
    public_key: str = ""
    private_key: str = ""
    preshared_key: str = ""
    address: str = ""
    allowed_ips: str = ""

    remote_allowed_ips: str | None = None
    remote_dns: str | None = None
    remote_persistent_keepalive: int | None = None


@dataclass
class InterfaceModel:
    id: int = -1  # primary key

    name: str = "wg0"
    local_ip: str = "10.8.0.1/24"
    public_hostname: str = "example.com"
    port: int = 51820

    public_key: str = ""
    private_key: str = ""
    pre_up: str = ""
    post_up: str = ""
    pre_down: str = ""
    post_down: str = ""

    default_dns: str = "1.1.1.1"
    default_allowed_ips: str = "0.0.0.0/0, ::/0"
    default_persistent_keepalive: int = 25

    enabled: bool = True


class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        self.create_table()

    def create_table(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS interfaces (
                id INTEGER PRIMARY KEY,
                name TEXT,
                local_ip TEXT,
                public_hostname TEXT,
                port INTEGER,
                public_key TEXT,
                private_key TEXT,
                pre_up TEXT,
                post_up TEXT,
                pre_down TEXT,
                post_down TEXT,
                default_dns TEXT,
                default_allowed_ips TEXT,
                default_persistent_keepalive INTEGER,
                enabled BOOLEAN DEFAULT 1
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS peers (
                id INTEGER PRIMARY KEY,
                name TEXT,
                public_key TEXT,
                private_key TEXT,
                preshared_key TEXT,
                address TEXT,
                allowed_ips TEXT,
                remote_allowed_ips TEXT,
                remote_dns TEXT,
                remote_persistent_keepalive INTEGER,
                FOREIGN KEY (interface_id) REFERENCES interfaces(id) ON DELETE CASCADE
            )
            """
        )

        self.conn.commit()

    def add_interface(self, interface: InterfaceModel) -> int:
        self.cursor.execute(
            """
            INSERT INTO interfaces (
                name,
                local_ip,
                public_hostname,
                port,
                public_key,
                private_key,
                pre_up,
                post_up,
                pre_down,
                post_down,
                default_dns,
                default_allowed_ips,
                default_persistent_keepalive,
                enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interface.name,
                interface.local_ip,
                interface.public_hostname,
                interface.port,
                interface.public_key,
                interface.private_key,
                interface.pre_up,
                interface.post_up,
                interface.pre_down,
                interface.post_down,
                interface.default_dns,
                interface.default_allowed_ips,
                interface.default_persistent_keepalive,
                int(interface.enabled),
            ),
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def add_peer(self, peer: PeerModel) -> int:
        self.cursor.execute(
            """
            INSERT INTO peers (
                interface_id,
                name,
                public_key,
                private_key,
                preshared_key,
                address,
                allowed_ips,
                remote_allowed_ips,
                remote_dns,
                remote_persistent_keepalive
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                peer.interface_id,
                peer.name,
                peer.public_key,
                peer.private_key,
                peer.preshared_key,
                peer.address,
                peer.allowed_ips,
                peer.remote_allowed_ips,
                peer.remote_dns,
                peer.remote_persistent_keepalive,
            ),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_interfaces(self) -> list[InterfaceModel]:
        self.cursor.execute("SELECT * FROM interfaces")
        return [InterfaceModel(*row) for row in self.cursor.fetchall()]

    def get_interfaces_ids(self) -> list[int]:
        self.cursor.execute("SELECT id FROM interfaces")
        return [row[0] for row in self.cursor.fetchall()]

    def get_peers(self) -> list[PeerModel]:
        self.cursor.execute("SELECT * FROM peers")
        return [PeerModel(*row) for row in self.cursor.fetchall()]

    def get_interface_by_id(self, _id: int) -> InterfaceModel | None:
        self.cursor.execute("SELECT * FROM interfaces WHERE id = ?", (_id,))
        return InterfaceModel(*row) if (row := self.cursor.fetchone()) else None

    def get_peer_by_id(self, _id: int) -> PeerModel | None:
        self.cursor.execute("SELECT * FROM peers WHERE id = ?", (_id,))
        return PeerModel(*row) if (row := self.cursor.fetchone()) else None

    def get_peers_by_interface_id(self, interface_id: int) -> list[PeerModel]:
        self.cursor.execute(
            "SELECT * FROM peers WHERE interface_id = ?", (interface_id,)
        )
        return [PeerModel(*row) for row in self.cursor.fetchall()]

    def get_peer_by_name(self, interface_id: int, name: str) -> PeerModel | None:
        self.cursor.execute("SELECT * FROM peers WHERE interface_id = ? AND name = ?", (interface_id, name))
        return PeerModel(*row) if (row := self.cursor.fetchone()) else None

    def get_interface_by_name(self, name: str) -> InterfaceModel | None:
        self.cursor.execute(
            "SELECT * FROM interfaces WHERE name = ?", (name,)
        )
        return InterfaceModel(*row) if (row := self.cursor.fetchone()) else None

    def delete_interface(self, _id: int) -> None:
        self.cursor.execute("DELETE FROM interfaces WHERE id = ?", (_id,)) # will delete all peers associated with this interface
        self.conn.commit()

    def delete_peer(self, _id: int) -> None:
        self.cursor.execute("DELETE FROM peers WHERE id = ?", (_id,))
        self.conn.commit()

    def get_peer_by_address(self, interface_id: int, address: str) -> PeerModel | None:
        self.cursor.execute("SELECT * FROM peers WHERE interface_id = ? AND address = ?", (interface_id, address))
        return PeerModel(*row) if (row := self.cursor.fetchone()) else None

    def update_interface(self, interface: InterfaceModel) -> None:
        self.cursor.execute(
            """
            UPDATE interfaces SET
                name = ?,
                local_ip = ?,
                public_hostname = ?,
                port = ?,
                public_key = ?,
                private_key = ?,
                pre_up = ?,
                post_up = ?,
                pre_down = ?,
                post_down = ?,
                default_dns = ?,
                default_allowed_ips = ?,
                default_persistent_keepalive = ?,
                enabled = ?
            WHERE id = ?
            """,
            (
                interface.name,
                interface.local_ip,
                interface.public_hostname,
                interface.port,
                interface.public_key,
                interface.private_key,
                interface.pre_up,
                interface.post_up,
                interface.pre_down,
                interface.post_down,
                interface.default_dns,
                interface.default_allowed_ips,
                interface.default_persistent_keepalive,
                int(interface.enabled),
                interface.id,
            ),
        )
        self.conn.commit()
    
    def update_peer(self, peer: PeerModel) -> None:
        self.cursor.execute(
            """
            UPDATE peers SET
                interface_id = ?,
                name = ?,
                public_key = ?,
                private_key = ?,
                preshared_key = ?,
                address = ?,
                allowed_ips = ?,
                remote_allowed_ips = ?,
                remote_dns = ?,
                remote_persistent_keepalive = ?
            WHERE id = ?
            """,
            (
                peer.interface_id,
                peer.name,
                peer.public_key,
                peer.private_key,
                peer.preshared_key,
                peer.address,
                peer.allowed_ips,
                peer.remote_allowed_ips,
                peer.remote_dns,
                peer.remote_persistent_keepalive,
                peer.id,
            ),
        )
        self.conn.commit()

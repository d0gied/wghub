from dataclasses import dataclass
from re import I
import sqlite3

from typing import TYPE_CHECKING


@dataclass
class PeerModel:
    id: int = -1 # primary key
    interface_id: int = -1 # foreign key
    name: str = "peer"
    public_key: str = ""
    private_key: str = ""
    address: str = ""
    allowed_ips: str = ""


@dataclass
class InterfaceModel:
    id: int = -1 # primary key
    interface_name: str = "wg0"
    local_ip: str = "10.8.0.1/24"
    public_hostname: str = "example.com"
    port: int = 51820
    public_key: str = ""
    private_key: str = ""
    dns: str = "1.1.1.1"
    client_allowed_ips: str = "0.0.0.0/0, ::/0"
    persistent_keepalive: int = 25

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
                interface_name TEXT NOT NULL,
                local_ip TEXT NOT NULL,
                public_hostname TEXT NOT NULL,
                port INTEGER NOT NULL,
                public_key TEXT NOT NULL,
                private_key TEXT NOT NULL,
                dns TEXT NOT NULL,
                client_allowed_ips TEXT NOT NULL,
                persistent_keepalive INTEGER NOT NULL
            )
            """
        )
        self.cursor.execute(
        """
            CREATE TABLE IF NOT EXISTS peers (
                id INTEGER PRIMARY KEY,
                interface_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                public_key TEXT NOT NULL,
                private_key TEXT NOT NULL,
                allowed_ips TEXT NOT NULL,
                address TEXT NOT NULL,
                FOREIGN KEY (interface_id) REFERENCES interfaces (id)
            )
        """
        )
        self.conn.commit()

    def insert_interface(self, interface: InterfaceModel):
        self.cursor.execute(
            """
            INSERT INTO interfaces (
                interface_name,
                local_ip,
                public_hostname,
                port,
                public_key,
                private_key,
                dns,
                client_allowed_ips,
                persistent_keepalive
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interface.interface_name,
                interface.local_ip,
                interface.public_hostname,
                interface.port,
                interface.public_key,
                interface.private_key,
                interface.dns,
                interface.client_allowed_ips,
                interface.persistent_keepalive,
            ),
        )
        self.conn.commit()
    
    def insert_peer(self, peer: PeerModel):
        self.cursor.execute(
            """
            INSERT INTO peers (
                interface_id,
                name,
                public_key,
                private_key,
                allowed_ips,
                address
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                peer.interface_id,
                peer.name,
                peer.public_key,
                peer.private_key,
                peer.allowed_ips,
                peer.address,
            ),
        )
        self.conn.commit()
    
    def get_interfaces(self) -> list[InterfaceModel]:
        self.cursor.execute("SELECT * FROM interfaces")
        return[InterfaceModel(*row) for row in self.cursor.fetchall()]

    def get_peers(self) -> list[PeerModel]:
        self.cursor.execute("SELECT * FROM peers")
        return [PeerModel(*row) for row in self.cursor.fetchall()]

    def get_interface_by_id(self, interface_id: int) -> InterfaceModel | None:
        self.cursor.execute("SELECT * FROM interfaces WHERE id = ?", (interface_id,))
        return InterfaceModel(*row) if (row := self.cursor.fetchone()) else None 
    
    def get_peer_by_id(self, peer_id: int) -> PeerModel | None:
        self.cursor.execute("SELECT * FROM peers WHERE id = ?", (peer_id,))
        return PeerModel(*row) if (row := self.cursor.fetchone()) else None
    
    def get_peers_by_interface_id(self, interface_id: int) -> list[PeerModel]:
        self.cursor.execute("SELECT * FROM peers WHERE interface_id = ?", (interface_id,))
        return [PeerModel(*row) for row in self.cursor.fetchall()]

    def get_peer_by_name(self, name: str) -> PeerModel | None:
        self.cursor.execute("SELECT * FROM peers WHERE name = ?", (name,))
        return PeerModel(*row) if (row := self.cursor.fetchone()) else None
    
    def get_interface_by_name(self, interface_name: str) -> InterfaceModel | None:
        self.cursor.execute("SELECT * FROM interfaces WHERE interface_name = ?", (interface_name,))
        return InterfaceModel(*row) if (row := self.cursor.fetchone()) else None
    
    def delete_interface(self, interface_id: int) -> None:
        self.cursor.execute("DELETE FROM interfaces WHERE id = ?", (interface_id,))
        self.conn.commit()
    
    def delete_peer(self, peer_id: int) -> None:
        self.cursor.execute("DELETE FROM peers WHERE id = ?", (peer_id,))
        self.conn.commit()

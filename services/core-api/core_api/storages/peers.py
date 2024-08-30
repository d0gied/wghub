from .connector import Table, Column, ForeignKey
from .interfaces import Interface, Interfaces
from pydantic import BaseModel
from ipaddress import IPv4Address, IPv4Interface, IPv6Network, IPv4Network


class Peer(BaseModel):
    id: int
    interface_id: int

    name: str
    public_key: str
    private_key: str
    preshared_key: str
    address: IPv4Address
    allowed_ips: list[IPv4Network | IPv6Network] | None

    remote_allowed_ips: list[IPv4Network | IPv6Network] | None
    remote_dns: str | None
    remote_persistent_keepalive: int | None

    def to_table_model(self) -> dict:
        data = self.model_dump()
        if data["allowed_ips"]:
            data["allowed_ips"] = self.dump_allowed_ips(data["allowed_ips"])
        if data["remote_allowed_ips"]:
            data["remote_allowed_ips"] = self.dump_allowed_ips(
                data["remote_allowed_ips"]
            )
        data["address"] = str(data["address"])
        data.pop("latest_handshake", None)
        data.pop("transfer_rx", None)
        data.pop("transfer_tx", None)
        return data

    @classmethod
    def from_table_model(cls, data: dict) -> "Peer":
        if data["allowed_ips"]:
            data["allowed_ips"] = data["allowed_ips"].split(", ")
        if data["remote_allowed_ips"]:
            data["remote_allowed_ips"] = data["remote_allowed_ips"].split(", ")
        return cls.model_validate(data)

    @staticmethod
    def dump_allowed_ips(allowed_ips: list[IPv4Network | IPv6Network]) -> str:
        return ", ".join([str(ip) for ip in allowed_ips])


class Peers(
    Table,
    name="peers",
    columns=[
        Column("id", "INTEGER", primary_key=True),
        Column("interface_id", "INTEGER", not_null=True),
        Column("name", "TEXT", not_null=True),
        Column("public_key", "TEXT", not_null=True, unique=True),
        Column("private_key", "TEXT", not_null=True, unique=True),
        Column("preshared_key", "TEXT", not_null=True, unique=True),
        Column("address", "TEXT", not_null=True),
        Column("allowed_ips", "TEXT", not_null=False),
        Column("remote_allowed_ips", "TEXT", not_null=False),
        Column("remote_dns", "TEXT", not_null=False),
        Column("remote_persistent_keepalive", "INTEGER", not_null=False),
        ForeignKey("interface_id", Interfaces),
    ],
):
    @classmethod
    def get(cls, id: int) -> Peer | None:
        cls.storage.execute(f"SELECT * FROM {cls.name} WHERE id = ?", (id,))
        return (
            Peer.from_table_model(row.dict())
            if (row := cls.storage.fetchone())
            else None
        )

    @classmethod
    def get_by_public_key(cls, interface: Interface, public_key: str) -> Peer | None:
        cls.storage.execute(
            f"SELECT * FROM {cls.name} WHERE interface_id = ? AND public_key = ?",
            (interface.id, public_key),
        )
        return (
            Peer.from_table_model(row.dict())
            if (row := cls.storage.fetchone())
            else None
        )

    @classmethod
    def get_by_address(cls, interface: Interface, address: IPv4Address) -> Peer | None:
        cls.storage.execute(
            f"SELECT * FROM {cls.name} WHERE interface_id = ? AND address = ?",
            (interface.id, str(address)),
        )
        return (
            Peer.from_table_model(row.dict())
            if (row := cls.storage.fetchone())
            else None
        )

    @classmethod
    def get_by_name(cls, interface: Interface, name: str) -> list[Peer]:
        cls.storage.execute(
            f"SELECT * FROM {cls.name} WHERE interface_id = ? AND name = ?",
            (interface.id, name),
        )
        return [Peer.from_table_model(row.dict()) for row in cls.storage.fetchall()]

    @classmethod
    def get_by_interface(cls, interface: Interface) -> list[Peer]:
        cls.storage.execute(
            f"SELECT * FROM {cls.name} WHERE interface_id = ?", (interface.id,)
        )
        return [Peer.from_table_model(row.dict()) for row in cls.storage.fetchall()]

    @classmethod
    def get_all(cls) -> list[Peer]:
        cls.storage.execute(f"SELECT * FROM {cls.name}")
        return [Peer.from_table_model(row.dict()) for row in cls.storage.fetchall()]

    @classmethod
    def add(cls, peer: Peer) -> int:
        return cls._insert(peer.to_table_model())

    @classmethod
    def update(cls, peer: Peer) -> None:
        base_peer = cls.get(peer.id)
        if not base_peer:
            raise ValueError("Interface not found")
        cls._update(peer.to_table_model(), {"id": peer.id})

    @classmethod
    def delete(cls, id: int) -> None:
        cls.storage.execute(f"DELETE FROM {cls.name} WHERE id = ?", (id,))
        cls.storage.commit()

import json
from .connector import Table, Column
from pydantic import BaseModel
from ipaddress import IPv4Interface, IPv6Network, IPv4Network


class Interface(BaseModel):
    id: int
    name: str
    local_ip: IPv4Interface
    public_hostname: str
    port: int

    public_key: str
    private_key: str
    pre_up: str
    post_up: str
    pre_down: str
    post_down: str

    default_dns: str
    default_allowed_ips: list[IPv4Network | IPv6Network]
    default_persistent_keepalive: int

    enabled: bool

    def to_table_model(self) -> dict:
        data = self.model_dump()
        data["default_allowed_ips"] = self.dump_allowed_ips(data["default_allowed_ips"])
        data["local_ip"] = str(data["local_ip"])
        return data

    @classmethod
    def from_table_model(cls, data: dict) -> "Interface":
        data["default_allowed_ips"] = data["default_allowed_ips"].split(", ")
        return cls.model_validate(data)

    @staticmethod
    def dump_allowed_ips(allowed_ips: list[IPv4Network | IPv6Network]) -> str:
        return ", ".join([str(ip) for ip in allowed_ips])


class Interfaces(
    Table,
    name="interfaces",
    columns=[
        Column("id", "INTEGER", primary_key=True),
        Column("name", "TEXT", not_null=True, unique=True),
        Column("local_ip", "TEXT", not_null=True),
        Column("public_hostname", "TEXT", not_null=True),
        Column("port", "INTEGER", not_null=True),
        Column("public_key", "TEXT", not_null=True),
        Column("private_key", "TEXT", not_null=True),
        Column("pre_up", "TEXT", not_null=True),
        Column("post_up", "TEXT", not_null=True),
        Column("pre_down", "TEXT", not_null=True),
        Column("post_down", "TEXT", not_null=True),
        Column("default_dns", "TEXT", not_null=True),
        Column("default_allowed_ips", "TEXT", not_null=True),
        Column("default_persistent_keepalive", "INTEGER", not_null=True),
        Column("enabled", "BOOLEAN", not_null=True),
    ],
):
    @classmethod
    def get(cls, id: int) -> Interface | None:
        cls.storage.execute(f"SELECT * FROM {cls.name} WHERE id = ?", (id,))
        return (
            Interface.from_table_model(row.dict())
            if (row := cls.storage.fetchone())
            else None
        )

    @classmethod
    def get_by_name(cls, name: str) -> Interface | None:
        cls.storage.execute(f"SELECT * FROM {cls.name} WHERE name = ?", (name,))
        return (
            Interface.from_table_model(row.dict())
            if (row := cls.storage.fetchone())
            else None
        )

    @classmethod
    def get_all(cls) -> list[Interface]:
        cls.storage.execute(f"SELECT * FROM {cls.name}")
        return [
            Interface.from_table_model(row.dict()) for row in cls.storage.fetchall()
        ]

    @classmethod
    def add(cls, interface: Interface) -> int:
        return cls._insert(interface.to_table_model())

    @classmethod
    def update(cls, interface: Interface) -> None:
        base_interface = cls.get(interface.id)
        if not base_interface:
            raise ValueError("Interface not found")
        cls._update(interface.to_table_model(), {"id": interface.id})

    @classmethod
    def delete(cls, id: int) -> None:
        cls.storage.execute(f"DELETE FROM {cls.name} WHERE id = ?", (id,))
        cls.storage.commit()

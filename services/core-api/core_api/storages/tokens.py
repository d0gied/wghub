from .connector import Table, Column


class Tokens(
    Table,
    name="tokens",
    columns=[
        Column("id", "INTEGER", primary_key=True),
        Column("value", "TEXT", not_null=True, unique=True),
    ],
):
    @classmethod
    def add(cls, value: str) -> None:
        cls.storage.execute(
            f"INSERT INTO {cls.name} (id, value) VALUES (?, ?)", (id, value)
        )
        cls.storage.commit()

    @classmethod
    def delete(cls, value: str) -> None:
        cls.storage.execute(f"DELETE FROM {cls.name} WHERE value = ?", (value,))
        cls.storage.commit()

    @classmethod
    def exists(cls, value: str) -> bool:
        cls.storage.execute(f"SELECT value FROM {cls.name} WHERE value = ?", (value,))
        return bool(cls.storage.fetchone())

    @classmethod
    def get_count(cls) -> int:
        cls.storage.execute(f"SELECT COUNT(*) FROM {cls.name}")
        return row[0] if (row := cls.storage.fetchone()) else 0

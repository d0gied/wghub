from .connector import Table, Column


class Tokens(
    Table,
    name="tokens",
    columns=[
        Column("id", "INTEGER", primary_key=True),
        Column("value", "TEXT", not_null=True),
    ],
):
    @classmethod
    def get(cls, id: str) -> str:
        cls.storage.execute(f"SELECT value FROM {cls.name} WHERE id = ?", (id,))
        return str(cls.storage.fetchone())

    @classmethod
    def add(cls, value: str) -> None:
        cls.storage.execute(
            f"INSERT INTO {cls.name} (id, value) VALUES (?, ?)", (id, value)
        )
        cls.storage.commit()

    @classmethod
    def delete(cls, value: str) -> None:
        cls.storage.execute(f"DELETE FROM {cls.name} WHERE id = ?", (id,))
        cls.storage.commit()

    @classmethod
    def exists(cls, id: str) -> bool:
        cls.storage.execute(f"SELECT value FROM {cls.name} WHERE id = ?", (id,))
        return bool(cls.storage.fetchone())

import sqlite3
from typing import Literal, Type

from loguru import logger


class Storage:
    class Row:
        def __init__(self, cursor: sqlite3.Cursor, row: tuple):
            self.cursor = cursor
            self.row = row

        def dict(self):
            return dict(
                zip([column[0] for column in self.cursor.description], self.row)
            )

        def __iter__(self):
            return iter(self.row)

        def __getitem__(self, key):
            return self.row[key]

        def __len__(self):
            return len(self.row)

        def __repr__(self):
            return f"<Row {self.row}>"

        def str(self):
            if len(self.row) == 1:
                return str(self.row[0])
            else:
                raise ValueError("Row has more than one column")

    _singleton = None

    def __new__(cls, *args, **kwargs):
        if not cls._singleton:
            cls._singleton = super(Storage, cls).__new__(cls)
        return cls._singleton

    def __init__(self, db_path: str = "wg.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def fetchall(self) -> list[Row]:
        return [self.Row(self.cursor, row) for row in self.cursor.fetchall()]

    def fetchone(self) -> Row | None:
        return self.Row(self.cursor, row) if (row := self.cursor.fetchone()) else None

    def execute(self, *args):
        logger.debug(f"SQL\n{args}")
        return self.cursor.execute(*args)

    def commit(self):
        return self.conn.commit()


class Column:
    def __init__(
        self,
        name: str,
        type: Literal["TEXT", "INT", "BOOLEAN", "INTEGER", "REAL", "BLOB", "JSON"],
        *,
        primary_key: bool = False,
        not_null: bool = False,
        unique: bool = False,
    ):
        self.type = type
        self.name = name
        self.unique = unique
        self.primary_key = primary_key
        self.not_null = not_null

    def __repr__(self):
        return f"<Column {self.name} {self.type}>"

    @staticmethod
    def _normalized(line: str) -> str:
        return " ".join(line.strip().split())

    def __str__(self):
        return self._normalized(
            f"{self.name} {self.type} "
            f" {'PRIMARY KEY' if self.primary_key else ''}"
            f" {'NOT NULL' if self.not_null else ''}"
            f" {'UNIQUE' if self.unique else ''}"
        )


class ForeignKey(Column):
    def __init__(
        self,
        name: str,
        reference: Type["Table"],
        column: str = "id",
        on_delete: Literal["CASCADE", "SET NULL"] = "CASCADE",
        **kwargs,
    ):
        super().__init__(name, "INTEGER", **kwargs)
        self.reference = reference
        self.column = column
        self.on_delete = on_delete

    def __str__(self):
        return self._normalized(
            f"FOREIGN KEY ({self.name}) REFERENCES {self.reference.name}({self.column}) ON DELETE {self.on_delete}"
        )


class Table:
    storage = Storage()
    name: str
    columns: list[Column]
    _tables: dict[str, Type["Table"]] = {}

    def __init_subclass__(cls, name: str, columns: list[Column] = [], **kwargs):
        if not name:
            raise ValueError("Name is required")
        if not columns:
            raise ValueError("Columns are required")
        if cls.__name__ in cls._tables:
            raise ValueError(f"Table {cls.__name__} already exists")
        cls.columns = columns
        cls.name = name
        cls._tables[cls.__name__] = cls
        cls._create_table()

    @classmethod
    def _create_table(cls):
        _columns = ", ".join(map(str, cls.columns))
        cls.storage.execute(f"CREATE TABLE IF NOT EXISTS {cls.name} ({_columns});")
        cls.storage.commit()

    @classmethod
    def _insert(cls, data: dict) -> int:
        data.pop("id", None)
        columns = ", ".join(data.keys())
        values = ", ".join("?" * len(data))
        cls.storage.execute(
            f"INSERT INTO {cls.name} ({columns}) VALUES ({values})",
            tuple(data.values()),
        )
        cls.storage.commit()
        last_id = cls.storage.cursor.lastrowid
        if not last_id:
            raise ValueError("Insert failed")
        return last_id

    @classmethod
    def _update(cls, data: dict, where: dict):
        columns = ", ".join(f"{key} = ?" for key in data.keys())
        where_columns = " AND ".join(f"{key} = ?" for key in where.keys())
        cls.storage.execute(
            f"UPDATE {cls.name} SET {columns} WHERE {where_columns}",
            tuple(data.values()) + tuple(where.values()),
        )

import re
import sqlite3
from dataclasses import dataclass


@dataclass
class User:
    username: str = ""
    user_id: int = -1
    rights: int = 0  # 0 - pending, 1 - user, 2 - admin


class Storage:
    def __init__(self):
        self.conn = sqlite3.connect("storage.db")
        self.cursor = self.conn.cursor()

        self.create_table()

    def create_table(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                rights INTEGER
            )
            """
        )
    
    def add_user(self, user: User):
        self.cursor.execute(
            """
            INSERT INTO users (user_id, username, rights)
            VALUES (?, ?, ?)
            """,
            (user.user_id, user.username, user.rights)
        )
        self.conn.commit()
    
    def get_user(self, user_id: int) -> User | None:
        self.cursor.execute(
            """
            SELECT * FROM users WHERE user_id = ?
            """,
            (user_id,)
        )
        return User(*row) if (row := self.cursor.fetchone()) else None

    def get_user_by_username(self, username: str) -> User | None:
        self.cursor.execute(
            """
            SELECT * FROM users WHERE username = ?
            """,
            (username,)
        )
        return User(*row) if (row := self.cursor.fetchone()) else None

    def set_rights(self, user_id: int, rights: int):
        self.cursor.execute(
            """
            UPDATE users SET rights = ? WHERE user_id = ?
            """,
            (rights, user_id)
        )
        self.conn.commit()
    
    def delete_user(self, user_id: int):
        self.cursor.execute(
            """
            DELETE FROM users WHERE user_id = ?
            """,
            (user_id,)
        )
        self.conn.commit()
    
    def get_users(self) -> list[User]:
        self.cursor.execute(
            """
            SELECT * FROM users
            """
        )
        return [User(*row) for row in self.cursor.fetchall()]
    
    def get_users_with_rights(self, rights: int) -> list[User]:
        self.cursor.execute(
            """
            SELECT * FROM users WHERE rights = ?
            """,
            (rights,)
        )
        return [User(*row) for row in self.cursor.fetchall()]
        
    def get_user_rights(self, user_id: int) -> int:
        self.cursor.execute(
            """
            SELECT rights FROM users WHERE user_id = ?
            """,
            (user_id,)
        )
        row = self.cursor.fetchone()
        if not row:
            raise ValueError("User not found")
        return row[0]
    
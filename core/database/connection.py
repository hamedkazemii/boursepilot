"""مدیر اتصال SQLite با schema migration سبک."""

from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from config import settings
from core.database.schema import SCHEMA_VERSION, apply_schema

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_default_db: Optional["Database"] = None


class Database:
    """اتصال thread-safe سبک به SQLite."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                str(self.path),
                timeout=30,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        with self.transaction() as conn:
            apply_schema(conn)
        logger.info("database ready path=%s version=%s", self.path, SCHEMA_VERSION)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
        finally:
            pass

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def execute(self, sql: str, params: tuple | dict = ()) -> sqlite3.Cursor:
        with self.transaction() as conn:
            return conn.execute(sql, params)

    def executemany(self, sql: str, seq: list) -> sqlite3.Cursor:
        with self.transaction() as conn:
            return conn.executemany(sql, seq)

    def fetchone(self, sql: str, params: tuple | dict = ()) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple | dict = ()) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute(sql, params).fetchall())

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None


def get_database(path: Optional[str | Path] = None) -> Database:
    """Singleton پیش‌فرض برای مسیر settings.DATABASE_PATH."""
    global _default_db
    target = Path(path) if path is not None else Path(settings.DATABASE_PATH)
    with _lock:
        if _default_db is None or Path(_default_db.path) != target:
            _default_db = Database(target)
        return _default_db

import os
import sqlite3

import config


def get_connection() -> sqlite3.Connection:
    folder = os.path.dirname(config.DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    connection = sqlite3.connect(config.DB_PATH, timeout=10)  # busy timeout: job e handler girano su thread diversi
    connection.execute("PRAGMA foreign_keys = ON")  # SQLite non applica le FK di default
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def init_db() -> None:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            website TEXT NOT NULL,
            failures INTEGER NOT NULL DEFAULT 0
        )
    """)

    # migrazione per i DB creati prima della colonna failures
    columns = [row[1] for row in cursor.execute("PRAGMA table_info(products)")]
    if "failures" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN failures INTEGER NOT NULL DEFAULT 0")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            target_price REAL,
            user_seq INTEGER,
            FOREIGN KEY (product_id) REFERENCES products(id),
            UNIQUE (chat_id, product_id)
        )
    """)

    # migrazione per i DB creati prima di user_seq: backfill 1..N per chat in ordine di inserimento
    columns = [row[1] for row in cursor.execute("PRAGMA table_info(subscriptions)")]
    if "user_seq" not in columns:
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN user_seq INTEGER")
        cursor.execute("""UPDATE subscriptions SET user_seq = (
                              SELECT COUNT(*) FROM subscriptions s2
                              WHERE s2.chat_id = subscriptions.chat_id AND s2.id <= subscriptions.id)""")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sub_chat_seq ON subscriptions (chat_id, user_seq)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            price REAL NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            language TEXT
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history (product_id)")

    connection.commit()
    connection.close()

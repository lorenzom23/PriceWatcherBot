from contextlib import contextmanager

from storage.database import get_connection


@contextmanager
def _cursor(commit=False):
    """Yield a cursor; commit on write paths, always close (rolls back on error)."""
    connection = get_connection()
    try:
        yield connection.cursor()
        if commit:
            connection.commit()
    finally:
        connection.close()

# products
def add_product(url, name, website) -> tuple[int, bool]:
    """Add a product and returns (id, created)"""
    with _cursor(commit=True) as cursor:
        cursor.execute("INSERT OR IGNORE INTO products (url, name, website) VALUES (?, ?, ?)", (url, name, website))
        created = cursor.rowcount == 1
        product_id = cursor.execute("SELECT id FROM products WHERE url = ?", (url,)).fetchone()
    return product_id[0], created

def get_tracked_products() -> list:
    """Returns the products at least one user subscribes to"""
    with _cursor() as cursor:
        return cursor.execute("""SELECT id, url, name FROM products
                                 WHERE id IN (SELECT product_id FROM subscriptions)""").fetchall()

def record_check_failure(product_id) -> int:
    """Increment and return the consecutive-failure counter"""
    with _cursor(commit=True) as cursor:
        cursor.execute("UPDATE products SET failures = failures + 1 WHERE id = ?", (product_id,))
        row = cursor.execute("SELECT failures FROM products WHERE id = ?", (product_id,)).fetchone()
    return row[0] if row else 0

def reset_check_failures(product_id):
    """Zero the failure counter after a successful check"""
    with _cursor(commit=True) as cursor:
        cursor.execute("UPDATE products SET failures = 0 WHERE id = ? AND failures != 0", (product_id,))

# price
def add_price(product_id, price, timestamp):
    """Add a price"""
    with _cursor(commit=True) as cursor:
        cursor.execute("INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, ?)",
                       (product_id, price, timestamp))

def prune_history(cutoff_iso):
    """Delete the price points older than the ISO cutoff"""
    with _cursor(commit=True) as cursor:
        # i timestamp sono ISO-8601: il confronto lessicografico è quello cronologico
        cursor.execute("DELETE FROM price_history WHERE timestamp < ?", (cutoff_iso,))

def get_last_price(product_id) -> float | None:
    """Get the last price of the passed product_id"""
    with _cursor() as cursor:
        price = cursor.execute("SELECT price FROM price_history WHERE product_id = ? ORDER BY id DESC LIMIT 1",
                               (product_id,)).fetchone()
    return price[0] if price else None

def get_history(product_id) -> list:
    """Returns all the prices"""
    with _cursor() as cursor:
        return cursor.execute("SELECT price, timestamp FROM price_history WHERE product_id = ? ORDER BY id",
                              (product_id,)).fetchall()

# subs
def add_subscription(chat_id, product_id, target_price = None):
    """Add a subscriber"""
    with _cursor(commit=True) as cursor:
        # COALESCE: un re-track senza soglia non deve azzerare quella esistente
        cursor.execute("INSERT INTO subscriptions (chat_id, product_id, target_price) VALUES (?, ?, ?)" \
                       "ON CONFLICT(chat_id, product_id) DO UPDATE SET target_price = COALESCE(excluded.target_price, target_price)",
                       (chat_id, product_id, target_price))

def get_subscribers(product_id) -> list:
    """Get all the subscribers"""
    with _cursor() as cursor:
        return cursor.execute("SELECT chat_id, target_price FROM subscriptions WHERE product_id = ?",
                              (product_id,)).fetchall()

def remove_subscription(chat_id, product_id):
    """Delete a subscriber from a product"""
    with _cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM subscriptions WHERE chat_id = ? AND product_id = ?",
                       (chat_id, product_id,))
        _delete_orphans(cursor)

def remove_chat_subscriptions(chat_id):
    """Delete every subscription of a chat (e.g. the user blocked the bot)"""
    with _cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM subscriptions WHERE chat_id = ?", (chat_id,))
        _delete_orphans(cursor)

def _delete_orphans(cursor):
    """Drop products (and their history) nobody subscribes to anymore"""
    cursor.execute("DELETE FROM price_history WHERE product_id NOT IN (SELECT product_id FROM subscriptions)")
    cursor.execute("DELETE FROM products WHERE id NOT IN (SELECT product_id FROM subscriptions)")

def get_subscriptions(chat_id) -> list:
    """Returns the products tracked"""
    with _cursor() as cursor:
        return cursor.execute("""SELECT subscriptions.product_id, products.name
                                 FROM subscriptions
                                 JOIN products ON subscriptions.product_id = products.id
                                 WHERE chat_id = ?""", (chat_id,)).fetchall()

# users
def save_user(chat_id, language):
    """Insert or update the user's language"""
    with _cursor(commit=True) as cursor:
        cursor.execute("""INSERT INTO users (chat_id, language) VALUES (?, ?)
                          ON CONFLICT(chat_id) DO UPDATE SET language = excluded.language""",
                       (chat_id, language))

def get_user_language(chat_id) -> str | None:
    """Return the saved language of a user, or None"""
    with _cursor() as cursor:
        row = cursor.execute("SELECT language FROM users WHERE chat_id = ?", (chat_id,)).fetchone()
    return row[0] if row else None

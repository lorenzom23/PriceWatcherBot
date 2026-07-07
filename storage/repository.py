from storage.database import get_connection

# products
def add_product(url, name, website) -> tuple[int, bool]:
    """Add a product and returns (id, created)"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("INSERT OR IGNORE INTO products (url, name, website) VALUES (?, ?, ?)", (url, name, website))
    created = cursor.rowcount == 1
    product_id = cursor.execute("SELECT id FROM products WHERE url = ?", (url,)).fetchone()

    connection.commit()
    connection.close()
    return product_id[0], created

def get_tracked_products() -> list:
    """Returns the products at least one user subscribes to"""
    connection = get_connection()
    cursor = connection.cursor()

    products = cursor.execute("""SELECT id, url, name FROM products
                                 WHERE id IN (SELECT product_id FROM subscriptions)""").fetchall()

    connection.close()
    return products

def record_check_failure(product_id) -> int:
    """Increment and return the consecutive-failure counter"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("UPDATE products SET failures = failures + 1 WHERE id = ?", (product_id,))
    row = cursor.execute("SELECT failures FROM products WHERE id = ?", (product_id,)).fetchone()

    connection.commit()
    connection.close()
    return row[0] if row else 0

def reset_check_failures(product_id):
    """Zero the failure counter after a successful check"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("UPDATE products SET failures = 0 WHERE id = ? AND failures != 0", (product_id,))

    connection.commit()
    connection.close()

# price
def add_price(product_id, price, timestamp):
    """Add a price"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, ?)",
                              (product_id, price, timestamp))

    connection.commit()
    connection.close()

def prune_history(cutoff_iso):
    """Delete the price points older than the ISO cutoff"""
    connection = get_connection()
    cursor = connection.cursor()

    # i timestamp sono ISO-8601: il confronto lessicografico è quello cronologico
    cursor.execute("DELETE FROM price_history WHERE timestamp < ?", (cutoff_iso,))

    connection.commit()
    connection.close()

def get_last_price(product_id) -> float | None:
    """Get the last price of the passed product_id"""
    connection = get_connection()
    cursor = connection.cursor()

    price = cursor.execute("SELECT price FROM price_history WHERE product_id = ? ORDER BY id DESC LIMIT 1",
                              (product_id, )).fetchone()

    connection.close()
    return price[0] if price else None

def get_history(product_id) -> list:
    """Returns all the prices"""    
    connection = get_connection()
    cursor = connection.cursor()

    prices = cursor.execute("SELECT price, timestamp FROM price_history WHERE product_id = ? ORDER BY id",
                              (product_id, )).fetchall()

    connection.close()
    return prices

# subs
def add_subscription(chat_id, product_id, target_price = None):
    """Add a subscriber"""
    connection = get_connection()
    cursor = connection.cursor()

    # COALESCE: un re-track senza soglia non deve azzerare quella esistente
    cursor.execute("INSERT INTO subscriptions (chat_id, product_id, target_price) VALUES (?, ?, ?)" \
                    "ON CONFLICT(chat_id, product_id) DO UPDATE SET target_price = COALESCE(excluded.target_price, target_price)",
                              (chat_id, product_id, target_price))

    connection.commit()
    connection.close()

def get_subscribers(product_id) -> list:
    """Get all the subscribers"""
    connection = get_connection()
    cursor = connection.cursor()

    subscribers = cursor.execute("SELECT chat_id, target_price FROM subscriptions WHERE product_id = ?",
                              (product_id, )).fetchall()

    connection.close()
    return subscribers

def remove_subscription(chat_id, product_id):
    """Delete a subscriber from a product"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM subscriptions WHERE chat_id = ? AND product_id = ?",
                              (chat_id, product_id,))
    _delete_orphans(cursor)

    connection.commit()
    connection.close()

def remove_chat_subscriptions(chat_id):
    """Delete every subscription of a chat (e.g. the user blocked the bot)"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM subscriptions WHERE chat_id = ?", (chat_id,))
    _delete_orphans(cursor)

    connection.commit()
    connection.close()

def _delete_orphans(cursor):
    """Drop products (and their history) nobody subscribes to anymore"""
    cursor.execute("DELETE FROM price_history WHERE product_id NOT IN (SELECT product_id FROM subscriptions)")
    cursor.execute("DELETE FROM products WHERE id NOT IN (SELECT product_id FROM subscriptions)")

def get_subscriptions(chat_id) -> list:
    """Returns teh products tracked"""    
    connection = get_connection()
    cursor = connection.cursor()

    products = cursor.execute("""SELECT subscriptions.product_id, products.name
                                FROM subscriptions
                                JOIN products ON subscriptions.product_id = products.id
                                WHERE chat_id = ?""", (chat_id,)).fetchall()

    connection.close()
    return products

# users
def save_user(chat_id, language):
    """Insert or update the user's language"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""INSERT INTO users (chat_id, language) VALUES (?, ?)
                      ON CONFLICT(chat_id) DO UPDATE SET language = excluded.language""",
                   (chat_id, language))

    connection.commit()
    connection.close()

def get_user_language(chat_id) -> str | None:
    """Return the saved language of a user, or None"""
    connection = get_connection()
    cursor = connection.cursor()

    row = cursor.execute("SELECT language FROM users WHERE chat_id = ?", (chat_id,)).fetchone()

    connection.close()
    return row[0] if row else None

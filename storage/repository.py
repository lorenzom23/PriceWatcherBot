from storage.database import get_connection

# products
def add_product(url, name, website) -> int:
    """Add a product and returns the ID"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("INSERT OR IGNORE INTO products (url, name, website) VALUES (?, ?, ?)", (url, name, website))
    product_id = cursor.execute("SELECT id FROM products WHERE url = ?", (url,)).fetchone()

    connection.commit()
    connection.close()
    return product_id[0]

def get_all_products() -> list:
    """Retunrs list of all products"""
    connection = get_connection()
    cursor = connection.cursor()

    products = cursor.execute("SELECT id, url FROM products").fetchall()

    connection.close()
    return products

# price
def add_price(product_id, price, timestamp):
    """Add a price"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, ?)",
                              (product_id, price, timestamp))

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

    cursor.execute("INSERT INTO subscriptions (chat_id, product_id, target_price) VALUES (?, ?, ?)" \
                    "ON CONFLICT(chat_id, product_id) DO UPDATE SET target_price = excluded.target_price",
                              (chat_id, product_id, target_price))

    connection.commit()
    connection.close()

def get_subscribers(product_id) -> list:
    """Get all the subscribers"""
    connection = get_connection()
    cursor = connection.cursor()

    subscribers = cursor.execute("SELECT chat_id FROM subscriptions WHERE product_id = ?",
                              (product_id, )).fetchall()

    connection.close()
    return subscribers

def remove_subscription(chat_id, product_id):
    """Delete a subscriber from a product"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM subscriptions WHERE chat_id = ? AND product_id = ?",
                              (chat_id, product_id,))

    connection.commit()
    connection.close()

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

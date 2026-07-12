import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psycopg2
from psycopg2 import pool

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

NEON_DB_URL = os.getenv('NEON_DB_URL')

connection_pool = None

def init_connection_pool():
    global connection_pool
    try:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=NEON_DB_URL,
            connect_timeout=30
        )
        print("[OK] Neon DB connection pool initialized successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to initialize Neon DB pool: {e}")
        return False

def get_neon_connection():
    try:
        if connection_pool:
            return connection_pool.getconn()
        return psycopg2.connect(NEON_DB_URL, connect_timeout=30)
    except Exception as e:
        print(f"[ERROR] Connection error: {e}")
        raise

def release_connection(conn):
    try:
        if connection_pool and conn:
            connection_pool.putconn(conn)
    except Exception as e:
        print(f"[ERROR] Failed to release connection: {e}")


# ==================== REFERRAL CODES TABLE ====================

def init_referral_codes_table():
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referral_codes (
                id SERIAL PRIMARY KEY,
                code VARCHAR(100) UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        print("[OK] Referral codes table created/verified in Neon DB")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create referral_codes table: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def validate_referral_code(code):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, code FROM referral_codes WHERE code = %s AND is_active = TRUE",
            (code.strip().upper(),)
        )
        row = cursor.fetchone()
        cursor.close()
        return True if row else False
    except Exception as e:
        print(f"[ERROR] validate_referral_code: {e}")
        return False
    finally:
        if conn:
            release_connection(conn)

def add_referral_code(code):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO referral_codes (code) VALUES (%s) ON CONFLICT (code) DO UPDATE SET is_active = TRUE",
            (code.strip().upper(),)
        )
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] add_referral_code: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def delete_referral_code(code_id):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM referral_codes WHERE id = %s", (code_id,))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] delete_referral_code: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def get_all_referral_codes():
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, code, is_active, created_at FROM referral_codes ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        return [{'id': r[0], 'code': r[1], 'is_active': r[2], 'created_at': r[3]} for r in rows]
    except Exception as e:
        print(f"[ERROR] get_all_referral_codes: {e}")
        return []
    finally:
        if conn:
            release_connection(conn)

def toggle_referral_code(code_id):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE referral_codes SET is_active = NOT is_active WHERE id = %s", (code_id,))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] toggle_referral_code: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def has_customer_used_referral_code(phone_number, referral_code):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        normalized_phone = phone_number.strip()
        normalized_code = referral_code.strip().upper()
        cursor.execute(
            "SELECT id FROM orders WHERE phone_number = %s AND referral_code = %s LIMIT 1",
            (normalized_phone, normalized_code)
        )
        row = cursor.fetchone()
        if row:
            cursor.close()
            return True
        cursor.execute(
            "SELECT id FROM completed_orders WHERE phone_number = %s AND referral_code = %s LIMIT 1",
            (normalized_phone, normalized_code)
        )
        row = cursor.fetchone()
        cursor.close()
        return True if row else False
    except Exception as e:
        print(f"[ERROR] has_customer_used_referral_code: {e}")
        raise
    finally:
        if conn:
            release_connection(conn)

# ==================== RESERVATIONS TABLE ====================

def init_reservations_table():
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id SERIAL PRIMARY KEY,
                product_id VARCHAR(50) NOT NULL,
                session_id VARCHAR(64) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_reservations_product ON reservations(product_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reservations_expires ON reservations(expires_at)")
        conn.commit()
        cursor.close()
        print("[OK] Reservations table created/verified in Neon DB")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create reservations table: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def create_reservation(product_id, session_id, expiry_minutes=10):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        cursor.execute(
            "DELETE FROM reservations WHERE product_id = %s AND expires_at < NOW()",
            (product_id,)
        )
        cursor.execute(
            "SELECT id, session_id FROM reservations WHERE product_id = %s AND expires_at > NOW()",
            (product_id,)
        )
        existing = cursor.fetchone()
        if existing and existing[1] != session_id:
            cursor.close()
            return False, "Product is temporarily reserved by another customer"
        cursor.execute("""
            INSERT INTO reservations (product_id, session_id, expires_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (product_id) DO UPDATE SET
                expires_at = EXCLUDED.expires_at,
                session_id = EXCLUDED.session_id
        """, (product_id, session_id, expires_at))
        conn.commit()
        cursor.close()
        return True, "Reserved"
    except Exception as e:
        print(f"[ERROR] create_reservation: {e}")
        if conn:
            conn.rollback()
        return False, str(e)
    finally:
        if conn:
            release_connection(conn)

def get_active_reservation(product_id):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, session_id, expires_at FROM reservations WHERE product_id = %s AND expires_at > NOW()",
            (product_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        if row:
            return {'id': row[0], 'session_id': row[1], 'expires_at': row[2]}
        return None
    except Exception as e:
        print(f"[ERROR] get_active_reservation: {e}")
        return None
    finally:
        if conn:
            release_connection(conn)

def release_reservation(product_id, session_id=None):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        if session_id:
            cursor.execute(
                "DELETE FROM reservations WHERE product_id = %s AND session_id = %s",
                (product_id, session_id)
            )
        else:
            cursor.execute("DELETE FROM reservations WHERE product_id = %s", (product_id,))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] release_reservation: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def get_reserved_product_ids():
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_id FROM reservations WHERE expires_at > NOW()")
        rows = cursor.fetchall()
        cursor.close()
        return {row[0] for row in rows}
    except Exception as e:
        print(f"[ERROR] get_reserved_product_ids: {e}")
        return set()
    finally:
        if conn:
            release_connection(conn)

def cleanup_expired_reservations():
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reservations WHERE expires_at < NOW()")
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()
        return deleted
    except Exception as e:
        print(f"[ERROR] cleanup_expired_reservations: {e}")
        if conn:
            conn.rollback()
        return 0
    finally:
        if conn:
            release_connection(conn)

# ==================== PRODUCTS TABLE ====================

def init_products_table():
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id VARCHAR(50) PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                price NUMERIC(10, 2) NOT NULL,
                size VARCHAR(20) NOT NULL,
                image_url TEXT,
                original_price NUMERIC(10, 2),
                stock INTEGER DEFAULT 1,
                code VARCHAR(50),
                condition_rating NUMERIC(3, 1) DEFAULT 9.0,
                is_sale INTEGER DEFAULT 0,
                sale_end_time TIMESTAMP,
                shipping_rule VARCHAR(100) DEFAULT 'Standard Shipping Applies',
                imported_premium INTEGER DEFAULT 0,
                brand VARCHAR(100),
                description TEXT,
                color VARCHAR(50),
                category VARCHAR(100),
                condition VARCHAR(100),
                images TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS images TEXT")
        cursor.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS category VARCHAR(100)")
        conn.commit()
        cursor.close()
        print("[OK] Products table created/verified in Neon DB")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create products table: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

PRODUCT_COLUMNS = """
    product_id, title, price, size, image_url, original_price, stock,
    code, condition_rating, is_sale, sale_end_time, shipping_rule,
    imported_premium, brand, description, color, category, condition,
    COALESCE(images, '[]'), created_at
"""

def _row_to_product(row):
    if not row:
        return None
    images_raw = row[18]
    images = []
    if images_raw:
        try:
            images = json.loads(images_raw)
        except (json.JSONDecodeError, TypeError):
            images = []
    if not images and row[4]:
        images = [row[4]]
    return {
        'id': row[0],
        'product_id': row[0],
        'name': row[1],
        'title': row[1],
        'price': float(row[2]),
        'size': row[3],
        'image_url': row[4],
        'original_price': float(row[5]) if row[5] else None,
        'stock': row[6],
        'code': row[7],
        'condition_rating': float(row[8]) if row[8] else 9.0,
        'is_sale': row[9],
        'sale_end_time': row[10].isoformat() if row[10] else None,
        'shipping_rule': row[11],
        'imported_premium': row[12],
        'brand': row[13],
        'description': row[14],
        'color': row[15],
        'category': row[16],
        'condition': row[17],
        'images': images,
        'created_at': row[19].isoformat() if row[19] else None
    }

def get_all_products_db():
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {PRODUCT_COLUMNS} FROM products WHERE stock > 0 ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        return [_row_to_product(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] Failed to fetch products: {e}")
        return []
    finally:
        if conn:
            release_connection(conn)

def get_product_by_id_db(product_id):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {PRODUCT_COLUMNS} FROM products WHERE product_id = %s", (product_id,))
        row = cursor.fetchone()
        cursor.close()
        return _row_to_product(row)
    except Exception as e:
        print(f"[ERROR] Failed to fetch product: {e}")
        return None
    finally:
        if conn:
            release_connection(conn)

def add_product_to_db(data):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products
            (product_id, title, price, size, image_url, original_price, stock,
             code, condition_rating, is_sale, sale_end_time, shipping_rule,
             imported_premium, brand, description, color, category, condition, images)
            VALUES (%(product_id)s, %(title)s, %(price)s, %(size)s, %(image_url)s,
                    %(original_price)s, %(stock)s, %(code)s, %(condition_rating)s,
                    %(is_sale)s, %(sale_end_time)s, %(shipping_rule)s,
                    %(imported_premium)s, %(brand)s, %(description)s, %(color)s,
                    %(category)s, %(condition)s, %(images)s)
        """, data)
        conn.commit()
        cursor.close()
        print(f"[OK] Product {data['product_id']} added to Neon DB")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to add product: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def update_product_in_db(product_id, data):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products SET
                title = %(title)s, price = %(price)s, size = %(size)s,
                original_price = %(original_price)s, stock = %(stock)s,
                code = %(code)s, condition_rating = %(condition_rating)s,
                category = %(category)s, description = %(description)s, images = %(images)s
            WHERE product_id = %(product_id)s
        """, {**data, 'product_id': product_id})
        conn.commit()
        cursor.close()
        print(f"[OK] Product {product_id} updated in Neon DB")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update product: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def delete_product_from_db(product_id):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
        conn.commit()
        cursor.close()
        print(f"[OK] Product {product_id} deleted from Neon DB")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to delete product: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def search_products_db(query):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        q = f"%{query}%"
        cursor.execute(f"""
            SELECT {PRODUCT_COLUMNS} FROM products
            WHERE stock > 0
              AND (title ILIKE %s OR brand ILIKE %s OR description ILIKE %s OR category ILIKE %s)
            ORDER BY created_at DESC
        """, (q, q, q, q))
        rows = cursor.fetchall()
        cursor.close()
        return [_row_to_product(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] Failed to search products: {e}")
        return []
    finally:
        if conn:
            release_connection(conn)

def filter_products_by_size_db(size):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {PRODUCT_COLUMNS} FROM products WHERE size = %s AND stock > 0 ORDER BY created_at DESC", (size,))
        rows = cursor.fetchall()
        cursor.close()
        return [_row_to_product(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] Failed to filter products: {e}")
        return []
    finally:
        if conn:
            release_connection(conn)

def filter_products_by_category_db(category):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {PRODUCT_COLUMNS} FROM products WHERE category = %s AND stock > 0 ORDER BY created_at DESC", (category,))
        rows = cursor.fetchall()
        cursor.close()
        return [_row_to_product(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] Failed to filter products by category: {e}")
        return []
    finally:
        if conn:
            release_connection(conn)

def filter_products_by_size_and_category_db(size, category):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {PRODUCT_COLUMNS} FROM products WHERE size = %s AND category = %s AND stock > 0 ORDER BY created_at DESC", (size, category))
        rows = cursor.fetchall()
        cursor.close()
        return [_row_to_product(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] Failed to filter products: {e}")
        return []
    finally:
        if conn:
            release_connection(conn)

def get_all_categories_db():
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM products WHERE stock > 0 AND category IS NOT NULL AND category != '' ORDER BY category")
        rows = cursor.fetchall()
        cursor.close()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"[ERROR] Failed to fetch categories: {e}")
        return []
    finally:
        if conn:
            release_connection(conn)

def reduce_stock_db(product_id, quantity=1):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET stock = GREATEST(stock - %s, 0) WHERE product_id = %s", (quantity, product_id))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to reduce stock: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

# ==================== ORDERS TABLE ====================

def init_orders_table():
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name VARCHAR(255) NOT NULL,
                phone_number VARCHAR(20) NOT NULL,
                delivery_address TEXT NOT NULL,
                city VARCHAR(100),
                product_id_or_name VARCHAR(255) NOT NULL,
                quantity INTEGER DEFAULT 1,
                total_price NUMERIC(10, 2) NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending',
                notes TEXT,
                scheme VARCHAR(50) DEFAULT 'None'
            )
        """)
        cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS scheme VARCHAR(50) DEFAULT 'None'")
        cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS referral_code VARCHAR(100)")
        cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS product_description TEXT")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        conn.commit()
        cursor.close()
        print("[OK] Orders table created/verified in Neon DB")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create orders table: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def _row_to_order(row):
    if not row:
        return None
    images_raw = row[16] if len(row) > 16 else None
    product_images = []
    if images_raw:
        try:
            product_images = json.loads(images_raw)
        except (json.JSONDecodeError, TypeError):
            product_images = []
    return {
        'id': row[0],
        'customer_name': row[1],
        'phone_number': row[2],
        'delivery_address': row[3],
        'city': row[4],
        'product_id_or_name': row[5],
        'quantity': row[6],
        'total_price': float(row[7]),
        'order_date': row[8],
        'status': row[9],
        'notes': row[10],
        'scheme': row[11] if len(row) > 11 else 'None',
        'referral_code': row[12] if len(row) > 12 else None,
        'product_description': row[13] if len(row) > 13 else None,
        'product_title': row[14] if len(row) > 14 else None,
        'product_price': float(row[15]) if len(row) > 15 and row[15] else None,
        'product_images': product_images
    }

def create_order(customer_name, phone_number, delivery_address, city,
                 product_id_or_name, quantity, total_price, notes=None, scheme='None', referral_code=None, product_description=None):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders
            (customer_name, phone_number, delivery_address, city,
             product_id_or_name, quantity, total_price, notes, status, order_date, scheme, referral_code, product_description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s)
            RETURNING id
        """, (customer_name, phone_number, delivery_address, city,
              product_id_or_name, quantity, total_price, notes, datetime.utcnow(), scheme, referral_code, product_description))
        order_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        print(f"[OK] Order created: ID {order_id}")
        return order_id
    except Exception as e:
        print(f"[ERROR] Failed to create order: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            release_connection(conn)

def get_order_by_id(order_id):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, customer_name, phone_number, delivery_address, city,
                   product_id_or_name, quantity, total_price, order_date,
                   status, notes, scheme, referral_code, product_description
            FROM orders WHERE id = %s
        """, (order_id,))
        row = cursor.fetchone()
        cursor.close()
        return _row_to_order(row)
    except Exception as e:
        print(f"[ERROR] Failed to fetch order: {e}")
        return None
    finally:
        if conn:
            release_connection(conn)

def get_all_orders(status=None):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        if status:
            cursor.execute("""
                SELECT o.id, o.customer_name, o.phone_number, o.delivery_address, o.city,
                       o.product_id_or_name, o.quantity, o.total_price, o.order_date,
                       o.status, o.notes, o.scheme, o.referral_code, o.product_description,
                       p.title AS product_title, p.price AS product_price, p.images AS product_images
                FROM orders o
                LEFT JOIN products p ON SPLIT_PART(o.product_id_or_name, ' - ', 1) = p.product_id
                WHERE o.status = %s ORDER BY o.order_date DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT o.id, o.customer_name, o.phone_number, o.delivery_address, o.city,
                       o.product_id_or_name, o.quantity, o.total_price, o.order_date,
                       o.status, o.notes, o.scheme, o.referral_code, o.product_description,
                       p.title AS product_title, p.price AS product_price, p.images AS product_images
                FROM orders o
                LEFT JOIN products p ON SPLIT_PART(o.product_id_or_name, ' - ', 1) = p.product_id
                ORDER BY o.order_date DESC
            """)
        rows = cursor.fetchall()
        cursor.close()
        return [_row_to_order(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] Failed to fetch orders: {e}")
        return []
    finally:
        if conn:
            release_connection(conn)

def update_order_status(order_id, new_status):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
        conn.commit()
        cursor.close()
        print(f"[OK] Order {order_id} status updated to {new_status}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update order status: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

# ==================== COMPLETED ORDERS TABLE ====================

def init_completed_orders_table():
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS completed_orders (
                id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL,
                customer_name VARCHAR(255) NOT NULL,
                phone_number VARCHAR(20) NOT NULL,
                delivery_address TEXT NOT NULL,
                city VARCHAR(100),
                product_id_or_name VARCHAR(255) NOT NULL,
                quantity INTEGER DEFAULT 1,
                total_price NUMERIC(10, 2) NOT NULL,
                order_date TIMESTAMP,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                scheme VARCHAR(50) DEFAULT 'None'
            )
        """)
        cursor.execute("ALTER TABLE completed_orders ADD COLUMN IF NOT EXISTS scheme VARCHAR(50) DEFAULT 'None'")
        cursor.execute("ALTER TABLE completed_orders ADD COLUMN IF NOT EXISTS referral_code VARCHAR(100)")
        cursor.execute("ALTER TABLE completed_orders ADD COLUMN IF NOT EXISTS product_description TEXT")
        conn.commit()
        cursor.close()
        print("[OK] Completed orders table created/verified in Neon DB")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create completed_orders table: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def mark_order_complete(order_id):
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, customer_name, phone_number, delivery_address, city,
                   product_id_or_name, quantity, total_price, order_date, notes, scheme, referral_code,
                   product_description
            FROM orders WHERE id = %s
        """, (order_id,))
        order = cursor.fetchone()
        if not order:
            print(f"[ERROR] Order {order_id} not found")
            return False
        cursor.execute("""
            INSERT INTO completed_orders
            (order_id, customer_name, phone_number, delivery_address, city,
             product_id_or_name, quantity, total_price, order_date, notes, scheme, referral_code,
             product_description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, order)
        cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))
        conn.commit()
        cursor.close()
        print(f"[OK] Order {order_id} marked complete and moved to completed_orders")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to mark order complete: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def get_completed_orders():
    conn = None
    try:
        conn = get_neon_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT co.id, co.order_id, co.customer_name, co.phone_number, co.delivery_address,
                   co.city, co.product_id_or_name, co.quantity, co.total_price, co.order_date,
                   co.completed_at, co.notes, co.scheme, co.referral_code, co.product_description,
                   p.title AS product_title, p.images AS product_images
            FROM completed_orders co
            LEFT JOIN products p ON SPLIT_PART(co.product_id_or_name, ' - ', 1) = p.product_id
            ORDER BY co.completed_at DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        result = []
        for r in rows:
            images_raw = r[16] if len(r) > 16 else None
            product_images = []
            if images_raw:
                try:
                    product_images = json.loads(images_raw)
                except (json.JSONDecodeError, TypeError):
                    product_images = []
            result.append({
                'id': r[0],
                'order_id': r[1],
                'customer_name': r[2],
                'phone_number': r[3],
                'delivery_address': r[4],
                'city': r[5],
                'product_id_or_name': r[6],
                'quantity': r[7],
                'total_price': float(r[8]),
                'order_date': r[9],
                'completed_at': r[10],
                'notes': r[11],
                'scheme': r[12] if len(r) > 12 else 'None',
                'referral_code': r[13] if len(r) > 13 else None,
                'product_description': r[14] if len(r) > 14 else None,
                'product_title': r[15] if len(r) > 15 else None,
                'product_images': product_images
            })
        return result
    except Exception as e:
        print(f"[ERROR] Failed to fetch completed orders: {e}")
        return []
    finally:
        if conn:
            release_connection(conn)

# ==================== CART ====================

SHIPPING_FEE = 500

def calculate_totals(cart_items, city=None):
    """
    cart_items: list of dicts with 'product_id' and 'quantity'
    city: optional string — if 'karachi' (case-insensitive), shipping is free
    Returns: {items: [...], item_count, subtotal, shipping, total}
    """
    items = []
    subtotal = 0.0

    for item in cart_items:
        product = get_product_by_id_db(item.get('product_id', ''))
        if not product or product.get('stock', 0) <= 0:
            continue

        qty = min(item.get('quantity', 1), product['stock'])
        price = float(product['price'])
        line_total = round(price * qty, 2)

        imgs = product.get('images') or []
        if not imgs and product.get('image_url'):
            imgs = [product['image_url']]

        items.append({
            'product_id': product['id'],
            'name': product.get('name', product.get('title', '')),
            'price': price,
            'quantity': qty,
            'line_total': line_total,
            'image': imgs[0] if imgs else '',
            'stock': product['stock']
        })
        subtotal += line_total

    subtotal = round(subtotal, 2)

    if city and city.strip().lower() == 'karachi':
        shipping = 0
    else:
        shipping = SHIPPING_FEE if items else 0

    total = round(max(subtotal + shipping, 0), 2)

    return {
        'cart_items': items,
        'item_count': len(items),
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total
    }

# ==================== CLEANUP ====================

def close_all_connections():
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        print("[OK] All Neon DB connections closed")

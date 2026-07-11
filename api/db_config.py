import os
import json
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

load_dotenv()

NEON_DB_URL = os.getenv('NEON_DB_URL')

def get_connection():
    return psycopg2.connect(NEON_DB_URL, connect_timeout=10)


# ==================== REFERRAL CODES TABLE ====================

def init_referral_codes_table():
    conn = None
    try:
        conn = get_connection()
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
        return True
    except Exception as e:
        print(f"[ERROR] init_referral_codes_table: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def validate_referral_code(code):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, code FROM referral_codes WHERE code = %s AND is_active = TRUE",
            (code.strip().upper(),)
        )
        row = cursor.fetchone()
        cursor.close()
        if row:
            return True
        return False
    except Exception as e:
        print(f"[ERROR] validate_referral_code: {e}")
        return False
    finally:
        if conn:
            conn.close()

def add_referral_code(code):
    conn = None
    try:
        conn = get_connection()
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
            conn.close()

def delete_referral_code(code_id):
    conn = None
    try:
        conn = get_connection()
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
            conn.close()

def get_all_referral_codes():
    conn = None
    try:
        conn = get_connection()
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
            conn.close()

def toggle_referral_code(code_id):
    conn = None
    try:
        conn = get_connection()
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
            conn.close()

# ==================== PRODUCTS TABLE ====================

def init_products_table():
    conn = None
    try:
        conn = get_connection()
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
        return True
    except Exception as e:
        print(f"[ERROR] init_products_table: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

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
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {PRODUCT_COLUMNS} FROM products WHERE stock > 0 ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        return [_row_to_product(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] get_all_products_db: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_product_by_id_db(product_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {PRODUCT_COLUMNS} FROM products WHERE product_id = %s", (product_id,))
        row = cursor.fetchone()
        cursor.close()
        return _row_to_product(row)
    except Exception as e:
        print(f"[ERROR] get_product_by_id_db: {e}")
        return None
    finally:
        if conn:
            conn.close()

def add_product_to_db(data):
    conn = None
    try:
        conn = get_connection()
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
        return True
    except Exception as e:
        print(f"[ERROR] add_product_to_db: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def update_product_in_db(product_id, data):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products SET
                title = %(title)s, price = %(price)s, size = %(size)s,
                original_price = %(original_price)s, stock = %(stock)s,
                code = %(code)s, condition_rating = %(condition_rating)s,
                category = %(category)s, images = %(images)s
            WHERE product_id = %(product_id)s
        """, {**data, 'product_id': product_id})
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] update_product_in_db: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def delete_product_from_db(product_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] delete_product_from_db: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def search_products_db(query):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        q = f"%{query}%"
        cursor.execute(f"""
            SELECT {PRODUCT_COLUMNS} FROM products
            WHERE stock > 0 AND (title ILIKE %s OR brand ILIKE %s OR description ILIKE %s OR category ILIKE %s)
            ORDER BY created_at DESC
        """, (q, q, q, q))
        rows = cursor.fetchall()
        cursor.close()
        return [_row_to_product(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] search_products_db: {e}")
        return []
    finally:
        if conn:
            conn.close()

def filter_products_by_size_db(size):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {PRODUCT_COLUMNS} FROM products WHERE size = %s AND stock > 0 ORDER BY created_at DESC", (size,))
        rows = cursor.fetchall()
        cursor.close()
        return [_row_to_product(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] filter_products_by_size_db: {e}")
        return []
    finally:
        if conn:
            conn.close()

def filter_products_by_category_db(category):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {PRODUCT_COLUMNS} FROM products WHERE category = %s AND stock > 0 ORDER BY created_at DESC", (category,))
        rows = cursor.fetchall()
        cursor.close()
        return [_row_to_product(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] filter_products_by_category_db: {e}")
        return []
    finally:
        if conn:
            conn.close()

def filter_products_by_size_and_category_db(size, category):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {PRODUCT_COLUMNS} FROM products WHERE size = %s AND category = %s AND stock > 0 ORDER BY created_at DESC", (size, category))
        rows = cursor.fetchall()
        cursor.close()
        return [_row_to_product(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] filter_products_by_size_and_category_db: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_categories_db():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM products WHERE stock > 0 AND category IS NOT NULL AND category != '' ORDER BY category")
        rows = cursor.fetchall()
        cursor.close()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"[ERROR] get_all_categories_db: {e}")
        return []
    finally:
        if conn:
            conn.close()

def reduce_stock_db(product_id, quantity=1):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET stock = GREATEST(stock - %s, 0) WHERE product_id = %s", (quantity, product_id))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] reduce_stock_db: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# ==================== ORDERS TABLE ====================

def init_orders_table():
    conn = None
    try:
        conn = get_connection()
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] init_orders_table: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def _row_to_order(row):
    if not row:
        return None
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
        'referral_code': row[12] if len(row) > 12 else None
    }

def create_order(customer_name, phone_number, delivery_address, city,
                 product_id_or_name, quantity, total_price, notes=None, scheme='None', referral_code=None):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders
            (customer_name, phone_number, delivery_address, city,
             product_id_or_name, quantity, total_price, notes, status, order_date, scheme, referral_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s)
            RETURNING id
        """, (customer_name, phone_number, delivery_address, city,
              product_id_or_name, quantity, total_price, notes, datetime.utcnow(), scheme, referral_code))
        order_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        return order_id
    except Exception as e:
        print(f"[ERROR] create_order: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def get_order_by_id(order_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, customer_name, phone_number, delivery_address, city,
                   product_id_or_name, quantity, total_price, order_date,
                   status, notes, scheme, referral_code
            FROM orders WHERE id = %s
        """, (order_id,))
        row = cursor.fetchone()
        cursor.close()
        return _row_to_order(row)
    except Exception as e:
        print(f"[ERROR] get_order_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_orders(status=None):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if status:
            cursor.execute("""
                SELECT id, customer_name, phone_number, delivery_address, city,
                       product_id_or_name, quantity, total_price, order_date,
                       status, notes, scheme, referral_code
                FROM orders WHERE status = %s ORDER BY order_date DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT id, customer_name, phone_number, delivery_address, city,
                       product_id_or_name, quantity, total_price, order_date,
                       status, notes, scheme, referral_code
                FROM orders ORDER BY order_date DESC
            """)
        rows = cursor.fetchall()
        cursor.close()
        return [_row_to_order(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] get_all_orders: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_order_status(order_id, new_status):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] update_order_status: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# ==================== COMPLETED ORDERS TABLE ====================

def init_completed_orders_table():
    conn = None
    try:
        conn = get_connection()
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
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] init_completed_orders_table: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def mark_order_complete(order_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, customer_name, phone_number, delivery_address, city,
                   product_id_or_name, quantity, total_price, order_date, notes, scheme, referral_code
            FROM orders WHERE id = %s
        """, (order_id,))
        order = cursor.fetchone()
        if not order:
            return False
        cursor.execute("""
            INSERT INTO completed_orders
            (order_id, customer_name, phone_number, delivery_address, city,
             product_id_or_name, quantity, total_price, order_date, notes, scheme, referral_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, order)
        cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] mark_order_complete: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_completed_orders():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, order_id, customer_name, phone_number, delivery_address,
                   city, product_id_or_name, quantity, total_price, order_date,
                   completed_at, notes, scheme, referral_code
            FROM completed_orders ORDER BY completed_at DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        result = []
        for r in rows:
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
                'referral_code': r[13] if len(r) > 13 else None
            })
        return result
    except Exception as e:
        print(f"[ERROR] get_completed_orders: {e}")
        return []
    finally:
        if conn:
            conn.close()

from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'moiz_shoe_store_secret_2026'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database helper
def get_db():
    conn = sqlite3.connect('shoes.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database tables if they don't exist"""
    conn = get_db()
    cursor = conn.cursor()

    # Create products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            name TEXT,
            brand TEXT,
            description TEXT,
            price REAL NOT NULL,
            original_price REAL,
            size TEXT NOT NULL,
            condition TEXT,
            condition_rating REAL DEFAULT 9.0,
            color TEXT,
            category TEXT,
            location TEXT,
            code TEXT,
            image_url TEXT,
            stock INTEGER DEFAULT 1,
            featured INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_sale INTEGER DEFAULT 0,
            sale_end_time TEXT,
            bundle_pack TEXT,
            shipping_rule TEXT DEFAULT 'Standard Shipping Applies',
            imported_premium INTEGER DEFAULT 0
        )
    """)

    # Create orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            whatsapp TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)

    conn.commit()
    conn.close()
    print("[OK] Database initialized: shoes.db")

# ==================== ROUTES ====================

@app.route('/')
def home():
    """Home page - Display product catalog"""
    size = request.args.get('size')

    conn = get_db()
    cursor = conn.cursor()

    # Query products - map 'name' or 'title' column to work with templates
    query = """
        SELECT id,
               COALESCE(title, name) as title,
               COALESCE(name, title) as name,
               brand, price, original_price, size, stock, code,
               condition_rating, image_url, category, is_sale, sale_end_time
        FROM products
        WHERE stock > 0
    """

    if size:
        query += " AND size = ?"
        cursor.execute(query + " ORDER BY id DESC", (size,))
    else:
        cursor.execute(query + " ORDER BY id DESC")

    products = cursor.fetchall()
    conn.close()

    return render_template('index.html', products=products)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Product detail page"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id,
               COALESCE(title, name) as title,
               COALESCE(name, title) as name,
               brand, description, price, original_price, size, stock, code,
               condition, condition_rating, image_url, category, color,
               shipping_rule
        FROM products
        WHERE id = ?
    """, (product_id,))

    product = cursor.fetchone()

    if not product:
        conn.close()
        return render_template('404.html'), 404

    # Get related products
    cursor.execute("""
        SELECT id,
               COALESCE(title, name) as title,
               COALESCE(name, title) as name,
               price, image_url, size
        FROM products
        WHERE id != ? AND stock > 0
        LIMIT 4
    """, (product_id,))

    related_products = cursor.fetchall()
    conn.close()

    return render_template('product.html', product=product, related_products=related_products)


@app.route('/checkout/<int:product_id>', methods=['GET', 'POST'])
def checkout(product_id):
    """Checkout page - COD order form"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id,
               COALESCE(title, name) as title,
               COALESCE(name, title) as name,
               price, stock, image_url, size, condition
        FROM products
        WHERE id = ?
    """, (product_id,))

    product = cursor.fetchone()

    if not product:
        conn.close()
        return render_template('404.html'), 404

    if product['stock'] < 1:
        flash('Sorry, this product is out of stock.', 'error')
        conn.close()
        return redirect(url_for('product_detail', product_id=product_id))

    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        whatsapp = request.form.get('whatsapp', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        notes = request.form.get('notes', '').strip()

        if not all([customer_name, whatsapp, address, city]):
            flash('Please fill in all required fields.', 'error')
            conn.close()
            return render_template('checkout.html', product=product)

        try:
            # Create order
            cursor.execute("""
                INSERT INTO orders (product_id, customer_name, whatsapp, address, city, notes, status, order_date)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (product_id, customer_name, whatsapp, address, city, notes, datetime.utcnow()))

            order_id = cursor.lastrowid

            # Reduce stock
            cursor.execute("UPDATE products SET stock = stock - 1 WHERE id = ?", (product_id,))

            conn.commit()
            conn.close()

            flash(f'Order placed successfully! Order ID: {order_id}', 'success')
            return redirect(url_for('order_confirmation', order_id=order_id))

        except Exception as e:
            conn.rollback()
            conn.close()
            flash('An error occurred. Please try again.', 'error')
            print(f"Error: {e}")
            return render_template('checkout.html', product=product)

    conn.close()
    return render_template('checkout.html', product=product)


@app.route('/order-confirmation/<int:order_id>')
def order_confirmation(order_id):
    """Order confirmation page"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.*,
               COALESCE(p.title, p.name) as product_name,
               p.price, p.brand, p.size, p.condition
        FROM orders o
        LEFT JOIN products p ON o.product_id = p.id
        WHERE o.id = ?
    """, (order_id,))

    order = cursor.fetchone()
    conn.close()

    if not order:
        return render_template('404.html'), 404

    return render_template('order_confirmation.html', order=order)


@app.route('/search')
def search():
    """Search products"""
    query = request.args.get('q', '').strip()

    if not query:
        return redirect(url_for('home'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id,
               COALESCE(title, name) as title,
               COALESCE(name, title) as name,
               brand, price, image_url, size, stock
        FROM products
        WHERE (COALESCE(title, name) LIKE ? OR brand LIKE ? OR description LIKE ?)
        AND stock > 0
    """, (f'%{query}%', f'%{query}%', f'%{query}%'))

    products = cursor.fetchall()
    conn.close()

    return render_template('search_results.html', products=products, query=query)


# ==================== MOIZ ADMIN ====================

@app.route('/moiz-admin/login', methods=['GET', 'POST'])
def moiz_admin_login():
    """Moiz Admin Login"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if email == 'moizshabbir2248@gmail.com' and password == 'abdulmoiz217@':
            session['logged_in'] = True
            return redirect(url_for('moiz_admin'))
        else:
            flash('Invalid credentials. Please try again.', 'error')

    return render_template('moiz_admin_login.html')


@app.route('/moiz-admin/logout')
def moiz_admin_logout():
    """Moiz Admin Logout"""
    session.pop('logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('moiz_admin_login'))


@app.route('/moiz-admin', methods=['GET', 'POST'])
def moiz_admin():
    """Moiz Admin Dashboard - Protected"""
    if not session.get('logged_in'):
        return redirect(url_for('moiz_admin_login'))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_product':
            try:
                # Handle image upload or URL
                image_path = None
                if 'image_file' in request.files:
                    file = request.files['image_file']
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        # Add timestamp to avoid conflicts
                        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        image_path = f"/static/uploads/{filename}"

                # If no file uploaded, use URL from text input
                if not image_path:
                    image_path = request.form.get('image_url') or None

                cursor.execute("""
                    INSERT INTO products (title, size, price, original_price, code, condition_rating,
                                        image_url, shipping_rule, is_sale, sale_end_time, bundle_pack,
                                        imported_premium, stock)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    request.form.get('title'),
                    request.form.get('size'),
                    request.form.get('price'),
                    request.form.get('original_price') or None,
                    request.form.get('code', '').strip() or None,
                    request.form.get('condition_rating', 9.0),
                    image_path,
                    'Free Shipping' if request.form.get('free_shipping') else 'Standard Shipping Applies',
                    1 if request.form.get('is_sale') else 0,
                    request.form.get('sale_end_time') or None,
                    request.form.get('bundle_pack') or None,
                    1 if request.form.get('imported_premium') else 0
                ))
                conn.commit()
                flash('Product added successfully!', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Error adding product: {e}', 'error')

        elif action == 'delete_product':
            try:
                product_id = request.form.get('product_id')
                cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
                conn.commit()
                flash('Product deleted successfully!', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Error deleting product: {e}', 'error')

        elif action == 'edit_product':
            try:
                cursor.execute("""
                    UPDATE products
                    SET title = ?, size = ?, price = ?, original_price = ?,
                        code = ?, condition_rating = ?, stock = ?
                    WHERE id = ?
                """, (
                    request.form.get('title'),
                    request.form.get('size'),
                    request.form.get('price'),
                    request.form.get('original_price') or None,
                    request.form.get('code', '').strip() or None,
                    request.form.get('condition_rating', 9.0),
                    request.form.get('stock', 1),
                    request.form.get('product_id')
                ))
                conn.commit()
                flash('Product updated successfully!', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Error updating product: {e}', 'error')

        conn.close()
        return redirect(url_for('moiz_admin'))

    # GET request - fetch data
    cursor.execute("""
        SELECT o.*, COALESCE(p.title, p.name) as product_title
        FROM orders o
        LEFT JOIN products p ON o.product_id = p.id
        WHERE o.status = 'pending'
        ORDER BY o.order_date DESC
    """)
    orders = cursor.fetchall()

    cursor.execute("""
        SELECT id, COALESCE(title, name) as title, size, price, original_price,
               code, stock, image_url, shipping_rule
        FROM products
        ORDER BY id DESC
    """)
    products = cursor.fetchall()

    conn.close()
    return render_template('moiz_admin.html', orders=orders, products=products)


@app.route('/moiz-admin-orders')
def moiz_admin_orders():
    """Orders dashboard - Protected"""
    if not session.get('logged_in'):
        return redirect(url_for('moiz_admin_login'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.id, o.customer_name, o.whatsapp, o.address, o.city,
               o.status, o.order_date,
               COALESCE(p.title, p.name) as product_title
        FROM orders o
        LEFT JOIN products p ON o.product_id = p.id
        ORDER BY o.order_date DESC
    """)

    orders = cursor.fetchall()
    conn.close()

    return render_template('orders_dashboard.html', orders=orders)


# ==================== CONTEXT PROCESSOR ====================

@app.context_processor
def utility_processor():
    """Make utility functions available in templates"""
    def format_datetime(dt):
        if dt:
            if isinstance(dt, str):
                try:
                    dt = datetime.fromisoformat(dt)
                except:
                    return dt
            return dt.strftime('%B %d, %Y at %I:%M %p')
        return ''
    return dict(format_datetime=format_datetime)


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500


# ==================== RUN APPLICATION ====================

if __name__ == '__main__':
    # Initialize database on startup
    init_database()

    print("\n" + "="*50)
    print("Shoes E-commerce Application Starting...")
    print("="*50)
    print("Access: http://127.0.0.1:5000")
    print("Admin Login: http://127.0.0.1:5000/moiz-admin/login")
    print("Email: moizshabbir2248@gmail.com")
    print("Using: sqlite3 (no SQLAlchemy)")
    print("="*50 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)

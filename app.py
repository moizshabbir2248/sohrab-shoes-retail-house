from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv()

from db_config import (
    init_connection_pool, close_all_connections,

    init_products_table, get_all_products_db, get_product_by_id_db,
    add_product_to_db, update_product_in_db, delete_product_from_db,
    search_products_db, filter_products_by_size_db, reduce_stock_db,
    filter_products_by_category_db, filter_products_by_size_and_category_db,
    get_all_categories_db,

    init_orders_table, create_order, get_order_by_id, get_all_orders,
    update_order_status,

    init_completed_orders_table, mark_order_complete, get_completed_orders,

    init_referral_codes_table, validate_referral_code, add_referral_code,
    delete_referral_code, get_all_referral_codes, toggle_referral_code
)

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'moiz_shoe_store_secret_2026')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'mov', 'avi', 'heic'}
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'moizshabbir2248@gmail.com')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'abdulmoiz217@')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_to_cloudinary(file):
    try:
        result = cloudinary.uploader.upload(
            file,
            folder="products",
            resource_type="auto"
        )
        return result.get('secure_url')
    except Exception as e:
        print(f"[ERROR] Cloudinary upload failed: {e}")
        return None


# ==================== ROUTES ====================

@app.route('/')
def home():
    size = request.args.get('size')
    category = request.args.get('category')

    if size and category:
        products = filter_products_by_size_and_category_db(size, category)
    elif size:
        products = filter_products_by_size_db(size)
    elif category:
        products = filter_products_by_category_db(category)
    else:
        products = get_all_products_db()

    categories = get_all_categories_db()
    all_categories = ['Shoes', 'Ladies Suits', 'Watches', 'Jewelry', 'Chappal']

    return render_template('index.html', products=products, categories=categories, all_categories=all_categories)


@app.route('/product/<product_id>')
def product_detail(product_id):
    product = get_product_by_id_db(product_id)

    if not product:
        return render_template('404.html'), 404

    all_products = get_all_products_db()
    related_products = [p for p in all_products if p['id'] != product_id][:4]

    return render_template('product.html', product=product, related_products=related_products)


@app.route('/checkout/<product_id>', methods=['GET', 'POST'])
def checkout(product_id):
    product = get_product_by_id_db(product_id)

    if not product:
        return render_template('404.html'), 404

    if product.get('stock', 0) < 1:
        flash('Sorry, this product is out of stock.', 'error')
        return redirect(url_for('product_detail', product_id=product_id))

    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        whatsapp = request.form.get('whatsapp', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        notes = request.form.get('notes', '').strip()
        quantity = int(request.form.get('quantity', 1))
        scheme = request.form.get('scheme', 'None')
        referral_code_input = request.form.get('referral_code', '').strip()

        if not all([customer_name, whatsapp, address, city]):
            flash('Please fill in all required fields.', 'error')
            return render_template('checkout.html', product=product)

        total_price = product['price'] * quantity
        discount = 0
        applied_referral = None

        if referral_code_input:
            if validate_referral_code(referral_code_input):
                discount = 200
                applied_referral = referral_code_input.upper()
                total_price = max(total_price - 200, 0)
            else:
                flash('Invalid or inactive coupon code. No discount applied.', 'error')
                return render_template('checkout.html', product=product)

        product_identifier = f"{product['id']} - {product['title']}"

        try:
            order_id = create_order(
                customer_name=customer_name,
                phone_number=whatsapp,
                delivery_address=address,
                city=city,
                product_id_or_name=product_identifier,
                quantity=quantity,
                total_price=total_price,
                notes=notes,
                scheme=scheme,
                referral_code=applied_referral
            )

            if order_id:
                reduce_stock_db(product_id, quantity)
                if discount > 0:
                    flash(f'Order placed! Rs {discount} discount applied. Order ID: {order_id}', 'success')
                else:
                    flash(f'Order placed successfully! Order ID: {order_id}', 'success')
                return redirect(url_for('order_confirmation', order_id=order_id))
            else:
                flash('An error occurred. Please try again.', 'error')
                return render_template('checkout.html', product=product)

        except Exception as e:
            flash('An error occurred. Please try again.', 'error')
            print(f"Error: {e}")
            return render_template('checkout.html', product=product)

    return render_template('checkout.html', product=product)


@app.route('/order-confirmation/<int:order_id>')
def order_confirmation(order_id):
    order = get_order_by_id(order_id)

    if not order:
        return render_template('404.html'), 404

    product_id = order['product_id_or_name'].split(' - ')[0] if ' - ' in order['product_id_or_name'] else None
    product = get_product_by_id_db(product_id) if product_id else None

    return render_template('order_confirmation.html', order=order, product=product)


@app.route('/search')
def search():
    query = request.args.get('q', '').strip()

    if not query:
        return redirect(url_for('home'))

    products = search_products_db(query)

    return render_template('search_results.html', products=products, query=query)


# ==================== MOIZ ADMIN ====================

@app.route('/moiz-admin/login', methods=['GET', 'POST'])
def moiz_admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('moiz_admin'))
        else:
            flash('Invalid credentials. Please try again.', 'error')

    return render_template('moiz_admin_login.html')


@app.route('/moiz-admin/logout')
def moiz_admin_logout():
    session.pop('logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('moiz_admin_login'))


@app.route('/moiz-admin', methods=['GET', 'POST'])
def moiz_admin():
    if not session.get('logged_in'):
        return redirect(url_for('moiz_admin_login'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_product':
            try:
                product_id = request.form.get('product_id', '').strip()
                title = request.form.get('title', '').strip()
                size = request.form.get('size', '').strip()
                price = float(request.form.get('price', 0))
                original_price = request.form.get('original_price', '').strip()
                code = request.form.get('code', '').strip()
                condition_rating = float(request.form.get('condition_rating', 9.0))
                stock = int(request.form.get('stock', 1))
                category = request.form.get('category', '').strip() or None

                files = request.files.getlist('image_files')
                valid_files = [f for f in files if f and f.filename and allowed_file(f.filename)]

                if not valid_files:
                    flash('Please select at least one product photo to upload.', 'error')
                    return redirect(url_for('moiz_admin'))

                images = []
                for f in valid_files[:5]:
                    url = upload_to_cloudinary(f)
                    if url:
                        images.append(url)

                if not images:
                    flash('Failed to upload images. Please try again.', 'error')
                    return redirect(url_for('moiz_admin'))

                data = {
                    'product_id': product_id,
                    'title': title,
                    'price': price,
                    'size': size,
                    'image_url': images[0],
                    'original_price': float(original_price) if original_price else None,
                    'stock': stock,
                    'code': code or None,
                    'condition_rating': condition_rating,
                    'is_sale': 1 if request.form.get('is_sale') else 0,
                    'sale_end_time': request.form.get('sale_end_time') or None,
                    'shipping_rule': 'Free Shipping' if request.form.get('free_shipping') else 'Standard Shipping Applies',
                    'imported_premium': 1 if request.form.get('imported_premium') else 0,
                    'brand': None,
                    'description': None,
                    'color': None,
                    'category': category,
                    'condition': None,
                    'images': json.dumps(images)
                }

                if add_product_to_db(data):
                    flash(f'Product {product_id} added with {len(images)} image(s)!', 'success')
                else:
                    flash('Error adding product to database.', 'error')

            except Exception as e:
                flash(f'Error adding product: {e}', 'error')

        elif action == 'edit_product':
            try:
                product_id = request.form.get('product_id', '').strip()
                existing = get_product_by_id_db(product_id)
                existing_images = json.dumps(existing.get('images', [])) if existing else '[]'

                new_files = request.files.getlist('image_files')
                valid_new_files = [f for f in new_files if f and f.filename and allowed_file(f.filename)]

                if valid_new_files:
                    images = []
                    for f in valid_new_files[:5]:
                        url = upload_to_cloudinary(f)
                        if url:
                            images.append(url)
                    if images:
                        existing_images = json.dumps(images)

                data = {
                    'title': request.form.get('title', '').strip(),
                    'size': request.form.get('size', '').strip(),
                    'price': float(request.form.get('price', 0)),
                    'original_price': float(request.form.get('original_price', 0)) if request.form.get('original_price') else None,
                    'code': request.form.get('code', '').strip() or None,
                    'condition_rating': float(request.form.get('condition_rating', 9.0)),
                    'stock': int(request.form.get('stock', 0)),
                    'category': request.form.get('category', '').strip() or None,
                    'images': existing_images
                }
                if update_product_in_db(product_id, data):
                    flash('Product updated successfully!', 'success')
                else:
                    flash('Failed to update product.', 'error')
            except Exception as e:
                flash(f'Error updating product: {e}', 'error')

        elif action == 'delete_product':
            try:
                product_id = request.form.get('product_id', '').strip()
                if delete_product_from_db(product_id):
                    flash('Product deleted successfully!', 'success')
                else:
                    flash('Failed to delete product.', 'error')
            except Exception as e:
                flash(f'Error deleting product: {e}', 'error')

        elif action == 'mark_complete':
            try:
                order_id = request.form.get('order_id')
                if mark_order_complete(order_id):
                    flash('Order marked as complete and moved to history!', 'success')
                else:
                    flash('Failed to mark order complete.', 'error')
            except Exception as e:
                flash(f'Error: {e}', 'error')

        elif action == 'update_order_status':
            try:
                order_id = request.form.get('order_id')
                new_status = request.form.get('status')
                if update_order_status(order_id, new_status):
                    flash('Order status updated successfully!', 'success')
                else:
                    flash('Failed to update order status.', 'error')
            except Exception as e:
                flash(f'Error updating order: {e}', 'error')

        elif action == 'add_referral_code':
            try:
                code = request.form.get('referral_code', '').strip()
                if not code:
                    flash('Please enter a code.', 'error')
                elif add_referral_code(code):
                    flash(f'Code "{code.upper()}" added successfully!', 'success')
                else:
                    flash('Failed to add code. It may already exist.', 'error')
            except Exception as e:
                flash(f'Error adding code: {e}', 'error')

        elif action == 'delete_referral_code':
            try:
                code_id = request.form.get('code_id')
                if delete_referral_code(code_id):
                    flash('Code deleted successfully!', 'success')
                else:
                    flash('Failed to delete code.', 'error')
            except Exception as e:
                flash(f'Error deleting code: {e}', 'error')

        elif action == 'toggle_referral_code':
            try:
                code_id = request.form.get('code_id')
                if toggle_referral_code(code_id):
                    flash('Code status toggled!', 'success')
                else:
                    flash('Failed to toggle code.', 'error')
            except Exception as e:
                flash(f'Error toggling code: {e}', 'error')

        return redirect(url_for('moiz_admin'))

    orders = get_all_orders()
    products = get_all_products_db()
    completed_orders = get_completed_orders()
    referral_codes = get_all_referral_codes()

    return render_template('moiz_admin.html', orders=orders, products=products, completed_orders=completed_orders, referral_codes=referral_codes)


# ==================== CONTEXT PROCESSOR ====================

@app.context_processor
def utility_processor():
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
    print("\n" + "="*60)
    print("Shoes E-commerce Application Starting...")
    print("="*60)

    print("Connecting to Neon DB (PostgreSQL)...")
    if init_connection_pool():
        print("[OK] Connection pool initialized")
    else:
        print("[ERROR] Failed to initialize connection pool")
        exit(1)

    print("Setting up products table...")
    init_products_table()

    print("Setting up orders table...")
    init_orders_table()

    print("Setting up completed_orders table...")
    init_completed_orders_table()

    print("Setting up referral_codes table...")
    init_referral_codes_table()

    print("\n" + "="*60)
    print("[OK] Database: Neon DB (PostgreSQL) - All tables")
    print("[OK] Cloudinary: Configured for image/video uploads")
    print("[OK] Products: Stored in Neon DB (media on Cloudinary)")
    print("[OK] Orders: Stored in Neon DB")
    print("[OK] Completed Orders: Stored in Neon DB")
    print("[OK] Referral Codes: Stored in Neon DB")
    print("="*60)
    print("\nAccess URLs:")
    print("   Main Site: http://127.0.0.1:5000")
    print("   Admin Panel: http://127.0.0.1:5000/moiz-admin/login")
    print("   Email: moizshabbir2248@gmail.com")
    print("="*60 + "\n")

    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        print("\nClosing database connections...")
        close_all_connections()
        print("[OK] Application shut down cleanly\n")

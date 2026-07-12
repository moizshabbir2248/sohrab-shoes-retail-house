from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import os
import json
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

from db_config import (
    init_connection_pool, close_all_connections,

    init_products_table, get_all_products_db, get_product_by_id_db,
    add_product_to_db, update_product_in_db, delete_product_from_db,
    search_products_db, reduce_stock_db,
    filter_products_by_category_db,
    get_all_categories_db,

    init_orders_table, create_order, get_order_by_id, get_all_orders,
    update_order_status,

    init_completed_orders_table, mark_order_complete, get_completed_orders,

    init_referral_codes_table, validate_referral_code, add_referral_code,
    delete_referral_code, get_all_referral_codes, toggle_referral_code,
    has_customer_used_referral_code,

    init_reservations_table, create_reservation, get_active_reservation,
    release_reservation, get_reserved_product_ids, cleanup_expired_reservations,

    calculate_totals, SHIPPING_FEE
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

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

def validate_csrf():
    token = request.form.get('_csrf_token')
    if not token or token != session.get('_csrf_token'):
        return False
    return True

def get_session_id():
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(16)
    return session['session_id']

def upload_to_cloudinary(file):
    try:
        if not file or not file.filename:
            return None, 'No file selected'
        if not allowed_file(file.filename):
            return None, f'File type not allowed: {file.filename}'
        result = cloudinary.uploader.upload(
            file,
            folder="products",
            resource_type="auto"
        )
        url = result.get('secure_url')
        if not url:
            return None, 'Cloudinary did not return a URL'
        return url, None
    except Exception as e:
        error_msg = f'Cloudinary upload failed for "{file.filename if file else "unknown"}": {str(e)}'
        print(f"[ERROR] {error_msg}")
        return None, error_msg


# ==================== ROUTES ====================

@app.route('/')
def home():
    category = request.args.get('category')

    if category:
        products = filter_products_by_category_db(category)
    else:
        products = get_all_products_db()

    categories = get_all_categories_db()
    all_categories = ['Shoes', 'Ladies Suits', 'Watches', 'Jewelry', 'Chappal']
    reserved_ids = get_reserved_product_ids()

    return render_template('index.html', products=products, categories=categories, all_categories=all_categories, reserved_ids=reserved_ids)


@app.route('/product/<product_id>')
def product_detail(product_id):
    product = get_product_by_id_db(product_id)

    if not product:
        return render_template('404.html'), 404

    all_products = get_all_products_db()
    related_products = [p for p in all_products if p['id'] != product_id][:4]

    reservation = get_active_reservation(product_id)
    is_reserved = reservation is not None
    is_mine = reservation and reservation['session_id'] == get_session_id() if reservation else False

    return render_template('product.html', product=product, related_products=related_products, is_reserved=is_reserved, is_mine=is_mine)


@app.route('/checkout/<product_id>', methods=['GET', 'POST'])
def checkout(product_id):
    product = get_product_by_id_db(product_id)

    if not product:
        return render_template('404.html'), 404

    if product.get('stock', 0) < 1:
        flash('Sorry, this product is out of stock.', 'error')
        return redirect(url_for('product_detail', product_id=product_id))

    sid = get_session_id()

    if request.method == 'GET':
        reservation = get_active_reservation(product_id)
        if reservation and reservation['session_id'] != sid:
            flash('This product is temporarily reserved by another customer. Please try again in a few minutes.', 'error')
            return redirect(url_for('product_detail', product_id=product_id))
        if not reservation or reservation['session_id'] != sid:
            ok, msg = create_reservation(product_id, sid)
            if not ok:
                flash(f'Could not reserve product: {msg}', 'error')
                return redirect(url_for('product_detail', product_id=product_id))
        return render_template('checkout.html', product=product)

    if not validate_csrf():
        flash('Session expired. Please try again.', 'error')
        return redirect(url_for('product_detail', product_id=product_id))

    reservation = get_active_reservation(product_id)
    if reservation and reservation['session_id'] != sid:
        flash('This product was reserved by another customer while you were checking out.', 'error')
        return redirect(url_for('product_detail', product_id=product_id))

    customer_name = request.form.get('customer_name', '').strip()
    whatsapp = request.form.get('whatsapp', '').strip()
    address = request.form.get('address', '').strip()
    city = request.form.get('city', '').strip()
    notes = request.form.get('notes', '').strip()
    quantity = int(request.form.get('quantity', 1))
    referral_code_input = request.form.get('referral_code', '').strip()

    if not all([customer_name, whatsapp, address, city]):
        flash('Please fill in all required fields.', 'error')
        return render_template('checkout.html', product=product)

    total_price = product['price'] * quantity
    discount = 0
    applied_referral = None

    if referral_code_input:
        if validate_referral_code(referral_code_input):
            try:
                if has_customer_used_referral_code(whatsapp, referral_code_input):
                    flash('This coupon has already been used by this phone number. One-time use only.', 'error')
                    return render_template('checkout.html', product=product)
            except Exception as e:
                print(f"[ERROR] Referral usage check failed: {e}")
                flash('Could not verify coupon. Please try again.', 'error')
                return render_template('checkout.html', product=product)
            discount = 200
            applied_referral = referral_code_input.upper()
            total_price = max(total_price - 200, 0)
        else:
            flash('Invalid or inactive coupon code. No discount applied.', 'error')
            return render_template('checkout.html', product=product)

    shipping = 0 if city.lower() == 'karachi' else 500
    total_price += shipping

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
            referral_code=applied_referral,
            product_description=product.get('description')
        )

        if order_id:
            release_reservation(product_id, sid)
            reduce_stock_db(product_id, quantity)
            msg_parts = []
            if discount > 0:
                msg_parts.append(f'Rs {discount} discount applied')
            if shipping > 0:
                msg_parts.append(f'Rs {shipping} shipping')
            summary = f' ({", ".join(msg_parts)})' if msg_parts else ''
            flash(f'Order placed successfully!{summary} Order ID: {order_id}', 'success')
            return redirect(url_for('order_confirmation', order_id=order_id))
        else:
            flash('An error occurred. Please try again.', 'error')
            return render_template('checkout.html', product=product)

    except Exception as e:
        flash('An error occurred. Please try again.', 'error')
        print(f"Error: {e}")
        return render_template('checkout.html', product=product)


@app.route('/order-confirmation/<int:order_id>')
def order_confirmation(order_id):
    order = get_order_by_id(order_id)

    if not order:
        return render_template('404.html'), 404

    product_id = order['product_id_or_name'].split(' - ')[0] if ' - ' in order['product_id_or_name'] else None
    product = get_product_by_id_db(product_id) if product_id else None

    return render_template('order_confirmation.html', order=order, product=product)


@app.route('/validate-referral', methods=['POST'])
def validate_referral():
    data = request.get_json(silent=True)
    print(f"[REFERRAL] Raw request JSON: {data}")

    if not data:
        print("[REFERRAL] ERROR: No JSON body received")
        return jsonify({'success': False, 'message': 'Invalid request.'})

    raw_code = data.get('code', '')
    code = raw_code.strip().upper()
    print(f"[REFERRAL] Raw code: '{raw_code}' → Normalized: '{code}'")

    if not code:
        print("[REFERRAL] ERROR: Empty code")
        return jsonify({'success': False, 'message': 'Please enter a code.'})

    try:
        result = validate_referral_code(code)
        print(f"[REFERRAL] DB result for '{code}': {result}")
    except Exception as e:
        print(f"[REFERRAL] ERROR: DB exception: {e}")
        return jsonify({'success': False, 'message': 'Database error. Please try again.'})

    if result:
        print(f"[REFERRAL] SUCCESS: Code '{code}' valid, discount: 200")
        return jsonify({
            'success': True,
            'discount_amount': 200,
            'message': f'Code applied! Rs 200 discount.'
        })
    else:
        print(f"[REFERRAL] FAILED: Code '{code}' not found or inactive")
        return jsonify({'success': False, 'message': 'Invalid or inactive code.'})


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
        if not validate_csrf():
            flash('Session expired. Please try again.', 'error')
            return render_template('moiz_admin_login.html')
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
        if not validate_csrf():
            flash('Session expired. Please try again.', 'error')
            return redirect(url_for('moiz_admin'))
        action = request.form.get('action')

        if action == 'add_product':
            try:
                product_id = request.form.get('product_id', '').strip()
                title = request.form.get('title', '').strip()
                price = float(request.form.get('price', 0))
                original_price = request.form.get('original_price', '').strip()
                code = request.form.get('code', '').strip()
                condition_rating = float(request.form.get('condition_rating', 9.0))
                stock = int(request.form.get('stock', 1))
                category = request.form.get('category', '').strip() or None
                description = request.form.get('description', '').strip() or None

                files = request.files.getlist('image_files')
                valid_files = [f for f in files if f and f.filename and allowed_file(f.filename)]

                if not valid_files:
                    flash('Please select at least one product photo to upload.', 'error')
                    return redirect(url_for('moiz_admin'))

                images = []
                upload_errors = []
                for f in valid_files[:5]:
                    url, error = upload_to_cloudinary(f)
                    if url:
                        images.append(url)
                    else:
                        upload_errors.append(error)

                if not images:
                    error_detail = '; '.join(upload_errors) if upload_errors else 'Unknown error'
                    flash(f'Failed to upload images: {error_detail}', 'error')
                    return redirect(url_for('moiz_admin'))

                data = {
                    'product_id': product_id,
                    'title': title,
                    'price': price,
                    'size': '',
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
                    'description': description,
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
                        url, error = upload_to_cloudinary(f)
                        if url:
                            images.append(url)
                    if images:
                        existing_images = json.dumps(images)

                data = {
                    'title': request.form.get('title', '').strip(),
                    'size': '',
                    'price': float(request.form.get('price', 0)),
                    'original_price': float(request.form.get('original_price', 0)) if request.form.get('original_price') else None,
                    'code': request.form.get('code', '').strip() or None,
                    'condition_rating': float(request.form.get('condition_rating', 9.0)),
                    'stock': int(request.form.get('stock', 0)),
                    'category': request.form.get('category', '').strip() or None,
                    'description': request.form.get('description', '').strip() or None,
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


@app.route('/admin/cleanup-reservations')
def cleanup_reservations():
    deleted = cleanup_expired_reservations()
    flash(f'Cleaned up {deleted} expired reservation(s).', 'success')
    return redirect(url_for('moiz_admin'))


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
    return dict(format_datetime=format_datetime, csrf_token=generate_csrf_token)


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500


# ==================== CART ====================

@app.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    summary = calculate_totals(cart)
    return render_template('cart.html', summary=summary)

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    data = request.get_json(silent=True) or {}
    product_id = data.get('product_id', '').strip()
    quantity = int(data.get('quantity', 1))

    if not product_id:
        return jsonify({'success': False, 'message': 'No product specified.'})

    product = get_product_by_id_db(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found.'})

    if product.get('stock', 0) <= 0:
        return jsonify({'success': False, 'message': 'Product is out of stock.'})

    cart = session.get('cart', [])

    for item in cart:
        if item['product_id'] == product_id:
            new_qty = min(item['quantity'] + quantity, product['stock'])
            item['quantity'] = new_qty
            session['cart'] = cart
            summary = calculate_totals(cart)
            return jsonify({'success': True, 'message': 'Cart updated.', 'cart_summary': summary})

    qty = min(quantity, product['stock'])
    cart.append({'product_id': product_id, 'quantity': qty})
    session['cart'] = cart
    summary = calculate_totals(cart)
    return jsonify({'success': True, 'message': 'Added to cart.', 'cart_summary': summary})

@app.route('/update-cart', methods=['POST'])
def update_cart():
    data = request.get_json(silent=True) or {}
    product_id = data.get('product_id', '').strip()
    quantity = int(data.get('quantity', 1))

    if not product_id:
        return jsonify({'success': False, 'message': 'No product specified.'})

    cart = session.get('cart', [])

    if quantity <= 0:
        cart = [item for item in cart if item['product_id'] != product_id]
    else:
        product = get_product_by_id_db(product_id)
        max_qty = product['stock'] if product else quantity
        for item in cart:
            if item['product_id'] == product_id:
                item['quantity'] = min(quantity, max_qty)
                break

    session['cart'] = cart
    summary = calculate_totals(cart)
    return jsonify({'success': True, 'message': 'Cart updated.', 'cart_summary': summary})

@app.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    data = request.get_json(silent=True) or {}
    product_id = data.get('product_id', '').strip()

    cart = session.get('cart', [])
    cart = [item for item in cart if item['product_id'] != product_id]
    session['cart'] = cart
    summary = calculate_totals(cart)
    return jsonify({'success': True, 'message': 'Removed from cart.', 'cart_summary': summary})

@app.route('/get-cart-summary')
def get_cart_summary():
    cart = session.get('cart', [])
    city = request.args.get('city', '').strip()
    summary = calculate_totals(cart, city=city if city else None)
    return jsonify(summary)

@app.route('/clear-cart', methods=['POST'])
def clear_cart():
    session.pop('cart', None)
    return jsonify({'success': True, 'message': 'Cart cleared.'})

@app.route('/checkout-cart', methods=['GET', 'POST'])
def checkout_cart():
    cart = session.get('cart', [])
    if not cart:
        flash('Your cart is empty.', 'error')
        return redirect(url_for('home'))

    summary = calculate_totals(cart)

    if request.method == 'POST':
        if not validate_csrf():
            flash('Session expired. Please try again.', 'error')
            return render_template('cart_checkout.html', summary=summary)

        customer_name = request.form.get('customer_name', '').strip()
        whatsapp = request.form.get('whatsapp', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        notes = request.form.get('notes', '').strip()
        referral_code_input = request.form.get('referral_code', '').strip()

        if not all([customer_name, whatsapp, address, city]):
            flash('Please fill in all required fields.', 'error')
            return render_template('cart_checkout.html', summary=summary)

        fresh_summary = calculate_totals(cart, city=city)
        if not fresh_summary['cart_items']:
            flash('Your cart is empty or items are out of stock.', 'error')
            return redirect(url_for('view_cart'))

        discount = 0
        applied_referral = None

        if referral_code_input:
            if validate_referral_code(referral_code_input):
                try:
                    if has_customer_used_referral_code(whatsapp, referral_code_input):
                        flash('This coupon has already been used by this phone number.', 'error')
                        return render_template('cart_checkout.html', summary=fresh_summary)
                except Exception as e:
                    print(f"[ERROR] Referral usage check failed: {e}")
                    flash('Could not verify coupon. Please try again.', 'error')
                    return render_template('cart_checkout.html', summary=fresh_summary)
                discount = 200
                applied_referral = referral_code_input.upper()
            else:
                flash('Invalid or inactive coupon code. No discount applied.', 'error')
                return render_template('cart_checkout.html', summary=fresh_summary)

        order_ids = []
        for item in fresh_summary['cart_items']:
            product = get_product_by_id_db(item['product_id'])
            if not product or product.get('stock', 0) < item['quantity']:
                flash(f'"{item["name"]}" is no longer available in requested quantity.', 'error')
                return render_template('cart_checkout.html', summary=fresh_summary)

            item_discount = discount // len(fresh_summary['cart_items']) if discount else 0
            item_total = max(item['line_total'] - item_discount, 0)
            if item == fresh_summary['cart_items'][-1]:
                item_total += discount - (item_discount * (len(fresh_summary['cart_items']) - 1))

            product_identifier = f"{product['id']} - {product['title']}"

            order_id = create_order(
                customer_name=customer_name,
                phone_number=whatsapp,
                delivery_address=address,
                city=city,
                product_id_or_name=product_identifier,
                quantity=item['quantity'],
                total_price=round(item_total, 2),
                notes=notes,
                referral_code=applied_referral,
                product_description=product.get('description')
            )

            if order_id:
                reduce_stock_db(product['id'], item['quantity'])
                order_ids.append(order_id)

        session.pop('cart', None)

        if order_ids:
            flash(f'{len(order_ids)} order(s) placed successfully! Total: Rs {fresh_summary["total"]}', 'success')
            return redirect(url_for('order_confirmation', order_id=order_ids[0]))
        else:
            flash('Failed to place orders. Please try again.', 'error')
            return render_template('cart_checkout.html', summary=fresh_summary)

    return render_template('cart_checkout.html', summary=summary)


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

    print("Setting up reservations table...")
    init_reservations_table()

    print("\n" + "="*60)
    print("[OK] Database: Neon DB (PostgreSQL) - All tables")
    print("[OK] Cloudinary: Configured for image/video uploads")
    print("[OK] Products: Stored in Neon DB (media on Cloudinary)")
    print("[OK] Orders: Stored in Neon DB")
    print("[OK] Completed Orders: Stored in Neon DB")
    print("[OK] Referral Codes: Stored in Neon DB")
    print("[OK] Reservations: Temporary product holds (10 min expiry)")
    print("[OK] CSRF Protection: Enabled for all POST forms")
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

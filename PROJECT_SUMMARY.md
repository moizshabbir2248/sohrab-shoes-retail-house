# FOOTWEAR E-COMMERCE PROJECT - TECHNICAL SUMMARY
**Date:** June 26, 2026  
**Database:** SQLite3 (shoes.db)  
**Framework:** Flask (Python)  
**Admin:** Moiz (moizshabbir2248@gmail.com)

---

## 1. DATABASE & SCHEMA

### Tables Overview:
- **products** (23 columns)
- **orders** (9 columns)

### PRODUCTS TABLE Schema:
```
id                  INTEGER PRIMARY KEY AUTOINCREMENT
title               TEXT NOT NULL              # Product display name
name                TEXT NULL                  # Legacy field (COALESCE with title)
brand               TEXT NULL
description         TEXT NULL
price               REAL NOT NULL              # Sale/current price
original_price      REAL NULL                  # For discount calculation
size                TEXT NOT NULL              # Shoe size
condition           TEXT NULL
condition_rating    REAL DEFAULT 9.0           # 1-10 scale
color               TEXT NULL
category            TEXT NULL
location            TEXT NULL
code                TEXT NULL                  # Warehouse location (SHERSHAH/BHORA)
image_url           TEXT NULL                  # Image path or URL
stock               INTEGER DEFAULT 1          # 0 = Sold Out
featured            INTEGER DEFAULT 0
created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
is_sale             INTEGER DEFAULT 0          # Sale countdown active flag
sale_end_time       TEXT NULL                  # ISO datetime string
bundle_pack         TEXT NULL                  # Bundle offer description
shipping_rule       TEXT DEFAULT 'Standard Shipping Applies'
imported_premium    INTEGER DEFAULT 0          # Premium imported tag
```

### ORDERS TABLE Schema:
```
id                  INTEGER PRIMARY KEY AUTOINCREMENT
product_id          INTEGER NOT NULL           # FK to products.id
customer_name       TEXT NOT NULL
whatsapp            TEXT NOT NULL
address             TEXT NOT NULL
city                TEXT NOT NULL
order_date          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
status              TEXT DEFAULT 'pending'     # pending/confirmed/shipped
notes               TEXT NULL
```

### Current Data:
- **Products:** 1 active
- **Orders:** 3 total

---

## 2. BACKEND LOGIC (app.py)

### Configuration:
```python
SECRET_KEY: 'moiz_shoe_store_secret_2026'
UPLOAD_FOLDER: 'static/uploads'
MAX_FILE_SIZE: 16MB
ALLOWED_EXTENSIONS: png, jpg, jpeg, gif, webp
```

### Route Structure:

#### PUBLIC ROUTES (Customer-Facing):
1. **`/` (GET)** - Homepage/Product Catalog
   - Displays all products with stock > 0
   - Size filter support (?size=42)
   - Returns: `index.html`

2. **`/product/<int:product_id>` (GET)** - Product Detail Page
   - Single product view with related products
   - Returns: `product.html`

3. **`/checkout/<int:product_id>` (GET, POST)** - Checkout/COD Form
   - GET: Display checkout form
   - POST: Create order, reduce stock, redirect to confirmation
   - Returns: `checkout.html`

4. **`/order-confirmation/<int:order_id>` (GET)** - Order Success Page
   - Displays order details after successful checkout
   - Returns: `order_confirmation.html`

5. **`/search` (GET)** - Product Search
   - Query parameter: ?q=search_term
   - Returns: `search_results.html`

#### ADMIN ROUTES (Protected):
6. **`/moiz-admin/login` (GET, POST)** - Admin Login
   - Credentials: moizshabbir2248@gmail.com / abdulmoiz217@
   - Sets session['logged_in'] = True
   - Returns: `moiz_admin_login.html`

7. **`/moiz-admin/logout` (GET)** - Admin Logout
   - Clears session
   - Redirects to login

8. **`/moiz-admin` (GET, POST)** - Main Admin Dashboard
   - **Security:** Requires session['logged_in'] = True
   - **GET:** Fetches pending orders + all products
   - **POST Actions:**
     - `add_product`: Insert new product (handles file upload OR URL)
     - `delete_product`: DELETE from products WHERE id
     - `edit_product`: UPDATE products SET ... WHERE id
   - Returns: `moiz_admin.html`

9. **`/moiz-admin-orders` (GET)** - Orders Dashboard (Legacy)
   - Protected by session check
   - Returns: `orders_dashboard.html`

### Session Security:
```python
# Login check decorator pattern:
if not session.get('logged_in'):
    return redirect(url_for('moiz_admin_login'))
```
- Session-based authentication
- No password hashing (plain text comparison - PRODUCTION RISK)
- Single admin user hardcoded

### File Upload Handling:
- Files saved to `static/uploads/` with timestamp prefix
- Secure filename sanitization via `werkzeug.utils.secure_filename`
- Falls back to image URL text input if no file uploaded

---

## 3. FRONTEND & FEATURES

### Active Templates & Features:

#### STOREFRONT (Customer-Facing):
**`index.html`** - Product Grid Homepage
- ✅ 2-column mobile, 3-col tablet, 4-col desktop grid
- ✅ Size filter pills (40-45)
- ✅ Product cards with image, title, size, price, condition rating
- ✅ **LIVE COUNTDOWN TIMER** (⏰ SALE ENDS HH:MM:SS) - updates every second
- ✅ Sold Out overlay badge for stock = 0
- ✅ Fixed announcement bar (COD Available)
- ✅ Matt Black (#0b0b0b) / Dark Charcoal (#161616) design

**`product.html`** - Product Detail Page
- ✅ Large product image
- ✅ Price display with original/sale pricing
- ✅ Size, condition, brand details
- ✅ Shipping rule display
- ✅ "Buy Now (COD)" button
- ✅ Related products carousel

**`checkout.html`** - COD Order Form
- ✅ Form fields: Customer Name, WhatsApp, Address, City, Notes
- ✅ Product summary card
- ✅ Final price display
- ✅ Form validation

**`order_confirmation.html`** - Order Success Page
- ✅ Success checkmark animation
- ✅ Order details (ID, date, status)
- ✅ Product summary
- ✅ Delivery information
- ✅ WhatsApp contact display
- ✅ "What Happens Next?" timeline
- ✅ Print functionality
- ✅ **FIXED:** No longer crashes on date display (uses format_datetime helper)

#### ADMIN PANEL:
**`moiz_admin_login.html`** - Admin Login
- ✅ Email/password form
- ✅ Matt Black design
- ✅ Flash messages for errors

**`moiz_admin.html`** - Unified Admin Dashboard (3 Tabs)
- **TAB 1: 🛒 Live COD Orders**
  - ✅ Table of pending orders
  - ✅ Customer details
  - ✅ Green WhatsApp chat button (auto-generates message link)
  
- **TAB 2: 📦 Manage Store Inventory**
  - ✅ Product listing table (ID, Title, Size, Price, Location Code, Shipping, Stock)
  - ✅ **🔴 SOLD OUT BADGE** (crimson red when stock = 0)
  - ✅ **✏️ EDIT BUTTON** (amber/yellow) - opens modal
  - ✅ **🗑 DELETE BUTTON** (red with confirmation)
  
- **TAB 3: ➕ Add New Product**
  - ✅ Basic Product Info form (Title, Size, Code, Condition Rating)
  - ✅ **🔥 Sales & Marketing Rules Card:**
    - ✅ **Auto-Discount Calculator** (red badge shows % OFF live)
    - ✅ Time-Limited Sale toggle + datetime picker
    - ✅ Marketing toggles:
      - ✅ Free Shipping checkbox
      - ✅ Bundle Pack offer (with dynamic text field)
      - ✅ Imported Premium Stock tag
  - ✅ **DRAG & DROP IMAGE UPLOAD** (📸 click or drag files)
    - Visual hover effects
    - File name display on selection
    - Fallback to URL text input
    - Max 16MB, accepts: png/jpg/jpeg/gif/webp

- **EDIT PRODUCT MODAL:**
  - ✅ Modal overlay (click outside to close)
  - ✅ Pre-filled form with current product data
  - ✅ Editable fields: Title, Size, Price, Original Price, Code, Condition, Stock
  - ✅ Stock hint: "Set to 0 to mark as Sold Out"
  - ✅ Submit to edit_product action

### JavaScript Features:
- Tab switching (3-tab admin interface)
- Real-time discount % calculation
- Countdown timer initialization and live updates
- Drag & drop file upload with visual feedback
- Edit modal open/close with data pre-fill
- Click-outside-to-close modal handler

---

## 4. RECENT FIXES (Resolved Issues)

### ✅ Jinja2 `.strftime()` Error - RESOLVED
**Problem:** Order confirmation page crashed with:
```
UndefinedError: 'str object' has no attribute 'strftime'
```
**Root Cause:** SQLite3 returns `order_date` as ISO string, not datetime object

**Solution Applied:**
- Changed from: `{{ order.order_date.strftime('%B %d, %Y at %I:%M %p') }}`
- Changed to: `{{ format_datetime(order.order_date) }}`
- Uses context processor utility that handles string → datetime conversion

### ✅ Database Mismatch Error - RESOLVED
**Problem:** Order confirmation crashed trying to access nested objects:
```
order.product.name, order.product.price, order.product.brand
```
**Root Cause:** SQL JOIN returns flat row dictionary, not nested objects

**Solution Applied:**
- SQL query already returns aliased columns: `product_name`, `price`, `brand`, `size`, `condition`
- Updated template to access flat fields: `order.product_name`, `order.price`, etc.
- Removed nested object references

### ✅ Sale Countdown Not Working - RESOLVED
**Problem:** Countdown timer badge not appearing on storefront

**Root Cause:** 
1. Database had products with `is_sale = 1` but `sale_end_time = NULL`
2. Home route wasn't fetching `is_sale` and `sale_end_time` columns

**Solution Applied:**
1. Updated home route query to include: `is_sale, sale_end_time`
2. Fixed existing products in database to have valid future timestamps
3. JavaScript countdown initializes on DOM load and updates every second
4. Format: `⏰ SALE ENDS HH:MM:SS` with red badge

### ✅ Location Code Optional - CONFIRMED
- No `required` attribute on Location Code field
- Backend safely handles: `.strip() or None` → stores NULL if empty
- No crashes when field left blank

---

## 5. SECURITY CONSIDERATIONS FOR PRODUCTION

### ⚠️ CURRENT RISKS:
1. **Plain Text Password Comparison** - Should use bcrypt/werkzeug.security
2. **Hardcoded Credentials** - Should move to environment variables
3. **No HTTPS Enforcement** - Session cookies vulnerable to interception
4. **No CSRF Protection** - Forms lack CSRF tokens
5. **SQL Injection Risk** - Using parameterized queries (✅ safe currently)
6. **No Rate Limiting** - Login endpoint vulnerable to brute force

### ✅ CURRENT SAFE PRACTICES:
- Session-based authentication active
- Parameterized SQL queries throughout
- File upload type validation (whitelist)
- Secure filename sanitization
- File size limits enforced

---

## 6. DEPLOYMENT STATUS

**Current Environment:** Development Server
```
Flask Debug Mode: ON
Host: 0.0.0.0:5000
Database: Local SQLite file (shoes.db)
File Storage: Local filesystem (static/uploads/)
```

**Access URLs:**
- Storefront: http://127.0.0.1:5000
- Admin Login: http://127.0.0.1:5000/moiz-admin/login
- Admin Dashboard: http://127.0.0.1:5000/moiz-admin

**Admin Credentials:**
- Email: moizshabbir2248@gmail.com
- Password: abdulmoiz217@

---

## 7. NEXT STEPS RECOMMENDATIONS

### IMMEDIATE (Pre-Production):
1. Implement password hashing (werkzeug.security)
2. Add CSRF protection (Flask-WTF)
3. Move credentials to environment variables
4. Set up proper error logging
5. Add backup strategy for shoes.db

### SHORT TERM:
1. Migrate to production WSGI server (Gunicorn/uWSGI)
2. Set up HTTPS/SSL certificate
3. Implement rate limiting (Flask-Limiter)
4. Add image compression for uploads
5. Create database migration system

### MEDIUM TERM:
1. Add order status tracking
2. Implement inventory low-stock alerts
3. Add sales analytics dashboard
4. Email/SMS notifications for orders
5. Product image gallery (multiple images per product)

---

**Project Status:** ✅ Fully Functional Development Build  
**All Critical Bugs:** ✅ Resolved  
**Ready for:** Internal Testing / Staging Deployment

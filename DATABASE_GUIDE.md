# Sohrab Shoes House - Database Architecture Guide

## ✅ Implementation Complete

Aapki Flask app ab **Neon DB (PostgreSQL)** se successfully connect ho rahi hai!

---

## 🏗️ Architecture Overview

### Database Strategy (Lightweight & Optimized)

1. **Products**: Hardcoded in `products_data.py` (No database storage)
2. **Orders**: Neon DB (PostgreSQL) - Sirf customer text data

---

## 📁 File Structure

```
├── app.py                  # Main Flask application (Updated)
├── db_config.py            # Neon DB connection & functions (New)
├── products_data.py        # Hardcoded products list (New)
├── static/
│   └── uploads/            # Product images
└── templates/
    └── (all HTML files)
```

---

## 🗄️ Database Schema

### Orders Table (Neon DB - PostgreSQL)

```sql
CREATE TABLE orders (
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
    notes TEXT
);
```

**Indexes for Performance:**
- `idx_orders_date` - Fast date-based queries
- `idx_orders_status` - Fast status filtering

---

## 🔌 Connection Details

**Neon DB URL:**
```
postgresql://neondb_owner:npg_7vKwrcY9xApW@ep-floral-butterfly-aogt9hvm-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

**Connection Pool Settings:**
- Min Connections: 1
- Max Connections: 10
- Timeout: 30 seconds (Prevents database locked errors)

---

## 📦 How to Add New Products

Products ko hardcoded list mein add karne ke liye `products_data.py` file edit karein:

```python
PRODUCTS = [
    {
        'id': 'PROD_001',                    # Unique ID (text)
        'title': 'Nike Air Max',             # Product title
        'brand': 'Nike',                     # Brand name
        'description': 'Premium shoes',      # Description
        'price': 1590.0,                     # Current price
        'original_price': 2000.0,            # Original price (optional)
        'size': '42',                        # Size
        'condition': 'Excellent',            # Condition
        'condition_rating': 9.0,             # Rating (0-10)
        'color': 'Black/White',              # Color
        'category': 'Sneakers',              # Category
        'code': 'NK-AM-001',                 # Internal code
        'image_url': '/static/uploads/image.jpg',  # Image path
        'stock': 1,                          # Stock quantity
        'is_sale': 0,                        # Sale flag (0 or 1)
        'sale_end_time': None,               # Sale end time
        'shipping_rule': 'Free Shipping',    # Shipping info
        'imported_premium': 0                # Premium flag (0 or 1)
    },
    # Add more products here...
]
```

**Steps:**
1. Open `products_data.py`
2. Copy the product template above
3. Update values for your new product
4. Save the file
5. Restart Flask app

---

## 🚀 How to Run

```bash
cd "C:\Users\user\Desktop\a new start for shoes business"
python app.py
```

**App will start on:**
- Main Site: http://127.0.0.1:5000
- Admin Panel: http://127.0.0.1:5000/moiz-admin/login

**Admin Credentials:**
- Email: moizshabbir2248@gmail.com
- Password: abdulmoiz217@

---

## 📊 Database Functions (Available in db_config.py)

### Create Order
```python
from db_config import create_order

order_id = create_order(
    customer_name="John Doe",
    phone_number="03001234567",
    delivery_address="123 Main St",
    city="Karachi",
    product_id_or_name="PROD_001 - Nike Air Max",
    quantity=1,
    total_price=1590.0,
    notes="Rush delivery"
)
```

### Get Order by ID
```python
from db_config import get_order_by_id

order = get_order_by_id(1)
print(order)  # Returns dict with all order details
```

### Get All Orders
```python
from db_config import get_all_orders

# All orders
all_orders = get_all_orders()

# Only pending orders
pending_orders = get_all_orders(status='pending')
```

### Update Order Status
```python
from db_config import update_order_status

success = update_order_status(order_id=1, new_status='completed')
```

---

## 🎯 Benefits of This Architecture

### ✅ Lightweight Database
- No product data in database = minimal storage
- Only customer orders stored = faster queries
- Reduced database costs

### ✅ Performance Optimized
- Connection pooling (10 max connections)
- 30-second timeout prevents locked errors
- Indexes on frequently queried columns

### ✅ Easy Product Management
- Add/edit products without database migrations
- No SQL needed - just edit Python file
- Instant updates (restart app)

### ✅ No Crash Risk
- Products in code = no database overload
- Connection pool handles traffic spikes
- Timeout prevents hanging connections

---

## 🔧 Troubleshooting

### Database Connection Failed
- Check internet connection
- Verify Neon DB URL is correct
- Check Neon DB is not paused (free tier auto-pauses after inactivity)

### Orders Not Saving
- Check database connection in terminal
- Verify all required fields are filled
- Check Neon DB dashboard for errors

### Products Not Showing
- Verify `products_data.py` syntax is correct
- Check `stock > 0` for products
- Restart Flask app after editing products

---

## 📝 Notes

1. **Stock Management**: Stock reduction happens in-memory only. After app restart, stock resets to values in `products_data.py`

2. **Images**: Store images in `static/uploads/` folder and reference them as `/static/uploads/filename.jpg`

3. **Database**: Only orders are stored in Neon DB. Products remain in code.

4. **Scaling**: Current setup handles 10 concurrent database connections. Increase `maxconn` in `db_config.py` if needed.

---

## 🎉 Summary

Aapki app ab fully optimized hai:
- ✅ Neon DB (PostgreSQL) successfully connected
- ✅ Orders table created with proper indexes
- ✅ Products hardcoded for lightweight operation
- ✅ Connection pooling enabled
- ✅ 30-second timeout prevents locked errors
- ✅ Clean architecture for easy maintenance

**Everything is ready to use!**

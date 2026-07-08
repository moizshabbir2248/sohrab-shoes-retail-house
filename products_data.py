"""
Hardcoded Products Data
Sab products yahan stored hain - database mein nahi
"""

PRODUCTS = [
    {
        'id': 'PROD_001',
        'title': 'Nike Air Max Premium',
        'brand': 'Nike',
        'description': 'Premium quality Nike Air Max shoes in excellent condition',
        'price': 1590.0,
        'original_price': 2000.0,
        'size': '42',
        'condition_rating': 9.0,
        'category': 'Sneakers',
        'image_url': '/static/uploads/20260626170652_myfirstminecraftskin.png',
        'stock': 1,
        'is_sale': 0,
        'sale_end_time': None,
        'shipping_rule': 'Free Shipping',
        'imported_premium': 0
    },
    {
        'id': 'test product',
        'title': 'addidas',
        'brand': None,
        'description': None,
        'price': 1500.0,
        'original_price': 2000.0,
        'size': '40',
        'condition_rating': 9.0,
        'category': None,
        'image_url': '/static/uploads/20260627134654_sss.png',
        'stock': 1,
        'is_sale': 0,
        'sale_end_time': None,
        'shipping_rule': 'Free Shipping',
        'imported_premium': 0
    },
]

def get_all_products():
    """Return all products with stock > 0"""
    return [p for p in PRODUCTS if p.get('stock', 0) > 0]

def get_product_by_id(product_id):
    """Get single product by ID"""
    for product in PRODUCTS:
        if str(product['id']) == str(product_id):
            return product
    return None

def search_products(query):
    """Search products by title, brand, or description"""
    query = query.lower()
    results = []
    for product in PRODUCTS:
        if (query in product.get('title', '').lower() or
            query in product.get('brand', '').lower() or
            query in product.get('description', '').lower()):
            results.append(product)
    return results

def filter_products_by_size(size):
    """Filter products by size"""
    return [p for p in PRODUCTS if p.get('size') == size and p.get('stock', 0) > 0]

def reduce_stock(product_id, quantity=1):
    """Reduce product stock after order (in-memory only)"""
    for product in PRODUCTS:
        if str(product['id']) == str(product_id):
            current_stock = product.get('stock', 0)
            product['stock'] = max(0, current_stock - quantity)
            return True
    return False

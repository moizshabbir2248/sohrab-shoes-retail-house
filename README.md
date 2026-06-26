# Premium Shoe Store E-Commerce System

A complete luxury e-commerce platform for selling imported shoes with Cash on Delivery (COD), featuring advanced sales management, time-limited promotions, bundle packs, and custom shipping rules.

## 🌟 Features

### Customer-Facing Website (Flask)
- **Luxury Minimalist Design**: Dark premium aesthetic (Hypebeast/Sneakerhead vibe)
- **Product Catalog**: Clean grid layout with size filters
- **Product Details**: Individual product pages with specs and similar products
- **COD Checkout**: Cash on Delivery ordering system with shipping transparency
- **Order Confirmation**: Professional order confirmation pages
- **Responsive Design**: Mobile-first, scales beautifully across devices

### Advanced Admin Panel (Streamlit)
- **📦 Inventory Management**: View, filter, update stock, delete products
- **➕ Add New Products**: Complete product entry form with free shipping toggle
- **🔥 Advanced Sales & Marketing**:
  - ⏰ Time-Limited Sales with countdown
  - 🎁 Bundle Pack Promotions (Buy 1 Get 1 Free, etc.)
  - 🚚 Custom Shipping Rules (Free shipping per product)
- **🛒 Order Management**: View and update COD orders
- **Auto-Migration**: Automatically updates database schema

### Marketing Features
1. **Time-Limited Sales**: Set sale prices with expiration dates
2. **Bundle Packs**: Configure promotional offers per product
3. **Custom Shipping**: Override shipping charges for specific shoes
4. **Sale Badges**: Automatic display of active promotions

## 📁 Project Structure

```
a new start for shoes business/
├── app.py                      # Flask web application
├── admin.py                    # Streamlit admin panel
├── shoes.db                    # SQLite database (auto-created)
├── templates/                  # HTML templates
│   ├── index.html             # Homepage/Product grid
│   ├── product.html           # Product detail page
│   ├── checkout.html          # Checkout form
│   ├── order_confirmation.html
│   ├── 404.html
│   └── 500.html
├── static/                     # Static assets (if needed)
└── README.md                   # This file
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Install Dependencies

```bash
pip install flask flask-sqlalchemy streamlit pandas
```

### Step 2: Initialize Database

The database will be created automatically when you first run the Flask app:

```bash
python app.py
```

This creates `shoes.db` with all necessary tables.

## 🎮 Running the System

### 1. Start the Customer Website (Flask)

```bash
python app.py
```

- **Customer Website**: http://127.0.0.1:5000
- **Mobile Access**: http://YOUR_IP:5000 (same network)

### 2. Start the Admin Panel (Streamlit)

Open a **new terminal** and run:

```bash
streamlit run admin.py
```

- **Admin Panel**: http://localhost:8501

## 🔧 Using the Admin Panel

### Adding Your First Shoe

1. **Navigate to** "➕ Add New Shoe"
2. **Fill in Product Information**:
   - Shoe Title (e.g., "Nike Air Jordan 1")
   - Size (40-45)
   - Condition (8/10 to Brand New)
   - Original Price & COD Sale Price
   - Bhora Location Code (e.g., "A-12")
   - Image URL (optional)
3. **Configure Shipping**:
   - Check "Apply FREE Shipping" if this shoe qualifies
4. **Click** "Add Shoe to Inventory"

### Configuring Advanced Sales

1. **Navigate to** "🔥 Advanced Sales & Marketing Rules"
2. **Select a Product** from the dropdown
3. **Choose a Marketing Feature**:

#### ⏰ Time-Limited Sale
- Enable sale checkbox
- Set end date and time
- Enter sale price
- System automatically displays discount percentage
- Sale expires automatically at the set time

#### 🎁 Bundle Packs
- Select from pre-configured offers:
  - Buy 1 Get 1 Free
  - Buy 2 Get 20% Off
  - Buy 3 Get 30% Off
  - Custom offers
- Displays on product cards

#### 🚚 Custom Shipping Rules
- **Standard Shipping Applies** (default)
- **FREE Shipping on this Shoe Only** (overrides standard charges)

### Managing Orders

1. **Navigate to** "🛒 View COD Orders"
2. **View Order Details**: Customer name, WhatsApp, address, product
3. **Update Order Status**:
   - Pending → Confirmed → Shipped → Delivered
   - Or mark as Cancelled

### Inventory Management

1. **Navigate to** "📦 View & Manage Inventory"
2. **Quick Actions**:
   - Update stock levels
   - Delete products
   - View sales statistics
3. **Filters**: Size, stock status, sale status

## 🛍️ Customer Shopping Flow

1. **Browse Products**: Homepage shows all available shoes
2. **Filter by Size**: Top filter bar (40-45)
3. **View Details**: Click any product card
4. **Order with COD**:
   - Click "Buy Now"
   - Fill delivery details (Name, WhatsApp, Address, City)
   - Place order
5. **Confirmation**: Order ID and WhatsApp confirmation message

## 💳 Shipping & Pricing

### Standard Shipping
- Applies to all products by default
- Shipping charges calculated at delivery
- Customer pays: **Product Price + Shipping**

### Free Shipping Products
- Set via Admin Panel → Advanced Sales → Custom Shipping
- Displays "FREE SHIPPING" badge (if implemented in templates)
- Customer pays: **Product Price Only**

### Price Display
- **Old Price**: Crossed out (if set)
- **Current Price**: Prominently displayed
- **Sale Price**: Shown during active sale periods
- **+ Shipping charges**: Noted in checkout (unless free shipping)

## 📊 Database Schema

### Products Table
```
id, name, brand, description, price, original_price, size, condition,
condition_rating, color, category, location, code, image_url, stock,
featured, created_at, is_sale, sale_end_time, bundle_pack, shipping_rule
```

### Orders Table
```
id, product_id, customer_name, whatsapp, address, city,
order_date, status, notes
```

## 🔐 Admin Access

### Flask Admin (Basic - Built-in)
- URL: http://127.0.0.1:5000/admin/login
- Username: `admin`
- Password: `admin123`
- **⚠️ Change these credentials in production!**

### Streamlit Admin (Advanced - Recommended)
- No login required (runs locally)
- Full inventory and sales management
- Use this for day-to-day operations

## 🎨 Design Specifications

### Color Palette
- Background: Matt Black `#0b0b0b`
- Cards: Dark Charcoal `#161616`
- Borders: `#222222`
- Text Primary: White `#ffffff`
- Text Secondary: Silver `#a0a0a0`
- Sold Out: Crimson Red `#ff3333`
- Buttons: White with Black text

### Typography
- Font: System UI (system-ui, -apple-system)
- Clean, minimalist spacing
- Uppercase labels with letter-spacing

## 🚨 Important Notes

1. **Database Consistency**: Both Flask app and Streamlit admin use `shoes.db`
2. **Schema Auto-Migration**: Admin panel automatically adds new columns if missing
3. **Shipping Rules**: Set per product, Flask reads them at checkout
4. **Time-Limited Sales**: Automatically expire based on `sale_end_time`
5. **Stock Management**: Orders automatically reduce stock count
6. **No Free Delivery Claims**: System correctly shows shipping charges apply (except for free shipping products)

## 📱 Mobile Optimization

- Fully responsive design
- Touch-optimized interactions
- Clean mobile navigation
- 2-column grid on phones, scales to 3-4 on larger screens

## 🔄 Workflow Example

### Scenario: Running a Weekend Sale

1. **Add Products** (if not already added):
   - Use "➕ Add New Shoe" in admin panel
   
2. **Configure Sale** (Friday):
   - Go to "🔥 Advanced Sales & Marketing"
   - Select product
   - Enable Time-Limited Sale
   - Set end time: Sunday 11:59 PM
   - Set sale price (e.g., 20% off)
   - Click "Apply Sale Configuration"

3. **Monitor Orders**:
   - Check "🛒 View COD Orders"
   - Update order statuses as you process them
   - Contact customers via WhatsApp with final pricing (product + shipping)

4. **Sale Ends Automatically**:
   - System returns to regular pricing after Sunday 11:59 PM
   - No manual intervention needed

## 🐛 Troubleshooting

### Database Errors
```bash
# Delete and recreate database
rm shoes.db  # Mac/Linux
del shoes.db  # Windows
python app.py  # Recreates tables
```

### Port Already in Use
```bash
# Flask (change port in app.py line 530)
app.run(debug=True, host='0.0.0.0', port=5001)

# Streamlit (use different port)
streamlit run admin.py --server.port 8502
```

### Missing Columns Error
- The admin panel auto-migrates schema
- Run `streamlit run admin.py` once to update database

## 📞 Support & Customization

### Change Admin Credentials
Edit `app.py` lines 213-214:
```python
ADMIN_USERNAME = 'your_username'
ADMIN_PASSWORD = 'your_secure_password'
```

### Modify Announcement Bar
Edit `templates/index.html` line 71:
```html
<div class="announcement-bar">
    Your Custom Message Here
</div>
```

### Add More Size Options
Edit `templates/index.html` size filter section

## 🎯 Best Practices

1. **Regular Backups**: Copy `shoes.db` file regularly
2. **Image URLs**: Use reliable image hosting (Imgur, Cloudinary)
3. **Product Codes**: Use consistent location coding (A-12, B-5, etc.)
4. **Stock Updates**: Update immediately after receiving/selling inventory
5. **Order Status**: Keep customers informed via WhatsApp
6. **Sale Planning**: Schedule sales during high-traffic periods
7. **Shipping Transparency**: Always confirm final price (product + shipping) via WhatsApp

## 📈 Future Enhancements

Potential features to add:
- WhatsApp API integration for automated messages
- Payment gateway integration (beyond COD)
- Customer accounts and order history
- Email notifications
- Analytics dashboard
- Multi-image gallery per product
- Product reviews and ratings
- Automatic sale expiration notifications

## 🌐 Accessing from Mobile

### Same WiFi Network:
1. Find your laptop's IP address:
   - Windows: `ipconfig` (look for IPv4 Address)
   - Mac/Linux: `ifconfig | grep inet`
   
2. On your phone's browser:
   ```
   http://YOUR_IP:5000
   ```
   Example: `http://192.168.1.100:5000`

### Firewall Issues (Windows):
If you can't access from mobile:
1. Open Windows Defender Firewall
2. Allow Python through the firewall
3. Or temporarily disable firewall for testing

## 📝 License

This is a custom e-commerce solution for your shoe business.

---

**Built with ❤️ for Premium Shoe Sales**

**Tech Stack**: Flask + SQLAlchemy + Streamlit + SQLite

For technical support or customization requests, refer to the code documentation in `app.py` and `admin.py`.

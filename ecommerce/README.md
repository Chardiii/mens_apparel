# ECommerce Platform

A full-featured ecommerce web application built with **Python Flask**, **SQLAlchemy**, and **MySQL** database. Supports multiple user roles: Buyer, Seller, Admin, and Rider.

## Project Structure

```
ecommerce/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
│
├── models/                     # Database models
│   ├── __init__.py
│   ├── user.py                # User model (Buyer, Seller, Admin, Rider)
│   ├── product.py             # Product model
│   ├── order.py               # Order and OrderItem models
│   ├── payment.py             # Payment model
│   └── review.py              # Review model
│
├── routes/                     # Flask blueprints (API routes)
│   ├── __init__.py
│   ├── main.py                # Main routes
│   ├── auth.py                # Authentication routes
│   ├── products.py            # Product routes
│   ├── orders.py              # Order routes
│   └── admin.py               # Admin routes
│
├── templates/                 # HTML templates
│   ├── base.html              # Base template
│   ├── index.html             # Home page
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── profile.html           # User profile
│   ├── products.html          # Products listing
│   ├── product_detail.html    # Product details
│   ├── add_product.html       # Add product (seller)
│   ├── seller_dashboard.html  # Seller dashboard
│   ├── buyer_dashboard.html   # Buyer dashboard
│   ├── rider_dashboard.html   # Rider dashboard
│   ├── order_detail.html      # Order details
│   ├── my_orders.html         # Buyer's orders
│   ├── checkout.html          # Checkout page
│   └── admin/                 # Admin templates
│       ├── dashboard.html
│       ├── users.html
│       ├── products.html
│       ├── orders.html
│       ├── sellers.html
│       ├── riders.html
│       └── reports.html
│
├── static/                    # Static files
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
│
└── .venv/                     # Virtual environment (auto-created)
```

## Features

### User Roles

1. **Buyer**
   - Browse and search products
   - Add items to shopping cart
   - Place orders
   - Track order status
   - Leave product reviews
   - View order history

2. **Seller**
   - Create and manage products
   - View orders received for their products
   - Manage product inventory
   - Monitor sales and ratings
   - View customer reviews

3. **Admin**
   - Manage all users
   - Monitor products and orders
   - Generate reports and analytics
   - Control seller and rider accounts
   - View platform statistics

4. **Rider/Delivery Partner**
   - View assigned deliveries
   - Update delivery status
   - Track earnings and ratings
   - Manage delivery profile

### Core Functionality

- ✅ User Authentication & Authorization
- ✅ Role-based Access Control (RBAC)
- ✅ Product Management (CRUD operations)
- ✅ Shopping Cart System
- ✅ Order Management
- ✅ Payment Processing (multiple methods)
- ✅ Order Tracking
- ✅ User Profiles
- ✅ Product Reviews & Ratings
- ✅ Admin Dashboard & Statistics

## Installation & Setup

### Prerequisites

- Python 3.8+
- MySQL/SQLyog
- pip (Python package manager)

### Step 1: Clone/Download the Project

```bash
cd c:\Users\veluz\OneDrive\Desktop\mode_web\ecommerce
```

### Step 2: Virtual Environment (Already Created)

The virtual environment has been automatically created at `.venv/`

### Step 3: Install Dependencies (Already Done)

All required packages have been installed. To verify:

```bash
.venv\Scripts\pip list
```

### Step 4: Database Setup

1. **Open MySQL/SQLyog**
2. **Create a new database:**
   ```sql
   CREATE DATABASE ecommerce_db;
   ```

3. **Update `.env` file** (if using non-root user):
   ```
   SQLALCHEMY_DATABASE_URI=mysql+pymysql://username:password@localhost/ecommerce_db
   ```

### Step 5: Run the Application

```bash
# Activate virtual environment (if not already active)
.venv\Scripts\activate

# Run the Flask app
python app.py
```

Or directly:
```bash
.venv\Scripts\python.exe app.py
```

The application will be available at: **http://localhost:5000**

## Default Test Accounts

**Admin Account** (create after first run):
- Username: `admin`
- Password: `admin123`
- Role: Admin

**Test Seller Account:**
- Username: `seller1`
- Password: `seller123`
- Role: Seller

**Test Buyer Account:**
- Username: `buyer1`
- Password: `buyer123`
- Role: Buyer

## Database Tables

The application automatically creates the following tables:

- `users` - User accounts (Buyer, Seller, Admin, Rider)
- `products` - Product listings
- `product_images` - Product images
- `orders` - Customer orders
- `order_items` - Items in each order
- `payments` - Payment information
- `reviews` - Product reviews

## Configuration

Edit `config.py` to customize:

- Database connection string
- Secret key (change in production)
- Session settings
- Debug mode

## Routes Overview

### Authentication Routes
- `GET/POST /auth/register` - User registration
- `GET/POST /auth/login` - User login
- `GET /auth/logout` - User logout
- `GET /auth/profile` - View profile
- `GET/POST /auth/profile/edit` - Edit profile

### Product Routes
- `GET /products/` - List all products
- `GET /products/<id>` - View product details
- `GET/POST /products/seller/add` - Add new product (Seller)
- `GET/POST /products/seller/edit/<id>` - Edit product (Seller)
- `POST /products/seller/delete/<id>` - Delete product (Seller)
- `GET /products/seller/dashboard` - Seller dashboard

### Order Routes
- `GET /orders/cart` - Shopping cart
- `POST /orders/add-to-cart/<id>` - Add to cart
- `GET/POST /orders/checkout` - Checkout page
- `GET /orders/<id>` - Order details
- `GET /orders/my-orders` - Buyer's orders
- `GET /orders/seller/received` - Seller's received orders

### Admin Routes
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/users` - Manage users
- `GET /admin/products` - Manage products
- `GET /admin/orders` - Manage orders
- `GET /admin/sellers` - Manage sellers
- `GET /admin/riders` - Manage riders
- `GET /admin/reports` - View reports

## Next Steps to Enhance

1. **Frontend Improvements**
   - Better UI/UX with more styling
   - Add JavaScript interactivity
   - Implement drag-and-drop for images
   - Add real-time notifications

2. **Backend Enhancements**
   - Implement payment gateway integration
   - Add email notifications
   - Implement search filters
   - Add product recommendations
   - Implement cart session management

3. **Advanced Features**
   - Real-time order tracking with GPS
   - Chat between buyer and seller
   - Wishlist functionality
   - Coupon and discount system
   - Multi-currency support
   - API endpoints for mobile app

4. **Security & Performance**
   - Add CSRF protection
   - Implement rate limiting
   - Add password hashing (already done)
   - Database query optimization
   - Caching implementation
   - Add SSL/HTTPS

5. **Testing**
   - Unit tests
   - Integration tests
   - API testing

## Troubleshooting

### Database Connection Error
- Ensure MySQL is running
- Check database name in `.env`
- Verify username and password

### Port 5000 Already in Use
```bash
# Use a different port
python -c "from app import create_app; create_app().run(debug=True, port=5001)"
```

### Import Errors
```bash
# Ensure virtual environment is activated and packages installed
.venv\Scripts\pip install -r requirements.txt
```

## Database Backup

To backup the database:
```bash
# Using mysqldump
mysqldump -u root ecommerce_db > backup.sql
```

To restore:
```bash
# Restore from backup
mysql -u root ecommerce_db < backup.sql
```

## Support & Documentation

- Flask Documentation: https://flask.palletsprojects.com/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- MySQL Documentation: https://dev.mysql.com/doc/

## License

This project is open-source and available for educational and commercial use.

---

**Happy Coding! 🚀**

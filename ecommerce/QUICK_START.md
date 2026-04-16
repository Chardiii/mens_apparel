# Quick Start Guide for ECommerce Platform

## What's been created:

✅ **Complete Folder Structure**
- Backend: Models, Routes, Configuration
- Frontend: HTML Templates with Bootstrap styling
- Static Files: CSS and JavaScript

✅ **Database Models**
- User (with roles: Buyer, Seller, Admin, Rider)
- Product (with images and reviews)
- Order (with items)
- Payment
- Review

✅ **Routes & Features**
- Authentication (Login/Register)
- Product Management
- Order Management
- Admin Dashboard
- User Profiles

✅ **Python Environment**
- Virtual environment created at `.venv/`
- All dependencies installed (Flask, SQLAlchemy, etc.)

## Quick Start:

### 1. Database Setup (Important!)
```
1. Open MySQL/SQLyog
2. Create database: CREATE DATABASE ecommerce_db;
3. The tables will be auto-created on first run
```

### 2. Run the Application
```
# Option A: Double-click run.bat (Windows)
run.bat

# Option B: Command line
.venv\Scripts\python.exe app.py

# The app will start at: http://localhost:5000
```

### 3. First-Time Usage
1. **Register** a new account (Buyer/Seller/Admin/Rider)
2. **Login** with your credentials
3. **Explore** the dashboard based on your role

### 4. Test Different Roles
- **Buyer**: Browse products, place orders, track deliveries
- **Seller**: Add products, manage inventory, view orders
- **Admin**: Manage users, products, orders, view analytics
- **Rider**: View assigned deliveries (feature in progress)

## Default Test Data:

After first run, you can:
1. Create test accounts for each role
2. Add sample products as a seller
3. Place test orders as a buyer
4. Admin can view all statistics

## Database Query Examples:

```sql
-- View all users
SELECT * FROM users;

-- View all products
SELECT * FROM products;

-- View all orders
SELECT * FROM orders;

-- View user by role
SELECT * FROM users WHERE role = 'seller';
```

## Next Steps:

1. **Customize UI**: Edit templates in `/templates` folder
2. **Add Features**: Extend routes in `/routes` folder
3. **Database**: Add more fields to models in `/models` folder
4. **Configuration**: Update settings in `config.py`

## Important Files:

- `app.py` - Main application file (start here)
- `config.py` - Configuration settings
- `.env` - Environment variables (database credentials)
- `models/` - Database models
- `routes/` - Application routes/endpoints
- `templates/` - HTML pages
- `static/` - CSS and JavaScript

## Troubleshooting:

**Issue: "Can't find MySQL"**
- Solution: Make sure MySQL is running (check Services or SQLyog)

**Issue: "Database error"**
- Solution: Check `.env` file has correct database name and credentials

**Issue: "Module not found"**
- Solution: Activate venv and reinstall: `.venv\Scripts\pip install -r requirements.txt`

## Contact/Support:

Refer to README.md for detailed documentation and configuration guide.

---

Happy Building! 🚀

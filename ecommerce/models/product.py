from . import db
from datetime import datetime

class Product(db.Model):
    __tablename__ = 'products'

    id          = db.Column(db.Integer, primary_key=True)
    seller_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name        = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    price       = db.Column(db.Float, nullable=False)
    # stock on the parent is the SUM of all variant stocks (kept for backwards compat)
    stock       = db.Column(db.Integer, default=0)
    category    = db.Column(db.String(100))

    rating       = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)

    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images      = db.relationship('ProductImage',   backref='product', lazy='dynamic', cascade='all, delete-orphan')
    variants    = db.relationship('ProductVariant', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem',      backref='product', lazy='dynamic')
    reviews     = db.relationship('Review',         backref='product', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def total_stock(self):
        """Sum of all variant stocks, or parent stock if no variants."""
        v = self.variants.all()
        return sum(x.stock for x in v) if v else self.stock

    def __repr__(self):
        return f'<Product {self.name}>'


class ProductVariant(db.Model):
    """SKU-level variant: size + optional colour, with its own stock."""
    __tablename__ = 'product_variants'

    id         = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    size       = db.Column(db.String(30), nullable=False)   # e.g. 'S', 'M', '32', '42'
    color      = db.Column(db.String(50), nullable=True)    # optional
    sku        = db.Column(db.String(100), nullable=True, index=True)
    stock      = db.Column(db.Integer, default=0, nullable=False)
    price_adj  = db.Column(db.Float, default=0.0)           # price delta vs parent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order_items = db.relationship('OrderItem', backref='variant', lazy='dynamic')

    @property
    def effective_price(self):
        return self.product.price + self.price_adj

    def __repr__(self):
        return f'<Variant {self.product_id} {self.size}/{self.color}>'


class ProductImage(db.Model):
    __tablename__ = 'product_images'

    id         = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    image_url  = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ProductImage {self.id}>'

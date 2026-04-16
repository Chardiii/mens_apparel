from . import db
from datetime import datetime


class CartItem(db.Model):
    __tablename__ = 'cart_items'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.id'), nullable=True)
    quantity   = db.Column(db.Integer, nullable=False, default=1)
    added_at   = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', lazy='joined')
    variant = db.relationship('ProductVariant', lazy='joined')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', 'variant_id', name='uq_cart_user_product_variant'),
    )

    @property
    def cart_key(self):
        return f"{self.product_id}:{self.variant_id or 0}"

    @property
    def price(self):
        if self.variant:
            return self.variant.effective_price
        return self.product.price

    @property
    def subtotal(self):
        return round(self.price * self.quantity, 2)

    def __repr__(self):
        return f'<CartItem user={self.user_id} product={self.product_id} variant={self.variant_id}>'

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_ua = db.Column(db.String, unique=True, nullable=False)
    name_ru = db.Column(db.String, nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    art = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)  # полное название товара
    cat = db.Column(db.String)  # основная категория
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    color = db.Column(db.String)
    size = db.Column(db.String)
    qty = db.Column(db.Float)
    old_price = db.Column(db.Float)
    new_price = db.Column(db.Float)
    sale = db.Column(db.String)
    image = db.Column(db.String)
    img_list = db.Column(db.String)  # миниатюра для product.html
    img_cat = db.Column(db.String)   # миниатюра для products.html
    gender = db.Column(db.String)
    season = db.Column(db.String)
    brand = db.Column(db.String)
    section = db.Column(db.String)
    category = db.relationship('Category', backref='products')

# --- Models for new db-der.db (normalized schema) ---
class DerCategory(db.Model):
    __bind_key__ = 'der'
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)

class DerProduct(db.Model):
    __bind_key__ = 'der'
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    article = db.Column(db.String)
    name = db.Column(db.String)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    brand = db.Column(db.String)
    season = db.Column(db.String)
    gender = db.Column(db.String)
    category = db.relationship('DerCategory', backref='products')

class DerVariant(db.Model):
    __bind_key__ = 'der'
    __tablename__ = 'variants'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    size = db.Column(db.String)
    color = db.Column(db.String)
    barcode = db.Column(db.String)
    stock = db.Column(db.Float)
    purchase_price = db.Column(db.Float)
    sale_price = db.Column(db.Float)
    new_price = db.Column(db.Float)
    total_price = db.Column(db.Float)
    discount = db.Column(db.Float)
    product = db.relationship('DerProduct', backref='variants')

def init_app(app):
    db.init_app(app) 
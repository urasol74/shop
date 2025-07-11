from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_ua = db.Column(db.String, unique=True, nullable=False)
    name_ru = db.Column(db.String, nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    art = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
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

def init_app(app):
    db.init_app(app) 
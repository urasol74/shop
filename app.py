from flask import Flask, render_template, send_from_directory, abort, request, url_for
import os
import re
from models import db, Category, Product, init_app

# Загружаем словарь красивых названий категорий
import json
with open(os.path.join('static', 'sections-book.json'), encoding='utf-8') as f:
    SECTIONS_BOOK = json.load(f)

def get_pretty_category(category):
    if not category:
        return ''
    return SECTIONS_BOOK.get(category.upper().strip(), category.capitalize())

import shutil
# --- Автоматическое обновление der.xlsx при запуске ---
src = "/home/ubuntu/bot_art/data/Новый.xlsx"
dst = os.path.join('data', 'der.xlsx')
os.makedirs(os.path.dirname(dst), exist_ok=True)
shutil.copyfile(src, dst)

app = Flask(__name__)
# Конфигурация SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
init_app(app)

# --- Автоматический импорт данных в базу ---
# (удалено по просьбе пользователя)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/categories')
def categories():
    cats = Category.query.order_by(Category.name_ru).all()
    categories = [{"raw": c.name_ua, "pretty": c.name_ru} for c in cats]
    return render_template(
        'sections.html',
        section_verbose='Категории',
        categories=categories,
        section_url='category',
        back_url='/'
    )

@app.route('/category/<category_ua>')
def show_category(category_ua):
    category = Category.query.filter_by(name_ua=category_ua).first_or_404()
    products = Product.query.filter_by(category_id=category.id).all()
    return render_template(
        'products.html',
        products=products,
        category=category.name_ru,
        section_verbose=category.name_ru,
        pretty_category=category.name_ru,
        back_url='/categories'
    )

@app.route('/product/<int:product_id>')
def product_page(product_id):
    product = Product.query.get_or_404(product_id)
    category = Category.query.get(product.category_id)
    return render_template('product.html', product=product, section_verbose=category.name_ru if category else '', back_url=f'/category/{category.name_ua if category else ""}')

@app.route('/search')
def search():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return render_template('search.html', query=query, results=[], count=0)
    products = Product.query.filter(
        (Product.art.ilike(f'%{query}%')) |
        (Product.name.ilike(f'%{query}%')) |
        (Product.color.ilike(f'%{query}%')) |
        (Product.size.ilike(f'%{query}%'))
    ).all()
    results = []
    for p in products:
        category = Category.query.get(p.category_id)
        results.append({
            "art": p.art,
            "name": p.name,
            "color": p.color,
            "size": p.size,
            "qty": p.qty,
            "category": category.name_ru if category else '',
            "section": category.name_ru if category else '',
            "url": url_for('product_page', product_id=p.id),
        })
    return render_template('search.html', query=query, results=results, count=len(results))

@app.route('/.well-known/acme-challenge/<path:filename>')
def letsencrypt_challenge(filename):
    acme_dir = os.path.join(app.root_path, '.well-known', 'acme-challenge')
    return send_from_directory(acme_dir, filename)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

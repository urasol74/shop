from flask import Flask, render_template, send_from_directory, abort, request, url_for
import os
import re
from models import db, Category, Product, init_app
from sqlalchemy import func, or_, and_

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

def save_notgender(products):
    notgender = []
    for p in products:
        if not p.gender:
            notgender.append({
                'art': p.art,
                'name': p.name,
                'category_id': p.category_id,
                'color': p.color,
                'size': p.size,
                'qty': p.qty,
                'old_price': p.old_price,
                'new_price': p.new_price,
                'sale': p.sale,
                'image': p.image,
                'season': p.season,
                'brand': p.brand
            })
    if notgender:
        with open('notgender.json', 'w', encoding='utf-8') as f:
            json.dump(notgender, f, ensure_ascii=False, indent=2)

def get_unique_categories_by_gender(gender, brand=None):
    query = Product.query.filter(func.lower(func.trim(Product.gender)) == gender.lower())
    if brand:
        query = query.filter(func.lower(func.trim(Product.brand)) == brand.lower())
    category_ids = query.with_entities(Product.category_id).distinct()
    categories = Category.query.filter(Category.id.in_(category_ids)).all()
    return [{'raw': c.name_ua, 'pretty': c.name_ru} for c in categories]

def get_underwear_categories_by_gender(gender):
    products = Product.query.filter(
        func.lower(func.trim(Product.gender)) == gender.lower(),
        func.lower(func.trim(Product.brand)) == 'undercolor'
    ).all()
    categories = sorted(set(p.name for p in products if p.name))
    return categories

def filter_and_sort_products(query):
    # Исключаем товары без гендера и с qty 0 или '-'
    products = [p for p in query if p.gender and str(p.qty).replace('.', '').isdigit() and float(p.qty) > 0]
    sort = request.args.get('sort', 'asc')
    reverse = sort == 'desc'
    products = sorted(
        products,
        key=lambda p: (p.new_price is None, p.new_price if p.new_price is not None else 0),
        reverse=reverse
    )
    return products, sort

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
    # Группировка по цвету и размерам для этого артикула
    same_art_products = Product.query.filter_by(art=product.art).all()
    color_size_map = {}
    for p in same_art_products:
        color = p.color.strip() if p.color else ''
        size = p.size.strip() if p.size else ''
        if color:
            if color not in color_size_map:
                color_size_map[color] = set()
            if size:
                color_size_map[color].add(size)
    color_size_list = [
        {"color": color, "sizes": sorted(list(sizes))}
        for color, sizes in color_size_map.items()
    ]
    color_size_list = sorted(color_size_list, key=lambda x: x['color'])
    back_url = request.args.get('back')
    if not back_url:
        back_url = f'/category/{category.name_ua if category else ""}'
    return render_template('product.html', product=product, section_verbose=category.name_ru if category else '', back_url=back_url, color_size_map=color_size_list)

@app.route('/search')
def search():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return render_template('search.html', query=query, results=[], count=0)
    words = query.split()
    q = Product.query
    for word in words:
        q = q.filter(
            or_(
                Product.art.ilike(f'%{word}%'),
                Product.name.ilike(f'%{word}%'),
                Product.color.ilike(f'%{word}%'),
                Product.size.ilike(f'%{word}%')
            )
        )
    products = q.all()
    results = []
    for p in products:
        category = Category.query.get(p.category_id)
        results.append({
            "id": p.id,  # добавляем id
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

@app.route('/women')
def women():
    categories = get_unique_categories_by_gender('жiн', brand='BENETTON')
    return render_template('sections.html', section_verbose='Женщина', categories=categories, section_url='women_category', back_url='/')

@app.route('/men')
def men():
    categories = get_unique_categories_by_gender('чол', brand='BENETTON')
    return render_template('sections.html', section_verbose='Мужчина', categories=categories, section_url='men_category', back_url='/')

@app.route('/kids')
def kids():
    girls = get_unique_categories_by_gender('дiвч', brand='BEN.012')
    boys = get_unique_categories_by_gender('хлопч', brand='BEN.012')
    # Удаляем дубли по raw
    seen = set()
    unique_categories = []
    for c in girls + boys:
        if c['raw'] not in seen:
            unique_categories.append(c)
            seen.add(c['raw'])
    return render_template('sections.html', section_verbose='Дети', categories=unique_categories, section_url='kids_category', back_url='/')

@app.route('/women/category/<category_name>')
def women_category(category_name):
    query = Product.query.filter(func.lower(func.trim(Product.gender)) == 'жiн', Product.name == category_name).all()
    products, sort = filter_and_sort_products(query)
    # Оставляем только по одному товару на артикул
    unique_products = {}
    for p in products:
        if p.art not in unique_products:
            unique_products[p.art] = p
    products = list(unique_products.values())
    return render_template('products.html', products=products, category=category_name, section_verbose=f'Женщина — {category_name}', back_url='/women', genders=None, sort=sort)

@app.route('/men/category/<category_name>')
def men_category(category_name):
    query = Product.query.filter(func.lower(func.trim(Product.gender)) == 'чол', Product.name == category_name).all()
    products, sort = filter_and_sort_products(query)
    # Оставляем только по одному товару на артикул
    unique_products = {}
    for p in products:
        if p.art not in unique_products:
            unique_products[p.art] = p
    products = list(unique_products.values())
    return render_template('products.html', products=products, category=category_name, section_verbose=f'Мужчина — {category_name}', back_url='/men', genders=None, sort=sort)

@app.route('/kids/category/<category_name>')
def kids_category(category_name):
    query = Product.query.filter(Product.gender.in_(['дiвч', 'хлопч']), Product.name == category_name).all()
    products, sort = filter_and_sort_products(query)
    # Оставляем только по одному товару на артикул
    unique_products = {}
    for p in products:
        if p.art not in unique_products:
            unique_products[p.art] = p
    products = list(unique_products.values())
    # Определяем, какие гендеры есть среди товаров
    genders_present = sorted(set(p.gender for p in products))
    genders_map = {'дiвч': 'Девочка', 'хлопч': 'Мальчик'}
    genders = [genders_map[g] for g in genders_present if g in genders_map]
    return render_template('products.html', products=products, category=category_name, section_verbose=f'Дети — {category_name}', back_url='/kids', genders=genders if len(genders) > 0 else None, sort=sort)

@app.route('/underwear')
def underwear():
    return render_template('underwear.html')

@app.route('/underwear/underwear-woman')
def underwear_woman():
    categories = get_underwear_categories_by_gender('жiн')
    categories_list = [{'raw': c, 'pretty': c.capitalize()} for c in categories]
    return render_template('sections.html', section_verbose='Бельё — Женщина', categories=categories_list, section_url='underwear_woman_category', back_url='/underwear')

@app.route('/underwear/underwear-men')
def underwear_men():
    categories = get_underwear_categories_by_gender('чол')
    categories_list = [{'raw': c, 'pretty': c.capitalize()} for c in categories]
    return render_template('sections.html', section_verbose='Бельё — Мужчина', categories=categories_list, section_url='underwear_men_category', back_url='/underwear')

@app.route('/underwear/underwear-boy')
def underwear_boy():
    categories = get_underwear_categories_by_gender('хлопч')
    categories_list = [{'raw': c, 'pretty': c.capitalize()} for c in categories]
    return render_template('sections.html', section_verbose='Бельё — Мальчик', categories=categories_list, section_url='underwear_boy_category', back_url='/underwear')

@app.route('/underwear/underwear-girl')
def underwear_girl():
    categories = get_underwear_categories_by_gender('дiвч')
    categories_list = [{'raw': c, 'pretty': c.capitalize()} for c in categories]
    return render_template('sections.html', section_verbose='Бельё — Девочка', categories=categories_list, section_url='underwear_girl_category', back_url='/underwear')

@app.route('/underwear/underwear-woman/category/<category_name>')
def underwear_woman_category(category_name):
    query = Product.query.filter(
        func.lower(func.trim(Product.gender)) == 'жiн',
        func.lower(func.trim(Product.brand)) == 'undercolor',
        Product.name == category_name
    ).all()
    products, sort = filter_and_sort_products(query)
    # Оставляем только по одному товару на артикул
    unique_products = {}
    for p in products:
        if p.art not in unique_products:
            unique_products[p.art] = p
    products = list(unique_products.values())
    return render_template('products.html', products=products, category=category_name, section_verbose=f'Бельё — Женщина — {category_name}', back_url='/underwear/underwear-woman', genders=None, sort=sort)

@app.route('/underwear/underwear-men/category/<category_name>')
def underwear_men_category(category_name):
    query = Product.query.filter(
        func.lower(func.trim(Product.gender)) == 'чол',
        func.lower(func.trim(Product.brand)) == 'undercolor',
        Product.name == category_name
    ).all()
    products, sort = filter_and_sort_products(query)
    # Оставляем только по одному товару на артикул
    unique_products = {}
    for p in products:
        if p.art not in unique_products:
            unique_products[p.art] = p
    products = list(unique_products.values())
    return render_template('products.html', products=products, category=category_name, section_verbose=f'Бельё — Мужчина — {category_name}', back_url='/underwear/underwear-men', genders=None, sort=sort)

@app.route('/underwear/underwear-boy/category/<category_name>')
def underwear_boy_category(category_name):
    query = Product.query.filter(
        func.lower(func.trim(Product.gender)) == 'хлопч',
        func.lower(func.trim(Product.brand)) == 'undercolor',
        Product.name == category_name
    ).all()
    products, sort = filter_and_sort_products(query)
    # Оставляем только по одному товару на артикул
    unique_products = {}
    for p in products:
        if p.art not in unique_products:
            unique_products[p.art] = p
    products = list(unique_products.values())
    return render_template('products.html', products=products, category=category_name, section_verbose=f'Бельё — Мальчик — {category_name}', back_url='/underwear/underwear-boy', genders=None, sort=sort)

@app.route('/underwear/underwear-girl/category/<category_name>')
def underwear_girl_category(category_name):
    query = Product.query.filter(
        func.lower(func.trim(Product.gender)) == 'дiвч',
        func.lower(func.trim(Product.brand)) == 'undercolor',
        Product.name == category_name
    ).all()
    products, sort = filter_and_sort_products(query)
    # Оставляем только по одному товару на артикул
    unique_products = {}
    for p in products:
        if p.art not in unique_products:
            unique_products[p.art] = p
    products = list(unique_products.values())
    return render_template('products.html', products=products, category=category_name, section_verbose=f'Бельё — Девочка — {category_name}', back_url='/underwear/underwear-girl', genders=None, sort=sort)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

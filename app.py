from flask import Flask, render_template, send_from_directory, abort, request, url_for, jsonify
import os
import re
from models import db, Category, Product, init_app
from sqlalchemy import func, or_, and_
from flask_cors import CORS

# Загружаем словарь красивых названий категорий
import json
with open(os.path.join('static', 'sections-book.json'), encoding='utf-8') as f:
    SECTIONS_BOOK = json.load(f)

def get_pretty_category(category):
    if not category:
        return ''
    return SECTIONS_BOOK.get(category.upper().strip(), category.capitalize())

def sort_product_images(images, art):
    """
    Сортирует изображения товара так, чтобы основной файл (без суффикса) был первым,
    а дополнительные файлы (-1, -2, -3, -4) шли после него
    """
    def sort_key(filename):
        # Если файл точно соответствует артикулу (без суффикса), ставим его первым
        if filename == f"{art}.jpg" or filename == f"{art}.jpeg" or filename == f"{art}.png" or filename == f"{art}.webp":
            return (0, filename)
        # Остальные файлы сортируем по алфавиту
        return (1, filename)
    
    return sorted(images, key=sort_key)

import shutil
# --- Автоматическое обновление der.xlsx при запуске ---
src = "/home/ubuntu/bot_art/data/Новый.xlsx"
dst = os.path.join('data', 'der.xlsx')
os.makedirs(os.path.dirname(dst), exist_ok=True)
shutil.copyfile(src, dst)

app = Flask(__name__)
CORS(app)
import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'shop.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
init_app(app)

@app.template_filter('basename')
def basename_filter(path):
    return os.path.basename(path)

@app.template_filter('image_name')
def image_name_filter(art):
    """
    Для детских товаров (с .K) возвращает имя картинки без .K
    """
    if art and str(art).endswith('.K'):
        return str(art).replace('.K', '') + '.jpg'
    return str(art) + '.jpg' if art else ''

@app.template_filter('format_price')
def format_price_filter(price):
    """
    Форматирует цену: убирает точку из тысяч и убирает .0
    Примеры: 1.219 -> 1219, 849.0 -> 849, 1.529 -> 1529
    """
    if price is None:
        return ''
    
    # Преобразуем в строку
    price_str = str(price)
    
    # Отладочная информация
    app.logger.info(f"DEBUG: Original price: {price}, type: {type(price)}")
    app.logger.info(f"DEBUG: Price string: {price_str}")
    
    # Убираем .0 если есть
    if price_str.endswith('.0'):
        price_str = price_str.replace('.0', '')
        app.logger.info(f"DEBUG: Removed .0: {price_str}")
    
    # Убираем точку (разделитель тысяч)
    if '.' in price_str:
        parts = price_str.split('.')
        app.logger.info(f"DEBUG: Parts after split: {parts}")
        price_str = parts[0] + parts[1]
        app.logger.info(f"DEBUG: Removed dot separator: {price_str}")
    
    app.logger.info(f"DEBUG: Final result: {price_str}")
    return price_str

@app.template_filter('format_sale')
def format_sale_filter(sale):
    """
    Форматирует скидку: убирает .0
    Примеры: 50.0 -> 50, 25.0 -> 25
    """
    if sale is None:
        return ''
    
    # Преобразуем в строку и убираем .0
    sale_str = str(sale)
    if sale_str.endswith('.0'):
        sale_str = sale_str.replace('.0', '')
    
    return sale_str

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
    # Маппинг для соответствия значений пола
    gender_mapping = {
        'жін': 'жiн',
        'чол': 'чол',
        'діти': 'дiвч',
        'дівч': 'дiвч',
        'хлопч': 'хлопч'
    }
    
    # Получаем правильное значение пола
    target_gender = gender_mapping.get(gender.lower(), gender)
    
    # Базовый запрос
    query = Product.query
    
    # Логика для товаров по полу
    if target_gender in ['жiн', 'чол']:
        # Для взрослых категорий (женщины/мужчины)
        # Включаем товары с соответствующим полом И унісекс товары
        query = query.filter(
            or_(
                Product.gender == target_gender,
                Product.gender == 'унісекс'
            )
        )
    elif target_gender in ['дiвч', 'хлопч']:
        # Для детских категорий (девочки/мальчики)
        # Включаем товары с соответствующим полом И товары с полом 'дит'
        query = query.filter(
            or_(
                Product.gender == target_gender,
                Product.gender == 'дит'
            )
        )
    else:
        # Для остальных случаев используем точное совпадение
        query = query.filter(Product.gender == target_gender)
    
    if brand:
        query = query.filter(func.lower(func.trim(Product.brand)) == brand.lower())
    
    # Получаем уникальные категории из поля cat
    categories = query.with_entities(Product.cat).distinct()
    category_list = [cat[0] for cat in categories if cat[0]]
    
    # Сортируем категории
    sorted_categories = sorted(category_list)
    
    return [{'raw': cat, 'pretty': get_pretty_category(cat)} for cat in sorted_categories]

def get_underwear_categories_by_gender(gender):
    # Базовый запрос
    query = Product.query.filter(
        func.lower(func.trim(Product.brand)) == 'undercolor'
    )
    
    # Логика для товаров по полу в белье
    if gender in ['жiн', 'чол']:
        # Для взрослых категорий (женщины/мужчины)
        # Включаем товары с соответствующим полом И унісекс товары
        query = query.filter(
            or_(
                func.lower(func.trim(Product.gender)) == gender.lower(),
                Product.gender == 'унісекс'
            )
        )
    elif gender in ['дiвч', 'хлопч']:
        # Для детских категорий (девочки/мальчики)
        # Включаем товары с соответствующим полом И товары с полом 'дит'
        query = query.filter(
            or_(
                func.lower(func.trim(Product.gender)) == gender.lower(),
                Product.gender == 'дит'
            )
        )
    else:
        # Для остальных случаев используем точное совпадение
        query = query.filter(func.lower(func.trim(Product.gender)) == gender.lower())
    
    # Получаем уникальные категории из поля cat
    categories = query.with_entities(Product.cat).distinct()
    category_list = [cat[0] for cat in categories if cat[0]]
    return sorted(category_list)

def parse_price_for_sorting(price):
    """
    Сортирует по числовому значению после удаления точки и .0
    Примеры: 849.0 -> 849, 1.249 -> 1249
    """
    if price is None:
        return 0
    
    price_str = str(price)
    
    # Отладочная информация
    app.logger.info(f"SORTING DEBUG: Original price: {price}, type: {type(price)}")
    app.logger.info(f"SORTING DEBUG: Price string: {price_str}")
    
    # Убираем .0 если есть
    if price_str.endswith('.0'):
        price_str = price_str.replace('.0', '')
        app.logger.info(f"SORTING DEBUG: Removed .0: {price_str}")
    
    # Убираем точку (разделитель тысяч)
    if '.' in price_str:
        parts = price_str.split('.')
        app.logger.info(f"SORTING DEBUG: Parts after split: {parts}")
        price_str = parts[0] + parts[1]
        app.logger.info(f"SORTING DEBUG: Removed dot separator: {price_str}")
    
    # Преобразуем в число для сортировки
    try:
        numeric_value = float(price_str)
        app.logger.info(f"SORTING DEBUG: Final result: {numeric_value}")
        return numeric_value
    except ValueError:
        app.logger.info(f"SORTING DEBUG: ValueError for price_str: {price_str}")
        return 0

def filter_and_sort_products(query):
    # Исключаем товары без гендера и с qty 0 или '-'
    products = [p for p in query if p.gender and str(p.qty).replace('.', '').isdigit() and float(p.qty) > 0]
    sort = request.args.get('sort', 'asc')
    reverse = sort == 'desc'
    products = sorted(
        products,
        key=lambda p: (p.new_price is None, parse_price_for_sorting(p.new_price)),
        reverse=reverse
    )
    return products, sort

def get_unique_seasons():
    """
    Получает уникальные сезоны из базы данных
    Объединяет 2024 осінь-зима и 2025 весна-літо в 2025 весна-літо
    """
    seasons = db.session.query(Product.season).distinct().filter(
        Product.season.isnot(None),
        Product.season != ''
    ).order_by(Product.season).all()
    
    # Получаем все сезоны
    all_seasons = [season[0] for season in seasons if season[0]]
    
    # Объединяем 2024 осінь-зима и 2025 весна-літо в 2025 весна-літо
    processed_seasons = []
    for season in all_seasons:
        if season in ['2024 осінь-зима', '2025 весна-літо']:
            if '2025 весна-літо' not in processed_seasons:
                processed_seasons.append('2025 весна-літо')
        else:
            if season not in processed_seasons:
                processed_seasons.append(season)
    
    return processed_seasons

# Новая страница
# Все товары
@app.route('/api/products')
def api_products():
    section = request.args.get('section')
    category = request.args.get('category')
    gender = request.args.get('gender')
    brand = request.args.get('brand')
    query = Product.query
    if section == 'women':
        query = query.filter(func.lower(func.trim(Product.gender)) == 'жiн', Product.name == category)
    elif section == 'men':
        query = query.filter(func.lower(func.trim(Product.gender)) == 'чол', Product.name == category)
    elif section == 'kids':
        query = query.filter(Product.gender.in_(['дiвч', 'хлопч']), Product.name == category)
    elif section == 'underwear' and gender and brand:
        query = query.filter(
            func.lower(func.trim(Product.gender)) == gender.lower(),
            func.lower(func.trim(Product.brand)) == brand.lower(),
            Product.name == category
        )
    products = query.all()
    result = []
    for p in products:
        result.append({
            'id': p.id,
            'art': p.art,
            'name': p.name,
            'color': p.color,
            'size': p.size,
            'qty': p.qty,
            'price': p.new_price,
            'old_price': p.old_price,
            'sale': p.sale,
            'image': p.image,
            'gender': p.gender,
            'season': p.season,
            'brand': p.brand,
        })
    return jsonify(result)

# Страница категорий
@app.route('/api/categories')
def api_categories():
    section = request.args.get('section')
    if section == 'women':
        categories = get_unique_categories_by_gender('жiн', brand='BENETTON')
    elif section == 'men':
        categories = get_unique_categories_by_gender('чол', brand='BENETTON')
    elif section == 'kids':
        girls = get_unique_categories_by_gender('дiвч', brand='BEN.012')
        boys = get_unique_categories_by_gender('хлопч', brand='BEN.012')
        # Удаляем дубли по raw
        seen = set()
        unique_categories = []
        for c in girls + boys:
            if c['raw'] not in seen:
                unique_categories.append(c)
                seen.add(c['raw'])
        categories = unique_categories
    else:
        cats = Category.query.order_by(Category.name_ru).all()
        categories = [{"raw": c.name_ua, "pretty": c.name_ru} for c in cats]
    return jsonify(categories)

@app.route('/api/product/<int:product_id>')
def api_product(product_id):
    product = Product.query.get_or_404(product_id)
    category = Category.query.get(product.category_id)
    # Группировка по цвету и размерам для этого артикула
    same_art_products = Product.query.filter_by(art=product.art).all()
    color_size_map = {}
    for p in same_art_products:
        if p.qty and str(p.qty).replace('.', '').isdigit() and float(p.qty) > 0:
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

    # Картинки
    import os
    pic_dir = os.path.join(app.root_path, 'static', 'pic', 'list')
    images = []
    if os.path.isdir(pic_dir):
        # Для детских товаров (с .K) ищем картинки без .K
        search_art = product.art.replace('.K', '') if product.art.endswith('.K') else product.art
        images = [f for f in os.listdir(pic_dir) if f.startswith(search_art) and f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        images = sort_product_images(images, search_art)

    return jsonify({
        "id": product.id,
        "art": product.art,
        "name": product.name,
        "category": category.name_ru if category else '',
        "old_price": product.old_price,
        "new_price": product.new_price,
        "sale": product.sale,
        "color_size_map": color_size_list,
        "images": images,
    })

@app.route('/api/underwear-categories')
def api_underwear_categories():
    gender = request.args.get('gender')
    categories = get_underwear_categories_by_gender(gender)
    categories_list = [{'raw': c, 'pretty': get_pretty_category(c)} for c in categories]
    return jsonify(categories_list)

# Старая страница
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
    query = Product.query.filter_by(category_id=category.id).all()
    products, sort = filter_and_sort_products(query)
    return render_template(
        'products.html',
        products=products,
        category=category.name_ru,
        section_verbose=category.name_ru,
        pretty_category=category.name_ru,
        back_url='/categories',
        sort=sort
    )

@app.route('/product/<int:product_id>')
def product_page(product_id):
    product = Product.query.get_or_404(product_id)
    category = Category.query.get(product.category_id)
    # Группировка по цвету и размерам для этого артикула
    same_art_products = Product.query.filter_by(art=product.art).all()
    color_size_map = {}
    for p in same_art_products:
        # Исключаем товары с qty 0 или '-'
        if p.qty and str(p.qty).replace('.', '').isdigit() and float(p.qty) > 0:
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

    # --- ДОБАВЬ ЭТО ---
    pic_dir = os.path.join(app.root_path, 'static', 'pic', 'list')
    images = []
    if os.path.isdir(pic_dir):
        # Для детских товаров (с .K) ищем картинки без .K
        search_art = product.art.replace('.K', '') if product.art.endswith('.K') else product.art
        images = [f for f in os.listdir(pic_dir) if f.startswith(search_art) and f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        images = sort_product_images(images, search_art)
    # --- КОНЕЦ ---

    return render_template(
        'product.html',
        product=product,
        section_verbose=category.name_ru if category else '',
        back_url=back_url,
        color_size_map=color_size_list,
        product_images=images  # <-- ВАЖНО!
    )

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
    # Ищем товары по категории (включая унісекс)
    query = Product.query.filter(
        or_(
            func.lower(func.trim(Product.gender)) == 'жiн',
            Product.gender == 'унісекс'
        ),
        Product.cat == category_name
    ).all()
    products, sort = filter_and_sort_products(query)
    # Оставляем только по одному товару на артикул
    unique_products = {}
    for p in products:
        if p.art not in unique_products:
            unique_products[p.art] = p
    products = list(unique_products.values())
    # Получаем русское название категории
    category_ru = get_pretty_category(category_name)
    seasons = get_unique_seasons()
    return render_template('products.html', products=products, category=category_ru, section_verbose=f'Женщина {category_ru}', back_url='/women', genders=None, sort=sort, seasons=seasons)

@app.route('/men/category/<category_name>')
def men_category(category_name):
    # Ищем товары по категории (включая унісекс)
    query = Product.query.filter(
        or_(
            func.lower(func.trim(Product.gender)) == 'чол',
            Product.gender == 'унісекс'
        ),
        Product.cat == category_name
    ).all()
    products, sort = filter_and_sort_products(query)
    # Оставляем только по одному товару на артикул
    unique_products = {}
    for p in products:
        if p.art not in unique_products:
            unique_products[p.art] = p
    products = list(unique_products.values())
    category_ru = get_pretty_category(category_name)
    seasons = get_unique_seasons()
    return render_template('products.html', products=products, category=category_ru, section_verbose=f'Мужчина {category_ru}', back_url='/men', genders=None, sort=sort, seasons=seasons)

@app.route('/kids/category/<category_name>')
def kids_category(category_name):
    # Ищем товары по категории (включая товары с полом 'дит')
    query = Product.query.filter(
        or_(
            Product.gender.in_(['дiвч', 'хлопч']),
            Product.gender == 'дит'
        ),
        Product.cat == category_name
    ).all()
    products, sort = filter_and_sort_products(query)
    # Оставляем только по одному товару на артикул
    unique_products = {}
    for p in products:
        if p.art not in unique_products:
            unique_products[p.art] = p
    products = list(unique_products.values())
    # Для детских категорий всегда показываем фильтр "Девочка" и "Мальчик"
    genders = ['Девочка', 'Мальчик']
    
    # Для детских категорий всегда показываем фильтр, даже если есть только товары 'дит'
    if not genders:
        genders = ['Девочка', 'Мальчик']
    
    category_ru = get_pretty_category(category_name)
    seasons = get_unique_seasons()
    return render_template('products.html', products=products, category=category_ru, section_verbose=f'Дети {category_ru}', back_url='/kids', genders=genders, sort=sort, seasons=seasons)

@app.route('/underwear')
def underwear():
    return render_template('underwear.html')

@app.route('/underwear/underwear-woman')
def underwear_woman():
    categories = get_underwear_categories_by_gender('жiн')
    categories_list = [{'raw': c, 'pretty': get_pretty_category(c)} for c in categories]
    return render_template('sections.html', section_verbose='Бельё — Женщина', categories=categories_list, section_url='underwear_woman_category', back_url='/underwear')

@app.route('/underwear/underwear-men')
def underwear_men():
    categories = get_underwear_categories_by_gender('чол')
    categories_list = [{'raw': c, 'pretty': get_pretty_category(c)} for c in categories]
    return render_template('sections.html', section_verbose='Бельё — Мужчина', categories=categories_list, section_url='underwear_men_category', back_url='/underwear')

@app.route('/underwear/underwear-boy')
def underwear_boy():
    categories = get_underwear_categories_by_gender('хлопч')
    categories_list = [{'raw': c, 'pretty': get_pretty_category(c)} for c in categories]
    return render_template('sections.html', section_verbose='Бельё — Мальчик', categories=categories_list, section_url='underwear_boy_category', back_url='/underwear')

@app.route('/underwear/underwear-girl')
def underwear_girl():
    categories = get_underwear_categories_by_gender('дiвч')
    categories_list = [{'raw': c, 'pretty': get_pretty_category(c)} for c in categories]
    return render_template('sections.html', section_verbose='Бельё — Девочка', categories=categories_list, section_url='underwear_girl_category', back_url='/underwear')

def get_underwear_products_by_gender_and_category(gender, category_name, section_name, back_url):
    """
    Общая функция для получения товаров белья по полу и категории
    """
    # Базовый запрос
    query = Product.query.filter(
        func.lower(func.trim(Product.brand)) == 'undercolor',
        Product.cat == category_name
    )
    
    # Логика для товаров по полу в белье
    if gender in ['жiн', 'чол']:
        # Для взрослых категорий (женщины/мужчины)
        # Включаем товары с соответствующим полом И унісекс товары
        query = query.filter(
            or_(
                func.lower(func.trim(Product.gender)) == gender,
                Product.gender == 'унісекс'
            )
        )
    elif gender in ['дiвч', 'хлопч']:
        # Для детских категорий (девочки/мальчики)
        # Включаем товары с соответствующим полом И товары с полом 'дит'
        query = query.filter(
            or_(
                func.lower(func.trim(Product.gender)) == gender,
                Product.gender == 'дит'
            )
        )
    else:
        # Для остальных случаев используем точное совпадение
        query = query.filter(func.lower(func.trim(Product.gender)) == gender)
    
    products = query.all()
    # Фильтруем товары (исключаем товары без гендера и с qty 0)
    products = [p for p in products if p.gender and str(p.qty).replace('.', '').isdigit() and float(p.qty) > 0]
    # Оставляем только по одному товару на артикул
    unique_products = {}
    for p in products:
        if p.art not in unique_products:
            unique_products[p.art] = p
    products = list(unique_products.values())
    # Сортируем по цене
    sort = 'asc'  # По умолчанию
    products = sorted(products, key=lambda p: (p.new_price is None, p.new_price or 0))
    category_ru = get_pretty_category(category_name)
    seasons = get_unique_seasons()
    return render_template('products.html', products=products, category=category_ru, section_verbose=f'Бельё {section_name} {category_ru}', back_url=back_url, genders=None, sort=sort, seasons=seasons)

@app.route('/underwear/underwear-woman/category/<category_name>')
def underwear_woman_category(category_name):
    return get_underwear_products_by_gender_and_category('жiн', category_name, 'Женщина', '/underwear/underwear-woman')

@app.route('/underwear/underwear-men/category/<category_name>')
def underwear_men_category(category_name):
    return get_underwear_products_by_gender_and_category('чол', category_name, 'Мужчина', '/underwear/underwear-men')

@app.route('/underwear/underwear-boy/category/<category_name>')
def underwear_boy_category(category_name):
    return get_underwear_products_by_gender_and_category('хлопч', category_name, 'Мальчик', '/underwear/underwear-boy')

@app.route('/underwear/underwear-girl/category/<category_name>')
def underwear_girl_category(category_name):
    return get_underwear_products_by_gender_and_category('дiвч', category_name, 'Девочка', '/underwear/underwear-girl')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

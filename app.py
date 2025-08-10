from flask import Flask, render_template, send_from_directory, abort, request, url_for, jsonify, session, redirect
from urllib.parse import parse_qsl, quote_plus
import os
import re
import hashlib
import hmac
import time
import json
from datetime import datetime
import shutil
from models import db, Category, Product, DerCategory, DerProduct, DerVariant, init_app
import sqlite3
from types import SimpleNamespace
from sqlalchemy import text
from sqlalchemy import func, or_, and_, exists
from flask_cors import CORS

# Загружаем словарь красивых названий категорий
import json
with open(os.path.join('static', 'sections-book.json'), encoding='utf-8') as f:
    SECTIONS_BOOK = json.load(f)

# Токен Telegram бота для проверки подписи
TELEGRAM_BOT_TOKEN = '7826392136:AAHtOUoqBz-95MprvAg5xw68jiOlwTqsHgU'

# ID администраторов (можно несколько)
ADMIN_USER_IDS = {1023307031, 631457244}

# Директория для устойчивого хранения данных (не очищается при перезапуске)
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, 'client.json')
LEGACY_USERS_FILE = os.path.join('static', 'client.json')
KNOWN_IDS_FILE = os.path.join(DATA_DIR, 'known_ids.json')
APPEND_LOG_FILE = os.path.join(BASE_DIR, 'static', 'client..json')  # append-only NDJSON лог

def append_user_id_log_entry(user_id: int, is_admin: bool) -> None:
    """Append-only лог: пишет одну JSON-строку с временем и ID (и признаком админа).

    Формат строки (NDJSON): {"timestamp": ISO8601, "id": int, "admin": bool}
    """
    try:
        # Гарантируем наличие директории
        os.makedirs(os.path.dirname(APPEND_LOG_FILE), exist_ok=True)

        entry = {
            'timestamp': datetime.now().isoformat(),
            'id': int(user_id),
            'admin': bool(is_admin),
        }
        # Открываем только в режиме добавления; никакой перезаписи
        with open(APPEND_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"Ошибка append-логирования ID: {e}")

def read_append_log() -> list[dict]:
    """Читает append-only NDJSON лог и возвращает список событий.

    Каждая строка — отдельный JSON-объект с ключами: timestamp, id, admin.
    Ломаные строки/ошибки парсинга игнорируются.
    """
    events: list[dict] = []
    try:
        if not os.path.exists(APPEND_LOG_FILE):
            return events
        with open(APPEND_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                    # Минимальная валидация
                    if isinstance(evt, dict) and 'id' in evt and 'timestamp' in evt:
                        events.append(evt)
                except Exception:
                    # пропускаем битые строки
                    continue
    except Exception as e:
        print(f"Ошибка чтения append-лога: {e}")
    return events

def aggregate_log_stats(events: list[dict]) -> dict:
    """Агрегирует события лога по пользователям."""
    per_user: dict[str, dict] = {}
    for evt in events:
        uid_str = str(evt.get('id'))
        ts = evt.get('timestamp') or ''
        is_admin = bool(evt.get('admin'))
        info = per_user.get(uid_str)
        if info is None:
            per_user[uid_str] = {
                'id': int(uid_str) if uid_str.isdigit() else uid_str,
                'admin': is_admin,
                'count': 1,
                'first_seen': ts,
                'last_seen': ts,
            }
        else:
            info['count'] += 1
            # Обновляем признак админа, если хоть раз был true
            info['admin'] = info['admin'] or is_admin
            # ISO-строки сравнимы лексикографически
            if ts and (not info['first_seen'] or ts < info['first_seen']):
                info['first_seen'] = ts
            if ts and (not info['last_seen'] or ts > info['last_seen']):
                info['last_seen'] = ts
    users_list = list(per_user.values())
    users_list.sort(key=lambda u: (u['last_seen'] or ''), reverse=True)
    admins_unique = sum(1 for u in users_list if u.get('admin'))
    return {
        'events_total': len(events),
        'users_total': len(users_list),
        'admins_total': admins_unique,
        'non_admins_total': max(0, len(users_list) - admins_unique),
        'users': users_list,
    }

## Маршруты объявляются ниже, после инициализации app

def _ensure_migration_of_legacy_users_file():
    """Мигрирует данные из legacy файла и объединяет их с существующими (выполняется только один раз)"""
    try:
        # Проверяем, была ли уже выполнена миграция
        migration_flag_file = os.path.join(DATA_DIR, 'migration_completed.flag')
        if os.path.exists(migration_flag_file):
            print("Миграция уже выполнена, пропускаем")
            return
            
        if os.path.exists(LEGACY_USERS_FILE):
            print("Выполняем миграцию legacy данных...")
            # Загружаем legacy данные
            with open(LEGACY_USERS_FILE, 'r', encoding='utf-8') as f:
                legacy_data = json.load(f)
            
            # Загружаем текущие данные
            current_data = load_users_data()
            
            # Объединяем данные, сохраняя историю
            if 'users' in legacy_data:
                for user_id, legacy_user in legacy_data['users'].items():
                    if user_id not in current_data['users']:
                        # Новый пользователь из legacy - конвертируем в новый формат
                        current_data['users'][user_id] = {
                            'id': int(user_id),
                            'login_time': legacy_user.get('login_time', datetime.now().isoformat()),
                            'first_visit': legacy_user.get('first_visit', legacy_user.get('login_time', datetime.now().isoformat())),
                            'visit_history': [legacy_user.get('login_time', datetime.now().isoformat())]
                        }
                    else:
                        # Пользователь уже существует - обновляем историю
                        current_user = current_data['users'][user_id]
                        if 'visit_history' not in current_user:
                            current_user['visit_history'] = []
                        
                        # Добавляем legacy время входа в историю
                        legacy_time = legacy_user.get('login_time')
                        if legacy_time and legacy_time not in current_user['visit_history']:
                            current_user['visit_history'].append(legacy_time)
                            current_user['visit_history'].sort()  # Сортируем по времени
            
            # Сохраняем объединенные данные
            save_users_data(current_data)
            
            # Создаем backup legacy файла
            backup_file = LEGACY_USERS_FILE + '.backup.' + datetime.now().strftime('%Y%m%d_%H%M%S')
            shutil.copyfile(LEGACY_USERS_FILE, backup_file)
            print(f"Legacy data migrated and backed up to {backup_file}")
            
            # Создаем флаг завершения миграции
            with open(migration_flag_file, 'w') as f:
                f.write('migration_completed')
            print("Миграция завершена успешно")
            
    except Exception as e:
        print(f"Migration warning (client.json): {e}")

# Выполняем миграцию только при первом запуске
_ensure_migration_of_legacy_users_file()

def verify_telegram_data(init_data: str) -> bool:
    """
    Проверяет подпись данных от Telegram WebApp согласно официальной спецификации.
    Алгоритм: https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    try:
        # Разбираем query-string надёжно и безопасно
        params_list = parse_qsl(init_data, keep_blank_values=True)
        params = dict(params_list)

        received_hash = params.pop('hash', None)
        if not received_hash:
            return False

        # Формируем data_check_string из отсортированных key=value пар (кроме hash)
        data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(params.items()))

        # Секретный ключ: HMAC_SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=TELEGRAM_BOT_TOKEN.encode('utf-8'),
            digestmod=hashlib.sha256,
        ).digest()

        # Подпись данных: HMAC_SHA256(secret_key, data_check_string)
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode('utf-8'),
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(calculated_hash, received_hash)
    except Exception as e:
        print(f"Ошибка проверки подписи Telegram: {e}")
        return False

def load_users_data():
    """Загружает данные о пользователях из устойчивого JSON файла"""
    try:
        if os.path.exists(USERS_FILE):
            print(f"Загружаем данные из основного файла {USERS_FILE}")
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Загружено {len(data.get('users', {}))} пользователей из основного файла")
                return data
        # fallback на legacy расположение
        if os.path.exists(LEGACY_USERS_FILE):
            print(f"Загружаем данные из legacy файла {LEGACY_USERS_FILE}")
            with open(LEGACY_USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Загружено {len(data.get('users', {}))} пользователей из legacy файла")
                return data
        print("Файлы данных не найдены, возвращаем пустую структуру")
        return {"users": {}, "last_updated": datetime.now().isoformat()}
    except Exception as e:
        print(f"Ошибка загрузки данных пользователей: {e}")
        return {"users": {}, "last_updated": datetime.now().isoformat()}

def save_users_data(data):
    """Сохраняет данные о пользователях в устойчивый JSON файл"""
    try:
        print(f"Сохранение данных пользователей в {USERS_FILE}")
        print(f"Количество пользователей для сохранения: {len(data.get('users', {}))}")
        for uid in data.get('users', {}):
            print(f"  Сохраняем пользователя {uid}")
        
        data['last_updated'] = datetime.now().isoformat()
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Данные успешно сохранены")
        return True
    except Exception as e:
        print(f"Ошибка сохранения данных пользователей: {e}")
        return False

def load_known_ids():
    try:
        if os.path.exists(KNOWN_IDS_FILE):
            with open(KNOWN_IDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"ids": []}
    except Exception as e:
        print(f"Ошибка загрузки known_ids: {e}")
        return {"ids": []}

def save_known_ids(ids_state):
    try:
        with open(KNOWN_IDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ids_state, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Ошибка сохранения known_ids: {e}")
        return False

def add_known_id(user_id: int):
    try:
        state = load_known_ids()
        ids = set(state.get('ids', []))
        ids.add(int(user_id))
        new_state = {"ids": sorted(ids)}
        save_known_ids(new_state)
    except Exception as e:
        print(f"Ошибка добавления ID в known_ids: {e}")

def update_user_activity(user_id, action, user_data=None):
    """Функция для сбора ID пользователей, времени входа и повторных посещений"""
    try:
        print(f"Обновление активности пользователя {user_id}")
        # Append-only лог всех посещений (админы и не админы)
        try:
            append_user_id_log_entry(user_id=user_id, is_admin=(int(user_id) in ADMIN_USER_IDS))
        except Exception as le:
            print(f"Лог ID (append) не записан: {le}")
        data = load_users_data()
        current_time = datetime.now().isoformat()
        
        print(f"Текущие данные: {len(data.get('users', {}))} пользователей")
        for uid in data.get('users', {}):
            print(f"  Пользователь {uid} в данных")
        
        if str(user_id) not in data['users']:
            # Новый пользователь - ID, время входа и первое посещение
            print(f"Добавляем нового пользователя {user_id}")
            data['users'][str(user_id)] = {
                'id': user_id,
                'login_time': current_time,
                'first_visit': current_time,
                'visit_history': [current_time]  # История посещений
            }
        else:
            # Существующий пользователь - обновляем время последнего входа и добавляем в историю
            print(f"Обновляем существующего пользователя {user_id}")
            user = data['users'][str(user_id)]
            user['login_time'] = current_time
            
            # Инициализируем историю посещений если её нет
            if 'visit_history' not in user:
                user['visit_history'] = [user.get('first_visit', current_time)]
            
            # Добавляем текущее посещение в историю
            user['visit_history'].append(current_time)
            
            # Ограничиваем историю последними 10 посещениями
            if len(user['visit_history']) > 10:
                user['visit_history'] = user['visit_history'][-10:]
        
        print(f"После обновления: {len(data.get('users', {}))} пользователей")
        for uid in data.get('users', {}):
            print(f"  Пользователь {uid} в данных")
        
        save_users_data(data)
        return True
    except Exception as e:
        print(f"Ошибка обновления активности пользователя: {e}")
        return False

def mark_user_logout(user_id):
    """Простая функция - пока не используется"""
    # Заморожена для дальнейшего использования
    return True

def get_pretty_category(category):
    if not category:
        return ''
    return SECTIONS_BOOK.get(category.upper().strip(), category.capitalize())

def der_get_categories_by_gender(
    gender_code: str,
    brand: str | None = None,
    include_unisex: bool = False,
    include_child: bool = False,
    season_label: str | None = None,
):
    q = db.session.query(DerCategory.name).join(DerProduct, DerProduct.category_id == DerCategory.id)
    g = func.lower(func.trim(DerProduct.gender))
    if include_unisex:
        q = q.filter(or_(g == gender_code, g == 'унісекс'))
    elif include_child:
        q = q.filter(or_(g == gender_code, g == 'дит'))
    else:
        q = q.filter(g == gender_code)
    if brand:
        q = q.filter(func.lower(func.trim(DerProduct.brand)) == brand.lower())
    # Фильтр по сезону (при заходе из кнопок на главной)
    if season_label:
        allowed = ['2024 осінь-зима', '2025 весна-літо'] if season_label == '2025 весна-літо' else [season_label]
        q = q.filter(DerProduct.season.in_(allowed))
    # only categories with stock > 0
    stock_exists = db.session.query(DerVariant.id).filter(and_(DerVariant.product_id == DerProduct.id, func.ifnull(DerVariant.stock, 0) > 0)).exists()
    q = q.filter(stock_exists)
    cats = [row[0] for row in q.distinct().order_by(DerCategory.name).all()]
    return [{'raw': c, 'pretty': get_pretty_category(c)} for c in cats]

def der_get_products_by_gender_and_category(category_name: str, gender_mode: str, brand: str | None = None):
    q = db.session.query(DerProduct, DerCategory).join(DerCategory, DerCategory.id == DerProduct.category_id)
    q = q.filter(DerCategory.name == category_name)
    g = func.lower(func.trim(DerProduct.gender))
    if gender_mode == 'women':
        q = q.filter(or_(g == 'жiн', g == 'унісекс'))
    elif gender_mode == 'men':
        q = q.filter(or_(g == 'чол', g == 'унісекс'))
    elif gender_mode == 'girl':
        q = q.filter(or_(g == 'дiвч', g == 'дит'))
    elif gender_mode == 'boy':
        q = q.filter(or_(g == 'хлопч', g == 'дит'))
    if brand:
        q = q.filter(func.lower(func.trim(DerProduct.brand)) == brand.lower())
    stock_exists = db.session.query(DerVariant.id).filter(and_(DerVariant.product_id == DerProduct.id, func.ifnull(DerVariant.stock, 0) > 0)).exists()
    q = q.filter(stock_exists)
    rows = q.all()
    products = []
    for prod, cat in rows:
        variants = DerVariant.query.filter_by(product_id=prod.id).all()
        total_stock = sum([(v.stock or 0) for v in variants])
        sale_prices, purchase_prices, discounts = [], [], []
        for v in variants:
            if v.sale_price:
                sale_prices.append(float(v.sale_price))
            if v.purchase_price:
                purchase_prices.append(float(v.purchase_price))
            if v.discount:
                discounts.append(float(v.discount))
        new_price = min(sale_prices) if sale_prices else None
        old_price = min(purchase_prices) if purchase_prices else None
        sale = max(discounts) if discounts else None
        products.append(SimpleNamespace(
            id=prod.id,
            art=prod.article,
            name=prod.name,
            cat=cat.name,
            category_id=None,
            color=None,
            size=None,
            qty=total_stock,
            old_price=old_price,
            new_price=new_price,
            sale=sale,
            image=None,
            season=prod.season,
            gender=prod.gender,
            brand=prod.brand,
            der=True,
        ))
    # Дедупликация: один товар на связку (артикул + сезон)
    unique_by_art_season = {}
    for p in products:
        key = (p.art, p.season)
        if key not in unique_by_art_season:
            unique_by_art_season[key] = p
        else:
            # Оставляем товар с большей доступностью или с меньшей ценой
            existing = unique_by_art_season[key]
            choose_current = False
            if (p.qty or 0) > (getattr(existing, 'qty', 0) or 0):
                choose_current = True
            elif (p.new_price or float('inf')) < (getattr(existing, 'new_price', float('inf')) or float('inf')):
                choose_current = True
            if choose_current:
                unique_by_art_season[key] = p
    return list(unique_by_art_season.values())

def der_get_underwear_categories_by_gender(gender_code: str, season_label: str | None = None):
    q = db.session.query(DerCategory.name).join(DerProduct, DerProduct.category_id == DerCategory.id)
    # Бренд белья
    q = q.filter(func.lower(func.trim(DerProduct.brand)) == 'undercolor')
    g = func.lower(func.trim(DerProduct.gender))
    # Логика пола
    if gender_code in ['жiн', 'чол']:
        q = q.filter(or_(g == gender_code, g == 'унісекс'))
    elif gender_code in ['дiвч', 'хлопч']:
        q = q.filter(or_(g == gender_code, g == 'дит'))
    else:
        q = q.filter(g == gender_code)
    # Фильтр по сезону
    if season_label:
        allowed = ['2024 осінь-зима', '2025 весна-літо'] if season_label == '2025 весна-літо' else [season_label]
        q = q.filter(DerProduct.season.in_(allowed))
    # Только категории, где есть остатки
    stock_exists = db.session.query(DerVariant.id).filter(and_(DerVariant.product_id == DerProduct.id, func.ifnull(DerVariant.stock, 0) > 0)).exists()
    q = q.filter(stock_exists)
    cats = [row[0] for row in q.distinct().order_by(DerCategory.name).all()]
    return [{'raw': c, 'pretty': get_pretty_category(c)} for c in cats]

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
app.config.update(
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_NAME='shop_session',
)
app.secret_key = 'your-secret-key-here-change-this-in-production'  # Секретный ключ для сессий
CORS(app)
import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'shop.db')}"
app.config['SQLALCHEMY_BINDS'] = {
    'der': f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'db-der.db')}"
}
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

def get_unique_categories_by_gender(gender, brand=None, season_label: str | None = None):
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
    
    # Фильтр по сезону (старая БД)
    if season_label:
        allowed = ['2024 осінь-зима', '2025 весна-літо'] if season_label == '2025 весна-літо' else [season_label]
        query = query.filter(Product.season.in_(allowed))

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

def get_available_seasons_for_products(products):
    """
    Возвращает список сезонов, присутствующих среди переданных товаров,
    с объединением '2024 осінь-зима' и '2025 весна-літо' в единый ярлык '2025 весна-літо'.
    Порядок — алфавитный по ярлыкам.
    """
    seasons_raw = [p.season for p in products if getattr(p, 'season', None)]
    labels = []
    for s in seasons_raw:
        if s in ['2024 осінь-зима', '2025 весна-літо']:
            label = '2025 весна-літо'
        else:
            label = s
        if label and label not in labels:
            labels.append(label)
    return sorted(labels)

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

@app.route('/api/auth/telegram', methods=['POST'])
def telegram_auth():
    """
    Авторизация пользователя через Telegram
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        user_id = data.get('user_id')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        username = data.get('username', '')
        init_data = data.get('init_data', '')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
        
        # Проверяем подпись данных от Telegram
        if init_data and not verify_telegram_data(init_data):
            return jsonify({'success': False, 'error': 'Invalid Telegram signature'}), 401
        
        # Создаем сессию для пользователя
        session['user_id'] = user_id
        session['first_name'] = first_name
        session['last_name'] = last_name
        session['username'] = username
        session['authenticated'] = True
        
        print(f"DEBUG: Сессия создана для пользователя {user_id}")
        print(f"DEBUG: Сессия после создания: {dict(session)}")
        
        # Отслеживаем активность пользователя
        user_data = {
            'first_name': first_name,
            'last_name': last_name,
            'username': username
        }
        update_user_activity(user_id, 'Авторизация через Telegram', user_data)

        # Сохраняем ID в устойчивом списке известных
        add_known_id(int(user_id))
        
        print(f"Пользователь {user_id} ({first_name} {last_name}) авторизован")
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'first_name': first_name,
            'last_name': last_name,
            'username': username
        })
        
    except Exception as e:
        print(f"Ошибка авторизации: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/status')
def auth_status():
    """
    Проверка статуса авторизации пользователя
    """
    if session.get('authenticated'):
        return jsonify({
            'authenticated': True,
            'user_id': session.get('user_id'),
            'first_name': session.get('first_name'),
            'last_name': session.get('last_name'),
            'username': session.get('username')
        })
    else:
        return jsonify({'authenticated': False})

@app.route('/api/auth/logout')
def logout():
    """
    Выход пользователя
    """
    try:
        user_id = session.get('user_id')
        if user_id:
            mark_user_logout(user_id)
        session.clear()
        return jsonify({'success': True, 'message': 'Выход выполнен успешно'})
    except Exception as e:
        print(f"Ошибка выхода: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/users')
def admin_users():
    """
    API для получения данных о пользователях (только для администратора)
    """
    try:
        if not session.get('authenticated'):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Проверяем, является ли пользователь администратором
        user_id = session.get('user_id')
        if user_id not in ADMIN_USER_IDS:
            return jsonify({'success': False, 'error': 'Access denied. Admin only.'}), 403
        
        print(f"Запрос данных пользователей от админа {user_id}")
        
        data = load_users_data()
        print(f"Загружено {len(data.get('users', {}))} пользователей")
        for user_id, user in data.get('users', {}).items():
            print(f"  Пользователь {user_id}: {user.get('id')}, посещений: {len(user.get('visit_history', []))}")
        
        # Возвращаем только пользователей в упрощенном формате
        return jsonify({
            'users': data.get('users', {}),
            'last_updated': data.get('last_updated', ''),
            'admin_id': session.get('user_id'),
            'total_users': len(data.get('users', {}))
        })
    except Exception as e:
        print(f"Ошибка получения данных пользователей: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/force-refresh-users')
def admin_force_refresh_users():
    """
    API для принудительного обновления данных о пользователях (только для администратора)
    """
    try:
        if not session.get('authenticated'):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Проверяем, является ли пользователь администратором
        user_id = session.get('user_id')
        if user_id not in ADMIN_USER_IDS:
            return jsonify({'success': False, 'error': 'Access denied. Admin only.'}), 403
        
        print(f"Принудительное обновление данных пользователей для админа {user_id}")
        
        # Принудительно перезагружаем данные
        data = load_users_data()
        
        print(f"Загружено {len(data.get('users', {}))} пользователей")
        for user_id, user in data.get('users', {}).items():
            print(f"  Пользователь {user_id}: {user.get('id')}, посещений: {len(user.get('visit_history', []))}")
        
        # Возвращаем данные
        return jsonify({
            'users': data.get('users', {}),
            'last_updated': data.get('last_updated', ''),
            'admin_id': session.get('user_id'),
            'total_users': len(data.get('users', {}))
        })
    except Exception as e:
        print(f"Ошибка принудительного обновления данных пользователей: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/log-stats')
def api_admin_log_stats():
    """Админ-эндпоинт: возвращает агрегированную статистику по append-логу."""
    try:
        if not session.get('authenticated'):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        user_id = session.get('user_id')
        if user_id not in ADMIN_USER_IDS:
            return jsonify({'success': False, 'error': 'Access denied. Admin only.'}), 403

        print(f"Запрос статистики логов от админа {user_id}")
        events = read_append_log()
        stats = aggregate_log_stats(events)
        print(f"Лог-событий: {stats['events_total']}, уникальных ID: {stats['users_total']}")
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        print(f"Ошибка выдачи статистики логов: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/user-activity', methods=['POST'])
def user_activity():
    """
    API для обновления активности пользователя
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        user_id = data.get('user_id')
        action = data.get('action', 'Unknown action')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
        
        # Получаем данные пользователя из сессии или из данных
        user_data = {
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'username': data.get('username', '')
        }
        
        # Если это закрытие страницы, отмечаем выход
        if action == 'Закрытие страницы':
            mark_user_logout(user_id)
        else:
            update_user_activity(user_id, action, user_data)
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Ошибка обновления активности: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Старая страница
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test-auth')
def test_auth():
    return render_template('test_auth.html')

@app.route('/admin')
def admin_panel():
    """Админ-панель. Если сессии нет, пробуем создать её из init_data."""
    # Тихо создаём сессию из init_data, если это запрос из Telegram WebApp
    if not session.get('authenticated'):
        init_data = request.args.get('init_data', '')
        if init_data and verify_telegram_data(init_data):
            params = dict(parse_qsl(init_data, keep_blank_values=True))
            user_raw = params.get('user')
            try:
                user = json.loads(user_raw) if user_raw else {}
            except Exception:
                user = {}
            user_id = user.get('id')
            if user_id:
                session['user_id'] = user_id
                session['first_name'] = user.get('first_name', '')
                session['last_name'] = user.get('last_name', '')
                session['username'] = user.get('username', '')
                session['authenticated'] = True

    if not session.get('authenticated'):
        return redirect('/')
    if session.get('user_id') not in ADMIN_USER_IDS:
        return jsonify({'error': 'Access denied. Admin only.'}), 403
    return render_template('admin.html')


@app.route('/admin/stats/<mode>')
def admin_stats(mode: str):
    """Страницы детальной статистики: all | online | today | actions"""
    # Тихо создаём сессию из init_data при первом заходе из Telegram WebApp
    if not session.get('authenticated'):
        init_data = request.args.get('init_data', '')
        if init_data and verify_telegram_data(init_data):
            params = dict(parse_qsl(init_data, keep_blank_values=True))
            user_raw = params.get('user')
            try:
                user = json.loads(user_raw) if user_raw else {}
            except Exception:
                user = {}
            user_id = user.get('id')
            if user_id:
                session['user_id'] = user_id
                session['first_name'] = user.get('first_name', '')
                session['last_name'] = user.get('last_name', '')
                session['username'] = user.get('username', '')
                session['authenticated'] = True

    if not session.get('authenticated'):
        return redirect('/')
    if session.get('user_id') not in ADMIN_USER_IDS:
        return jsonify({'error': 'Access denied. Admin only.'}), 403

    # Валидация режима
    allowed_modes = {'all', 'online', 'today', 'actions'}
    if mode not in allowed_modes:
        mode = 'all'

    return render_template('admin_stats.html', mode=mode)



@app.route('/my-id')
def my_telegram_id():
    """
    Страница для отображения Telegram ID пользователя
    """
    return render_template('my_id.html')

@app.route('/categories')
def categories():
    cats = Category.query.order_by(Category.name_ru).all()
    categories = [{"raw": c.name_ua, "pretty": c.name_ru} for c in cats]
    return render_template(
        'sections.html',
        section_verbose='Категории',
        categories=categories,
        section_url='show_category',
        back_url='/'
    )

@app.route('/gender')
def gender():
        mode = request.args.get('mode')
        default_season = request.args.get('default_season', '')
        title_map = {
            'old': 'Каталог старый сезон',
            'new': 'Каталог новая коллекция',
        }
        catalog_title = title_map.get(mode, 'Каталог')
        return render_template('gender.html', back_url='/', catalog_title=catalog_title, mode=mode, default_season=default_season)

@app.route('/kids-girl')
def kids_girl():
    girls = der_get_categories_by_gender('дiвч', brand='BEN.012', include_child=True)
    return render_template('sections.html', section_verbose='Девочка', categories=girls, section_url='kids_girl_category', back_url='/gender', slide_from='right')

@app.route('/kids-boy')
def kids_boy():
    boys = der_get_categories_by_gender('хлопч', brand='BEN.012', include_child=True)
    return render_template('sections.html', section_verbose='Мальчик', categories=boys, section_url='kids_boy_category', back_url='/gender', slide_from='right')

@app.route('/kids-girl/category/<category_name>')
def kids_girl_category(category_name):
    products = der_get_products_by_gender_and_category(category_name, 'girl', brand='BEN.012')
    sort = request.args.get('sort', 'asc')
    reverse = sort == 'desc'
    products = sorted(products, key=lambda p: (p.new_price is None, parse_price_for_sorting(p.new_price)), reverse=reverse)
    category_ru = get_pretty_category(category_name)
    seasons = get_available_seasons_for_products(products)
    return render_template('products.html', products=products, category=category_ru, section_verbose=f'Девочка {category_ru}', back_url='/kids-girl', genders=None, sort=sort, seasons=seasons)

@app.route('/kids-boy/category/<category_name>')
def kids_boy_category(category_name):
    products = der_get_products_by_gender_and_category(category_name, 'boy', brand='BEN.012')
    sort = request.args.get('sort', 'asc')
    reverse = sort == 'desc'
    products = sorted(products, key=lambda p: (p.new_price is None, parse_price_for_sorting(p.new_price)), reverse=reverse)
    category_ru = get_pretty_category(category_name)
    seasons = get_available_seasons_for_products(products)
    return render_template('products.html', products=products, category=category_ru, section_verbose=f'Мальчик {category_ru}', back_url='/kids-boy', genders=None, sort=sort, seasons=seasons)

@app.route('/category/<category_ua>')
def show_category(category_ua):
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    category = Category.query.filter_by(name_ua=category_ua).first_or_404()
    query = Product.query.filter_by(category_id=category.id).all()
    products, sort = filter_and_sort_products(query)
    title_map = {'old': 'Каталог старый сезон', 'new': 'Каталог новая коллекция'}
    section_verbose = title_map.get(mode, category.name_ru)
    back_url = '/categories'
    if mode or default_season:
        q = []
        if mode:
            q.append(f"mode={quote_plus(mode)}")
        if default_season:
            q.append(f"default_season={quote_plus(default_season)}")
        back_url = back_url + '?' + '&'.join(q)
    return render_template(
        'products.html',
        products=products,
        category=category.name_ru,
        section_verbose=section_verbose,
        pretty_category=category.name_ru,
        back_url=back_url,
        sort=sort,
        default_season=default_season
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

@app.route('/der/product/<int:der_product_id>')
def der_product_page(der_product_id: int):
    # Получаем продукт и его вариации из новой БД
    prod: DerProduct | None = DerProduct.query.get_or_404(der_product_id)
    variants: list[DerVariant] = DerVariant.query.filter_by(product_id=der_product_id).all()

    # Группируем по цвету и размерам только с наличием
    color_size_map = {}
    for v in variants:
        if v.stock and float(v.stock) > 0:
            color = (v.color or '').strip()
            size = (v.size or '').strip()
            if not color:
                continue
            if color not in color_size_map:
                color_size_map[color] = set()
            if size:
                color_size_map[color].add(size)
    color_size_list = [
        {"color": color, "sizes": sorted(list(sizes))}
        for color, sizes in color_size_map.items()
    ]
    color_size_list = sorted(color_size_list, key=lambda x: x['color'])

    # Собираем мета по сезонам для этого артикула
    seasons_meta = []
    if prod and prod.article:
        same_products = DerProduct.query.filter_by(article=prod.article).all()
        for sp in same_products:
            vlist = DerVariant.query.filter_by(product_id=sp.id).all()
            # цвета/размеры по этому сезону
            cs_map = {}
            for vv in vlist:
                if vv.stock and float(vv.stock) > 0:
                    c = (vv.color or '').strip()
                    s = (vv.size or '').strip()
                    if not c:
                        continue
                    if c not in cs_map:
                        cs_map[c] = set()
                    if s:
                        cs_map[c].add(s)
            color_sizes = [
                {"color": c, "sizes": sorted(list(sz))} for c, sz in cs_map.items()
            ]
            # цены по сезону
            sale_prices, purchase_prices, discounts = [], [], []
            for vv in vlist:
                if vv.sale_price:
                    sale_prices.append(float(vv.sale_price))
                if vv.purchase_price:
                    purchase_prices.append(float(vv.purchase_price))
                if vv.discount:
                    discounts.append(float(vv.discount))
            season_new = min(sale_prices) if sale_prices else None
            season_old = min(purchase_prices) if purchase_prices else None
            season_disc = max(discounts) if discounts else None
            seasons_meta.append({
                'product_id': sp.id,
                'season': sp.season,
                'color_sizes': color_sizes,
                'new_price': season_new,
                'old_price': season_old,
                'discount': season_disc,
            })

    # Картинки по артикулу
    pic_dir = os.path.join(app.root_path, 'static', 'pic', 'list')
    images = []
    if os.path.isdir(pic_dir) and prod and prod.article:
        search_art = prod.article.replace('.K', '') if str(prod.article).endswith('.K') else prod.article
        images = [f for f in os.listdir(pic_dir) if f.startswith(search_art) and f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        images = sort_product_images(images, search_art)

    # Заголовок раздела (категория)
    section_verbose = prod.category.name if prod and prod.category else ''

    back_url = request.args.get('back') or '/'

    # Рассчитываем цены для текущего сезона
    sale_prices, purchase_prices, discounts = [], [], []
    for v in variants:
        if v.sale_price:
            sale_prices.append(float(v.sale_price))
        if v.purchase_price:
            purchase_prices.append(float(v.purchase_price))
        if v.discount:
            discounts.append(float(v.discount))
    cur_new = min(sale_prices) if sale_prices else None
    cur_old = min(purchase_prices) if purchase_prices else None
    cur_disc = max(discounts) if discounts else None

    # Подготавливаем совместимый объект product для шаблона product.html
    product_ns = SimpleNamespace(
        id=prod.id,
        art=prod.article,
        name=prod.name,
        category_id=None,
        old_price=cur_old,
        new_price=cur_new,
        sale=cur_disc,
        season=prod.season,
        gender=prod.gender,
        brand=prod.brand,
    )

    return render_template(
        'product.html',
        product=product_ns,
        section_verbose=section_verbose,
        back_url=back_url,
        color_size_map=color_size_list,
        product_images=images,
        der_seasons=seasons_meta,
        der_current_id=prod.id
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

@app.route('/api/search')
def api_search():
    """
    Живой поиск по новой БД (db-der.db) через ORM. Если ничего не найдено — падем на старую БД.
    Параметры: q — строка запроса
    """
    query_str = request.args.get('q', '').strip()
    if not query_str:
        return jsonify({"query": query_str, "count": 0, "results": []})

    words = [w.lower() for w in query_str.split() if w]

    # Поиск в новой БД (DerProduct/DerVariant) с подсчётом количества (sum(stock))
    q_der = db.session.query(
        DerProduct,
        func.sum(func.coalesce(DerVariant.stock, 0)).label('qty')
    ).outerjoin(DerVariant, DerVariant.product_id == DerProduct.id)
    for w in words:
        q_der = q_der.filter(
            or_(
                func.lower(func.trim(DerProduct.article)).like(f"%{w}%"),
                func.lower(func.trim(DerProduct.name)).like(f"%{w}%"),
                func.lower(func.trim(DerVariant.color)).like(f"%{w}%"),
                func.lower(func.trim(DerVariant.size)).like(f"%{w}%"),
            )
        )
    # Не фильтруем по остатку: показываем и нулевые, чтобы поиск работал всегда
    q_der = q_der.group_by(DerProduct.id).limit(50)
    der_rows = q_der.all()

    results: list[dict] = []
    for p, qty in der_rows:
        cat_name = p.category.name if p.category else ''
        results.append({
            "id": p.id,
            "art": p.article,
            "name": p.name,
            "category": cat_name,
            "qty": float(qty or 0),
            "url": url_for('der_product_page', der_product_id=p.id),
            "image": url_for('static', filename=f'pic/cat/{p.article}.jpg')
        })

    return jsonify({"query": query_str, "count": len(results), "results": results})

@app.route('/favorites')
def favorites():
    # Клиентская страница, данные берутся из localStorage на стороне браузера
    return render_template('favorit.html')

@app.route('/.well-known/acme-challenge/<path:filename>')
def letsencrypt_challenge(filename):
    acme_dir = os.path.join(app.root_path, '.well-known', 'acme-challenge')
    return send_from_directory(acme_dir, filename)

@app.route('/women')
def women():
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    title_map = {'old': 'Каталог старый сезон', 'new': 'Каталог новая коллекция'}
    section_verbose = title_map.get(mode, 'Женское')
    categories = der_get_categories_by_gender('жiн', brand='BENETTON', include_unisex=True, season_label=(default_season or None))
    extra_query = []
    if mode:
        extra_query.append(f"mode={quote_plus(mode)}")
    if default_season:
        extra_query.append(f"default_season={quote_plus(default_season)}")
    extra_query = '&'.join(extra_query)
    back_url = '/gender'
    if extra_query:
        back_url = f"/gender?{extra_query}"
    return render_template('sections.html', section_verbose=section_verbose, categories=categories, section_url='women_category', back_url=back_url, slide_from='right', extra_query=extra_query, default_season=default_season)

@app.route('/men')
def men():
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    title_map = {'old': 'Каталог старый сезон', 'new': 'Каталог новая коллекция'}
    section_verbose = title_map.get(mode, 'Мужское')
    categories = der_get_categories_by_gender('чол', brand='BENETTON', include_unisex=True, season_label=(default_season or None))
    extra_query = []
    if mode:
        extra_query.append(f"mode={quote_plus(mode)}")
    if default_season:
        extra_query.append(f"default_season={quote_plus(default_season)}")
    extra_query = '&'.join(extra_query)
    back_url = '/gender'
    if extra_query:
        back_url = f"/gender?{extra_query}"
    return render_template('sections.html', section_verbose=section_verbose, categories=categories, section_url='men_category', back_url=back_url, slide_from='right', extra_query=extra_query, default_season=default_season)

@app.route('/kids')
def kids():
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    title_map = {'old': 'Каталог старый сезон', 'new': 'Каталог новая коллекция'}
    section_verbose = title_map.get(mode, 'Дети')
    girls = get_unique_categories_by_gender('дiвч', brand='BEN.012', season_label=(default_season or None))
    boys = get_unique_categories_by_gender('хлопч', brand='BEN.012', season_label=(default_season or None))
    # Удаляем дубли по raw
    seen = set()
    unique_categories = []
    for c in girls + boys:
        if c['raw'] not in seen:
            unique_categories.append(c)
            seen.add(c['raw'])
    extra_query = []
    if mode:
        extra_query.append(f"mode={quote_plus(mode)}")
    if default_season:
        extra_query.append(f"default_season={quote_plus(default_season)}")
    extra_query = '&'.join(extra_query)
    back_url = '/'
    if extra_query:
        back_url = f"/gender?{extra_query}"
    return render_template('sections.html', section_verbose=section_verbose, categories=unique_categories, section_url='kids_category', back_url=back_url, extra_query=extra_query, default_season=default_season)

@app.route('/women/category/<category_name>')
def women_category(category_name):
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    products = der_get_products_by_gender_and_category(category_name, 'women', brand='BENETTON')
    sort = request.args.get('sort', 'asc')
    reverse = sort == 'desc'
    products = sorted(products, key=lambda p: (p.new_price is None, parse_price_for_sorting(p.new_price)), reverse=reverse)
    # Получаем русское название категории
    category_ru = get_pretty_category(category_name)
    seasons = get_available_seasons_for_products(products)
    title_map = {'old': 'Каталог старый сезон', 'new': 'Каталог новая коллекция'}
    section_verbose = title_map.get(mode, f'Женщина {category_ru}')
    title_gender = 'Женщина'
    back_url = '/women'
    extra_query = []
    if mode:
        extra_query.append(f"mode={quote_plus(mode)}")
    if default_season:
        extra_query.append(f"default_season={quote_plus(default_season)}")
    extra_query = '&'.join(extra_query)
    if extra_query:
        back_url = f"/women?{extra_query}"
    return render_template('products.html', products=products, category=category_ru, section_verbose=section_verbose, back_url=back_url, genders=None, sort=sort, seasons=seasons, default_season=default_season, title_gender=title_gender)

@app.route('/men/category/<category_name>')
def men_category(category_name):
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    products = der_get_products_by_gender_and_category(category_name, 'men', brand='BENETTON')
    sort = request.args.get('sort', 'asc')
    reverse = sort == 'desc'
    products = sorted(products, key=lambda p: (p.new_price is None, parse_price_for_sorting(p.new_price)), reverse=reverse)
    category_ru = get_pretty_category(category_name)
    seasons = get_available_seasons_for_products(products)
    title_map = {'old': 'Каталог старый сезон', 'new': 'Каталог новая коллекция'}
    section_verbose = title_map.get(mode, f'Мужчина {category_ru}')
    title_gender = 'Мужчина'
    back_url = '/men'
    extra_query = []
    if mode:
        extra_query.append(f"mode={quote_plus(mode)}")
    if default_season:
        extra_query.append(f"default_season={quote_plus(default_season)}")
    extra_query = '&'.join(extra_query)
    if extra_query:
        back_url = f"/men?{extra_query}"
    return render_template('products.html', products=products, category=category_ru, section_verbose=section_verbose, back_url=back_url, genders=None, sort=sort, seasons=seasons, default_season=default_season, title_gender=title_gender)

@app.route('/kids/category/<category_name>')
def kids_category(category_name):
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
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
    genders = None

    category_ru = get_pretty_category(category_name)
    seasons = get_available_seasons_for_products(products)
    title_map = {'old': 'Каталог старый сезон', 'new': 'Каталог новая коллекция'}
    section_verbose = title_map.get(mode, f'Дети {category_ru}')
    title_gender = ''
    back_url = '/kids'
    extra_query = []
    if mode:
        extra_query.append(f"mode={quote_plus(mode)}")
    if default_season:
        extra_query.append(f"default_season={quote_plus(default_season)}")
    extra_query = '&'.join(extra_query)
    if extra_query:
        back_url = f"/kids?{extra_query}"
    return render_template('products.html', products=products, category=category_ru, section_verbose=section_verbose, back_url=back_url, genders=genders, sort=sort, seasons=seasons, default_season=default_season, title_gender=title_gender)

@app.route('/underwear')
def underwear():
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    extra_query = []
    if mode:
        extra_query.append(f"mode={quote_plus(mode)}")
    if default_season:
        extra_query.append(f"default_season={quote_plus(default_season)}")
    extra_query = '&'.join(extra_query)
    return render_template('underwear.html', extra_query=extra_query, default_season=default_season)

@app.route('/underwear/underwear-woman')
def underwear_woman():
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    categories_list = der_get_underwear_categories_by_gender('жiн', season_label=(default_season or None))
    extra_query = []
    if mode:
        extra_query.append(f"mode={quote_plus(mode)}")
    if default_season:
        extra_query.append(f"default_season={quote_plus(default_season)}")
    extra_query = '&'.join(extra_query)
    back_url = '/underwear'
    if extra_query:
        back_url = back_url + '?' + extra_query
    return render_template('sections.html', section_verbose='Бельё — Женщина', categories=categories_list, section_url='underwear_woman_category', back_url=back_url, mode=mode, default_season=default_season)

@app.route('/underwear/underwear-men')
def underwear_men():
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    categories_list = der_get_underwear_categories_by_gender('чол', season_label=(default_season or None))
    extra_query = []
    if mode:
        extra_query.append(f"mode={quote_plus(mode)}")
    if default_season:
        extra_query.append(f"default_season={quote_plus(default_season)}")
    extra_query = '&'.join(extra_query)
    back_url = '/underwear'
    if extra_query:
        back_url = back_url + '?' + extra_query
    return render_template('sections.html', section_verbose='Бельё — Мужчина', categories=categories_list, section_url='underwear_men_category', back_url=back_url, mode=mode, default_season=default_season)

@app.route('/underwear/underwear-boy')
def underwear_boy():
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    categories_list = der_get_underwear_categories_by_gender('хлопч', season_label=(default_season or None))
    extra_query = []
    if mode:
        extra_query.append(f"mode={quote_plus(mode)}")
    if default_season:
        extra_query.append(f"default_season={quote_plus(default_season)}")
    extra_query = '&'.join(extra_query)
    back_url = '/underwear'
    if extra_query:
        back_url = back_url + '?' + extra_query
    return render_template('sections.html', section_verbose='Бельё — Мальчик', categories=categories_list, section_url='underwear_boy_category', back_url=back_url, mode=mode, default_season=default_season)

@app.route('/underwear/underwear-girl')
def underwear_girl():
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    categories_list = der_get_underwear_categories_by_gender('дiвч', season_label=(default_season or None))
    extra_query = []
    if mode:
        extra_query.append(f"mode={quote_plus(mode)}")
    if default_season:
        extra_query.append(f"default_season={quote_plus(default_season)}")
    extra_query = '&'.join(extra_query)
    back_url = '/underwear'
    if extra_query:
        back_url = back_url + '?' + extra_query
    return render_template('sections.html', section_verbose='Бельё — Девочка', categories=categories_list, section_url='underwear_girl_category', back_url=back_url, mode=mode, default_season=default_season)

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
    seasons = get_available_seasons_for_products(products)
    return render_template('products.html', products=products, category=category_ru, section_verbose=f'Бельё {section_name} {category_ru}', back_url=back_url, genders=None, sort=sort, seasons=seasons)

@app.route('/underwear/underwear-woman/category/<category_name>')
def underwear_woman_category(category_name):
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    products = der_get_products_by_gender_and_category(category_name, 'women', brand='undercolor')
    sort = request.args.get('sort', 'asc')
    reverse = sort == 'desc'
    products = sorted(products, key=lambda p: (p.new_price is None, parse_price_for_sorting(p.new_price)), reverse=reverse)
    category_ru = get_pretty_category(category_name)
    seasons = get_available_seasons_for_products(products)
    title_map = {'old': 'Каталог старый сезон', 'new': 'Каталог новая коллекция'}
    section_verbose = title_map.get(mode, f'Бельё Женщина {category_ru}')
    back_url = '/underwear/underwear-woman'
    if mode or default_season:
        q = []
        if mode:
            q.append(f"mode={quote_plus(mode)}")
        if default_season:
            q.append(f"default_season={quote_plus(default_season)}")
        back_url = back_url + '?' + '&'.join(q)
    return render_template('products.html', products=products, category=category_ru, section_verbose=section_verbose, back_url=back_url, genders=None, sort=sort, seasons=seasons, default_season=default_season, title_gender='Женщина')

@app.route('/underwear/underwear-men/category/<category_name>')
def underwear_men_category(category_name):
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    products = der_get_products_by_gender_and_category(category_name, 'men', brand='undercolor')
    sort = request.args.get('sort', 'asc')
    reverse = sort == 'desc'
    products = sorted(products, key=lambda p: (p.new_price is None, parse_price_for_sorting(p.new_price)), reverse=reverse)
    category_ru = get_pretty_category(category_name)
    seasons = get_available_seasons_for_products(products)
    title_map = {'old': 'Каталог старый сезон', 'new': 'Каталог новая коллекция'}
    section_verbose = title_map.get(mode, f'Бельё Мужчина {category_ru}')
    back_url = '/underwear/underwear-men'
    if mode or default_season:
        q = []
        if mode:
            q.append(f"mode={quote_plus(mode)}")
        if default_season:
            q.append(f"default_season={quote_plus(default_season)}")
        back_url = back_url + '?' + '&'.join(q)
    return render_template('products.html', products=products, category=category_ru, section_verbose=section_verbose, back_url=back_url, genders=None, sort=sort, seasons=seasons, default_season=default_season, title_gender='Мужчина')

@app.route('/underwear/underwear-boy/category/<category_name>')
def underwear_boy_category(category_name):
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    products = der_get_products_by_gender_and_category(category_name, 'boy', brand='undercolor')
    sort = request.args.get('sort', 'asc')
    reverse = sort == 'desc'
    products = sorted(products, key=lambda p: (p.new_price is None, parse_price_for_sorting(p.new_price)), reverse=reverse)
    category_ru = get_pretty_category(category_name)
    seasons = get_available_seasons_for_products(products)
    title_map = {'old': 'Каталог старый сезон', 'new': 'Каталог новая коллекция'}
    section_verbose = title_map.get(mode, f'Бельё Мальчик {category_ru}')
    back_url = '/underwear/underwear-boy'
    if mode or default_season:
        q = []
        if mode:
            q.append(f"mode={quote_plus(mode)}")
        if default_season:
            q.append(f"default_season={quote_plus(default_season)}")
        back_url = back_url + '?' + '&'.join(q)
    return render_template('products.html', products=products, category=category_ru, section_verbose=section_verbose, back_url=back_url, genders=None, sort=sort, seasons=seasons, default_season=default_season, title_gender='Мальчик')

@app.route('/underwear/underwear-girl/category/<category_name>')
def underwear_girl_category(category_name):
    mode = request.args.get('mode')
    default_season = request.args.get('default_season', '')
    products = der_get_products_by_gender_and_category(category_name, 'girl', brand='undercolor')
    sort = request.args.get('sort', 'asc')
    reverse = sort == 'desc'
    products = sorted(products, key=lambda p: (p.new_price is None, parse_price_for_sorting(p.new_price)), reverse=reverse)
    category_ru = get_pretty_category(category_name)
    seasons = get_available_seasons_for_products(products)
    title_map = {'old': 'Каталог старый сезон', 'new': 'Каталог новая коллекция'}
    section_verbose = title_map.get(mode, f'Бельё Девочка {category_ru}')
    back_url = '/underwear/underwear-girl'
    if mode or default_season:
        q = []
        if mode:
            q.append(f"mode={quote_plus(mode)}")
        if default_season:
            q.append(f"default_season={quote_plus(default_season)}")
        back_url =back_url + '?' + '&'.join(q)
    return render_template('products.html', products=products, category=category_ru, section_verbose=section_verbose, back_url=back_url, genders=None, sort=sort, seasons=seasons, default_season=default_season, title_gender='Девочка')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

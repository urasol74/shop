import sqlite3
import openpyxl
import os
import re
from flask import Flask
from models import db, Product, Category
import hashlib

def clean_number(value):
    """
    Очищает число от запятых и преобразует в float
    """
    if not value:
        return 0.0
    
    # Преобразуем в строку и убираем запятые
    value_str = str(value).replace(',', '')
    
    try:
        return float(value_str)
    except ValueError:
        return 0.0

def create_app():
    """Создает Flask приложение для импорта"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'instance', 'shop.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def get_record_hash(record):
    """
    Создает хеш записи для сравнения
    """
    # Создаем строку из всех полей записи
    record_str = f"{record['art']}|{record['name']}|{record['size']}|{record['color']}|{record['qty']}|{record['old_price']}|{record['new_price']}|{record['sale']}|{record['gender']}|{record['brand']}|{record['season']}"
    return hashlib.md5(record_str.encode()).hexdigest()

def import_from_db_to_db_incremental():
    """
    Инкрементально импортирует данные из base.db в shop.db
    """
    app = create_app()
    
    # Подключение к базе bot_art
    bot_db_path = "/home/ubuntu/bot_art/instance/base.db"
    if not os.path.exists(bot_db_path):
        print(f"Ошибка: База данных {bot_db_path} не найдена")
        return
    
    # Загружаем справочные данные из base.xlsx
    base_xlsx_path = os.path.join('data', 'base.xlsx')
    if not os.path.exists(base_xlsx_path):
        print(f"Ошибка: Файл {base_xlsx_path} не найден")
        return
    
    print("Загружаем справочные данные из base.xlsx...")
    try:
        wb_base = openpyxl.load_workbook(base_xlsx_path)
        ws_base = wb_base.active
        
        # Составляем map артикул -> (gender, season, brand)
        base_map = {}
        for row in ws_base.iter_rows(min_row=2):
            art = str(row[0].value).strip().upper() if row[0].value else None
            brand = row[6].value if len(row) > 6 else None   # Колонка 7 (индекс 6) - Торговая марка
            season = row[8].value if len(row) > 8 else None  # Колонка 9 (индекс 8) - Сезон
            gender = row[9].value if len(row) > 9 else None  # Колонка 10 (индекс 9) - Пол
            if art:
                base_map[art] = {
                    'brand': brand,
                    'season': season,
                    'gender': gender
                }
        print(f"Загружено {len(base_map)} записей из base.xlsx")
    except Exception as e:
        print(f"Ошибка при чтении base.xlsx: {e}")
        return
    
    # Подключаемся к базе bot_art
    try:
        bot_conn = sqlite3.connect(bot_db_path)
        bot_cur = bot_conn.cursor()
        
        # Получаем все товары из base.db
        bot_cur.execute("SELECT art, name, size, color, qty, old_price, new_price, sale FROM sklad_items")
        bot_items = bot_cur.fetchall()
        bot_conn.close()
        
        print(f"Найдено {len(bot_items)} товаров в base.db")
    except Exception as e:
        print(f"Ошибка при чтении base.db: {e}")
        return
    
    with app.app_context():
        try:
            # Подготавливаем данные из bot_art
            bot_records = {}
            for item in bot_items:
                art, name, size, color, qty, old_price, new_price, sale = item
                
                if not art:
                    continue
                    
                # Очищаем артикул
                art = str(art).replace('.K', '').strip().upper()
                
                # Получаем категорию из name (только основную категорию до первой запятой)
                full_name = str(name).strip() if name else "НЕИЗВЕСТНО"
                category_name_ua = full_name.split(',')[0].strip()
                
                # Исключения для категорий
                if category_name_ua.strip().upper() in ["НАБІР", "КОМПЛЕКТ"]:
                    category_name_ua = "БЮСТГАЛЬТЕР"
                
                # Получаем дополнительные данные из base_map
                base_info = base_map.get(art, {})
                gender = base_info.get('gender')
                brand = base_info.get('brand')
                season = base_info.get('season')
                
                # Если не найдено и артикул оканчивается на .K, пробуем без .K
                if not gender and art.endswith('.K'):
                    art_nok = art.replace('.K', '')
                    base_info_nok = base_map.get(art_nok, {})
                    if base_info_nok:
                        base_info = base_info_nok
                        gender = base_info.get('gender')
                        brand = base_info.get('brand')
                        season = base_info.get('season')
                
                # Очищаем числовые значения
                qty_clean = clean_number(qty)
                old_price_clean = clean_number(old_price)
                new_price_clean = clean_number(new_price)
                sale_clean = clean_number(sale) if sale else 0
                
                # Создаем ключ для записи
                record_key = f"{art}_{color}_{size}"
                
                bot_records[record_key] = {
                    'art': art,
                    'name': full_name,  # Полное название товара
                    'cat': category_name_ua,  # Основная категория
                    'category_name': category_name_ua,  # Основная категория
                    'size': size,
                    'color': color,
                    'qty': qty_clean,
                    'old_price': old_price_clean,
                    'new_price': new_price_clean,
                    'sale': sale_clean,
                    'gender': gender,
                    'brand': brand,
                    'season': season,
                    'image': f"/static/pic/{art}.jpg"
                }
            
            # Получаем существующие записи из shop.db
            existing_products = Product.query.all()
            existing_records = {}
            
            for product in existing_products:
                record_key = f"{product.art}_{product.color}_{product.size}"
                existing_records[record_key] = {
                    'product': product,
                    'hash': get_record_hash({
                        'art': product.art,
                        'name': product.name,
                        'size': product.size,
                        'color': product.color,
                        'qty': product.qty,
                        'old_price': product.old_price,
                        'new_price': product.new_price,
                        'sale': product.sale,
                        'gender': product.gender,
                        'brand': product.brand,
                        'season': product.season
                    })
                }
            
            # Статистика
            count_new = 0
            count_updated = 0
            count_deleted = 0
            
            # Обрабатываем новые и измененные записи
            for record_key, bot_record in bot_records.items():
                try:
                    # Находим или создаем категорию
                    category_name_ua = bot_record['category_name']
                    category = Category.query.filter_by(name_ua=category_name_ua).first()
                    if not category:
                        category = Category(name_ua=category_name_ua, name_ru=category_name_ua)
                        db.session.add(category)
                        db.session.commit()
                    
                    if record_key in existing_records:
                        # Запись существует - проверяем, изменилась ли она
                        existing_product = existing_records[record_key]['product']
                        existing_hash = existing_records[record_key]['hash']
                        
                        new_hash = get_record_hash(bot_record)
                        
                        if existing_hash != new_hash:
                            # Запись изменилась - обновляем
                            existing_product.name = bot_record['name']
                            existing_product.cat = bot_record['cat']
                            existing_product.category_id = category.id
                            existing_product.qty = bot_record['qty']
                            existing_product.old_price = bot_record['old_price']
                            existing_product.new_price = bot_record['new_price']
                            existing_product.sale = bot_record['sale']
                            existing_product.gender = bot_record['gender']
                            existing_product.brand = bot_record['brand']
                            existing_product.season = bot_record['season']
                            existing_product.image = bot_record['image']
                            count_updated += 1
                    else:
                        # Новая запись - создаем
                        product = Product(
                            art=bot_record['art'],
                            name=bot_record['name'],
                            cat=bot_record['cat'],
                            size=bot_record['size'],
                            color=bot_record['color'],
                            qty=bot_record['qty'],
                            old_price=bot_record['old_price'],
                            new_price=bot_record['new_price'],
                            sale=bot_record['sale'],
                            category_id=category.id,
                            gender=bot_record['gender'],
                            brand=bot_record['brand'],
                            season=bot_record['season'],
                            image=bot_record['image']
                        )
                        db.session.add(product)
                        count_new += 1
                        
                except Exception as e:
                    print(f"Ошибка при обработке записи {record_key}: {e}")
                    continue
            
            # Удаляем записи, которых нет в bot_art
            for record_key, existing_record in existing_records.items():
                if record_key not in bot_records:
                    try:
                        db.session.delete(existing_record['product'])
                        count_deleted += 1
                    except Exception as e:
                        print(f"Ошибка при удалении записи {record_key}: {e}")
                        continue
            
            # Коммитим изменения
            db.session.commit()
            
            print(f"Инкрементальный импорт завершен!")
            print(f"Новых товаров: {count_new}")
            print(f"Обновлено товаров: {count_updated}")
            print(f"Удалено товаров: {count_deleted}")
            print(f"Всего изменений: {count_new + count_updated + count_deleted}")
            
        except Exception as e:
            print(f"Ошибка при работе с базой данных: {e}")
            db.session.rollback()

if __name__ == "__main__":
    import_from_db_to_db_incremental() 
import sqlite3
import openpyxl
import os
import re
from flask import Flask
from models import db, Product, Category

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

def import_from_db_to_db():
    """
    Импортирует данные из base.db в shop.db с дополнением из base.xlsx
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
            brand = row[6].value if len(row) > 6 else None   # G
            season = row[8].value if len(row) > 8 else None  # I
            gender = row[9].value if len(row) > 9 else None  # J
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
    
    # Очищаем текущую базу shop.db
    with app.app_context():
        try:
            print("Очищаем текущую базу shop.db...")
            Product.query.delete()
            Category.query.delete()
            db.session.commit()
            
            count_new = 0
            count_upd = 0
            
            # Обрабатываем каждый товар
            for i, item in enumerate(bot_items):
                try:
                    art, name, size, color, qty, old_price, new_price, sale = item
                    
                    if not art:
                        continue
                        
                    # Очищаем артикул
                    art = str(art).replace('.K', '').strip().upper()
                    
                    # Получаем категорию из name
                    category_name_ua = str(name).strip() if name else "НЕИЗВЕСТНО"
                    
                    # Исключения для категорий
                    if category_name_ua.strip().upper() in ["НАБІР", "КОМПЛЕКТ"]:
                        category_name_ua = "БЮСТГАЛЬТЕР"
                    
                    # Находим или создаем категорию
                    category = Category.query.filter_by(name_ua=category_name_ua).first()
                    if not category:
                        category = Category(name_ua=category_name_ua, name_ru=category_name_ua)
                        db.session.add(category)
                        db.session.commit()
                    
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
                    
                    # Создаем или обновляем товар
                    product = Product.query.filter_by(art=art, color=color, size=size).first()
                    if product:
                        # Обновляем существующий товар
                        product.name = category_name_ua
                        product.category_id = category.id
                        product.qty = qty_clean
                        product.old_price = old_price_clean
                        product.new_price = new_price_clean
                        product.sale = sale_clean
                        product.gender = gender
                        product.brand = brand
                        product.season = season
                        product.image = f"/static/pic/{art}.jpg"
                        count_upd += 1
                    else:
                        # Создаем новый товар
                        product = Product(
                            art=art,
                            name=category_name_ua,
                            size=size,
                            color=color,
                            qty=qty_clean,
                            old_price=old_price_clean,
                            new_price=new_price_clean,
                            sale=sale_clean,
                            category_id=category.id,
                            gender=gender,
                            brand=brand,
                            season=season,
                            image=f"/static/pic/{art}.jpg"
                        )
                        db.session.add(product)
                        count_new += 1
                    
                    # Коммитим каждые 100 записей для экономии памяти
                    if (i + 1) % 100 == 0:
                        db.session.commit()
                        print(f"Обработано {i + 1} товаров...")
                        
                except Exception as e:
                    print(f"Ошибка при обработке товара {i}: {e}")
                    continue
            
            # Финальный коммит
            db.session.commit()
            
            print(f"Импорт завершен!")
            print(f"Новых товаров: {count_new}")
            print(f"Обновлено товаров: {count_upd}")
            print(f"Всего: {count_new + count_upd}")
            
        except Exception as e:
            print(f"Ошибка при работе с базой данных: {e}")
            db.session.rollback()

if __name__ == "__main__":
    import_from_db_to_db() 
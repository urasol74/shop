#!/usr/bin/env python3
import sqlite3
import openpyxl
import os
from flask import Flask
from models import db, Product, Category

def create_app():
    """Создает Flask приложение для импорта"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'instance', 'shop.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def force_update():
    """
    Принудительно обновляет данные в shop.db из base.xlsx
    """
    app = create_app()
    
    # Загружаем справочные данные из base.xlsx
    base_xlsx_path = os.path.join('data', 'base.xlsx')
    wb = openpyxl.load_workbook(base_xlsx_path)
    ws = wb.active
    
    # Составляем map артикул -> (gender, season, brand)
    base_map = {}
    for row in ws.iter_rows(min_row=2):
        art = str(row[0].value).strip().upper() if row[0].value else None
        brand = row[6].value if len(row) > 6 else None
        season = row[8].value if len(row) > 8 else None
        gender = row[9].value if len(row) > 9 else None
        if art:
            base_map[art] = {
                'brand': brand,
                'season': season,
                'gender': gender
            }
    
    print(f"Загружено {len(base_map)} записей из base.xlsx")
    
    with app.app_context():
        # Получаем все товары из shop.db
        products = Product.query.all()
        updated_count = 0
        
        for product in products:
            # Ищем данные в base_map
            base_info = base_map.get(product.art, {})
            gender = base_info.get('gender')
            brand = base_info.get('brand')
            season = base_info.get('season')
            
            # Если не найдено и артикул оканчивается на .K, пробуем без .K
            if not gender and product.art.endswith('.K'):
                art_nok = product.art.replace('.K', '')
                base_info_nok = base_map.get(art_nok, {})
                if base_info_nok:
                    base_info = base_info_nok
                    gender = base_info.get('gender')
                    brand = base_info.get('brand')
                    season = base_info.get('season')
            
            # Обновляем данные
            if gender or brand or season:
                if gender:
                    product.gender = gender
                if brand:
                    product.brand = brand
                if season:
                    product.season = season
                updated_count += 1
        
        # Сохраняем изменения
        db.session.commit()
        print(f"Обновлено {updated_count} товаров")

if __name__ == "__main__":
    force_update() 
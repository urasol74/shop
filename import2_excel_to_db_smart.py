#!/usr/bin/env python3
import sqlite3
import pandas as pd
import os
import re
import zipfile

DB_PATH = "/home/ubuntu/shop/instance/db-der.db"
EXCEL_PATH = "/home/ubuntu/shop/data/db-der.xlsx"

# ---------- Создание БД ----------
def create_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article TEXT,
        name TEXT,
        category_id INTEGER,
        brand TEXT,
        season TEXT,
        gender TEXT,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        size TEXT,
        color TEXT,
        barcode TEXT,
        stock REAL,
        purchase_price REAL,
        sale_price REAL,
        new_price REAL,
        total_price REAL,
        discount REAL,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)
    conn.commit()
    conn.close()

# ---------- Умный импорт ----------
def smart_import_excel():
    # Исправляем регистр SharedStrings в xlsx (Linux чувствителен к регистру)
    def ensure_sharedstrings_lowercase(xlsx_path: str) -> None:
        if not os.path.exists(xlsx_path):
            return
        try:
            with zipfile.ZipFile(xlsx_path, 'r') as z:
                names = set(z.namelist())
                if 'xl/sharedStrings.xml' in names:
                    return
                if 'xl/SharedStrings.xml' not in names:
                    return
            tmp = xlsx_path + '.tmp'
            with zipfile.ZipFile(xlsx_path, 'r') as zin, zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    zout.writestr(item, data)
                    if item.filename == 'xl/SharedStrings.xml':
                        zout.writestr('xl/sharedStrings.xml', data)
            os.replace(tmp, xlsx_path)
        except Exception:
            pass

    ensure_sharedstrings_lowercase(EXCEL_PATH)
    # Читаем excel
    df = pd.read_excel(EXCEL_PATH, header=None)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Собираем данные из Excel
    excel_products = {}  # {article: {data}}
    excel_variants = {}  # {article: [variants]}
    
    current_product_article = None

    def safe_float(value, default=0.0):
        if pd.isna(value):
            return default
        try:
            return float(str(value).replace(",", ".").replace("\xa0", "").replace(" ", ""))
        except (ValueError, TypeError):
            return default

    def is_variant_row(r) -> bool:
        for idx in (3, 4, 6, 8, 9, 10, 11, 12):
            if len(r) > idx and pd.notna(r[idx]) and str(r[idx]).strip() != "":
                return True
        return False

    for i, row in df.iterrows():
        cell0 = row[0] if len(row) > 0 else None
        cell_value = str(cell0).strip() if pd.notna(cell0) else ""

        # Пропускаем заголовки отчета
        if cell_value and any(skip in cell_value.lower() for skip in ['оценка', 'параметри', 'відбір', 'магазин', 'склад', 'номенклатура', 'артикул']):
            continue

        # Заголовок продукта?
        if cell_value and " " in cell_value and len(cell_value.split(" ")) > 1:
            parts = cell_value.split(" ", 1)
            article = parts[0]
            category_name = parts[1]

            brand = str(row[3]).strip() if len(row) > 3 and pd.notna(row[3]) else ""
            season = str(row[4]).strip() if len(row) > 4 and pd.notna(row[4]) else ""
            gender = str(row[6]).strip() if len(row) > 6 and pd.notna(row[6]) else ""

            excel_products[article] = {
                'name': cell_value,
                'category_name': category_name,
                'brand': brand,
                'season': season,
                'gender': gender
            }
            excel_variants[article] = []
            current_product_article = article
            continue

        # Вариант строки может иметь пустую первую колонку
        if current_product_article is not None and is_variant_row(row):
            size = str(row[3]).strip() if len(row) > 3 and pd.notna(row[3]) else ""
            color = str(row[4]).strip() if len(row) > 4 and pd.notna(row[4]) else ""
            barcode = str(row[6]).strip() if len(row) > 6 and pd.notna(row[6]) else ""

            stock = safe_float(row[8]) if len(row) > 8 else 0
            purchase_price = safe_float(row[9]) if len(row) > 9 else 0
            sale_price = safe_float(row[10]) if len(row) > 10 else 0
            new_price = safe_float(row[10]) if len(row) > 10 else 0
            total_price = safe_float(row[11]) if len(row) > 11 else 0
            discount = safe_float(row[12]) if len(row) > 12 else 0

            excel_variants[current_product_article].append({
                'size': size,
                'color': color,
                'barcode': barcode,
                'stock': stock,
                'purchase_price': purchase_price,
                'sale_price': sale_price,
                'new_price': new_price,
                'total_price': total_price,
                'discount': discount
            })

    print(f"Найдено в Excel: {len(excel_products)} продуктов")

    # Получаем существующие данные из БД
    cur.execute("SELECT article, name, category_id, brand, season, gender FROM products")
    db_products = {row[0]: {'id': None, 'name': row[1], 'category_id': row[2], 'brand': row[3], 'season': row[4], 'gender': row[5]} for row in cur.fetchall()}
    
    # Получаем ID продуктов
    for article in db_products:
        cur.execute("SELECT id FROM products WHERE article=?", (article,))
        result = cur.fetchone()
        if result:
            db_products[article]['id'] = result[0]

    # Обрабатываем продукты
    updated_products = 0
    new_products = 0
    deleted_products = 0

    # Обновляем и добавляем продукты
    for article, product_data in excel_products.items():
        if article in db_products:
            # Проверяем, нужно ли обновить
            db_product = db_products[article]
            if (db_product['name'] != product_data['name'] or 
                db_product['brand'] != product_data['brand'] or 
                db_product['season'] != product_data['season'] or 
                db_product['gender'] != product_data['gender']):
                
                # Обновляем категорию если нужно
                cur.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (product_data['category_name'],))
                conn.commit()
                cur.execute("SELECT id FROM categories WHERE name=?", (product_data['category_name'],))
                category_id = cur.fetchone()[0]

                # Обновляем продукт
                cur.execute("""
                    UPDATE products 
                    SET name=?, category_id=?, brand=?, season=?, gender=?
                    WHERE article=?
                """, (product_data['name'], category_id, product_data['brand'], 
                     product_data['season'], product_data['gender'], article))
                conn.commit()
                updated_products += 1
        else:
            # Добавляем новый продукт
            cur.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (product_data['category_name'],))
            conn.commit()
            cur.execute("SELECT id FROM categories WHERE name=?", (product_data['category_name'],))
            category_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO products(article, name, category_id, brand, season, gender)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (article, product_data['name'], category_id, product_data['brand'], 
                 product_data['season'], product_data['gender']))
            conn.commit()
            new_products += 1

    # Удаляем продукты, которых нет в Excel
    excel_articles = set(excel_products.keys())
    db_articles = set(db_products.keys())
    articles_to_delete = db_articles - excel_articles

    for article in articles_to_delete:
        # Сначала удаляем варианты
        cur.execute("DELETE FROM variants WHERE product_id IN (SELECT id FROM products WHERE article=?)", (article,))
        # Затем удаляем продукт
        cur.execute("DELETE FROM products WHERE article=?", (article,))
        deleted_products += 1

    conn.commit()

    # Обрабатываем варианты
    updated_variants = 0
    new_variants = 0
    deleted_variants = 0

    for article, variants_data in excel_variants.items():
        # Получаем ID продукта
        cur.execute("SELECT id FROM products WHERE article=?", (article,))
        result = cur.fetchone()
        if not result:
            continue
        product_id = result[0]

        # Получаем существующие варианты (учитываем штрихкод в ключе)
        cur.execute("SELECT size, color, barcode FROM variants WHERE product_id=?", (product_id,))
        existing_variants = {(row[0] or '', row[1] or '', row[2] or '') for row in cur.fetchall()}

        # Обрабатываем варианты из Excel
        for variant in variants_data:
            variant_key = (variant['size'] or '', variant['color'] or '', variant['barcode'] or '')
            if variant_key in existing_variants:
                # Обновляем существующий вариант
                cur.execute("""
                    UPDATE variants 
                    SET stock=?, purchase_price=?, sale_price=?, new_price=?, total_price=?, discount=?
                    WHERE product_id=? AND size=? AND color=? AND barcode=?
                """, (
                    variant['stock'], variant['purchase_price'], variant['sale_price'],
                    variant['new_price'], variant['total_price'], variant['discount'],
                    product_id, variant['size'], variant['color'], variant['barcode']
                ))
                updated_variants += 1
            else:
                # Добавляем новый вариант
                cur.execute("""
                    INSERT INTO variants(product_id, size, color, barcode, stock, purchase_price, sale_price, new_price, total_price, discount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (product_id, variant['size'], variant['color'], variant['barcode'],
                     variant['stock'], variant['purchase_price'], variant['sale_price'], variant['new_price'],
                     variant['total_price'], variant['discount']))
                new_variants += 1

        # Удаляем варианты, которых нет в Excel
        excel_variant_keys = {(v['size'] or '', v['color'] or '', v['barcode'] or '') for v in variants_data}
        variants_to_delete = existing_variants - excel_variant_keys

        for size, color, barcode in variants_to_delete:
            cur.execute("DELETE FROM variants WHERE product_id=? AND size=? AND color=? AND barcode=?", 
                       (product_id, size, color, barcode))
            deleted_variants += 1

    conn.commit()
    conn.close()

    print(f"📊 РЕЗУЛЬТАТЫ УМНОГО ИМПОРТА:")
    print(f"  Продукты:")
    print(f"    - Обновлено: {updated_products}")
    print(f"    - Добавлено: {new_products}")
    print(f"    - Удалено: {deleted_products}")
    print(f"  Варианты:")
    print(f"    - Обновлено: {updated_variants}")
    print(f"    - Добавлено: {new_variants}")
    print(f"    - Удалено: {deleted_variants}")

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        create_db()
    smart_import_excel()
    print("\nУмный импорт завершён.") 
#!/usr/bin/env python3
import sqlite3
import pandas as pd
import os
import re

DB_PATH = "/home/ubuntu/shop/instance/test-db-der.db"
EXCEL_PATH = "/home/ubuntu/shop/data/test-db-der.xlsx"

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
        new_price REAL,
        total_price REAL,
        discount REAL,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)
    conn.commit()
    conn.close()

# ---------- Импорт ----------
def import_excel():
    # Читаем excel как есть
    df = pd.read_excel(EXCEL_PATH, header=None)
    print(f"Прочитано {len(df)} строк из Excel")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    current_product_id = None

    for i, row in df.iterrows():
        print(f"\nОбрабатываем строку {i}: {row[0] if pd.notna(row[0]) else 'пустая'}")
        
        # Проверяем — это "шапка" или "вариант"
        # Если первая ячейка не пустая и содержит "|" — это шапка
        if pd.notna(row[0]) and "|" in str(row[0]):
            print(f"  -> Это заголовок продукта")
            # Пример: "3089C300Q.K ПОЛО-СОРОЧКА"
            nomenclature = row[0].split("|")[0].strip()
            
            # Извлекаем артикул и название категории
            # Артикул заканчивается на точку + буквы/цифры
            match = re.match(r'^([A-Z0-9]+\.[A-Z0-9]+)\s+(.+)$', nomenclature)
            if match:
                article = match.group(1)
                category_name = match.group(2)
            else:
                # Если не удалось распарсить, берем первое слово как артикул
                parts = nomenclature.split(" ", 1)
                article = parts[0]
                category_name = parts[1] if len(parts) > 1 else "Без категории"

            brand = str(row[1]).strip() if len(row) > 1 and pd.notna(row[1]) else ""
            season = str(row[2]).strip() if len(row) > 2 and pd.notna(row[2]) else ""
            gender = str(row[3]).strip() if len(row) > 3 and pd.notna(row[3]) else ""

            print(f"  -> Номенклатура: {nomenclature}")
            print(f"  -> Артикул: {article}")
            print(f"  -> Категория: {category_name}")
            print(f"  -> Бренд: {brand}")
            print(f"  -> Сезон: {season}")
            print(f"  -> Пол: {gender}")

            # Добавляем категорию
            cur.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (category_name,))
            conn.commit()
            cur.execute("SELECT id FROM categories WHERE name=?", (category_name,))
            category_id = cur.fetchone()[0]

            # Добавляем продукт
            cur.execute("""
                INSERT INTO products(article, name, category_id, brand, season, gender)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (article, nomenclature, category_id, brand, season, gender))
            conn.commit()

            current_product_id = cur.lastrowid
            print(f"  -> ID продукта: {current_product_id}")

        elif current_product_id is not None and pd.notna(row[0]):
            print(f"  -> Это вариант товара")
            # Это вариант
            size = str(row[1]).strip() if len(row) > 1 and pd.notna(row[1]) else ""
            color = str(row[2]).strip() if len(row) > 2 and pd.notna(row[2]) else ""
            barcode = str(row[3]).strip() if len(row) > 3 and pd.notna(row[3]) else ""
            
            # Безопасная обработка числовых значений
            def safe_float(value, default=0.0):
                if pd.isna(value):
                    return default
                try:
                    return float(str(value).replace(",", ".").replace("\xa0", "").replace(" ", ""))
                except (ValueError, TypeError):
                    return default
            
            stock = safe_float(row[4]) if len(row) > 4 else 0
            purchase_price = safe_float(row[5]) if len(row) > 5 else 0
            new_price = safe_float(row[6]) if len(row) > 6 else 0
            total_price = safe_float(row[7]) if len(row) > 7 else 0
            discount = safe_float(row[8]) if len(row) > 8 else 0

            print(f"    -> Артикул: {row[0]}")
            print(f"    -> Размер: {size}")
            print(f"    -> Цвет: {color}")
            print(f"    -> Штрихкод: {barcode}")
            print(f"    -> Остаток: {stock}")
            print(f"    -> Цена закупки: {purchase_price}")
            print(f"    -> Новая цена: {new_price}")
            print(f"    -> Общая цена: {total_price}")
            print(f"    -> Скидка: {discount}")

            cur.execute("""
                INSERT INTO variants(product_id, size, color, barcode, stock, purchase_price, new_price, total_price, discount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (current_product_id, size, color, barcode, stock, purchase_price, new_price, total_price, discount))
            conn.commit()
        else:
            print(f"  -> Пропускаем строку (не заголовок и не вариант)")

    conn.close()

def show_results():
    """Показываем результаты импорта"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("\n=== РЕЗУЛЬТАТЫ ИМПОРТА ===")
    
    # Категории
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    print(f"\nКатегории ({len(categories)}):")
    for cat in categories:
        print(f"  {cat[0]}: {cat[1]}")
    
    # Продукты
    cur.execute("""
        SELECT p.id, p.article, p.name, c.name as category, p.brand, p.season, p.gender
        FROM products p
        JOIN categories c ON p.category_id = c.id
    """)
    products = cur.fetchall()
    print(f"\nПродукты ({len(products)}):")
    for prod in products:
        print(f"  {prod[0]}: {prod[1]} - {prod[2]} ({prod[3]})")
    
    # Варианты
    cur.execute("""
        SELECT v.id, p.article, v.size, v.color, v.barcode, v.stock, v.purchase_price
        FROM variants v
        JOIN products p ON v.product_id = p.id
    """)
    variants = cur.fetchall()
    print(f"\nВарианты ({len(variants)}):")
    for var in variants:
        print(f"  {var[0]}: {var[1]} - {var[2]}/{var[3]} (остаток: {var[5]}, цена: {var[6]})")
    
    conn.close()

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        create_db()
    import_excel()
    show_results()
    print("\nИмпорт завершён.") 
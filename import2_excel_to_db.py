import sqlite3
import pandas as pd
import os
import re
import zipfile
import shutil

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


# ---------- Импорт ----------
def import_excel():
    # Исправляем не-стандартную раскладку имени SharedStrings в XLSX (Linux чувствителен к регистру)
    def ensure_sharedstrings_lowercase(xlsx_path: str) -> None:
        if not os.path.exists(xlsx_path):
            return
        try:
            with zipfile.ZipFile(xlsx_path, 'r') as z:
                names = set(z.namelist())
                if 'xl/sharedStrings.xml' in names:
                    return  # всё ок
                if 'xl/SharedStrings.xml' not in names:
                    return  # нечего исправлять
            # Нужно добавить копию файла с нижним регистром
            tmp_path = xlsx_path + '.tmp'
            with zipfile.ZipFile(xlsx_path, 'r') as zin, zipfile.ZipFile(tmp_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    zout.writestr(item, data)
                    if item.filename == 'xl/SharedStrings.xml':
                        # Дополнительно пишем под именем, которое ожидает openpyxl
                        zout.writestr('xl/sharedStrings.xml', data)
            backup = xlsx_path + '.bak'
            shutil.move(xlsx_path, backup)
            shutil.move(tmp_path, xlsx_path)
        except Exception:
            # Тихо продолжаем — пусть ошибка проявится дальше, если не получилось
            pass

    ensure_sharedstrings_lowercase(EXCEL_PATH)

    # Читаем excel
    df = pd.read_excel(EXCEL_PATH, header=None)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Полная очистка перед импортом, чтобы избежать дублей/ошибочных данных
    cur.execute("DELETE FROM variants")
    cur.execute("DELETE FROM products")
    cur.execute("DELETE FROM categories")
    conn.commit()

    current_product_id = None
    products_count = 0
    variants_count = 0

    def is_variant_row(r) -> bool:
        # вариант распознаём по заполненным полям размера/цвета/штрихкода/цен/остатка
        cols_idx = [3, 4, 6, 8, 9, 10, 11, 12]
        for idx in cols_idx:
            if len(r) > idx and pd.notna(r[idx]) and str(r[idx]).strip() != "":
                return True
        return False

    for i, row in df.iterrows():
        cell0 = row[0] if len(row) > 0 else None
        cell0_str = str(cell0).strip() if pd.notna(cell0) else ""
        cell_value = cell0_str

        # Пропускаем заголовки отчета полностью
        if cell_value and any(skip in cell_value.lower() for skip in ['оценка', 'параметри', 'відбір', 'магазин', 'склад', 'номенклатура', 'артикул']):
            continue

        # Определяем — это заголовок продукта?
        is_header = False
        if cell_value and " " in cell_value and len(cell_value.split(" ")) > 1:
            is_header = True

        if is_header:
            # Это заголовок продукта
            parts = cell_value.split(" ", 1)
            article = parts[0]
            category_name = parts[1]

            # Получаем бренд и сезон из соседних ячеек
            brand = str(row[3]).strip() if len(row) > 3 and pd.notna(row[3]) else ""
            season = str(row[4]).strip() if len(row) > 4 and pd.notna(row[4]) else ""
            gender = str(row[6]).strip() if len(row) > 6 and pd.notna(row[6]) else ""  # Колонка 6 содержит пол

            # Добавляем категорию
            cur.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (category_name,))
            conn.commit()
            cur.execute("SELECT id FROM categories WHERE name=?", (category_name,))
            category_id = cur.fetchone()[0]

            # Добавляем продукт
            cur.execute(
                """
                INSERT INTO products(article, name, category_id, brand, season, gender)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (article, cell_value, category_id, brand, season, gender),
            )
            conn.commit()

            current_product_id = cur.lastrowid
            products_count += 1
            continue

        if current_product_id is not None and is_variant_row(row):
            # Это вариант товара (первая колонка может быть пустой)
            size = str(row[3]).strip() if len(row) > 3 and pd.notna(row[3]) else ""
            color = str(row[4]).strip() if len(row) > 4 and pd.notna(row[4]) else ""
            barcode = str(row[6]).strip() if len(row) > 6 and pd.notna(row[6]) else ""  # Колонка 6 содержит штрихкод

            # Безопасная обработка числовых значений
            def safe_float(value, default=0.0):
                if pd.isna(value):
                    return default
                try:
                    return float(str(value).replace(",", ".").replace("\xa0", "").replace(" ", ""))
                except (ValueError, TypeError):
                    return default

            # Извлекаем данные о ценах и остатках из колонок 8-12
            stock = safe_float(row[8]) if len(row) > 8 else 0
            purchase_price = safe_float(row[9]) if len(row) > 9 else 0
            sale_price = safe_float(row[10]) if len(row) > 10 else 0
            new_price = safe_float(row[10]) if len(row) > 10 else 0
            total_price = safe_float(row[11]) if len(row) > 11 else 0
            discount = safe_float(row[12]) if len(row) > 12 else 0

            cur.execute(
                """
                INSERT INTO variants(product_id, size, color, barcode, stock, purchase_price, sale_price, new_price, total_price, discount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (current_product_id, size, color, barcode, stock, purchase_price, sale_price, new_price, total_price, discount),
            )
            conn.commit()
            variants_count += 1

    conn.close()
    print(f"Импортировано продуктов: {products_count}")
    print(f"Импортировано вариантов: {variants_count}")


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        create_db()
    import_excel()

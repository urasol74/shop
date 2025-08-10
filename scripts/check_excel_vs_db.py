#!/usr/bin/env python3
import os
import math
import sqlite3
import zipfile
import pandas as pd

BASE = "/home/ubuntu/shop"
DB_PATH = os.path.join(BASE, "instance", "db-der.db")
XLSX_PATH = os.path.join(BASE, "data", "db-der.xlsx")


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
        tmp_path = xlsx_path + '.tmp'
        with zipfile.ZipFile(xlsx_path, 'r') as zin, zipfile.ZipFile(tmp_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                zout.writestr(item, data)
                if item.filename == 'xl/SharedStrings.xml':
                    zout.writestr('xl/sharedStrings.xml', data)
        os.replace(tmp_path, xlsx_path)
    except Exception:
        pass


def isnonempty(x) -> bool:
    try:
        return (x is not None) and (not (isinstance(x, float) and math.isnan(x))) and str(x).strip() != ''
    except Exception:
        return False


def is_variant_row(r) -> bool:
    for idx in (3, 4, 6, 8, 9, 10, 11, 12):
        if len(r) > idx and isnonempty(r[idx]):
            return True
    return False


def scan_excel(xlsx_path: str):
    ensure_sharedstrings_lowercase(xlsx_path)
    df = pd.read_excel(xlsx_path, header=None)
    products_count = 0
    variants_count = 0
    distinct_articles = set()
    categories = set()
    have = False
    skips = ['оценка', 'параметри', 'відбір', 'магазин', 'склад', 'номенклатура', 'артикул']

    for _, row in df.iterrows():
        c0 = row[0] if len(row) > 0 else None
        s = str(c0).strip() if isnonempty(c0) else ''
        if s:
            low = s.lower()
            if any(k in low for k in skips):
                continue
            if ' ' in s and len(s.split(' ')) > 1:
                # product header: "<article> <category name>"
                parts = s.split(' ', 1)
                article = parts[0]
                category_name = parts[1]
                products_count += 1
                have = True
                distinct_articles.add(article)
                categories.add(category_name)
                continue
        if have and is_variant_row(row):
            variants_count += 1

    return {
        'excel_products': products_count,
        'excel_variants': variants_count,
        'excel_distinct_articles': len(distinct_articles),
        'excel_categories': len(categories),
    }


def scan_db(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("select count(*) from categories")
    db_categories = cur.fetchone()[0]
    cur.execute("select count(*) from products")
    db_products = cur.fetchone()[0]
    cur.execute("select count(*) from variants")
    db_variants = cur.fetchone()[0]
    cur.execute("select count(distinct article) from products")
    db_distinct_articles = cur.fetchone()[0]
    cur.execute("select count(distinct product_id) from variants")
    db_products_with_variants = cur.fetchone()[0]
    conn.close()
    return {
        'db_categories': db_categories,
        'db_products': db_products,
        'db_variants': db_variants,
        'db_distinct_articles': db_distinct_articles,
        'db_products_with_variants': db_products_with_variants,
    }


def main():
    excel = scan_excel(XLSX_PATH)
    db = scan_db(DB_PATH)
    print("Excel:")
    for k, v in excel.items():
        print(f"  {k}: {v}")
    print("DB:")
    for k, v in db.items():
        print(f"  {k}: {v}")
    print("Diff (DB - Excel):")
    for k_excel, v_excel in excel.items():
        k_db = k_excel.replace('excel_', 'db_')
        if k_db in db:
            print(f"  {k_db}: {db[k_db] - v_excel}")


if __name__ == '__main__':
    main()


